"""LangGraph multi-step chapter generation workflow."""

from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END


class ChapterState(TypedDict):
    """State for the chapter generation workflow."""
    project_id: int
    chapter_id: int
    user_instruction: str
    version_type: str
    model_key: str

    # Intermediate results
    context: dict
    memories: list
    conflicts: list
    draft: str
    review_result: dict
    revised_draft: str
    memory_changes: list
    version_id: int


def retrieve_memory_node(state: ChapterState) -> dict:
    """Node: Retrieve relevant memories."""
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


def draft_chapter_node(state: ChapterState) -> dict:
    """Node: Generate chapter draft with RAG."""
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

    draft = generate_with_memory(
        project=project,
        chapter=chapter,
        context=state.get('context', {}),
        system_prompt=system_prompt,
        user_instruction=state.get('user_instruction', ''),
        model_key=state.get('model_key'),
        version_type=state.get('version_type', 'custom'),
    )

    return {'draft': draft}


def review_draft_node(state: ChapterState) -> dict:
    """Node: Review draft for consistency."""
    from server.services.novel.consistency_reviewer import review_chapter

    try:
        result = review_chapter(state['project_id'], state['chapter_id'])
    except Exception:
        result = {'score': 0, 'issues': []}

    return {'review_result': result}


def revise_draft_node(state: ChapterState) -> dict:
    """Node: Revise draft based on review feedback."""
    review = state.get('review_result', {})
    issues = review.get('issues', [])
    high_issues = [i for i in issues if i.get('severity') == 'high']

    if not high_issues:
        return {'revised_draft': state.get('draft', '')}

    from server.services.novel import get_llm_provider

    issue_text = '\n'.join(f'- {i["description"]}' for i in high_issues[:5])
    prompt = f"""请根据以下审稿意见修改章节内容，只修改有问题的部分，保持其他内容不变。

【审稿意见】
{issue_text}

【原稿】
{state.get('draft', '')[:8000]}

请输出修改后的完整章节内容。只输出正文，不要解释。"""

    provider, default_model = get_llm_provider()
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
        revised = state.get('draft', '')

    return {'revised_draft': revised}


def extract_memory_node(state: ChapterState) -> dict:
    """Node: Extract memory changes from final draft."""
    from server.services.memory.memory_writer import extract_and_create_changes

    content = state.get('revised_draft') or state.get('draft', '')
    if not content:
        return {'memory_changes': []}

    try:
        changes = extract_and_create_changes(
            state['project_id'], state['chapter_id'], content
        )
        return {'memory_changes': [c.id for c in changes]}
    except Exception:
        return {'memory_changes': []}


def persist_version_node(state: ChapterState) -> dict:
    """Node: Save the final version."""
    from server.models import db
    from server.models.novel.chapter import NovelChapterVersion

    content = state.get('revised_draft') or state.get('draft', '')
    if not content:
        return {}

    version = NovelChapterVersion(
        chapter_id=state['chapter_id'],
        version_type=state.get('version_type', 'custom'),
        title=f'{state.get("version_type", "custom")}版',
        content_markdown=content,
        model=state.get('model_key', 'workflow'),
        accepted=False,
    )
    db.session.add(version)
    db.session.commit()

    return {'version_id': version.id}


def build_chapter_workflow():
    """Build the LangGraph workflow for chapter generation.

    Flow: retrieve_memory -> check_conflicts -> draft -> review -> revise -> extract_memory -> persist
    """
    graph = StateGraph(ChapterState)

    graph.add_node('retrieve_memory', retrieve_memory_node)
    graph.add_node('check_conflicts', check_conflicts_node)
    graph.add_node('draft_chapter', draft_chapter_node)
    graph.add_node('review_draft', review_draft_node)
    graph.add_node('revise_draft', revise_draft_node)
    graph.add_node('extract_memory', extract_memory_node)
    graph.add_node('persist_version', persist_version_node)

    graph.set_entry_point('retrieve_memory')
    graph.add_edge('retrieve_memory', 'check_conflicts')
    graph.add_edge('check_conflicts', 'draft_chapter')
    graph.add_edge('draft_chapter', 'review_draft')
    graph.add_edge('review_draft', 'revise_draft')
    graph.add_edge('revise_draft', 'extract_memory')
    graph.add_edge('extract_memory', 'persist_version')
    graph.add_edge('persist_version', END)

    return graph.compile()


def run_chapter_workflow(project_id, chapter_id, user_instruction='',
                         version_type='custom', model_key=None):
    """Run the full chapter generation workflow.

    Returns:
        Final state dict with version_id and memory_changes.
    """
    workflow = build_chapter_workflow()

    initial_state = {
        'project_id': project_id,
        'chapter_id': chapter_id,
        'user_instruction': user_instruction,
        'version_type': version_type,
        'model_key': model_key or '',
        'context': {},
        'memories': [],
        'conflicts': [],
        'draft': '',
        'review_result': {},
        'revised_draft': '',
        'memory_changes': [],
        'version_id': 0,
    }

    result = workflow.invoke(initial_state)
    return result
