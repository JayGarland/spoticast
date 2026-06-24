---
title: "Direction — Sharpen the Experience (Steerability Lenses)"
created: 2026-06-23
status: accepted; v1 (lenses) shipped
audience: Boss / Internal
decision_owner: Boss
---

# Direction — Sharpen the Experience

Audience: Boss / Internal

## Context

By 2026-06-23 Resonova's internals were solid: the persistent memory loop works
(feedback fold threshold = 2), stance B (host taste-awareness) is live, and the two
release blockers from the full product re-audit were fixed (blind Spotify playback;
the memory-off honesty bug). See `docs/handoffs/Full Product Re-Audit Chef Gate 2026-06-23.md`.

The boss then asked to **advance the product**. Three thrusts were on the table:

1. **Reach real users** — hosted beta + per-user isolation + a cost model (the v0.1
   north star in `v0.1-access-shape-decision-record.md`; biggest architecture/budget lift).
2. **Sharpen the experience** — steerability + a visible memory surface.
3. **Deeper, richer casts** — the opt-in deep-research generation mode (`deep-research-generation-mode-brief.md`; costly, design-first).

## Decision

**Pursue "sharpen the experience" now.** Reasoning:

- The **market wedge is confirmed and unoccupied** (`resonova-market-benchmark.md`): every
  incumbent personalizes from a black box; Resonova's axis is *inspectable, editable taste
  memory + two-host hosted depth*. The market's clearest near-term gap for Resonova is
  **steerability** ("lenses": mood / era / host tone / analysis depth) — named in the README
  and the convergence point of every comparable (Prompted Playlists, DJ voice requests,
  NotebookLM custom instructions).
- The **visible memory surface is already built** — `#memory-panel` renders taste / preferences /
  memories, with per-memory pin/delete, a trail toggle, clear, and refresh. So the real
  net-new gap is steerability, not inspection.
- Lowest architecture/budget risk of the three thrusts; keeps hosting/billing/multi-user parked.

## v1 — Steerability Lenses (shipped `0210340`, 2026-06-23)

Two **optional per-cast** generation options that steer *how the hosts discuss the music*
(at shipment time, never *whether* they address the listener — the stance-B fourth wall was
untouched):

- **Depth** — `Brief` / `Balanced` / `Deep Dive`. Wires the previously-unused
  `commentary_preferences.depth` into the prompt; per-cast value overrides the durable pref.
- **Vibe** — `Warm` / `Witty` / `Analytical` / `Late-night` / `Chill`. Overrides the durable
  `commentary_preferences.tone` for that cast.

Design notes:

- Rides the existing `commentary_language` path end to end: `GenerateRequest` → `Job` →
  context passthrough → `build_prompt`. Injected as a `CAST DIRECTIVES` block.
- Per-cast override of durable prefs; **no lens selected ⇒ prompt byte-identical** to before.
- Whitelist-validated server-side; passed through even for incognito (steering, not memory).
- UI selects sit in the generate-options block; **both** the form and the quick playlist-card
  path send them; last choice persists in `localStorage`.
- Files: `resonova/server.py`, `resonova/api/gemini.py`, `resonova/web/index.html`,
  `resonova/web/player.js`, `tests/test_profile.py` (3 new lens tests).

## Constraints preserved

- Stance-B / fourth-wall guardrail unchanged: lenses change host *style*, never break the
  fourth wall, recite inventory, or address the listener.
- No new architecture; no hosting / accounts / billing / multi-user (all still parked).

## v2 — Personalized Ordering + Shareable Identity (shipped 2026-06-23)

- **Personalized flow-aware ordering** (`9da5282`) — the episode-ordering scorer now applies a
  *soft* taste bias (artist affinity from the durable profile + a strong/popular opener), kept
  small vs the variety penalties. The 20-random-candidate generation is preserved, so the order
  leans toward taste but stays non-deterministic — **never locked** (a loved artist opened ~39/50,
  yet 30 runs produced 30 distinct orders). No energy arc: Spotify audio-features are
  deprecated/403, so the signal is durable taste + track `popularity`. No-taste path byte-identical.
- **Shareable episode identity** (`1e33437`) — each episode gets an evocative one-line tagline
  (one LLM call; stance-B preserved — describes the music, not the listener), a deterministic
  gradient cover, and a Share button that copies a blurb to the clipboard. Old episodes degrade to
  no-tagline.

## Pivot Note (2026-06-23)

The later decision record `bounded-personal-music-narrator-pivot.md` changes the product direction:
strict Stance B is now the shipped safety baseline, while bounded Stance C is the product target.

Do **not** reinterpret the shipped `Depth` lens retroactively. `Brief` / `Balanced` / `Deep Dive`
still means analysis depth and pacing. Future work may add or integrate **personal narration
depth** with the lens system, but it must preserve the current analysis-depth behavior and make
memory exposure user-controllable.

## Next candidates within this thrust (not yet approved)

From the market benchmark's fit-ranked list, still in "sharpen" scope:

- **Mood / context lens** (morning / late-night / road-trip / focus) and an **era-angle lens** —
  deferred from v1 (boss chose Depth + Vibe first); the cleanest next lenses.
- ~~Richer episode naming / shareable episode identity~~ — **shipped `1e33437`** (see v2 above).
- ~~Flow-aware track ordering~~ — **shipped `9da5282`** (taste-biased, never locked; no energy arc — audio-features deprecated).
- Optional: saved/default lens presets beyond the existing durable prefs.

## Relation to the roadmap

This is a v0.1 product-sharpening move that strengthens the differentiator without touching the
parked access/hosting/billing decisions. "Reach real users" (hosted beta) and "deeper casts"
(deep-research mode) remain the other two thrusts, available when the boss chooses to switch.
