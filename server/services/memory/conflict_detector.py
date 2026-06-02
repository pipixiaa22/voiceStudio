"""Detect conflicts between new chapter goals and existing memories."""

from server.services.memory.retriever import retrieve_memories


def detect_conflicts(project_id, chapter_goal, existing_memories=None):
    """Check if chapter goal conflicts with existing memories.

    Args:
        project_id: Project ID.
        chapter_goal: Text describing the chapter's plot/conflict goals.
        existing_memories: Optional pre-fetched memories. If None, will retrieve.

    Returns:
        List of conflict dicts with 'description', 'severity', 'memory_type'.
    """
    if not chapter_goal:
        return []

    if existing_memories is None:
        existing_memories = retrieve_memories(project_id, chapter_goal, k=10)

    if not existing_memories:
        return []

    from server.services.novel import get_llm_provider

    memory_text = '\n'.join(
        f'- [{m["memory_type"]}] {m["content"][:200]}'
        for m in existing_memories[:5]
    )

    prompt = f"""你是小说设定一致性检查助手。请检查以下章节目标是否与已有设定冲突。

【已有设定】
{memory_text}

【章节目标】
{chapter_goal}

请以 JSON 格式输出冲突列表：
{{
  "conflicts": [
    {{
      "description": "冲突描述",
      "severity": "high|medium|low",
      "memory_type": "冲突涉及的设定类型"
    }}
  ]
}}

如果没有冲突，输出 {{"conflicts": []}}。
只输出 JSON，不要解释。"""

    provider, default_model = get_llm_provider()
    messages = [{'role': 'user', 'content': prompt}]

    try:
        response = provider.complete(
            messages,
            model=default_model,
            system_prompt='你是设定一致性检查助手，只输出 JSON。',
            max_tokens=2048,
            timeout=30,
        )
    except Exception:
        return []

    from server.services.memory.memory_writer import _parse_memory_json
    result = _parse_memory_json(response)
    if not result:
        return []

    return result.get('conflicts', [])


def summarize_old_chapter(project_id, chapter_content, max_length=500):
    """Compress an old chapter's content into a summary for memory.

    Args:
        project_id: Project ID.
        chapter_content: Full chapter content.
        max_length: Target summary length.

    Returns:
        Summary string.
    """
    if not chapter_content or len(chapter_content) <= max_length:
        return chapter_content

    from server.services.novel import get_llm_provider

    prompt = f"""请将以下章节内容压缩为 {max_length} 字以内的摘要，保留关键剧情、人物行为、设定变更和伏笔。

【章节内容】
{chapter_content[:6000]}

只输出摘要，不要解释。"""

    provider, default_model = get_llm_provider()
    messages = [{'role': 'user', 'content': prompt}]

    try:
        return provider.complete(
            messages,
            model=default_model,
            system_prompt='你是小说摘要助手。',
            max_tokens=2048,
            timeout=30,
        )
    except Exception:
        return chapter_content[:max_length]
