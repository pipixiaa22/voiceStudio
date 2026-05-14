# tests/test_splitter.py
from splitter import split_text


def test_split_by_sentence():
    text = "你好吗？我很好。今天天气不错！"
    result = split_text(text)
    assert result == ["你好吗？", "我很好。", "今天天气不错！"]


def test_split_long_sentence_by_comma():
    text = "这是一个很长的句子，包含了很多内容，需要在逗号处拆分。"
    result = split_text(text, max_chars=15)
    assert len(result) > 1
    for segment in result:
        assert len(segment) <= 15


def test_force_split_very_long_segment():
    text = "这是一个超级超级超级超级超级超级超级超级超级超级超级长的句子没有标点符号"
    result = split_text(text, max_chars=10)
    for segment in result:
        assert len(segment) <= 10


def test_empty_text():
    result = split_text("")
    assert result == []


def test_whitespace_only():
    result = split_text("   \n  \t  ")
    assert result == []
