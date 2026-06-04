# server/services/novel/version_generator.py
from server.models import db
from server.models.novel.chapter import NovelChapterVersion
from server.services.novel.chapter_generator import generate_single_version


DEFAULT_VERSION_TYPES = ['steady', 'conflict', 'suspense']


def generate_versions(project_id, chapter_id, params):
    """Generate multiple versions for a chapter."""
    version_types = params.get('version_types', DEFAULT_VERSION_TYPES)
    user_instruction = params.get('user_instruction', '')
    model_key = params.get('model_key')
    model_config = params.get('model_config')

    results = []
    for vtype in version_types:
        try:
            version = generate_single_version(
                project_id=project_id,
                chapter_id=chapter_id,
                version_type=vtype,
                user_instruction=user_instruction,
                model_key=model_key,
                model_config=model_config,
            )
            results.append(version.to_dict())
        except Exception as e:
            results.append({
                'version_type': vtype,
                'error': str(e),
            })

    return {'versions': results}
