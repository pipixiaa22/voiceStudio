"""Multi-retrieval with ranking and compression for RAG memory."""

from server.services.memory.vector_store import search


# Budget allocation for memory types (relative weights)
MEMORY_TYPE_WEIGHTS = {
    'character': 1.0,
    'world_rule': 0.9,
    'event': 0.8,
    'relationship': 0.8,
    'foreshadowing': 0.7,
    'style': 0.5,
    'summary': 0.6,
}


def retrieve_memories(project_id, query, chapter_context=None, k=10):
    """Retrieve relevant memories for chapter generation.

    Args:
        project_id: Project ID.
        query: Search query (chapter outline + user instruction).
        chapter_context: Optional dict with current chapter info for filtering.
        k: Number of results to retrieve.

    Returns:
        List of memory dicts sorted by relevance, with 'content' and 'metadata'.
    """
    if not query or not query.strip():
        return []

    results = search(project_id, query, k=k)
    if not results:
        return []

    memories = []
    for doc, score in results:
        meta = doc.metadata or {}
        importance = meta.get('importance', 3)
        # Combine vector similarity score with importance
        combined_score = (1 - score) * 0.7 + (importance / 5) * 0.3

        memories.append({
            'content': doc.page_content,
            'memory_type': meta.get('memory_type', ''),
            'memory_id': meta.get('memory_id', ''),
            'importance': importance,
            'score': combined_score,
            'vector_score': 1 - score,
        })

    # Sort by combined score descending
    memories.sort(key=lambda m: m['score'], reverse=True)
    return memories


def retrieve_by_type(project_id, memory_type, query, k=5):
    """Retrieve memories filtered by type.

    Args:
        project_id: Project ID.
        memory_type: Filter to this memory type.
        query: Search query.
        k: Number of results.

    Returns:
        List of memory dicts.
    """
    results = search(project_id, query, k=k, filter_dict={'memory_type': memory_type})
    if not results:
        return []

    memories = []
    for doc, score in results:
        meta = doc.metadata or {}
        memories.append({
            'content': doc.page_content,
            'memory_type': memory_type,
            'memory_id': meta.get('memory_id', ''),
            'importance': meta.get('importance', 3),
            'score': 1 - score,
        })

    memories.sort(key=lambda m: m['score'], reverse=True)
    return memories


def format_memories_for_prompt(memories, max_chars=3000):
    """Format retrieved memories into a prompt section.

    Args:
        memories: List of memory dicts from retrieve_memories().
        max_chars: Maximum character budget for the memories section.

    Returns:
        Formatted string for prompt injection.
    """
    if not memories:
        return ''

    parts = []
    total = 0
    for mem in memories:
        text = mem['content']
        if total + len(text) > max_chars:
            remaining = max_chars - total
            if remaining > 50:
                text = text[:remaining] + '...'
            else:
                break
        parts.append(text)
        total += len(text)

    return '\n\n'.join(parts)
