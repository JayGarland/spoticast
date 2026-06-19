---
title: "Spoticast → Resonova: Environment Setup, Bug Fixes & TTS Model Upgrade"
source: "chat-session 4d0db808 (Spoticast workspace, before rename to Resonova)"
author: ""
published: false
created: 2026-06-19
description: "Legacy handoff from the Spoticast-era chat session covering Spotify API fixes, Gemini 3 model migration, and TTS exploration."
tags:
  - handoff
  - spoticast
  - resonova
  - tts
  - spotify-api
  - gemini
---

## Goal

Set up the Spoticast (now Resonova) project on Windows, fix Spotify API compatibility issues, upgrade from Gemini 2.5 to Gemini 3 models, and explore alternative TTS providers.

## Current Progress

### ✅ Environment Setup

- Python 3.13.14 installed via `uv` managed Python
- `uv` 0.11.22 package manager set up
- `.venv` created with all dependencies
- `.env` configured with Spotify credentials and Gemini API keys

### ✅ Spotify API Fixes (commit `2bb8e6a`)

- **`fetch_playlist`**: Spotify Web API changed response format — `"track"` key is now `"item"` for track objects
- **`_parse_track`**: Handle `"track"` boolean flag in new API format (previously it was a nested object)
- **`fetch_user_playlists` / `fetch_featured_playlists` / `fetch_recent_plays`**: Added defensive `.get()` for missing `"tracks"` key
- **`server.py`**: Restricted error message rewriting to `SpotifyException` instances only (was catching all 404s and mislabeling them)

### ✅ TTS Model Fixes

- **`tts.py`**: Changed from hardcoded `"gemini-2.5-flash-tts"` to using `settings.gemini_tts_model` from config
- **`config.py`**: Added `gemini_tts_model` setting (default: `gemini-2.5-pro-preview-tts`)
- **`.env.example`**: Added `GEMINI_TTS_MODEL` template

### ✅ Model Upgrade: Gemini 2.5 → Gemini 3

- Script generation model: `gemini-2.5-flash` → `gemini-3-flash-preview`
- TTS model: tested `gemini-2.5-pro-preview-tts` (works, best quality), `gemini-3-pro-preview` available

### 🔮 Future TTS Options (documented in `memories/repo/future-tts-options.md`)

- **火山引擎「豆包语音播客大模型」**: Podcast-optimized, multi-speaker, ~¥70/¥100 per 10M tokens
- **CosyVoice 2.0** (Alibaba open-source): Multi-speaker + voice cloning, requires GPU
- **Baidu TTS**: 2M chars/month free, no multi-speaker
- **iFlytek TTS**: 500 req/day free, no multi-speaker
- **Xiaomi XiaoAi (小爱同学)**: No public API found

## What Worked

1. Using `uv` to manage Python version and venv locally per-repo
2. Defensive `.get()` pattern for evolving Spotify API responses
3. Restricting error handler to `SpotifyException` only (not all exceptions)
4. Separating TTS model config from script generation model
5. Using Chrome MCP server for end-to-end verification of the web UI

## What Didn't Work

1. `gemini-2.5-flash-tts` model name — this suffix doesn't exist; TTS is enabled via `speech_config` + `response_modalities=["AUDIO"]`, NOT via model suffix
2. `gemini-2.5-flash` for TTS — it's text-only, doesn't support audio output
3. Xiaomi XiaoAi (小爱同学) — no public API available
4. Chat history migration from `spoticast` → `resonova` workspace — files copied successfully but VS Code Copilot Chat UI doesn't show old sessions (full VS Code restart may help)

## Next Steps

1. **Verify the app still works** after renaming from Spoticast to Resonova — check all imports, config references, and the web UI at `http://127.0.0.1:8765`
2. **Evaluate 火山引擎 豆包 TTS** as a potential Gemini TTS replacement for better podcast-quality audio
3. **Audit the `.env` file** — ensure `GEMINI_TTS_MODEL` is set correctly after the rename
4. **Test Spotify playlist generation end-to-end** with a public playlist URL

## Relevant Files

| File | Relevance |
|------|-----------|
| `spoticast/api/spotify.py` | Spotify API fixes (now at `resonova/api/spotify.py`) |
| `spoticast/api/tts.py` | TTS model name fix |
| `spoticast/config.py` | Added `gemini_tts_model` setting |
| `spoticast/server.py` | Error handler fix |
| `.env.example` | Added `GEMINI_TTS_MODEL` |
| `memories/repo/future-tts-options.md` | Future TTS alternatives |
| `generated/episodes/` | Generated podcast episodes |

## Constraints

- Do NOT revert the Spotify API response format fixes — the new format (`"item"` key, boolean `"track"` flag) is the current API behavior
- Do NOT hardcode model names — always use `settings` from `config.py`
- TTS model and script generation model MUST be separate — they have different API capabilities
- Keep `.env` out of version control (already in `.gitignore`)

## Validation Needed

- [ ] Run `uv run python -m resonova` and confirm the server starts without errors
- [ ] Paste a public Spotify playlist URL and verify episode generation works
- [ ] Check that TTS audio is generated correctly with the current model config
- [ ] Verify the web UI loads at `http://127.0.0.1:8765`
