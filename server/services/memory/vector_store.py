"""Vector store wrapper with project-level isolation.

Supports two backends:
- ChromaDB (default, local file-based)
- pgvector (PostgreSQL, auto-selected when DATABASE_URL is postgresql)
"""

import os
import logging
import threading

logger = logging.getLogger(__name__)

_stores = {}
_stores_lock = threading.Lock()


def _is_pgvector_available():
    """Check if the current database is PostgreSQL (pgvector-capable)."""
    db_url = os.environ.get('DATABASE_URL', '')
    return db_url.startswith('postgresql')


def get_vector_store(project_id):
    """Get or create a vector store for a project.

    Each project gets its own collection to prevent cross-project contamination.
    Thread-safe: entire creation is inside the lock to prevent duplicates.

    Backend selection:
    - If DATABASE_URL is PostgreSQL → use pgvector (same connection)
    - Otherwise → use ChromaDB (local file)
    """
    project_id = str(project_id)
    with _stores_lock:
        if project_id in _stores:
            return _stores[project_id]

        from server.services.memory.embeddings import get_embeddings
        embeddings = get_embeddings()
        if embeddings is None:
            return None

        if _is_pgvector_available():
            store = _create_pgvector_store(project_id, embeddings)
        else:
            store = _create_chroma_store(project_id, embeddings)

        if store is not None:
            _stores[project_id] = store
        return store


def _create_pgvector_store(project_id, embeddings):
    """Create a pgvector-backed store using the same PostgreSQL connection."""
    try:
        from langchain_postgres import PGVector

        connection_string = os.environ.get('DATABASE_URL', '')
        # SQLAlchemy URL format works directly with langchain-postgres
        collection_name = f'novel_{project_id}'

        store = PGVector(
            connection=connection_string,
            embeddings=embeddings,
            collection_name=collection_name,
            use_jsonb=True,
        )
        logger.info(f'Using pgvector for project {project_id}')
        return store
    except Exception as e:
        logger.warning(f'Failed to create pgvector store, falling back to ChromaDB: {e}')
        return _create_chroma_store(project_id, embeddings)


def _create_chroma_store(project_id, embeddings):
    """Create a ChromaDB-backed store (local file)."""
    try:
        persist_dir = os.environ.get('CHROMADB_PERSIST_DIR') or os.path.join(os.getcwd(), 'data', 'chromadb')
        os.makedirs(persist_dir, exist_ok=True)

        from langchain_community.vectorstores import Chroma
        store = Chroma(
            collection_name=f'novel_{project_id}',
            embedding_function=embeddings,
            persist_directory=persist_dir,
        )
        logger.info(f'Using ChromaDB for project {project_id}')
        return store
    except Exception as e:
        logger.error(f'Failed to create ChromaDB store: {e}')
        return None


def invalidate_store(project_id):
    """Remove a cached store so it will be recreated on next access."""
    project_id = str(project_id)
    with _stores_lock:
        _stores.pop(project_id, None)


def add_documents(project_id, texts, metadatas=None):
    """Add documents to the project's vector store.

    Returns:
        List of document IDs, or None if store unavailable.
    """
    store = get_vector_store(project_id)
    if store is None:
        return None

    ids = store.add_texts(texts=texts, metadatas=metadatas)
    return ids


def search(project_id, query, k=10, filter_dict=None):
    """Search the project's vector store.

    Returns:
        List of (Document, score) tuples, or empty list if store unavailable.
    """
    store = get_vector_store(project_id)
    if store is None:
        return []

    kwargs = {'k': k}
    if filter_dict:
        kwargs['filter'] = filter_dict

    return store.similarity_search_with_score(query, **kwargs)


def delete_by_memory_id(project_id, memory_id):
    """Delete all chunks belonging to a memory from the vector store."""
    store = get_vector_store(project_id)
    if store is None:
        return

    try:
        store.delete(where={'memory_id': str(memory_id)})
    except Exception:
        logger.warning(f'Failed to delete vectors for memory {memory_id}')


def _clear_collection(store):
    """Delete all documents from a collection.

    Tries multiple strategies since the API varies across backends.
    """
    # Try ChromaDB-style clear
    try:
        result = store.get(include=[])
        all_ids = result.get('ids', [])
        if all_ids:
            store.delete(ids=all_ids)
        return
    except Exception:
        pass

    try:
        store._collection.delete(where={'memory_id': {'$ne': '__no_match__'}})
        return
    except Exception:
        pass

    try:
        store._collection.delete(where={})
        return
    except Exception:
        pass

    # Try pgvector-style clear (delete by filter)
    try:
        store.delete(where={'memory_id': {'$ne': '__no_match__'}})
        return
    except Exception:
        pass

    logger.warning('All collection clear strategies failed')


def rebuild_index(project_id, memories):
    """Rebuild the entire vector index for a project from memory records.

    Uses delete-then-add strategy. Caller should mark memories as pending
    BEFORE calling this, and only mark indexed AFTER a successful return
    with count > 0.

    Args:
        project_id: Project ID.
        memories: List of NovelMemory objects.

    Returns:
        Number of indexed chunks, or 0 if vector store unavailable.
    """
    store = get_vector_store(project_id)
    if store is None:
        return 0

    # Clear existing collection
    _clear_collection(store)

    from server.services.memory.chunker import chunk_text

    texts = []
    metadatas = []
    for mem in memories:
        chunks = chunk_text(mem.content)
        for i, chunk in enumerate(chunks):
            texts.append(chunk)
            metadatas.append({
                'memory_id': str(mem.id),
                'memory_type': mem.memory_type,
                'source_type': mem.source_type,
                'source_id': str(mem.source_id) if mem.source_id else '',
                'importance': mem.importance,
                'chunk_index': i,
            })

    if texts:
        store.add_texts(texts=texts, metadatas=metadatas)

    return len(texts)


def reset_stores():
    """Reset cached stores (for testing)."""
    global _stores
    _stores = {}


def reset_vector_stores():
    """Clear all cached vector store instances.

    Called after embedding key or persist dir changes so the next
    get_vector_store() recreates stores with updated config.
    """
    global _stores
    with _stores_lock:
        count = len(_stores)
        _stores = {}
    if count:
        logger.info('Vector store cache cleared (%d entries)', count)
