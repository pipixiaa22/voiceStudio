# server/services/novel/blueprint_generator.py
import json
import requests
from server.models import db
from server.models.novel.project import NovelProject
from server.models.novel.outline import NovelOutlineNode
from server.models.novel.entity import NovelEntity, NovelRelation
from server.models.novel.event import NovelEvent
from server.models.novel.memory import NovelMemory


def generate_blueprint(project_id, params):
    """Generate a full novel blueprint from premise."""
    project = NovelProject.query.get_or_404(project_id)

    premise = params.get('premise', project.premise or '')
    if not premise:
        raise ValueError('请提供小说创意')

    outline_chapters = _resolve_outline_chapter_count(project, params)
    depth = params.get('depth', 'standard')

    # Build prompt
    depth_requirements = {
        'quick': '- 主要角色 2-4 个，道具/地点/势力 2-4 个。\n- 只生成 1 卷。\n- 关键事件 2-3 个，伏笔 1-2 个。',
        'standard': f'- 主要角色 4-8 个，道具/地点/势力 4-10 个。\n- 必须有关键事件、伏笔、道具或地点，不能只输出章节标题。\n- 如果整体故事超过 {outline_chapters} 章，也要给出全书主线骨架、关键事件和伏笔清单；章节只展开前 {outline_chapters} 章。',
        'deep': f'- 主要角色 6-10 个，道具/地点/势力 6-12 个。\n- 必须有关键事件 5-8 个、伏笔 3-5 个、道具/地点/势力详细描述。\n- 尽可能覆盖全书卷纲，每卷都要有详细的 plot_goal、conflict_goal、characters、events、foreshadowing。\n- memory_seeds 必须包含详细的世界规则、人物背景、道具能力、伏笔线索。\n- 全部 volumes 下的 chapters 总数必须等于 {outline_chapters}。',
    }
    depth_req = depth_requirements.get(depth, depth_requirements['standard'])

    system_prompt = f"""你是一位资深小说策划师，擅长根据一句话创意扩展成完整的小说蓝图。
请根据以下信息生成完整的小说蓝图：

类型：{project.genre}
目标字数：{project.target_total_words}
目标章节数：{project.target_chapters}
每章字数：{project.words_per_chapter}
卷数：{project.volume_count}
本次必须生成前 {outline_chapters} 个章节节点，不能只生成一章，也不要输出超过 {outline_chapters} 个章节。

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
  "entities": [
    {{
      "name": "道具/地点/势力名",
      "entity_type": "item|location|faction",
      "summary": "简介",
      "importance": 1-10,
      "attributes": {{}}
    }}
  ],
  "relations": [
    {{
      "source": "角色或实体名",
      "target": "角色或实体名",
      "relation_type": "ally|enemy|mentor|belongs_to|owns|knows|conflict",
      "label": "关系标签",
      "description": "关系说明",
      "strength": 0.0-1.0
    }}
  ],
  "world_settings": {{
    "rules": ["世界规则"],
    "power_system": "能力/修炼/科技体系",
    "locations": ["关键地点"],
    "taboos": ["不可违背的设定"],
    "overall_outline": {{
      "ending_direction": "结局方向",
      "main_arc": "全书主线推进路径",
      "stage_goals": ["开篇阶段", "中段阶段", "高潮阶段"],
      "theme": "主题表达"
    }}
  }},
  "volumes": [
    {{
      "title": "卷标题",
      "summary": "卷大纲：本卷承担的阶段目标、主要冲突、关键反转和收束点",
      "plot_goal": "本卷剧情目标",
      "conflict_goal": "本卷核心冲突",
      "characters": ["本卷核心人物"],
      "events": ["本卷关键事件"],
      "foreshadowing": ["本卷铺设或回收的伏笔"],
      "chapters": [
        {{
          "title": "章节标题",
          "summary": "章节摘要",
          "plot_goal": "剧情目标",
          "conflict_goal": "冲突目标",
          "characters": ["本章登场人物"],
          "events": ["本章关键事件"],
          "foreshadowing": ["本章铺设或回应的伏笔"],
          "target_words": 3000
        }}
      ]
    }}
  ],
  "main_conflict": "主线冲突描述",
  "key_events": [
    {{
      "title": "事件标题",
      "summary": "事件摘要",
      "event_type": "inciting|turning_point|reveal|climax|setup",
      "timeline_order": 1,
      "participants": ["参与者"]
    }}
  ],
  "foreshadowing": [
    {{
      "title": "伏笔标题",
      "content": "伏笔内容、预计回收方向",
      "importance": 1-5
    }}
  ],
  "memory_seeds": [
    {{
      "title": "长期记忆标题",
      "content": "需要长期保存的人物、道具、世界规则、伏笔或风格事实",
      "memory_type": "character|world_rule|event|foreshadowing|relationship|style|summary",
      "importance": 1-5,
      "summary": "一句话摘要"
    }}
  ]
}}

要求：
- 严格输出 JSON，不要使用 Markdown 代码块。
{depth_req}
- 必须明确三层大纲：overall_outline 决定全书走向；volume summary/plot_goal/conflict_goal 决定本卷方向；chapter summary/plot_goal/conflict_goal 刻画具体情节。
- 全部 volumes 下的 chapters 总数必须等于 {outline_chapters}。"""

    from server.services.novel import get_llm_provider
    provider, default_model = get_llm_provider(params.get('model_config'))

    messages = [{'role': 'user', 'content': f'一句话创意：{premise}'}]
    try:
        response = provider.complete(
            messages,
            model=default_model,
            system_prompt=system_prompt,
            max_tokens=4096,
            timeout=60,
        )
    except requests.Timeout:
        response = json.dumps(_build_timeout_fallback_blueprint(project, premise, outline_chapters), ensure_ascii=False)

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
    char_entities = {}
    if main_char.get('name'):
        main_entity = NovelEntity(
            project_id=project_id,
            entity_type='character',
            name=main_char['name'],
            summary=main_char.get('summary'),
            importance=10,
        )
        if main_char.get('attributes'):
            main_entity.attributes = main_char['attributes']
        db.session.add(main_entity)
        db.session.flush()
        char_entities[main_char['name']] = main_entity

    # Create other characters
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

    # Create non-character entities such as items, locations, and factions
    entity_by_name = dict(char_entities)
    for item in result.get('entities', []):
        if not item.get('name'):
            continue
        entity = NovelEntity(
            project_id=project_id,
            entity_type=item.get('entity_type', 'item'),
            name=item['name'],
            summary=item.get('summary'),
            importance=item.get('importance', 5),
        )
        if item.get('attributes'):
            entity.attributes = item['attributes']
        db.session.add(entity)
        db.session.flush()
        entity_by_name[item['name']] = entity

    # Create named relations when both endpoints are known
    relations_created = 0
    for rel in result.get('relations', []):
        source = entity_by_name.get(rel.get('source'))
        target = entity_by_name.get(rel.get('target'))
        if not source or not target or source.id == target.id:
            continue
        relation = NovelRelation(
            project_id=project_id,
            source_entity_id=source.id,
            target_entity_id=target.id,
            relation_type=rel.get('relation_type', 'knows'),
            label=rel.get('label'),
            description=rel.get('description'),
            strength=rel.get('strength', 0.5),
        )
        db.session.add(relation)
        relations_created += 1

    # Create outline tree
    chapter_order = 0
    for vol_idx, volume in enumerate(result.get('volumes', []), 1):
        vol_node = NovelOutlineNode(
            project_id=project_id,
            node_type='volume',
            title=volume.get('title', f'第{vol_idx}卷'),
            summary=volume.get('summary'),
            order_index=vol_idx,
            plot_goal=volume.get('plot_goal'),
            conflict_goal=volume.get('conflict_goal'),
        )
        vol_node.characters = volume.get('characters', [])
        vol_node.events = volume.get('events', [])
        vol_node.foreshadowing = volume.get('foreshadowing', [])
        db.session.add(vol_node)
        db.session.flush()

        for ch_idx, chapter in enumerate(volume.get('chapters', []), 1):
            if chapter_order >= outline_chapters:
                break
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
            ch_node.characters = chapter.get('characters', [])
            ch_node.events = chapter.get('events', [])
            ch_node.foreshadowing = chapter.get('foreshadowing', [])
            db.session.add(ch_node)
        if chapter_order >= outline_chapters:
            break

    # Create event graph nodes
    events_created = 0
    for idx, event_data in enumerate(result.get('key_events', []), 1):
        if isinstance(event_data, str):
            event_data = {'title': event_data, 'summary': event_data}
        if not event_data.get('title'):
            continue
        event = NovelEvent(
            project_id=project_id,
            title=event_data['title'],
            summary=event_data.get('summary'),
            event_type=event_data.get('event_type', 'event'),
            timeline_order=event_data.get('timeline_order', idx),
        )
        event.participants = event_data.get('participants', [])
        db.session.add(event)
        events_created += 1

    # Seed long-term memories from blueprint facts
    memories_created = 0
    for memory_data in _build_blueprint_memory_seeds(project, result):
        memory = NovelMemory(
            project_id=project_id,
            source_type='project',
            memory_type=memory_data.get('memory_type', 'summary'),
            title=memory_data.get('title'),
            content=memory_data.get('content', ''),
            summary=memory_data.get('summary'),
            importance=memory_data.get('importance', 3),
            status='active',
            vector_status='pending',
        )
        db.session.add(memory)
        memories_created += 1

    db.session.commit()

    # Index seeded memories best-effort after commit.
    try:
        from server.services.memory.memory_writer import index_memory
        for memory in NovelMemory.query.filter_by(project_id=project_id, source_type='project', vector_status='pending').all():
            index_memory(memory)
    except Exception:
        pass

    return {
        'project_id': project_id,
        'title': project.title,
        'characters_created': len(char_entities),
        'entities_created': len(entity_by_name),
        'relations_created': relations_created,
        'events_created': events_created,
        'memories_created': memories_created,
        'volumes_created': len(result.get('volumes', [])),
        'chapters_created': chapter_order,
    }


def _resolve_outline_chapter_count(project, params):
    depth = params.get('depth', 'standard')
    requested = params.get('outline_chapters') or params.get('chapter_count')

    if requested:
        try:
            requested = int(requested)
        except (TypeError, ValueError):
            requested = None

    if requested:
        return max(3, min(requested, project.target_chapters or requested, 20))

    # Default by depth
    if depth == 'quick':
        return max(3, min(8, project.target_chapters or 8))
    elif depth == 'deep':
        return max(6, min(15, project.target_chapters or 15))
    else:  # standard
        return max(3, min(12, project.target_chapters or 12))


def _build_blueprint_memory_seeds(project, result):
    """Convert blueprint facts into long-term memory seed records."""
    seeds = []

    world_settings = result.get('world_settings') or {}
    if world_settings:
        seeds.append({
            'title': '世界观基础设定',
            'content': json.dumps(world_settings, ensure_ascii=False),
            'memory_type': 'world_rule',
            'importance': 5,
            'summary': '蓝图生成的世界观、规则、地点和禁忌。',
        })

    if result.get('main_conflict'):
        seeds.append({
            'title': '主线冲突',
            'content': result['main_conflict'],
            'memory_type': 'summary',
            'importance': 5,
            'summary': '全书主线冲突。',
        })

    for item in result.get('foreshadowing', []):
        if isinstance(item, str):
            item = {'title': item, 'content': item}
        if not item.get('content') and not item.get('title'):
            continue
        seeds.append({
            'title': item.get('title') or '蓝图伏笔',
            'content': item.get('content') or item.get('title'),
            'memory_type': 'foreshadowing',
            'importance': item.get('importance', 4),
            'summary': item.get('summary') or item.get('title'),
        })

    for event in result.get('key_events', []):
        if isinstance(event, str):
            event = {'title': event, 'summary': event}
        if not event.get('title'):
            continue
        seeds.append({
            'title': event['title'],
            'content': event.get('summary') or event['title'],
            'memory_type': 'event',
            'importance': event.get('importance', 4),
            'summary': event.get('summary'),
        })

    for seed in result.get('memory_seeds', []):
        if not seed.get('content'):
            continue
        seeds.append({
            'title': seed.get('title'),
            'content': seed['content'],
            'memory_type': seed.get('memory_type', 'summary'),
            'importance': seed.get('importance', 3),
            'summary': seed.get('summary'),
        })

    return seeds


def _build_timeout_fallback_blueprint(project, premise, outline_chapters):
    title = project.title if project.title and project.title != '未命名小说' else '未命名小说'
    chapters = []
    for idx in range(1, outline_chapters + 1):
        chapters.append({
            'title': f'第{idx}章',
            'summary': f'围绕「{premise}」推进第{idx}个关键剧情节点。',
            'plot_goal': '建立主线、推进人物选择与阶段目标。',
            'conflict_goal': '制造阻碍、误解或外部压力，让主角必须行动。',
            'target_words': project.words_per_chapter,
        })
    return {
        'title': title,
        'premise': premise,
        'main_character': {
            'name': '主角',
            'summary': '围绕核心创意展开成长与抉择的中心人物。',
            'attributes': {},
        },
        'characters': [],
        'entities': [
            {
                'name': '核心线索物',
                'entity_type': 'item',
                'summary': '承载主线秘密或关键能力的道具。',
                'importance': 7,
                'attributes': {},
            }
        ],
        'relations': [],
        'world_settings': {
            'genre': project.genre,
            'note': 'AI 蓝图请求超时，已生成可编辑的起步结构。',
            'rules': ['后续生成前需要补全详细世界规则。'],
        },
        'volumes': [{
            'title': '第一卷',
            'summary': '建立世界、人物目标和第一阶段主线冲突。',
            'chapters': chapters,
        }],
        'main_conflict': f'围绕「{premise}」展开的核心目标与阻碍。',
        'key_events': [
            {'title': '开端事件', 'summary': '主角被迫进入核心冲突。', 'event_type': 'inciting', 'timeline_order': 1},
            {'title': '第一次选择', 'summary': '主角做出影响后续路线的关键选择。', 'event_type': 'turning_point', 'timeline_order': 2},
            {'title': '阶段危机', 'summary': '第一阶段目标遭遇重大阻碍。', 'event_type': 'climax', 'timeline_order': 3},
        ],
        'foreshadowing': [
            {'title': '核心秘密伏笔', 'content': f'围绕「{premise}」保留一个后续回收的核心秘密。', 'importance': 4},
        ],
        'memory_seeds': [],
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
