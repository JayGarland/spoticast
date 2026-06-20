---
title: "External Audio Balance & Replay Variety Audit — Report"
source: "External auditor — against docs/handoffs/External Audio Balance and Replay Variety Audit Handoff.md"
created: 2026-06-20
status: draft
verdict_audio: "Frontend Spotify volume is NOT sufficient on mobile. Add server-side commentary loudness normalization at generation time; keep a modest client trim for desktop/old episodes."
verdict_variety: "Uniform shuffle is not enough — and the script cache makes repeated orders return identical commentary. Minimal fix: persist recent per-playlist orders and pick a novel one (this also busts the cache and refreshes content). Profile/feedback stays parked."
constraints_met: "No code changed. No commits. No .env/token values read or printed."
---

# External Audio Balance & Replay Variety Audit — Report

## Executive Summary

**Audio balance.** The root cause is structural, not a tuning problem. Commentary MP3s are exported with **no loudness normalization at all** (`audio.py` converts raw Gemini TTS PCM straight to MP3), so commentary plays at whatever loudness the TTS model happened to produce — typically well below the integrated loudness of mastered Spotify tracks. The *only* balancing lever today is the client-side `_SPOTIFY_VOLUME = 0.62`, and that lever is applied on the one surface where it is least reliable: the Spotify Web Playback SDK's `setVolume()` is a known no-op on iOS / mobile Safari, where playback volume is controlled by the hardware. So on the owner's phone — the product's target environment — the music very likely plays at full while commentary stays quiet, producing exactly the reported mismatch. Lowering Spotify further can't help mobile and would hurt desktop; HTML `<audio>` can't exceed `volume = 1`. The durable, cross-device fix is therefore **server-side loudness normalization of the commentary at generation time** (EBU R128 / `loudnorm` via the ffmpeg that pydub already uses), with the client trim retained only as a secondary adjustment for desktop and already-saved episodes.

**Replay variety.** Two reinforcing causes make repeated generations feel stale. First, `_select_playlist_tracks_for_episode()` shuffles but has **no memory of prior generated orders** — its retry loop only avoids reproducing the *original playlist order*, not the order you got last time. Second, and more importantly, the Gemini script cache is keyed on **order alone** (`cache_key("script_v4_ordered", username, *track_uris)`), with no seed/nonce/episode-id — so any time a shuffle lands on a previously-seen order, the app returns **byte-identical commentary**, and for short playlists (≤ `MAX_TRACKS`, where every track is always included) the song *set* never changes either. Order variation also only changes *sequence*, never the hosts' angle, voice, or content (consistent with the earlier UX audit). The smallest high-impact fix is to **persist a short history of recent orders per playlist and choose a novel one** — this guarantees a different sequence, which in turn busts the order-keyed cache and yields genuinely fresh commentary (different neighbors → different transitions). Deeper freshness (taste profile, feedback weighting, prompt/lens variation) is the real long-term answer but should stay **parked** per the existing strategy.

---

## Method & Limitations

**Inspected:** `resonova/api/audio.py`, `resonova/api/tts.py`, `resonova/api/gemini.py` (prompt + cache key), `resonova/cache.py`, `resonova/server.py` (`_select_playlist_tracks_for_episode`), `resonova/web/player.js` (volume constants/usage); strategy docs `audio-level-balance-brief.md`, `playlist-order-variety-brief.md`, `persistent-profile-feedback-brief.md`; prior `External Product UX Design Audit Handoff.md` and `Resonova MVP Audit Handoff.md`. The running app was reachable for live UI corroboration.

**Limitations (honest):**
- **Audio loudness was not measured instrumentally.** I did not capture/meter the actual LUFS of commentary vs. Spotify output on the device — that requires audio capture tooling the audit environment doesn't have. The loudness-mismatch conclusion is from the code (no normalization) plus the documented iOS `setVolume` limitation plus the owner's report, not from a measured delta. A measurement step is included in the acceptance test.
- **Commit-level `git diff` could not be run this pass** (the sandbox VM that runs git was unavailable). Findings rest on the current code state, which is decisive for both issues; commit *messages* (`783ddf1` balance Spotify volume, `1f07074` vary cast order, `e729f2b` bounded SDK recovery) are taken from the brief.

---

## Part A — Audio Level Balance

### Findings

**A1 · High · Commentary is never loudness-normalized.** `assemble_commentary()` builds an `AudioSegment` from raw 24 kHz/16-bit/mono PCM, appends 800 ms of trailing silence, and exports to MP3 — no gain, normalization, or compression (`audio.py:15-29`). Commentary loudness is 100% whatever the TTS model emitted. TTS speech is typically quiet and varies block-to-block; mastered music is loud and consistent. This is the structural source of the imbalance.

**A2 · High · The only balance lever lives on the least reliable surface for mobile.** Balance is achieved solely by lowering Spotify via `_SPOTIFY_VOLUME = 0.62` (`player.js:1163`), applied through the SDK constructor and `spotifyPlayer.setVolume()` (`player.js:644`). The Web Playback SDK's `setVolume()` does not control output volume on iOS/mobile Safari (hardware-controlled) — a limitation the team has already noted. So on the target device the intended attenuation likely **does nothing**, leaving full-loudness music against quiet commentary.

**A3 · Medium · No floor/ceiling on commentary loudness.** Because nothing normalizes the file, even desktop balance is a moving target: a quieter-than-usual TTS block will feel softer regardless of the Spotify trim. A target loudness gives consistency across blocks and episodes.

**A4 · Constraint · The fix has to raise commentary, not just lower music.** HTML `<audio>` can't exceed `volume = 1`, and Spotify is already attenuated, so the headroom is in the commentary file. That can only be added at the file level (server-side), which conveniently is the one audio surface Resonova fully controls on every device.

### Recommendation (audio)

**Target strategy:** normalize commentary to a defined integrated loudness at generation time, and treat the client Spotify trim as a secondary, desktop-only adjustment.

- **Primary (durable, cross-device):** in `assemble_commentary()`, run the exported commentary through EBU R128 loudness normalization — `ffmpeg`'s `loudnorm` filter (already available via pydub's ffmpeg dependency) targeting roughly **I = -14 LUFS, TP = -1 dBTP, LRA ~11** (the streaming-normalization ballpark Spotify itself uses, so commentary sits at a similar perceived level to music). A simpler pydub-only fallback is `pydub.effects.normalize()` plus a fixed target-gain toward a measured dBFS, but loudnorm is the more reliable, perceptual choice and is preferred. Apply a true-peak ceiling/limiter so raising quiet speech doesn't clip.
- **Secondary:** keep `_SPOTIFY_VOLUME` (it still helps on desktop where `setVolume` works, and it affects already-saved episodes). Once commentary is normalized up toward -14 LUFS, consider raising `_SPOTIFY_VOLUME` back toward ~0.8–0.9 so desktop isn't over-attenuated.
- **Do not** add a user-facing balance slider for the MVP — it pushes a tuning burden onto the owner and isn't needed once normalization lands. Keep it as a future fallback only if normalization proves insufficient.

**Minimal implementation path:** one change in `resonova/api/audio.py` (normalize on export) + one optional constant tweak in `player.js`. No schema, queue, or player-logic changes.

**Risk — old vs. new episodes:** server-side normalization affects **only future generated commentary**; the ~dozen already-saved episodes keep their quiet MP3s. The client `_SPOTIFY_VOLUME` change affects **both**. If consistent old-episode loudness matters, add an optional **one-time batch re-normalize** over `generated/episodes/**/*.mp3` (idempotent if you tag normalized files), but this is optional and lower priority than fixing the generation path.

**Acceptance test method:**
- *Instrumented:* generate a new episode; meter integrated LUFS of a commentary MP3 (e.g. `ffmpeg -i file.mp3 -af loudnorm=print_format=json -f null -`) and confirm it lands near the -14 LUFS target; compare against a Spotify track's known ~-14 LUFS.
- *Perceptual, phone (primary):* on the phone via Tailscale HTTPS, play a new episode through a commentary→music→commentary transition at a fixed system volume and confirm no need to adjust volume between segments.
- *Perceptual, desktop:* repeat; verify desktop isn't now too quiet on music (tune `_SPOTIFY_VOLUME` if so).
- *Regression:* play one **old** saved episode and note that it's still quiet (expected) — decide whether the batch re-normalize is worth it.

---

## Part B — Replay Variety / Shuffle

### Findings

**B1 · High · Shuffle has no memory of prior generated orders.** `_select_playlist_tracks_for_episode()` (`server.py:78-88`) shuffles the full track list up to five times, returning the first result whose first `MAX_TRACKS` differs from the **original playlist order** (`selection != original_selection`). It never compares against orders produced by *previous generations*, and nothing is persisted, so two consecutive regenerations can yield the same (or near-same) order purely by chance — with no guard.

**B2 · High · The script cache is keyed on order only, so repeated orders return identical commentary.** `generate_script()` builds `script_key = cache_key("script_v4_ordered", username, *track_uris)` (`gemini.py:367-370`); `cache_key` is a SHA1 of the lowercased, pipe-joined parts (`cache.py:16-19`) — **no seed, nonce, or episode id**. Consequences: (a) any regeneration that lands on a previously-used order is a cache **hit** and replays the exact same script (even though `temperature=1.1` would otherwise vary it); (b) there is no way to get a *different take on the same order* — content variety is entirely a side effect of order variety. This is the mechanism that most directly produces "it feels the same."

**B3 · Medium · Short playlists and clustering weaken shuffle further.** For playlists with ≤ `MAX_TRACKS` tracks (default 30), every track is always included — only order changes, so the song *set* and (on cache hits) the commentary are identical across runs. Uniform `random.shuffle` also makes no effort to space out tracks by the same artist/album (clustering) and has no opener/closer variation, so even fresh orders can feel lumpy. (For playlists *larger* than `MAX_TRACKS`, the shuffle-then-slice does already vary the selected subset run-to-run — that part is fine.)

**B4 · Medium · "Energy-arc" ordering is tempting but not reliably available.** Spotify's audio-features endpoint returns 403 in Development Mode and the pipeline degrades gracefully without it (per `Resonova MVP Audit Handoff.md`), so `energy/valence/tempo` may be empty (`gemini.py:264` guards on `if feat`). Any ordering algorithm that depends on audio features (energy arc, tempo flow) can't be trusted as the primary mechanism in this environment.

**B5 · Product · Order alone changes sequence, not content, voice, or angle.** As the prior UX audit already noted, robust "freshness" ultimately needs taste profile, feedback, and prompt/lens variation — none of which exist yet, and all of which are explicitly parked in `persistent-profile-feedback-brief.md`.

### Recommendation (variety)

**Keep shuffle, but make it memory-aware — that single change fixes both B1 and B2 at once.**

Minimal robust MVP algorithm:
1. **Persist recent orders per playlist** in a small local file (e.g. `generated/variety/<playlist_id>.json`: a list of the last *k* selected-URI-orders, k≈3–5, with timestamps). Gitignored under existing `generated/`.
2. On generation, shuffle as today but **reject any candidate whose order matches a recent one**; pick the first novel order (fall back to most-different if all collide on a tiny playlist). This *guarantees* a new sequence, which — because the cache key includes order — automatically **busts the script cache and produces fresh commentary** with different prev/next neighbors. One mechanism, both problems.
3. **Artist/album adjacency spacing:** after choosing the order, do a light pass that avoids placing two tracks by the same artist/album back-to-back (swap within the window). Cheap, no features needed, removes the "lumpy" feel.
4. **Preserve pasted track order** unchanged (pasted input is an intentional signal) — keep the existing branch that skips shuffling for `track_uris`.
5. **For playlists > `MAX_TRACKS`,** also record which *tracks* were used recently and bias selection toward not-recently-used tracks (selection novelty), so big playlists rotate their material rather than re-drawing the same favorites.

**Cache-key implication (important):** the order-keyed cache is *correct* and worth keeping for cost — and with memory-aware novel ordering it naturally yields new scripts. If, later, you want a *different take on the same order* (e.g. a "Surprise me" re-roll), add an explicit small `variation` token (a rotating lens/seed 0..N-1) to **both** the prompt and the cache key, so repeats rotate through a bounded set of distinct takes without unbounded cost. Do **not** nonce the key per run (that defeats caching entirely).

**Parked (do later, not now):** taste/profile + feedback weighting, explicit modes (`Deep cut` / `Flow` / `Favorites` / `Surprise`), and energy/mood-arc ordering (blocked by audio-features availability). These are the real long-term freshness levers but are out of scope for a stable MVP.

---

## Answers To The Key Questions

1. **Is `_SPOTIFY_VOLUME = 0.62` good enough for mobile?** No. On iOS/mobile Safari the SDK `setVolume()` is effectively a no-op, so the attenuation likely doesn't apply on the target device. It's a partial desktop fix at best.
2. **Should commentary be normalized at generation, and where?** Yes — in `resonova/api/audio.py` (`assemble_commentary`), via ffmpeg `loudnorm` to a fixed target (~-14 LUFS, -1 dBTP). This is the only fix that works across devices because it operates on the file Resonova controls.
3. **Order-only, or memory/feedback for variety?** Order-only is insufficient, but the *minimal* effective fix is **memory-aware ordering** (recent-order avoidance), not full profile/feedback. Persistent memory/feedback is the real long-term fix and should stay parked.
4. **Smallest change that makes repeats feel less stale?** Persist recent per-playlist orders and pick a novel one. Because the cache is order-keyed, novel order → cache-bust → fresh commentary. One small persisted artifact + one selection tweak.
5. **What stays parked until the MVP is stable?** Taste profile, feedback loops, explicit replay "modes," energy/mood-arc ordering (features unreliable), a user balance slider, and old-episode batch re-normalization (optional, low priority).

---

## Concrete Next Implementation Brief (RUG-ready, if approved)

**Work item 1 — Commentary loudness normalization (audio).**
- Scope: `resonova/api/audio.py` only (+ optional one-line `player.js` constant).
- Change: in `assemble_commentary()`, after building the segment, apply ffmpeg `loudnorm` (I=-14, TP=-1, LRA=11) on export (or a two-pass measure+apply for accuracy); keep the 800 ms trail silence.
- Optional: raise `_SPOTIFY_VOLUME` toward ~0.85 once commentary is louder.
- Acceptance: new commentary meters near -14 LUFS; phone A/B shows no inter-segment volume adjustment; desktop music not too quiet; old episodes unchanged (documented).
- Out of scope: slider, per-segment gain UI, touching saved episodes (separate optional batch task).

**Work item 2 — Memory-aware replay ordering (variety).**
- Scope: `resonova/server.py` (`_select_playlist_tracks_for_episode` + a tiny persistence helper, possibly a new `resonova/variety.py`); no change to `gemini.py` cache key required for the MVP.
- Change: persist last k orders per playlist under `generated/variety/<playlist_id>.json`; reject recent orders when shuffling; add artist/album adjacency spacing; for >MAX_TRACKS playlists, bias selection away from recently-used tracks; keep pasted-order branch untouched.
- Acceptance: three consecutive regenerations of the same playlist produce three distinct orders and three distinct scripts (cache misses); pasted track lists keep exact order; no same-artist back-to-back within the spacing window.
- Out of scope: cache-key changes, lenses/modes, profile/feedback, energy-arc.

---

## Do-Not-Do List (avoid overbuild)

- **Do not** rely on Spotify SDK `setVolume()` as the mobile balance fix — it doesn't work on iOS.
- **Do not** add a user-facing balance slider for the MVP.
- **Do not** nonce the script cache key per run (kills caching/cost control). Use bounded order memory; add a small rotating `variation` token only if a "re-roll same order" feature is later wanted.
- **Do not** build energy/mood-arc ordering now — audio features are unreliable (Dev Mode 403).
- **Do not** implement persistent profile/feedback during this work — it stays parked.
- **Do not** touch Spotify SDK recovery, the player UI layout, or the pasted-track-order behavior.
- **Do not** retro-modify saved episodes as part of the core fix (optional separate batch only).
- **Do not** expose `.env`, tokens, or secrets.

---

## Evidence Index

| Claim | Evidence |
|---|---|
| No commentary normalization | `audio.py:15-29` (PCM→MP3, only trail silence) |
| TTS raw PCM, model-dependent loudness | `tts.py:41-96` (returns raw PCM; no gain stage) |
| Balance lever is client Spotify volume only | `player.js:1163` (`_SPOTIFY_VOLUME = 0.62`), `:644` (`setVolume`), brief note on iOS no-op |
| Shuffle has no prior-order memory | `server.py:78-88` (compares only to original order; nothing persisted) |
| Script cache keyed on order only | `gemini.py:367-370`; `cache.py:16-19` (SHA1 of parts, no seed/nonce) |
| Short playlists include all tracks | `server.py:81-88` (`episode_tracks[:max_tracks]` after shuffle of full list) |
| Audio features unreliable (Dev Mode) | `Resonova MVP Audit Handoff.md` (audio-features 403, graceful degrade); `gemini.py:264` guard |
| Order changes sequence not content | `External Product UX Design Audit Handoff.md` (variety finding) |
| Prior decisions: shuffle + parked normalization/profile | `playlist-order-variety-brief.md`, `audio-level-balance-brief.md`, `persistent-profile-feedback-brief.md` |

Commits named in the brief (messages, not diff-verified this pass): `783ddf1` balance Spotify music volume · `1f07074` vary playlist cast order · `e729f2b` add bounded Spotify SDK recovery.

---

## Areas Not Tested

- **Instrumented loudness measurement** of commentary vs. Spotify on-device — not performed (no audio-capture tooling). Conclusion is code- and report-based; the acceptance test specifies the measurement.
- **Commit-level `git diff`** — not performed (git sandbox unavailable); current code state used instead.
- **Whether `setVolume` is a no-op on the owner's *specific* phone** — taken from the documented SDK limitation + owner report, not re-measured on the device.
- **Behavior on very short playlists (2–4 tracks)** for the proposed order-memory algorithm — flagged as an edge case to handle (fall back to most-different order when all recent orders collide).

## Constraint Compliance

No code implemented, no commits, no `.env`/token values read or printed, product identity unchanged, no rewrite recommended, and verified facts (code/line evidence) are separated from the items dependent on on-device audio behavior (flagged as not measured).
