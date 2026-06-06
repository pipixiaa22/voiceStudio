# Novel Continuation Phase 3+4 — Generation Pipeline & Auto-Continue

> Scope: Phase 3 (Generation Pipeline) + Phase 4 (Continuous Writing)
> Approach: Enhance existing LangGraph workflow with structured output, unify generation paths, add auto-continue mode

## 1. Background

Phase 1+2 delivered:
- NarrativeState service (`narrative_state.py`)
- Structured output with `chapter_state` (completed goals, open threads, hooks)
- Blueprint depth levels
- Outline deviation detection in review
- Frontend: chapter_state tags, depth selector, knowledge increment display

Phase 3+4 builds on this foundation to create a unified generation pipeline and continuous writing mode.

## 2. Pipeline Upgrade (Phase 3)

### Current state

Two separate generation paths exist:
- `chapter_version` → `version_generator.generate_versions()` → `chapter_generator.generate_single_version()` — single LLM call, structured output
- `chapter_workflow` → `workflow.run_chapter_workflow()` — LangGraph 7-node pipeline, plain text output

### Target state

One unified path through LangGraph with structured output:

```
retrieve_memory -> check_conflicts -> plan -> draft (structured) -> review -> revise (if needed) -> extract -> persist
```

### Changes to `server/services/memory/workflow.py`

**`plan_node` (new, required):**
- Takes context + outline from state
- Short LLM call: "Given this outline and context, produce a scene plan for this chapter"
- Output: scene list with beats, estimated word count per scene
- Saves plan to `version.context_snapshot.plan`
- If planning fails, pipeline continues without plan (graceful degradation)

**`draft_chapter_node` (upgrade):**
- Use `generate_with_memory(structured_output=True)` instead of plain text
- Returns `{content_markdown, knowledge_updates, chapter_state}`
- Store all three in state

**`review_draft_node` (upgrade):**
- Use `review_content()` with outline context (from Phase 1+2)
- Return structured issues with severity levels

**`revise_draft_node` (upgrade):**
- Only revise if high-severity issues found
- If revision still has high issues, mark state as `needs_human_review`
- Use structured output for revision too

**`persist_version_node` (upgrade):**
- Save `chapter_state` to `version.context_snapshot`
- Create `NovelGraphChange` candidates from `knowledge_updates.graph_changes`
- Create `NovelMemoryChange` candidates from `knowledge_updates.memory_changes`
- Uses `_create_graph_change_candidates` and `_create_memory_change_candidates` from `chapter_generator.py`

**`extract_memory_node` (simplify):**
- No longer needs a separate LLM call
- Knowledge changes are already extracted from structured output in draft node
- This node becomes a no-op or is removed

### State type update

```python
class ChapterState(TypedDict):
    # Existing
    project_id: int
    chapter_id: int
    user_instruction: str
    version_type: str
    model_key: str
    model_config: dict
    context: dict
    memories: list
    conflicts: list
    draft: str
    review_result: dict
    revised_draft: str
    memory_changes: list
    version_id: int
    # New
    structured_result: dict       # {content_markdown, knowledge_updates, chapter_state}
    plan: str                     # scene plan text
    needs_human_review: bool      # high issues survived revision
```

## 3. Generation Unification (Phase 3)

### Remove standalone chapter_generator path

After upgrading the workflow, the `chapter_version` generation type dispatches through LangGraph:

**`server/services/novel/generation_runner.py`:**
- `_run_chapter_version(gen, params)` → calls `run_chapter_workflow()` instead of `generate_versions()`
- Remove `_run_chapter_workflow` (merged into chapter_version)
- `start_generation()` no longer needs `chapter_workflow` type

**`server/services/novel/version_generator.py`:**
- `generate_versions()` calls `run_chapter_workflow()` for each version type
- Returns combined results

**`server/services/novel/chapter_generator.py`:**
- Keep `_create_graph_change_candidates()` and `_create_memory_change_candidates()` as shared utilities
- Move them to a new `server/services/novel/knowledge_delta.py` or keep in chapter_generator
- `generate_single_version()` becomes internal to the workflow

### Route changes

**`server/routes/novels/chapters.py`:**
- `POST /generate-versions` → still works, now goes through pipeline
- `POST /generate-workflow` → removed (merged into generate-versions)

## 4. Auto-Continue Mode (Phase 4)

### Concept

User clicks "连续续写" → system generates N chapters sequentially → each chapter goes through the full pipeline → auto-confirms → updates narrative state → continues until done or paused.

### New route

`POST /api/novels/<pid>/auto-continue`

Params:
```json
{
  "count": 3,
  "version_type": "steady",
  "start_from_chapter_id": null
}
```

### Implementation

**`server/services/novel/auto_continue.py` (new):**

```python
def run_auto_continue(project_id, params):
    """Generate multiple chapters sequentially."""
    count = params.get('count', 3)
    version_type = params.get('version_type', 'steady')
    results = []

    for i in range(count):
        # 1. Create next chapter + outline node if needed
        chapter = _ensure_next_chapter(project_id, params)

        # 2. Run pipeline
        from server.services.memory.workflow import run_chapter_workflow
        result = run_chapter_workflow(
            project_id=project_id,
            chapter_id=chapter.id,
            version_type=version_type,
            model_config=params.get('model_config'),
        )

        # 3. Check for pause conditions
        if result.get('needs_human_review'):
            results.append({
                'chapter_id': chapter.id,
                'status': 'paused',
                'reason': 'high_severity_review',
                'review_result': result.get('review_result'),
            })
            break

        # 4. Auto-confirm chapter
        chapter.status = 'confirmed'
        db.session.commit()

        # 5. Generate summary
        from server.services.novel.summarizer import generate_summary
        generate_summary(chapter.id)

        results.append({
            'chapter_id': chapter.id,
            'version_id': result.get('version_id'),
            'status': 'confirmed',
        })

    return {'chapters': results, 'completed': len([r for r in results if r['status'] == 'confirmed'])}
```

### Pause conditions

Auto-continue pauses (checked after persist, before auto-confirm) when:
1. `needs_human_review` is True — high-severity review issues survived auto-revision
2. Any GraphChange in `knowledge_updates.graph_changes` has confidence < 0.5
3. Any MemoryChange in `knowledge_updates.memory_changes` has `change_type: 'modify'` (editing existing facts is risky)
4. Chapter generation fails (LLM error, timeout) — caught as exception, chapter not confirmed

### SSE integration

Auto-continue uses the existing `NovelGeneration` + SSE infrastructure:
- Create one `NovelGeneration` record for the entire auto-continue batch
- Update progress as each chapter completes: `{progress: 33, current_chapter: 2, total: 3}`
- Broadcast `progress` events via SSE
- On completion or pause, broadcast `completed` with full results

### Frontend

**`web/src/components/novel/NovelGenerationPanel.vue`:**
- Add "连续续写" button below the existing "生成续写版本" button
- Clicking opens a small modal/drawer with:
  - Chapter count selector (2-5)
  - Version type selector (same as single generation)
  - Start button
- During auto-continue, show progress: "正在生成第 2/5 章..."
- On pause, show the review issues and a "继续" button

## 5. Data Flow

### Single chapter (unified pipeline)
```
User clicks "续写版本"
  -> POST /generate-versions
  -> generation_runner.start_generation('chapter_version')
  -> _run_chapter_version()
  -> run_chapter_workflow(project_id, chapter_id, ...)
     -> retrieve_memory_node: build context + RAG
     -> check_conflicts_node: detect setting conflicts
     -> plan_node: generate scene plan (short LLM call)
     -> draft_chapter_node: generate structured output
        -> content_markdown + knowledge_updates + chapter_state
     -> review_draft_node: consistency review with outline context
     -> revise_draft_node: fix high-severity issues (if any)
        -> if still high issues: needs_human_review = True
     -> persist_version_node: save version + GraphChange + MemoryChange
  -> SSE: completed with version + knowledge changes
```

### Auto-continue
```
User clicks "连续续写" -> selects count=3
  -> POST /auto-continue
  -> auto_continue.run_auto_continue()
  -> For each chapter:
     -> _ensure_next_chapter(): create chapter + outline
     -> run_chapter_workflow(): full pipeline
     -> Check pause conditions
     -> Auto-confirm chapter
     -> Generate summary
     -> SSE: progress {chapter: N, total: 3}
  -> SSE: completed with all results
```

## 6. Files Modified

### Modified backend files:
- `server/services/memory/workflow.py` — upgrade all nodes, add plan_node, structured output
- `server/services/novel/generation_runner.py` — unify chapter_version through workflow
- `server/services/novel/version_generator.py` — delegate to workflow
- `server/services/novel/chapter_generator.py` — extract knowledge_delta utilities

### New backend files:
- `server/services/novel/auto_continue.py` — auto-continue logic
- `server/services/novel/knowledge_delta.py` — shared GraphChange/MemoryChange creation (optional, could stay in chapter_generator)

### Modified frontend files:
- `web/src/components/novel/NovelGenerationPanel.vue` — add auto-continue button + modal
- `web/src/stores/novels.js` — add auto-continue action

## 7. Testing

- Verify single chapter pipeline produces structured output with chapter_state
- Verify knowledge changes are created from structured output
- Verify auto-continue generates N chapters sequentially
- Verify auto-continue pauses on high-severity review issues
- Verify auto-continue pauses on low-confidence graph changes
- Verify SSE progress updates correctly during auto-continue
- Verify narrative state updates after each auto-continued chapter

## 8. Risks

1. **LangGraph complexity**: Adding a plan node increases pipeline length. Mitigation: plan node is a short LLM call, can be skipped with a flag.
2. **Auto-continue cost**: N chapters = N * (plan + draft + review + revise) LLM calls. Mitigation: user selects count, can stop anytime.
3. **State consistency**: If auto-continue fails mid-way, some chapters are confirmed and some aren't. Mitigation: each chapter is independently confirmed, partial results are returned.
4. **Backward compatibility**: Unifying paths may break existing `chapter_workflow` endpoint. Mitigation: redirect to `chapter_version`.
