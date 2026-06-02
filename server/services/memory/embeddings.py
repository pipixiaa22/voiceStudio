"""Embedding model wrapper for memory indexing and retrieval."""

import os
import logging

logger = logging.getLogger(__name__)

_embeddings = None


def get_embeddings():
    """Get or create the embedding model instance.

    Uses OpenAI-compatible embedding API. Checks for API key in order:
    1. OPENAI_API_KEY (for OpenAI embeddings)
    2. DEEPSEEK_API_KEY (for DeepSeek embeddings, if supported)
    """
    global _embeddings
    if _embeddings is not None:
        return _embeddings

    from langchain_openai import OpenAIEmbeddings

    api_key = os.environ.get('OPENAI_API_KEY') or os.environ.get('DEEPSEEK_API_KEY')
    base_url = None

    if os.environ.get('DEEPSEEK_API_KEY') and not os.environ.get('OPENAI_API_KEY'):
        base_url = 'https://api.deepseek.com/v1'

    if not api_key:
        logger.warning('No embedding API key found. Memory indexing will not work.')
        return None

    _embeddings = OpenAIEmbeddings(
        api_key=api_key,
        base_url=base_url,
    )
    return _embeddings


def reset_embeddings():
    """Reset the cached embedding instance (for testing)."""
    global _embeddings
    _embeddings = None
