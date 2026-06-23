# Memory-Off Honesty Fix — Handoff

Audience: Agents

## Status

**Already fixed.** Commit `81fa9ad` ("Fix memory-off dropping all personalization, not just the trail") resolves the audit finding. No further action required.

## What was wrong

`resonova/server.py` attached the persistent profile to the generation context only when `memory_enabled=True`. This meant `resonova/api/gemini.py`'s DURABLE-keep / TRAIL-drop split was dead code — toggling memory off silently dropped durable taste data too.

## What changed

Single change in `resonova/server.py` (old lines ~581-582):

```diff
         if not job.incognito:
             try:
                 _prompt_profile = profile_store.load_profile()
-                if _prompt_profile.get("memory_enabled", True):
-                    context["persistent_profile"] = _prompt_profile
+                context["persistent_profile"] = _prompt_profile
             except Exception as _pe:
                 logger.warning("Could not load profile for prompt: %s", _pe)
```

## Verification

- `python -m py_compile resonova/server.py` — exit 0
- No other files modified
- `resonova/api/gemini.py` untouched — the DURABLE/TRAIL split in `build_prompt` is unchanged and now gets exercised correctly

## Behaviour after fix

| incognito | memory_enabled | Profile sent to gemini.py |
|---|---|---|
| True | any | No (profile never loaded) |
| False | False | Yes; gemini.py applies TRAIL-drop (durable taste only) |
| False | True | Yes; gemini.py includes everything |

## Commit

`81fa9ad54265af6f258648f149291f5a3221d069` — the tip of the default branch as of this handoff.

## Risks

None identified. The `memory_enabled` toggle is still correctly respected inside `gemini.py` and the profile-summarizer code in `server.py` (lines 788-810). Incognito casts continue to skip all profile writes and reads.
