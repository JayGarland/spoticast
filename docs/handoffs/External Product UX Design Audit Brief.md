# External Product UX Design Audit Brief

## Purpose

This handoff is for an external AI auditor/inspector. The auditor should evaluate Resonova at both:

- user experience level, by using a browser/Chrome MCP server against the running app
- design/product level, by inspecting the codebase, docs, handoffs, and git history

The auditor should not implement code. The output should be an evidence-backed audit report and prioritized recommendations.

## Product Goal

Resonova is a personal AI radio/cast companion.

Current MVP:

```text
Spotify playlist
-> AI-generated cast/radio script
-> Gemini TTS host commentary
-> browser playback interleaving commentary and Spotify music
```

Ultimate direction:

```text
Resonova should become a personal AI radio companion that grows with the owner's listening history, taste profile, feedback, and repeated use.
```

The product should feel personal, replayable, and alive rather than like a one-shot playlist summarizer.

## Current Known State

The app is local/private-first and single-user.

Recent accepted milestones:

- Private phone access via Tailscale.
- Tailscale HTTPS fixed Spotify Web Playback SDK mobile initialization.
- Mobile SDK diagnostics showed `SecureCtx=true`, `Protocol=https:`, `ready=yes`, and `device_id` after HTTPS.
- Developer diagnostic panel can now be toggled from the ON AIR header rail.
- Playlist-generated casts now vary track order by default.

Current known UX issue:

- Phone lockscreen/control panel only exposes pause/play for the current segment. The owner cannot reliably go to previous or next segment from phone controls.

## What Is Parked

Do not treat these as completed:

- Persistent taste/profile memory.
- Thumbs up/down or segment feedback.
- Comparable app research.
- Product vision and roadmap expansion.
- PWA/native app decision.
- Spotify preview URL fallback.
- Full Media Session controls.
- Mobile playback hardening beyond current diagnostics/toggle.

Reference: `docs/strategy/mobile-playback-hardening-brief.md`

## Required Repository References

Start with these:

- `README.md`
- `pyproject.toml`
- `.env.example`
- `docs/strategy/operating-model.md`
- `docs/strategy/resonova-mvp-audit-brief.md`
- `docs/strategy/persistent-profile-feedback-brief.md`
- `docs/strategy/mobile-playback-hardening-brief.md`
- `docs/strategy/playlist-order-variety-brief.md`
- `docs/strategy/agent-performance-weights-2026-06-19.md`
- `docs/handoffs/Resonova MVP Audit Handoff.md`
- `docs/handoffs/Private Phone Access Handoff.md`
- `docs/handoffs/Tailscale HTTPS for Mobile Spotify SDK Handoff.md`
- `docs/handoffs/Diagnostic Panel Toggle Handoff.md`

Implementation areas to inspect:

- `resonova/server.py`
- `resonova/api/spotify.py`
- `resonova/api/gemini.py`
- `resonova/api/tts.py`
- `resonova/api/research.py`
- `resonova/api/lastfm.py`
- `resonova/web/index.html`
- `resonova/web/player.js`
- `resonova/web/styles.css`
- `resonova/episodes.py`

## Relevant Git History

Inspect recent commits:

```bash
git log --oneline -30
```

Important recent commits:

- `1f07074 Vary playlist cast order`
- `fef63ab Add diagnostic panel toggle`
- `7934b0a Document mobile playback hardening plan`
- `38d2779 Support Tailscale HTTPS Spotify callbacks`
- `d0ea11a Add mobile Spotify SDK lifecycle diagnostics`
- `6e23bc1 Make mobile Spotify diagnostics visible`
- `b0347e0 Rollback failed mobile playback recovery`
- `5a533c9 Add OCP workspace skills, handoff docs, and MVP audit brief`
- `0901bc6 Rename project from Spoticast to Resonova`

The history includes failed/reverted mobile playback attempts. Treat this as useful evidence: avoid recommending broad recovery loops without proof.

## Browser / Chrome MCP Audit Tasks

Use the running app if available.

Likely URLs:

- Desktop local: `http://127.0.0.1:8765`
- Tailscale HTTPS: `https://buttking.tail15ea24.ts.net:8765`

If the server is not running, report that and include startup instructions rather than guessing.

Audit tasks:

1. Open the app and document the first-run flow.
2. Evaluate whether the first screen communicates "personal AI radio companion" or just "paste a playlist."
3. Inspect playlist selection, generation, progress, and playback screens.
4. Check desktop responsive layout and mobile viewport layout.
5. Inspect the ON AIR header, Skip control, Diag toggle, and playback progress.
6. Assess whether the diagnostic toggle is discoverable but not user-facing noise.
7. Evaluate phone/lockscreen control expectations conceptually, especially previous/next segment support.
8. If authenticated Spotify state is unavailable, still evaluate unauthenticated and static UI states.

Do not expose secrets or inspect `.env` values.

## UX Questions To Answer

### Core Journey

- Can a first-time user understand what Resonova does?
- Is the transition from playlist input to generated cast clear?
- Does the generation progress feel trustworthy while waiting?
- Does the playback screen explain what is commentary versus Spotify music?
- Does the replay/library experience make sense?

### Repeat Use

- Does the app invite repeated listening?
- Does the playlist-order variation solve enough of the rigidity problem?
- What still makes the app feel stateless or repetitive?
- Where should persistent memory and feedback appear without overbuilding?

### Mobile

- Does the phone layout feel usable?
- Are playback controls reachable?
- Is there an obvious way to skip next/previous from the app UI?
- What should appear in phone lockscreen/control panel controls?
- Would a PWA or Media Session API meaningfully improve perceived product quality?

### Design

- Does the visual system support the product identity: intelligent personal radio, not a generic AI tool?
- Are typography, spacing, controls, and states consistent?
- Is the diagnostic/developer tooling visually separated from user-facing controls?
- Are cards, buttons, and progress indicators used appropriately?
- What are the top visual polish issues?

### Product Strategy

- What should be the next product milestone after the local MVP?
- Should the next investment be persistent memory, feedback, Media Session controls, PWA/native packaging, or roadmap/comparable-app research?
- What should remain explicitly parked?

## Expected Output

Create a report under:

```text
docs/handoffs/External Product UX Design Audit Handoff.md
```

The report must include:

- Executive summary.
- What was inspected.
- Browser/MCP validation results.
- UX findings with severity.
- Design findings with severity.
- Product strategy findings.
- Mobile/control-panel findings.
- Recommendations split into:
  - immediate fixes
  - next sprint
  - parked/later
- Evidence with file paths, screenshots if available, and relevant git commit references.
- Clear statement of any areas not tested.

## Constraints

- Do not implement code.
- Do not commit changes.
- Do not expose secrets.
- Do not read or print `.env` values.
- Do not redefine the product away from personal AI radio/cast companion.
- Do not recommend a full rewrite unless evidence is overwhelming.
- Separate verified facts from assumptions.

