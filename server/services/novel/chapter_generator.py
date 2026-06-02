# server/services/novel/chapter_generator.py
import json
from server.models import db
from server.models.novel.chapter import NovelChapter, NovelChapterVersion
from server.models.novel.project import NovelProject
from server.services.novel.context_builder import build_context
from server.services.novel.prompt_templates import build_chapter_system_prompt, build_chapter_user_prompt


def generate_single_version(project_id, chapter_id, version_type='custom', user_instruction='', model_key=None):
    """Generate a single version for a chapter."""
    project = NovelProject.query.get_or_404(project_id)
    chapter = NovelChapter.query.get_or_404(chapter_id)

    # Build context
    context = build_context(project_id, chapter_id, user_instruction, project.words_per_chapter)

    # Build prompts
    system_prompt = build_chapter_system_prompt(
        project.genre,
        version_type=version_type,
        style_guide=project.style_guide,
    )
    user_prompt = build_chapter_user_prompt(context)

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

    # Create version
    version = NovelChapterVersion(
        chapter_id=chapter_id,
        version_type=version_type,
        title=f'{version_type}版',
        content_markdown=content,
        model=model_key or default_model,
        accepted=False,
    )
    version.prompt = {'system': system_prompt, 'user': user_prompt}
    version.context_snapshot = {'context_hash': hash(json.dumps(context, sort_keys=True, default=str))}

    db.session.add(version)
    db.session.commit()

    return version
