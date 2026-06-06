# server/services/novel/chapter_generator.py
import json
from server.models import db
from server.models.novel.chapter import NovelChapter, NovelChapterVersion
from server.models.novel.project import NovelProject
from server.models.novel.graph_change import NovelGraphChange
from server.models.novel.memory import NovelMemoryChange
from server.services.novel.context_builder import build_context
from server.services.novel.prompt_templates import build_chapter_system_prompt


def generate_single_version(
    project_id,
    chapter_id,
    version_type='custom',
    user_instruction='',
    model_key=None,
    model_config=None,
):
    """Generate a single version for a chapter."""
    project = NovelProject.query.get_or_404(project_id)
    chapter = NovelChapter.query.get_or_404(chapter_id)

    # Build context
    context = build_context(project_id, chapter_id, user_instruction, project.words_per_chapter)

    # Build system prompt
    system_prompt = build_chapter_system_prompt(
        project.genre,
        version_type=version_type,
        style_guide=project.style_guide,
    )

    # Generate with RAG memory
    from server.services.memory.rag_chain import generate_with_memory
    structured_result = generate_with_memory(
        project=project,
        chapter=chapter,
        context=context,
        system_prompt=system_prompt,
        user_instruction=user_instruction,
        model_key=model_key,
        model_config=model_config,
        version_type=version_type,
        structured_output=True,
    )
    content = structured_result['content_markdown']
    knowledge_updates = structured_result.get('knowledge_updates') or {}
    chapter_state = structured_result.get('chapter_state')

    # Create version
    version = NovelChapterVersion(
        chapter_id=chapter_id,
        version_type=version_type,
        title=f'{version_type}版',
        content_markdown=content,
        model=model_key or 'unknown',
        accepted=False,
    )
    version.prompt = {'system': system_prompt, 'user': user_instruction}
    snapshot = {'context_hash': hash(json.dumps(context, sort_keys=True, default=str))}
    if chapter_state:
        snapshot['chapter_state'] = chapter_state
    version.context_snapshot = snapshot

    db.session.add(version)
    db.session.flush()

    graph_changes = _create_graph_change_candidates(
        project_id=project_id,
        chapter_id=chapter_id,
        version_id=version.id,
        changes=knowledge_updates.get('graph_changes') or [],
    )
    memory_changes = _create_memory_change_candidates(
        project_id=project_id,
        chapter_id=chapter_id,
        version_id=version.id,
        changes=knowledge_updates.get('memory_changes') or [],
    )

    db.session.commit()

    version.generated_graph_changes = [c.to_dict() for c in graph_changes]
    version.generated_memory_changes = [c.to_dict() for c in memory_changes]

    return version


def _clamp_number(value, default, min_value, max_value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = default
    return max(min_value, min(max_value, value))


def _create_graph_change_candidates(project_id, chapter_id, version_id, changes):
    allowed_targets = {'entity', 'event'}
    created = []
    for item in changes:
        if not isinstance(item, dict):
            continue

        after = item.get('after') or {}
        if not isinstance(after, dict):
            continue

        target_type = item.get('target_type') or 'entity'
        if target_type not in allowed_targets:
            continue

        if target_type == 'entity':
            name = (after.get('name') or '').strip()
            if not name:
                continue
            after = {
                **after,
                'name': name,
                'entity_type': after.get('entity_type') or 'character',
                'importance': _clamp_number(after.get('importance'), 5, 1, 10),
            }
        elif target_type == 'event':
            title = (after.get('title') or '').strip()
            if not title:
                continue
            after = {
                **after,
                'title': title,
                'event_type': after.get('event_type') or 'event',
            }

        change = NovelGraphChange(
            project_id=project_id,
            chapter_id=chapter_id,
            change_type=item.get('change_type') if item.get('change_type') in ('add', 'modify') else 'add',
            target_type=target_type,
            source='ai_confirm',
            confidence=float(item.get('confidence', 0.7) or 0.7),
        )
        change.after = {
            **after,
            '_source_version_id': version_id,
            '_description': item.get('description', ''),
        }
        db.session.add(change)
        created.append(change)
    return created


def _create_memory_change_candidates(project_id, chapter_id, version_id, changes):
    from server.services.memory.document_types import MEMORY_TYPES

    created = []
    for item in changes:
        if not isinstance(item, dict):
            continue

        after = item.get('after') or {}
        if not isinstance(after, dict):
            continue

        content = (after.get('content') or '').strip()
        if not content:
            continue

        memory_type = after.get('memory_type') or 'summary'
        if memory_type not in MEMORY_TYPES:
            memory_type = 'summary'

        normalized_after = {
            **after,
            'content': content,
            'memory_type': memory_type,
            'importance': _clamp_number(after.get('importance'), 3, 1, 5),
            'source_type': 'ai_extract',
            'source_id': chapter_id,
            'metadata': {
                **(after.get('metadata') or {}),
                'chapter_id': chapter_id,
                'version_id': version_id,
                'description': item.get('description', ''),
            },
        }

        change = NovelMemoryChange(
            project_id=project_id,
            change_type=item.get('change_type') if item.get('change_type') in ('add', 'modify') else 'add',
            source='ai_generation',
            status='pending',
        )
        change.after = normalized_after
        db.session.add(change)
        created.append(change)
    return created
