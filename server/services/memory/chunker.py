"""Text chunking for long-term memory indexing."""


def chunk_text(text, max_chunk_size=500, overlap=50):
    """Split text into chunks for embedding.

    Args:
        text: Input text to chunk.
        max_chunk_size: Maximum characters per chunk.
        overlap: Character overlap between consecutive chunks.

    Returns:
        List of text chunks.
    """
    if not text:
        return []
    if len(text) <= max_chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chunk_size
        chunk = text[start:end]

        # Try to break at sentence boundary
        if end < len(text):
            last_period = chunk.rfind('。')
            last_question = chunk.rfind('？')
            last_exclaim = chunk.rfind('！')
            break_point = max(last_period, last_question, last_exclaim)
            if break_point > max_chunk_size // 2:
                chunk = chunk[:break_point + 1]
                end = start + break_point + 1

        chunks.append(chunk.strip())
        start = end - overlap

    return [c for c in chunks if c]
