"""LangChain RAG orchestration: retrieval -> prompt -> LLM -> output."""

from server.services.memory.retriever import retrieve_memories, format_memories_for_prompt


def generate_with_memory(project, chapter, context, system_prompt, user_instruction='',
                         model_key=None, version_type='custom'):
    """Generate chapter content with RAG memory augmentation.

    Args:
        project: NovelProject instance.
        chapter: NovelChapter instance.
        context: Context dict from context_builder.build_context().
        system_prompt: System prompt from prompt_templates.
        user_instruction: User's generation instruction.
        model_key: Optional model override.
        version_type: Version type for generation.

    Returns:
        Generated content string.
    """
    # Build retrieval query from context
    query_parts = []
    if context.get('outline'):
        query_parts.append(context['outline'])
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

    # Build enhanced user prompt with memory section
    prompt_sections = []
    if context.get('outline'):
        prompt_sections.append(f'【大纲】\n{context["outline"]}')
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
    prompt_sections.append(f'【输出要求】\n- 只输出正文 Markdown。\n- 不要解释。\n- 目标字数：{target_words}字')

    user_prompt = '\n\n'.join(prompt_sections)

    # Get LLM provider
    from server.services.novel import get_llm_provider
    provider, default_model = get_llm_provider()

    # Call LLM
    messages = [{'role': 'user', 'content': user_prompt}]
    content = provider.complete(
        messages,
        model=model_key or default_model,
        system_prompt=system_prompt,
        max_tokens=8192,
        timeout=120,
    )

    return content
