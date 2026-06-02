"""Memory write operations: create, update, index."""

import logging
from server.models import db
from server.models.novel.memory import NovelMemory

logger = logging.getLogger(__name__)

# Re-export for backward compatibility
from server.services.memory.utils import parse_memory_json as _parse_memory_json


def create_memory(project_id, content, memory_type, title=None, source_type='manual_note',
                  source_id=None, importance=3, summary=None, metadata=None):
    """Create a new memory record and queue it for indexing.

    Returns:
        The created NovelMemory instance.
    """
    memory = NovelMemory(
        project_id=project_id,
        source_type=source_type,
        source_id=source_id,
        memory_type=memory_type,
        title=title,
        content=content,
        summary=summary,
        importance=importance,
        status='active',
        vector_status='pending',
    )
    if metadata:
        memory.metadata_ = metadata

    db.session.add(memory)
    db.session.commit()
    return memory


def index_memory(memory):
    """Index a single memory into the vector store.

    Updates vector_status to 'indexed' on success, 'failed' on error.
    """
    from server.services.memory.vector_store import add_documents, delete_by_memory_id
    from server.services.memory.chunker import chunk_text

    chunks = chunk_text(memory.content)
    if not chunks:
        memory.vector_status = 'indexed'
        db.session.commit()
        return

    metadatas = [{
        'memory_id': str(memory.id),
        'memory_type': memory.memory_type,
        'source_type': memory.source_type,
        'source_id': str(memory.source_id) if memory.source_id else '',
        'importance': memory.importance,
        'chunk_index': i,
    } for i in range(len(chunks))]

    try:
        delete_by_memory_id(memory.project_id, memory.id)
        ids = add_documents(memory.project_id, chunks, metadatas)
        if ids is None:
            memory.vector_status = 'pending'
        else:
            memory.vector_status = 'indexed'
    except Exception:
        logger.exception('Failed to index memory %s', memory.id)
        memory.vector_status = 'failed'

    db.session.commit()


def create_and_index(project_id, content, memory_type, **kwargs):
    """Create a memory and immediately index it.

    Returns:
        The created NovelMemory instance.
    """
    memory = create_memory(project_id, content, memory_type, **kwargs)
    index_memory(memory)
    return memory


def extract_and_create_changes(project_id, chapter_id, chapter_content):
    """Extract memories from a chapter and create pending change records.

    Called after chapter confirmation. Uses LLM to identify new facts.

    Returns:
        List of created NovelMemoryChange instances.
    """
    from server.models.novel.memory import NovelMemoryChange
    from server.services.novel.prompt_templates import build_memory_extract_prompt
    from server.services.novel import get_llm_provider
    from server.services.novel.context_builder import build_context
    from server.models.novel.chapter import NovelChapter
    from server.services.memory.utils import parse_memory_json

    chapter = NovelChapter.query.get(chapter_id)
    context = build_context(project_id, chapter_id) if chapter else {}

    prompt = build_memory_extract_prompt(chapter_content, context)

    provider, default_model = get_llm_provider()
    messages = [{'role': 'user', 'content': prompt}]

    try:
        response = provider.complete(
            messages,
            model=default_model,
            system_prompt='你是小说记忆管理助手，只输出 JSON。',
            max_tokens=4096,
            timeout=60,
        )
    except Exception:
        logger.exception('LLM call failed during memory extraction')
        return []

    result = parse_memory_json(response)
    if not result:
        return []

    changes = []

    # Create "add" changes for new memories (skip duplicates)
    for item in result.get('new_memories', []):
        if not item.get('content'):
            continue
        title = item.get('title', '')
        # Check for existing memory with same title in project
        if title:
            existing = NovelMemory.query.filter_by(
                project_id=project_id, title=title, status='active'
            ).first()
            if existing:
                continue
        change = NovelMemoryChange(
            project_id=project_id,
            change_type='add',
            after={
                'title': title,
                'content': item['content'],
                'memory_type': item.get('memory_type', 'summary'),
                'importance': item.get('importance', 3),
                'summary': item.get('summary', ''),
                'source_type': 'ai_extract',
                'source_id': chapter_id,
            },
            source='ai_extract',
            status='pending',
        )
        db.session.add(change)
        changes.append(change)

    # Create "modify" changes for updates (populate before field)
    for item in result.get('updates', []):
        existing_title = item.get('existing_title', '')
        existing = None
        if existing_title:
            existing = NovelMemory.query.filter_by(
                project_id=project_id, title=existing_title, status='active'
            ).first()

        change = NovelMemoryChange(
            project_id=project_id,
            change_type='modify',
            after={
                'title': existing_title,
                'content': item.get('new_content', ''),
                'memory_type': item.get('memory_type', 'summary'),
            },
            source='ai_extract',
            status='pending',
        )
        if existing:
            change.memory_id = existing.id
            change.before = {
                'title': existing.title,
                'content': existing.content,
                'memory_type': existing.memory_type,
                'importance': existing.importance,
            }
        db.session.add(change)
        changes.append(change)

    db.session.commit()
    return changes
