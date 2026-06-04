"""Runtime config hot-reload management.

Classifies config keys by reload strategy and executes the appropriate
hooks after a config save, returning per-key effect results for the frontend.
"""

import logging

logger = logging.getLogger(__name__)

# Keys that only affect os.environ; no cached objects to reset.
HOT_ENV_KEYS = {
    'REDIS_KEY_PREFIX',
}

# Keys that require resetting cached runtime clients.
RELOADABLE_KEYS = {
    'REDIS_URL',
    'CHROMADB_PERSIST_DIR',
    'OPENAI_API_KEY',
    'DEEPSEEK_API_KEY',
    'DASHSCOPE_API_KEY',
}

# Keys that cannot be hot-reloaded safely.
RESTART_REQUIRED_KEYS = {
    'DATABASE_URL',
}


def apply_runtime_updates(updates):
    """Apply hot-reload hooks for the given config updates.

    Args:
        updates: dict of {key: new_value} that were just written to .env.

    Returns:
        List of dicts: [{key, status, message}, ...]
        status is one of: 'hot_applied', 'reloaded', 'restart_required'.
    """
    results = []
    handled_keys = set()

    # Redis URL: rebuild client
    if 'REDIS_URL' in updates:
        from server.services.redis_client import reset_redis_client
        reset_redis_client()
        results.append({
            'key': 'REDIS_URL',
            'status': 'reloaded',
            'message': 'Redis 连接已重建',
        })
        handled_keys.add('REDIS_URL')

    # Embedding keys: reset embeddings + vector stores
    embedding_keys = {'OPENAI_API_KEY', 'DEEPSEEK_API_KEY', 'DASHSCOPE_API_KEY'}
    if embedding_keys & updates.keys():
        from server.services.memory.embeddings import reset_embeddings
        from server.services.memory.vector_store import reset_vector_stores
        reset_embeddings()
        reset_vector_stores()
        changed = sorted(embedding_keys & updates.keys())
        results.append({
            'key': 'EMBEDDINGS',
            'status': 'reloaded',
            'message': f'Embedding 客户端已重建（{", ".join(changed)}）',
        })
        handled_keys |= embedding_keys & updates.keys()

    # ChromaDB persist dir: clear vector stores
    if 'CHROMADB_PERSIST_DIR' in updates:
        from server.services.memory.vector_store import reset_vector_stores
        reset_vector_stores()
        results.append({
            'key': 'CHROMADB_PERSIST_DIR',
            'status': 'reloaded',
            'message': '向量库缓存已清空，下次访问使用新目录',
        })
        handled_keys.add('CHROMADB_PERSIST_DIR')

    # Database URL: cannot hot-reload
    if 'DATABASE_URL' in updates:
        results.append({
            'key': 'DATABASE_URL',
            'status': 'restart_required',
            'message': '数据库连接已保存，需重启后切换当前运行数据库',
        })
        handled_keys.add('DATABASE_URL')

    # Remaining hot env keys
    for key in HOT_ENV_KEYS & updates.keys():
        if key not in handled_keys:
            results.append({
                'key': key,
                'status': 'hot_applied',
                'message': '已更新当前进程环境变量',
            })
            handled_keys.add(key)

    # Any other keys not yet handled
    for key in updates:
        if key not in handled_keys:
            results.append({
                'key': key,
                'status': 'hot_applied',
                'message': '已保存',
            })

    return results
