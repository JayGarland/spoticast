---
title: "Fresh Cast MVP Handoff"
source: "docs/handoffs/Fresh Cast MVP Implementation Brief.md"
author: ""
published: false
created: 2026-06-23
description: "Implementation of episode continuation — cache busting, prompt enrichment, and UI guard to prevent repetitive casts when regenerating the same playlist."
tags:
  - handoff
  - fresh-cast
  - mvp
---

## Goal

When a user chooses to generate a new cast for a playlist they've already cast, the new episode should be a **continuation** — build on what worked, don't repeat what was already said. Three concrete changes:

1. **Cache key** — add `prior_cast_count` to the script fingerprint so each episode after the first is guaranteed to trigger a fresh generation.
2. **Prompt enrichment** — inject a lightweight previous-cast summary into the prompt with a "build forward" instruction.
3. **UI guard** — confirm before starting a fresh generation when saved episodes already exist for the playlist.

## Current Progress

All four tasks from the implementation brief are complete and validated.

### Task 1 — `episodes.py`: helpers + summary field

**Changes:**

- **`save_episode`** — added `prior_cast_summary: str | None = None` parameter. When provided, `meta["prior_cast_summary"]` is persisted alongside the episode (after the tagline block). Existing callers (partial-save error paths) continue to work without this parameter since it defaults to `None`, and the `if prior_cast_summary is not None` guard prevents writing `null` into the JSON.

- **`get_playlist_episode_count(playlist_uri)`** — new function (after `list_episodes()`). Iterates episode directories, counts those matching `playlist_uri` with `status == "complete"`. Returns `0` if the episodes directory doesn't exist.

- **`get_latest_playlist_episode(playlist_uri)`** — new function (after `get_playlist_episode_count`). Returns the most recent complete episode for a playlist (by `created_at`), or `None`. Used to read the prior cast summary and replay count.

**Validation:** `python -m py_compile resonova/episodes.py` exits 0.

### Task 2 — `server.py`: prior-cast context injection

**Changes:**

- **`_extract_cast_summary(script, episode_name)`** — new helper (top of file, after imports). Builds a lightweight text summary: episode title, intro first sentence, first sentence of up to 6 tracks' commentary. Hard-capped at 700 chars.

- **Prior-cast context loading in `_run_generation`** — after the research enrichment step and before `generate_script()`, loads `prior_cast_count` via `get_playlist_episode_count()` and stores it in `context["prior_cast_count"]`. When `prior_cast_count > 0`, also loads `prior_cast_summary` and `prior_cast_replay_count` from the latest episode.

- **Summary extraction + persistence** — after `script, identity` are gathered and `episode_name` is set, calls `_extract_cast_summary(script, episode_name)` and passes `prior_cast_summary=_cast_summary` to the success-path `save_episode()` call (~line 839). Error partial-save paths do NOT pass it (they already have different `status` values and are not used for prior-cast injection).

**Validation:** `python -m py_compile resonova/server.py` exits 0.

### Task 3 — `gemini.py`: cache key + prompt injection

**Changes:**

- **`_script_cache_fingerprint`** — added `"prior_cast_count": context.get("prior_cast_count", 0)` to `cache_context`. `0` for first-ever cast → same cache key as before (no regression). Increments with each saved episode → next generation guaranteed fresh.

- **`build_prompt`** — extracted `prior_cast_count`, `prior_cast_summary`, `prior_cast_replay_count` from context. Added a PREVIOUS CAST block at the end of the prompt (before the final return) with conditions:
  - If `prior_cast_count > 0` AND `prior_cast_summary` exists: full PREVIOUS CAST block with the summary, episode numbering, and a continuation instruction that varies by `prior_cast_replay_count` (> 0 → "open a new angle", == 0 → "try a different approach").
  - If `prior_cast_count > 0` but no summary (legacy episodes): fallback CONTINUATION INSTRUCTION without specific previous-cast details.
  - If `prior_cast_count == 0` (no prior episodes): no block added, prompt is byte-identical to before.

**Validation:** `python -m py_compile resonova/api/gemini.py` exits 0.

### Task 4 — `player.js`: UI guard

**Changes:**

- **`generate(rawInput)`** — after the single-generation lock check and after parsing `rawInput`, checks whether `parsed.playlist_uri` has existing saved episodes in `this._episodes`. If yes, asks the user for confirmation via an overlay dialog. The single-generation lock check runs FIRST (so active generation navigates to progress without showing the dialog).

- **`_confirmRegeneration(text)`** — new method returning a Promise that resolves `true` if user clicks "Generate fresh" or `false` if they click "Cancel". Shows a modal overlay with the confirmation text and two buttons.

- **HTML** — added `.regeneration-confirm` overlay to `index.html` with a text element and Cancel/Generate fresh buttons.

- **CSS** — added `.regeneration-confirm` styles to `styles.css` (fixed overlay with backdrop blur, centered card, dark styling matching the existing design system).

**UI flow:** Single-generation lock check → episode count check → (if episodes exist) show confirmation → (if proceed) continue with generation as normal. If `this._episodes` is empty/unloaded, treats as 0 (no confirmation — safe fallback).

**Validation:** `node --check resonova/web/player.js` exits 0.

## What Worked

- The cache key approach (Task 3a) is minimal and zero-regression: `prior_cast_count` defaults to `0` when absent from context, so existing cache entries from before this change are unaffected.
- The fallback in `build_prompt` for legacy episodes (no stored `prior_cast_summary`) means the feature works immediately for any playlist with prior episodes, even before any episode has the new summary field.
- The single-generation lock in `player.js` runs before the confirmation check, so users already in an active generation session don't get a confirmation dialog — they just navigate to progress.

## What Didn't Work

- Nothing significant. The implementation followed the brief closely and all changes compiled/checked on first pass.

## Next Steps

1. **Manual QA** — test the full flow:
   - Generate a cast for a playlist → verify prompt has no PREVIOUS CAST block.
   - Regenerate the same playlist → verify cache is busted, prompt contains PREVIOUS CAST block with summary.
   - Click Cancel on confirmation → verify no generation starts.
   - Tap generate while active generation is running → verify redirect to progress without confirmation.
   - Verify `replay_count > 0` vs `== 0` generates different continuation instruction text.
2. **Incognito casts** — verify that incognito mode still works: prior-cast context is loaded for incognito (it's production for the playlist, not personalization), but this should be confirmed.
3. **Monitor** — watch for any edge cases with legacy episodes (those saved before this change) that have no `prior_cast_summary` field.

## Relevant Files

- `resonova/episodes.py` — `get_playlist_episode_count()`, `get_latest_playlist_episode()`, modified `save_episode()`
- `resonova/server.py` — `_extract_cast_summary()` (new), prior-cast context injection in `_run_generation()`
- `resonova/api/gemini.py` — `_script_cache_fingerprint()` (added `prior_cast_count`), `build_prompt()` (added PREVIOUS CAST block)
- `resonova/web/player.js` — `generate()` (regeneration guard), `_confirmRegeneration()` (new)
- `resonova/web/index.html` — `.regeneration-confirm` overlay HTML
- `resonova/web/styles.css` — `.regeneration-confirm` overlay styles

## Constraints

- Do NOT modify: `resonova/config.py`, `resonova/profile.py`, `resonova/variety.py`, `resonova/api/research.py`, `resonova/api/spotify.py`, any test files.
- Error partial-save paths in `_run_generation` (quota_failed, gen_failed) should NOT receive `prior_cast_summary` — they are not used for prior-cast injection.
- The `prior_cast_summary` field is persisted alongside the episode but is NOT returned by `_public_episode()` — it's intentionally kept internal (the UI does not need it).

## Validation Needed

- [ ] `python -m py_compile resonova/episodes.py resonova/server.py resonova/api/gemini.py` — PASS
- [ ] `node --check resonova/web/player.js` — PASS
- [ ] Manual: first-ever cast for a playlist → no confirmation dialog, cache key unchanged
- [ ] Manual: second cast for same playlist → confirmation dialog appears, cache key differs from first
- [ ] Manual: active generation tap → redirect to progress (no dialog)
- [ ] Manual: Cancel dismisses dialog without starting generation
- [ ] Manual: prompt for episode 2+ contains PREVIOUS CAST block
- [ ] Manual: replay_count > 0 → "open a new angle" | replay_count == 0 → "try a different approach"
- [ ] Manual: legacy episodes (no `prior_cast_summary`) → fallback CONTINUATION INSTRUCTION
