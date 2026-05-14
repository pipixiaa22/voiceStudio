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
    # Verify actual content
    assert "这是一个很长的句子，" in result
    assert "包含了很多内容，" in result
    assert "需要在逗号处拆分。" in result


def test_force_split_very_long_segment():
    text = "这是一个超级超级超级超级超级超级超级超级超级超级超级长的句子没有标点符号"
    result = split_text(text, max_chars=10)
    for segment in result:
        assert len(segment) <= 10
    # Verify reassembly preserves the original text
    assert "".join(result) == text


def test_content_preservation():
    """Joined segments must reproduce the original text exactly."""
    texts = [
        "你好吗？我很好。今天天气不错！",
        "这是一个很长的句子，包含了很多内容，需要在逗号处拆分。",
        "没有标点符号的纯文本",
        "混合：逗号、分号；还有句号。",
    ]
    for text in texts:
        result = split_text(text)
        assert "".join(result) == text, f"Content lost for: {text}"


def test_mixed_sentence_and_comma_splitting():
    """Sentences split by punctuation, then long sentences further split by comma."""
    text = "短句。这是一个很长的句子，包含了很多内容，需要在逗号处拆分。末尾。"
    result = split_text(text, max_chars=15)
    # "短句。" and "末尾。" stay whole
    assert "短句。" in result
    assert "末尾。" in result
    # Long sentence split by commas
    for segment in result:
        assert len(segment) <= 15


def test_empty_text():
    result = split_text("")
    assert result == []


def test_whitespace_only():
    result = split_text("   \n  \t  ")
    assert result == []
