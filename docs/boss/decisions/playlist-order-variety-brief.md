# Playlist Order Variety Brief

## Customer Issue

When a generated cast always follows the fixed Spotify playlist order, repeat listening becomes rigid. After a few plays, the owner hears the same sequence and the cast feels stale.

## Product Decision

Playlist-generated casts should vary the episode order by default.

Explicit pasted track lists should preserve user order, because manually pasted order is a stronger intentional signal than a playlist's stored order.

## Implementation Rule

- For Spotify playlist input: shuffle the fetched playlist tracks, then apply `MAX_TRACKS`.
- For direct track-list input: preserve pasted order and apply `MAX_TRACKS`.
- Gemini script caching must be order-sensitive because per-track commentary references what previously played and what is coming next.

## Acceptance

- Re-generating from the same playlist can produce a different track order.
- The generated commentary and playback queue use the same order.
- Saved episode replay remains deterministic for that saved episode.
- Existing explicit track-list workflows remain unchanged.

