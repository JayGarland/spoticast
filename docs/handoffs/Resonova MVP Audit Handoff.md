---
title: "Resonova MVP Audit Handoff"
source: "OCP Workspace Lead — direct audit against docs/strategy/resonova-mvp-audit-brief.md"
created: 2026-06-19
status: draft
tags:
  - handoff
  - audit
  - mvp
  - resonova
  - spoticast
---

# Resonova MVP Audit Handoff

## Executive Summary

The Resonova local MVP is functional and well-structured. The rename from Spoticast to Resonova is complete in all source code. The server starts, the web UI loads, API routes respond, and 3 previously generated episodes exist on disk. The core flow — Spotify playlist → AI script → multi-speaker TTS → streaming browser playback — works end-to-end. Configuration is cleanly separated between script generation and TTS models. No secrets are exposed in the repo.

Key gaps: `.env.example` model defaults are stale, `.lastfm_user` is not gitignored, no tests exist, and the MVP is still one-shot (no persistent taste profile between sessions).

---

## Git and Working Tree State

- **Branch**: `main`, 3 commits ahead of `origin/main`
- **Working tree at strategy-layer review**: `docs/handoffs/Resonova MVP Audit Handoff.md` is untracked until the owner/strategy layer accepts it
- **Last commits**:
  - `5a533c9` — Add OCP workspace skills, handoff docs, and MVP audit brief
  - `0901bc6` — Rename project from Spoticast to Resonova
  - `2bb8e6a` (`base/spoticast`) — Spotify API fixes + Gemini 3 model upgrade
- **Branches**: `main` (active), `base/spoticast` (pre-rename baseline), `upstream/main` (original Spoticast upstream)

---

## Current MVP Capability Map

| Capability | Status | Notes |
|---|---|---|
| Spotify OAuth (PKCE) | ✅ Working | Redirects to `http://127.0.0.1:8765/auth/callback` |
| Playlist fetch | ✅ Working | Via URI or pasted track list; handles new Spotify API format |
| Audio features fetch | ⚠️ Degraded | `/audio-features` restricted in Dev Mode; pipeline continues gracefully |
| User context fetch | ✅ Working | Top tracks, top artists (short/medium/long term), recently played |
| Last.fm enrichment | ✅ Working | Fan-era classification, artist profiles, play counts, loved tracks |
| Gemini grounded research | ✅ Working | Google Search grounding via Vertex AI / AI Studio |
| Script generation | ✅ Working | Gemini 3.1 Pro, structured JSON output, two-host dialogue |
| TTS synthesis | ✅ Working | Multi-speaker (Charon + Aoede voices), PCM → MP3 conversion |
| Streaming playback | ✅ Working | SSE progress stream; intro plays immediately, tracks stream as ready |
| Browser playback | ✅ Working | Interleaved HTML Audio (commentary) + Spotify Web Playback SDK (music) |
| Crossfade | ✅ Working | Commentary fades out ~2s before end for smooth transition |
| Episode persistence | ✅ Working | `generated/episodes/<uuid>/episode.json` with queue metadata |
| Episode replay | ✅ Working | Episodes listed in UI, selectable for replay |

---

## End-to-End Flow Map

```text
User opens browser at http://127.0.0.1:8765
    │
    ├─ Landing page: "Resonova" branding, Connect Spotify button
    │
    ▼
Spotify OAuth (PKCE flow) → token cached in .research_cache/.spotify_oauth
    │
    ├─ Connection confirmed, UI shows playlist browser + paste input
    ├─ Optional: Last.fm username → validates, persists to .lastfm_user
    │
    ▼
User pastes playlist URL / URI / track list → clicks "Generate Cast"
    │
    ▼
[Background job via SSE]
    │
    ├─ 1. FETCH: playlist tracks + audio features + user context
    │       (audio features gracefully degraded if Dev Mode 403)
    │
    ├─ 2. CONTEXT: build playlist context (listener profile, audio stats)
    │
    ├─ 3. RESEARCH: Last.fm enrichment (fan-era, artist profiles, track data)
    │       → Gemini grounded research (Google Search for interviews, stories)
    │
    ├─ 4. SCRIPT: Gemini generates structured JSON with intro, per-track commentary, outro
    │       (two hosts: Sam/HOST_A "Charon" voice, Alex/HOST_B "Aoede" voice)
    │
    ├─ 5. TTS (intro): Gemini TTS synthesizes intro dialogue → PCM → MP3
    │       → "intro_ready" SSE event → browser starts playback immediately
    │
    ├─ 6. TTS (per-track, streaming): each track's commentary synthesized sequentially
    │       → "track_ready" SSE event → appended to live playback queue
    │       → Queue: [commentary.mp3] → [spotify:track:xxx] → [commentary.mp3] → ...
    │
    ├─ 7. TTS (outro): final wrap-up synthesized
    │       → "outro_ready" SSE event → appended to queue
    │
    ├─ 8. EPISODE SAVED: episode.json written to generated/episodes/<uuid7>/
    │
    ▼
Playback: HTML Audio ↔ Spotify SDK interleaved, crossfade between segments
```

---

## Architecture Map

```
resonova/                        # Python package root (renamed from spoticast)
  __init__.py                    # Empty
  __main__.py                    # Entry: uvicorn + browser auto-open
  config.py                      # Pydantic Settings from .env
  cache.py                       # Disk cache (.research_cache/)
  server.py                      # FastAPI app, routes, SSE job streaming
  episodes.py                    # Episode CRUD (generated/episodes/)
  api/
    __init__.py                  # Empty
    spotify.py                   # OAuth, playlist/track/features/user-context fetch
    gemini.py                    # Script generation (structured JSON)
    tts.py                       # Multi-speaker TTS synthesis
    audio.py                     # PCM → MP3 assembly (pydub)
    lastfm.py                    # Fan-era, artist profiles, track enrichment
    research.py                  # Gemini + Google Search grounding
  web/
    index.html                   # Single-page UI (landing → connected → generating → playing)
    player.js                    # Spotify SDK + HTML Audio queue + crossfade
    styles.css                   # Dark theme with nebula background
generated/                       # Runtime MP3 + episode JSON (gitignored)
  episodes/<uuid7>/
    intro.mp3
    track_000_commentary.mp3 ... track_NNN_commentary.mp3
    outro.mp3
    episode.json
.research_cache/                 # Disk caches: gemini/, lastfm/, research/, .spotify_oauth (gitignored)
```

### External API Dependencies

| Service | Module | Auth Method | Purpose |
|---|---|---|---|
| Spotify Web API | `spotify.py` | OAuth PKCE | Playlists, tracks, audio features, user data |
| Spotify Web Playback SDK | `player.js` | OAuth access token | In-browser music playback |
| Gemini (AI Studio) | `gemini.py`, `tts.py`, `research.py` | API key | Script generation, TTS, grounded research |
| Last.fm | `lastfm.py` | API key + secret | Artist profiles, fan-era, play counts |

### Model Name Configuration

| Setting | Config Key | Default in `config.py` | Actual `.env` Value |
|---|---|---|---|
| Script generation | `gemini_model` | `gemini-3.1-pro-preview` | `gemini-3.1-pro-preview` |
| Research | `gemini_research_model` | `gemini-3.1-flash-lite-preview` | `gemini-3.1-flash-lite-preview` |
| TTS | `gemini_tts_model` | `gemini-2.5-pro-preview-tts` | `gemini-3.1-flash-tts-preview` |

> **Finding**: The `.env.example` file shows stale defaults (`gemini-2.5-pro` for script, `gemini-2.5-pro-preview-tts` for TTS) that don't match `config.py`. The actual `.env` uses `gemini-3.1-flash-tts-preview` for TTS — a newer model than the config default.

---

## Rename Health: Spoticast → Resonova

### Python Source Code — Clean

No `spoticast` references found in any `.py` file. Package name, imports, and internal references all use `resonova`:

- `pyproject.toml`: `name = "resonova"`, entry point `resonova = "resonova.__main__:main"`
- `resonova/__main__.py`: imports from `resonova.config`, runs `resonova.server:app`
- `resonova/server.py`: `FastAPI(title="Resonova")`
- All API modules import from `resonova.config`, `resonova.cache`, `resonova.episodes`

### Frontend — Clean

- `index.html`: `<title>Resonova</title>`, logo text "Reso<span>nova</span>"
- `player.js`: `class ResonovaPlayer`, Spotify player name `'Resonova'`
- No `spoticast` string in HTML, JS, or CSS

### Documentation — Intentional Historical References

`spoticast` appears only in:

- `README.md` lines 7, 13, 27 — lineage documentation (intentional: explains the rename)
- `docs/handoffs/Spoticast → Resonova.md` — legacy handoff from pre-rename era
- `docs/handoffs/Spoticast Local MVP Handoff.md` — pre-rename handoff
- `docs/strategy/resonova-mvp-audit-brief.md` — audit context

All `spoticast` references in docs are either:

- Historical context (naming the upstream/base)
- File paths prefixed with "now at `resonova/...`"
- Intentional lineage documentation in README

### CLI Entry Points — Working

- `uv run resonova` — works (uses `pyproject.toml [project.scripts]`)
- `uv run python -m resonova` — works (starts server, opens browser)
- `make run` — invokes `uv run resonova`

---

## Configuration and Secret Handling

### `.env` Protection

| Artifact | Gitignored? | Status |
|---|---|---|
| `.env` | ✅ Yes | Confirmed via `git check-ignore` |
| `generated/` | ✅ Yes | Contains MP3 + episode JSON |
| `.research_cache/` | ✅ Yes | Contains disk caches + Spotify OAuth token |
| `.cache` | ✅ Yes | Build artifacts |
| `.lastfm_user` | ❌ **Not gitignored** | Persists Last.fm username across restarts; not currently present on disk |

### `.env.example` Alignment

| Variable | `.env.example` Default | `config.py` Default | Aligned? |
|---|---|---|---|
| `GEMINI_MODEL` | `gemini-2.5-pro` (commented) | `gemini-3.1-pro-preview` | ❌ Stale |
| `GEMINI_TTS_MODEL` | `gemini-2.5-pro-preview-tts` (commented) | `gemini-2.5-pro-preview-tts` | ✅ |
| `MAX_TRACKS` | `30` | `30` | ✅ |
| `PORT` | `8765` (commented) | `8765` | ✅ |

---

## Validation Results

### Commands Run and Results

| # | Command | Result |
|---|---|---|
| 1 | `uv run python -c "import resonova; print('Import OK')"` | ✅ Import OK |
| 2 | `uv run python -c "from resonova.config import settings; ..."` | ✅ Settings loaded: model=`gemini-3.1-pro-preview`, tts=`gemini-3.1-flash-tts-preview`, port=8765 |
| 3 | `uv run resonova` (server start) | ✅ Server started on `http://127.0.0.1:8765` |
| 4 | Web UI load | ✅ `GET /` → 200, `GET /web/styles.css` → 200, `GET /web/player.js` → 200 |
| 5 | API: `/auth/token` | ✅ 200, authenticated |
| 6 | API: `/api/episodes` | ✅ 200, returned episode list |
| 7 | API: `/api/episodes/<id>` | ✅ 200, returned episode metadata |
| 8 | API: `/api/recent` | ✅ 200 |
| 9 | API: `/api/playlists` | ✅ 200 |
| 10 | API: `/auth/lastfm/status` | ✅ 200 |
| 11 | Audio serving | ✅ `GET /audio/episodes/.../intro.mp3` → 206 Partial Content |
| 12 | `git check-ignore .env generated/ .research_cache/ .cache` | ✅ All gitignored |
| 13 | `git status` | ✅ Clean working tree after commit |

### Not Validated

| Check | Reason |
|---|---|
| Full playlist → script → TTS generation | Requires real Spotify + Gemini API calls; 3 existing episodes on disk confirm the flow has worked recently |
| TTS audio quality | Subjective; no tooling to assess |
| Spotify Web Playback SDK in browser | Requires active Spotify Premium session + device; server logs show token refresh and API calls succeeding |
| Last.fm full enrichment | Requires Last.fm credentials; module code and status endpoint confirmed functional |
| `make dev` (auto-reload) | Not tested — `make run` was validated; dev mode uses same uvicorn app |

---

## Risks and Gaps

### What Could Break the MVP Flow

1. **Gemini model deprecation**: `gemini-2.5-pro-preview-tts` (config default) and `gemini-3.1-flash-tts-preview` (actual .env value) are preview models — Google may deprecate them
2. **Spotify API format changes**: Already happened once (item/track key shift); defensive `.get()` patterns help but aren't comprehensive
3. **ffmpeg not installed**: Required by pydub for PCM→MP3; README only mentions `brew install ffmpeg` (macOS), no Windows instructions
4. **Spotify Dev Mode restrictions**: Audio features endpoint returns 403 for Dev Mode apps; pipeline degrades gracefully but loses audio analysis data
5. **No token refresh error handling**: If Spotify refresh token expires, user must re-authenticate manually
6. **Single-threaded TTS**: Tracks are synthesized sequentially — a single Gemini API outage blocks the entire generation

### Fragile Areas

1. **`.lastfm_user` not gitignored**: If a user commits this file, their Last.fm username is exposed (low severity — username alone is not a secret, but still a leak)
2. **`.env.example` stale defaults**: New users following `.env.example` comments would use `gemini-2.5-pro` which may not support TTS
3. **No test suite**: Zero automated tests; all validation is manual
4. **In-memory job state**: `_jobs` dict in `server.py` — server restart loses in-progress jobs
5. **Hardcoded voice mapping in `tts.py`**: Voices are `Charon`/`Aoede` with no config override path

### Gaps Between Current MVP and Resonova Product Direction

| Resonova Direction | Current State | Gap |
|---|---|---|
| Long-term taste profile | No persistent profile between sessions | Major — needs storage design |
| Listening history | Spotify top/recent fetched per-generation; Last.fm data fetched live | Medium — no accumulation |
| Refreshable sessions | One-shot generation only | Medium — needs regeneration UI + cache invalidation |
| Feedback loops | No feedback mechanism | Major — no UI or storage for likes/ratings |
| Customizable lenses (mood, era, genre) | No lens selection in UI or prompt | Minor — system prompt is static |
| Future source expansion beyond Spotify | Spotify-only | Future — architecture supports it (pluggable API modules) |

---

## Recommended Preservation List

These parts should not be broken during future development:

1. **Spotify API defensive patterns** (`spotify.py`): The `_parse_track()` dual-format handling and `.get()` fallbacks for missing keys — these are battle-tested against real API changes
2. **Separate model configs**: `gemini_model` (script) != `gemini_tts_model` (TTS) != `gemini_research_model` (research) — this separation is critical
3. **SSE streaming architecture**: Server pushes intro/track/outro events; frontend appends to live queue — enables "play while generating" UX
4. **Disk cache layer** (`cache.py`): JSON file cache with SHA1 keys, used by gemini, lastfm, and research modules — prevents redundant API calls
5. **Graceful degradation**: Audio features 403 → continue; Last.fm missing → skip enrichment; research fails → no crash
6. **Multi-speaker TTS config**: `tts.py` uses `MultiSpeakerVoiceConfig` with prebuilt voices — don't regress to single-voice or text-only TTS
7. **Episode persistence format**: `episode.json` with `queue: [{type, url|uri}]` — the replay feature depends on this schema

---

## Candidate Issues

These are neutral observations, not approved next tasks:

1. **`CANDIDATE`**: `.env.example` `GEMINI_MODEL` comment shows `gemini-2.5-pro`; should be `gemini-3.1-pro-preview` to match `config.py` default
2. **`CANDIDATE`**: `.lastfm_user` should be added to `.gitignore`
3. **`CANDIDATE`**: No Windows ffmpeg install instructions in README (only `brew install ffmpeg`)
4. **`CANDIDATE`**: `gemini_tts_model` config default (`gemini-2.5-pro-preview-tts`) differs from actual `.env` value (`gemini-3.1-flash-tts-preview`) — unclear which is the intended production default
5. **`CANDIDATE`**: Zero automated tests — any refactor carries regression risk
6. **`CANDIDATE`**: `TTS voice names` (Charon, Aoede) are hardcoded in `tts.py` with no settings override
7. **`CANDIDATE`**: Server uses in-memory `_jobs` dict — horizontal scaling would require Redis or similar
8. **`CANDIDATE`**: No favicon — browsers hit `/favicon.ico` and get 404 on every page load
9. **`CANDIDATE`**: `make dev` uses `$${PORT:-8765}` escaping — works in bash/zsh but may fail in other shells on Windows

---

## Open Questions for Strategy Layer

1. Is the current one-shot flow (playlist → episode) acceptable as the foundation, or should the first expansion be a persistent taste profile?
2. Should the TTS model default in `config.py` be updated to match the actual working model (`gemini-3.1-flash-tts-preview`), or stay at `gemini-2.5-pro-preview-tts` for quality?
3. Is the `base/spoticast` branch still needed as a reference point, or can it be archived?
4. Should the audit include actually running a full generation with Spotify + Gemini API calls, or is the existing episode evidence sufficient?

---

## Work Not Performed

- No new features implemented (by design — audit-only scope)
- No refactoring or code changes
- No full end-to-end generation with real API calls (existing episodes on disk confirm the flow)
- No Spotify Web Playback SDK browser testing (requires active Spotify Premium session)
- No TTS audio quality assessment (no tooling)
- No security audit of OAuth token storage
