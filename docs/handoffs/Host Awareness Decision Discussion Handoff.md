# Host Awareness / 4th-Wall — Decision Discussion Handoff

Audience: External / web-UI agent (NO workspace access — this doc is self-contained).
Status: CHECKPOINT — v0.1 product-soul decision. Pending boss decision after this discussion.
Date: 2026-06-22

## What Resonova is (context for a fresh agent)

Resonova is a **personal AI radio companion**. The user pastes a Spotify playlist; the system
generates a "cast" where **two AI hosts** talk between the tracks — intros, context, stories about
the music. Baseline product goal: *Resonova should understand the listener better the more they use
it — without ever feeling invasive.*

It already builds an inspectable memory profile of the listener's taste (top artists, derived genre
descriptors, saved library, followed artists, explicit feedback). Today that memory only **steers**
what the hosts find interesting — the hosts **never reference or address the listener**. A real test
cast confirmed: zero listener mentions. That's by a deliberate guardrail.

## The decision

**Should the hosts KNOW and/or TALK TO the single listener?** Three positions, with example host
lines so you can hear the difference:

- **A — Overhear (current).** Hosts never reference/address the listener; memory steers invisibly.
  The listener overhears a music show.
  *e.g. "That fade-out is pure late-90s Warp."*
- **B — Acknowledge taste, don't address.** Hosts reflect the listener's taste in **third person,
  descriptor-only** — no "you", no data, no history.
  *e.g. "This set's built for someone who lives in the quiet end of things."*
- **C — Address the listener.** Hosts know there's one listener and speak to **"you"** (still
  descriptor-based, no history-recital).
  *e.g. "If you're after something slower tonight, this one fits."*

"Know" (taste steers + can be reflected) is likely yes. "Talk to you directly" is the crux: B says
no/minimal, C says yes.

## Hard constraints (must hold for ANY option — owner's non-negotiables)

1. **Descriptor, never inventory.** Hosts may say "leans to the quiet end," but must NEVER read the
   listener's own artist names back at them — that feels like surveillance even without history.
2. **No cross-cast memory bleed / no history-recital.** NEVER "last time we discussed X," no
   carrying prior-cast context into a new cast. (The owner had a bad ChatGPT experience where memory
   dragged old chat context into new reasoning — must not repeat.)
3. **Not timid/defensive.** The owner dislikes ChatGPT's over-cautious, conservative style. Don't
   over-correct into blandness.
4. **The playlist already conveys the vibe.** You can't make a techno playlist feel "quiet" via
   commentary — commentary should match the music, never fight it.

## The meta-question (how to resolve, not just which stance)

1. **Pursue ONE stance** as the product default.
2. **Leave it to the user** — offer selectable **modes** for cast generation (e.g. "Radio" = A,
   "Companion" = B/C). The user picks.
3. **Experiment one-by-one** (try each, compare on real casts).

## Chef recommendation (for the discussion to confirm or challenge)

- **Stance: B**, possibly drifting to a *light* C. It's the most faithful to the owner's "tasteful a
  bit / no bleed / not defensive" and to constraint #1 — aware and warm without feeling watched.
  Full C (direct "you", any "lately") is where the creepiness risk concentrates; allow only the
  lightest second person, never history.
- **Approach: pursue ONE (B) as the default now**, and treat A (pure radio) and C (direct companion)
  as **optional modes to expose later only if users want the control** — do NOT build multiple modes
  or run a full one-by-one experiment yet (subtle differences, few testers, real cost). A default
  setting (not a per-cast friction prompt) keeps the baseline simple (playlist → generate).
- **Mark as a checkpoint:** yes — this defines the product's soul; record the decision before the
  prompt is changed.

## What we want from this discussion

A recommended stance (A / B / C, or B-now-with-C-as-a-mode), a position on single-default vs
user-modes, and the reasoning — weighing warmth vs creepiness against the four hard constraints. Note
any host-line do/don't examples. The decision returns to the owner + chef, who hold final say.
