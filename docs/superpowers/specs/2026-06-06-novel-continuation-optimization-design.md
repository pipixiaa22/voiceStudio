# Novel Continuation Module Optimization — Phase 1+2 Design

> Scope: Phase 1 (Three-level outline & blueprint enhancement) + Phase 2 (Structured knowledge update闭环)
> Approach: Layered extraction — NarrativeState service + refactored context_builder + enhanced structured output

## 1. Background

The novel continuation module already has substantial infrastructure:
- Three-level outline (volume/chapter nodes + overall_outline in project settings)
- Blueprint generator creating characters, entities, relations, events, foreshadowing, memory seeds
- Context builder with 10 context sections
- Chapter generator with structured output (content_markdown + knowledge_updates)
- GraphChange/MemoryChange confirmation workflow
- LangGraph 7-node workflow
- Consistency reviewer with 9 dimensions
- RAG memory system

This optimization enhances the architecture without rebuilding from scratch.

## 2. NarrativeState Service

### New file: `server/services/novel/narrative_state.py`

A pure data aggregation service that loads all narrative context from the database.

```python
@dataclass
class NarrativeState:
    project: NovelProject
    overall_outline: dict
    current_volume: NovelOutlineNode | None
    current_chapter_outline: NovelOutlineNode | None
    characters: list[NovelEntity]
    relations: list[NovelRelation]
    events: list[NovelEvent]
    event_relations: list[NovelEventRelation]
    memories: list[NovelMemory]
    open_foreshadowing: list[str]
    recent_chapters: list[NovelChapter]
    world_settings: dict
```

Functions:
- `load_state(project_id, chapter_id=None) -> NarrativeState` — Loads all data from DB
- `summarize_for_context(state: NarrativeState, max_budget=12000) -> dict` — Produces context dict compatible with current context_builder output format

### Refactor: `server/services/novel/context_builder.py`

`build_context()` will be refactored to:
1. Call `load_state()` to get NarrativeState
2. Call `summarize_for_context()` to produce the context dict
3. Keep the same return format for backward compatibility

Responsibility split:
- `narrative_state.py` — DB queries, data aggregation, budget-controlled formatting
- `context_builder.py` — thin wrapper, backward-compatible API
- `rag_chain.py` — RAG retrieval, conflict detection, prompt assembly, LLM call (unchanged)

### `server/services/memory/rag_chain.py` (no structural change)

`generate_with_memory()` keeps its current role:
- Receives context dict from context_builder
- Handles RAG retrieval and conflict detection
- Builds prompt sections and calls LLM
- Only change: enhanced structured output instruction (chapter_state)

## 3. Enhanced Structured Output

### Current output format:
```json
{
  "content_markdown": "正文",
  "knowledge_updates": {
    "graph_changes": [...],
    "memory_changes": [...]
  }
}
```

### New output format (add chapter_state):
```json
{
  "content_markdown": "正文",
  "knowledge_updates": {
    "graph_changes": [...],
    "memory_changes": [...]
  },
  "chapter_state": {
    "completed_plot_goals": ["本章完成的剧情目标"],
    "open_threads": ["未解决的悬念"],
    "new_questions": ["本章新提出的问题"],
    "next_chapter_hooks": ["下一章钩子"]
  }
}
```

### Changes:

**`server/services/memory/rag_chain.py`:**
- `_build_structured_output_instruction()` — Add `chapter_state` to JSON schema
- `_parse_structured_generation()` — Parse and validate `chapter_state`

**`server/services/novel/chapter_generator.py`:**
- Save `chapter_state` to `version.context_snapshot` alongside the context hash
- Return `chapter_state` in the version dict for frontend display

**`server/models/novel/chapter.py`:**
- `NovelChapterVersion.to_dict()` — Include `chapter_state` from context_snapshot

## 4. Blueprint Depth Levels

### Three depth levels:

| Level | Name | Output | LLM Tokens |
|-------|------|--------|------------|
| quick | 快速蓝图 | 总纲 + 1卷 + 8-12章, minimal characters | ~3000 |
| standard | 标准蓝图 | 总纲 + 多卷骨架 + 当前卷详细章纲 | ~4000 |
| deep | 深度蓝图 | 总纲 + 全书卷纲 + 详细章纲 + 角色/事件/伏笔/道具/记忆种子 | ~6000 |

### Changes:

**`server/services/novel/blueprint_generator.py`:**
- `generate_blueprint()` accepts `depth` param ('quick', 'standard', 'deep')
- Adjust system prompt based on depth:
  - quick: fewer characters (2-4), fewer events (2-3), 1 volume
  - standard: current behavior (4-8 characters, 1-2 volumes)
  - deep: more characters (6-10), more events (5-8), all volumes, detailed memory seeds
- `_resolve_outline_chapter_count()` adjusts based on depth

**`web/src/components/novel/NovelBlueprintWizard.vue`:**
- Add radio group for depth selection before generation
- Default: 'standard'

## 5. Prompt Strategy Enhancement

### Enhanced review prompt:

**`server/services/novel/prompt_templates.py`:**
- Add `build_outline_deviation_check()` — generates outline context for review
- Enhance `build_review_prompt()` to include:
  - 总大纲 for main-line deviation detection
  - 卷大纲 for volume-goal deviation detection
  - 章大纲 for chapter-goal deviation detection
  - New review dimensions: outline deviation, pacing against target_words

### Enhanced chapter draft prompt:

**`server/services/memory/rag_chain.py`:**
- `_build_structured_output_instruction()` adds explicit instruction:
  - "chapter_state 必须包含 completed_plot_goals, open_threads, new_questions, next_chapter_hooks"
  - "completed_plot_goals 必须对照章大纲的 plot_goal 和 conflict_goal"

## 6. Frontend Changes

### `web/src/components/novel/NovelVersionList.vue`
- Below each version, show chapter_state if available:
  - Completed goals (green tags)
  - Open threads (yellow tags)
  - Next chapter hooks (blue tags)

### `web/src/components/novel/NovelBlueprintWizard.vue`
- Add depth level radio group at the top of the wizard
- Three options: 快速蓝图 / 标准蓝图 / 深度蓝图
- Default: 标准蓝图

### `web/src/components/novel/NovelGenerationPanel.vue`
- After generation completes, show a summary bar:
  - "本次生成引入 X 条图谱变更, Y 条记忆变更"
  - Link to graph changes review

## 7. Data Flow

```
User clicks "续写版本"
  -> Frontend sends POST /generate-versions
  -> generation_runner.start_generation()
  -> _run_chapter_version()
  -> version_generator.generate_versions()
  -> chapter_generator.generate_single_version()
     -> narrative_state.load_state(project_id, chapter_id)
     -> narrative_state.summarize_for_context(state)
     -> context_builder.build_context() [delegates to NarrativeState]
     -> rag_chain.generate_with_memory()
        -> retrieve_memories()
        -> detect_conflicts()
        -> build prompt with 3-level outline + memories + context
        -> LLM call with structured output instruction
        -> parse response: content_markdown + knowledge_updates + chapter_state
     -> create NovelChapterVersion with chapter_state in context_snapshot
     -> create NovelGraphChange candidates
     -> create NovelMemoryChange candidates
  -> SSE broadcast to frontend
  -> Frontend shows versions with chapter_state
```

## 8. Files Modified

### New files:
- `server/services/novel/narrative_state.py`

### Modified backend files:
- `server/services/novel/context_builder.py` — delegate to NarrativeState
- `server/services/novel/chapter_generator.py` — save chapter_state
- `server/services/novel/blueprint_generator.py` — depth levels
- `server/services/novel/prompt_templates.py` — outline deviation check
- `server/services/memory/rag_chain.py` — chapter_state in structured output
- `server/models/novel/chapter.py` — version.to_dict() includes chapter_state

### Modified frontend files:
- `web/src/components/novel/NovelVersionList.vue` — show chapter_state
- `web/src/components/novel/NovelBlueprintWizard.vue` — depth selector
- `web/src/components/novel/NovelGenerationPanel.vue` — knowledge增量 display

## 9. Testing

- Verify existing generation path still works (no regressions)
- Test NarrativeState.load_state() returns correct data for projects with/without chapters
- Test structured output parsing with and without chapter_state
- Test blueprint depth levels produce different output volumes
- Test review prompt includes outline context
- Frontend: verify version list shows chapter_state tags

## 10. Risks

1. **Backward compatibility**: Existing versions don't have chapter_state. Version list must handle missing chapter_state gracefully.
2. **Context budget**: Adding chapter_state to the output may increase LLM token usage. Budget is managed by existing `_truncate()` calls.
3. **NarrativeState query count**: Loading all data in one call may be slow for large projects. Mitigation: limit queries (e.g., recent 5 chapters, top 10 characters).
