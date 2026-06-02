"""Chroma vector store wrapper with project-level isolation."""

import os
import logging

logger = logging.getLogger(__name__)

_stores = {}


def get_vector_store(project_id):
    """Get or create a Chroma vector store for a project.

    Each project gets its own collection to prevent cross-project contamination.
    """
    project_id = str(project_id)
    if project_id in _stores:
        return _stores[project_id]

    from server.services.memory.embeddings import get_embeddings
    embeddings = get_embeddings()
    if embeddings is None:
        return None

    persist_dir = os.path.join(os.getcwd(), 'data', 'chromadb')
    os.makedirs(persist_dir, exist_ok=True)

    from langchain_community.vectorstores import Chroma
    store = Chroma(
        collection_name=f'novel_{project_id}',
        embedding_function=embeddings,
        persist_directory=persist_dir,
    )
    _stores[project_id] = store
    return store


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


def rebuild_index(project_id, memories):
    """Rebuild the entire vector index for a project from memory records.

    Args:
        project_id: Project ID.
        memories: List of NovelMemory objects.

    Returns:
        Number of indexed chunks.
    """
    store = get_vector_store(project_id)
    if store is None:
        return 0

    # Clear existing collection
    try:
        store._collection.delete(where={})
    except Exception:
        pass

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
