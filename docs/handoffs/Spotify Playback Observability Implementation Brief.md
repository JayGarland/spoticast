# Spotify Playback Observability Implementation Brief

Created: 2026-06-20
Owner: Chef/Codex gate
Target manager: RUG orchestrator
Status: approved for implementation

## Goal

Add mobile Spotify playback observability only. Do not change playback behavior in this task.

This is Item 1 from:

- `docs/handoffs/External Intermittent Mobile Spotify Playback Audit Report.md`

The purpose is to make the next real-phone failure diagnosable instead of guessing whether it was stale Spotify device, network offline, bfcache/page restore, or play-command-accepted-but-silent.

## Strict Scope

Modify only if needed:

- `resonova/web/player.js`
- `resonova/web/styles.css`
- `docs/handoffs/Spotify Playback Observability Implementation Handoff.md`

Do not modify:

- server auth/token code
- Spotify recovery behavior
- play/skip/previous behavior
- episode generation/cache behavior
- `.env`

## Required Behavior

Add an owner-only diagnostic event timeline that is visible only when the existing `Diag` panel is enabled.

The timeline must record bounded recent events, not unbounded logs.

Required event categories:

1. `online` / `offline`
   - Record `navigator.onLine` at startup.
   - Record browser `online` and `offline` events.
2. page lifecycle
   - Record `visibilitychange`.
   - Add and record `pageshow` and `pagehide`.
   - Include `event.persisted` for `pageshow/pagehide` where available.
3. Spotify device lifecycle
   - Add `deviceGeneration` counter.
   - Increment when the SDK reports a new `ready` device ID.
   - Record device ID in redacted form, for example last 6 chars only.
   - Record device acquisition timestamp or age.
4. recovery lifecycle
   - Record recovery start/success/failure.
   - Record device discard.
5. play command lifecycle
   - Record Spotify play command start.
   - Record HTTP status and truncated response body on failure.
   - Record playback-start verification result:
     - confirmed
     - blind mode
     - failed
6. deadline lifecycle
   - Record blind deadline armed/fired.
   - Record segment deadline armed/fired.

## Diagnostic UI

In the existing `Diag` panel:

- show:
  - `Online` yes/no
  - `Device gen`
  - `Device age`
- add an `Events` section listing the most recent timeline entries.
- add a copy button that copies the timeline text to clipboard.

Keep the panel compact enough for mobile.

## Hard Constraints

- No behavior change: do not alter recovery, timeouts, queue advancement, blind deadlines, or playback commands.
- No token or secret logging.
- Do not log full access tokens, full auth headers, or `.env` values.
- Device ID must be redacted.
- Keep event ring buffer bounded, suggested max 50 entries.
- Keep code local to the existing `ResonovaPlayer` class.
- No new dependencies.

## Acceptance Tests

Static:

```powershell
node --check resonova/web/player.js
uv run python -c "from resonova import server; print('server ok')"
git diff --check
```

Manual desktop smoke:

1. Start Resonova.
2. Enable `Diag`.
3. Confirm `Online`, `Device gen`, `Device age`, and `Events` appear.
4. Switch browser tab away/back.
5. Confirm events include `visibilitychange`.
6. Use browser devtools network offline/online if available.
7. Confirm events include `offline` and `online`.
8. Click copy timeline and confirm clipboard contains a readable text timeline.

Real-phone acceptance:

1. Enable `Diag`.
2. Play a cast until a Spotify segment.
3. Lock/idle phone long enough to trigger the intermittent issue.
4. Return to page.
5. Copy event timeline.
6. Timeline should make one branch clear:
   - offline/network interruption,
   - pageshow/pagehide or visibility restore,
   - stale device/discard/rebuild,
   - play accepted but playback start entered blind mode.

## Handoff Output

Create:

`docs/handoffs/Spotify Playback Observability Implementation Handoff.md`

Include:

- files changed
- exact behavior added
- verification commands and results
- whether there were any behavior changes
- real-phone test checklist
- risks / parked follow-up work

## Parked Follow-up Work

Do not implement these yet:

- stall-aware playback verification
- replacing blind playback behavior
- explicit offline UI state
- "Skip music, keep commentary"
- cast cache / loaded-cast management

Those require evidence from this observability pass.
