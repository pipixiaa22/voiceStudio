"""LangGraph multi-step chapter generation workflow with structured output."""

from typing import TypedDict
from langgraph.graph import StateGraph, END


class ChapterState(TypedDict):
    """State for the chapter generation workflow."""
    project_id: int
    chapter_id: int
    user_instruction: str
    version_type: str
    model_key: str
    model_config: dict

    # Intermediate results
    context: dict
    memories: list
    conflicts: list
    plan: str
    structured_result: dict
    draft: str
    review_result: dict
    revised_draft: str
    needs_human_review: bool
    version_id: int


def retrieve_memory_node(state: ChapterState) -> dict:
    """Node: Retrieve relevant memories and build context."""
    from server.services.novel.context_builder import build_context
    from server.services.memory.retriever import retrieve_memories

    context = build_context(
        state['project_id'], state['chapter_id'],
        state.get('user_instruction', ''),
    )
    query = context.get('outline', '') + ' ' + state.get('user_instruction', '')
    memories = retrieve_memories(state['project_id'], query, k=10)

    return {'context': context, 'memories': memories}


def check_conflicts_node(state: ChapterState) -> dict:
    """Node: Check for setting conflicts."""
    from server.services.memory.conflict_detector import detect_conflicts

    conflicts = []
    if state.get('context', {}).get('outline'):
        try:
            conflicts = detect_conflicts(
                state['project_id'],
                state['context']['outline'],
                state.get('memories'),
            )
        except Exception:
            pass

    return {'conflicts': conflicts}


def plan_node(state: ChapterState) -> dict:
    """Node: Generate a scene plan for the chapter."""
    from server.services.novel import get_llm_provider

    context = state.get('context', {})
    outline = context.get('outline', '')
    if not outline:
        return {'plan': ''}

    prompt = f"""根据以下章大纲，生成本章的场景计划。每个场景包含：场景目标、主要人物、预计字数。

【章大纲】
{outline}

【续写简报】
{context.get('continuation_brief', '')}

请以简洁的列表格式输出场景计划，不要超过 5 个场景。只输出计划，不要写正文。"""

    try:
        provider, default_model = get_llm_provider(state.get('model_config'))
        response = provider.complete(
            [{'role': 'user', 'content': prompt}],
            model=state.get('model_key') or default_model,
            system_prompt='你是小说场景规划师。',
            max_tokens=1024,
            timeout=30,
        )
        return {'plan': response.strip()}
    except Exception:
        return {'plan': ''}


def draft_chapter_node(state: ChapterState) -> dict:
    """Node: Generate chapter draft with structured output."""
    from server.models.novel.project import NovelProject
    from server.models.novel.chapter import NovelChapter
    from server.services.novel.prompt_templates import build_chapter_system_prompt
    from server.services.memory.rag_chain import generate_with_memory

    project = NovelProject.query.get_or_404(state['project_id'])
    chapter = NovelChapter.query.get_or_404(state['chapter_id'])

    system_prompt = build_chapter_system_prompt(
        project.genre,
        version_type=state.get('version_type', 'custom'),
        style_guide=project.style_guide,
    )

    plan = state.get('plan', '')
    if plan:
        system_prompt += f'\n\n【场景计划】\n{plan}\n请按照此计划展开写作。'

    structured_result = generate_with_memory(
        project=project,
        chapter=chapter,
        context=state.get('context', {}),
        system_prompt=system_prompt,
        user_instruction=state.get('user_instruction', ''),
        model_key=state.get('model_key'),
        model_config=state.get('model_config'),
        version_type=state.get('version_type', 'custom'),
        structured_output=True,
    )

    return {
        'structured_result': structured_result,
        'draft': structured_result.get('content_markdown', ''),
    }


def review_draft_node(state: ChapterState) -> dict:
    """Node: Review draft for consistency."""
    from server.services.novel.consistency_reviewer import review_content

    draft = state.get('draft', '')
    if not draft:
        return {'review_result': {'overall_score': 0, 'issues': []}}

    try:
        result = review_content(
            state['project_id'],
            state['chapter_id'],
            draft,
            params={'model_config': state.get('model_config')},
        )
    except Exception:
        result = {'overall_score': 0, 'issues': []}

    return {'review_result': result}


def revise_draft_node(state: ChapterState) -> dict:
    """Node: Revise draft if high-severity issues found."""
    review = state.get('review_result', {})
    issues = review.get('issues', [])
    high_issues = [i for i in issues if i.get('severity') == 'high']

    if not high_issues:
        return {'revised_draft': state.get('draft', ''), 'needs_human_review': False}

    from server.services.novel import get_llm_provider

    issue_text = '\n'.join(f'- {i["description"]}' for i in high_issues[:5])
    prompt = f"""请根据以下审稿意见修改章节内容，只修改有问题的部分，保持其他内容不变。

【审稿意见】
{issue_text}

【原稿】
{state.get('draft', '')[:8000]}

请输出修改后的完整章节内容。只输出正文，不要解释。"""

    provider, default_model = get_llm_provider(state.get('model_config'))
    messages = [{'role': 'user', 'content': prompt}]

    try:
        revised = provider.complete(
            messages,
            model=state.get('model_key') or default_model,
            system_prompt='你是小说修改助手。',
            max_tokens=8192,
            timeout=120,
        )
    except Exception:
        return {'revised_draft': state.get('draft', ''), 'needs_human_review': True}

    # Re-review the revised draft
    try:
        from server.services.novel.consistency_reviewer import review_content
        re_review = review_content(
            state['project_id'],
            state['chapter_id'],
            revised,
            params={'model_config': state.get('model_config')},
        )
        re_high = [i for i in re_review.get('issues', []) if i.get('severity') == 'high']
        needs_human = len(re_high) > 0
    except Exception:
        needs_human = False

    return {'revised_draft': revised, 'needs_human_review': needs_human}


def persist_version_node(state: ChapterState) -> dict:
    """Node: Save the final version with knowledge changes."""
    import json
    from server.models import db
    from server.models.novel.chapter import NovelChapterVersion

    content = state.get('revised_draft') or state.get('draft', '')
    if not content:
        return {}

    structured_result = state.get('structured_result', {})
    chapter_state = structured_result.get('chapter_state')
    knowledge_updates = structured_result.get('knowledge_updates') or {}

    version = NovelChapterVersion(
        chapter_id=state['chapter_id'],
        version_type=state.get('version_type', 'custom'),
        title=f'{state.get("version_type", "custom")}版',
        content_markdown=content,
        model=state.get('model_key', 'workflow'),
        accepted=False,
    )

    snapshot = {'context_hash': hash(json.dumps(state.get('context', {}), sort_keys=True, default=str))}
    if chapter_state:
        snapshot['chapter_state'] = chapter_state
    if state.get('plan'):
        snapshot['plan'] = state['plan']
    version.context_snapshot = snapshot

    db.session.add(version)
    db.session.flush()

    # Create knowledge change candidates
    from server.services.novel.chapter_generator import _create_graph_change_candidates, _create_memory_change_candidates
    _create_graph_change_candidates(
        project_id=state['project_id'],
        chapter_id=state['chapter_id'],
        version_id=version.id,
        changes=knowledge_updates.get('graph_changes') or [],
    )
    _create_memory_change_candidates(
        project_id=state['project_id'],
        chapter_id=state['chapter_id'],
        version_id=version.id,
        changes=knowledge_updates.get('memory_changes') or [],
    )

    db.session.commit()

    return {'version_id': version.id}


def build_chapter_workflow():
    """Build the LangGraph workflow for chapter generation.

    Flow: retrieve_memory -> check_conflicts -> plan -> draft -> review -> revise -> persist
    """
    graph = StateGraph(ChapterState)

    graph.add_node('retrieve_memory', retrieve_memory_node)
    graph.add_node('check_conflicts', check_conflicts_node)
    graph.add_node('plan', plan_node)
    graph.add_node('draft_chapter', draft_chapter_node)
    graph.add_node('review_draft', review_draft_node)
    graph.add_node('revise_draft', revise_draft_node)
    graph.add_node('persist_version', persist_version_node)

    graph.set_entry_point('retrieve_memory')
    graph.add_edge('retrieve_memory', 'check_conflicts')
    graph.add_edge('check_conflicts', 'plan')
    graph.add_edge('plan', 'draft_chapter')
    graph.add_edge('draft_chapter', 'review_draft')
    graph.add_edge('review_draft', 'revise_draft')
    graph.add_edge('revise_draft', 'persist_version')
    graph.add_edge('persist_version', END)

    return graph.compile()


def run_chapter_workflow(project_id, chapter_id, user_instruction='',
                         version_type='custom', model_key=None, model_config=None):
    """Run the full chapter generation workflow.

    Returns:
        Final state dict with version_id, needs_human_review, review_result.
    """
    workflow = build_chapter_workflow()

    initial_state: ChapterState = {
        'project_id': project_id,
        'chapter_id': chapter_id,
        'user_instruction': user_instruction,
        'version_type': version_type,
        'model_key': model_key or '',
        'model_config': model_config or {},
        'context': {},
        'memories': [],
        'conflicts': [],
        'plan': '',
        'structured_result': {},
        'draft': '',
        'review_result': {},
        'revised_draft': '',
        'needs_human_review': False,
        'version_id': 0,
    }

    result = workflow.invoke(initial_state)
    return result
