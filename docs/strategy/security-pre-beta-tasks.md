---
title: "Security Pre-Beta Task Tracker"
created: 2026-06-25
source: gem-reviewer OWASP audit (trial run, 2026-06-25)
audience: Boss / Chef
---

# Security Pre-Beta Task Tracker

Source: gem-reviewer OWASP audit conducted 2026-06-25 on current codebase.

---

## Finding #1 — Weak SESSION_SECRET_KEY default (CRITICAL)

**Status: Mitigated + hardened**

The `config.py` default `"change-me-in-production"` is dangerous for any shared deployment.

- `.env` already had `SESSION_SECRET_KEY=bcfde115…` (64-char hex) — mitigated in production.
- Commit `ccf10b4` added a startup `RuntimeError` that refuses to boot if the default is still set.

No further action needed.

---

## Finding #2 — Host header injection in `_resolve_redirect_uri()` (HIGH)

**Status: Mitigated in production**

`server.py:_resolve_redirect_uri()` trusted the raw `Host` header when building the OAuth redirect URI. A spoofed request could redirect auth callbacks to an attacker domain.

- Mitigated: `REDIRECT_URI` env var is set in production (commit `2d56957` / Cloudflare Tunnel setup), which bypasses the Host-header path entirely.
- The unsafe code path still exists when `REDIRECT_URI` is unset.

**Action before open beta**: add server-side allowlist validation of the resolved redirect URI against known configured values, rather than relying on env var presence.

---

## Finding #3 — SessionMiddleware missing Secure flag / explicit SameSite (HIGH)

**Status: Fixed — commit `ccf10b4`**

- `https_only=settings.use_https` — Secure cookie flag in HTTPS deployments.
- `same_site="lax"` — explicit; kept lax (not strict) because the Spotify OAuth callback is a cross-site redirect that strict would drop.

No further action needed.

---

## Finding #4 — Missing OAuth CSRF state parameter (MEDIUM)

**Status: OPEN — pre-beta required**

`/auth/spotify` initiates the OAuth flow without generating or validating a `state` parameter. An attacker could craft a `/auth/callback?code=…` request and inject a Spotify session into a logged-in user's browser (CSRF).

**What to implement:**
1. On `/auth/spotify`: generate a random token (`secrets.token_urlsafe(32)`), store it in the session (`request.session["oauth_state"] = token`), and pass it to Spotify as `&state=<token>`.
2. On `/auth/callback`: compare `request.query_params.get("state")` against `request.session.pop("oauth_state", None)`. Reject with 400 if they don't match or if either is missing.

**Files to change:** `resonova/server.py` — the `/auth/spotify` and `/auth/callback` route handlers.

**Priority:** Park until Option B multi-user work is complete. Must be done before open beta (Option C). CSRF matters more once the allowlist is removed and arbitrary users can initiate auth flows.

---

## Summary

| # | Finding | Severity | Status |
|---|---|---|---|
| 1 | Weak SESSION_SECRET_KEY default | CRITICAL | Done — startup guard added |
| 2 | Host header injection | HIGH | Mitigated in prod; harden before open beta |
| 3 | SessionMiddleware cookie hardening | HIGH | Done — commit ccf10b4 |
| 4 | Missing OAuth CSRF state parameter | MEDIUM | **Open — do before open beta** |
