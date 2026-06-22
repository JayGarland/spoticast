# Handoff — Music Memory Layer Selection for Personal Cast App

## Context

I have a working MVP of a small Spotify-based “personal cast” app. Current version can run locally with Spotify app credentials, Gemini key, and a selected playlist. The MVP is currently closer to a one-shot customized cast generated from a playlist.

The next product question is whether the app should remain playlist-based, or grow into a personalized cast/radio that improves over time based on the user’s listening history and behavior.

## Core Problem

Spotify is the best active music source, but Spotify Web API alone is not enough for deep long-term memory.

Spotify can provide useful signals such as:

* playlist content
* saved tracks
* current playback
* recently played tracks
* top artists/tracks over broad time ranges

But it does not directly provide a complete raw long-term listening timeline through the normal API. Therefore, insights like:

* “you listened to this artist 86 times over 8 months”
* “you return to this genre every winter”
* “your night-driving taste changed over time”

require a separate memory layer.

## Options to Discuss

### Option A — Spotify API only

Use only Spotify data exposed by the official API.

Pros:

* simplest MVP path
* no extra user account dependency
* direct integration with current app
* good enough for playlist-based or one-shot generation

Cons:

* weak long-term personalization
* no exact full listening history
* difficult to build seasonal or behavioral insights
* app may stay as a “playlist summarizer/cast generator” rather than a growing personal radio

Best for:

* MVP
* prototype
* fast demo
* one-user local version

### Option B — Spotify API + Our Own Database

Use Spotify as the active source, but store listening events over time in our own backend database.

Typical flow:

Spotify API → recent/current listening data → our database → analysis layer → personalized cast generation

Pros:

* best long-term product direction
* full control over data model
* enables real personalization over time
* can support context labels such as night, driving, studying, walking, etc.
* avoids depending completely on Last.fm or ListenBrainz

Cons:

* requires backend persistence
* requires scheduled polling or user-triggered sync
* no deep historical data unless we import user privacy export or external scrobbling history
* more engineering work

Best for:

* serious product direction
* personalized cast/radio that grows with usage
* building our own product intelligence

### Option C — Last.fm Integration

Use Last.fm as an external scrobbling/history source.

Pros:

* mature listening-history platform
* already designed around scrobbling
* can give historical listening data if the user already uses Last.fm
* useful shortcut for music memory

Cons:

* extra external account
* not every user has existing Last.fm history
* dependency on third-party API and data quality
* may not map perfectly to Spotify IDs

Best for:

* fast access to existing user music history
* users who already scrobble
* optional import/integration layer

### Option D — ListenBrainz Integration

Use ListenBrainz as an open-source/open-data alternative to Last.fm.

Pros:

* open ecosystem
* API-oriented
* connected to MusicBrainz metadata
* good fit if we value transparency and data ownership

Cons:

* less mainstream than Last.fm
* many users may not already have history there
* still adds external account/integration complexity

Best for:

* open-source-friendly direction
* metadata-rich experiments
* optional alternative to Last.fm

### Option E — Study YourSpotify

YourSpotify is not necessarily something to integrate directly. It is more useful as a reference implementation.

It shows a practical architecture for:

* connecting to Spotify
* polling listening activity
* storing data in a database
* displaying listening statistics

Pros:

* directly relevant technical reference
* validates the “Spotify + own database” direction
* can help us design the memory layer faster

Cons:

* it is analytics/dashboard-oriented, not cast-generation-oriented
* we should not just clone the product
* needs adaptation to our own goal

Best for:

* technical architecture reference
* database schema inspiration
* polling/sync strategy inspiration

## Recommended Direction

My recommendation is:

1. Keep the MVP Spotify-only for now.
2. For the next serious version, choose Spotify API + our own database as the main architecture.
3. Use YourSpotify as a technical reference.
4. Treat Last.fm and ListenBrainz as optional external import/scrobbling integrations, not as the core product dependency.

The reason is that the app’s real goal is not just music statistics. The goal is a personalized cast/radio that grows over time. For that, we need our own memory layer eventually.

## Proposed Decision

For now, decide between two paths:

### Lightweight Path

Continue with Spotify-only.

Use playlist + top tracks/artists + recent plays to generate better one-shot casts.

Good if the goal is to keep the app small and local.

### Product-Growth Path

Add a memory database.

Start storing listening events from now on, then later generate casts from long-term behavioral patterns.

Good if the goal is to make the app evolve into a personal radio/cast assistant.

## Main Question for Discussion

Should this app stay as a simple playlist-based AI cast generator, or should we design it as a long-term personal music memory system?

My preferred answer: keep the current MVP simple, but design the next version around a memory layer.
