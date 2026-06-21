---
title: "Persistent Profile / Spotify Trails / Feedback Design Handoff"
created: 2026-06-21
status: design-complete (no code)
owner: Manager (reporting to Chef)
parent_brief: docs/handoffs/Persistent Profile Spotify Trails Design Brief.md
boss_decision: "Data-rich. user-library-read + user-follow-read are day-one scopes."
---

# Persistent Profile / Spotify Trails / Feedback Design Handoff

This is a design/handoff document only. No product code was written or changed.

It separates **VERIFIED FACTS** (read from the actual code or confirmed against
official Spotify docs) from **RECOMMENDATIONS** (design proposals that still need
boss/chef approval before build).

---

## 1. Verified Current Architecture Facts

All file:line references were read directly from the repo on the design branch.

### 1.1 Spotify scopes (source of truth)

VERIFIED — `resonova/config.py:52-63`, `Settings.spotify_scopes` returns exactly
these 9 scopes (space-joined):

```
user-read-recently-played
user-top-read
playlist-read-private
playlist-read-collaborative
streaming
user-modify-playback-state
user-read-playback-state
user-read-email
user-read-private
```

This matches the corrected list in the parent brief, including `streaming` and
`user-modify-playback-state`. Note: `user-modify-playback-state` is a
playback-*control* scope (it starts/pauses/transfers playback), **not** a
library/playlist-modifying write scope. `user-read-email` and `user-read-private`
are requested today but `user-read-email` is **not** needed for the memory layer
(see §10 open decision — it is a candidate for removal).

VERIFIED — the scope string is used in two places only:
`resonova/api/spotify.py:37` and `:47` (both inside `get_oauth`). There is no
other scope list anywhere; `config.py` is the single source.

### 1.2 OAuth / token handling

VERIFIED — `resonova/api/spotify.py:15-86`:
- OAuth is handled by `spotipy.SpotifyOAuth`. The token is cached to
  `.research_cache/.spotify_oauth` (`_OAUTH_CACHE`, line 15).
- Single-user / single-token model. There is no per-user keying anywhere — the
  process serves one authenticated Spotify identity at a time.
- `/auth/token` (`server.py:183-188`) returns the raw access token to the
  browser so the Web Playback SDK can use it. (Relevant to privacy: the token is
  already exposed to the frontend by design; the profile layer must not persist it.)

### 1.3 Spotify signals already fetched

VERIFIED — `resonova/api/spotify.py`:
- `fetch_user_context()` (`:243-266`) pulls top tracks + top artists across
  `short_term` / `medium_term` / `long_term` (50 each) and recently-played (50).
  Returns a `UserContext` dataclass (`:113-122`).
- `fetch_recent_plays()` (`:269-301`) derives recently-listened *playlists* from
  recently-played play-context.
- `fetch_user_playlists()` (`:328-352`) / `fetch_featured_playlists()` (`:304-325`).
- `build_playlist_context()` (`:355-418`) flattens top artists/tracks into a
  per-track context dict with `is_personal_favorite`, `recently_played`,
  `artist_in_top` flags, plus a `listener_profile` block
  (`top_artists_all_time[:20]`, `recently_played_count`).
- `fetch_audio_features()` (`:198-240`) — NOTE: the `/audio-features` endpoint
  returns 403 in Spotify Dev Mode and the code already degrades gracefully
  (`:213-220`). Audio features are therefore unreliable for a released app and
  should NOT be a load-bearing profile signal.

VERIFIED — `user-library-read` (saved tracks) and `user-follow-read` (followed
artists) are **NOT** fetched anywhere today. There are no calls to
`current_user_saved_tracks` or `current_user_followed_artists` in the codebase.
Designing them in is net-new work (scope + fetch + summarize).

### 1.4 Last.fm enrichment (already deep)

VERIFIED — `resonova/api/lastfm.py`:
- Optional; gated by API keys + a username (`is_configured()`, `:53-54`).
- Username persisted to a flat file `.lastfm_user` (`:36`), not in `.env`.
- Provides per-user: total scrobbles + member-since (`:375-400`); multi-period
  artist rankings overall/12m/3m/1m (`:165-191`); fan-era classification per
  artist (`:194-221`); loved tracks (`:467`); top-track play counts up to 1000
  (`:488`); per-artist bio/tags/similar-you-love (`:240-313`); per-track tags +
  wiki blurb (`:320-368`).
- Caches to `.research_cache/lastfm/` via `resonova/cache.py` plus in-memory dicts.
- Connect/disconnect/status endpoints: `server.py:191-213`; frontend widget:
  `player.js:761-809`, `index.html:115-141`.

This is the richest existing taste signal and is **already summarized**
(fan-era strings, top-artist lists) rather than raw — a good model to follow.

### 1.5 Resonova-owned memory that exists today

VERIFIED — two persistent stores already exist, both file-based under `generated/`:

**Saved cast episodes** — `resonova/episodes.py`:
- One JSON per episode at `generated/episodes/<episode_id>/episode.json`
  (`:33-69`). Fields: id, name, playlist_uri, playlist_name, track_count,
  created_at, status, queue, plus optional order_fingerprint /
  track_order_preview.
- `list_episodes()` (`:72-117`) computes per-playlist run numbers.
- Full CRUD: get/rename/delete (`:120-167`), surfaced via `server.py:239-287`.
- No taste summary is derived from these today — they are playback artifacts.

**Per-playlist variety memory** — `resonova/variety.py`:
- One JSON per playlist at `generated/variety/<sha1(playlist_uri)>.json`
  (`:26-27`), keyed by a SHA1 hash of the playlist URI (already a privacy-friendly
  pattern — no human-readable URI in the filename, though the URI is stored
  inside the file at `:33`).
- Stores last 5 selected track orders (`_MAX_RECENT = 5`, `:50`) to avoid
  repeating episode orderings. Written only after a successful save
  (`server.py:518-519`).
- This is the existing precedent for "summarized rolling memory with a cap."

VERIFIED — storage convention: all durable Resonova data lives under
`generated/` (episodes, variety) or `.research_cache/` (caches, oauth token,
lastfm user). `generated/` and `.research_cache/` are the natural homes for a
profile file. (Confirmed `.research_cache/` already holds the oauth token and
lastfm user — so a profile file must go somewhere that is clearly NOT secret-bearing.)

### 1.6 Where generation prompt context is assembled

VERIFIED — the pipeline in `server.py:_run_generation` (`:362-559`):
1. fetch tracks → `build_playlist_context` (`spotify_api`, `:404`)
2. optional Last.fm `enrich_context` (`:407-415`)
3. grounded research `enrich_with_research` (`:423-425`)
4. `gemini_api.generate_script(context)` (`:432`)

VERIFIED — the prompt is built in `resonova/api/gemini.py:build_prompt`
(`:208-329`). It already has a `═══ LISTENER PROFILE ═══` section
(`:313-314`) fed from `context["listener_profile"]` and `context["lastfm_user"]`.
This is the exact, single injection point a persistent profile would plug into —
no new wiring location needed, just an additional summarized block.

VERIFIED — the system prompt already instructs restraint on listener data:
`gemini.py:134` ("use sparingly and only when it reveals something interesting
about the music itself, not to comment on listening habits") and `:58`
("This is a music knowledge show, not a listener profile show"). The persistent
profile MUST respect this existing guardrail — see §7.

### 1.7 Frontend surfaces for memory controls

VERIFIED — `resonova/web/index.html` states/sections:
- `state-landing` (`:31`), `state-connected` (`:107`), `state-generating`
  (`:213`), `state-playing` (`:257`).
- Inside `state-connected`: a `service-row` Last.fm widget (`:115`) and three
  library sections — `section-episodes` (`:184`), `section-recent` (`:190`),
  `section-playlists` (`:196`).

VERIFIED — the Last.fm widget (`player.js:761-809`) is the existing pattern for a
small connect/status/disconnect service control. A "Memory" panel should reuse
this pattern and live in the same `state-connected` service/library area. The
saved-cast list (`section-episodes`) already has per-item delete — the precedent
for "inspect + remove" UI exists.

### 1.8 Spotify endpoint/scope facts (confirmed against official docs)

VERIFIED via `developer.spotify.com` (fetched 2026-06-21):
- `user-library-read` → "Read access to a user's library." Endpoint
  `GET /me/tracks` ("Get User's Saved Tracks"). Max `limit=50`, offset-based
  pagination, returns `total`/`next`.
- `user-follow-read` → "Read access to the list of artists and other users that
  the user follows." Endpoint `GET /me/following`, only `type=artist` supported,
  max `limit=50`, **cursor-based** pagination (`after` cursor).
- Write scopes confirmed and explicitly OUT of scope per HARD NO-GO:
  `user-library-modify`, `user-follow-modify`, `playlist-modify-private`,
  `playlist-modify-public`.
- `user-read-currently-playing` exists as a narrower alternative to
  `user-read-playback-state`.
- No relevant read scope was found to be deprecated (only the Implicit Grant
  *flow* is deprecated, which Resonova does not use — it uses Authorization Code
  via spotipy).

CANNOT-VERIFY NOTE: I confirmed scope strings, endpoint paths, and pagination
from official docs. I did NOT independently re-confirm current Spotify *platform
policy / quota-mode* constraints (e.g. extended-quota review requirements for a
released multi-user app). Those are a release-stage concern flagged in §10, not
verified here.

---

## 2. Current Signals Already Available (summary table)

| Signal | Source | Status | Persisted today? |
|---|---|---|---|
| Top artists/tracks (short/med/long) | Spotify `user-top-read` | live per generation | No |
| Recently played tracks + playlists | Spotify `user-read-recently-played` | live | No |
| User playlists | Spotify `playlist-read-*` | live | No |
| Playback/device state | Spotify `user-read-playback-state` | live (player) | No |
| Audio features | Spotify (no scope) | UNRELIABLE (403 in Dev Mode) | No |
| Scrobbles, fan-era, loved, play counts, artist bios | Last.fm (optional) | live when connected | cached only |
| Saved casts (episodes) | Resonova | persisted | `generated/episodes/` |
| Per-playlist order memory | Resonova | persisted | `generated/variety/` |
| Saved tracks (library) | Spotify `user-library-read` | NOT FETCHED YET | No |
| Followed artists | Spotify `user-follow-read` | NOT FETCHED YET | No |
| Explicit feedback | — | DOES NOT EXIST YET | No |

Key takeaway: Resonova already *reads* a lot per-generation but *remembers*
almost nothing about taste. The profile layer's job is to **summarize and
persist** what is already fetched, plus add the two boss-approved scopes and a
feedback channel.

---

## 3. RECOMMENDATION — Minimal v0 Profile Schema

One human-inspectable JSON file. Recommended path:
`generated/profile/profile.json` (sits alongside `generated/episodes/` and
`generated/variety/`, is git-ignorable, and is NOT in `.research_cache/` so it is
clearly separated from the oauth token / secrets).

This revises the brief's suggested shape: I **dropped** `audio-features`-derived
fields (unreliable), **dropped** raw URI lists in favour of human-readable
"Artist — Track" strings, **added** explicit `pinned`/`source` provenance on
every memory and preference, and **kept the whole thing small and string-first**
so the owner can read and edit it by hand.

```json
{
  "profile_version": 1,
  "updated_at": "2026-06-21T00:00:00Z",
  "memory_enabled": true,

  "sources": {
    "spotify": {
      "connected": true,
      "scopes_used": ["user-top-read", "user-library-read", "user-follow-read"],
      "last_refreshed_at": "2026-06-21T00:00:00Z"
    },
    "lastfm": { "connected": false, "last_refreshed_at": null },
    "resonova": { "saved_cast_count": 7, "feedback_count": 3 }
  },

  "taste_profile": {
    "top_artists": ["Radiohead", "Burial", "Aphex Twin"],
    "saved_library_artists": ["Four Tet", "Caribou"],
    "followed_artists": ["Jamie xx", "Floating Points"],
    "recurring_styles": ["ambient techno", "90s alt-rock", "uk garage"],
    "favorite_eras": ["late 90s", "early 2010s"],
    "recent_shifts": ["leaning more ambient this month"],
    "playlist_patterns": ["late-night focus playlists", "long-form mixes"]
  },

  "commentary_preferences": {
    "tone": ["analytical", "warm"],
    "depth": "balanced",
    "avoid": ["talking about my listening habits directly", "long intros"],
    "loved_patterns": ["recording stories", "artist connections"]
  },

  "memories": [
    {
      "id": "mem_01J...",
      "text": "Cares about production detail more than lyrics.",
      "source": "feedback",
      "confidence": "high",
      "pinned": true,
      "created_at": "2026-06-21T00:00:00Z",
      "last_used_at": null
    }
  ]
}
```

Design rules baked into the schema:
- **String-first, no raw blobs.** Every taste field is a short human-readable
  list. No URI dumps, no audio-feature vectors, no per-track scrobble logs.
- **Provenance on everything.** Each memory has a `source`
  (`spotify | lastfm | feedback | saved_cast | manual`) and `confidence`. This is
  what makes feedback-override (§6) tractable.
- **`pinned` + `memory_enabled`** make edit/disable trivial (see §8).
- **No secrets, no email, no tokens** persisted — only derived summaries.
- Caps recommended at build time: `memories` ≤ ~40 entries (LRU/least-confidence
  eviction), each list field ≤ ~20 items, following the `variety.py` cap precedent.

**Feedback raw events** stay in a *separate* append-only file
`generated/profile/feedback.jsonl` (one event per line), summarized into
`profile.json` rather than read raw at generation time. Recommended retention:
keep raw feedback for a rolling window (e.g. last ~200 events or 90 days), then
let the summary in `profile.json` carry the durable signal. This honours
"prefer summarized memory over raw permanent logs."

---

## 4. RECOMMENDATION — Day-One vs Parked Signals

### Day-one signals (build these first)

1. **Persist what is already fetched.** Summarize the existing
   `fetch_user_context()` output (top artists, recurring styles via Last.fm tags
   when present, recently-played playlist patterns) into `taste_profile` after
   each generation. Zero new scopes, lowest risk, immediate "it remembers me"
   payoff for a fresh browser user.
2. **Saved tracks** — Spotify `user-library-read` (boss-approved). Fetch
   `GET /me/tracks` (cap a sensible page count, e.g. up to 200 most-recent saved),
   summarize into `taste_profile.saved_library_artists` + style hints. This is the
   "what the user keeps" durable signal.
3. **Followed artists** — Spotify `user-follow-read` (boss-approved). Fetch
   `GET /me/following?type=artist`, summarize into
   `taste_profile.followed_artists`. Explicit affinity beyond recent behavior.
4. **Saved-cast history** — derive light memory from existing
   `generated/episodes/` (e.g. "frequently casts late-night focus playlists").
   Resonova-owned, no new permission.
5. **Explicit feedback** — new lightweight thumbs + tags channel (§6). The only
   signal that can *override* the inferred ones.

For #2 and #3, both must be summarized to artist names / style words — do NOT
persist raw saved-track URIs or full followed-artist payloads.

### Parked signals (evaluate later, with product reason)

- **Saved albums / saved shows** (`user-library-read` already covers albums; shows
  need separate handling). Park: album-oriented taste is marginal for v0 and shows
  are out of music-commentary scope.
- **Current playback / queue continuity** ("what were you just doing"). Park:
  `user-read-playback-state` is already granted, but turning live device state
  into persistent memory risks feeling invasive and adds little to taste. Use it
  live only (as today), do not persist.
- **Audio features.** Park indefinitely — 403 in Dev Mode, unreliable for a
  released app.
- Anything multi-source, account-based, or write-scoped — out per HARD NO-GO.

---

## 5. RECOMMENDATION — Candidate New OAuth Scopes Beyond Day-One

Day-one scopes (`user-library-read`, `user-follow-read`) are boss-approved; their
consent copy is below. Everything past those is a recommendation requiring a
product reason and acceptable consent burden.

### Day-one (approved) — connect-time consent copy

| Scope | Benefit | Risk | Connect-time consent copy |
|---|---|---|---|
| `user-library-read` | Durable "what you keep" taste signal; stronger than one playlist | Low — read-only; can feel personal | "**Your saved music** — Resonova reads the tracks in your library to learn the artists and styles you keep coming back to. It never adds, removes, or changes anything." |
| `user-follow-read` | Explicit artist affinity beyond recent plays | Low — read-only | "**Artists you follow** — Resonova sees who you follow to understand your favourite artists. Read-only; your follows are never changed." |

Implementation note: Spotify shows scopes on its own consent screen, but Resonova
should also surface this copy on its own connect screen so the user understands
*why* before the redirect (and can later see it in the Memory panel, §8).

### Candidate additional scopes (NOT approved — for boss decision)

| Scope | Benefit | Risk / cost | Recommendation |
|---|---|---|---|
| `user-read-currently-playing` | Narrower than the already-granted `user-read-playback-state`; "continue from what you were listening to" | Extra consent line for marginal taste value; redundant with existing playback scope | **Do not add.** Existing `user-read-playback-state` already covers live needs; neither should be persisted. |
| (saved albums via existing `user-library-read`) | Album-oriented taste | Adds fetch + summarize cost, low marginal value | Park; revisit if album commentary becomes a feature. |
| Any `*-modify` write scope | — | Modifies the user's library/playlists | **HARD NO-GO.** Never request. |

Net recommendation: ship exactly the two approved read scopes. Do not expand the
consent burden further for v0. Separately, consider **removing** `user-read-email`
(§10) since the memory layer does not need it and the brief forbids persisting email.

---

## 6. RECOMMENDATION — Feedback Model (explicit overrides inferred)

### Capture (keep it tiny)

- **Episode-level**: thumbs up / thumbs down on a finished cast.
- **Segment-level**: thumbs up / down on a single track-commentary segment
  (the player already tracks `currentItem` and per-track indices in
  `player.js`, so attaching a segment id is cheap).
- **Quick tags** (multi-select, no free-text required): `too long`,
  `too shallow`, `too generic`, `wrong vibe`, `good story`, `good analysis`.
- **Optional** one-line free-text note.

Start with this fixed taxonomy; do not build a rating system.

### Storage

- Raw events → `generated/profile/feedback.jsonl` (append-only, one JSON/line:
  `{id, episode_id, segment_index|null, verdict, tags[], note?, created_at}`).
- A summarizer folds repeated signals into `profile.json`
  (`commentary_preferences.avoid` / `.loved_patterns` and high-confidence
  `memories`). E.g. three "too long" votes → `avoid: ["long intros"]` with
  `source: feedback, confidence: high`.

### Override rule (the core of the model)

Precedence at generation time, highest wins:
1. `pinned: true` manual/feedback memories and `commentary_preferences` — **absolute**.
2. `source: feedback`, `confidence: high` — overrides inferred Spotify/Last.fm.
3. `source: spotify | lastfm | saved_cast` inferred summaries — default.

Concretely: if Spotify behavior infers "loves long-form ambient" but the user
thumbs-down with `too long`, the feedback-derived `avoid: ["long intros"]`
(higher precedence) wins and is what the prompt sees. Inferred memory is never
deleted by feedback — it is **shadowed** by a higher-precedence preference, so
the override is itself inspectable and reversible.

### Update policy

**Semi-automatic.** Inferred taste summaries update automatically after
generations (cheap, reversible). Feedback-derived preferences are applied
automatically but always shown in the Memory panel as editable/removable, and the
owner can pin or delete any of them. This avoids both "silent opaque learning"
and "the user must curate before it works."

---

## 7. RECOMMENDATION — Prompt Integration (no bloat, no leaks, not invasive)

Integration point is fixed and already exists: the `═══ LISTENER PROFILE ═══`
block in `gemini.py:build_prompt` (`:313-314`). Add **one** compact
`═══ PERSISTENT MEMORY ═══` block built from `profile.json` — do not scatter
profile data across the prompt.

Rules:
- **Hard size cap.** Emit at most ~12-15 short lines total: a handful of
  taste descriptors + the active `commentary_preferences` + up to ~5 highest-value
  `memories`. Select by `pinned` then `confidence` then recency. This keeps the
  existing prompt's token budget and avoids drowning the music research.
- **Steer style, don't narrate the user.** Feed `commentary_preferences`
  (tone/depth/avoid/loved) as *instructions to the hosts*, and taste as *context
  for choosing what's interesting* — NOT as facts to read aloud. Reinforce the
  existing guardrails (`gemini.py:58`, `:134`): the hosts must never say "you
  often listen to…" or recite the profile. The profile makes commentary *better
  targeted*, not *about the listener*.
- **No private leakage.** Only summarized strings reach the prompt. No emails, no
  raw scrobble counts as monologue fodder, no "you saved this on March 3rd."
  Saved-library and followed-artist data become "the listener clearly values X"
  framing, never an inventory recital.
- **Fresh-user fallback** (§ below) — when the profile is empty, omit the block
  entirely so a first-time cast is unchanged from today's behavior.

### Fresh user (only Spotify auth, no Resonova history)

On first authorized generation: build `taste_profile` from the live
`fetch_user_context` + the two new scopes, write `profile.json`, but keep the
prompt block minimal (top artists + obvious styles, no feedback prefs yet). The
user should *see* a profile start to populate in the Memory panel after their
first cast ("Resonova is starting to learn your taste") without any commentary
feeling presumptuous on cast #1.

---

## 8. RECOMMENDATION — Memory Inspect / Edit / Reset / Disable UX

Reuse the Last.fm service-widget pattern (`player.js:761-809`,
`index.html:115`). Add a **Memory** panel in `state-connected`, beside the
Last.fm widget and the library sections.

Controls (all act on `generated/profile/profile.json`):
- **Inspect** — render `taste_profile`, `commentary_preferences`, and `memories`
  as readable rows. Show each memory's `source` + `confidence` so the user sees
  *why* it's there. (Mirror the saved-cast list's inspect-and-act layout in
  `section-episodes`.)
- **Edit** — remove an individual memory or preference (per-row ✕, mirroring the
  episode delete button). Pin a memory (`pinned: true`). Optionally add a manual
  memory (`source: manual`). Hand-editing the JSON file remains supported and is a
  feature, not a fallback — it is the "inspectable" promise.
- **Reset** — "Clear memory" wipes `profile.json` + `feedback.jsonl` back to an
  empty profile (the user keeps saved casts). Confirm before wiping.
- **Disable** — `memory_enabled: false` toggle. When off, generation ignores the
  profile entirely (omits the prompt block) and no new summaries are written;
  existing file is retained until the user resets.

New backend endpoints needed (thin, mirroring the episodes/lastfm routes in
`server.py`): `GET /api/profile`, `PATCH /api/profile` (edit/pin/disable),
`DELETE /api/profile` (reset), `POST /api/feedback`. No new storage tech — flat
files like everything else.

---

## 9. RECOMMENDATION — Implementation Task Breakdown

Sized so a future manager can delegate each as a bounded step. No code here.

1. **Profile store module** (`resonova/profile.py`): load/save/reset of
   `generated/profile/profile.json`, schema from §3, caps + eviction. Mirror
   `variety.py`/`episodes.py` style. Pure functions, unit-testable.
2. **Summarizers**: (a) Spotify-context → taste summary from existing
   `fetch_user_context` output; (b) Last.fm → taste summary; (c) saved-cast
   history → patterns; (d) feedback events → `commentary_preferences`/memories.
   Each is small and independently testable.
3. **Two new Spotify fetchers** in `spotify.py`: `fetch_saved_tracks()`
   (`/me/tracks`, paginated, capped) and `fetch_followed_artists()`
   (`/me/following?type=artist`, cursor-paginated). Add the two scopes to
   `config.py:spotify_scopes`. Degrade gracefully on 403/401 like
   `fetch_audio_features` already does.
4. **Profile write hook** in `server.py:_run_generation`: after a successful
   `save_episode` (near `:519`), update the profile (only if `memory_enabled`).
   Must not block or fail the generation if summarization errors.
5. **Prompt block** in `gemini.py:build_prompt`: add the capped
   `═══ PERSISTENT MEMORY ═══` section per §7, gated on a non-empty profile.
6. **Feedback channel**: `generated/profile/feedback.jsonl` writer + summarizer +
   `POST /api/feedback`. Frontend thumbs/tags on episode and segment in
   `player.js` / `index.html`.
7. **Memory panel UX**: `GET/PATCH/DELETE /api/profile` endpoints + the Memory
   widget in `state-connected` (inspect/edit/pin/reset/disable).
8. **Connect-time consent copy**: surface the §5 day-one scope copy on the
   Resonova connect screen (`state-landing`) and the Memory panel.
9. **Tests**: profile store round-trip + cap eviction; summarizer determinism;
   feedback override precedence (§6); fresh-user empty-profile → unchanged prompt.
10. **Honesty/copy pass**: once memory exists, update any "no memory" disclaimers
    (Phase 2 honesty bundle) to reflect the real behavior.

Suggested first slice for a minimal vertical demo: tasks 1, 2(a), 4, 5, 7
(inspect+reset only) — proves "it remembers me and I can clear it" with zero new
scopes. Add tasks 3 (day-one scopes) and 6 (feedback) as the second slice.

---

## 10. Open Boss Decisions

1. **`user-read-email` removal.** The memory layer does not need it and the brief
   forbids persisting email. Should we drop `user-read-email` (and possibly
   `user-read-private`) from the scope list to reduce consent burden, or keep for
   a future account reason? (Recommend: drop `user-read-email` for v0.)
2. **Profile file location.** Recommend `generated/profile/profile.json`. Confirm
   this (vs `data/profile/…`) and confirm it should be git-ignored.
3. **Feedback granularity for v0.** Episode-only, or episode + segment? (Recommend
   both, but segment can be deferred to slice two.)
4. **Update policy.** Confirm semi-automatic (auto-summarize + always editable) vs
   manual-only. (Recommend semi-automatic.)
5. **Raw feedback retention window.** Confirm a rolling cap (e.g. ~200 events /
   90 days) before relying solely on the summary.
6. **Fresh-user commentary.** Is it acceptable for cast #1 to use a thin live
   profile, or must memory only influence cast #2 onward? (Recommend thin profile
   from cast #1, but no listener-narration ever.)
7. **Spotify quota/policy for release.** NOT verified here. Before a multi-user
   release, confirm whether the added read scopes affect Spotify's
   extended-quota/policy review. This is a release-stage gate, flagged not resolved.

---

## Appendix — Verification Status Summary

VERIFIED (read from code): all of §1 file:line claims, the 9 current scopes, the
single scope source, the existing storage stores, the prompt injection point, the
existing listener-data guardrails, and the frontend surfaces.

VERIFIED (official Spotify docs, fetched 2026-06-21): scope strings + endpoint
paths + pagination for `user-library-read`/`GET /me/tracks` and
`user-follow-read`/`GET /me/following`; write scopes confirmed out of scope; no
relevant read scope deprecated.

COULD NOT VERIFY: current Spotify platform *policy/quota-mode* constraints for a
released multi-user app (extended-quota review). Flagged as open decision #7, not
asserted. All of §§3-9 are design RECOMMENDATIONS pending boss/chef approval, not
validated behavior.
