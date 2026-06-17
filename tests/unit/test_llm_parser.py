"""Unit tests for _parse_llm_response in app.ingest.extractor."""
import pytest
from app.ingest.extractor import _parse_llm_response


class TestParseLlmResponse:

    def test_plain_json_object(self):
        raw = '{"summary": "Handles payments.", "rules": [{"title": "R1", "definition": "D1", "confidence": 0.9}]}'
        rules, summary = _parse_llm_response(raw)
        assert len(rules) == 1
        assert rules[0]["title"] == "R1"
        assert summary == "Handles payments."

    def test_markdown_json_fence(self):
        raw = '```json\n{"rules": [{"title": "R2", "definition": "D2", "confidence": 0.8}]}\n```'
        rules, summary = _parse_llm_response(raw)
        assert len(rules) == 1
        assert rules[0]["title"] == "R2"
        assert summary is None

    def test_markdown_plain_fence(self):
        raw = '```\n{"rules": [{"title": "R3", "definition": "D3", "confidence": 0.7}]}\n```'
        rules, summary = _parse_llm_response(raw)
        assert len(rules) == 1

    def test_multiple_rules(self):
        raw = '{"rules": [{"title": "A"}, {"title": "B"}, {"title": "C"}]}'
        rules, summary = _parse_llm_response(raw)
        assert len(rules) == 3
        assert summary is None

    def test_empty_rules_list(self):
        raw = '{"summary": "Auth module.", "rules": []}'
        rules, summary = _parse_llm_response(raw)
        assert rules == []
        assert summary == "Auth module."

    def test_invalid_json_returns_empty(self):
        rules, summary = _parse_llm_response("this is not json at all")
        assert rules == []
        assert summary is None

    def test_missing_rules_key_returns_empty(self):
        rules, summary = _parse_llm_response('{"data": [{"title": "X"}]}')
        assert rules == []
        assert summary is None

    def test_empty_string_returns_empty(self):
        rules, summary = _parse_llm_response("")
        assert rules == []
        assert summary is None

    def test_whitespace_only_returns_empty(self):
        rules, summary = _parse_llm_response("   \n  ")
        assert rules == []
        assert summary is None
