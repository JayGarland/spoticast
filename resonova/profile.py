"""Persistent listener profile — load/save/reset of generated/profile/profile.json.

Schema version: 1  (§3 of the Persistent Profile design handoff)

Caps: memories ≤ 40 (pinned + high-confidence + newest kept; lowest-value evicted),
      each list field in taste_profile ≤ 20 items.

No secrets, tokens, email addresses, or raw Spotify/Last.fm payloads are persisted.
Only summarised strings reach this file and, from there, the prompt.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_PROFILE_DIR = Path("generated") / "profile"
_PROFILE_PATH = _PROFILE_DIR / "profile.json"
_OWNER_PATH = _PROFILE_DIR / "owner_id"
_PROFILE_VERSION = 1

# Size caps — mirrors the variety.py _MAX_RECENT precedent
_MAX_MEMORIES = 40
_MAX_LIST_ITEMS = 20

# Confidence score: lower number = higher value (kept first when evicting)
_CONFIDENCE_RANK: dict[str, int] = {"high": 0, "medium": 1, "low": 2}


# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------

def _empty_profile() -> dict:
    """Return a valid, fully-populated empty profile skeleton."""
    return {
        "profile_version": _PROFILE_VERSION,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "memory_enabled": True,
        "sources": {
            "spotify": {
                "connected": False,
                "scopes_used": [],
                "last_refreshed_at": None,
            },
            "lastfm": {"connected": False, "last_refreshed_at": None},
            "resonova": {"saved_cast_count": 0, "feedback_count": 0},
        },
        "taste_profile": {
            "top_artists": [],
            "recurring_styles": [],
            "favorite_eras": [],
            "recent_shifts": [],
            "playlist_patterns": [],
            "saved_library_artists": [],
            "followed_artists": [],
            "replay_affinity": [],
        },
        "commentary_preferences": {
            "tone": [],
            "depth": "balanced",
            "avoid": [],
            "loved_patterns": [],
        },
        "memories": [],
    }


# ---------------------------------------------------------------------------
# Load / save / reset
# ---------------------------------------------------------------------------

def load_profile() -> dict:
    """Load the profile from disk; return a fresh empty profile on any error."""
    if not _PROFILE_PATH.exists():
        return _empty_profile()
    try:
        data = json.loads(_PROFILE_PATH.read_text())
        # Forward-compat: fill any missing top-level keys added in later versions
        empty = _empty_profile()
        for key in ("taste_profile", "commentary_preferences", "memories", "sources"):
            if key not in data:
                data[key] = empty[key]
        # Forward-compat: fill new taste_profile sub-keys (Slice Two)
        for sub in ("saved_library_artists", "followed_artists"):
            if sub not in data.get("taste_profile", {}):
                data["taste_profile"][sub] = []
        # Forward-compat: replay affinity trail field
        if "replay_affinity" not in data.get("taste_profile", {}):
            data["taste_profile"]["replay_affinity"] = []
        return data
    except Exception:
        return _empty_profile()


def save_profile(profile: dict) -> None:
    """Enforce size caps, stamp updated_at, and persist profile to disk."""
    profile = _enforce_caps(profile)
    profile["updated_at"] = datetime.now(timezone.utc).isoformat()
    _PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    _PROFILE_PATH.write_text(json.dumps(profile, indent=2))


def reset_profile() -> dict:
    """Wipe profile to an empty skeleton; saved cast episodes are untouched.

    Also deletes the feedback file so cleared preferences do not resurrect.
    """
    empty = _empty_profile()
    _PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    _PROFILE_PATH.write_text(json.dumps(empty, indent=2))
    if _FEEDBACK_PATH.exists():
        _FEEDBACK_PATH.unlink()
    return empty


def get_owner_id() -> str | None:
    """Return the Spotify user id that owns this instance, or None if unclaimed."""
    if _OWNER_PATH.exists():
        return _OWNER_PATH.read_text(encoding="utf-8").strip() or None
    return None


def claim_or_check_owner(user_id: str | None) -> bool:
    """Single-user guard. The first valid connect claims ownership of this instance.

    Returns True if *user_id* is (or just became) the owner; False for any other
    account or when the id is unknown. Used to stop a second Spotify account's data
    from merging into the owner's profile (cross-user bleed). Not cleared by
    reset_profile — clearing memory does not unlock the instance.
    """
    if not user_id:
        return False
    owner = get_owner_id()
    if owner is None:
        _PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        _OWNER_PATH.write_text(user_id, encoding="utf-8")
        return True
    return owner == user_id


# ---------------------------------------------------------------------------
# Cap enforcement + eviction
# ---------------------------------------------------------------------------

def _memory_value(m: dict) -> tuple:
    """Sort key for descending value order: pinned > high-confidence > newest."""
    pinned = 1 if m.get("pinned") else 0                             # higher = better
    conf = 2 - _CONFIDENCE_RANK.get(m.get("confidence", "low"), 2)  # high=2, low=0
    ts = m.get("created_at", "")                                     # newer ISO > older
    return (pinned, conf, ts)


def _enforce_caps(profile: dict) -> dict:
    """Apply size caps in-place.

    Taste-profile list fields are truncated to _MAX_LIST_ITEMS.
    Memories above _MAX_MEMORIES are evicted by lowest value first
    (unpinned, then low-confidence, then oldest).
    """
    taste = profile.get("taste_profile", {})
    for field in ("top_artists", "recurring_styles", "favorite_eras",
                  "recent_shifts", "playlist_patterns",
                  "saved_library_artists", "followed_artists", "replay_affinity"):
        if isinstance(taste.get(field), list):
            taste[field] = taste[field][:_MAX_LIST_ITEMS]

    memories: list[dict] = profile.get("memories", [])
    if len(memories) > _MAX_MEMORIES:
        # Sort highest-value first, keep the top _MAX_MEMORIES
        memories = sorted(memories, key=_memory_value, reverse=True)[:_MAX_MEMORIES]
        profile["memories"] = memories

    return profile


# ---------------------------------------------------------------------------
# Context summariser (Slice One: Spotify context + Last.fm enrichment only)
# ---------------------------------------------------------------------------

def summarize_context(context: dict[str, Any], profile: dict | None = None,
                      memory_enabled: bool = True) -> dict:
    """Update the profile from an already-fetched generation context.

    Uses only data already in *context* — zero new Spotify fetches or scopes.
    Call after build_playlist_context() (and optionally enrich_context()).

    When *memory_enabled* is False, TRAIL fields (recent_shifts, playlist_patterns)
    are not written.  DURABLE fields are always updated.

    Returns the updated profile dict (caller must call save_profile to persist).
    """
    if profile is None:
        profile = load_profile()

    listener = context.get("listener_profile", {})
    artist_profiles: dict[str, dict] = context.get("artist_profiles", {})
    lastfm_user: dict = context.get("lastfm_user", {})

    taste = profile.setdefault("taste_profile", {
        "top_artists": [], "recurring_styles": [], "favorite_eras": [],
        "recent_shifts": [], "playlist_patterns": [],
    })
    sources = profile.setdefault("sources", {
        "spotify": {"connected": False, "scopes_used": [], "last_refreshed_at": None},
        "lastfm": {"connected": False, "last_refreshed_at": None},
        "resonova": {"saved_cast_count": 0, "feedback_count": 0},
    })

    now_iso = datetime.now(timezone.utc).isoformat()

    # ── Top artists from Spotify (build_playlist_context already computed them) ──
    spotify_top = list(listener.get("top_artists_all_time", []))
    if spotify_top:
        existing = taste.get("top_artists") or []
        # New names first, then keep existing that aren't duplicated, dedup, cap
        merged = list(dict.fromkeys(spotify_top + [a for a in existing if a not in spotify_top]))
        taste["top_artists"] = merged[:_MAX_LIST_ITEMS]

    # ── Recurring styles from Last.fm artist tags ─────────────────────────────
    tag_counts: dict[str, int] = {}
    for ap in artist_profiles.values():
        for tag in (ap.get("tags") or [])[:5]:
            if tag:
                tag_counts[tag.lower()] = tag_counts.get(tag.lower(), 0) + 1
    lastfm_styles: list[str] = []
    if tag_counts:
        lastfm_styles = [t for t, _ in sorted(tag_counts.items(), key=lambda x: -x[1])]

    # ── Recurring styles from Spotify genres ──────────────────────────────────
    spotify_genres: list[str] = list(listener.get("spotify_genres") or [])

    # Merge: Last.fm tags first (preserving frequency order), then Spotify genres,
    # de-duplicated (preserving first occurrence order), capped.
    existing_styles = taste.get("recurring_styles") or []
    all_new = list(dict.fromkeys(lastfm_styles + spotify_genres))
    merged_styles = list(dict.fromkeys(all_new + [s for s in existing_styles if s not in all_new]))
    taste["recurring_styles"] = merged_styles[:_MAX_LIST_ITEMS]

    # ── Source provenance stamps ──────────────────────────────────────────────
    spotify_src = sources.setdefault("spotify", {})
    spotify_src["connected"] = True
    spotify_src["last_refreshed_at"] = now_iso
    spotify_src.setdefault("scopes_used", [])

    if lastfm_user:
        lastfm_src = sources.setdefault("lastfm", {})
        lastfm_src["connected"] = True
        lastfm_src["last_refreshed_at"] = now_iso

    profile["profile_version"] = _PROFILE_VERSION
    return profile


# ---------------------------------------------------------------------------
# Saved-tracks + followed-artists summarizer (Slice Two)
# ---------------------------------------------------------------------------

_RECENT_TRACK_WINDOW = 50  # most-recent N additions = "current state"


def summarize_library(
    saved_tracks: list[dict],
    followed_artists: list[str],
    profile: dict | None = None,
    memory_enabled: bool = True,
) -> dict:
    """Update the profile from saved tracks and followed artists.

    saved_tracks: list of {artist_names: list[str], added_at: str}, NEWEST FIRST.
    followed_artists: list of artist name strings.

    Design rule (boss-directed):
    - The most-recent _RECENT_TRACK_WINDOW tracks signal CURRENT/EVOLVING taste
      → feeds taste_profile.recent_shifts with a concise artist summary.
    - The older remainder represent DURABLE long-term taste
      → feeds taste_profile.saved_library_artists.
    - followed_artists → taste_profile.followed_artists (explicit affinity).

    When *memory_enabled* is False, TRAIL fields (recent_shifts) are not written.
    DURABLE fields (saved_library_artists, followed_artists) are always updated.

    Returns the updated profile dict (caller must call save_profile to persist).
    """
    if profile is None:
        profile = load_profile()

    taste = profile.setdefault("taste_profile", {
        "top_artists": [], "recurring_styles": [], "favorite_eras": [],
        "recent_shifts": [], "playlist_patterns": [],
        "saved_library_artists": [], "followed_artists": [],
    })
    sources = profile.setdefault("sources", {
        "spotify": {"connected": False, "scopes_used": [], "last_refreshed_at": None},
        "lastfm": {"connected": False, "last_refreshed_at": None},
        "resonova": {"saved_cast_count": 0, "feedback_count": 0},
    })

    now_iso = datetime.now(timezone.utc).isoformat()

    if saved_tracks:
        recent_tracks = saved_tracks[:_RECENT_TRACK_WINDOW]
        older_tracks = saved_tracks[_RECENT_TRACK_WINDOW:]

        # TRAIL: recent_shifts only written when memory_enabled is True
        if memory_enabled:
            recent_artists: list[str] = []
            seen: set[str] = set()
            for t in recent_tracks:
                for name in t.get("artist_names", []):
                    if name and name not in seen:
                        seen.add(name)
                        recent_artists.append(name)

            if recent_artists:
                existing_shifts = taste.get("recent_shifts") or []
                merged_shifts = list(dict.fromkeys(
                    recent_artists + [a for a in existing_shifts if a not in recent_artists]
                ))
                taste["recent_shifts"] = merged_shifts[:_MAX_LIST_ITEMS]

        # Older tracks → saved_library_artists (durable long-term taste)
        durable_artists: list[str] = []
        seen_d: set[str] = set()
        for t in older_tracks:
            for name in t.get("artist_names", []):
                if name and name not in seen_d:
                    seen_d.add(name)
                    durable_artists.append(name)

        if durable_artists:
            existing_lib = taste.get("saved_library_artists") or []
            merged_lib = list(dict.fromkeys(
                durable_artists + [a for a in existing_lib if a not in durable_artists]
            ))
            taste["saved_library_artists"] = merged_lib[:_MAX_LIST_ITEMS]

    # Followed artists → explicit affinity
    if followed_artists:
        existing_followed = taste.get("followed_artists") or []
        merged_followed = list(dict.fromkeys(
            followed_artists + [a for a in existing_followed if a not in followed_artists]
        ))
        taste["followed_artists"] = merged_followed[:_MAX_LIST_ITEMS]

    # Update Spotify source stamp with new scopes
    spotify_src = sources.setdefault("spotify", {})
    spotify_src["connected"] = True
    spotify_src["last_refreshed_at"] = now_iso
    used = set(spotify_src.get("scopes_used") or [])
    if saved_tracks is not None:
        used.add("user-library-read")
    if followed_artists is not None:
        used.add("user-follow-read")
    spotify_src["scopes_used"] = sorted(used)

    profile["profile_version"] = _PROFILE_VERSION
    return profile


# ---------------------------------------------------------------------------
# Saved-cast-history summarizer (Slice Two, Section D)
# ---------------------------------------------------------------------------

def summarize_saved_casts(profile: dict | None = None,
                          memory_enabled: bool = True) -> dict:
    """Derive patterns from the existing saved episode library.

    Reads episodes via episodes.list_episodes() — zero new scopes or API calls.
    - Sets sources.resonova.saved_cast_count to the real count (always).
    - Derives playlist_patterns from episode naming patterns (TRAIL — only when
      *memory_enabled* is True).

    Returns the updated profile dict (caller must call save_profile to persist).
    """
    if profile is None:
        profile = load_profile()

    from resonova import episodes as episodes_store

    taste = profile.setdefault("taste_profile", {
        "top_artists": [], "recurring_styles": [], "favorite_eras": [],
        "recent_shifts": [], "playlist_patterns": [],
        "saved_library_artists": [], "followed_artists": [], "replay_affinity": [],
    })
    sources = profile.setdefault("sources", {
        "spotify": {"connected": False, "scopes_used": [], "last_refreshed_at": None},
        "lastfm": {"connected": False, "last_refreshed_at": None},
        "resonova": {"saved_cast_count": 0, "feedback_count": 0},
    })

    eps = episodes_store.list_episodes()
    resonova_src = sources.setdefault("resonova", {"saved_cast_count": 0, "feedback_count": 0})
    resonova_src["saved_cast_count"] = len(eps)

    if eps:
        # Derive light patterns: playlist names that appear more than once
        from collections import Counter
        playlist_name_counts: Counter = Counter()
        for ep in eps:
            pl_name = ep.get("playlist_name", "").strip()
            if pl_name and pl_name not in ("Custom tracks", ""):
                playlist_name_counts[pl_name] += 1

        if memory_enabled:
            patterns: list[str] = []
            for name, count in playlist_name_counts.most_common(5):
                if count >= 2:
                    patterns.append(f"frequently casts from '{name}'")
                elif count == 1:
                    patterns.append(f"cast from '{name}'")

            if patterns:
                existing_patterns = taste.get("playlist_patterns") or []
                # Remove stale cast-derived patterns before re-deriving
                kept = [p for p in existing_patterns if not p.startswith(("frequently casts from", "cast from"))]
                merged = list(dict.fromkeys(patterns + kept))
                taste["playlist_patterns"] = merged[:_MAX_LIST_ITEMS]

            # Replay-derived playlist affinity (TRAIL — memory-on only).
            # Weight replayed playlists higher than merely generated ones.
            replay_by_playlist: dict[str, int] = {}
            for ep in eps:
                rc = ep.get("replay_count", 0)
                if rc > 0:
                    pl_name = ep.get("playlist_name", "").strip()
                    if pl_name and pl_name not in ("Custom tracks", ""):
                        replay_by_playlist[pl_name] = replay_by_playlist.get(pl_name, 0) + rc

            affinity_lines: list[str] = []
            for pl_name, total_replays in sorted(replay_by_playlist.items(), key=lambda x: -x[1])[:5]:
                affinity_lines.append(f"strong affinity with '{pl_name}' style")

            if affinity_lines:
                existing_affinity = taste.get("replay_affinity") or []
                kept_affinity = [a for a in existing_affinity
                                 if not a.startswith("strong affinity with")]
                merged_affinity = list(dict.fromkeys(affinity_lines + kept_affinity))
                taste["replay_affinity"] = merged_affinity[:_MAX_LIST_ITEMS]
            else:
                # Clear stale replay affinity if no replays exist
                existing_affinity = taste.get("replay_affinity") or []
                taste["replay_affinity"] = [a for a in existing_affinity
                                             if not a.startswith("strong affinity with")]

    profile["profile_version"] = _PROFILE_VERSION
    return profile


# ---------------------------------------------------------------------------
# Feedback channel (Slice Two, Section E)
# ---------------------------------------------------------------------------

_FEEDBACK_PATH = _PROFILE_DIR / "feedback.jsonl"

FEEDBACK_TAGS = frozenset([
    "too long", "too shallow", "too generic",
    "wrong vibe", "good story", "good analysis",
])

_FEEDBACK_FOLD_THRESHOLD = 2  # occurrences before folding into high-confidence preference


def append_feedback(event: dict) -> None:
    """Append a feedback event to feedback.jsonl (append-only)."""
    _PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    with _FEEDBACK_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


def _load_feedback() -> list[dict]:
    """Load all feedback events; return [] on any error."""
    if not _FEEDBACK_PATH.exists():
        return []
    events: list[dict] = []
    try:
        for line in _FEEDBACK_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except Exception:
                    pass
    except Exception:
        pass
    return events


def fold_feedback_into_profile(profile: dict | None = None) -> dict:
    """Read feedback.jsonl and fold repeated signals into commentary_preferences.

    Override precedence: pinned > feedback(high) > inferred(spotify/lastfm/saved_cast).
    Inferred memories are SHADOWED (never deleted) by higher-precedence feedback prefs.

    Returns the updated profile dict (caller must call save_profile to persist).
    """
    if profile is None:
        profile = load_profile()

    events = _load_feedback()
    if not events:
        return profile

    prefs = profile.setdefault("commentary_preferences", {
        "tone": [], "depth": "balanced", "avoid": [], "loved_patterns": [],
    })
    sources = profile.setdefault("sources", {
        "spotify": {"connected": False, "scopes_used": [], "last_refreshed_at": None},
        "lastfm": {"connected": False, "last_refreshed_at": None},
        "resonova": {"saved_cast_count": 0, "feedback_count": 0},
    })

    resonova_src = sources.setdefault("resonova", {"saved_cast_count": 0, "feedback_count": 0})
    resonova_src["feedback_count"] = len(events)

    # Tally tags across all events
    from collections import Counter
    down_tag_counts: Counter = Counter()
    up_tag_counts: Counter = Counter()
    for ev in events:
        verdict = ev.get("verdict", "")
        for tag in ev.get("tags", []):
            if tag in FEEDBACK_TAGS:
                if verdict == "down":
                    down_tag_counts[tag] += 1
                elif verdict == "up":
                    up_tag_counts[tag] += 1

    # Map down-tags to avoid patterns
    _TAG_TO_AVOID = {
        "too long": "long intros",
        "too shallow": "shallow analysis",
        "too generic": "generic commentary",
        "wrong vibe": "wrong-vibe segments",
    }
    _TAG_TO_LOVED = {
        "good story": "storytelling segments",
        "good analysis": "deep analysis",
    }

    now_iso = datetime.now(timezone.utc).isoformat()
    memories: list[dict] = profile.setdefault("memories", [])
    existing_mem_texts = {m["text"] for m in memories}

    avoid = list(prefs.get("avoid") or [])
    loved = list(prefs.get("loved_patterns") or [])

    for tag, pattern in _TAG_TO_AVOID.items():
        count = down_tag_counts[tag]
        if count >= _FEEDBACK_FOLD_THRESHOLD:
            if pattern not in avoid:
                avoid.append(pattern)
            # Add a high-confidence memory (feedback source)
            mem_text = f"Listener dislikes: {pattern} (from feedback)"
            if mem_text not in existing_mem_texts:
                existing_mem_texts.add(mem_text)
                memories.append({
                    "id": f"feedback_{tag.replace(' ', '_')}",
                    "text": mem_text,
                    "source": "feedback",
                    "confidence": "high",
                    "pinned": False,
                    "created_at": now_iso,
                })

    for tag, pattern in _TAG_TO_LOVED.items():
        count = up_tag_counts[tag]
        if count >= _FEEDBACK_FOLD_THRESHOLD:
            if pattern not in loved:
                loved.append(pattern)
            mem_text = f"Listener loves: {pattern} (from feedback)"
            if mem_text not in existing_mem_texts:
                existing_mem_texts.add(mem_text)
                memories.append({
                    "id": f"feedback_{tag.replace(' ', '_')}",
                    "text": mem_text,
                    "source": "feedback",
                    "confidence": "high",
                    "pinned": False,
                    "created_at": now_iso,
                })

    prefs["avoid"] = avoid[:_MAX_LIST_ITEMS]
    prefs["loved_patterns"] = loved[:_MAX_LIST_ITEMS]
    profile["memories"] = memories

    profile["profile_version"] = _PROFILE_VERSION
    return profile


# ---------------------------------------------------------------------------
# Profile PATCH helpers (Slice Two, Section F)
# ---------------------------------------------------------------------------

def set_memory_enabled(profile: dict, enabled: bool) -> dict:
    """Toggle memory_enabled on the profile."""
    profile["memory_enabled"] = bool(enabled)
    return profile


def pin_memory(profile: dict, memory_id: str, pinned: bool) -> dict:
    """Set pinned state on a memory by id. No-op if not found."""
    for m in profile.get("memories", []):
        if m.get("id") == memory_id:
            m["pinned"] = bool(pinned)
            break
    return profile


def delete_memory(profile: dict, memory_id: str) -> dict:
    """Remove a memory by id. No-op if not found."""
    profile["memories"] = [
        m for m in profile.get("memories", []) if m.get("id") != memory_id
    ]
    return profile

def select_memories_for_prompt(profile: dict, limit: int = 5) -> list[dict]:
    """Return up to *limit* highest-value memories for prompt injection.

    Selection: pinned first, then confidence descending, then newest.
    """
    memories = profile.get("memories", [])
    if not memories:
        return []
    return sorted(memories, key=_memory_value, reverse=True)[:limit]


def profile_has_content(profile: dict) -> bool:
    """Return True when the profile has any summarised taste data or memories."""
    taste = profile.get("taste_profile", {})
    has_taste = any(
        isinstance(taste.get(f), list) and taste[f]
        for f in ("top_artists", "recurring_styles", "favorite_eras",
                  "recent_shifts", "playlist_patterns",
                  "saved_library_artists", "followed_artists",
                  "replay_affinity")
    )
    has_prefs = any(
        isinstance(profile.get("commentary_preferences", {}).get(f), list)
        and profile["commentary_preferences"][f]
        for f in ("tone", "avoid", "loved_patterns")
    )
    has_memories = bool(profile.get("memories"))
    return has_taste or has_prefs or has_memories
