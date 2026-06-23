# Full Product Re-Audit — Chef Gate

Audience: Agents / Internal
Date: 2026-06-23
Auditor runtime: 3 bounded inspect-only passes, `gem-reviewer` on DeepSeek (Copilot CLI BYOK), read-only (`--deny-tool=write`), sandboxed to a worktree.
Chef: verified the decisive Blocker/High claims independently before accepting (the auditor has a documented over-claim tendency — see the prior `Internal Auditor Product Reviewer Trial Chef Gate.md`).

## How it ran

Full product re-audit split into 3 domain passes (per the single-vs-multi pre-flight: a 6-domain audit trips the context/decomposition triggers, so it was split into bounded single-agent passes and chef-synthesized):
1. Spotify playback + recovery + mobile lockscreen/background + bad-network.
2. Library + saved casts + replay variety + generation-complete + UX + diagnostics.
3. Memory controls + feedback fold + stance B + single-user guard + style derivation.

Near-zero cost (DeepSeek). Both worktree and main stayed clean. Each pass returned a severity-ranked, `file:line`-cited report.

## Parallel-commit reconciliation

The audit ran against a worktree snapshot. During the audit the boss committed `dd5c9b1` ("Relax hidden-page Spotify transition gate") to main, which **removed the mobile-only hidden-page defer block** in `player.js`. This **supersedes** Pass 1's desktop-hidden-tab finding — see below. All other findings are in code untouched by `dd5c9b1` and still stand. The `42b02ae` fold-threshold commit survived (it is `dd5c9b1`'s parent).

## Findings (chef-calibrated severity)

| Sev | Finding | Evidence | Verified | Notes |
|---|---|---|---|---|
| Blocker | **Blind Spotify playback still open.** `_waitForSpotifyPlaybackStart` returns success on `currentUri === uri && !state.paused` with no position-advance check; blind deadline = full `duration_ms + 3000`. SDK "playing" with no audio → silence for a whole track. | `resonova/web/player.js:1325`, `:1816-1829` | Chef-verified | This is the **prior trial's F1** — never fixed, not a new regression. |
| High | **"Memory off" drops ALL personalization, not just the trail.** `server.py` attaches the profile to the prompt only when `memory_enabled` is True, so the partial DURABLE-keep / TRAIL-drop logic already written in `gemini.py` is dead code. The toggle's promise ("keep durable taste, drop behavioral trail") is broken. | `resonova/server.py:580-584`, `resonova/api/gemini.py:329-348` | Chef-verified | Trust/honesty bug; only on the non-default memory-off path. Small, well-scoped fix (attach profile whenever not incognito; gemini.py already handles the split). |
| Med-High | **Stale-SSE hijack.** `intro_ready` calls `_startPlayback()` unconditionally without checking `_activeGenerationId`; back-from-generating never closes the old EventSource. gen1's intro can hijack the UI after the user starts gen2. | `resonova/web/player.js:1428-1433`, `:2971-2973`, `:1398` | Chef-verified | Real but narrow trigger window; single-user. Fix = one guard check + close stream. |
| Superseded | Pass 1 flagged the *mobile-only* hidden-page defer guard as exposing desktop hidden tabs. `dd5c9b1` removed that block entirely (deferral now reacts on hidden-page Connect failure). | (removed in `dd5c9b1`) | n/a | **Needs a real-device re-test of hidden-page behavior on the new code**, not the audit's wording. |
| Low (accept) | Owner guard `claim_or_check_owner` does check-then-write without a lock — theoretical first-connect race. | `resonova/profile.py:130-137` | Relayed | Vanishingly rare for single-user v0.1; already a parked item. |

**Stance B (boss top-of-mind): no bug.** The guardrail wording at `gemini.py:380-393` is comprehensive and fourth-wall-preserving (no "you", no inventory, no cross-cast history, no playlist contradiction). Optional hardening only: move the guardrail from the user-data section into the system prompt for stronger model compliance.

## Polish / parked (relayed; corroborates known items)

MediaSession album hardcoded + no lockscreen artwork (cosmetic); "Saving" status label opaque; progress step "context" maps to the "fetch" icon; already-parked field cleanup independently re-surfaced (`favorite_eras` dead, raw feedback `note` stored-but-unused, `user-read-email` unused scope). Reset-clears-`feedback.jsonl` verified working.

## Release-readiness verdict

**Not ready for broader customer testing** until the **blind-playback blocker** and the **memory-off honesty bug** are fixed. Stale-SSE and the rest are fix-soon, not gate.

## Recommended next actions (implementation → manager-route + gate-before-commit)

Boss approved queuing all three (2026-06-23):
1. **Blind playback (F1):** add two-sample position verification to `_waitForSpotifyPlaybackStart`; shorten the blind deadline with a re-check. (Own slice — subtle timing, higher risk.)
2. **Memory-off honesty fix:** attach the profile regardless of `memory_enabled` (not incognito) so `gemini.py`'s existing DURABLE/TRAIL split runs.
3. **Stale-SSE guard:** check `_activeGenerationId` in `intro_ready`; close the old EventSource on back-from-generating.

Suggested slicing: (2)+(3) bundled (tiny, low-risk); (1) on its own. Frontend changes require `node --check resonova/web/player.js` + a browser load in the chef gate.

## Boss decisions still open

- Real-device re-test of hidden-page Spotify behavior on `dd5c9b1`.
- Routing/sequencing of the three fixes (chef to confirm before routing a manager).
