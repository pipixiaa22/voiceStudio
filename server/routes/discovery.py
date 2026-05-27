import json
from flask import Blueprint, request, jsonify
from sqlalchemy import select
from server.models import db, DiscoverySource, DiscoveryQuery, DiscoveryItem, DiscoveryAnalysis
from server.services.discovery.registry import ConnectorRegistry
from server.services.discovery import scoring as scoring_service
from server.services.discovery.analyzer import analyze_item
from server.services.discovery.script_adapter import create_text_from_analysis

discovery_bp = Blueprint('discovery', __name__)


def _get_item_or_404(item_id):
    """Get a DiscoveryItem by ID or return 404."""
    item = db.session.get(DiscoveryItem, item_id)
    if item is None:
        from flask import abort
        abort(404)
    return item


@discovery_bp.route('/api/discovery/sources', methods=['GET'])
def get_sources():
    sources = db.session.execute(
        select(DiscoverySource).order_by(DiscoverySource.id)
    ).scalars().all()
    result = []
    for src in sources:
        d = src.to_dict()
        connector = ConnectorRegistry.get(src.platform_key)
        d['needs_api_key'] = connector is not None and hasattr(connector, '_get_api_key')
        result.append(d)
    return jsonify(result)


@discovery_bp.route('/api/discovery/search', methods=['POST'])
def search():
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求数据不能为空'}), 400

    platform = data.get('platform', '').strip()
    query_text = data.get('query', '').strip()
    limit = min(int(data.get('limit', 20)), 50)
    filters = data.get('filters') or {}

    if not platform:
        return jsonify({'error': '请选择平台'}), 400
    if not query_text:
        return jsonify({'error': '请输入搜索关键词'}), 400

    source = db.session.execute(
        select(DiscoverySource).filter_by(platform_key=platform)
    ).scalars().first()
    if not source or not source.is_enabled:
        return jsonify({'error': '该平台未启用'}), 400

    connector = ConnectorRegistry.get(platform)
    if not connector:
        return jsonify({'error': '该平台暂不支持搜索'}), 400

    dq = DiscoveryQuery(
        query_type='keyword',
        platform_key=platform,
        query_text=query_text,
        filters_json=json.dumps(filters, ensure_ascii=False),
        status='running',
    )
    db.session.add(dq)
    db.session.commit()

    try:
        results = connector.search(query_text, limit, filters)
    except Exception as e:
        dq.status = 'failed'
        dq.error_message = str(e)
        db.session.commit()
        return jsonify({'error': f'搜索失败: {str(e)}'}), 502

    items = []
    for result in results:
        score_result = scoring_service.score_item(result)

        item = DiscoveryItem(
            query_id=dq.id,
            platform_key=result.get('platform_key', platform),
            source_url=result['source_url'],
            source_id=result.get('source_id'),
            title=result.get('title'),
            author_name=result.get('author_name'),
            cover_url=result.get('cover_url'),
            published_at=result.get('published_at'),
            duration=result.get('duration'),
            stats_json=json.dumps(result.get('stats', {}), ensure_ascii=False),
            tags_json=json.dumps(result.get('tags', []), ensure_ascii=False),
            raw_json=json.dumps(result, ensure_ascii=False),
        )
        db.session.add(item)
        db.session.flush()

        analysis = DiscoveryAnalysis(
            item_id=item.id,
            xianxia_score=score_result['xianxia_score'],
            hot_score=score_result['hot_score'],
            format_score=score_result['format_score'],
            score_reasons_json=json.dumps(score_result['reasons'], ensure_ascii=False),
        )
        db.session.add(analysis)

        item_dict = item.to_dict()
        item_dict['xianxia_score'] = score_result['xianxia_score']
        item_dict['hot_score'] = score_result['hot_score']
        item_dict['format_score'] = score_result['format_score']
        items.append(item_dict)

    dq.status = 'completed'
    dq.item_count = len(items)
    db.session.commit()

    return jsonify({
        'query_id': dq.id,
        'items': items,
        'total': len(items),
    })


@discovery_bp.route('/api/discovery/resolve-url', methods=['POST'])
def resolve_url():
    data = request.get_json()
    if not data or not data.get('url'):
        return jsonify({'error': '请输入视频链接'}), 400

    url = data['url'].strip()

    dq = DiscoveryQuery(
        query_type='url',
        platform_key='manual',
        query_text=url,
        status='running',
    )
    db.session.add(dq)
    db.session.commit()

    connector = ConnectorRegistry.get('manual')
    try:
        result = connector.resolve_url(url)
    except Exception as e:
        dq.status = 'failed'
        dq.error_message = str(e)
        db.session.commit()
        return jsonify({'error': f'解析链接失败: {str(e)}'}), 502

    score_result = scoring_service.score_item(result)

    item = DiscoveryItem(
        query_id=dq.id,
        platform_key=result.get('platform_key', 'manual'),
        source_url=result.get('source_url', url),
        source_id=result.get('source_id'),
        title=result.get('title'),
        author_name=result.get('author_name'),
        cover_url=result.get('cover_url'),
        duration=result.get('duration'),
        stats_json=json.dumps(result.get('stats', {}), ensure_ascii=False),
        tags_json=json.dumps(result.get('tags', []), ensure_ascii=False),
        raw_json=json.dumps(result, ensure_ascii=False),
    )
    db.session.add(item)
    db.session.flush()

    analysis = DiscoveryAnalysis(
        item_id=item.id,
        xianxia_score=score_result['xianxia_score'],
        hot_score=score_result['hot_score'],
        format_score=score_result['format_score'],
        score_reasons_json=json.dumps(score_result['reasons'], ensure_ascii=False),
    )
    db.session.add(analysis)

    dq.status = 'completed'
    dq.item_count = 1
    db.session.commit()

    item_dict = item.to_dict()
    item_dict['xianxia_score'] = score_result['xianxia_score']
    item_dict['hot_score'] = score_result['hot_score']
    item_dict['format_score'] = score_result['format_score']
    return jsonify(item_dict)


@discovery_bp.route('/api/discovery/items', methods=['GET'])
def list_items():
    stmt = select(DiscoveryItem)

    platform = request.args.get('platform')
    if platform:
        stmt = stmt.filter_by(platform_key=platform)

    favorited = request.args.get('favorited')
    if favorited == 'true':
        stmt = stmt.filter_by(is_favorited=True)

    min_score = request.args.get('min_score')
    if min_score:
        stmt = stmt.join(DiscoveryAnalysis).filter(
            DiscoveryAnalysis.xianxia_score >= float(min_score)
        )

    page = int(request.args.get('page', 1))
    per_page = min(int(request.args.get('per_page', 20)), 100)

    stmt = stmt.order_by(DiscoveryItem.created_at.desc())

    # Count total
    from sqlalchemy import func
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.session.execute(count_stmt).scalar()

    items = db.session.execute(
        stmt.offset((page - 1) * per_page).limit(per_page)
    ).scalars().all()

    result = []
    for item in items:
        d = item.to_dict()
        if item.analysis:
            d['xianxia_score'] = item.analysis.xianxia_score
            d['hot_score'] = item.analysis.hot_score
            d['format_score'] = item.analysis.format_score
        result.append(d)

    return jsonify({'items': result, 'total': total, 'page': page, 'per_page': per_page})


@discovery_bp.route('/api/discovery/items/<int:item_id>', methods=['GET'])
def get_item(item_id):
    item = _get_item_or_404(item_id)
    d = item.to_dict()
    if item.analysis:
        d['analysis'] = item.analysis.to_dict()
    return jsonify(d)


@discovery_bp.route('/api/discovery/items/<int:item_id>/analyze', methods=['POST'])
def analyze(item_id):
    item = _get_item_or_404(item_id)

    score_result = {
        'xianxia_score': item.analysis.xianxia_score if item.analysis else 0,
        'hot_score': item.analysis.hot_score if item.analysis else 0,
        'format_score': item.analysis.format_score if item.analysis else 0,
        'reasons': json.loads(item.analysis.score_reasons_json) if item.analysis and item.analysis.score_reasons_json else [],
    }

    item_dict = item.to_dict()

    try:
        llm_result = analyze_item(item_dict, score_result)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'分析失败: {str(e)}'}), 502

    if item.analysis:
        analysis = item.analysis
    else:
        analysis = DiscoveryAnalysis(item_id=item.id)
        db.session.add(analysis)

    analysis.xianxia_score = score_result['xianxia_score']
    analysis.hot_score = score_result['hot_score']
    analysis.format_score = score_result['format_score']
    analysis.score_reasons_json = json.dumps(score_result['reasons'], ensure_ascii=False)
    analysis.analysis_json = json.dumps(llm_result, ensure_ascii=False)
    analysis.generated_title = llm_result.get('generated_title')
    analysis.generated_content = llm_result.get('generated_content')
    analysis.recommended_template = llm_result.get('recommended_template')
    analysis.recommended_voice_desc = llm_result.get('recommended_voice_desc')
    analysis.recommended_max_chars = llm_result.get('recommended_max_chars')

    db.session.commit()
    return jsonify(analysis.to_dict())


@discovery_bp.route('/api/discovery/items/<int:item_id>/create-text', methods=['POST'])
def create_text(item_id):
    item = _get_item_or_404(item_id)

    if not item.analysis or not item.analysis.generated_content:
        return jsonify({'error': '请先分析该视频并生成原创脚本'}), 400

    data = request.get_json() or {}
    folder_id = data.get('folder_id')
    tag_names = data.get('tag_names', ['热点参考'])

    item_dict = item.to_dict()
    analysis_result = json.loads(item.analysis.analysis_json) if item.analysis.analysis_json else {}
    analysis_result['generated_title'] = item.analysis.generated_title
    analysis_result['generated_content'] = item.analysis.generated_content

    try:
        text = create_text_from_analysis(item_dict, analysis_result, folder_id, tag_names)
        db.session.commit()
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    return jsonify({'text_id': text.id, 'title': text.title}), 201


@discovery_bp.route('/api/discovery/items/<int:item_id>/favorite', methods=['PUT'])
def toggle_favorite(item_id):
    item = _get_item_or_404(item_id)
    item.is_favorited = not item.is_favorited
    db.session.commit()
    return jsonify({'is_favorited': item.is_favorited})


@discovery_bp.route('/api/discovery/queries', methods=['GET'])
def list_queries():
    queries = db.session.execute(
        select(DiscoveryQuery).order_by(DiscoveryQuery.created_at.desc()).limit(50)
    ).scalars().all()
    return jsonify([q.to_dict() for q in queries])


@discovery_bp.route('/api/discovery/items/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    item = _get_item_or_404(item_id)
    if item.analysis:
        db.session.delete(item.analysis)
    db.session.delete(item)
    db.session.commit()
    return '', 204
