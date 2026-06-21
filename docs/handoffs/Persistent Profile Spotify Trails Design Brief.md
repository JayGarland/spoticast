# Persistent Profile / Spotify Trails / Feedback Design Brief

Date: 2026-06-21
Owner: Chef
Status: Ready to route

Boss decision (2026-06-21): data appetite is **data-rich now**. Promote Spotify saved library (`user-library-read`) and followed artists (`user-follow-read`) to day-one scope, with clear connect-time consent copy. Consent, inspectability, and reset controls still apply.

## Purpose

Design the first real Resonova memory layer.

The product baseline is not just "generate commentary for one playlist." Resonova should become a personal AI radio companion that understands the listener better the more they use it.

This is a design task only. Do not implement code yet.

## Product Baseline

For a new test user, the intended direction is:

```text
open Resonova in the browser -> connect Spotify Premium -> authorize Resonova -> start listening
```

After that, Resonova should gradually build an inspectable profile from:

- Spotify-authorized listening trails
- generated/saved casts
- repeated playlist sessions
- explicit feedback
- optional Last.fm history, if connected

The result should be better commentary over time: more personal context, better host framing, better taste continuity, fewer repeated generic observations, and more useful callbacks to the listener's history.

## Current Repo Facts To Verify

Inspect these files before designing:

- `resonova/config.py`
- `resonova/api/spotify.py`
- `resonova/api/lastfm.py`
- `resonova/server.py`
- `resonova/episodes.py`
- `resonova/variety.py`
- `resonova/web/index.html`
- `resonova/web/player.js`
- `docs/strategy/persistent-profile-feedback-brief.md`
- `docs/strategy/release-access-and-memory-positioning-brief.md`
- `docs/strategy/v0.1-roadmap.md`

Current Spotify scopes the app already requests (source of truth: `resonova/config.py`, `spotify_scopes`). The manager must re-verify against the code, not this list:

- `user-read-recently-played` - recent track URIs, recent playlist context where available
- `user-top-read` - top tracks/artists across short, medium, long term
- `playlist-read-private`
- `playlist-read-collaborative`
- `streaming` - Web Playback SDK playback
- `user-modify-playback-state` - playback control (a write/control scope already shipped)
- `user-read-playback-state`
- `user-read-email`
- `user-read-private`

Note: an earlier draft of this brief labeled an incomplete list "Verified" and omitted `streaming` and `user-modify-playback-state`. The app already ships one write/control scope, so the privacy framing below ("write scopes parked") refers to *library/playlist-modifying* write scopes, not playback control.

Verified current product memory/storage pieces:

- saved cast episodes exist
- episode queue replay exists
- per-playlist variety memory exists
- optional Last.fm enrichment can add play counts, loved tracks, fan-era context, top artists, and artist profiles

## Candidate Additional APIs / Signals To Evaluate

Evaluate more personal-data APIs, but do not assume all should be added.

Day-one scope (boss-approved 2026-06-21, data-rich):

- Spotify saved tracks / library signal
  - Scope: `user-library-read`
  - Product value: durable "what the user keeps" taste signal, stronger than one playlist.
- Spotify followed artists
  - Scope: `user-follow-read`
  - Product value: explicit artist affinity beyond recent behavior.

Still evaluate (recommend only with product reason + consent copy):

- Spotify saved albums / saved shows, if relevant to music commentary
  - Product value: album-oriented taste, long-form listening, podcast/show context if Resonova later supports it.
- Spotify current playback / queue / playback state
  - Product value: session context, current listening mode, device state, possible "what were you just doing?" continuity.
- Existing saved-cast and replay history
  - Product value: Resonova-owned memory that does not need extra third-party permissions.
- Feedback events
  - Product value: direct correction of host style, depth, vibe, and unwanted patterns.

Lower-priority or parked candidates:

- Write scopes that modify the user's Spotify library or playlists.
- Non-Spotify source expansion.
- Account-system-dependent memory.
- Raw long-term event logging without summary, controls, and retention policy.

## Required Design Questions

Answer these before implementation:

1. What is the smallest useful profile object?
2. Which Spotify signals should be used on day one, and which should be parked?
3. Which new OAuth scopes are worth asking for, and how should the consent copy explain them?
4. What raw data should never be persisted?
5. What should be summarized into profile memory?
6. How long should raw trails or generated traces be retained, if at all?
7. How should the user inspect, edit, reset, or disable memory?
8. How should explicit feedback override inferred Spotify behavior?
9. How should prompts use memory without bloating, leaking private details, or making commentary weirdly invasive?
10. What should happen for a fresh user with only Spotify authorization and no prior Resonova history?

## Suggested Minimal Data Model

Design, revise, or reject this shape:

```json
{
  "profile_version": 1,
  "updated_at": "ISO-8601",
  "source_summary": {
    "spotify": {
      "connected": true,
      "scopes_used": [],
      "last_refreshed_at": "ISO-8601"
    },
    "lastfm": {
      "connected": false,
      "last_refreshed_at": null
    },
    "resonova": {
      "saved_cast_count": 0,
      "feedback_count": 0
    }
  },
  "taste_profile": {
    "top_artists": [],
    "recurring_genres_or_styles": [],
    "favorite_eras": [],
    "recent_shifts": [],
    "playlist_patterns": [],
    "listening_contexts": []
  },
  "commentary_preferences": {
    "tone": [],
    "depth": "balanced",
    "avoid": [],
    "loved_patterns": []
  },
  "memories": [
    {
      "id": "mem_...",
      "text": "Short inspectable memory sentence.",
      "source": "spotify|lastfm|feedback|saved_cast|manual",
      "confidence": "low|medium|high",
      "created_at": "ISO-8601",
      "last_used_at": null
    }
  ]
}
```

Keep the first version small. The profile should be understandable to a human, not a hidden recommender blob.

## Consent And Privacy Rules

- Do not request more Spotify scopes just because they are available.
- Each new scope needs a product reason and a user-facing explanation.
- Prefer summarized memory over raw permanent logs.
- Do not persist Spotify tokens, API keys, or secrets in profile files.
- Do not persist the user's email unless there is a release-approved account reason.
- Make memory inspectable, editable, resettable, and disableable.
- Feedback should be allowed to correct or override inferred memory.

## Spotify Documentation To Verify

Use official Spotify docs before recommending new scopes or endpoints:

- Scopes: https://developer.spotify.com/documentation/web-api/concepts/scopes
- Top items: https://developer.spotify.com/documentation/web-api/reference/get-users-top-artists-and-tracks
- Recently played: https://developer.spotify.com/documentation/web-api/reference/get-recently-played
- Saved tracks: https://developer.spotify.com/documentation/web-api/reference/get-users-saved-tracks
- Followed artists: https://developer.spotify.com/documentation/web-api/reference/get-followed
- Current user playlists: https://developer.spotify.com/documentation/web-api/reference/get-a-list-of-current-users-playlists
- Playback state: https://developer.spotify.com/documentation/web-api/reference/get-information-about-the-users-current-playback

Also verify current Spotify platform policy constraints before release planning.

## Expected Deliverable

Write:

```text
docs/handoffs/Persistent Profile Spotify Trails Design Handoff.md
```

The handoff must include:

- verified current architecture
- current signals already available
- candidate new APIs/scopes with value and risk
- recommended minimal v0 profile schema
- feedback model
- prompt integration approach
- memory inspection/reset UX
- implementation task breakdown
- open boss decisions

Do not implement code.

## Suggested Prompt To Paste Into Manager Agent

```text
Use docs/handoffs/Persistent Profile Spotify Trails Design Brief.md as the parent brief.

Design Resonova's first persistent profile, Spotify trails, and feedback layer.

This is a design/handoff task only. Do not implement code.

Resonova's product baseline is that the companion should understand the listener better the more they use it. For v0.1, the target entry path is browser-based direct use: open Resonova, connect Spotify Premium, authorize, generate/listen.

Re-verify scopes directly from resonova/config.py (do not trust any inline list). Inspect the current repo and verify:
- existing Spotify scopes and API calls
- existing Last.fm enrichment
- saved cast storage
- variety memory
- generation prompt context
- frontend surfaces where memory/feedback controls could live

Day-one data appetite (boss-approved, data-rich): add user-library-read (saved tracks) and user-follow-read (followed artists) to the design, with clear connect-time consent copy for each. Any scope beyond those still needs a product reason and acceptable consent burden.

Produce docs/handoffs/Persistent Profile Spotify Trails Design Handoff.md with:
- current architecture facts
- recommended minimal profile schema
- recommended Spotify/Last.fm/Resonova-owned signals
- candidate new OAuth scopes with benefit/risk
- feedback model
- inspect/edit/reset memory UX
- prompt integration plan
- implementation tasks
- open boss decisions

Do not approve hosting, public accounts, billing, subscriptions, multi-source expansion, or code implementation.
```
