GENRE_TEMPLATES = {
    '玄幻': {
        'system': '你是一位资深玄幻小说作家，擅长修炼体系设计、战斗描写、升级打怪的节奏把控。',
        'chapter_prompt': '请根据以下大纲和上下文，生成本章内容。注意：修炼体系要合理，战斗描写要有画面感，节奏要有爽点。',
        'review_criteria': '修炼体系是否一致，境界差距是否合理，战斗描写是否有画面感，是否有爽点。',
    },
    '仙侠': {
        'system': '你是一位资深仙侠小说作家，擅长仙侠世界观、门派势力、法宝道具的描写。',
        'chapter_prompt': '请根据以下大纲和上下文，生成本章内容。注意：仙侠氛围要到位，门派关系要清晰，意境描写要优美。',
        'review_criteria': '仙侠氛围是否到位，门派关系是否清晰，法宝设定是否一致，意境描写是否优美。',
    },
    '都市': {
        'system': '你是一位资深都市小说作家，擅长都市生活、职场商战、人际关系的描写。',
        'chapter_prompt': '请根据以下大纲和上下文，生成本章内容。注意：都市感要强，对话要自然，情节要有代入感。',
        'review_criteria': '都市感是否强，对话是否自然，社会关系是否合理，情节是否有代入感。',
    },
    '悬疑': {
        'system': '你是一位资深悬疑小说作家，擅长线索铺设、误导设计、真相揭示的把控。',
        'chapter_prompt': '请根据以下大纲和上下文，生成本章内容。注意：悬念要到位，线索要埋好，节奏要紧张。',
        'review_criteria': '悬念是否到位，线索是否合理，误导是否有效，真相揭示是否有冲击力。',
    },
    '言情': {
        'system': '你是一位资深言情小说作家，擅长感情描写、人物心理、情感冲突的刻画。',
        'chapter_prompt': '请根据以下大纲和上下文，生成本章内容。注意：感情戏要细腻，心理描写要深入，情感冲突要真实。',
        'review_criteria': '感情戏是否细腻，心理描写是否深入，情感冲突是否真实，人物关系发展是否自然。',
    },
    '科幻': {
        'system': '你是一位资深科幻小说作家，擅长科幻设定、科技描写、世界观构建。',
        'chapter_prompt': '请根据以下大纲和上下文，生成本章内容。注意：科幻设定要自洽，科技描写要有想象力，世界观要宏大。',
        'review_criteria': '科幻设定是否自洽，科技描写是否有想象力，世界观是否宏大，逻辑是否严密。',
    },
    '历史': {
        'system': '你是一位资深历史小说作家，擅长历史背景、人物刻画、事件还原的描写。',
        'chapter_prompt': '请根据以下大纲和上下文，生成本章内容。注意：历史感要强，人物要立体，事件要有据可循。',
        'review_criteria': '历史感是否强，人物是否立体，事件是否合理，时代氛围是否到位。',
    },
    '末世': {
        'system': '你是一位资深末世小说作家，擅长末世生存、资源争夺、人性考验的描写。',
        'chapter_prompt': '请根据以下大纲和上下文，生成本章内容。注意：末世感要强，生存压力要真实，人性冲突要深刻。',
        'review_criteria': '末世感是否强，生存压力是否真实，人性冲突是否深刻，资源设定是否合理。',
    },
    '轻小说': {
        'system': '你是一位资深轻小说作家，擅长轻松幽默、角色互动、日常与冒险的平衡。',
        'chapter_prompt': '请根据以下大纲和上下文，生成本章内容。注意：文风要轻松，对话要有趣，角色要有萌点。',
        'review_criteria': '文风是否轻松，对话是否有趣，角色是否有萌点，节奏是否明快。',
    },
}

VERSION_TYPE_MODIFIERS = {
    'steady': '请稳健推进剧情，保持节奏平稳，注重逻辑连贯性。',
    'conflict': '请最大化冲突和张力，让人物面对更激烈的矛盾。',
    'climax': '请写出爽点爆发的感觉，让读者感到痛快淋漓。',
    'suspense': '请增加悬疑感和反转，让读者意想不到。',
    'romance': '请加强感情戏的描写，让人物之间的情感更细腻动人。',
    'polish': '请精修文笔，提升文字质量和文学性。',
}


def get_genre_template(genre):
    return GENRE_TEMPLATES.get(genre, GENRE_TEMPLATES['玄幻'])


def get_version_modifier(version_type):
    return VERSION_TYPE_MODIFIERS.get(version_type, '')


def build_chapter_system_prompt(genre, version_type=None, style_guide=None):
    template = get_genre_template(genre)
    parts = [template['system']]

    if version_type:
        modifier = get_version_modifier(version_type)
        if modifier:
            parts.append(modifier)

    if style_guide:
        if style_guide.get('pov'):
            parts.append(f'叙事视角：{style_guide["pov"]}')
        if style_guide.get('tone'):
            tone = style_guide['tone']
            if isinstance(tone, list):
                tone = '、'.join(tone)
            parts.append(f'文风基调：{tone}')
        if style_guide.get('taboos'):
            taboos = style_guide['taboos']
            if isinstance(taboos, list):
                taboos = '；'.join(taboos)
            parts.append(f'禁忌：{taboos}')

    return '\n'.join(parts)


def build_chapter_user_prompt(context):
    parts = []

    if context.get('outline'):
        parts.append(f'【本章大纲】\n{context["outline"]}')

    if context.get('previous_summaries'):
        parts.append(f'【前文摘要】\n{context["previous_summaries"]}')

    if context.get('text_tail'):
        parts.append(f'【上一章结尾】\n{context["text_tail"]}')

    if context.get('characters'):
        parts.append(f'【相关人物】\n{context["characters"]}')

    if context.get('events'):
        parts.append(f'【相关事件】\n{context["events"]}')

    if context.get('world_building'):
        parts.append(f'【世界观设定】\n{context["world_building"]}')

    if context.get('foreshadowing'):
        parts.append(f'【未回收伏笔】\n{context["foreshadowing"]}')

    parts.append(f'目标字数：{context.get("target_words", 3000)} 字')
    parts.append('请直接输出正文 Markdown，不要输出其他内容。')

    return '\n\n'.join(parts)


def build_extract_prompt(chapter_content):
    return f"""请从以下章节正文中提取知识图谱变更候选。

要求提取：
1. 新出现的人物（姓名、类型、简介）
2. 新出现的关系（谁和谁、关系类型、描述）
3. 新发生的事件（标题、摘要、类型、参与者）
4. 新的因果关系（哪个事件导致了哪个事件）
5. 人物状态变化（所在地、阵营、目标、情绪变化）
6. 关系变化（关系类型或状态变化）

请以 JSON 格式输出，结构如下：
{{
  "changes": [
    {{
      "change_type": "add|modify",
      "target_type": "entity|relation|event|event_relation",
      "after": {{ ... }},
      "confidence": 0.0-1.0,
      "description": "变更描述"
    }}
  ]
}}

【章节正文】
{chapter_content}"""


def build_review_prompt(chapter_content, context):
    parts = ['请对以下章节进行一致性审稿。']

    if context.get('characters'):
        parts.append(f'【已有人物设定】\n{context["characters"]}')
    if context.get('world_rules'):
        parts.append(f'【世界观规则】\n{context["world_rules"]}')
    if context.get('previous_summaries'):
        parts.append(f'【前文摘要】\n{context["previous_summaries"]}')

    parts.append(f"""请检查以下方面：
1. 人设是否崩坏（性格、能力、行为是否与设定一致）
2. 世界观规则是否冲突
3. 时间线是否合理
4. 人物位置是否合理
5. 事件因果是否断裂
6. 伏笔是否遗忘
7. 本章是否推进了冲突
8. 是否与前文重复
9. 是否水文（无意义的填充内容）

请以 JSON 格式输出：
{{
  "issues": [
    {{
      "severity": "high|medium|low",
      "category": "character|world|timeline|location|causality|foreshadow|progression|redundancy|padding",
      "location": "问题位置描述",
      "description": "问题描述",
      "suggestion": "修复建议"
    }}
  ],
  "overall_score": 0-100,
  "summary": "总体评价"
}}

【章节正文】
{chapter_content}""")

    return '\n\n'.join(parts)
