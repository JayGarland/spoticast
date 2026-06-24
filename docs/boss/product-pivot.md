---
title: "Decision - Bounded Personal Music Narrator Pivot"
created: 2026-06-23
status: accepted
audience: Boss / Chef / Product strategy agents
decision_owner: Boss
---

# Decision - Bounded Personal Music Narrator Pivot

## Summary

Resonova's product direction is now **bounded Stance C: a private music-memory
narrator**. Strict Stance B remains the shipped safety baseline, but it is not
the final product soul.

The distinction:

- **Strict B = current safety baseline.** Hosts can use private memory as a
  taste lens and may give rare third-person, descriptor-only nods.
- **Bounded C = product direction.** Hosts may directly address the listener
  and may use bounded music-domain history when it is grounded in the current
  playlist and user-controlled memory.
- **Unbounded C = banned.** No cross-domain, uninspectable, uninvited, or
  unrelated personal callbacks.

## Rationale

The boss-curated research in `docs/boss/research/` changes the product read. Resonova
should not compete as "AI commentary over a playlist"; Spotify AI DJ, Wrapped
AI podcast, NotebookLM-style audio recap, AI radio, and stats tools already make
that space crowded.

The defensible direction is:

> long-term listening trail -> personal memory -> evolving narrated cast

Resonova should explain the relationship between the listener and the music, not
only explain the music. This is the difference between a content generator and a
private music-memory narrator.

The ChatGPT memory-bleed concern is still valid, but the research narrows it:
ChatGPT failed because its episodic memory was unbounded - cross-domain,
uninspectable, and uninvited - not because all episodic memory is wrong.
Resonova is domain-limited to music, playlist-grounded, inspectable/resettable,
and already has memory-off/incognito controls. That makes bounded music-domain
episodic callbacks legitimate product material.

## Guardrails

Allowed direction:

- Direct "you" when grounded in the current playlist and music-domain memory.
- Bounded callbacks to listening patterns, replay affinity, seasonal returns,
  repeated playlist/genre returns, and feedback corrections.
- User-controllable degrees of personal narration in a future design.

Still banned:

- Cross-domain ChatGPT-style memory bleed.
- Uninspectable or uninvited personal context.
- Raw artist/track inventory recital as proof of memory.
- Private memory leaking into shared or public casts.
- Changing current `cast_depth` semantics without a separate implementation
  plan.

## Relationship To Stance B

Stance B was the correct shipped safety move while memory controls and derived
style descriptors were being stabilized. It remains the fallback trust posture
and the current implemented behavior.

This decision supersedes the older "C rejected" framing. Bounded C is no longer
parked as merely a distant experiment; it is the product direction to design
toward. Any behavior change still requires a separate implementation plan,
prompt design, and listening tests.

## Research Evidence

Read these boss-curated references before future product-direction, Chef, or
strategy work:

- `docs/boss/research/AI Companion Personalization and Trust.md`
- `docs/boss/research/Resonova-analysis-market-competition.md`

These are exported web-UI research and discussion histories. Treat them as
product evidence, not incidental scratch notes.
