# server/services/novel/blueprint_generator.py
import json
from server.models import db
from server.models.novel.project import NovelProject
from server.models.novel.outline import NovelOutlineNode
from server.models.novel.entity import NovelEntity, NovelRelation


def generate_blueprint(project_id, params):
    """Generate a full novel blueprint from premise."""
    project = NovelProject.query.get_or_404(project_id)

    premise = params.get('premise', project.premise or '')
    if not premise:
        raise ValueError('请提供小说创意')

    # Build prompt
    system_prompt = f"""你是一位资深小说策划师，擅长根据一句话创意扩展成完整的小说蓝图。
请根据以下信息生成完整的小说蓝图：

类型：{project.genre}
目标字数：{project.target_total_words}
目标章节数：{project.target_chapters}
每章字数：{project.words_per_chapter}
卷数：{project.volume_count}

请以 JSON 格式输出，包含以下字段：
{{
  "title": "小说标题",
  "premise": "一句话简介",
  "main_character": {{
    "name": "主角名",
    "summary": "主角简介",
    "attributes": {{}}
  }},
  "characters": [
    {{
      "name": "角色名",
      "entity_type": "character",
      "summary": "角色简介",
      "importance": 1-10
    }}
  ],
  "world_settings": {{}},
  "volumes": [
    {{
      "title": "卷标题",
      "summary": "卷简介",
      "chapters": [
        {{
          "title": "章节标题",
          "summary": "章节摘要",
          "plot_goal": "剧情目标",
          "conflict_goal": "冲突目标",
          "target_words": 3000
        }}
      ]
    }}
  ],
  "main_conflict": "主线冲突描述",
  "key_events": ["事件1", "事件2"]
}}"""

    from server.services.novel import get_llm_provider
    provider, default_model = get_llm_provider()

    messages = [{'role': 'user', 'content': f'一句话创意：{premise}'}]
    response = provider.complete(
        messages,
        model=default_model,
        system_prompt=system_prompt,
        max_tokens=8192,
        timeout=120,
    )

    # Parse response
    result = _parse_json_response(response)

    # Update project
    if result.get('title'):
        project.title = result['title']
    if result.get('premise'):
        project.premise = result['premise']
    if result.get('world_settings'):
        project.settings = result['world_settings']
    project.status = 'active'

    # Create main character
    main_char = result.get('main_character', {})
    if main_char.get('name'):
        entity = NovelEntity(
            project_id=project_id,
            entity_type='character',
            name=main_char['name'],
            summary=main_char.get('summary'),
            importance=10,
        )
        if main_char.get('attributes'):
            entity.attributes = main_char['attributes']
        db.session.add(entity)
        db.session.flush()

    # Create other characters
    char_entities = {}
    for char in result.get('characters', []):
        if not char.get('name'):
            continue
        entity = NovelEntity(
            project_id=project_id,
            entity_type=char.get('entity_type', 'character'),
            name=char['name'],
            summary=char.get('summary'),
            importance=char.get('importance', 5),
        )
        db.session.add(entity)
        db.session.flush()
        char_entities[char['name']] = entity

    # Create outline tree
    chapter_order = 0
    for vol_idx, volume in enumerate(result.get('volumes', []), 1):
        vol_node = NovelOutlineNode(
            project_id=project_id,
            node_type='volume',
            title=volume.get('title', f'第{vol_idx}卷'),
            summary=volume.get('summary'),
            order_index=vol_idx,
        )
        db.session.add(vol_node)
        db.session.flush()

        for ch_idx, chapter in enumerate(volume.get('chapters', []), 1):
            chapter_order += 1
            ch_node = NovelOutlineNode(
                project_id=project_id,
                parent_id=vol_node.id,
                node_type='chapter',
                title=chapter.get('title', f'第{chapter_order}章'),
                summary=chapter.get('summary'),
                order_index=ch_idx,
                target_words=chapter.get('target_words', project.words_per_chapter),
                plot_goal=chapter.get('plot_goal'),
                conflict_goal=chapter.get('conflict_goal'),
            )
            db.session.add(ch_node)

    db.session.commit()

    return {
        'project_id': project_id,
        'title': project.title,
        'characters_created': len(char_entities) + (1 if main_char.get('name') else 0),
        'volumes_created': len(result.get('volumes', [])),
        'chapters_created': chapter_order,
    }


def _parse_json_response(text):
    """Extract JSON from LLM response."""
    # Try to find JSON block
    import re
    json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if json_match:
        return json.loads(json_match.group(1))

    # Try the whole text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find first { and last }
    start = text.find('{')
    end = text.rfind('}')
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError('无法解析 AI 返回的 JSON')
