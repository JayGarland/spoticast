---
title: "Decision Note — Memory-Gated Stance (B when memory off, bounded C when memory on)"
created: 2026-06-23
status: accepted direction; implementation owned by the bounded-C pivot chef; gated on listening tests
audience: Chef / Internal
decision_owner: Boss
relates_to: bounded-personal-music-narrator-pivot.md, companion-direction-and-memory-use-brief.md
---

# Decision Note — Memory-Gated Stance

Input for whoever implements the `bounded-personal-music-narrator-pivot.md`. This is a
decision + design refinement, not an implementation. Do not change behavior without a
separate prompt-design plan and real-device listening tests.

## The mapping (boss decision, 2026-06-23)

Tie the host stance to the existing memory control:

- **Memory OFF** (toggle off, partial memory-off, or per-cast Incognito) → **strict Stance B**:
  fourth-wall-preserving, no direct "you", descriptor-only — the shipped safety baseline.
- **Memory ON** → **bounded Stance C**: hosts may directly address the listener and use
  bounded, music-domain, playlist-grounded, user-controlled memory callbacks.

**Why this is the right shape:** it makes consent a control the user already understands —
personal narration happens *only because the user chose to be remembered* — and keeps strict B
exactly one toggle away as the safety floor. It is a concrete realization of the pivot's vague
"user-controllable degrees of personal narration."

Implementation rides the existing `memory_enabled` signal already in the generation context →
`build_prompt` branches the stance guardrail (B vs bounded-C). Same `gemini.py` guardrail block
that other stance work touches — sequence to avoid collisions.

## Required refinements (do NOT ship the raw binary)

1. **The toggle sets the CEILING; intensity RAMPS with real grounded memory.** Memory-on must NOT
   produce full Stance C on a brand-new/empty profile (hollow or fabricated callbacks). Light
   personal touches early, fuller as the trail/replay-affinity/feedback actually accumulate.
2. **Default care.** Memory is on by default, so this makes C the new-user default — ease into it;
   do not go full-personal on the first cast.
3. **Relabel the memory toggle so the consequence is legible.** "Track my listening trail"
   undersells it once it also flips the hosts to personal address. The user should understand
   memory-on = "the hosts speak to you and remember your patterns."
4. **Shared/public/multi-user casts force B regardless of the toggle** — personal callbacks must
   never leak into a cast someone else could hear. Hard dependency on per-user isolation (parked).
   *Status: shared/public mode is deferred; this design is for the private single-user experience only.*
5. **Listening tests before C becomes the live default** — on paper it is clean; whether it lands
   warm vs. creepy only shows on a real device with real memory.
6. **`cast_depth` semantics unchanged** (per the pivot).

## Bounds (restated from the pivot)

Music-domain only · playlist-grounded · inspectable/resettable. Banned: cross-domain memory bleed,
raw artist/track inventory recital, uninspectable/uninvited context, leaking into shared casts.

## Marking it in git

Tag the **implementation** commit with an annotated tag (e.g. `git tag -a stance-c-launch -m "…"`)
when it lands — do not tag before there is code to point at.
