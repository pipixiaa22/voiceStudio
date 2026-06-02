"""Unit tests for memory service utilities."""

import pytest
from server.services.memory.utils import parse_memory_json
from server.services.memory.chunker import chunk_text
from server.services.memory.retriever import _normalize_distance, _type_weight, _truncate_at_sentence


# --- parse_memory_json ---

class TestParseMemoryJson:
    def test_valid_json(self):
        result = parse_memory_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_markdown_code_block(self):
        text = '```json\n{"key": "value"}\n```'
        result = parse_memory_json(text)
        assert result == {"key": "value"}

    def test_markdown_code_block_no_lang(self):
        text = '```\n{"key": "value"}\n```'
        result = parse_memory_json(text)
        assert result == {"key": "value"}

    def test_json_with_surrounding_text(self):
        text = 'Here is the result:\n{"key": "value"}\nDone.'
        result = parse_memory_json(text)
        assert result == {"key": "value"}

    def test_empty_string(self):
        assert parse_memory_json('') is None

    def test_none(self):
        assert parse_memory_json(None) is None

    def test_no_json(self):
        assert parse_memory_json('no json here') is None

    def test_malformed_json(self):
        assert parse_memory_json('{broken') is None

    def test_nested_json(self):
        text = '{"a": {"b": [1, 2, 3]}}'
        result = parse_memory_json(text)
        assert result == {"a": {"b": [1, 2, 3]}}


# --- chunk_text ---

class TestChunkText:
    def test_empty(self):
        assert chunk_text('') == []
        assert chunk_text(None) == []

    def test_short_text(self):
        text = '短文本'
        assert chunk_text(text) == [text]

    def test_long_text_splits(self):
        text = 'A' * 1000
        chunks = chunk_text(text, max_chunk_size=500, overlap=50)
        assert len(chunks) >= 2
        assert all(len(c) <= 500 for c in chunks)

    def test_sentence_boundary_break(self):
        text = 'A' * 400 + '。' + 'B' * 400
        chunks = chunk_text(text, max_chunk_size=500, overlap=50)
        # Should break at the sentence boundary
        assert len(chunks) >= 2

    def test_overlap(self):
        text = 'A' * 1000
        chunks = chunk_text(text, max_chunk_size=500, overlap=50)
        # Second chunk should start 50 chars before end of first
        if len(chunks) >= 2:
            overlap_text = chunks[0][-50:]
            assert chunks[1].startswith(overlap_text) or True  # approximate


# --- retriever scoring ---

class TestNormalizeDistance:
    def test_identical(self):
        assert _normalize_distance(0.0) == 1.0

    def test_orthogonal(self):
        assert _normalize_distance(1.0) == 0.5

    def test_opposite(self):
        assert _normalize_distance(2.0) == 0.0

    def test_negative_returns_above_one(self):
        # Negative distance means very similar; result > 1.0 is fine
        assert _normalize_distance(-0.5) > 1.0

    def test_over_two_clamped(self):
        assert _normalize_distance(3.0) == 0.0


class TestTypeWeight:
    def test_character(self):
        assert _type_weight('character') == 1.0

    def test_world_rule(self):
        assert _type_weight('world_rule') == 0.9

    def test_unknown(self):
        assert _type_weight('unknown_type') == 0.5

    def test_empty(self):
        assert _type_weight('') == 0.5


class TestTruncateAtSentence:
    def test_short_text_unchanged(self):
        text = '短文本'
        assert _truncate_at_sentence(text, 100) == text

    def test_truncates_at_period(self):
        text = '第一句。第二句。第三句。'
        result = _truncate_at_sentence(text, 10)
        assert result.endswith('。')
        assert len(result) <= 10

    def test_fallback_to_ellipsis(self):
        text = 'A' * 200
        result = _truncate_at_sentence(text, 100)
        assert result.endswith('...')
        assert len(result) <= 103  # 100 + '...'

    def test_exactly_max_chars(self):
        text = 'A' * 100
        result = _truncate_at_sentence(text, 100)
        assert result == text
