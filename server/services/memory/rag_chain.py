"""LangChain RAG orchestration: retrieval -> prompt -> LLM -> output."""

from server.services.memory.retriever import retrieve_memories, format_memories_for_prompt
from server.services.memory.utils import parse_memory_json


def generate_with_memory(project, chapter, context, system_prompt, user_instruction='',
                         model_key=None, model_config=None, version_type='custom',
                         structured_output=False):
    """Generate chapter content with RAG memory augmentation.

    Args:
        project: NovelProject instance.
        chapter: NovelChapter instance.
        context: Context dict from context_builder.build_context().
        system_prompt: System prompt from prompt_templates.
        user_instruction: User's generation instruction.
        model_key: Optional model override.
        model_config: Optional provider config from the frontend.
        version_type: Version type for generation.

    Returns:
        Generated content string.
    """
    # Build retrieval query from context
    query_parts = []
    if context.get('overall_outline'):
        query_parts.append(context['overall_outline'])
    if context.get('volume_outline'):
        query_parts.append(context['volume_outline'])
    if context.get('outline'):
        query_parts.append(context['outline'])
    if context.get('continuation_brief'):
        query_parts.append(context['continuation_brief'])
    if user_instruction:
        query_parts.append(user_instruction)
    if context.get('characters'):
        query_parts.append(context['characters'][:500])
    query = ' '.join(query_parts) if query_parts else ''

    # Retrieve relevant memories
    memory_text = ''
    if query:
        memories = retrieve_memories(project.id, query, k=10)
        memory_text = format_memories_for_prompt(memories, max_chars=3000)

    # Check for conflicts (best effort)
    conflicts = []
    if memory_text and context.get('outline'):
        try:
            from server.services.memory.conflict_detector import detect_conflicts
            conflicts = detect_conflicts(project.id, context['outline'], memories)
        except Exception:
            pass

    # Build enhanced user prompt with memory section
    prompt_sections = []
    # Add conflict warnings to prompt if found
    if conflicts:
        conflict_text = '\n'.join(
            f'- [{c.get("severity", "medium")}] {c["description"]}'
            for c in conflicts
        )
        prompt_sections.append(f'【设定冲突警告】\n{conflict_text}\n请在生成时避免加剧这些冲突。')
    if context.get('overall_outline'):
        prompt_sections.append(f'【总大纲：全书走向】\n{context["overall_outline"]}')
    if context.get('volume_outline'):
        prompt_sections.append(f'【卷大纲：阶段方向】\n{context["volume_outline"]}')
    if context.get('outline'):
        prompt_sections.append(f'【章大纲：本章情节】\n{context["outline"]}')
    if context.get('continuation_brief'):
        prompt_sections.append(f'【续写简报】\n{context["continuation_brief"]}')
    if context.get('previous_summaries'):
        prompt_sections.append(f'【前文摘要】\n{context["previous_summaries"]}')
    if context.get('text_tail'):
        prompt_sections.append(f'【前文末尾】\n{context["text_tail"]}')
    if memory_text:
        prompt_sections.append(f'【长期记忆】\n{memory_text}')
    if context.get('characters'):
        prompt_sections.append(f'【人物设定】\n{context["characters"]}')
    if context.get('events'):
        prompt_sections.append(f'【事件时间线】\n{context["events"]}')
    if context.get('world_building'):
        prompt_sections.append(f'【世界观】\n{context["world_building"]}')
    if context.get('foreshadowing'):
        prompt_sections.append(f'【伏笔】\n{context["foreshadowing"]}')
    if user_instruction:
        prompt_sections.append(f'【用户指令】\n{user_instruction}')

    target_words = context.get('target_words', 3000)
    if structured_output:
        prompt_sections.append(_build_structured_output_instruction(target_words))
    else:
        prompt_sections.append(
            f'【输出要求】\n'
            f'- 只输出正文 Markdown。\n'
            f'- 不要解释。\n'
            f'- 目标字数：{target_words}字。\n'
            f'- 紧接前文自然续写，不用摘要式开场。\n'
            f'- 每一场都要推进人物目标、冲突或信息揭示，避免原地水文。\n'
            f'- 新增设定、能力、关系和时间线必须服从长期记忆与已有人物事件。'
        )

    user_prompt = '\n\n'.join(prompt_sections)

    # Get LLM provider
    from server.services.novel import get_llm_provider
    provider, default_model = get_llm_provider(model_config)

    # Call LLM
    messages = [{'role': 'user', 'content': user_prompt}]
    response = provider.complete(
        messages,
        model=model_key or default_model,
        system_prompt=system_prompt,
        max_tokens=8192,
        timeout=120,
    )

    if structured_output:
        return _parse_structured_generation(response)

    return response


def _build_structured_output_instruction(target_words):
    return f"""【输出要求】
- 必须只输出一个 JSON 对象，不要使用 Markdown 代码块，不要解释。
- 正文必须放在 content_markdown 字段，目标字数：{target_words}字。
- 正文要紧接前文自然续写，不用摘要式开场。
- 每一场都要推进人物目标、冲突或信息揭示，避免原地水文。
- 新增设定、能力、关系和时间线必须服从长期记忆与已有人物事件。
- 如果本次续写引入新人物、道具、地点、势力、事件、伏笔或世界规则，必须同时写入 knowledge_updates，不能只写进正文。
- 必须同时输出 chapter_state，记录本章的剧情推进状态。

JSON 结构：
{{
  "content_markdown": "小说正文 Markdown",
  "knowledge_updates": {{
    "graph_changes": [
      {{
        "change_type": "add|modify",
        "target_type": "entity|event",
        "after": {{
          "entity_type": "character|item|location|faction",
          "name": "实体名称",
          "summary": "简介",
          "importance": 1-10,
          "attributes": {{}}
        }},
        "confidence": 0.0-1.0,
        "description": "为什么需要写入图谱"
      }}
    ],
    "memory_changes": [
      {{
        "change_type": "add|modify",
        "after": {{
          "title": "记忆标题",
          "content": "需要长期记住的事实、伏笔、道具能力、人物目标或世界规则",
          "memory_type": "character|world_rule|event|foreshadowing|relationship|style|summary",
          "importance": 1-5,
          "summary": "一句话摘要"
        }},
        "description": "为什么需要写入长期记忆"
      }}
    ]
  }},
  "chapter_state": {{
    "completed_plot_goals": ["本章完成的剧情目标，对照章大纲的 plot_goal 和 conflict_goal"],
    "open_threads": ["本章未解决的悬念或未完成的目标"],
    "new_questions": ["本章新提出的问题或谜团"],
    "next_chapter_hooks": ["为下一章铺设的钩子或悬念"]
  }}
}}"""


def _parse_structured_generation(text):
    data = parse_memory_json(text)
    if not isinstance(data, dict):
        raise ValueError('无法解析小说续写结构化 JSON 输出')

    content = data.get('content_markdown') or data.get('content') or ''
    if not isinstance(content, str) or not content.strip():
        raise ValueError('小说续写结构化输出缺少 content_markdown')

    updates = data.get('knowledge_updates') or {}
    if not isinstance(updates, dict):
        updates = {}

    graph_changes = updates.get('graph_changes') or []
    memory_changes = updates.get('memory_changes') or []
    if not isinstance(graph_changes, list):
        graph_changes = []
    if not isinstance(memory_changes, list):
        memory_changes = []

    # chapter_state is optional for backward compatibility
    chapter_state = data.get('chapter_state')
    if chapter_state and not isinstance(chapter_state, dict):
        chapter_state = None

    result = {
        'content_markdown': content.strip(),
        'knowledge_updates': {
            'graph_changes': graph_changes,
            'memory_changes': memory_changes,
        },
    }
    if chapter_state:
        result['chapter_state'] = chapter_state

    return result
