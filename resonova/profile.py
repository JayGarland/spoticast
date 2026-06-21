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
    """Wipe profile to an empty skeleton; saved cast episodes are untouched."""
    empty = _empty_profile()
    _PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    _PROFILE_PATH.write_text(json.dumps(empty, indent=2))
    return empty


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
                  "recent_shifts", "playlist_patterns"):
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

def summarize_context(context: dict[str, Any], profile: dict | None = None) -> dict:
    """Update the profile from an already-fetched generation context.

    Uses only data already in *context* — zero new Spotify fetches or scopes.
    Call after build_playlist_context() (and optionally enrich_context()).

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
    if tag_counts:
        # Sort by frequency; merge with existing styles
        new_styles = [t for t, _ in sorted(tag_counts.items(), key=lambda x: -x[1])]
        existing_styles = taste.get("recurring_styles") or []
        merged_styles = list(dict.fromkeys(new_styles + [s for s in existing_styles if s not in new_styles]))
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
# Prompt helper: select memories for the compact prompt block
# ---------------------------------------------------------------------------

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
                  "recent_shifts", "playlist_patterns")
    )
    has_prefs = any(
        isinstance(profile.get("commentary_preferences", {}).get(f), list)
        and profile["commentary_preferences"][f]
        for f in ("tone", "avoid", "loved_patterns")
    )
    has_memories = bool(profile.get("memories"))
    return has_taste or has_prefs or has_memories
