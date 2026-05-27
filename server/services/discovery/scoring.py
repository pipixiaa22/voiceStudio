from datetime import datetime, timezone

LEVEL1_KEYWORDS = {'修仙': 0.3, '玄幻': 0.3, '仙帝': 0.3, '仙尊': 0.3, '重生': 0.3, '渡劫': 0.3}
LEVEL2_KEYWORDS = {'炼气': 0.15, '筑基': 0.15, '金丹': 0.15, '元婴': 0.15, '宗门': 0.15,
                   '师尊': 0.15, '女帝': 0.15, '系统': 0.1, '逆袭': 0.15}
STRUCTURE_KEYWORDS = {'开局': 0.2, '我竟然': 0.2, '一口气看完': 0.2, '穿越成': 0.2,
                      '被逐出宗门': 0.2, '三千年后归来': 0.2}

FORMAT_KEYWORDS = {'有声小说': 0.4, '小说推文': 0.4, '一张图': 0.4, '书荒推荐': 0.4,
                   '一口气看完': 0.3, '完整版': 0.3, '全集': 0.3}

PLATFORM_VIEW_BASELINES = {
    'youtube': 100_000,
    'bilibili': 500_000,
    'douyin': 500_000,
    'kuaishou': 500_000,
    'manual': 100_000,
}


def _match_keywords(text: str, keywords: dict[str, float]) -> float:
    score = 0.0
    for keyword, weight in keywords.items():
        if keyword in text:
            score += weight
    return min(score, 1.0)


def score_xianxia(title: str, tags: list[str]) -> tuple[float, list[str]]:
    combined = title + ' '.join(tags)
    reasons = []

    s1 = _match_keywords(combined, LEVEL1_KEYWORDS)
    if s1 > 0:
        hit = [k for k in LEVEL1_KEYWORDS if k in combined]
        reasons.append(f'一级关键词命中: {"/".join(hit)}')

    s2 = _match_keywords(combined, LEVEL2_KEYWORDS)
    if s2 > 0:
        hit = [k for k in LEVEL2_KEYWORDS if k in combined]
        reasons.append(f'二级关键词命中: {"/".join(hit)}')

    s3 = _match_keywords(combined, STRUCTURE_KEYWORDS)
    if s3 > 0:
        hit = [k for k in STRUCTURE_KEYWORDS if k in combined]
        reasons.append(f'结构词命中: {"/".join(hit)}')

    total = min(s1 + s2 + s3, 1.0)
    return total, reasons


def score_hot(stats: dict, platform_key: str, published_at=None) -> tuple[float, list[str]]:
    reasons = []
    baseline = PLATFORM_VIEW_BASELINES.get(platform_key, 100_000)

    views = stats.get('views', 0)
    likes = stats.get('likes', 0)
    comments = stats.get('comments', 0)
    shares = stats.get('shares', 0)

    view_score = min(views / baseline, 1.0)

    engagement = 0.0
    if views > 0:
        engagement = min((likes + comments + shares) / views, 0.3)

    time_multiplier = 1.0
    if published_at:
        if isinstance(published_at, str):
            try:
                published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
            except ValueError:
                published_at = None
        if published_at:
            days_ago = (datetime.now(timezone.utc) - published_at).days
            if days_ago <= 7:
                time_multiplier = 1.0
                reasons.append('近7天发布')
            elif days_ago <= 30:
                time_multiplier = 0.7
            else:
                time_multiplier = 0.4

    if views > 0:
        reasons.append(f'播放量 {views}')

    total = min((view_score * 0.7 + engagement) * time_multiplier, 1.0)
    return total, reasons


def score_format(title: str, duration: float | None) -> tuple[float, list[str]]:
    reasons = []
    score = 0.0

    keyword_score = _match_keywords(title, FORMAT_KEYWORDS)
    if keyword_score > 0:
        score += min(keyword_score, 0.4)
        hit = [k for k in FORMAT_KEYWORDS if k in title]
        reasons.append(f'形态关键词命中: {"/".join(hit)}')

    if duration is not None and 30 <= duration <= 480:
        score += 0.3
        reasons.append(f'时长 {int(duration)}秒 符合短视频')

    return min(score, 1.0), reasons


def score_item(item: dict) -> dict:
    title = item.get('title') or ''
    tags = item.get('tags') or []
    stats = item.get('stats') or {}
    platform_key = item.get('platform_key', 'manual')
    duration = item.get('duration')
    published_at = item.get('published_at')

    xianxia, x_reasons = score_xianxia(title, tags)
    hot, h_reasons = score_hot(stats, platform_key, published_at)
    fmt, f_reasons = score_format(title, duration)

    return {
        'xianxia_score': round(xianxia, 2),
        'hot_score': round(hot, 2),
        'format_score': round(fmt, 2),
        'reasons': x_reasons + h_reasons + f_reasons,
    }
