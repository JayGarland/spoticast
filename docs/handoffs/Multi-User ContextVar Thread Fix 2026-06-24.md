# Multi-User ContextVar Thread Isolation Fix

Date: 2026-06-24
Commit: c5c5aa7
Status: DEPLOYED — confirmed fixed by live two-user test

---

## The Bug

After Option B multi-user isolation was merged, a second user who logged in with
their own Spotify account still saw the **owner's playlists and data** rather than
their own.

Confirmed via `/api/me` debug endpoint: the tester's session correctly stored their
own user ID (`31xwqnbfjj2mrn72mqrtbrchk4ta`), not the owner's. The session layer was
correct. The data layer was wrong.

---

## Root Cause

`_per_session_client` is a `ContextVar` (in `resonova/api/spotify.py`) set in the
async request handler (`get_current_user`) to bind the correct Spotify client for
the current user. `get_client()` checks this ContextVar first; if `None`, it falls
back to `oauth.get_cached_token()` — the file-cached **owner** token.

All Spotify API calls in `server.py` go through `loop.run_in_executor(None, ...)`,
which dispatches work to a `ThreadPoolExecutor`. While Python 3.7+ specifies that
`run_in_executor` copies the current execution context into the thread via
`copy_context()`, the ContextVar was returning `None` inside those threads in
practice, causing every threaded Spotify call to fall back to the file-cached owner
token regardless of which user initiated the request.

Affected endpoints/functions (8 sites):
- `api_recent` → `fetch_recent_plays`
- `api_playlists` → `fetch_user_playlists`
- `api_profile_refresh` → `fetch_saved_tracks`, `fetch_followed_artists`
- `_auto_refresh_profile_on_connect` → `fetch_saved_tracks`, `fetch_followed_artists`
- `_run_generation` → `fetch_tracks`, `fetch_playlist`, `fetch_playlist_name`,
  `fetch_audio_features`, `fetch_user_context`

---

## Fix

Added `_with_sp(sp, fn, *args)` helper in `server.py`:

```python
def _with_sp(sp, fn, *args):
    """Set the per-session Spotify client inside the executor thread before calling fn."""
    spotify_api.set_session_client(sp)
    return fn(*args)
```

All 8 affected `run_in_executor` calls changed from:
```python
loop.run_in_executor(None, spotify_api.fetch_recent_plays)
```
to:
```python
loop.run_in_executor(None, _with_sp, sp, spotify_api.fetch_recent_plays)
```

Also added `Job.sp` field so `_run_generation` (a background asyncio Task, not an
HTTP handler) carries the correct client without relying on ContextVar propagation
across task boundaries.

`_auto_refresh_profile_on_connect` received an explicit `sp` parameter (passed from
`/auth/callback` where `sp` is already in scope).

---

## Why This Was Missed

### Miss 1 — Chef gate did not run a live two-user smoke test

The manager's own handoff listed "Smoke-test the app with multi-user flows (two
different Spotify accounts)" as a required gate step. The chef gate verified:
- All three test suites pass
- Server import OK
- Code diff structurally correct

But did **not** actually log in with a second Spotify account and verify data
isolation end-to-end. That one test would have caught the bug instantly.

### Miss 2 — The implementation brief had no multi-user acceptance criterion

The chef's implementation brief to the manager specified the design (ContextVar +
SessionMiddleware) but did not include an explicit acceptance criterion:
"User B must see only their own playlists, not User A's." The manager correctly
implemented the specified design and validated against the written criteria.

### Miss 3 — ContextVar thread propagation looks correct on paper

The ContextVar approach is architecturally sound and matches Python documentation.
The propagation failure is a subtle CPython behavior under the specific combination
of asyncio, ThreadPoolExecutor, and Starlette's request lifecycle. It does not
trigger any test failure or import error. Only a live multi-user test reveals it.

---

## Process Fix Going Forward

Any multi-user feature gate must include an explicit live check:
> Log in as User A → verify User A sees their data → separately log in as User B
> (different browser or incognito) → verify User B sees **only** their own data.

This check must be performed by the chef before accepting multi-user isolation work,
regardless of test suite results. It cannot be delegated to the manager's
self-validation because it requires two real Spotify accounts and a running server.

---

## Blame Distribution

| Layer | Owner | Verdict |
|---|---|---|
| Chef gate missing live multi-user test | Chef | Primary miss |
| Implementation brief missing acceptance criterion | Chef | Contributing |
| Manager did not proactively add concurrency test | Manager | Contributing |
| Python ContextVar thread propagation subtlety | Language | Amplifier |

Net: **chef-owned gap**, consistent with prior review (2026-06-21) showing that
multi-user/concurrency scenarios require explicit chef live validation, not just
test-suite passes.
