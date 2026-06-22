# Mobile Playback — Background/Lock Continuity Brief

Audience: Agents
Status: Diagnosis accepted, approach decided (2026-06-22). Not yet implemented — queued build item.
Relates to: the "Next Technical Gate" in `docs/strategy/agent-performance-weights-2026-06-19.md`.

## Diagnosis (accepted)

From a real mobile log: `play:cmd:fail 404:device-not-visible`, `Spotify device unavailable while
page hidden`, `visibilitychange hidden`.

Root cause: while Chrome on the phone is backgrounded/locked, the Spotify **Web Playback SDK**
browser device can be locally "ready" but **not visible to Spotify Connect**. Resonova then tries
to start a Spotify segment, Spotify returns device-not-found/visible (404), and recovery is only
possible once the page is visible again. This is a **browser/platform limitation**, not an
auth/network failure. The current graceful handling is correct as far as it goes.

## Decision (chef)

Implement the near-term flow fix as **one bundle** (items 1–4 are complementary steps of a single
solution, not alternatives); item 5 is the acknowledged long-term reality, not now.

1. **Do not start a Spotify segment while `document.hidden`.** If the current segment is Spotify
   and the page is hidden, mark it `pending_unlock` instead of firing `/me/player/play`.
2. **Auto-resume on `visibilitychange → visible`.** On unlock/return: run recovery, verify the
   device is visible to Connect, then start the exact pending track.
3. **Keep "Skip Music" as fallback.** If recovery still fails, the user can continue the cast.
4. **Not a fatal error.** UI copy stays "Spotify waiting for phone unlock," never "Spotify
   playback failed" — because it is a platform limitation, not a crash.
5. **Long-term (separate, deferred):** a native mobile app, or using the Spotify app as the
   external player. The browser Web Playback SDK cannot reliably behave like a background native
   music service. Do NOT scope this into the near-term fix.

## Why this and not "pick one"

Items 1–4 are the coherent browser-side fix and should ship together. Item 5 is a different,
larger product direction (native/external player) that the near-term fix buys time for. So the
decision is: ship 1–4 as the next mobile-continuity slice; record 5 as the eventual real fix.

## Acceptance (for the future implementer)

- Hidden page + Spotify segment → no `/me/player/play` call; segment marked pending_unlock.
- Return to visible → recovery runs, device-visible verified, exact pending track starts.
- Recovery failure → "Skip Music" fallback works; no fatal-error state.
- All user-facing copy for this path reads as "waiting for unlock," not failure.
- Verify on a real phone (lock/unlock mid-cast at a Spotify segment boundary).

## Sequencing note

This is a real product gate but independent of the current memory/companion build. Queue it; it is
a good bounded slice for a manager (RUG) once prioritized. Needs real-device verification (only the
boss can do that).
