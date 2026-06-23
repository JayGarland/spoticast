# Memory-Off Honesty Fix — Implementation Brief

Audience: Agents

## Context

Audit finding: High — "Memory off drops ALL personalization, not just the trail."
Verified in: Full Product Re-Audit Chef Gate 2026-06-23

The `memory_enabled` toggle is supposed to drop only the behavioral trail (recent listening
history / session context) while keeping durable taste data (long-term genre preferences,
recurring styles). The split logic already exists in `resonova/api/gemini.py`
(DURABLE-keep / TRAIL-drop), but it is dead code. `resonova/server.py` only attaches the
profile to the prompt when `memory_enabled=True`. When memory is off, no profile reaches
`gemini.py` at all, so the split never runs.

## Files

Allowed:
- `resonova/server.py` — profile attachment logic (~line 580-584)

No-go:
- Do not touch `resonova/api/gemini.py` — the DURABLE/TRAIL split already works correctly
- Do not touch the memory toggle UI in `resonova/web/player.js`
- Do not touch `resonova/profile.py`
- Do not modify any other files

## Task

In `resonova/server.py`, find the block that conditionally attaches the profile/memory
context to the Gemini prompt (currently gated on `memory_enabled=True`).

Change the condition so that:
- The profile is sent whenever the request is NOT incognito.
- `memory_enabled` does NOT control whether the profile is sent — it is already
  respected inside `resonova/api/gemini.py` (DURABLE-keep / TRAIL-drop).

After the fix:

| incognito | memory_enabled | Expected behaviour |
|---|---|---|
| True | any | No profile sent (unchanged) |
| False | False | Profile sent; gemini.py applies TRAIL-drop (durable taste only, no trail) |
| False | True | Profile sent; gemini.py includes everything (unchanged) |

## Acceptance Criteria

- [ ] `resonova/server.py` sends the profile whenever NOT incognito, regardless of `memory_enabled`
- [ ] No change to `resonova/api/gemini.py` DURABLE/TRAIL logic
- [ ] `python -m py_compile resonova/server.py` exits 0
- [ ] No other files modified

## Output

Produce a handoff at: `docs/handoffs/Memory-Off Honesty Fix Handoff.md`

Include: exact lines changed, verification performed, risks noted.

Do not commit.
