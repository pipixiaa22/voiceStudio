from srt import _format_timestamp, generate_srt


def test_generate_srt_basic():
    segments = ["你好世界好", "我很好呀！"]
    result = generate_srt(segments, chars_per_second=5)
    expected = (
        "1\n"
        "00:00:00,000 --> 00:00:01,000\n"
        "你好世界好\n"
        "\n"
        "2\n"
        "00:00:02,000 --> 00:00:03,000\n"
        "我很好呀！\n"
    )
    assert result == expected


def test_generate_srt_custom_speed():
    segments = ["测试"]
    result = generate_srt(segments, chars_per_second=2)
    assert "00:00:00,000 --> 00:00:01,000" in result


def test_generate_srt_empty():
    result = generate_srt([], chars_per_second=5)
    assert result == ""


def test_generate_srt_multiline_segment():
    segments = ["你好\n世界"]
    result = generate_srt(segments, chars_per_second=2)
    assert "你好 世界" in result
    assert "\n世" not in result


def test_format_timestamp_edge_cases():
    assert _format_timestamp(0.0) == "00:00:00,000"
    assert _format_timestamp(61.123) == "00:01:01,123"
    assert _format_timestamp(3599.999) == "00:59:59,999"


def test_generate_srt_sub_second_duration():
    segments = ["测试"]
    result = generate_srt(segments, chars_per_second=3)
    # "测试" has 2 chars, 2/3 = 0.6666...s -> round to 0.667s
    assert "00:00:00,000 --> 00:00:00,667" in result
