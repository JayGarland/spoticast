# Fresh Cast MVP — Implementation Brief

Audience: Manager agents

## Context

Customer report: regenerating the same playlist produces repetitive casts — hosts cover
the same topics, same framing, same talking points. Root causes confirmed:

1. **Script cache** (`gemini.py`): cache key includes the full persistent profile + track
   URIs but NOT the per-playlist episode count. If the profile hasn't changed, regenerating
   the same playlist returns the exact same cached script.

2. **No prior-cast context**: even when the cache is bypassed, the model has no knowledge
   of what was covered in the previous episode. It independently converges on the same
   talking points because the same research material is injected each time.

Product decision (boss + WebUI agent): when a user chooses to generate a new cast for a
playlist they've already cast, the new episode should be a *continuation* — build on what
worked, don't repeat what was already said.

## MVP Scope (do these three, nothing else)

1. **Cache key** — add `prior_cast_count` to the script fingerprint so each episode after
   the first is guaranteed to trigger a fresh generation.
2. **Prompt enrichment** — inject a lightweight previous-cast summary into the prompt with
   a "build forward" instruction.
3. **UI guard** — confirm before starting a fresh generation when saved episodes already
   exist for the playlist; redirect to progress if generation is already running.

## Files Allowed

- `resonova/episodes.py`
- `resonova/server.py`
- `resonova/api/gemini.py`
- `resonova/web/player.js`

No-go:
- `resonova/config.py`, `resonova/profile.py`, `resonova/variety.py`
- `resonova/api/research.py`, `resonova/api/spotify.py`
- Any test files

---

## Task 1 — `episodes.py`: add helpers + summary field

### 1a. New function: `get_playlist_episode_count`

```python
def get_playlist_episode_count(playlist_uri: str) -> int:
    """Return the number of saved (non-error) episodes for a given playlist URI."""
    if not _EPISODES_DIR.exists():
        return 0
    count = 0
    for ep_dir in _EPISODES_DIR.iterdir():
        meta_path = ep_dir / "episode.json"
        if not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text())
        except Exception:
            continue
        if meta.get("playlist_uri") == playlist_uri and meta.get("status") == "complete":
            count += 1
    return count
```

Place after `list_episodes()`.

### 1b. New function: `get_latest_playlist_episode`

```python
def get_latest_playlist_episode(playlist_uri: str) -> dict | None:
    """Return the most recently created complete episode for a playlist, or None."""
    if not _EPISODES_DIR.exists():
        return None
    candidates = []
    for ep_dir in _EPISODES_DIR.iterdir():
        meta_path = ep_dir / "episode.json"
        if not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text())
        except Exception:
            continue
        if meta.get("playlist_uri") == playlist_uri and meta.get("status") == "complete":
            candidates.append(meta)
    if not candidates:
        return None
    return max(candidates, key=lambda m: m["created_at"])
```

Place after `get_playlist_episode_count`.

### 1c. `save_episode`: accept optional `prior_cast_summary`

Add parameter `prior_cast_summary: str | None = None` to `save_episode()`.
After the `tagline` block, add:

```python
if prior_cast_summary is not None:
    meta["prior_cast_summary"] = prior_cast_summary
```

This persists the summary so the *next* generation can read it.

---

## Task 2 — `server.py`: inject prior-cast context + persist summary

### 2a. New helper: `_extract_cast_summary`

Add near the top of `server.py` (after imports, before route handlers):

```python
def _extract_cast_summary(script: dict, episode_name: str) -> str:
    """
    Build a lightweight text summary of a generated script for prior-cast injection.

    Extracts: episode title, intro opening sentence, first sentence of each track's
    commentary. Capped at ~600 chars to keep the prompt lean.
    """
    parts: list[str] = [f'Episode title: "{episode_name}"']

    intro_text: str = ""
    intro = script.get("intro") or {}
    if isinstance(intro, dict):
        intro_text = (intro.get("text") or "").strip()
    elif isinstance(intro, str):
        intro_text = intro.strip()
    if intro_text:
        first_sentence = intro_text.split(".")[0].strip()
        if first_sentence:
            parts.append(f"Intro framing: {first_sentence}.")

    track_segments = script.get("tracks") or []
    for seg in track_segments[:6]:  # cap to first 6 tracks
        commentary = ""
        if isinstance(seg, dict):
            raw = seg.get("commentary") or seg.get("text") or ""
            if isinstance(raw, dict):
                raw = raw.get("text") or ""
            commentary = str(raw).strip()
        if commentary:
            first = commentary.split(".")[0].strip()
            artist = seg.get("artist", "") if isinstance(seg, dict) else ""
            title = seg.get("title", "") if isinstance(seg, dict) else ""
            label = f"{artist} – {title}" if artist and title else "track"
            if first:
                parts.append(f"{label}: {first}.")

    summary = " | ".join(parts)
    return summary[:700]  # hard cap
```

### 2b. In `_run_generation`: load prior-cast context before script generation

Inside `_run_generation`, after the research enrichment step (after
`research_api.enrich_with_research(context, ...)`) and before
`gemini_api.generate_script(context)`, add:

```python
# Prior-cast context for cache-busting and prompt enrichment
_prior_count = episodes_store.get_playlist_episode_count(job.playlist_uri) if job.playlist_uri else 0
context["prior_cast_count"] = _prior_count
if _prior_count > 0 and job.playlist_uri:
    _latest = episodes_store.get_latest_playlist_episode(job.playlist_uri)
    if _latest:
        if _latest.get("prior_cast_summary"):
            context["prior_cast_summary"] = _latest["prior_cast_summary"]
        # replay_count > 0 means the user listened to ≥50% of segments at least once
        # (tracked via the "meaningful" replay event in episodes.py)
        context["prior_cast_replay_count"] = _latest.get("replay_count", 0)
```

### 2c. In `_run_generation`: extract summary and persist with episode

After `script, identity = await asyncio.gather(...)` and after `episode_name` is assigned,
add:

```python
_cast_summary = _extract_cast_summary(script, episode_name)
```

Then pass `prior_cast_summary=_cast_summary` to the `episodes_store.save_episode()` call
in the success path (around line 772). The error partial-save paths do NOT need it.

---

## Task 3 — `gemini.py`: cache key + prompt injection

### 3a. `_script_cache_fingerprint`: add `prior_cast_count`

In `_script_cache_fingerprint`, add `"prior_cast_count"` to `cache_context`:

```python
cache_context = {
    "incognito": bool(context.get("incognito", False)),
    "memory_enabled": memory_enabled,
    "cast_depth": context.get("cast_depth"),
    "cast_vibe": context.get("cast_vibe"),
    "commentary_language": context.get("commentary_language"),
    "prior_cast_count": context.get("prior_cast_count", 0),   # ← add this
    "persistent_profile": persistent_profile,
}
```

`prior_cast_count` is `0` for a first-ever cast → same cache key as today (no regression).
Count increments with each saved episode → next generation guaranteed fresh.

### 3b. `build_prompt`: inject PREVIOUS CAST block

In `build_prompt`, after extracting all context variables, add:

```python
prior_cast_count: int = context.get("prior_cast_count", 0)
prior_cast_summary: str | None = context.get("prior_cast_summary")
```

At the END of the prompt (just before the final return), insert a PREVIOUS CAST section
when applicable:

```python
if prior_cast_count > 0 and prior_cast_summary:
    prompt_parts.append(
        f"\n## PREVIOUS CAST (episode {prior_cast_count} of this playlist)\n"
        f"{prior_cast_summary}\n\n"
        f"## CONTINUATION INSTRUCTION\n"
        f"This is episode {prior_cast_count + 1} for this playlist. "
        f"Build forward from the previous cast above. "
        f"Do not repeat the same framing, entry points, or talking points. "
        f"If the previous cast was thin on a track, go deeper this time. "
        f"If it was strong, open a new angle. "
        f"Make this feel like a natural next episode, not a repetition.\n"
    )
elif prior_cast_count > 0:
    # Have cast count but no stored summary (legacy episodes without summary field)
    prompt_parts.append(
        f"\n## CONTINUATION INSTRUCTION\n"
        f"This is episode {prior_cast_count + 1} for this playlist. "
        f"The listener has heard a previous cast for this playlist. "
        f"Vary your entry points, framing, and talking points — do not repeat.\n"
    )
```

The `prior_cast_replay_count` signal shapes the tone of the continuation instruction:
- `> 0` (user completed ≥50% of segments at least once) → they engaged with it; open
  a new angle on the same strengths.
- `== 0` → unclear whether they engaged; try a different approach, go deeper.

```python
prior_cast_count: int = context.get("prior_cast_count", 0)
prior_cast_summary: str | None = context.get("prior_cast_summary")
prior_cast_replay_count: int = context.get("prior_cast_replay_count", 0)
```

Continuation instruction text to use in the PREVIOUS CAST block:

```python
if prior_cast_replay_count > 0:
    continuation = (
        f"The listener replayed this cast (engaged with ≥50% of segments). "
        f"They found value in it — open a new angle, go further, do not repeat the same framing."
    )
else:
    continuation = (
        f"It is unclear whether the listener fully engaged with the previous cast. "
        f"Try a noticeably different approach: different entry points, different angle on the tracks."
    )
```

Adapt the exact `prompt_parts.append(...)` call to match how `build_prompt` currently
assembles its output (it may use string concatenation or a list — match the existing
pattern).

---

## Task 4 — `player.js`: UI guard

### 4a. Confirmation before fresh generation

The player already has an `_episodes` list (or fetches from `/api/episodes`). When
`generate(rawInput)` is called:

1. After parsing `rawInput` and getting a valid `playlistUri`, check whether
   `this._episodes` (or the loaded episode list) contains any entries where
   `episode.playlist_uri === playlistUri && episode.status === "complete"`.

2. If yes, show a lightweight confirmation overlay:
   - Text: `"You already have N cast(s) for this playlist. Generate a fresh episode?"`
   - Two buttons: `Cancel` (dismiss overlay, no generation) and `Generate fresh`
     (close overlay, continue with generation as normal).
   - Style: matches the existing modal/overlay pattern in the player.

3. If No (first cast ever) → proceed directly, no confirmation.

### 4b. Active generation redirect (already partially done by single-gen lock)

The single-gen lock (chef patch, current HEAD) already handles this: a second tap during
active generation returns to the generating state. Verify this still works after the
confirmation dialog is added. If the lock runs *before* the confirmation check, re-order
so the lock check comes first (no confirmation needed if generation already running —
just navigate to progress).

### 4c. Episode count source

Use `this._episodes` (the episodes array already loaded by the player). Filter by
`playlist_uri` and `status === "complete"`. Do NOT add a new network request for this
check — use the already-loaded list. If `this._episodes` is not populated at the time of
the tap, treat as 0 (no confirmation needed — conservative fallback avoids blocking
generation when data is unavailable).

---

## Acceptance Criteria

- [ ] Regenerating a saved playlist produces a different script (cache key busted)
- [ ] First-ever cast for a playlist: no confirmation dialog, no regression in cache key
- [ ] Prompt for episode 2+ contains a PREVIOUS CAST block when summary is available
- [ ] When `replay_count > 0` on prior episode, continuation instruction says "open a new angle" (liked signal)
- [ ] When `replay_count == 0`, continuation instruction says "try a different approach" (unknown engagement)
- [ ] Legacy episodes without `prior_cast_summary` still trigger the fallback instruction
- [ ] Confirmation dialog shows correct episode count (singular/plural)
- [ ] Cancel dismisses dialog without starting generation
- [ ] Tapping generate during active generation navigates to progress (no dialog shown)
- [ ] `python -m py_compile resonova/server.py resonova/api/gemini.py resonova/episodes.py` exits 0
- [ ] `node --check resonova/web/player.js` exits 0
- [ ] No other files modified

## Output

Produce a handoff at: `docs/handoffs/Fresh Cast MVP Handoff.md`

Include: changed functions with before/after logic, verification performed, any
edge cases noted (e.g. partial episode save paths, incognito casts).

Do not commit.
