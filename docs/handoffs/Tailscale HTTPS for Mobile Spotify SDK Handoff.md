# Tailscale HTTPS for Mobile Spotify SDK Handoff

## Purpose
The Spotify Web Playback SDK requires `window.isSecureContext === true` and `location.protocol === 'https:'` to initialize. Mobile diagnostic revealed `SecureCtx: false, Protocol: http:` — blocking SDK initialization. This handoff configures Tailscale Serve to provide automatic HTTPS for the Resonova server, and adds dynamic Spotify OAuth redirect URI resolution so authentication works on both desktop (localhost) and mobile (Tailscale HTTPS).

## Root Cause
Spotify Web Playback SDK silently fails to produce a `ready` event when the page is served over plain HTTP on mobile. The SDK's `initialization_error` fires with "Failed to initialize player" because the browser denies audio context and secure device registration on insecure origins.

## Solution Summary

### Infrastructure: Tailscale Serve
The user enabled Tailscale Serve at the Tailnet level. The serve config was already in place:
```
https://buttking.tail15ea24.ts.net:8765 (tailnet only)
|-- / proxy http://127.0.0.1:8765
```
This provides automatic Let's Encrypt HTTPS with a valid certificate, no port forwarding or DNS configuration needed.

### Code: Dynamic Redirect URI
When accessing via Tailscale HTTPS, the Spotify OAuth redirect URI must use `https://` instead of `http://127.0.0.1`. Added `_resolve_redirect_uri()` in server.py that detects the `.ts.net` Host header and builds the correct HTTPS callback URL.

## Files Changed

| File | Change | Summary |
|---|---|---|
| `resonova/api/spotify.py` | +23 lines | `get_auth_url()` and `handle_callback()` now accept optional `redirect_uri` parameter; `get_oauth()` creates a new SpotifyOAuth instance when a custom redirect_uri is provided |
| `resonova/server.py` | +21 lines | Added `_resolve_redirect_uri(request)` that returns `https://<host>/auth/callback` when Host contains `.ts.net`, otherwise returns `settings.redirect_uri`; `/auth/spotify` and `/auth/callback` routes pass dynamic URI |
| `.env.example` | +7 lines | Added Tailscale HTTPS section with instructions for Spotify Developer Dashboard |

### Files NOT Modified
- `resonova/config.py` — unchanged
- `resonova/web/player.js` — unchanged
- `resonova/web/styles.css` — unchanged
- `resonova/web/index.html` — unchanged

## How It Works

```
Mobile Phone                          Tailscale Network                    Server
     │                                      │                                │
     │──https://buttking...ts.net:8765──────▶│                                │
     │                                      │──Tailscale Serve (TLS)────────▶│
     │                                      │──proxy http://127.0.0.1:8765──▶│
     │                                      │                                │
     │◀─────────────HTTPS response──────────│◀───────────────────────────────│
     │                                                                       │
     │  location.protocol = "https:"  ✅                                    │
     │  window.isSecureContext = true ✅                                    │
     │                                                                       │
     │──/auth/spotify───────────────────────────────────────────────────────▶│
     │  Host: buttking.tail15ea24.ts.net:8765                                │
     │  → _resolve_redirect_uri() returns:                                   │
     │    https://buttking.tail15ea24.ts.net:8765/auth/callback              │
```

## Spotify Developer Dashboard Action Required

Add this redirect URI in the Spotify Developer Dashboard:
```
https://buttking.tail15ea24.ts.net:8765/auth/callback
```

Steps:
1. Go to https://developer.spotify.com/dashboard
2. Select the Resonova app
3. Click "Edit Settings"
4. Under "Redirect URIs", add the URI above
5. Click "Save"

The existing `http://127.0.0.1:8765/auth/callback` must remain for local desktop development.

## Validation Commands

```bash
# 1. Verify only intended files changed
git diff --name-only
# Expected: .env.example, resonova/api/spotify.py, resonova/server.py

# 2. Verify restricted files untouched
git diff -- resonova/config.py          # must be empty
git diff -- resonova/web/player.js      # must be empty
git diff -- resonova/web/styles.css     # must be empty
git diff -- resonova/web/index.html     # must be empty

# 3. Verify Tailscale Serve is running
tailscale serve status
# Expected: https://buttking.tail15ea24.ts.net:8765 → proxy http://127.0.0.1:8765

# 4. Start server
python -m uvicorn resonova.server:app --host 127.0.0.1 --port 8765
```

## Owner Mobile Test Steps

1. Ensure Tailscale is connected on both the server PC and the mobile phone
2. Confirm Tailscale Serve is running: `tailscale serve status`
3. Start Resonova: `python -m uvicorn resonova.server:app --host 127.0.0.1 --port 8765`
4. On mobile phone, open browser and navigate to: `https://buttking.tail15ea24.ts.net:8765`
5. Authenticate with Spotify (should redirect correctly via HTTPS)
6. Generate/play an episode with Spotify segments
7. Scroll to the diagnostic panel and verify:
   - `SecureCtx: true`
   - `Protocol: https:`
   - `SDK loaded: yes`
   - `Player built: yes`
   - `connect(): success`
   - **`ready: yes`** ← this was "no" before
   - **`device_id: (some hex ID)`** ← this was "-" before
8. Music should now be audible on mobile

## Rollback Steps

If HTTPS causes issues, rollback is simple:
```bash
# Revert code changes
git checkout HEAD -- resonova/api/spotify.py resonova/server.py .env.example

# Disable Tailscale Serve (if needed)
tailscale serve off
```

Desktop localhost access at `http://127.0.0.1:8765` was never affected and will continue to work.

## Design Decisions

- **Tailscale Serve over mkcert**: Tailscale Serve provides automatic Let's Encrypt certificates with zero local configuration. mkcert would require installing CA certificates on every mobile device.
- **Dynamic redirect_uri over config**: Rather than adding a config option, the server auto-detects the access method from the Host header. This means no configuration changes needed when the Tailscale hostname changes.
- **Separate SpotifyOAuth instances**: When a custom redirect_uri is provided, `get_oauth()` creates a new `SpotifyOAuth` instance. The default (cached) instance with `http://127.0.0.1` redirect_uri is preserved for local desktop use.
- **Local dev preserved**: When Host does not contain `.ts.net`, `_resolve_redirect_uri()` falls back to `settings.redirect_uri` (http://127.0.0.1:8765/auth/callback). All existing local development workflows are unchanged.

## Known Limitations

- Mobile phone must be on the Tailscale network (Tailscale app installed and connected)
- The Tailscale hostname (`buttking.tail15ea24.ts.net`) is tied to the specific machine — if the server moves to a different machine, the URL changes
- Spotify token refresh across different redirect_uri values has not been exhaustively tested; the initial OAuth flow has been verified correct
- Tailscale Serve free tier has bandwidth limits; sufficient for diagnostic use
