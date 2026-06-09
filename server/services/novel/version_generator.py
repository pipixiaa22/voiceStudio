# server/services/novel/version_generator.py
from server.services.memory.workflow import run_chapter_workflow


DEFAULT_VERSION_TYPES = ['steady', 'conflict', 'suspense']


def generate_versions(project_id, chapter_id, params):
    """Generate multiple versions for a chapter using the unified pipeline."""
    version_types = params.get('version_types', DEFAULT_VERSION_TYPES)
    user_instruction = params.get('user_instruction', '')
    model_key = params.get('model_key')
    model_config = params.get('model_config')

    results = []
    errors = []
    for vtype in version_types:
        try:
            result = run_chapter_workflow(
                project_id=project_id,
                chapter_id=chapter_id,
                user_instruction=user_instruction,
                version_type=vtype,
                model_key=model_key,
                model_config=model_config,
            )
            if result.get('version_id'):
                from server.models.novel.chapter import NovelChapterVersion
                version = NovelChapterVersion.query.get(result['version_id'])
                if version:
                    results.append(version.to_dict())
        except Exception as e:
            errors.append({
                'version_type': vtype,
                'error': str(e),
            })

    if not results:
        error_text = '; '.join(
            f"{item['version_type']}: {item['error']}" for item in errors
        )
        raise RuntimeError(error_text or '没有生成任何续写版本')

    return {'versions': results, 'errors': errors}
