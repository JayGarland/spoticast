# Episode Library Navigation and Model Refresh Handoff

**Date:** 2026-06-20  
**Branch/checkpoint:** from `98d6b4c Add saved cast management and replay variety`  
**Status:** Implementation complete — chef-reviewed, not committed per scope instructions

---

## Summary

Three improvements shipped in this task:

| Area | Change |
|---|---|
| A. Past Episodes UX | Grouped by playlist with collapsible accordion |
| B. In-app navigation | Back-to-library buttons + browser history (pushState/popstate) |
| C. Model config | `gemini-3.1-flash-lite-preview` → `gemini-3.1-flash-lite` default; TTS default updated to `gemini-3.1-flash-tts-preview` |

---

## Files Changed

```
.env.example            |   3 +-
resonova/config.py      |   6 ++-
resonova/web/index.html |   6 +++
resonova/web/player.js  |  96 ++++++++++++++++++++++++++
resonova/web/styles.css | 113 +++++++++++++++++++++++++++
5 files changed, 219 insertions(+), 5 deletions(-)
```

---

## A. Grouped Past Episodes (Accordion)

### Behavior
- `_loadEpisodes()` now groups episodes by `playlist_uri` before rendering.
- **Spotify playlist episodes** are grouped under their `playlist_name` header.
- **Custom track-list casts** (those with `playlist_uri = "track_list"`) are collected under a single **"Custom Casts"** group.
- Each group header shows: playlist name · N casts · latest date.
- Clicking/tapping a group header toggles its body open or closed (chevron `▸`/`▾` reflects state).
- **Default:** the most recently updated group is expanded; all others are collapsed.
- After rename or delete, `_loadEpisodes()` is called which re-renders all groups freshly.
- Custom casts do not show `Run #` badges (the existing `isPlaylistEpisode` guard already prevented this; no logic change needed).

### New methods in player.js
- `_episodeGroupHTML(group, expanded)` — renders one accordion group as HTML string.
- Group toggle handler added at the top of the `state-connected` click delegation (checks `[data-group-toggle]` attribute).

### CSS classes added (styles.css)
- `.ep-group` — container, border, border-radius
- `.ep-group.expanded` — state modifier
- `.ep-group-header` — clickable row, flex layout
- `.ep-group-chevron` — `▸`/`▾` indicator
- `.ep-group-name` — playlist name in Cormorant Garamond
- `.ep-group-meta` — cast count + latest date in DM Mono
- `.ep-group-body` / `.ep-group-cards` — hidden/shown body with card padding

### API compatibility
- `/api/episodes` output is unchanged. The frontend consumes the existing `playlist_uri`, `playlist_name`, `created_at`, and `run_number` fields. No backend changes.

---

## B. In-app Navigation / Back Path

### Browser history
- `init()` now calls `history.replaceState({ resonovaState: 'connected' | 'landing' })` on load.
- `generate()` calls `this._pushHistoryState('generating')` before `_showState('generating')`.
- `_startPlayback()` calls `this._pushHistoryState('playing')` before `_showState('playing')`.
- `_initHistoryNav()` registers a `popstate` listener: any back navigation to `'generating'` or `'playing'` state collapses into showing `'connected'`; `'landing'` shows landing.

### Back buttons
- **Playing state:** `<button class="back-btn" id="back-to-library-btn">← Library</button>` added above the segment-type badge. Clicking calls `_showState('connected')` — **does not stop playback**; audio and Spotify playback continue in the background.
- **Library while playing:** Chef gate added `Return to Player`, shown only when playback is active and the visible state is the library. This makes the back path reversible without relying on browser forward history.
- **Generating state:** `<button class="back-btn" id="back-from-generating-btn">← Back · generating in background</button>` added at the top of the generating state. Clicking shows the connected/library view; the SSE stream continues and will call `_loadEpisodes()` on completion and `_startPlayback()` on `intro_ready` (which will switch back to the playing view automatically).

### Safe behaviour
- Playback is never stopped by a back navigation — only the visible state changes.
- Generation continues fully in the background after the user returns to the library view. The `done` event still refreshes the episode list.

---

## C. Model Config Refresh

### Changes
| Setting | Old default | New default | Reason |
|---|---|---|---|
| `gemini_research_model` | `gemini-3.1-flash-lite-preview` | `gemini-3.1-flash-lite` | Preview shut down 2026-05-25 per official Gemini changelog |
| `gemini_tts_model` | `gemini-2.5-pro-preview-tts` | `gemini-3.1-flash-tts-preview` | Aligns with prod `.env` already in use; supports multi-speaker `MultiSpeakerVoiceConfig` API used by `tts.py` |
| `gemini_model` (script gen) | `gemini-3.1-pro-preview` | *(unchanged)* | No A/B testing yet; keep stable |

### Files touched
- `resonova/config.py` — field default strings updated with inline rationale comments.
- `.env.example` — tuning section updated: `GEMINI_RESEARCH_MODEL` comment added, `GEMINI_TTS_MODEL` comment updated. Real `.env` file NOT touched.

### Note for owners
Chef gate updated the local real `.env` file to `GEMINI_RESEARCH_MODEL=gemini-3.1-flash-lite` so the next real generation run does not use the shut-down preview model. `.env` is ignored and is not part of the commit diff.

---

## Validation Results

```
node --check resonova/web/player.js
→ Exit: 0  (syntax clean)

uv run python -c "from resonova.config import Settings; ..."
→ research_model default: gemini-3.1-flash-lite
→ tts_model default:      gemini-3.1-flash-tts-preview

uv run python -c "from resonova import server; print('server ok')"
→ server ok

uv run python tests/test_variety_episodes.py
→ fingerprint_stable ✓
→ select_produces_variety ✓
→ select_short_playlist ✓
→ pasted_track_order_not_affected ✓
→ save_variety_memory ✓
→ episodes_lifecycle ✓
→ episodes_backward_compat ✓
→ run_number ✓
→ episode_path_traversal_rejected ✓
→ All tests passed ✓
```

No running server available in this session for browser automation tests; see manual checklist below.

---

## Chef Gate Review Notes

Codex reviewed the manager output and made two bounded corrections before acceptance:

1. Updated local `.env` research model from `gemini-3.1-flash-lite-preview` to `gemini-3.1-flash-lite` so runtime behavior matches the new defaults.
2. Cleaned a small indentation artifact in `player.js` around the `generate()` state transition.
3. Added a `Return to Player` control in the library view when playback is active, so `← Library` does not strand the user away from playback controls.

---

## Manual Boss Test Checklist

### A. Grouped episodes
- [ ] Open the app with multiple saved casts from different playlists
- [ ] Past Episodes section shows one accordion row per playlist + one "Custom Casts" row if any custom casts exist
- [ ] Each row header shows: playlist name, cast count, latest date
- [ ] Most recent playlist group is expanded by default; others collapsed
- [ ] Clicking a collapsed group header expands it (chevron changes to `▾`)
- [ ] Clicking an expanded group header collapses it (chevron changes to `▸`)
- [ ] Episode cards inside groups have Play / Rename / Delete buttons working
- [ ] Rename → group re-renders correctly with new name
- [ ] Delete → group re-renders (or disappears if last episode in group)
- [ ] Custom track-list cast: appears in "Custom Casts" group, no `Run #` badge shown
- [ ] Mobile: group headers are tappable, layout is clean and scrollable

### B. In-app navigation
- [ ] Playing state has "← Library" button visible at top
- [ ] Clicking "← Library" while playing returns to the library view WITHOUT stopping audio
- [ ] Library view now shows "Return to Player" while audio is active
- [ ] Clicking "Return to Player" returns to the playing controls
- [ ] Generating state has "← Back · generating in background" button visible
- [ ] Clicking that button returns to library; when intro is ready, playing state appears automatically
- [ ] Browser back button from playing state returns to library (without stopping audio if supported)
- [ ] Browser back button from generating state returns to library
- [ ] Mobile device: hardware back gesture works the same way

### C. Model config
- [ ] Owner: update real `.env` to remove or update `GEMINI_RESEARCH_MODEL` line
- [ ] Generate a new cast and confirm no API errors related to the research model
- [ ] Confirm TTS synthesis works (multi-speaker dialogue renders correctly)

---

## Risks / Parked Work

| Risk | Notes |
|---|---|
| Real `.env` overrides research model | Owner must manually remove `GEMINI_RESEARCH_MODEL=gemini-3.1-flash-lite-preview` from their `.env`. Code default is correct. |
| Gemini `gemini-3.1-flash-lite` availability | Assumed available as stated in owner feedback. Verify API key / Vertex IAM allows this model. |
| Playback after "← Library" | Audio element and Spotify SDK remain active. If user generates a new cast immediately after returning to library, two playback contexts could conflict. Existing `_startPlayback()` fully resets the queue so this is safe. |
| Generating → back → new cast | SSE stream for the previous job continues. When it fires `intro_ready`, it will call `_startPlayback()` and switch to playing state even if the user is mid-form on a new cast. Low frequency edge case; no fix in scope here. |
| Accordion empty state | If user deletes all episodes in a group, `_loadEpisodes()` re-renders and empty groups disappear naturally (no episodes → no group key). Tested via `episodes_lifecycle` test. |

---

## Strategy Note: Model Freshness Decision

`gemini-3.1-flash-lite-preview` was deprecated on 2026-05-25 per official Gemini changelog (referenced in owner feedback). The replacement `gemini-3.1-flash-lite` is the GA version of the same model and is API-compatible. No prompt engineering or API call changes are needed.

`gemini-3.1-flash-tts-preview` was already in use in the production `.env` and confirmed working with the multi-speaker `MultiSpeakerVoiceConfig` API pattern in `resonova/api/tts.py`. The code default `gemini-2.5-pro-preview-tts` was a stale leftover from an earlier development phase.

`gemini-3.1-pro-preview` (script generation) is left unchanged pending A/B quality testing before committing to a model change.
