"""Unit tests for _parse_llm_response in app.ingest.extractor."""
import pytest
from app.ingest.extractor import _parse_llm_response


class TestParseLlmResponse:

    def test_plain_json_object(self):
        raw = '{"rules": [{"title": "R1", "definition": "D1", "confidence": 0.9}]}'
        result = _parse_llm_response(raw)
        assert len(result) == 1
        assert result[0]["title"] == "R1"

    def test_markdown_json_fence(self):
        raw = '```json\n{"rules": [{"title": "R2", "definition": "D2", "confidence": 0.8}]}\n```'
        result = _parse_llm_response(raw)
        assert len(result) == 1
        assert result[0]["title"] == "R2"

    def test_markdown_plain_fence(self):
        raw = '```\n{"rules": [{"title": "R3", "definition": "D3", "confidence": 0.7}]}\n```'
        result = _parse_llm_response(raw)
        assert len(result) == 1

    def test_multiple_rules(self):
        raw = '{"rules": [{"title": "A"}, {"title": "B"}, {"title": "C"}]}'
        result = _parse_llm_response(raw)
        assert len(result) == 3

    def test_empty_rules_list(self):
        raw = '{"rules": []}'
        result = _parse_llm_response(raw)
        assert result == []

    def test_invalid_json_returns_empty(self):
        result = _parse_llm_response("this is not json at all")
        assert result == []

    def test_missing_rules_key_returns_empty(self):
        result = _parse_llm_response('{"data": [{"title": "X"}]}')
        assert result == []

    def test_empty_string_returns_empty(self):
        result = _parse_llm_response("")
        assert result == []

    def test_whitespace_only_returns_empty(self):
        result = _parse_llm_response("   \n  ")
        assert result == []
