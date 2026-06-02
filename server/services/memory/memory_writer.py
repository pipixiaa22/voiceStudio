"""Memory write operations: create, update, index."""

from server.models import db
from server.models.novel.memory import NovelMemory


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
        # Delete old vectors first
        delete_by_memory_id(memory.project_id, memory.id)
        add_documents(memory.project_id, chunks, metadatas)
        memory.vector_status = 'indexed'
    except Exception:
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
