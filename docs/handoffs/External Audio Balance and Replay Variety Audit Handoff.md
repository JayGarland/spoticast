# External Audio Balance and Replay Variety Audit Handoff

## Purpose

Commission an external auditor/inspector to evaluate two Resonova product-quality issues that remain after the mobile playback recovery work:

1. Commentary and Spotify music loudness still may not feel balanced.
2. Playlist-generated cast order variation exists, but the owner reports it still feels too rigid / not robust enough.

This is an audit request, not an implementation request. Produce findings, product judgment, and implementation recommendations with evidence. Do not patch first.

## Product Context

Resonova is a private, single-user AI radio/cast MVP:

- User chooses a Spotify playlist or track list.
- Server generates AI commentary and TTS host audio.
- Browser player interleaves commentary audio with Spotify Web Playback SDK music segments.
- Owner expects it to feel like a replayable personal radio companion, not a one-shot playlist summarizer.

The recent mobile foreground recovery work is now owner-validated enough to proceed with product-quality review:

- Recovery button appears after lockscreen failure.
- Recover Spotify works in the owner’s phone test.
- Current request is now about experience quality, not SDK recovery.

## Owner Feedback To Audit

### A. Volume / Loudness

Owner feedback:

> Commentary sounds smaller/quieter than Spotify music. The volume level between commentary segment and music does not match.

Known implementation:

- `resonova/web/player.js`
  - Commentary uses HTML audio with `this.audioEl.volume = 1`.
  - Spotify SDK player volume uses `_SPOTIFY_VOLUME = 0.62`.
  - Spotify volume is applied through constructor volume and `spotifyPlayer.setVolume(_SPOTIFY_VOLUME)`.
  - Existing docs note `setVolume()` may be a no-op on iOS / mobile contexts.
- `docs/strategy/audio-level-balance-brief.md`
  - Current frontend mitigation is `_SPOTIFY_VOLUME = 0.62`.
  - Backend commentary normalization was parked.

Audit question:

- Is frontend Spotify volume control enough for Resonova’s target mobile browser environment, or does the product need backend commentary loudness normalization / compression?
- What is the minimal reliable audio-level strategy for the MVP?

### B. Fixed/Rigid Cast Order

Owner feedback:

> Every time I play the generated cast from my playlist, it follows the same fixed playlist order and becomes boring. Current shuffle still feels too rigid or not robust.

Known implementation:

- `resonova/server.py`
  - `_select_playlist_tracks_for_episode(tracks)` does:
    - copy playlist tracks,
    - `random.shuffle()`,
    - apply `MAX_TRACKS`,
    - retry up to five times only to avoid exactly matching the original first `MAX_TRACKS`.
  - Direct pasted track lists preserve user order.
- `docs/strategy/playlist-order-variety-brief.md`
  - Current decision: shuffle playlist-generated casts by default; preserve pasted track order.
- `docs/handoffs/External Product UX Design Audit Handoff.md`
  - Already noted order variety only partly solves rigidity because it changes sequence, not content, voice, taste memory, or feedback.

Audit question:

- Is uniform random shuffle sufficient, or should Resonova use a stronger replay-variety algorithm?
- How should the app avoid feeling stale across repeated generations from the same playlist?
- Should this be solved only by order selection, or also by feedback/profile memory and prompt variation?

## Files To Inspect

- `resonova/server.py`
- `resonova/web/player.js`
- `resonova/api/gemini.py`
- `resonova/api/audio.py`
- `resonova/api/tts.py`
- `docs/strategy/audio-level-balance-brief.md`
- `docs/strategy/playlist-order-variety-brief.md`
- `docs/strategy/persistent-profile-feedback-brief.md`
- `docs/handoffs/External Product UX Design Audit Handoff.md`
- `docs/handoffs/Spotify SDK Foreground Recovery Implementation handoff.md`

## Commits / History To Inspect

Use `git show` and `git diff` directly:

- `783ddf1` — Balance Spotify music volume
- `1f07074` — Vary playlist cast order
- `e729f2b` — Add bounded Spotify SDK recovery

Useful commands:

```bash
git log --oneline -20
git show --stat --oneline 783ddf1 1f07074 e729f2b
git show 783ddf1 -- resonova/web/player.js docs/strategy/audio-level-balance-brief.md
git show 1f07074 -- resonova/server.py docs/strategy/playlist-order-variety-brief.md
```

## Specific Audit Tasks

### 1. Audio-Level Audit

Inspect:

- Whether `_SPOTIFY_VOLUME = 0.62` is a reliable cross-device fix.
- Whether Spotify SDK volume control is ineffective on the owner’s phone environment.
- Whether generated TTS audio files should be normalized server-side.
- Whether the right MVP fix is:
  - lower Spotify further,
  - raise/commentary normalize TTS,
  - add per-segment gain metadata,
  - use ffmpeg/pydub LUFS normalization,
  - add a user-facing balance slider,
  - or a combination.

Produce:

- Recommended target strategy.
- Minimal implementation path.
- Risks for saved old episodes vs future generated episodes.
- Acceptance test method for phone and desktop.

### 2. Replay-Variety / Shuffle Audit

Inspect:

- Current `_select_playlist_tracks_for_episode()` behavior.
- Whether `random.shuffle()` over the full playlist then slicing `MAX_TRACKS` is enough.
- Failure cases:
  - short playlists,
  - playlists with clustered artists/albums,
  - repeated generations selecting too many same tracks,
  - same opener/closer patterns,
  - no memory of prior generated order,
  - no energy/mood arc,
  - no novelty controls.

Evaluate possible algorithms:

- Recent-order avoidance persisted per playlist.
- Seeded shuffle with episode ID plus prior-run diversity.
- Weighted selection favoring not-recently-used tracks.
- Artist/album spacing rules.
- Energy arc rules using Spotify audio features.
- Owner taste/profile/feedback weighting.
- Explicit modes such as `Shuffle`, `Deep cut`, `Flow`, `Favorites`, `Surprise`.

Produce:

- Whether current shuffle should be kept, replaced, or extended.
- Minimal robust MVP algorithm.
- Data that must be persisted locally.
- How to preserve direct pasted track order.
- How Gemini prompt/cache keys should change if order/selection policy changes.

## Key Questions The Auditor Must Answer

1. Is the current audio balance fix (`_SPOTIFY_VOLUME = 0.62`) good enough for mobile, given SDK volume limitations?
2. Should Resonova normalize commentary audio at generation time, and if yes, where should that happen?
3. Should replay variety be solved by better ordering only, or by persistent memory/feedback as the real product fix?
4. What is the smallest implementation that makes repeat generations from the same playlist feel less stale?
5. What should remain parked until after the current MVP is stable?

## Non-Goals

- Do not change Spotify SDK recovery.
- Do not redesign the entire player UI.
- Do not implement persistent profile/feedback during the audit.
- Do not expose tokens, `.env`, or secrets.
- Do not patch code before producing findings.

## Expected Auditor Output

Return a report with:

- Findings ranked by severity/product impact.
- File and line references.
- Recommendation for audio balance.
- Recommendation for replay variety.
- Concrete next implementation brief suitable for RUG manager if a fix is approved.
- Explicit do-not-do list to avoid overbuilding.

## Current Working State

- Branch: `main`
- Latest relevant commit: `e729f2b Add bounded Spotify SDK recovery`
- Repo was clean before this handoff was created.
- Current owner-validated result: mobile recovery button appears and works.
