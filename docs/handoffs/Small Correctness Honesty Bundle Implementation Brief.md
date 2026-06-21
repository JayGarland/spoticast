# Small Correctness / Honesty Bundle Implementation Brief

Audience: Agents

## Purpose

Implement a tightly scoped cleanup bundle before larger v0.1 access or profile work.

Parent roadmap:

- `docs/strategy/v0.1-roadmap.md`
- `docs/strategy/v0.1-access-shape-decision-record.md`
- `docs/handoffs/Product Baseline Release Readiness Review.md`

## Role And Scope

Recommended owner: RUG manager under chef gate.

This is implementation work, but it is intentionally small. Do not turn it into a UI redesign, release architecture task, profile implementation, or hosting task.

## Objective

Clear concrete trust leaks:

1. Saved episodes must replay their own outro, not the newest shared outro.
2. App/README copy must not claim implemented memory before persistent profile exists.
3. User-facing app copy must not make normal users think developer setup is part of v0.1.
4. Windows/cross-platform setup and paste hints should be accurate.
5. Reduced-motion/accessibility polish should be verified and fixed only if a small obvious gap remains.

## Allowed Files

Use the smallest diff possible. Expected files:

- `resonova/server.py`
- `resonova/web/index.html`
- `resonova/web/styles.css`
- `README.md`

Only touch another file if validation proves it is necessary, and explain why in the handoff.

## Required Changes

### 1. Outro Path Fix

Current bug:

- Outro is assembled as shared `outro.mp3`.
- Saved queue uses `/audio/outro.mp3`.
- Older saved episodes can replay the newest outro.

Required behavior:

- Outro audio must be written into the current episode folder, matching intro and track commentary.
- Saved queue and `outro_ready` event must reference the episode-specific URL.
- Existing intro and track behavior must remain unchanged.

### 2. Memory Honesty Copy

Current issue:

- Landing/README claim memory or learning that is not implemented.

Required behavior:

- Until persistent profile exists, copy should describe the current product honestly: two AI hosts generate commentary from the current playlist, Spotify context, and optional Last.fm enrichment.
- Do not remove the long-term product direction from README; distinguish current MVP from future memory/profile direction.

### 3. Developer Setup Copy

Current issue:

- User-facing app surface mentions `brew install ffmpeg`, which makes developer setup look like normal-user v0.1 onboarding.

Required behavior:

- App landing should not present developer prerequisites as a normal user requirement.
- README can keep developer setup, but it must be cross-platform enough for Windows and macOS.

### 4. Cross-Platform Hints

Current issue:

- Paste hint uses Mac-only shortcut symbols.

Required behavior:

- Show both Mac and Windows shortcuts or use neutral copy.
- Keep pasted-track workflow intact.

### 5. Reduced Motion / Accessibility

Required behavior:

- Check whether `prefers-reduced-motion` exists.
- If absent, add a minimal CSS rule that reduces or disables perpetual waveform/pulse animations.
- Do not redesign the visual system.

## No-Go Rules

- Do not implement persistent profile or feedback.
- Do not change generation logic beyond the outro path fix.
- Do not touch hosting, accounts, billing, subscriptions, cloud storage, multi-source, PWA, or native app work.
- Do not rename broad UI sections.
- Do not change Spotify recovery logic.
- Do not normalize line endings or run broad formatters.
- Do not commit.

## Validation Required

Run:

```powershell
uv run python -c "from resonova import server; print('server ok')"
uv run python tests/test_variety_episodes.py
```

Also run a syntax/static check appropriate for changed frontend files if available. At minimum, inspect changed HTML/CSS manually and report that no obvious malformed tags/selectors were introduced.

If a command cannot run, record the exact error and why.

## Required Handoff

Write a handoff at:

```text
docs/handoffs/Small Correctness Honesty Bundle Handoff.md
```

Include:

- changed files
- exact behavior changed
- validation commands and results
- remaining risks
- anything not performed
- confirmation that no release architecture, profile/feedback, billing, hosting, or broad UI redesign work was done

## Suggested Manager Prompt

```text
Implement the small correctness/honesty bundle described in docs/handoffs/Small Correctness Honesty Bundle Implementation Brief.md.

Stay inside the allowed files unless a different file is strictly required and explained.

Do not implement profile/feedback, hosting, accounts, billing, multi-source, PWA/native, or Spotify recovery changes.

Do not run broad formatters or normalize line endings.

Do not commit.

Produce the required handoff at docs/handoffs/Small Correctness Honesty Bundle Handoff.md and stop.
```
