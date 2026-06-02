# server/services/novel/summarizer.py
from server.models import db
from server.models.novel.chapter import NovelChapter


def generate_summary(chapter_id):
    """Generate a summary for a confirmed chapter."""
    chapter = NovelChapter.query.get_or_404(chapter_id)
    if not chapter.content_markdown:
        raise ValueError('章节内容为空')

    prompt = f"""请为以下章节生成一段 200-500 字的摘要，用于后续章节的前文上下文参考。

摘要要求：
1. 概括本章主要剧情
2. 记录重要人物行为和状态变化
3. 记录新出现的冲突和伏笔
4. 记录已解决的问题
5. 保持客观叙述，不要添加评价

【章节标题】{chapter.title}

【章节正文】
{chapter.content_markdown}"""

    from server.services.novel import get_llm_provider
    provider, default_model = get_llm_provider()

    messages = [{'role': 'user', 'content': prompt}]
    summary = provider.complete(
        messages,
        model=default_model,
        system_prompt='你是一位小说摘要撰写专家，擅长提炼章节要点。',
        max_tokens=1024,
        timeout=30,
    )

    chapter.summary = summary.strip()
    db.session.commit()

    return {'chapter_id': chapter_id, 'summary': chapter.summary}
