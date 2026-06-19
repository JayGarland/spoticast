---
title: "External Product UX Design Audit Handoff"
source: "External AI auditor — against docs/handoffs/External Product UX Design Audit Brief.md"
created: 2026-06-19
status: draft
scope: "Evidence-backed UX + product/design audit. No code implemented. No commits. No secrets read."
---

# External Product UX Design Audit Handoff

## Executive Summary

Resonova is a well-built, visually distinctive local MVP that already does more than "paste a playlist." The core loop — playlist → AI script → multi-speaker TTS → interleaved Spotify/commentary playback with crossfade and live streaming — works, and generated episodes are persisted and replayable. The design system (editorial serif + mono, nebula background, ON AIR motif, color-coded commentary vs. music) genuinely reads as "intelligent personal radio," not a generic AI tool. That identity is the product's biggest asset and should be preserved.

The most important findings are gaps between what the product *promises* and what it currently *delivers*, and a set of concrete mobile-control limitations with a single clear root cause:

- **The Media Session API is not used anywhere in the codebase.** This is the direct, verified root cause of the parked lockscreen problem: the phone control panel can only expose generic play/pause and cannot offer previous/next segment. This is the highest-leverage fix available.
- **The landing screen over-promises.** It advertises "Listening memory" and "Two AI hosts learn your taste," but persistent taste/profile memory and feedback are parked and not implemented. Every generation is effectively stateless. This is a trust/expectation risk.
- **There are no responsive breakpoints at all** (zero `@media` queries in 1,155 lines of CSS) and the layout is locked to `100vh` + `overflow:hidden`. Mobile rendering works only incidentally and is exposed to the classic iOS Safari viewport-bar bug.
- **The only in-app playback control is Skip (forward).** There is no in-app play/pause and no previous — on desktop *or* mobile.
- **A real data-integrity bug:** the outro is written to a single shared `generated/outro.mp3` instead of the episode's own folder, so replaying any older episode plays the most recent outro, and concurrent generations collide.

None of this calls for a rewrite. The recommended next milestone is **Media Session + full in-app transport controls** (small, high-perceived-quality, directly unblocks the known mobile pain), followed by the already-designed **persistent profile + feedback** layer to make the app earn its own tagline.

> **Audit method note:** A live browser pass **was performed** via the Claude-in-Chrome MCP against the running instance at `http://127.0.0.1:8765` (owner's Windows machine, after the extension was connected). It confirmed the connected/library and playing states on a real render. Findings tagged *(live-confirmed)* were observed at runtime; all others are from static inspection of the shipped HTML/CSS/JS, backend code, docs, and git history. One item could not be faithfully tested live — true mobile-viewport rendering, because desktop-Chrome window resizing does not emulate a phone viewport reliably; see [Areas Not Tested](#areas-not-tested).

---

## What Was Inspected

**Docs / strategy (read in full):** `README.md`, `docs/strategy/operating-model.md`, `docs/strategy/resonova-mvp-audit-brief.md`, `docs/strategy/persistent-profile-feedback-brief.md`, `docs/strategy/mobile-playback-hardening-brief.md`, `docs/strategy/playlist-order-variety-brief.md`, `docs/handoffs/Resonova MVP Audit Handoff.md`, plus the audit brief itself.

**Frontend (read in full):** `resonova/web/index.html` (329 lines), `resonova/web/player.js` (936 lines), `resonova/web/styles.css` (1,155 lines).

**Backend (read in full / targeted):** `resonova/server.py` (416 lines), `resonova/episodes.py` (71 lines); pipeline cross-checks against `resonova/api/*`.

**Repo state:** `git log` (30 commits), `git status`, branches, `.gitignore`, `generated/` tree on disk.

**Explicitly not read (per constraints):** `.env` values. No secrets are reproduced in this report.

---

## Browser / MCP Validation Results

A live pass was run via the Claude-in-Chrome MCP against `http://127.0.0.1:8765` on the owner's Windows machine.

| Brief task | Result |
|---|---|
| Open the running app | **Live-confirmed** — app loads; title "Resonova"; instance was already Spotify-authenticated, so it opened directly into the connected/library state |
| Connected/library state | **Live-confirmed** — "What are we listening to?" heading, paste box, Generate Cast, "Past Episodes" (e.g. *Drifting Through Stardust*, *Slowcore Echoes*, *Midwest Summer Echoes*) and "Your Playlists" grid all render on-brand (see UX-3, D-1) |
| Mac-only key hints on Windows | **Live-confirmed** — the paste hint visibly renders `⌘A` / `⌘C` on a Windows machine (UX-8) |
| Playing state + controls | **Live-confirmed** — loaded a saved episode; the playing screen shows the "AI Commentary / Podcast Intro" segment with the accent-purple commentary waveform. The live DOM contains exactly **two** interactive controls: *"Toggle Spotify diagnostic panel"* and *"Skip to next segment"* — **no play/pause, no previous** (decisive evidence for UX-2, D-3, and the mobile section) |
| Diagnostic toggle separation | **Live-confirmed** — the Diag toggle exists in the header rail during playback, unobtrusive, exactly as designed (D-4) |
| Commentary vs. music distinction | **Live-confirmed** — segment badge "AI Commentary", italic title, purple waveform observed during the commentary segment (UX-5) |
| Control/progress legibility | **Live observation** — the Skip button, episode-progress bar, and attribution render at very low contrast against the near-black background; they are barely visible at rest (adds to D-6) |
| Unauthenticated landing state | **Not observed live** — the instance was already authenticated; evaluated statically (`#state-landing` exists as a discrete block) |
| True mobile-viewport render | **Not faithfully testable** — desktop-Chrome window resize to 390px did not reproduce a phone layout in the capture; the zero-`@media` finding from source remains authoritative (D-2). See Areas Not Tested. |
| Prior runtime evidence | The in-repo `Resonova MVP Audit Handoff.md` separately recorded a server start with `GET /` 200, `/api/episodes`, `/api/playlists`, audio 206, etc. Cited as corroborating prior evidence. |

---

## UX Findings (with severity)

Severity scale: **Critical** (blocks core promise / data loss) · **High** (clear user pain or trust risk) · **Medium** (noticeable friction) · **Low** (polish).

### UX-1 · High · The product promises memory it does not have
The landing tagline is "Personal AI radio · **Listening memory** · Your music" and a feature bullet reads "Two AI hosts **learn your taste**" (`resonova/web/index.html:76,80-82`). Verified against the backend: there is no persistent profile read or write in the generation pipeline (`server.py` builds context fresh each run from live Spotify/Last.fm only), and persistent memory/feedback are explicitly parked (`docs/strategy/persistent-profile-feedback-brief.md`, status: draft/design-only). A first-time user is promised a companion that remembers them; a repeat user gets a stateless generator. This is the single biggest gap between identity and reality.
*Recommendation:* either soften the copy now ("Two AI hosts talk through your playlist") or ship the minimal profile layer so the claim becomes true. Do not leave the claim unbacked.

### UX-2 · High · No in-app play/pause or previous — only Skip-forward (live-confirmed)
The entire playing-state control surface is one Skip button (the live DOM of the playing screen contained exactly two controls: the Diag toggle and "Skip to next segment" — nothing else) (`index.html:295-303`; `player.js skip()` at `:814-829`). There is no pause/resume control and no "previous segment" in the UI. Pausing depends entirely on OS media keys / lockscreen, and going back is impossible by any means. This is felt on desktop too, not just mobile.
*Recommendation:* add a proper transport row — Previous · Play/Pause · Skip — in the playing state. Previous requires keeping a small history stack (the queue is currently consumed with `Array.shift()`, so played items are discarded; see UX-7).

### UX-3 · Medium · First screen leads with utility, not identity, *after* connect
The landing screen does communicate identity well (waveform, "Personal AI radio," three feature bullets). But immediately post-connect the heading becomes "What are we listening to?" with a paste box and library grids (`index.html:104-190`). The transition from "personal radio companion" to "paste-a-playlist tool" is abrupt — the connected state has no reminder of what makes Resonova different from a summarizer.
*Recommendation:* carry one line of identity into the connected state (e.g. a short "your hosts" or "what's new since last time" strip), especially once a profile exists.

### UX-4 · Low · Generation progress is trustworthy, with one visual gap
The generating state shows four labeled steps (fetch / research / script / TTS) with active spinner, done-checkmarks, and live SSE messages (`index.html:195-230`, `player.js _updateProgressStep`). This reads as trustworthy. Minor bug: `_markAllStepsDone()` marks only `step-fetch/step-script/step-tts` and omits `step-research` (`player.js:763-771`), so when `intro_ready` fires the Research row can be left un-checked while everything else completes. Cosmetic but noticeable.

### UX-5 · Low · Commentary vs. music *is* clearly communicated
Answering the brief's question directly: yes. During playback the UI distinguishes the two via a segment-type badge ("AI Commentary" vs "Now Playing"), an accent-purple vs. green dot and waveform, an italicized title for commentary, a "Up next: <track>" line, and a persistent "Commentary by Gemini · Music by Spotify" attribution (`index.html:236-317`, `player.js _setSegmentType/_setNowPlaying`). This is a genuine strength.

### UX-6 · Medium · Replay/library exists but is shallow
Episodes are persisted (`episodes.py`) and surfaced under "Past Episodes," clickable to replay (`player.js _loadEpisodes/_playEpisode`). Good. But a saved episode replays from a stored queue with no scrubbing, no per-segment navigation, and (per UX-2) no way to go back a segment. There is also no delete/rename/manage affordance. The library proves the data model supports a richer "your shows" experience that the UI doesn't yet expose.

### UX-7 · Medium · Queue is destructively consumed — blocks "previous" and resume-from-position
`_playNext()` uses `this.queue.shift()` (`player.js:348`), discarding each item as it plays. There is no played-history stack and no current-index pointer. This is the structural reason previous/seek/resume can't exist today. Any future transport work should refactor to an index-based queue first.

### UX-8 · Low · Mac-only keyboard hints on a Windows project
The paste hint hard-codes `⌘A` / `⌘C` (`index.html:159`) and the landing prerequisite says `brew install ffmpeg` (`index.html:96`); README repeats `brew`. The owner's working tree is on `F:\` (Windows). On Windows these instructions are wrong (`Ctrl+A`/`Ctrl+C`, and ffmpeg isn't installed via brew).
*Recommendation:* detect platform or show both; fix README's ffmpeg instructions for Windows.

---

## Design Findings (with severity)

### D-1 · Strength · Cohesive, on-identity visual system
The token set (`styles.css:3-21`) is disciplined: a defined palette (deep `--bg`, `--accent` periwinkle, `--on-air` red, `--green` for Spotify, cream text ramp), two purposeful typefaces (Cormorant Garamond display, DM Mono body), nebula + film-grain background, and a recurring waveform/ON-AIR radio motif. Spacing, card styles, and button variants (`.btn-primary/.btn-ghost/.btn-sm`) are consistent across states. This is the product's strongest design asset and supports the "intelligent personal radio" goal well. Preserve it.

### D-2 · Critical-for-mobile · No responsive design whatsoever
There are **zero `@media` queries** in the entire 1,155-line stylesheet (verified by grep). Layout adapts only through `max-width` caps (580/640px), a couple of `clamp()` font sizes, and fl/grid auto-fill. Specific risks on a phone:
- The landing feature row is a fixed `display:flex; gap:2.5rem` of three ~100px columns (`styles.css:232-250`) — likely to crowd or wrap awkwardly under ~360px.
- The body is `overflow:hidden` and `#app` is `height:100vh` (`styles.css:25-33,61-70`). `100vh` on mobile Safari/Chrome includes the retracting URL bar, so content can be clipped or the layout can jump; there is no `dvh`/`svh` fallback.
- The connected state manages its own `max-height: calc(100vh - 6rem); overflow-y:auto` (`styles.css:269-276`), which compounds the `100vh` problem on mobile.
*Recommendation:* add a small mobile breakpoint pass (stack landing features, switch `100vh`→`100dvh`, verify tap-target sizes). This is the cheapest way to raise perceived mobile quality.

### D-3 · High · Media Session / lockscreen metadata is absent
No `navigator.mediaSession`, `MediaMetadata`, or `setActionHandler` anywhere (verified by grep). Commentary plays through a bare `<audio id="resonova-audio">` with no media metadata, so the OS lockscreen has nothing rich to show and no custom actions to call. This is the verified root cause of the brief's known issue ("lockscreen only exposes pause/play... cannot go to previous or next segment"). See [Mobile / Control-Panel Findings](#mobile--control-panel-findings).

### D-4 · Medium · Developer tooling is well-separated — meets the brief's bar
The diagnostic system is appropriately quarantined from user-facing UI. The "Diag" toggle is a small, low-opacity button injected into the ON AIR header rail only during playback, persisted via `localStorage('resonova:diag')`, hidden by default (`player.js _createDiagToggle:51-65`, `styles.css .diag-toggle:1128-1155`). The panel itself (`.spotify-diag`) is visually distinct (monospace, fixed overlay, warn-colored fields). This satisfies "discoverable but not user-facing noise." Minor note: the panel is information-dense and developer-oriented (UA strings, `connect()` results) — correct for an owner/dev, but confirm it never shows for a non-owner guest.

### D-5 · Low · Heavy perpetual animation, no reduced-motion path
The landing (40 bars) and playing (36 bars) waveforms plus the ON AIR pulse run infinite CSS animations, and there is no `prefers-reduced-motion` block anywhere (verified). For a motion-sensitive user this is uncomfortable, and on low-end phones the always-animating bars cost battery.
*Recommendation:* add a `@media (prefers-reduced-motion: reduce)` rule to pause/soften the waveforms and pulse.

### D-6 · Low · Accessibility gaps
Good: decorative waveforms are `aria-hidden`, the connect CTA is a real `<a href>`, the textarea is labeled by placeholder + hint. Gaps: state changes and now-playing updates have no `aria-live` region, so a screen-reader user won't hear "now playing X" or segment transitions; segment state leans on color (purple/green) though it is backed by text labels, which mitigates it; the Skip SVG button relies on a `title` rather than an explicit `aria-label`. None are blockers for a single-owner MVP, but cheap to fix.

### D-8 · Medium · Playback controls are too low-contrast (live-confirmed)
On the live playing screen, the Skip button, episode-progress bar, and attribution line are rendered in the faint cream ramp (`--cream-low` / `--cream-faint`) on the near-black background and are barely perceptible at rest. The single most important interactive affordance in the playing state (Skip) nearly disappears. This compounds UX-2 (few controls) — the one control that exists is hard to see.
*Recommendation:* raise the resting contrast of transport controls and progress to at least a clearly legible level; treat Skip (and future Play/Pause/Previous) as primary, not decorative.

### D-7 · Low · Progress is segment-count, not time
Episode progress is `completedItems / totalItems` with a "X / Y segments" label and a thin fill bar (`player.js _updateProgress`, `index.html:305-314`). Reasonable and honest for the streaming model, but there's no elapsed/remaining time and no scrub. Fine to defer.

---

## Product Strategy Findings

### Verified current state
- **Still one-shot and effectively stateless.** Context is rebuilt every generation from live Spotify + (optional) Last.fm; nothing about the owner accumulates between runs (`server.py _run_generation`). Episodes persist as *artifacts*, but there is no profile, no feedback, no cross-session learning.
- **Order variety is implemented and matches its brief.** `_select_playlist_tracks_for_episode()` (`server.py:78-88`) random-shuffles playlist tracks with up to 5 retries to avoid reproducing the exact original order, then applies `MAX_TRACKS`; pasted track lists preserve user order (`server.py:276-286`). This satisfies `playlist-order-variety-brief.md` (commit `1f07074`).
- **But order variety only partly solves rigidity.** It changes *sequence*, not *content*. Commentary is cached and deterministic per order, so a re-listen of the same saved episode is identical, and a re-generation reshuffles but still draws from the same static prompt with no memory of what the owner liked. The "stale on repeat" problem is mitigated at the playlist-replay level and untouched at the taste/voice level.

### What still makes the app feel stateless / repetitive
1. No memory of prior episodes, liked segments, or preferred host tone/depth.
2. No feedback capture, so the system cannot improve even in principle.
3. A single static script/persona prompt — no mood/era/lens selection.
4. Shuffle is uniform-random, not taste- or flow-aware (no energy arc, no "open strong").

### Recommended next milestone (after local MVP)
**Ship Media Session + full in-app transport controls first.** Rationale: it is small, reversible, directly closes the only *named* current UX defect (mobile prev/next), and produces an outsized jump in perceived product quality (real lockscreen art + working controls is what makes an audio app feel "real"). It also forces the index-based queue refactor (UX-7) that everything else needs.

**Then ship the persistent profile + feedback layer** that's already designed in `persistent-profile-feedback-brief.md`. This is what makes the landing copy honest (UX-1) and converts Resonova from "generator" to "companion." The brief's file-based, single-user, local-first shape is right-sized; build the smallest version (a `taste_profile.json` read into the prompt + thumbs up/down written to `feedback.jsonl`) before anything fancier.

### Investment ranking (auditor's view, for owner decision)
1. **Media Session + transport controls** — highest perceived quality per unit effort; unblocks the known issue.
2. **Persistent profile + lightweight feedback** — closes the identity gap; already designed.
3. **Mobile responsive pass + `100dvh`** — cheap, broad polish for the primary device.
4. **PWA packaging** — meaningful but *second-order*; install-to-home-screen only feels good once Media Session + responsive layout exist. Low value before then.
5. **Comparable-app research / roadmap expansion** — useful input, but should follow, not precede, the profile decision.

### What should remain explicitly parked
Full mobile-playback hardening beyond the diagnostic toggle (the git history shows repeated failed/reverted recovery loops — `b0347e0`, `b3bffcd` — so avoid broad watchdog/retry work without a fresh reproduction), Spotify preview-URL fallback, native packaging, multi-user/cloud, and any comparable-app research that would gate the profile work.

---

## Mobile / Control-Panel Findings

**Root cause (verified):** no Media Session API usage. Commentary is a bare `<audio>` element and Spotify music is driven via Web Playback SDK REST calls; neither path registers `MediaMetadata` or action handlers. So the OS gives only the generic transport it infers from a playing `<audio>` tag — which explains exactly why the lockscreen exposes pause/play for "the current segment" but no previous/next.

**What the phone control panel *should* expose, and what's needed to get there:**

| Desired lockscreen control | Currently possible? | What it needs |
|---|---|---|
| Title / artist / artwork on lockscreen | No | `navigator.mediaSession.metadata = new MediaMetadata({...})` set on every `_setNowPlaying` |
| Play / Pause (reliable) | Partial (OS-inferred) | `setActionHandler('play'/'pause', …)` wired to the audio el + Spotify SDK |
| Next segment | No | `setActionHandler('nexttrack', () => resonova.skip())` — skip already exists |
| Previous segment | No | `setActionHandler('previoustrack', …)` **plus** the index-based queue with history (UX-7); previous is impossible today because played items are `shift()`-discarded |

**In-app mobile controls:** equally limited — the playing state offers only Skip, and there is no responsive layout, so the in-app experience on a phone is a desktop layout scaled into a `100vh` box. Reachability of the single Skip button is fine; everything else (pause, previous) is simply absent.

**PWA / Media Session, would it improve perceived quality?** Media Session: **yes, materially and cheaply** — it's the difference between "a web page making noise" and "a real audio app" on the lockscreen. PWA: **yes but later** — standalone install removes the browser chrome (which would also sidestep the `100vh` URL-bar issue), but it adds little until Media Session and a responsive layout exist. Sequence Media Session first.

---

## Bugs Found During Audit (verified, not UX-opinion)

- **B-1 · High · Outro written to a shared file, not the episode folder.** `server.py:377-380` synthesizes the outro to `"outro.mp3"` and pushes URL `/audio/outro.mp3`, while intro and per-track commentary correctly go under `episodes/<id>/` (`server.py:341-363`). Confirmed on disk: a single `generated/outro.mp3` exists at the root alongside `generated/episodes/`. Consequences: (a) replaying any older episode plays whatever outro was generated *last*, not its own; (b) two concurrent generations overwrite each other's outro; (c) `make clean-cache` wipes the only copy. Fix is one line (write to `f"{ep_dir}/outro.mp3"` and update the URL + saved queue).
- **B-2 · Low · `_markAllStepsDone()` skips the research step** (`player.js:763-771`) — see UX-4.

---

## Recommendations

### Immediate fixes (small, low-risk, high-clarity)
1. **Fix the outro path bug (B-1).** Write outro into the episode dir; update the pushed URL and saved queue. One-line-class change, prevents wrong-outro replay and concurrency clobber.
2. **Reconcile the landing copy with reality (UX-1).** Until memory ships, change "Listening memory" / "learn your taste" to claims the MVP actually delivers.
3. **Fix Mac-only instructions for Windows (UX-8):** `Ctrl+A`/`Ctrl+C` hint and Windows ffmpeg guidance in `index.html` + README.
4. **Add `prefers-reduced-motion` (D-5)** and an `aria-label` on the Skip button (D-6).
5. **Fix the research-step checkmark (B-2 / UX-4).**

### Next sprint (the real milestone)
6. **Refactor the queue to index-based with history (UX-7)** — prerequisite for everything below.
7. **Add Media Session metadata + action handlers (D-3, mobile section)** — lockscreen art, play/pause, next, previous.
8. **Add an in-app transport row (UX-2):** Previous · Play/Pause · Skip in the playing state.
9. **Add a mobile responsive pass (D-2):** one breakpoint, stack landing features, switch `100vh`→`100dvh`, verify tap targets.

### Parked / later (in priority order, pending owner approval)
10. **Persistent profile + lightweight feedback** per the existing brief (smallest file-based version first) — the thing that makes the tagline true.
11. **PWA packaging** — after Media Session + responsive layout land.
12. **Library management** (delete/rename/scrub) and **lens selection** (mood/era/host style).
13. **Keep parked:** broad mobile-playback hardening loops, preview-URL fallback, native packaging, multi-user, comparable-app research as a gating step.

---

## Evidence Index

| Finding | Primary evidence |
|---|---|
| No Media Session API | grep for `mediaSession`/`MediaMetadata`/`setActionHandler`/`previoustrack`/`nexttrack` across `resonova/` → no matches |
| No responsive CSS | grep `@media` in `resonova/web/styles.css` → no matches (1,155 lines) |
| `100vh`/`overflow:hidden` layout | `styles.css:25-33, 61-70, 269-276` |
| Only Skip control | `index.html:295-303`; `player.js:814-829` |
| Landing over-promise | `index.html:76, 80-82` vs. `server.py _run_generation` (no profile read) + `persistent-profile-feedback-brief.md` (parked) |
| Destructive queue | `player.js:337-361` (`queue.shift()`), no history stack |
| Outro path bug | `server.py:341-363` (episode dir) vs. `:377-380` (`"outro.mp3"`); on disk `generated/outro.mp3` at root |
| Order variety | `server.py:78-88, 276-286`; `playlist-order-variety-brief.md`; commit `1f07074` |
| Diag toggle separation | `player.js:51-65`; `styles.css:1128-1155`; brief/commit `fef63ab` |
| Episode persistence/replay | `episodes.py:22-71`; `player.js _loadEpisodes/_playEpisode`; `index.html:166-169` |
| Reduced-motion absent | grep `prefers-reduced-motion` → no matches |
| Mac-only copy | `index.html:96, 159`; `README.md` ffmpeg lines |

Relevant commits (from `git log --oneline -30`): `1f07074` vary playlist cast order · `fef63ab` diagnostic panel toggle · `38d2779` Tailscale HTTPS callbacks · `d0ea11a`/`6e23bc1` mobile SDK diagnostics · `b0347e0`/`b3bffcd` reverted/failed mobile playback recovery (evidence to avoid broad recovery loops) · `0901bc6` rename to Resonova.

---

## Areas Not Tested

A live Chrome-MCP pass *was* completed (connected/library state, playing state, controls, segment UI, Mac-key bug — see Browser/MCP Validation Results). The following remain untested:

- **True mobile-viewport rendering and real-device behavior.** Desktop-Chrome window resize did not faithfully emulate a phone, so the actual phone layout, tap-target sizing, and the `100vh` URL-bar behavior were not observed on a real device. The zero-`@media` finding (D-2) is from source and is authoritative regardless; on-device confirmation is still worthwhile.
- **OS lockscreen / control-panel behavior on a phone.** The Media Session conclusion is grounded in verified code absence (no `mediaSession` anywhere) and the live DOM (only Skip + Diag controls), but the *exact* lockscreen control set on the owner's phone was not observed directly.
- **A full new generation (playlist → script → TTS → interleaved Spotify playback).** Only a saved-episode replay was exercised live; a fresh generation and live Spotify SDK music playback were not run.
- **Unauthenticated landing state** — the instance was already authenticated; landing was evaluated statically only.
- **TTS / audio quality and crossfade feel** — subjective, no tooling, not assessed.
- **Performance on low-end devices** — not measured.

**To confirm the mobile/lockscreen items** (owner, on Windows + phone): open the app on the phone via the Tailscale HTTPS host (`https://<host>.ts.net:8765`) so the Spotify Web Playback SDK initializes in a secure context, start an episode, lock the phone, and note exactly which controls the lockscreen exposes. That closes the only material gaps above. Do not expose `.env` values during that pass.

---

## Constraint Compliance

No code implemented. No commits made. No `.env` values read or printed. Product identity (personal AI radio/cast companion) preserved. No rewrite recommended. Verified facts (code/grep/on-disk evidence) are separated from assumptions (anything dependent on live rendering is flagged as untested).
