from datetime import datetime, timezone, timedelta
from server.services.discovery.scoring import (
    score_xianxia, score_hot, score_format, score_item,
)


def test_xianxia_level1_keywords():
    score, reasons = score_xianxia('仙帝重生归来', [])
    assert score >= 0.3
    assert any('一级' in r for r in reasons)


def test_xianxia_level2_keywords():
    score, reasons = score_xianxia('废柴筑基逆袭', [])
    assert score >= 0.15
    assert any('二级' in r for r in reasons)


def test_xianxia_structure_keywords():
    score, reasons = score_xianxia('开局被逐出宗门', [])
    assert score >= 0.2
    assert any('结构' in r for r in reasons)


def test_xianxia_no_match():
    score, reasons = score_xianxia('今天天气真好', [])
    assert score == 0.0
    assert len(reasons) == 0


def test_xianxia_from_tags():
    score, _ = score_xianxia('短视频', ['修仙', '重生'])
    assert score >= 0.3


def test_xianxia_cap_at_1():
    score, _ = score_xianxia('修仙玄幻仙帝仙尊重生渡劫开局穿越成', [])
    assert score <= 1.0


def test_hot_high_views():
    score, reasons = score_hot({'views': 200000, 'likes': 10000, 'comments': 500}, 'youtube')
    assert score > 0.5
    assert any('播放量' in r for r in reasons)


def test_hot_zero_views():
    score, _ = score_hot({'views': 0, 'likes': 0, 'comments': 0}, 'youtube')
    assert score == 0.0


def test_hot_time_decay_recent():
    now = datetime.now(timezone.utc)
    recent = now - timedelta(days=3)
    score_recent, reasons = score_hot({'views': 100000}, 'youtube', recent)
    assert any('近7天' in r for r in reasons)

    old = now - timedelta(days=60)
    score_old, _ = score_hot({'views': 100000}, 'youtube', old)
    assert score_recent > score_old


def test_hot_platform_baseline():
    score_yt, _ = score_hot({'views': 100000}, 'youtube')
    score_bili, _ = score_hot({'views': 100000}, 'bilibili')
    assert score_yt > score_bili


def test_format_keyword_match():
    score, reasons = score_format('有声小说 修仙', None)
    assert score >= 0.4
    assert any('形态' in r for r in reasons)


def test_format_duration_in_range():
    score, reasons = score_format('普通标题', 120)
    assert score >= 0.3
    assert any('时长' in r for r in reasons)


def test_format_duration_out_of_range():
    score, _ = score_format('普通标题', 10)
    assert score < 0.3


def test_score_item_full():
    item = {
        'title': '仙帝重生归来 有声小说',
        'tags': ['修仙'],
        'stats': {'views': 200000, 'likes': 10000, 'comments': 500},
        'platform_key': 'youtube',
        'duration': 120,
        'published_at': (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
    }
    result = score_item(item)
    assert result['xianxia_score'] > 0.5
    assert result['hot_score'] > 0.5
    assert result['format_score'] > 0.5
    assert len(result['reasons']) > 0


def test_score_item_empty():
    item = {'title': '', 'tags': [], 'stats': {}, 'platform_key': 'manual'}
    result = score_item(item)
    assert result['xianxia_score'] == 0.0
    assert result['hot_score'] == 0.0
    assert result['format_score'] == 0.0
