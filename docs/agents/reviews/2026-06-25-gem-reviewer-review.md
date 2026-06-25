# Agent Review — 2026-06-25 — gem-reviewer

## Role Tested

Internal Auditor / Security Reviewer (via direct invocation with `--deny-tool write`)

## Task Assigned

Security audit of `resonova/server.py` and `resonova/api/spotify.py`.
OWASP focus: A01 Broken Access Control, A02 Cryptographic Failures, A03 Injection,
SessionMiddleware cookie attributes.

## Inputs Provided

- Scoped brief naming two target files and four OWASP categories
- `--deny-tool write` to enforce read-only
- No PRD.yaml or DESIGN.md provided (not relevant for this audit)

## Output Summary

Returned structured JSON with 8 findings across three OWASP categories plus INFO notes.
Duration: 52s. Tokens: ↑331.3k (288.8k cached) / ↓3.5k. `Changes +0 -0`.

## Evidence

### Critical findings (chef-verified)

| Severity | Location | Finding | Verified |
|---|---|---|---|
| CRITICAL | `config.py:64` | `session_secret_key` default is `'change-me-in-production'`; forged session cookies possible if not overridden | ✅ Real |
| HIGH | `server.py:281` | `_resolve_redirect_uri()` trusts raw `Host` header to build OAuth redirect_uri; Host header injection → OAuth code capture | ✅ Real |
| HIGH | `server.py:50` | `SessionMiddleware` missing `secure=True`, `same_site="strict"` | ✅ Real |
| MEDIUM | `server.py:296-323` | No OAuth `state` parameter validation — session fixation variant possible | ✅ Real |
| MEDIUM | `server.py:312-318` | Allowlist denial message slightly leaks beta-access existence | Low priority |
| LOW | `server.py:201` | `user_id` read from session without cross-check against token_info user — mitigated by signed session | ✅ Real, low priority |
| INFO | `spotify.py:17` | Dev-mode OAuth cache at `.research_cache/.spotify_oauth` — stale token persistence risk in dev | Context-correct |

### Correct clean passes (no false positives)

- ContextVar `_per_session_client` isolation — correctly identified as safe
- `handle_callback_for_session` bypassing file cache — correctly identified as safe
- `subprocess.run` in `audio.py` — hardcoded command array, no user input, correctly cleared
- No SQL, eval, exec, template injection — correctly confirmed clean

## Strengths

- All findings cite `file:line`
- Correctly differentiated CRITICAL/HIGH/MEDIUM/LOW/INFO
- Scope discipline: only read target files + `config.py` (for SECRET_KEY) + `audio.py` (subprocess check)
- Returned structured JSON without prompting
- `Changes +0 -0` confirmed — `--deny-tool write` respected
- `confidence: 0.92` self-reported and consistent with finding quality
- A03 correctly returned "no critical issues" with evidence

## Failures / Risks

- None on this trial
- Expanded scope slightly to `config.py` and `audio.py` without explicit permission — appropriate judgment call; should remain rare

## Cost / Coordination Notes

- DeepSeek deepseek-v4-pro, in-process invocation (Start-Job env var inheritance issue noted — env vars must be set in-process or passed explicitly)
- 52 seconds, ~331k tokens (mostly cached)
- No worktree needed since `--deny-tool write` prevented any writes

## Decision

**use more** — strong first pass. All findings are real, structured, and cite specific file:line.
No false positives. Scope discipline was good. Correct "clean" verdicts on non-issues.

## Conditions For Future Use

- Always use `--deny-tool write` for audit-only runs
- Pass key explicitly in-process or via ArgumentList (not via Start-Job env inheritance alone)
- Works well for A01-A03 OWASP scans; for LLM-specific security (prompt injection) prefer `se-security-reviewer`
- Scope to ≤3-4 files per pass; large file sets will exceed context without guidance

## Follow-Up

Top 3 issues to fix (chef recommendation, pending boss approval):

1. **CRITICAL** — Enforce non-default `SECRET_KEY` at startup (assert or raise if value matches default)
2. **HIGH** — Add trusted-origin allowlist to `_resolve_redirect_uri()`, or require `REDIRECT_URI` env var in production
3. **HIGH** — Add `secure=True, same_site="strict"` to `SessionMiddleware` in `server.py`
