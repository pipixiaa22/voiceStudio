import json
from server.models.base import db
from server.models.text import Text, Tag


def create_text_from_analysis(
    item: dict,
    analysis_result: dict,
    folder_id: int | None = None,
    tag_names: list[str] | None = None,
) -> Text:
    """将分析结果转为 Text 模型实例并保存"""
    title = analysis_result.get('generated_title') or item.get('title') or '未命名'
    content = analysis_result.get('generated_content') or ''

    if not content:
        raise ValueError('分析结果中没有原创脚本内容')

    source_context = {
        'discovery_item_id': item.get('id'),
        'platform': item.get('platform_key'),
        'source_url': item.get('source_url'),
        'generated_from': 'discovery_analysis',
    }

    text = Text(
        title=title,
        content=content,
        folder_id=folder_id,
        source_context_json=json.dumps(source_context, ensure_ascii=False),
    )

    if tag_names:
        tags = []
        for name in tag_names:
            tag = Tag.query.filter_by(name=name).first()
            if not tag:
                tag = Tag(name=name)
                db.session.add(tag)
            tags.append(tag)
        text.tags = tags

    db.session.add(text)
    return text
