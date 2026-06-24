# Option B — Multi-User Isolation Problem

Date: 2026-06-24
Status: IMPLEMENTED — all four fixes deployed and verified (commit c5c5aa7)
Bug fix: ContextVar thread propagation (see docs/handoffs/Multi-User ContextVar Thread Fix 2026-06-24.md)
Audience: Boss + Chef

---

## The Problem

Resonova is single-user by design throughout all layers. Sharing the Cloudflare Tunnel
URL with a second person does not give them their own session — it breaks yours.

---

## What Actually Happens When Person B Opens the URL

1. Person B loads the page — they see your UI, your saved casts, your profile data.
2. Person B clicks "Connect Spotify" and authenticates.
3. Their OAuth callback hits `/auth/callback` on your server.
4. `handle_callback()` calls `oauth.get_access_token()` which **overwrites the single
   token cache file** at `.research_cache/.spotify_oauth`.
5. Your Spotify session is now gone. The next API call you make fails.
6. The `claim_or_check_owner` guard fires — it sees Person B's `user_id` doesn't match
   the stored owner and rejects them from the profile.
7. Result: Person B is locked out of the profile. You are logged out of Spotify.
   Neither of you can use the app.

The owner guard was built to prevent data contamination, not to enable multi-user.
It blocks the second user from writing to your profile but doesn't give them their own
space or protect your Spotify session.

---

## Root Cause: Three Single-User Assumptions Stacked

### Layer 1 — Spotify auth is a global singleton

`resonova/api/spotify.py`:
- `_oauth` is a module-level `SpotifyOAuth` instance — one for the entire process.
- The token is cached to a single file: `.research_cache/.spotify_oauth`.
- `get_client()` reads from that one file. `handle_callback()` overwrites it.
- There is no concept of "which user's token" — there is only one token.

### Layer 2 — All data paths are fixed, not user-scoped

- Profile: `generated/profile/profile.json` — one file, no user key.
- Feedback: `generated/profile/feedback.jsonl` — one file, no user key.
- Episodes: `generated/episodes/` — one folder, no ownership record.
- Research cache: `.research_cache/` — shared across all users.

### Layer 3 — No HTTP session management

- No cookies, no JWTs, no session IDs on requests.
- The server has no way to know which incoming request belongs to which user.
- All requests share the same server-side state.

---

## What the Patch Needs to Cover

The patch described earlier (per-user data paths + allowlist) is necessary but **not
sufficient**. It fixes Layer 2 and adds an allowlist, but Layers 1 and 3 must also be
fixed or the token collision still kills sessions.

### Full patch scope for Option B:

**Fix 1 — HTTP session (Layer 3)**
Add cookie-based session management (e.g. `itsdangerous` signed cookies or
`starlette.middleware.sessions`). Each browser gets a session cookie. The session
stores `{user_id, access_token, refresh_token}` in memory keyed by session ID.

**Fix 2 — Per-session Spotify client (Layer 1)**
Stop using the global `_oauth` file cache for multi-user. On login, store the token
in the HTTP session instead of the file. Create a `spotipy.Spotify` client per request
from the session's token. The file cache can remain for single-user/dev mode fallback.

**Fix 3 — Per-user data paths (Layer 2)**
Move all data under `generated/users/{spotify_user_id}/`:
- `generated/users/{uid}/profile/profile.json`
- `generated/users/{uid}/profile/feedback.jsonl`
- `generated/users/{uid}/episodes/`

`profile.py` and `episodes.py` accept a `user_id` argument.
`server.py` extracts `user_id` from the session on every request.

**Fix 4 — Allowlist middleware**
Env var: `ALLOWED_SPOTIFY_USER_IDS=uid1,uid2,...`
Middleware rejects any authenticated user not on the list with a friendly "not invited"
page. Prevents unknown visitors from consuming API quota.

---

## Does the Patch Fully Solve the Problem?

Yes — if all four fixes are implemented together.

| Problem | Fixed by |
|---|---|
| Person B's login kills Person A's Spotify session | Fix 1 + Fix 2 |
| Users see each other's profile / episodes | Fix 3 |
| Unknown visitors can access the app | Fix 4 |
| No way for server to identify who is requesting | Fix 1 |

Implementing only Fix 3 (data paths) without Fix 1 + 2 does NOT solve the problem —
the token collision still occurs on any second login.

---

## New Dependencies Required

| Dependency | Purpose |
|---|---|
| `itsdangerous` or `starlette[sessions]` | Signed session cookies |

No database needed. SQLite is not required for Option B. File-based storage works
fine once scoped per user.

---

## Files That Need Changing

| File | Change |
|---|---|
| `resonova/api/spotify.py` | Remove global `_oauth` singleton for multi-user path; support per-session token |
| `resonova/server.py` | Add session middleware; extract `user_id` from session on every request; pass to all store calls |
| `resonova/profile.py` | Accept `user_id` arg; resolve all paths under `generated/users/{uid}/` |
| `resonova/episodes.py` | Accept `user_id` arg; resolve paths under `generated/users/{uid}/episodes/` |
| `resonova/variety.py` | Accept `user_id` arg if it reads per-user state |
| `resonova/config.py` | Add `allowed_spotify_user_ids` setting |
| `pyproject.toml` | Add session dependency |

Frontend (`player.js`, `index.html`): no changes needed — the session cookie is
transparent to the browser.

---

## What Is NOT Required for Option B

- SQLite or any database
- React / Vue / any frontend framework
- Redis or any cache server
- Docker or containerisation
- Any changes to the Gemini or TTS pipeline
