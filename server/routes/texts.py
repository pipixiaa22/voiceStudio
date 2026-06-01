import sys
import os

import requests as http_requests
from deep_translator import GoogleTranslator
from flask import Blueprint, request, jsonify
from server.models import db, Text, Tag
from server.services.jianying_draft import inject_subtitles_into_draft, parse_srt_timeline

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from splitter import split_text
from srt import generate_srt, generate_bilingual_srt

MIMO_LLM_URL = 'https://token-plan-cn.xiaomimimo.com/anthropic/v1/messages'

texts_bp = Blueprint('texts', __name__)


@texts_bp.route('/api/texts', methods=['GET'])
def get_texts():
    query = Text.query

    folder_id = request.args.get('folder_id')
    if folder_id:
        query = query.filter_by(folder_id=folder_id)

    tag_name = request.args.get('tag')
    if tag_name:
        query = query.filter(Text.tags.any(Tag.name == tag_name))

    sort_by = request.args.get('sort_by', 'created_at')
    order = request.args.get('order', 'desc')
    sort_column = getattr(Text, sort_by, Text.created_at)
    query = query.order_by(sort_column.desc() if order == 'desc' else sort_column.asc())

    texts = query.all()
    return jsonify([t.to_dict() for t in texts])


@texts_bp.route('/api/texts/<int:text_id>', methods=['GET'])
def get_text(text_id):
    text = Text.query.get_or_404(text_id)
    return jsonify(text.to_dict())


@texts_bp.route('/api/texts', methods=['POST'])
def create_text():
    data = request.get_json()
    if not data or not data.get('content'):
        return jsonify({'error': '内容不能为空'}), 400

    text = Text(
        title=data.get('title', '未命名'),
        content=data['content'],
        folder_id=data.get('folder_id'),
    )

    tag_ids = data.get('tag_ids', [])
    if tag_ids:
        tags = Tag.query.filter(Tag.id.in_(tag_ids)).all()
        text.tags = tags

    db.session.add(text)
    db.session.commit()
    return jsonify(text.to_dict()), 201


@texts_bp.route('/api/texts/<int:text_id>', methods=['PUT'])
def update_text(text_id):
    text = Text.query.get_or_404(text_id)
    data = request.get_json()

    if 'title' in data:
        text.title = data['title']
    if 'content' in data:
        text.content = data['content']
    if 'folder_id' in data:
        text.folder_id = data['folder_id']
    if 'tag_ids' in data:
        tags = Tag.query.filter(Tag.id.in_(data['tag_ids'])).all()
        text.tags = tags

    db.session.commit()
    return jsonify(text.to_dict())


@texts_bp.route('/api/texts/<int:text_id>', methods=['DELETE'])
def delete_text(text_id):
    text = Text.query.get_or_404(text_id)
    db.session.delete(text)
    db.session.commit()
    return '', 204


@texts_bp.route('/api/texts/import', methods=['POST'])
def import_text():
    if 'file' not in request.files:
        return jsonify({'error': '没有上传文件'}), 400

    file = request.files['file']
    if not file.filename.endswith('.txt'):
        return jsonify({'error': '只支持 .txt 文件'}), 400

    content = file.read().decode('utf-8')
    title = file.filename.replace('.txt', '')

    text = Text(title=title, content=content)
    db.session.add(text)
    db.session.commit()
    return jsonify(text.to_dict()), 201


def _dedup_title(base_title, existing_titles):
    """Append (1), (2), ... to base_title until it's unique."""
    if base_title not in existing_titles:
        return base_title
    i = 1
    while f'{base_title}({i})' in existing_titles:
        i += 1
    return f'{base_title}({i})'


@texts_bp.route('/api/texts/batch-import', methods=['POST'])
def batch_import():
    files = request.files.getlist('files')
    if not files:
        return jsonify({'error': '没有上传文件'}), 400

    folder_id = request.form.get('folder_id')
    folder_id = int(folder_id) if folder_id else None

    existing_titles = {t.title for t in Text.query.with_entities(Text.title).all()}
    imported = []

    for file in files:
        if not file.filename.endswith('.txt'):
            continue
        content = file.read().decode('utf-8')
        base_title = file.filename.replace('.txt', '')
        title = _dedup_title(base_title, existing_titles)
        existing_titles.add(title)

        text = Text(title=title, content=content, folder_id=folder_id)
        db.session.add(text)
        imported.append(text)

    db.session.commit()
    return jsonify([t.to_dict() for t in imported]), 201


@texts_bp.route('/api/texts/generate-srt', methods=['POST'])
def generate_srt_preview():
    data = request.get_json()
    if not data or not data.get('content'):
        return jsonify({'error': '内容不能为空'}), 400

    content = data['content']
    speed = float(data.get('speed', 5))
    max_chars = int(data.get('max_chars', 20))
    gap = float(data.get('gap', 1.0))

    segments = split_text(content, max_chars=max_chars)
    srt_content = generate_srt(segments, chars_per_second=speed, gap=gap)

    return jsonify({'srt': srt_content, 'segments': len(segments), 'segments_list': segments})


@texts_bp.route('/api/texts/generate-bilingual-srt', methods=['POST'])
def generate_bilingual_srt_preview():
    data = request.get_json()
    if not data or not data.get('content'):
        return jsonify({'error': '内容不能为空'}), 400

    content = data['content']
    speed = float(data.get('speed', 5))
    max_chars = int(data.get('max_chars', 20))
    gap = float(data.get('gap', 1.0))

    segments = split_text(content, max_chars=max_chars)

    translator = GoogleTranslator(source='zh-CN', target='en')
    translations = []
    for seg in segments:
        try:
            translated = translator.translate(seg)
            translations.append(translated or '')
        except Exception:
            translations.append('')

    srt_content = generate_bilingual_srt(segments, translations, chars_per_second=speed, gap=gap)

    return jsonify({
        'srt': srt_content,
        'segments': len(segments),
        'segments_list': segments,
        'translations': translations,
    })


@texts_bp.route('/api/texts/<int:text_id>/srt', methods=['GET'])
def export_srt(text_id):
    text = Text.query.get_or_404(text_id)

    speed = float(request.args.get('speed', 5))
    max_chars = int(request.args.get('max_chars', 20))
    gap = float(request.args.get('gap', 1.0))

    segments = split_text(text.content, max_chars=max_chars)
    srt_content = generate_srt(segments, chars_per_second=speed, gap=gap)

    # URL-encode the filename to handle non-ASCII characters
    from urllib.parse import quote
    encoded_filename = quote(f'{text.title}.srt')

    return srt_content, 200, {
        'Content-Type': 'text/srt; charset=utf-8',
        'Content-Disposition': f"attachment; filename*=UTF-8''{encoded_filename}"
    }


@texts_bp.route('/api/texts/srt-to-jianying', methods=['POST'])
def import_srt_to_jianying():
    data = request.get_json() or {}
    draft_dir = data.get('draft_dir')
    srt_content = data.get('srt_content')
    if not draft_dir:
        return jsonify({'error': '请填写剪映工程目录'}), 400
    if not srt_content:
        return jsonify({'error': '请先生成 SRT 字幕'}), 400

    try:
        timeline = parse_srt_timeline(srt_content)
        result = inject_subtitles_into_draft(
            draft_dir,
            timeline,
            track_name=data.get('track_name') or '墨影字幕-文本库',
        )
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify(result)
