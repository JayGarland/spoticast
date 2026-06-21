"""Gemini TTS — multi-speaker dialogue synthesis via Vertex AI (ADC auth)."""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field

from google import genai
from google.genai import types

from resonova.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Quota error classification
# ---------------------------------------------------------------------------

class GeminiTTSQuotaError(Exception):
    """Raised when Gemini TTS returns a 429 / RESOURCE_EXHAUSTED quota error."""

    def __init__(self, code: str, model: str, retry_after_seconds: int | None, message: str):
        super().__init__(message)
        self.code = code
        self.model = model
        self.retry_after_seconds = retry_after_seconds
        self.quota_message = message


def format_duration(seconds: int) -> str:
    """Format a duration in seconds as a human-readable string."""
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    mins = minutes % 60
    if mins == 0:
        return f"{hours}h"
    return f"{hours}h {mins}m"


def _parse_quota_error(exc: Exception) -> dict | None:
    """
    Classify a Gemini API exception.

    Returns a structured dict if the exception is a TTS quota exhaustion error
    (RESOURCE_EXHAUSTED / 429 / QuotaFailure), or None for unrelated errors.
    """
    exc_str = str(exc)
    exc_type = type(exc).__name__

    # status_code attribute (google-genai ClientError) or gRPC code
    status_code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    http_code = getattr(exc, "http_status", None)

    is_quota = (
        "RESOURCE_EXHAUSTED" in exc_str
        or "ResourceExhausted" in exc_type
        or "QuotaFailure" in exc_str
        or status_code == 429
        or http_code == 429
        or exc_str[:60].startswith("429")
    )

    if not is_quota:
        return None

    # Parse retry delay — REST API returns "retryDelay": "31678s" in JSON details
    retry_after_seconds: int | None = None
    m = re.search(r"['\"]retryDelay['\"]\s*:\s*['\"](\d+)s['\"]", exc_str)
    if m:
        retry_after_seconds = int(m.group(1))
    else:
        # Plain-text fallbacks: "retryDelay ~= 8h47m" or "Please retry in 8h47m58s"
        m = re.search(r"(?:retryDelay|retry in)[^0-9\n]*?(\d+)h(\d+)m", exc_str, re.IGNORECASE)
        if m:
            retry_after_seconds = int(m.group(1)) * 3600 + int(m.group(2)) * 60
        else:
            m = re.search(r"(?:retryDelay|retry in)[^0-9\n]*?(\d+)s\b", exc_str, re.IGNORECASE)
            if m:
                retry_after_seconds = int(m.group(1))

    # Try to extract the exact model name from the error body
    model = settings.gemini_tts_model
    m_model = re.search(r'"model"\s*:\s*"([^"]+)"', exc_str)
    if not m_model:
        m_model = re.search(r"'model'\s*:\s*'([^']+)'", exc_str)
    if not m_model:
        m_model = re.search(r"\bmodel[:\s]+([a-z0-9\-\.]+tts[a-z0-9\-\.]*)", exc_str, re.IGNORECASE)
    if m_model:
        model = m_model.group(1)

    if retry_after_seconds is not None:
        wait_str = format_duration(retry_after_seconds)
        message = (
            f"Generation paused: Gemini TTS quota exhausted (model: {model}). "
            f"Retry after about {wait_str}. "
            f"Generated segments so far are saved."
        )
    else:
        message = (
            f"Generation paused: Gemini TTS quota exhausted (model: {model}). "
            f"The daily limit has been reached — try again later. "
            f"Generated segments so far are saved."
        )

    return {
        "code": "tts_quota_exhausted",
        "model": model,
        "retry_after_seconds": retry_after_seconds,
        "message": message,
    }

# Speaker name and voice for each host role.
# Charon (Informative) suits the analytical HOST_A; Aoede (Breezy) fits the intuitive HOST_B.
_VOICE_MAP = {
    "HOST_A": ("Alex", "Charon"),
    "HOST_B": ("Sam", "Aoede"),
}


# ---------------------------------------------------------------------------
# TTS resource pool with per-resource cooldown tracking
# ---------------------------------------------------------------------------

@dataclass
class _TtsResource:
    """One TTS API resource (Google project/key) with its own quota cooldown."""
    label: str
    client_kwargs: dict = field(repr=False)
    _cooldown_until: float = field(default=0.0, repr=False)

    def is_cooling(self) -> bool:
        """Return True if this resource is still within a quota cooldown window."""
        return time.monotonic() < self._cooldown_until

    def set_cooldown(self, retry_after_seconds: int | None) -> None:
        """Mark this resource as quota-exhausted for the given duration."""
        secs = retry_after_seconds if (retry_after_seconds and retry_after_seconds > 0) else 3600
        self._cooldown_until = time.monotonic() + secs

    def cooldown_remaining(self) -> float:
        """Seconds until this resource's cooldown expires (0.0 if not cooling)."""
        return max(0.0, self._cooldown_until - time.monotonic())


_tts_resources: list[_TtsResource] | None = None


def _build_tts_resources() -> list[_TtsResource]:
    """Build the ordered TTS resource list from config (called once, lazily)."""
    resources: list[_TtsResource] = []

    # Primary resource: GEMINI_TTS_API_KEY overrides GEMINI_API_KEY for TTS only.
    if settings.gemini_tts_api_key:
        primary_kwargs: dict = {"api_key": settings.gemini_tts_api_key}
    elif settings.gemini_api_key:
        primary_kwargs = {"api_key": settings.gemini_api_key}
    else:
        import google.auth
        project = settings.google_cloud_project
        if not project:
            _, project = google.auth.default()
        # TTS models require a regional endpoint, not "global"
        primary_kwargs = {"vertexai": True, "project": project, "location": "us-central1"}

    resources.append(_TtsResource(label="primary", client_kwargs=primary_kwargs))

    # Backup resources: each must be from a SEPARATE Google project for independent quota.
    if settings.gemini_tts_backup_api_keys:
        backup_num = 1
        for raw_key in settings.gemini_tts_backup_api_keys.split(","):
            key = raw_key.strip()
            if not key:
                continue
            resources.append(_TtsResource(
                label=f"backup_{backup_num}",
                client_kwargs={"api_key": key},
            ))
            backup_num += 1

    return resources


def _get_tts_resources() -> list[_TtsResource]:
    """Return the module-level TTS resource pool, initialising it on first call."""
    global _tts_resources
    if _tts_resources is not None:
        return _tts_resources
    _tts_resources = _build_tts_resources()
    return _tts_resources


async def synthesize_dialogue(lines: list[dict]) -> bytes:
    """
    Synthesize a full multi-speaker dialogue in one API call.

    Tries resources in order (primary, then backups). On quota exhaustion,
    marks that resource as cooling and continues to the next. When all
    resources are exhausted or cooling, raises GeminiTTSQuotaError so the
    caller's graceful-failure path can run.

    Non-quota errors surface immediately without trying backup resources.

    Returns raw PCM bytes: 16-bit signed, 24kHz, mono.
    """
    # Format the dialogue so the model knows which speaker says each line.
    # Speaker names must match the keys in speaker_voice_configs below.
    dialogue_parts = []
    for line in lines:
        name, _ = _VOICE_MAP.get(line["host"], _VOICE_MAP["HOST_A"])
        dialogue_parts.append(f"{name}: {line['text']}")

    # Collect the unique speaker names present in this dialogue block
    speakers_present = sorted({_VOICE_MAP[l["host"]][0] for l in lines if l["host"] in _VOICE_MAP})
    speaker_list = " and ".join(speakers_present)
    # Style direction matters a lot for naturalness — without it the model defaults
    # to a clean broadcast voice with long pauses and even pacing between speakers.
    prompt = (
        f"Audio Profile: Alex is warm, enthusiastic, quick to react — voice has energy "
        f"and forward momentum. Sam is more measured but engaged, occasionally dry. "
        f"Both are casual and natural, NOT broadcast presenters.\n\n"
        f"Scene: Two friends who know music well, talking in a relaxed setting. "
        f"Rapid turn-taking, short gaps between speakers, occasional laugh or pause.\n\n"
        f"Director's Notes: Respect any [pause], [laughs], [excited], [thoughtful], "
        f"[amused] markers embedded in the text — these are performance cues, not spoken words. "
        f"Keep the overall energy conversational and alive.\n\n"
        + "\n".join(dialogue_parts)
    )

    speaker_voice_configs = [
        types.SpeakerVoiceConfig(
            speaker=name,
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
            ),
        )
        for _host, (name, voice) in _VOICE_MAP.items()
    ]

    generate_config = types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                speaker_voice_configs=speaker_voice_configs,
            ),
        ),
    )

    resources = _get_tts_resources()
    last_quota_info: dict | None = None

    for resource in resources:
        if resource.is_cooling():
            # This resource's per-project quota cooldown is still active — skip it
            continue

        client = genai.Client(**resource.client_kwargs)
        try:
            response = await client.aio.models.generate_content(
                model=settings.gemini_tts_model,
                contents=prompt,
                config=generate_config,
            )
            return response.candidates[0].content.parts[0].inline_data.data

        except Exception as exc:
            quota_info = _parse_quota_error(exc)
            if quota_info:
                resource.set_cooldown(quota_info["retry_after_seconds"])
                last_quota_info = quota_info
                logger.warning(
                    "TTS resource %s quota exhausted (model=%s); trying next resource.",
                    resource.label,
                    quota_info["model"],
                )
                continue
            # Non-quota errors (network, auth, payload) surface immediately.
            # Do not silently route to backups for arbitrary failures.
            raise

    # All resources are either already cooling or just became quota-exhausted.
    # Report the earliest next-available time so the caller can surface it.
    earliest_remaining: int | None = None
    for resource in resources:
        remaining = int(resource.cooldown_remaining())
        if remaining > 0:
            if earliest_remaining is None or remaining < earliest_remaining:
                earliest_remaining = remaining

    model = last_quota_info["model"] if last_quota_info else settings.gemini_tts_model

    if earliest_remaining is not None:
        wait_str = format_duration(earliest_remaining)
        message = (
            f"Generation paused: all configured Gemini TTS resources are exhausted "
            f"(model: {model}). Earliest retry in about {wait_str}. "
            f"Generated segments so far are saved."
        )
    else:
        message = (
            f"Generation paused: all configured Gemini TTS resources are exhausted "
            f"(model: {model}). Try again later. "
            f"Generated segments so far are saved."
        )

    raise GeminiTTSQuotaError(
        code="tts_quota_exhausted",
        model=model,
        retry_after_seconds=earliest_remaining,
        message=message,
    )
