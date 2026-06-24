---
title: "Multi-User Isolation Patch Chef Gate Handoff"
source: ""
author: ""
published: false
created: 2026-06-23
description: "All four fixes for Option B multi-user isolation have been implemented and validated. Ready for chef gate review."
tags:
  - handoff
---

## Goal

Implement Option B multi-user isolation — four atomic changes to make Resonova support multiple users with per-session Spotify OAuth, per-user data paths, HTTP sessions, and an allowlist.

## Current Progress

All four fixes are implemented and validated:

1. **Session middleware** — `itsdangerous` added to dependencies, `SessionMiddleware` wired into `server.py` with `session_secret_key` from config.

2. **Multi-user Spotify OAuth** — `server.py` now uses per-session token storage (in HTTP session) instead of a global file cache. New functions in `resonova/api/spotify.py`: `handle_callback_for_session`, `get_client_from_token`, `refresh_token_if_needed`, `set_session_client`. Per-request session client binding via `get_current_user()` helper and `ContextVar`.

3. **Per-user data paths** — All path-using functions in `resonova/profile.py`, `resonova/episodes.py`, `resonova/variety.py` now accept `user_id: str` as first argument. Paths scoped to `generated/users/{user_id}/`. Separate user profiles, episode stores, and variety memories.

4. **Spotify user allowlist** — `allowed_spotify_user_ids` config field; enforced in `/auth/callback`.

### Files Created

- `scripts/migrate_to_per_user.py` — one-shot migration script for existing data

### Files Modified

- `pyproject.toml` — added `itsdangerous` dependency
- `resonova/config.py` — added `session_secret_key` and `allowed_spotify_user_ids` fields
- `resonova/api/spotify.py` — context var, per-session client functions
- `resonova/profile.py` — all functions accept `user_id`, removed `claim_or_check_owner`
- `resonova/episodes.py` — all functions accept `user_id`
- `resonova/variety.py` — all functions accept `user_id`
- `resonova/server.py` — session middleware, `get_current_user`, rewritten callbacks and endpoints
- `tests/test_profile.py` — all calls pass `user_id`, new temp directory setup
- `tests/test_variety_episodes.py` — all calls pass `user_id`

## What Worked

- The context variable approach in `spotify.py` cleanly separates per-session clients from the dev/CLI fallback singleton.
- Migrating from module-level path constants to `_profile_dir(user_id)` functions was straightforward and testable.
- Server endpoints using `get_current_user()` centralize auth + client binding.

## What Didn't Work

- `test_profile.py` originally monkey-patched module-level path constants (`_PROFILE_DIR`, `_PROFILE_PATH`, `_FEEDBACK_PATH`). Since those are now functions, the test setup was rewritten to use `os.chdir` into a temp dir with proper `generated/users/{user_id}/` subdirectory structure.
- `test_variety_episodes.py` had a recursive `_run_tests()` call embedded inside `_test_no_taste_unchanged` — fixed by adding a proper `if __name__ == "__main__"` guard.

## Next Steps (Chef Gate)

1. Review all changes for correctness and edge cases.
2. Smoke-test the app with multi-user flows (two different Spotify accounts).
3. Run the migration script on the production data path if needed.
4. Consider setting proper `session_secret_key` in production (not the default).
5. Decide whether to commit or defer — DO NOT COMMIT yet per instructions.

## Relevant Files

- `resonova/server.py` — main entry point with session, auth callback, endpoints
- `resonova/api/spotify.py` — session-aware OAuth helper functions
- `resonova/profile.py` — per-user profile store
- `resonova/episodes.py` — per-user episodes store
- `resonova/variety.py` — per-user variety memory
- `resonova/config.py` — new config fields
- `scripts/migrate_to_per_user.py` — data migration script
- `tests/test_profile.py` — profile store tests
- `tests/test_variety_episodes.py` — variety/episodes store tests

## Constraints

- `claim_or_check_owner` was removed. `get_owner_id` kept read-only for migration script compatibility.
- All data paths are now under `generated/users/{user_id}/` instead of `generated/profile/`, `generated/episodes/`, `generated/variety/`.
- The file-based singleton fallback in `get_client()` is preserved for dev/CLI use.

## Validation Needed

- [x] `python tests/test_profile.py` — 45 tests pass
- [x] `python tests/test_variety_episodes.py` — 15/17 pass (2 pre-existing failures unrelated to multi-user changes: missing `player.js` and `playlist_card_quick_generate`)
- [x] `python tests/test_tts_failover.py` — all 5 tests pass
- [x] `from resonova.server import app` — import OK
- [ ] Chef review of all 8 files
