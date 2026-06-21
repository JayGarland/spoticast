"""
Focused tests for Gemini TTS backup resource failover.

Run with:
    uv run python tests/test_tts_failover.py

No real API calls are made — all Gemini client calls are mocked.
"""
from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Test 1: Backup key parsing — trim whitespace, ignore empties, preserve order
# ---------------------------------------------------------------------------

def _test_backup_key_parsing():
    """_build_tts_resources must trim whitespace, drop empties, and preserve order."""
    import resonova.api.tts as tts_mod
    from resonova.api.tts import _TtsResource

    raw = " key_alpha , key_beta ,, key_gamma , "

    # Simulate the parsing logic used in _build_tts_resources
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    assert keys == ["key_alpha", "key_beta", "key_gamma"], f"Unexpected keys: {keys}"
    assert len(keys) == 3, "Empty entries must be ignored"

    # Verify _build_tts_resources produces correctly-labelled resources in order
    from unittest.mock import patch as _patch
    from resonova.config import settings

    with _patch.object(settings, "gemini_api_key", "primary_key"), \
         _patch.object(settings, "gemini_tts_api_key", None), \
         _patch.object(settings, "gemini_tts_backup_api_keys", raw):
        resources = tts_mod._build_tts_resources()

    assert resources[0].label == "primary"
    assert resources[1].label == "backup_1"
    assert resources[2].label == "backup_2"
    assert resources[3].label == "backup_3"
    assert len(resources) == 4

    # Keys must NOT appear in labels or repr output (labels use ordinal names only)
    for res in resources[1:]:
        assert "key_alpha" not in res.label
        assert "key_beta" not in res.label
        assert "key_gamma" not in res.label
        assert "key_alpha" not in repr(res)
        assert "key_beta" not in repr(res)
        assert "key_gamma" not in repr(res)

    print("  backup_key_parsing ✓")


# ---------------------------------------------------------------------------
# Test 2: Primary quota failure → backup success
# ---------------------------------------------------------------------------

def _test_primary_quota_backup_success():
    """Primary marks itself cooling; backup is tried and succeeds; no error raised."""
    import resonova.api.tts as tts_mod
    from resonova.api.tts import _TtsResource, GeminiTTSQuotaError

    quota_exc = Exception('429 RESOURCE_EXHAUSTED "retryDelay": "3600s"')
    success_bytes = b"fake_audio_pcm"

    primary = _TtsResource(label="primary", client_kwargs={"api_key": "key_p"})
    backup = _TtsResource(label="backup_1", client_kwargs={"api_key": "key_b"})

    call_count = [0]

    async def fake_generate(**_kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            raise quota_exc
        mock_resp = MagicMock()
        mock_resp.candidates[0].content.parts[0].inline_data.data = success_bytes
        return mock_resp

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(side_effect=fake_generate)

    with patch.object(tts_mod, "_tts_resources", [primary, backup]), \
         patch("resonova.api.tts.genai.Client", return_value=mock_client):
        lines = [{"host": "HOST_A", "text": "Hello world"}]
        result = asyncio.run(tts_mod.synthesize_dialogue(lines))

    assert result == success_bytes, "Should return backup audio bytes"
    assert primary.is_cooling(), "Primary must be marked cooling after quota error"
    assert not backup.is_cooling(), "Backup must NOT be marked cooling after success"
    assert call_count[0] == 2, f"Expected 2 API calls (primary fail + backup success), got {call_count[0]}"

    print("  primary_quota_backup_success ✓")


# ---------------------------------------------------------------------------
# Test 3: All resources quota-fail → GeminiTTSQuotaError raised
# ---------------------------------------------------------------------------

def _test_all_resources_exhausted():
    """When every resource hits quota, GeminiTTSQuotaError is raised with earliest retry-after."""
    import resonova.api.tts as tts_mod
    from resonova.api.tts import _TtsResource, GeminiTTSQuotaError

    quota_exc = Exception('429 RESOURCE_EXHAUSTED "retryDelay": "3600s"')

    primary = _TtsResource(label="primary", client_kwargs={"api_key": "key_p"})
    backup = _TtsResource(label="backup_1", client_kwargs={"api_key": "key_b"})

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(side_effect=quota_exc)

    raised: GeminiTTSQuotaError | None = None
    with patch.object(tts_mod, "_tts_resources", [primary, backup]), \
         patch("resonova.api.tts.genai.Client", return_value=mock_client):
        lines = [{"host": "HOST_A", "text": "Hello"}]
        try:
            asyncio.run(tts_mod.synthesize_dialogue(lines))
        except GeminiTTSQuotaError as exc:
            raised = exc

    assert raised is not None, "GeminiTTSQuotaError must be raised when all resources fail"
    assert raised.code == "tts_quota_exhausted"
    assert raised.retry_after_seconds is not None, "retry_after_seconds should be set from cooldown"
    assert raised.retry_after_seconds > 0

    # The error message must mention all resources exhausted
    assert "all configured" in raised.quota_message.lower(), (
        f"Message must say all resources exhausted; got: {raised.quota_message}"
    )

    # No key values must appear in message or exception string
    assert "key_p" not in str(raised)
    assert "key_b" not in str(raised)
    assert "key_p" not in raised.quota_message
    assert "key_b" not in raised.quota_message

    # Both resources must now be cooling
    assert primary.is_cooling(), "Primary must be cooling"
    assert backup.is_cooling(), "Backup must be cooling"

    print("  all_resources_exhausted ✓")


# ---------------------------------------------------------------------------
# Test 4: Non-quota error does NOT try backup resources
# ---------------------------------------------------------------------------

def _test_non_quota_error_no_backup():
    """A non-quota API error must surface immediately; backups must not be tried."""
    import resonova.api.tts as tts_mod
    from resonova.api.tts import _TtsResource, GeminiTTSQuotaError

    # 503 is not a quota error — _parse_quota_error returns None for it
    non_quota_exc = Exception("503 Service Unavailable")

    primary = _TtsResource(label="primary", client_kwargs={"api_key": "key_p"})
    backup = _TtsResource(label="backup_1", client_kwargs={"api_key": "key_b"})

    call_count = [0]

    async def fake_generate(**_kwargs):
        call_count[0] += 1
        raise non_quota_exc

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(side_effect=fake_generate)

    raised: Exception | None = None
    with patch.object(tts_mod, "_tts_resources", [primary, backup]), \
         patch("resonova.api.tts.genai.Client", return_value=mock_client):
        lines = [{"host": "HOST_A", "text": "Hello"}]
        try:
            asyncio.run(tts_mod.synthesize_dialogue(lines))
        except GeminiTTSQuotaError:
            raise AssertionError("Must NOT raise GeminiTTSQuotaError for a non-quota error")
        except Exception as exc:
            raised = exc

    assert raised is not None, "Non-quota exception must be re-raised"
    assert str(raised) == "503 Service Unavailable", f"Unexpected exception: {raised}"

    # Only one API call made — backup was never tried
    assert call_count[0] == 1, (
        f"Non-quota error must not trigger backup; expected 1 call, got {call_count[0]}"
    )

    # Primary must NOT be marked cooling (cooldown is quota-specific)
    assert not primary.is_cooling(), "Primary must NOT be cooling after a non-quota error"

    print("  non_quota_error_no_backup ✓")


# ---------------------------------------------------------------------------
# Test 5: Already-cooling resource is skipped, backup is tried first
# ---------------------------------------------------------------------------

def _test_cooling_resource_is_skipped():
    """A resource that is already cooling must be skipped without an API call."""
    import resonova.api.tts as tts_mod
    from resonova.api.tts import _TtsResource

    success_bytes = b"backup_audio"

    primary = _TtsResource(label="primary", client_kwargs={"api_key": "key_p"})
    backup = _TtsResource(label="backup_1", client_kwargs={"api_key": "key_b"})

    # Pre-cool the primary resource
    primary.set_cooldown(3600)
    assert primary.is_cooling()

    call_count = [0]

    async def fake_generate(**_kwargs):
        call_count[0] += 1
        mock_resp = MagicMock()
        mock_resp.candidates[0].content.parts[0].inline_data.data = success_bytes
        return mock_resp

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(side_effect=fake_generate)

    with patch.object(tts_mod, "_tts_resources", [primary, backup]), \
         patch("resonova.api.tts.genai.Client", return_value=mock_client):
        lines = [{"host": "HOST_A", "text": "Hello"}]
        result = asyncio.run(tts_mod.synthesize_dialogue(lines))

    assert result == success_bytes
    # Only one call — the cooling primary was skipped entirely
    assert call_count[0] == 1, f"Expected 1 call (backup only), got {call_count[0]}"

    print("  cooling_resource_is_skipped ✓")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _run_tests() -> None:
    _test_backup_key_parsing()
    _test_primary_quota_backup_success()
    _test_all_resources_exhausted()
    _test_non_quota_error_no_backup()
    _test_cooling_resource_is_skipped()
    print("All TTS failover tests passed ✓")


if __name__ == "__main__":
    _run_tests()
