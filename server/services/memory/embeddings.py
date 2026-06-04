"""Embedding model wrapper for memory indexing and retrieval.

Supports three providers (checked in order):
1. DASHSCOPE_API_KEY — Qwen text-embedding-v3 via DashScope OpenAI-compatible API
2. OPENAI_API_KEY — OpenAI embeddings
3. DEEPSEEK_API_KEY — DeepSeek embeddings (fallback)
"""

import os
import logging
import threading

logger = logging.getLogger(__name__)

_embeddings = None
_embeddings_lock = threading.Lock()


def get_embeddings():
    """Get or create the embedding model instance.

    Uses OpenAI-compatible embedding API. Checks for API key in order:
    1. DASHSCOPE_API_KEY (for Qwen embeddings via DashScope)
    2. OPENAI_API_KEY (for OpenAI embeddings)
    3. DEEPSEEK_API_KEY (for DeepSeek embeddings, if supported)

    Thread-safe: uses a lock to prevent duplicate instance creation.
    """
    global _embeddings
    if _embeddings is not None:
        return _embeddings

    with _embeddings_lock:
        if _embeddings is not None:
            return _embeddings

        from langchain_openai import OpenAIEmbeddings

        dashscope_key = os.environ.get('DASHSCOPE_API_KEY')
        openai_key = os.environ.get('OPENAI_API_KEY')
        deepseek_key = os.environ.get('DEEPSEEK_API_KEY')

        api_key = None
        base_url = None
        model = None

        if dashscope_key:
            api_key = dashscope_key
            base_url = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
            model = 'text-embedding-v3'
            logger.info('Using Qwen embeddings via DashScope (text-embedding-v3)')
        elif openai_key:
            api_key = openai_key
            logger.info('Using OpenAI embeddings')
        elif deepseek_key:
            api_key = deepseek_key
            base_url = 'https://api.deepseek.com/v1'
            logger.info('Using DeepSeek embeddings')

        if not api_key:
            logger.warning('No embedding API key found (DASHSCOPE_API_KEY, OPENAI_API_KEY, or DEEPSEEK_API_KEY). Memory indexing will not work.')
            return None

        kwargs = {'api_key': api_key}
        if base_url:
            kwargs['base_url'] = base_url
        if model:
            kwargs['model'] = model

        _embeddings = OpenAIEmbeddings(**kwargs)
        return _embeddings


def reset_embeddings():
    """Reset the cached embedding instance (for testing)."""
    global _embeddings
    with _embeddings_lock:
        _embeddings = None
