from srt import generate_srt


def test_generate_srt_basic():
    segments = ["你好世界好", "我很好呀！"]
    result = generate_srt(segments, chars_per_second=5)
    expected = (
        "1\n"
        "00:00:00,000 --> 00:00:01,000\n"
        "你好世界好\n"
        "\n"
        "2\n"
        "00:00:01,000 --> 00:00:02,000\n"
        "我很好呀！"
    )
    assert result == expected


def test_generate_srt_custom_speed():
    segments = ["测试"]
    result = generate_srt(segments, chars_per_second=2)
    assert "00:00:00,000 --> 00:00:01,000" in result


def test_generate_srt_empty():
    result = generate_srt([], chars_per_second=5)
    assert result == ""
