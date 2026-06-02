# server/services/novel/chapter_generator.py
import json
from server.models import db
from server.models.novel.chapter import NovelChapter, NovelChapterVersion
from server.models.novel.project import NovelProject
from server.services.novel.context_builder import build_context
from server.services.novel.prompt_templates import build_chapter_system_prompt


def generate_single_version(project_id, chapter_id, version_type='custom', user_instruction='', model_key=None):
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
    content = generate_with_memory(
        project=project,
        chapter=chapter,
        context=context,
        system_prompt=system_prompt,
        user_instruction=user_instruction,
        model_key=model_key,
        version_type=version_type,
    )

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
    version.context_snapshot = {'context_hash': hash(json.dumps(context, sort_keys=True, default=str))}

    db.session.add(version)
    db.session.commit()

    return version
