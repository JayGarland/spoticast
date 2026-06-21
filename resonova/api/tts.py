"""Gemini TTS — multi-speaker dialogue synthesis via Vertex AI (ADC auth)."""

from __future__ import annotations

import re

from google import genai
from google.genai import types

from resonova.config import settings


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

_client_kwargs: dict | None = None


def _resolve_client_kwargs() -> dict:
    global _client_kwargs
    if _client_kwargs is not None:
        return _client_kwargs
    if settings.gemini_api_key:
        _client_kwargs = {"api_key": settings.gemini_api_key}
    else:
        import google.auth
        project = settings.google_cloud_project
        if not project:
            _, project = google.auth.default()
        # TTS models require a regional endpoint, not "global"
        _client_kwargs = {"vertexai": True, "project": project, "location": "us-central1"}
    return _client_kwargs


def _new_client() -> genai.Client:
    """Return a fresh genai.Client each call to avoid httpx closed-client errors."""
    return genai.Client(**_resolve_client_kwargs())


async def synthesize_dialogue(lines: list[dict]) -> bytes:
    """
    Synthesize a full multi-speaker dialogue in one API call.

    Returns raw PCM bytes: 16-bit signed, 24kHz, mono.
    The model handles natural pacing and speaker transitions.
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

    client = _new_client()
    try:
        response = await client.aio.models.generate_content(
            model=settings.gemini_tts_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                        speaker_voice_configs=speaker_voice_configs,
                    ),
                ),
            ),
        )
    except Exception as exc:
        quota_info = _parse_quota_error(exc)
        if quota_info:
            raise GeminiTTSQuotaError(**quota_info) from exc
        raise

    return response.candidates[0].content.parts[0].inline_data.data
