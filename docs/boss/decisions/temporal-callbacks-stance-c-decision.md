# Decision: Allow Pattern-Level Temporal Callbacks in Bounded Stance C

**Date:** 2026-06-25  
**Decision maker:** Boss (owner)  
**Status:** Approved — implemented in `resonova/api/gemini.py`

## Problem

The prior `_persistent_memory_guardrail()` blanket-banned the phrase `"last time"` as a precaution against creepy tracking recital. This was too broad: it also silenced pattern-level temporal callbacks like "this sound keeps coming back for you" and "your feedback pointed toward X" — which are exactly the differentiated voice that separates Resonova from Spotify AI DJ and Last.fm-style stats.

The market competition analysis (`docs/boss/research/Resonova-analysis-market-competition.md`) identified "long-term listening trails → personal memory → evolving narrated cast" as Resonova's defensible moat. Temporal callbacks at the pattern level are the mechanism that makes that moat real in the hosts' voice.

## Decision

**Allow** pattern-level temporal callbacks in Bounded Stance C (memory enabled).  
**Keep banned** raw tracking recital and raw session numbers.

### Approved boundaries

| Rule | Examples |
|------|----------|
| Music-domain only | "this sound keeps coming back for you" ✓ / "you've been stressed lately" ✗ |
| Must come from profile / feedback / playlist pattern | grounded in actual listener history |
| No raw numbers | "you replayed 4 times" ✗ / "this keeps pulling you back" ✓ |
| No non-music personal context | weather, mood, work, location — all off |
| Keep sparse | not every segment; rare and earned |

### Why allow

If temporal callbacks stay banned, Resonova narrates playlists the way any commentary layer could — good writing, but no memory. The pivot to Bounded Stance C (2026-06-23) exists precisely to make memory-enabled casts feel meaningfully different. Pattern-level callbacks are the voice of that memory. Blocking them weakens the product's core differentiator.

### Why not fully unlock

Raw tracking recital ("you replayed this 4 times", "you listened to this 3 times this week") feels surveillance-grade. It names the listener's own data back at them as proof the product is watching. Sparse, grounded pattern callbacks feel like a host who knows you. Raw counts feel like a fitness tracker. The line is: describe the pattern, never cite the number.

## Code change

`resonova/api/gemini.py` → `_persistent_memory_guardrail(memory_enabled=True)`:

- **Removed from MAY clause**: `"and feedback corrections"` (now explicit list)
- **Added to MAY clause**: `"and pattern-level temporal callbacks (e.g. 'this sound keeps coming back for you'...)"`
- **Removed from NEVER clause**: `say "last time"` (blanket ban lifted)
- **Narrowed in NEVER clause**: `"mention replay counts or session history"` → `"recite raw replay counts or raw session numbers"`
- **Kept in NEVER clause**: `say "you replayed"` and `say "last cast"` (still banned)

## Related docs

- `docs/boss/product-pivot.md` — Stance C product pivot (2026-06-23)
- `docs/handoffs/Host Awareness Decision Discussion Handoff.md` — Stance A/B/C definitions
- `docs/boss/research/Resonova-analysis-market-competition.md` — temporal callbacks as moat
- `docs/boss/decisions/companion-direction-and-memory-use-brief.md` — memory control model
