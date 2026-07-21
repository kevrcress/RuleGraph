"""Unit tests verifying the config-driven LLM request timeout is propagated.

Phase 1 of the resumable-ingest-pipeline plan: `extract_rules` must issue the
Anthropic call with an explicit timeout sourced from config (default 300s), and a
raised timeout must surface as `ExtractionResult.error` (caught by the per-file
`except` path in batch_pipeline's sequential loop).
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import anthropic
import pytest

from app.config import settings
from app.ingest import extractor
from app.ingest.extractor import _get_client, extract_rules


class TestTimeoutConstructor:
    """The AsyncAnthropic constructor must receive the timeout kwarg."""

    def test_get_client_passes_timeout_direct_key(self):
        with patch.object(extractor.anthropic, "AsyncAnthropic") as mock_ctor:
            _get_client("sk-test", base_url="", timeout=42.0)
        _, kwargs = mock_ctor.call_args
        assert kwargs["timeout"] == 42.0

    def test_get_client_passes_timeout_proxy_branch(self):
        with patch.object(extractor.anthropic, "AsyncAnthropic") as mock_ctor:
            _get_client("sk-test", base_url="http://localhost:4000", timeout=99.0)
        _, kwargs = mock_ctor.call_args
        assert kwargs["timeout"] == 99.0
        assert kwargs["base_url"] == "http://localhost:4000"

    def test_real_sdk_accepts_timeout_kwarg(self):
        """Guard against an SDK that silently ignores the constructor timeout."""
        client = anthropic.AsyncAnthropic(api_key="sk-test", timeout=123.0)
        # The SDK stores the constructor timeout on the client.
        assert client.timeout == 123.0


class TestTimeoutFromConfig:
    """extract_rules (db=None) sources the timeout from settings and passes it through."""

    @pytest.mark.asyncio
    async def test_legacy_path_uses_config_timeout(self):
        extractor._client = None  # force a fresh legacy client build
        captured: dict[str, object] = {}

        def fake_get_client(api_key, base_url="", timeout=None):
            captured["timeout"] = timeout
            mock_client = MagicMock()
            resp = MagicMock()
            resp.content = [MagicMock(text='{"summary": "s", "rules": []}')]
            mock_client.messages.create = AsyncMock(return_value=resp)
            return mock_client

        with patch.object(extractor, "_get_client", side_effect=fake_get_client), \
                patch.object(settings, "anthropic_api_key", "sk-test"), \
                patch.object(settings, "llm_request_timeout_seconds", 300):
            result = await extract_rules("print('hi')", complexity=0.1, db=None)

        assert result.error is None
        assert captured["timeout"] == 300
        extractor._client = None


class TestLegacyClientRebuildsOnTimeoutChange:
    """`_ensure_legacy_client` must rebuild when the requested timeout changes.

    Regression guard: the process-global client previously pinned the first caller's
    timeout forever, silently dropping later (e.g. admin-tuned) values.
    """

    def test_rebuilds_when_timeout_differs_and_caches_when_same(self):
        from app.ingest.extractor import _ensure_legacy_client

        extractor._client = None
        extractor._client_timeout = None
        builds: list[float | None] = []

        def fake_get_client(api_key, base_url="", timeout=None):
            builds.append(timeout)
            return MagicMock()

        with patch.object(extractor, "_get_client", side_effect=fake_get_client), \
                patch.object(settings, "anthropic_api_key", "sk-test"):
            c1 = _ensure_legacy_client(timeout=300.0)
            c2 = _ensure_legacy_client(timeout=300.0)   # same → cached, no rebuild
            c3 = _ensure_legacy_client(timeout=30.0)     # changed → rebuild

        assert builds == [300.0, 30.0]
        assert c1 is c2
        assert c3 is not c2
        extractor._client = None
        extractor._client_timeout = None


class TestTimeoutSurfacesAsError:
    """A raised APITimeoutError must become ExtractionResult.error, not propagate."""

    @pytest.mark.asyncio
    async def test_timeout_becomes_extraction_error(self):
        extractor._client = None
        timeout_exc = anthropic.APITimeoutError(request=MagicMock())

        def fake_get_client(api_key, base_url="", timeout=None):
            mock_client = MagicMock()
            mock_client.messages.create = AsyncMock(side_effect=timeout_exc)
            return mock_client

        with patch.object(extractor, "_get_client", side_effect=fake_get_client), \
                patch.object(settings, "anthropic_api_key", "sk-test"):
            result = await extract_rules("print('hi')", complexity=0.1, db=None)

        assert result.rules == []
        assert result.error is not None
        extractor._client = None
