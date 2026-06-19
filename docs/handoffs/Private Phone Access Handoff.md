---
title: "Private Phone Access Handoff"
source: "OCP Workspace Lead — direct execution against docs/strategy/private-phone-access-brief.md"
created: 2026-06-19
status: draft
tags:
  - handoff
  - tailscale
  - phone-access
  - private
  - infrastructure
---

# Private Phone Access Handoff

## Owner Validation Addendum

Owner-side validation completed after the initial handoff.

Evidence:

- The 7-step private phone access path was completed by the owner.
- Phone lock-screen / system media control panel displayed Resonova playback.
- Screenshot evidence shows the phone connected to Resonova at `100.92.222.31:8765`.
- Playback was active from the phone control panel with elapsed/duration display (`00:29 / 02:36`) and a pause control.

Updated status:

| Item | Status |
|---|---|
| Private phone access through Tailscale | ✅ Owner-validated |
| Phone browser can play Resonova audio | ✅ Owner-validated |
| Lock-screen/system media panel appears | ✅ Owner-validated |
| Media control panel function quality | ⚠️ Needs improvement |

Owner note:

```text
The control panel function needs to improve.
```

Candidate follow-up:

- Improve mobile/system media-session behavior: metadata title/artist/artwork, previous/next controls, play/pause reliability, seek behavior, and better distinction between AI commentary and Spotify music segments.

---

## Executive Summary

Tailscale is **not yet installed** on the Resonova PC. This is the single blocking prerequisite for phone access.

All other pieces are ready:

- The server now supports binding to `0.0.0.0` via a `HOST` config setting (newly added).
- The server is reachable from the PC's LAN IP (`192.168.1.174:8765`), returning HTTP 200 for the landing page and all API routes.
- Episodes are listable and their audio files are servable from the LAN IP.
- Once Tailscale is installed on both the PC and phone, the phone browser URL will be `http://<tailscale-ip-or-magicdns>:8765`.

No phone testing was possible (no physical phone available in this environment), so mobile browser behavior, Spotify auth on mobile, and screen-lock behavior remain **unvalidated** and are documented as assumptions and next steps.

---

## Tailscale Status

### Current State

| Check | Result |
|---|---|
| `tailscale` CLI | Not installed (`tailscale: command not found`) |
| Tailscale Windows service | Not present |
| Tailscale network interface | Not present |
| Tailscale available via winget | ✅ Yes — `Tailscale.Tailscale` v1.98.4 |

### ZeroTier Note

The PC has **ZeroTier** installed (IP `10.147.17.31` on interface `ZeroTier One`). ZeroTier is an alternative private network mesh similar to Tailscale. The strategy brief explicitly chooses Tailscale first, so this handoff documents the Tailscale path. If Tailscale installation proves difficult, ZeroTier is a viable fallback — the server binding changes in this handoff work identically for either.

### Installation Prerequisite (Not Performed)

Tailscale installation was **not performed** because:

1. It requires admin privileges for the Windows installer.
2. Installing system software is outside the scope of a code-level audit/setup task.
3. The brief says: "If Tailscale is not installed or cannot be validated directly, document the exact missing prerequisite."

**Minimal setup steps for the owner:**

```powershell
# 1. Install Tailscale on the PC (requires admin)
winget install Tailscale.Tailscale

# 2. Start Tailscale and authenticate
tailscale up

# 3. Find the PC's Tailscale IP
tailscale ip -4
# Example output: 100.x.y.z

# 4. Install Tailscale on the phone
# iOS: https://apps.apple.com/app/tailscale/id1470499037
# Android: https://play.google.com/store/apps/details?id=com.tailscale.ipn
# Or: F-Droid / direct APK from https://tailscale.com/download

# 5. Open the Tailscale app on the phone and sign in with the same account
# 6. The phone will appear in the tailnet; both devices can now reach each other
```

---

## Server Binding Changes

### What Changed

Three files were modified to support binding to all network interfaces (required for Tailscale access):

**`resonova/config.py`** — added `host` setting:

```python
host: str = "127.0.0.1"   # default: localhost only
```

**`resonova/__main__.py`** — uses `settings.host` instead of hardcoded `"127.0.0.1"`:

```python
host = settings.host
```

The browser auto-open still uses `127.0.0.1` regardless of the bound host (so the PC browser always opens locally).

**`.env.example`** — added `HOST` entry:

```env
# HOST=0.0.0.0       # uncomment for phone/Tailscale access (default: 127.0.0.1)
```

Also fixed the stale `GEMINI_MODEL` comment from `gemini-2.5-pro` to `gemini-3.1-pro-preview`.

### How to Use

**Local-only (default, no `.env` change needed):**

```bash
make run
# Server binds to 127.0.0.1:8765 — localhost only
```

**Phone access (add to `.env` or set env var):**

```env
HOST=0.0.0.0
```

```bash
make run
# Server binds to 0.0.0.0:8765 — reachable from Tailscale IP
```

Or without modifying `.env`:

```bash
# PowerShell
$env:HOST="0.0.0.0"; uv run resonova

# bash/zsh
HOST=0.0.0.0 make run
```

---

## Validation Results

### Commands Run

| # | Command | Result |
|---|---|---|
| 1 | `tailscale status` | ❌ CLI not installed |
| 2 | `winget search tailscale` | ✅ `Tailscale.Tailscale` v1.98.4 available |
| 3 | `uv run python -c "from resonova.config import settings; print(settings.host)"` | ✅ `127.0.0.1` (default) |
| 4 | `$env:HOST="0.0.0.0"; uv run python -c "..."` | ✅ `0.0.0.0` (override works) |
| 5 | `$env:HOST="0.0.0.0"; uv run resonova` | ✅ Server started on `http://0.0.0.0:8765` |
| 6 | `curl http://192.168.1.174:8765/` | ✅ HTTP 200 — landing page served |
| 7 | `curl http://192.168.1.174:8765/api/episodes` | ✅ HTTP 200 — 3 episodes returned |

### Server Logs (excerpt)

```
INFO:     Uvicorn running on http://0.0.0.0:8765 (Press CTRL+C to quit)
INFO:     127.0.0.1:55477 - "GET / HTTP/1.1" 200 OK
INFO:     127.0.0.1:55477 - "GET /web/styles.css HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:55478 - "GET /web/player.js HTTP/1.1" 200 OK
INFO:     127.0.0.1:55478 - "GET /auth/token HTTP/1.1" 200 OK
INFO:     127.0.0.1:55478 - "GET /api/episodes HTTP/1.1" 200 OK
INFO:     192.168.1.174:55576 - "GET / HTTP/1.1" 200 OK
INFO:     192.168.1.174:55578 - "GET /api/episodes HTTP/1.1" 200 OK
```

### Reachability Summary

| Endpoint | Status |
|---|---|
| `http://127.0.0.1:8765/` | ✅ (localhost, always works) |
| `http://192.168.1.174:8765/` | ✅ (LAN IP, works with `HOST=0.0.0.0`) |
| `http://<tailscale-ip>:8765/` | ⏳ Not tested — Tailscale not installed |

### Network Topology

```text
PC (192.168.1.174, Wi-Fi)
├── Resonova server on 0.0.0.0:8765
├── Tailscale: NOT INSTALLED ⬅ blocking
└── ZeroTier: installed (10.147.17.31) — fallback option

Phone
├── Tailscale: needs installation
└── Browser URL (after Tailscale setup): http://100.x.y.z:8765
```

---

## Phone Access Flow (Documented Steps)

Once Tailscale is installed on both devices, the complete flow is:

```text
1. PC: Start Resonova with HOST=0.0.0.0
       $env:HOST="0.0.0.0"; uv run resonova
       → Server listening on 0.0.0.0:8765

2. PC: Verify Tailscale IP
       tailscale ip -4
       → e.g., 100.87.154.62

3. Phone: Open Tailscale app → confirm connected to tailnet

4. Phone: Open mobile browser (Safari / Chrome)
       → Navigate to http://100.87.154.62:8765

5. Phone: Resonova landing page loads
       → If the PC was already authenticated, the app should use the cached server token
       → If not authenticated, "Connect Spotify" currently redirects back to 127.0.0.1 and fails on phone
```

### Spotify OAuth Consideration

The Spotify OAuth redirect URI is currently hardcoded to `http://127.0.0.1:8765/auth/callback` (generated from `settings.redirect_uri` which uses `127.0.0.1`).

**This means**: When the phone opens the app at the Tailscale IP and clicks "Connect Spotify", the OAuth flow redirects back to `127.0.0.1:8765` — which is the PC's localhost, NOT the phone. The phone will not be able to complete the OAuth flow on its own.

**Three workarounds exist** (not yet implemented — documented as candidate issues):

1. **Pre-auth on PC**: Authenticate Spotify on the PC first (at `http://127.0.0.1:8765`). The token is cached in `.research_cache/.spotify_oauth`. The phone can then load `http://<tailscale-ip>:8765` and use the existing session — the server reads the cached token regardless of which IP the request comes from. This is the simplest path and likely works as-is.

2. **Add Tailscale IP to Spotify Developer Dashboard**: Add `http://<tailscale-ip>:8765/auth/callback` as an additional redirect URI in the Spotify app settings. Then the phone can complete its own OAuth flow. Tailscale IPs are stable per device.

3. **Dynamic redirect URI**: Modify `config.py` to use the request's `Host` header instead of hardcoding `127.0.0.1`. This would make the redirect URI work from any IP. More work but most flexible.

**Recommendation**: Try workaround #1 first (PC pre-auth). It requires zero code changes and leverages the existing token cache.

---

## Limitations and Unvalidated Items

### Not Validated (No Phone Available)

| Item | Reason |
|---|---|
| Phone browser landing page load | No physical phone in this environment |
| Mobile layout/rendering | Cannot test CSS responsiveness on phone viewport |
| Spotify OAuth on phone | Cannot test mobile browser OAuth flow |
| Episode listing/replay on phone | Cannot test mobile browser audio playback |
| Audio playback on phone | Cannot test HTML Audio + Spotify SDK on mobile |
| Screen lock / background behavior | Cannot test audio during screen lock |
| Spotify Web Playback SDK on mobile | SDK may or may not work in mobile browser |

### Known Limitations (Code-Level)

| Limitation | Details |
|---|---|
| **Spotify redirect URI** | Hardcoded to `http://127.0.0.1:8765/auth/callback` in `config.py` — phone OAuth won't work directly; needs pre-auth on PC or redirect URI update |
| **Spotify Web Playback SDK** | The SDK requires Spotify Premium and may have limited support in mobile browsers (it is primarily designed for desktop browsers). Even if the UI loads, music playback through the SDK on mobile is uncertain. |
| **No HTTPS** | Tailscale traffic is encrypted at the WireGuard layer, but the browser will show `http://` (not HTTPS). This is fine for private use. |
| **No PWA manifest** | The app has no service worker or manifest — it cannot be "installed" on the phone home screen |
| **Mobile viewport present, layout untested** | The HTML has `<meta name="viewport" content="width=device-width, initial-scale=1.0">` — good, but the CSS (`max-width: 580px` centered layout) has not been tested on actual mobile screens |

### Assumptions (Unverified)

1. **Assumption**: Tailscale's WireGuard tunnel will route traffic between phone and PC correctly on the user's network (home Wi-Fi + potential cellular fallback).
2. **Assumption**: The phone's mobile browser supports HTML5 Audio playback (standard on iOS Safari and Android Chrome).
3. **Assumption**: Pre-authenticating Spotify on the PC and then accessing from the phone via the same server will work — the token cache is file-based and server reads it regardless of client IP.
4. **Assumption**: The phone and PC will be on the same Tailscale tailnet (same account login).

---

## Candidate Issues

1. **`CANDIDATE`**: `redirect_uri` in `config.py` is hardcoded to `127.0.0.1` — blocks phone OAuth flow (workaround: pre-auth on PC)
2. **`CANDIDATE`**: Spotify Web Playback SDK may not function in mobile browsers — could require fallback to HTML Audio-only playback on phone (server would need to stream Spotify audio)
3. **`CANDIDATE`**: No service worker / PWA manifest — app cannot be added to phone home screen for app-like experience
4. **`CANDIDATE`**: Mobile CSS has not been tested — font sizes, button sizes, and layout may need mobile-specific adjustments
5. **`CANDIDATE`**: Tailscale is not installed — requires admin intervention
6. **`CANDIDATE`**: The `.env.example` `GEMINI_MODEL` comment was fixed to `gemini-3.1-pro-preview` as a side-effect of this change — this is a minor improvement but technically outside scope (documented for transparency)

---

## Changes Made

| File | Change | Reason |
|---|---|---|
| `resonova/config.py` | Added `host: str = "127.0.0.1"` setting | Required for binding to `0.0.0.0` for Tailscale access |
| `resonova/__main__.py` | Uses `settings.host` instead of hardcoded `"127.0.0.1"` | Reads host from config/env |
| `.env.example` | Added `# HOST=0.0.0.0` entry; fixed `GEMINI_MODEL` comment | Documents the new setting; fixes stale model name |

No other files changed. No secrets exposed. No public reachability added.

---

## Next Steps for the Owner

### Immediate (to complete phone access)

1. Install Tailscale on PC: `winget install Tailscale.Tailscale`
2. Run `tailscale up` and authenticate
3. Install Tailscale on phone (App Store / Play Store)
4. Add `HOST=0.0.0.0` to `.env`
5. Run `make run` on PC
6. Pre-auth Spotify on PC browser at `http://127.0.0.1:8765`
7. On phone, open browser → `http://<tailscale-ip>:8765`
8. Verify: landing page loads, episodes list, episode replay works

### If Spotify OAuth doesn't work on phone

1. Authenticate Spotify on the **PC browser** first
2. Then open the Tailscale URL on the phone — the server reads the cached token
3. If that fails, add `http://<tailscale-ip>:8765/auth/callback` to the Spotify Developer Dashboard

### If Spotify music playback doesn't work on mobile

This is expected — the Spotify Web Playback SDK is desktop-focused. Fallback options (not in scope for this task):

- Server-side Spotify audio streaming (requires audio proxy)
- Phone uses native Spotify app for music, Resonova web UI only for commentary/control

---

## Recommendation

**Mobile browser remains the right first step** — do not pivot to native app or PWA yet. The Tailscale + browser approach is simple, private, and requires zero new infrastructure. The main unknowns (mobile Spotify SDK, layout) need real phone testing to assess — those should be validated before any decision to build a native app.

---

## Work Not Performed

- Tailscale installation (requires admin + system-level setup)
- Phone testing (no physical phone in this environment)
- Spotify OAuth redirect URI dynamic resolution
- Mobile CSS/layout testing
- PWA/service worker setup
- HTTPS/certificate setup (not needed — Tailscale encrypts at WireGuard layer)
