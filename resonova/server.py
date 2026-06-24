"""FastAPI application — routes, background jobs, SSE progress streaming."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from uuid import uuid4
try:
    from uuid import uuid7  # type: ignore[attr-defined]  # Python 3.14+
except ImportError:
    from uuid_extensions import uuid7

logger = logging.getLogger(__name__)
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from resonova.config import settings
from resonova import episodes as episodes_store
from resonova import profile as profile_store
from resonova import variety as variety_store
from resonova.api import audio as audio_api
from resonova.api import gemini as gemini_api
from resonova.api import lastfm as lastfm_api
from resonova.api import research as research_api
from resonova.api import spotify as spotify_api
from resonova.api import tts as tts_api
from resonova.api.tts import GeminiTTSQuotaError

app = FastAPI(title="Resonova")

# Serve generated audio files
_GENERATED_DIR = Path("generated")
_GENERATED_DIR.mkdir(exist_ok=True)
app.mount("/audio", StaticFiles(directory=str(_GENERATED_DIR)), name="audio")

# Serve frontend static files
_WEB_DIR = Path(__file__).parent / "web"
app.mount("/web", StaticFiles(directory=str(_WEB_DIR)), name="web")

from starlette.middleware.sessions import SessionMiddleware
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret_key)


# ---------------------------------------------------------------------------
# Cast summary extraction for prior-cast context injection
# ---------------------------------------------------------------------------

def _extract_cast_summary(script: dict, episode_name: str) -> str:
    """
    Build a lightweight text summary of a generated script for prior-cast injection.

    Script schema: intro and each track's commentary are [{host, text}] arrays.
    Extracts: episode title, intro opening sentence, first sentence of each track's
    commentary (capped to 6 tracks). Hard-capped at 700 chars to keep the prompt lean.
    """
    def _join_turns(turns: object) -> str:
        if not isinstance(turns, list):
            return ""
        return " ".join(t.get("text", "") for t in turns if isinstance(t, dict))

    parts: list[str] = [f'Episode title: "{episode_name}"']

    intro_text = _join_turns(script.get("intro") or []).strip()
    if intro_text:
        first_sentence = intro_text.split(".")[0].strip()
        if first_sentence:
            parts.append(f"Intro framing: {first_sentence}.")

    for seg in (script.get("tracks") or [])[:6]:
        if not isinstance(seg, dict):
            continue
        commentary = _join_turns(seg.get("commentary") or []).strip()
        if commentary:
            first = commentary.split(".")[0].strip()
            label = seg.get("track_uri", "track")
            if first:
                parts.append(f"{label}: {first}.")

    return " | ".join(parts)[:700]


# ---------------------------------------------------------------------------
# In-memory job state
# ---------------------------------------------------------------------------

class Job:
    def __init__(self, job_id: str, playlist_uri: str):
        self.job_id = job_id
        self.playlist_uri = playlist_uri
        self.playlist_name: str = ""
        self.user_id: str = ""
        self.track_uris: list[str] | None = None
        self.incognito: bool = False
        self.commentary_language: str | None = None
        self.cast_depth: str | None = None
        self.cast_vibe: str | None = None
        self.status: str = "pending"   # pending | running | done | error
        self.events: list[dict] = []
        self.queue: list[dict] | None = None
        self.error: str | None = None
        self._event = asyncio.Event()

    def push(self, event_type: str, data: Any):
        self.events.append({"type": event_type, "data": data})
        self._event.set()
        self._event.clear()

    def push_threadsafe(self, loop: asyncio.AbstractEventLoop, event_type: str, data: Any):
        """Thread-safe variant for use from run_in_executor threads."""
        self.events.append({"type": event_type, "data": data})
        loop.call_soon_threadsafe(self._event.set)

    async def wait_for_event(self):
        await self._event.wait()


_jobs: dict[str, Job] = {}


def _format_generation_error(exc: Exception) -> str:
    """Return a user-facing error without hiding the real failing class/status."""
    try:
        from spotipy import SpotifyException
    except ImportError:
        SpotifyException = None  # type: ignore[assignment]

    if SpotifyException is not None and isinstance(exc, SpotifyException):
        status = exc.http_status
        reason = getattr(exc, "reason", None) or getattr(exc, "msg", None) or str(exc)
        if status == 404:
            return "Playlist not found. Make sure it's public (or that you own it) and that the URI is correct."
        if status == 401:
            return "Spotify session expired. Reconnect Spotify, then try again."
        if status == 403:
            return (
                "Spotify denied this request (403). This is usually playlist access, account permissions, "
                "or a restricted Spotify endpoint rather than a stale login. Try a playlist you own; "
                f"details: {reason}"
            )
        return f"Spotify request failed ({status}): {reason}"

    return str(exc)


# ---------------------------------------------------------------------------
# TTS quota cooldown guard (in-process, survives job restarts within a session)
# ---------------------------------------------------------------------------

_tts_cooldown_until: float = 0.0  # Unix timestamp; 0.0 = no active cooldown
_tts_cooldown_model: str | None = None


def _get_tts_cooldown() -> dict | None:
    """Return cooldown info if the quota cooldown is still active, else None."""
    remaining = int(_tts_cooldown_until - time.time())
    if remaining > 0:
        wait_str = tts_api.format_duration(remaining)
        return {
            "code": "tts_quota_exhausted",
            "model": _tts_cooldown_model,
            "retry_after_seconds": remaining,
            "message": (
                f"Gemini TTS quota is still cooling down. "
                f"Try again in about {wait_str}."
            ),
        }
    return None


def _set_tts_cooldown(retry_after_seconds: int | None, model: str | None = None) -> None:
    """Record a cooldown expiry time. Falls back to 1 hour when delay is unknown."""
    global _tts_cooldown_until, _tts_cooldown_model
    secs = retry_after_seconds if (retry_after_seconds and retry_after_seconds > 0) else 3600
    _tts_cooldown_until = time.time() + secs
    _tts_cooldown_model = model
    logger.info("TTS quota cooldown set: %.0fs (until %s)", secs, _tts_cooldown_until)


async def get_current_user(request: Request) -> tuple[str, "spotipy.Spotify"]:
    """Validate session, refresh token if needed, bind per-session Spotify client."""
    token_info = request.session.get("token_info")
    if not token_info:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token_info = spotify_api.refresh_token_if_needed(token_info)
    request.session["token_info"] = token_info
    user_id: str = request.session["user_id"]
    sp = spotify_api.get_client_from_token(token_info)
    spotify_api.set_session_client(sp)
    return user_id, sp


def _select_playlist_tracks_for_episode(tracks: list[Any], playlist_uri: str, user_id: str) -> list[Any]:
    """Return a memory-aware varied episode order from a playlist.

    When a durable taste profile exists, build an artist-affinity set and pass
    it as a soft bias — the order remains non-deterministic but favours the
    listener's known artists.
    """
    profile = profile_store.load_profile(user_id)
    taste_profile = profile.get("taste_profile") or {}

    artists: list[str] = []
    artists.extend(taste_profile.get("top_artists") or [])
    artists.extend(taste_profile.get("saved_library_artists") or [])
    artists.extend(taste_profile.get("followed_artists") or [])

    if artists:
        artist_affinity = {a.lower().strip() for a in artists if a}
        taste = {"artist_affinity": artist_affinity}
    else:
        taste = None  # No profile data → identical to today's behaviour

    return variety_store.select_tracks_for_episode(
        tracks, playlist_uri, settings.max_tracks, user_id=user_id, taste=taste,
    )


async def _auto_refresh_profile_on_connect(user_id: str) -> None:
    """Non-blocking: populate profile from library after connect, if profile is empty."""
    try:
        profile = profile_store.load_profile(user_id)
        spotify_src = profile.get("sources", {}).get("spotify", {})
        if spotify_src.get("connected") and profile_store.profile_has_content(profile):
            return
        loop = asyncio.get_event_loop()
        saved_tracks = await loop.run_in_executor(None, spotify_api.fetch_saved_tracks)
        followed_artists = await loop.run_in_executor(None, spotify_api.fetch_followed_artists)
        profile = profile_store.summarize_library(user_id, saved_tracks, followed_artists, profile)
        profile = profile_store.summarize_saved_casts(user_id, profile)
        profile = profile_store.fold_feedback_into_profile(user_id, profile)
        profile_store.save_profile(user_id, profile)
        logger.info("Auto-refreshed profile for user %s on connect", user_id)
    except Exception as exc:
        logger.warning("Auto-refresh profile on connect failed (non-blocking): %s", exc)




@app.get("/", response_class=HTMLResponse)
async def serve_index():
    html_path = _WEB_DIR / "index.html"
    return HTMLResponse(content=html_path.read_text(), status_code=200)


def _resolve_redirect_uri(request: Request) -> str:
    """Build the redirect_uri from the incoming request's Host header.

    When REDIRECT_URI (redirect_uri_override) is explicitly configured, use it
    directly — no Host-header detection needed.

    Otherwise, tunnel auto-detection: when the incoming Host header indicates a
    known tunnel provider, switch to HTTPS and drop the port — the tunnel handles
    TLS termination and forwards on the standard HTTPS port.

    Supported tunnels (no config change needed):
      - Tailscale Serve / Funnel  → *.ts.net
      - ngrok free / named        → *.ngrok-free.app, *.ngrok.io, *.ngrok.app

    Falls back to the configured default (http://127.0.0.1:8765) for local dev.
    """
    # Explicit override always wins — no Host-header guessing needed.
    if settings.redirect_uri_override:
        return settings.redirect_uri_override

    host = request.headers.get("host", "")
    _TUNNEL_SUFFIXES = (".ts.net", ".ngrok-free.app", ".ngrok.io", ".ngrok.app")
    if any(host.endswith(suffix) for suffix in _TUNNEL_SUFFIXES):
        return f"https://{host}/auth/callback"
    if settings.use_https:
        return f"https://{host}/auth/callback"
    return settings.redirect_uri


@app.get("/auth/spotify")
async def auth_spotify(request: Request):
    url = spotify_api.get_auth_url(_resolve_redirect_uri(request))
    return RedirectResponse(url)


@app.get("/auth/callback")
async def auth_callback(request: Request, code: str | None = None, error: str | None = None):
    if error or not code:
        return HTMLResponse(f"<h1>Auth failed</h1><p>{error}</p>", status_code=400)
    token_info = spotify_api.handle_callback_for_session(code, _resolve_redirect_uri(request))
    sp = spotify_api.get_client_from_token(token_info)
    spotify_api.set_session_client(sp)
    loop = asyncio.get_event_loop()
    me = await loop.run_in_executor(None, sp.me)
    user_id: str = me["id"]
    allowed_raw = settings.allowed_spotify_user_ids.strip()
    if allowed_raw:
        allowed_ids = {uid.strip() for uid in allowed_raw.split(",") if uid.strip()}
        if user_id not in allowed_ids:
            return HTMLResponse(
                "<h1>Not invited</h1><p>This beta is private. Ask the host to add you.</p>",
                status_code=403,
            )
    request.session["token_info"] = token_info
    request.session["user_id"] = user_id
    asyncio.create_task(_auto_refresh_profile_on_connect(user_id))
    return RedirectResponse("/?auth=success")


@app.get("/auth/token")
async def auth_token(request: Request):
    token_info = request.session.get("token_info")
    if token_info is None:
        return JSONResponse({"token": None, "authenticated": False})
    return JSONResponse({"token": token_info.get("access_token"), "authenticated": True})


@app.get("/auth/lastfm/status")
async def lastfm_status():
    return JSONResponse(lastfm_api.get_status())


class LastFMConnectRequest(BaseModel):
    username: str


@app.post("/auth/lastfm/connect")
async def lastfm_connect(req: LastFMConnectRequest):
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, lastfm_api.connect, req.username.strip())
        return JSONResponse(result)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/auth/lastfm/disconnect")
async def lastfm_disconnect():
    lastfm_api.disconnect()
    return JSONResponse({"connected": False})


@app.get("/api/recent")
async def api_recent(request: Request):
    user_id, sp = await get_current_user(request)
    loop = asyncio.get_event_loop()
    playlists = await loop.run_in_executor(None, spotify_api.fetch_recent_plays)
    return JSONResponse({"playlists": playlists})



@app.get("/api/playlists")
async def api_playlists(request: Request, limit: int = 50, offset: int = 0):
    user_id, sp = await get_current_user(request)
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, lambda: spotify_api.fetch_user_playlists(limit, offset)
    )
    return JSONResponse(result)


@app.get("/api/episodes")
async def api_episodes(request: Request):
    user_id, sp = await get_current_user(request)
    return JSONResponse({"episodes": episodes_store.list_episodes(user_id)})


@app.get("/api/tts-cooldown")
async def api_tts_cooldown():
    """Report active TTS quota cooldown so the client can block immediate retries."""
    info = _get_tts_cooldown()
    if info:
        return JSONResponse({"active": True, **info})
    return JSONResponse({"active": False})


@app.get("/api/episodes/{episode_id}")
async def api_episode(episode_id: str, request: Request):
    user_id, sp = await get_current_user(request)
    try:
        ep = episodes_store.get_episode(user_id, episode_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if ep is None:
        raise HTTPException(status_code=404, detail="Episode not found")
    return JSONResponse(ep)


class RenameEpisodeRequest(BaseModel):
    name: str


@app.patch("/api/episodes/{episode_id}")
async def api_rename_episode(episode_id: str, req: RenameEpisodeRequest, request: Request):
    user_id, sp = await get_current_user(request)
    try:
        updated = episodes_store.rename_episode(user_id, episode_id, req.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if updated is None:
        raise HTTPException(status_code=404, detail="Episode not found")
    return JSONResponse(updated)


@app.delete("/api/episodes/{episode_id}")
async def api_delete_episode(episode_id: str, request: Request):
    user_id, sp = await get_current_user(request)
    try:
        deleted = episodes_store.delete_episode(user_id, episode_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not deleted:
        raise HTTPException(status_code=404, detail="Episode not found")
    return JSONResponse({"deleted": True, "id": episode_id})


class ReplayRequest(BaseModel):
    event: str
    session_id: str
    completed_segments: int = 0
    total_segments: int = 0


@app.post("/api/episodes/{episode_id}/replay")
async def api_replay_episode(episode_id: str, req: ReplayRequest, request: Request):
    """Record a replay start or meaningful-completion event for a saved episode."""
    user_id, sp = await get_current_user(request)
    if req.event not in ("start", "meaningful"):
        raise HTTPException(status_code=400, detail="event must be 'start' or 'meaningful'")
    if not req.session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    if req.completed_segments < 0 or req.total_segments < 0:
        raise HTTPException(status_code=400, detail="segment counts must be non-negative")
    try:
        result = episodes_store.record_replay_event(
            user_id,
            episode_id,
            req.event,
            req.session_id,
            req.completed_segments,
            req.total_segments,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if result == "not_found":
        raise HTTPException(status_code=404, detail="Episode not found")
    return JSONResponse({"ok": True})


@app.get("/api/profile")
async def api_get_profile(request: Request):
    """Return the current listener profile (memory layer)."""
    user_id, sp = await get_current_user(request)
    return JSONResponse(profile_store.load_profile(user_id))


@app.delete("/api/profile")
async def api_delete_profile(request: Request):
    """Reset the listener profile to an empty skeleton; saved casts are untouched."""
    user_id, sp = await get_current_user(request)
    empty = profile_store.reset_profile(user_id)
    return JSONResponse(empty)


class ProfilePatchRequest(BaseModel):
    memory_enabled: bool | None = None
    pin_memory_id: str | None = None
    pin_value: bool | None = None
    delete_memory_id: str | None = None


@app.patch("/api/profile")
async def api_patch_profile(req: ProfilePatchRequest, request: Request):
    """Patch memory_enabled, pin a memory, or delete a memory."""
    user_id, sp = await get_current_user(request)
    profile = profile_store.load_profile(user_id)
    if req.memory_enabled is not None:
        profile = profile_store.set_memory_enabled(profile, req.memory_enabled)
    if req.pin_memory_id is not None:
        pinned = req.pin_value if req.pin_value is not None else True
        profile = profile_store.pin_memory(profile, req.pin_memory_id, pinned)
    if req.delete_memory_id is not None:
        profile = profile_store.delete_memory(profile, req.delete_memory_id)
    profile_store.save_profile(user_id, profile)
    return JSONResponse(profile)


@app.post("/api/profile/refresh")
async def api_profile_refresh(request: Request):
    """Fetch saved tracks + followed artists, update the profile. No cast generated."""
    user_id, sp = await get_current_user(request)
    loop = asyncio.get_event_loop()
    try:
        saved_tracks, followed_artists = await asyncio.gather(
            loop.run_in_executor(None, spotify_api.fetch_saved_tracks),
            loop.run_in_executor(None, spotify_api.fetch_followed_artists),
        )
        profile = profile_store.load_profile(user_id)
        profile = profile_store.summarize_library(user_id, saved_tracks, followed_artists, profile)
        profile = profile_store.summarize_saved_casts(user_id, profile)
        profile = profile_store.fold_feedback_into_profile(user_id, profile)
        profile_store.save_profile(user_id, profile)
        return JSONResponse(profile)
    except Exception as exc:
        logger.exception("Profile refresh failed")
        raise HTTPException(status_code=500, detail=str(exc))


class FeedbackRequest(BaseModel):
    episode_id: str
    segment_index: int | None = None
    verdict: str  # "up" or "down"
    tags: list[str] = []
    note: str | None = None


@app.post("/api/feedback")
async def api_feedback(req: FeedbackRequest, request: Request):
    """Record feedback for an episode and fold into profile preferences."""
    user_id, sp = await get_current_user(request)
    if req.verdict not in ("up", "down"):
        raise HTTPException(status_code=400, detail="verdict must be 'up' or 'down'")
    valid_tags = [t for t in req.tags if t in profile_store.FEEDBACK_TAGS]

    event = {
        "id": str(uuid4()),
        "episode_id": req.episode_id,
        "segment_index": req.segment_index,
        "verdict": req.verdict,
        "tags": valid_tags,
        "note": req.note,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    profile_store.append_feedback(user_id, event)

    # Fold into profile (non-blocking on error)
    try:
        profile = profile_store.load_profile(user_id)
        profile = profile_store.fold_feedback_into_profile(user_id, profile)
        profile_store.save_profile(user_id, profile)
    except Exception as fe:
        logger.warning("Feedback fold failed (non-blocking): %s", fe)

    return JSONResponse({"ok": True, "id": event["id"]})


class GenerateRequest(BaseModel):
    playlist_uri: str | None = None
    track_uris: list[str] | None = None
    incognito: bool = False
    commentary_language: str | None = None
    cast_depth: str | None = None
    cast_vibe: str | None = None


@app.post("/generate")
async def generate(req: GenerateRequest, request: Request):
    user_id, sp = await get_current_user(request)
    if not req.playlist_uri and not req.track_uris:
        raise HTTPException(status_code=400, detail="Provide playlist_uri or track_uris")

    # Block immediate retries while a quota cooldown is known
    cooldown = _get_tts_cooldown()
    if cooldown:
        raise HTTPException(status_code=429, detail=cooldown)

    job_id = str(uuid7())
    source = req.playlist_uri or "track_list"
    job = Job(job_id, source)
    job.user_id = user_id
    job.track_uris = req.track_uris
    job.incognito = req.incognito
    if req.commentary_language:
        job.commentary_language = req.commentary_language.strip()[:40] or None
    _ALLOWED_DEPTHS = {"brief", "balanced", "deep"}
    _ALLOWED_VIBES = {"warm", "witty", "analytical", "late_night", "chill"}
    if req.cast_depth in _ALLOWED_DEPTHS:
        job.cast_depth = req.cast_depth
    if req.cast_vibe in _ALLOWED_VIBES:
        job.cast_vibe = req.cast_vibe
    _jobs[job_id] = job

    # Run generation in background so we can stream progress
    asyncio.create_task(_run_generation(job))

    return {"job_id": job_id}


@app.get("/jobs/{job_id}/status")
async def job_status(job_id: str):
    """Lightweight polling endpoint — fallback when SSE stream is silent."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"status": job.status, "error": job.error}


@app.get("/jobs/{job_id}/stream")
async def job_stream(job_id: str, request: Request):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        sent_index = 0
        while True:
            if await request.is_disconnected():
                break

            # Drain any new events
            while sent_index < len(job.events):
                ev = job.events[sent_index]
                sent_index += 1
                yield {"event": ev["type"], "data": json.dumps(ev["data"])}

            if job.status in ("done", "error"):
                break

            # Wait for new events (with timeout to allow disconnect checks).
            # Send an SSE comment as heartbeat so proxies/tunnels (Tailscale
            # Funnel, Cloudflare Tunnel, etc.) don't buffer the stream into
            # silence and break the connection.
            try:
                await asyncio.wait_for(job.wait_for_event(), timeout=15.0)
            except asyncio.TimeoutError:
                yield {"comment": "heartbeat"}

    return EventSourceResponse(event_generator())


@app.get("/audio/{filename}")
async def serve_audio(filename: str):
    path = _GENERATED_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(str(path), media_type="audio/mpeg")


# ---------------------------------------------------------------------------
# Generation pipeline
# ---------------------------------------------------------------------------

async def _run_generation(job: Job):
    """Background task: fetch data → generate script → synthesize audio → save episode."""
    loop = asyncio.get_event_loop()
    episode_id = job.job_id

    try:
        job.status = "running"
        job.push("progress", {"step": "fetch", "message": "Fetching playlist and user data..."})

        # Fetch tracks — either from a playlist URI or from a direct track list
        _order_fingerprint: str | None = None
        _track_order_preview: list[str] | None = None
        _playlist_selected_uris: list[str] | None = None

        if job.track_uris:
            tracks = await loop.run_in_executor(
                None, spotify_api.fetch_tracks, job.track_uris[:settings.max_tracks]
            )
            job.playlist_name = "Custom tracks"
        else:
            tracks, job.playlist_name = await asyncio.gather(
                loop.run_in_executor(None, spotify_api.fetch_playlist, job.playlist_uri),
                loop.run_in_executor(None, spotify_api.fetch_playlist_name, job.playlist_uri),
            )
            tracks = _select_playlist_tracks_for_episode(tracks, job.playlist_uri, job.user_id)
            _playlist_selected_uris = [t.uri for t in tracks]
            _order_fingerprint = variety_store.compute_fingerprint(_playlist_selected_uris)
            _track_order_preview = [f"{t.artist} – {t.name}" for t in tracks[:3]]

        if not tracks:
            raise ValueError("No tracks found. Check the playlist link or track list.")

        job.push("progress", {"step": "fetch", "message": f"Fetched {len(tracks)} tracks. Loading audio features..."})

        track_uris = [t.uri for t in tracks]
        features, user_ctx = await asyncio.gather(
            loop.run_in_executor(None, spotify_api.fetch_audio_features, track_uris),
            loop.run_in_executor(None, spotify_api.fetch_user_context),
            return_exceptions=True,
        )

        # Optional enrichment must NEVER abort generation.  Substitute safe
        # empty values and log a warning when a fetch fails.
        if isinstance(features, BaseException):
            logger.warning("fetch_audio_features failed (%s) — continuing without audio analysis", features)
            features = {}
        if isinstance(user_ctx, BaseException):
            logger.warning("fetch_user_context failed (%s) — continuing without personalization", user_ctx)
            user_ctx = spotify_api.UserContext(
                top_tracks_short=[], top_tracks_medium=[], top_tracks_long=[],
                top_artists_short=[], top_artists_medium=[], top_artists_long=[],
                recently_played=[], top_genres=[],
            )
            job.push("progress", {"step": "fetch", "message": "Personalization unavailable, continuing..."})

        job.push("progress", {"step": "context", "message": "Building listener profile..."})

        context = spotify_api.build_playlist_context(tracks, features, user_ctx)

        # Last.fm enrichment: fan-era, play counts, loved tracks, artist bios/similar
        if lastfm_api.is_configured():
            job.push("progress", {"step": "research", "message": "Fetching Last.fm history and artist data..."})

            def _lastfm_progress(message: str):
                job.push_threadsafe(loop, "progress", {"step": "research", "message": message})

            context = await loop.run_in_executor(
                None, lambda: lastfm_api.enrich_context(context, progress_cb=_lastfm_progress)
            )

        # Grounded research: Gemini + Google Search for interviews, news, stories
        job.push("progress", {"step": "research", "message": "Researching artists and songs..."})

        def _research_progress(message: str):
            job.push_threadsafe(loop, "progress", {"step": "research", "message": message})

        context = await loop.run_in_executor(
            None, lambda: research_api.enrich_with_research(context, progress_cb=_research_progress)
        )

        job.push("progress", {"step": "script", "message": "Generating podcast script with Gemini..."})

        # Attach playlist name to context so generate_episode_name can use it
        context["playlist_name"] = job.playlist_name

        # Incognito flag: signals build_prompt to omit all personalization blocks
        context["incognito"] = job.incognito
        if job.commentary_language:
            context["commentary_language"] = job.commentary_language

        # Cast lenses: analysis depth and host vibe (steering, not personal memory)
        context["cast_depth"] = job.cast_depth
        context["cast_vibe"] = job.cast_vibe

        # Attach profile to context for prompt injection (non-blocking; missing = omit block)
        # Omitted entirely for incognito casts (no personalization at all).
        if not job.incognito:
            try:
                _prompt_profile = profile_store.load_profile(job.user_id)
                context["persistent_profile"] = _prompt_profile
            except Exception as _pe:
                logger.warning("Could not load profile for prompt: %s", _pe)

        # Prior-cast context for cache-busting and prompt enrichment
        _prior_count = episodes_store.get_playlist_episode_count(job.playlist_uri, job.user_id) if job.playlist_uri else 0
        context["prior_cast_count"] = _prior_count
        if _prior_count > 0 and job.playlist_uri:
            _latest = episodes_store.get_latest_playlist_episode(job.playlist_uri, job.user_id)
            if _latest:
                if _latest.get("prior_cast_summary"):
                    context["prior_cast_summary"] = _latest["prior_cast_summary"]
                context["prior_cast_replay_count"] = _latest.get("replay_count", 0)
                if _latest.get("id"):
                    _ep_feedback = profile_store.get_episode_feedback(job.user_id, _latest["id"])
                    if _ep_feedback:
                        context["prior_cast_feedback"] = _ep_feedback

        script, identity = await asyncio.gather(
            gemini_api.generate_script(context),
            gemini_api.generate_episode_identity(context),
        )
        episode_name = identity["title"]
        tagline = identity.get("tagline") or None

        # Extract cast summary for persisting with this episode (used by next generation)
        _cast_summary = _extract_cast_summary(script, episode_name)

        job.push("progress", {"step": "tts", "message": "Synthesizing intro audio..."})

        ep_dir = episodes_store.episode_audio_dir(job.user_id, episode_id)
        saved_queue: list[dict] = []
        tracks_by_uri = {t.uri: t for t in tracks}
        total_tracks = len(script["tracks"])

        # --- Synthesize intro, then start streaming immediately ---
        intro_file = f"{ep_dir}/intro.mp3"
        intro_pcm = await tts_api.synthesize_dialogue(script["intro"])
        await loop.run_in_executor(
            None, audio_api.assemble_commentary, intro_pcm, intro_file
        )
        saved_queue.append({"type": "audio", "url": f"/audio/{intro_file}"})
        job.push("intro_ready", {"url": f"/audio/{intro_file}", "episode_name": episode_name, "tagline": tagline})

        # --- Synthesize per-track commentary, streaming each as it finishes ---
        for i, track_script in enumerate(script["tracks"]):
            job.push("progress", {
                "step": "tts",
                "message": f"Synthesizing commentary for track {i+1}/{total_tracks}...",
            })

            commentary_file = f"{ep_dir}/track_{i:03d}_commentary.mp3"
            pcm = await tts_api.synthesize_dialogue(track_script["commentary"])
            await loop.run_in_executor(
                None, audio_api.assemble_commentary, pcm, commentary_file
            )

            track_uri = track_script["track_uri"]
            track_meta = tracks_by_uri.get(track_uri)
            spotify_item = {"type": "spotify", "uri": track_uri}
            if track_meta:
                spotify_item.update({
                    "name": track_meta.name,
                    "artist": track_meta.artist,
                    "duration_ms": track_meta.duration_ms,
                })

            saved_queue.append({"type": "audio", "url": f"/audio/{commentary_file}"})
            saved_queue.append(spotify_item)

            track_ready_payload = {
                "index": i,
                "total": total_tracks,
                "commentary_url": f"/audio/{commentary_file}",
                "track_uri": track_uri,
            }
            if track_meta:
                track_ready_payload.update({
                    "track_name": track_meta.name,
                    "artist": track_meta.artist,
                    "duration_ms": track_meta.duration_ms,
                })
            job.push("track_ready", track_ready_payload)

        # --- Synthesize outro ---
        if script.get("outro"):
            job.push("progress", {"step": "tts", "message": "Synthesizing outro..."})
            outro_file = f"{ep_dir}/outro.mp3"
            outro_url = f"/audio/{outro_file}"
            outro_pcm = await tts_api.synthesize_dialogue(script["outro"])
            await loop.run_in_executor(
                None, audio_api.assemble_commentary, outro_pcm, outro_file
            )
            saved_queue.append({"type": "audio", "url": outro_url})
            job.push("outro_ready", {"url": outro_url})

        # Persist episode for future playback
        episodes_store.save_episode(
            user_id=job.user_id,
            episode_id=episode_id,
            name=episode_name,
            playlist_uri=job.playlist_uri,
            playlist_name=job.playlist_name,
            track_count=total_tracks,
            queue=saved_queue,
            order_fingerprint=_order_fingerprint,
            track_order_preview=_track_order_preview,
            tagline=tagline,
            prior_cast_summary=_cast_summary,
        )

        # Persist variety memory only after successful save (playlist episodes only)
        if _playlist_selected_uris and job.playlist_uri:
            variety_store.save_variety_memory(job.playlist_uri, job.user_id, _playlist_selected_uris)

        # Update persistent listener profile (Slice One: context summariser).
        # Slice Two: also run saved-cast + feedback summarizers.
        # Skipped entirely for incognito casts (no writes).
        # When memory_enabled is False, summarizers still update DURABLE fields
        # but skip TRAIL fields.
        # Must NOT block or fail generation.
        if not job.incognito:
            try:
                _profile = profile_store.load_profile(job.user_id)
                _memory_enabled = _profile.get("memory_enabled", True)
                _profile = profile_store.summarize_context(
                    context, _profile, memory_enabled=_memory_enabled
                )
                _profile = profile_store.summarize_saved_casts(
                    job.user_id, _profile, memory_enabled=_memory_enabled
                )
                _profile = profile_store.fold_feedback_into_profile(job.user_id, _profile)
                profile_store.save_profile(job.user_id, _profile)
            except Exception as _profile_exc:
                logger.warning("Profile update failed (non-blocking): %s", _profile_exc)

        job.push("done", {"episode_id": episode_id, "episode_name": episode_name})
        job.status = "done"

    except GeminiTTSQuotaError as exc:
        job.status = "error"
        job.error = str(exc)
        _set_tts_cooldown(exc.retry_after_seconds, exc.model)
        # Preserve partial progress so the user can see the cast was attempted
        if saved_queue:
            try:
                episodes_store.save_episode(
                    user_id=job.user_id,
                    episode_id=episode_id,
                    name=episode_name,
                    playlist_uri=job.playlist_uri,
                    playlist_name=job.playlist_name,
                    track_count=total_tracks,
                    queue=saved_queue,
                    order_fingerprint=_order_fingerprint,
                    track_order_preview=_track_order_preview,
                    tagline=tagline,
                    status="quota_failed",
                )
            except Exception as save_exc:
                logger.warning("Failed to save partial episode %s: %s", job.job_id, save_exc)
        job.push("error", {
            "code": exc.code,
            "model": exc.model,
            "retry_after_seconds": exc.retry_after_seconds,
            "message": exc.quota_message,
        })
        logger.error(
            "TTS quota exhausted for job %s (model=%s, retry_after=%ss)",
            job.job_id, exc.model, exc.retry_after_seconds,
        )

    except Exception as exc:
        job.status = "error"
        job.error = str(exc)
        # Graceful partial-save: if some audio was produced, persist a partial
        # episode so the cast isn't orphaned with no episode.json.
        if saved_queue:
            try:
                # episode_name / total_tracks are always set before TTS starts,
                # which is when saved_queue becomes non-empty.
                episodes_store.save_episode(
                    user_id=job.user_id,
                    episode_id=episode_id,
                    name=episode_name,
                    playlist_uri=job.playlist_uri,
                    playlist_name=job.playlist_name,
                    track_count=total_tracks,
                    queue=saved_queue,
                    order_fingerprint=_order_fingerprint,
                    track_order_preview=_track_order_preview,
                    tagline=tagline,
                    status="gen_failed",
                )
            except Exception as save_exc:
                logger.warning("Failed to save partial episode %s: %s", job.job_id, save_exc)
        job.push("error", {"message": _format_generation_error(exc)})
        logger.exception("Generation failed for job %s", job.job_id)
