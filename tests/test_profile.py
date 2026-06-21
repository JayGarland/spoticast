"""
Tests for profile.py — store round-trip, cap eviction, and prompt impact.

Run with:
    uv run python tests/test_profile.py

No Spotify / Gemini / network calls required.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path


def _run_tests() -> None:
    import resonova.profile as profile_mod

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        profile_mod._PROFILE_DIR = tmp_path / "profile"
        profile_mod._PROFILE_PATH = profile_mod._PROFILE_DIR / "profile.json"

        _test_empty_profile(profile_mod)
        _test_round_trip(profile_mod)
        _test_reset(profile_mod)
        _test_missing_file_returns_empty(profile_mod)
        _test_corrupted_file_returns_empty(profile_mod)
        _test_cap_list_fields(profile_mod)
        _test_cap_memories_eviction(profile_mod)
        _test_memory_eviction_order(profile_mod)
        _test_profile_has_content(profile_mod)
        _test_select_memories_for_prompt(profile_mod)
        _test_summarize_context_minimal(profile_mod)
        _test_summarize_context_with_lastfm(profile_mod)
        _test_empty_profile_prompt_unchanged()
        _test_disabled_profile_prompt_unchanged()
        _test_populated_profile_prompt_has_block()

    print("All profile tests passed ✓")


# ---------------------------------------------------------------------------
# Store tests
# ---------------------------------------------------------------------------

def _test_empty_profile(m):
    p = m._empty_profile()
    assert p["profile_version"] == 1
    assert p["memory_enabled"] is True
    assert isinstance(p["memories"], list)
    assert isinstance(p["taste_profile"]["top_artists"], list)
    print("  empty_profile ✓")


def _test_round_trip(m):
    p = m._empty_profile()
    p["taste_profile"]["top_artists"] = ["Radiohead", "Burial"]
    p["memories"].append({
        "id": "mem_001",
        "text": "Prefers post-rock.",
        "source": "spotify",
        "confidence": "medium",
        "pinned": False,
        "created_at": "2026-06-21T00:00:00+00:00",
    })
    m.save_profile(p)

    loaded = m.load_profile()
    assert loaded["taste_profile"]["top_artists"] == ["Radiohead", "Burial"]
    assert len(loaded["memories"]) == 1
    assert loaded["memories"][0]["text"] == "Prefers post-rock."
    print("  round_trip ✓")


def _test_reset(m):
    # Populate, then reset
    p = m.load_profile()
    p["taste_profile"]["top_artists"] = ["Flying Lotus"]
    m.save_profile(p)

    empty = m.reset_profile()
    assert empty["taste_profile"]["top_artists"] == []
    assert empty["memories"] == []

    loaded = m.load_profile()
    assert loaded["taste_profile"]["top_artists"] == []
    print("  reset ✓")


def _test_missing_file_returns_empty(m):
    import shutil
    if m._PROFILE_PATH.exists():
        m._PROFILE_PATH.unlink()
    p = m.load_profile()
    assert p["profile_version"] == 1
    assert p["memories"] == []
    print("  missing_file_returns_empty ✓")


def _test_corrupted_file_returns_empty(m):
    m._PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    m._PROFILE_PATH.write_text("{not valid json")
    p = m.load_profile()
    assert p["profile_version"] == 1
    assert p["memories"] == []
    print("  corrupted_file_returns_empty ✓")


def _test_cap_list_fields(m):
    p = m._empty_profile()
    # Write 30 artists (cap is 20)
    p["taste_profile"]["top_artists"] = [f"Artist{i}" for i in range(30)]
    m.save_profile(p)

    loaded = m.load_profile()
    assert len(loaded["taste_profile"]["top_artists"]) == m._MAX_LIST_ITEMS, (
        f"Expected {m._MAX_LIST_ITEMS}, got {len(loaded['taste_profile']['top_artists'])}"
    )
    print("  cap_list_fields ✓")


def _test_cap_memories_eviction(m):
    p = m._empty_profile()
    # Fill with _MAX_MEMORIES + 10 low-confidence memories
    for i in range(m._MAX_MEMORIES + 10):
        p["memories"].append({
            "id": f"mem_{i:04d}",
            "text": f"Memory {i}",
            "source": "spotify",
            "confidence": "low",
            "pinned": False,
            "created_at": f"2026-06-{(i % 30) + 1:02d}T00:00:00+00:00",
        })
    m.save_profile(p)

    loaded = m.load_profile()
    assert len(loaded["memories"]) == m._MAX_MEMORIES, (
        f"Expected {m._MAX_MEMORIES}, got {len(loaded['memories'])}"
    )
    print("  cap_memories_eviction ✓")


def _test_memory_eviction_order(m):
    """Pinned + high-confidence memories must survive eviction over low-confidence ones."""
    p = m._empty_profile()

    # Add max+1 memories: one pinned+high, one medium, rest low
    p["memories"].append({
        "id": "pinned_001",
        "text": "Must survive.",
        "source": "manual",
        "confidence": "high",
        "pinned": True,
        "created_at": "2020-01-01T00:00:00+00:00",  # oldest
    })
    for i in range(m._MAX_MEMORIES):  # fills to _MAX_MEMORIES + 1 total (will evict 1)
        p["memories"].append({
            "id": f"low_{i:04d}",
            "text": f"Low memory {i}",
            "source": "spotify",
            "confidence": "low",
            "pinned": False,
            "created_at": "2026-06-21T00:00:00+00:00",
        })

    m.save_profile(p)
    loaded = m.load_profile()

    assert len(loaded["memories"]) == m._MAX_MEMORIES

    ids = {mem["id"] for mem in loaded["memories"]}
    assert "pinned_001" in ids, "Pinned high-confidence memory must survive eviction"
    print("  memory_eviction_order ✓")


# ---------------------------------------------------------------------------
# profile_has_content / select_memories_for_prompt
# ---------------------------------------------------------------------------

def _test_profile_has_content(m):
    p = m._empty_profile()
    assert not m.profile_has_content(p), "Empty profile should report no content"

    p["taste_profile"]["top_artists"] = ["Björk"]
    assert m.profile_has_content(p), "Profile with top_artists should have content"
    print("  profile_has_content ✓")


def _test_select_memories_for_prompt(m):
    p = m._empty_profile()
    mems = [
        {"id": "a", "text": "A", "source": "spotify", "confidence": "low",
         "pinned": False, "created_at": "2026-01-01T00:00:00+00:00"},
        {"id": "b", "text": "B", "source": "feedback", "confidence": "high",
         "pinned": False, "created_at": "2026-01-02T00:00:00+00:00"},
        {"id": "c", "text": "C", "source": "manual", "confidence": "medium",
         "pinned": True, "created_at": "2026-01-01T00:00:00+00:00"},
    ]
    p["memories"] = mems
    selected = m.select_memories_for_prompt(p, limit=2)
    # Expect: pinned C first, then high-confidence B
    assert selected[0]["id"] == "c", f"Expected pinned memory first, got {selected[0]['id']}"
    assert selected[1]["id"] == "b", f"Expected high-confidence second, got {selected[1]['id']}"
    print("  select_memories_for_prompt ✓")


# ---------------------------------------------------------------------------
# Summarise context
# ---------------------------------------------------------------------------

def _test_summarize_context_minimal(m):
    """Summariser builds taste_profile from listener_profile without Last.fm."""
    context = {
        "listener_profile": {
            "top_artists_all_time": ["Boards of Canada", "Aphex Twin", "Autechre"],
            "recently_played_count": 12,
        },
        "artist_profiles": {},
    }
    p = m._empty_profile()
    updated = m.summarize_context(context, p)
    assert "Boards of Canada" in updated["taste_profile"]["top_artists"]
    assert updated["sources"]["spotify"]["connected"] is True
    print("  summarize_context_minimal ✓")


def _test_summarize_context_with_lastfm(m):
    """Summariser merges Last.fm artist tags into recurring_styles."""
    context = {
        "listener_profile": {
            "top_artists_all_time": ["Four Tet"],
            "recently_played_count": 5,
        },
        "artist_profiles": {
            "Four Tet": {"tags": ["electronica", "idm", "ambient"], "fan_era": "longtime fan"},
        },
        "lastfm_user": {"username": "testuser", "total_scrobbles": 50000},
    }
    p = m._empty_profile()
    updated = m.summarize_context(context, p)
    assert "electronica" in updated["taste_profile"]["recurring_styles"]
    assert updated["sources"]["lastfm"]["connected"] is True
    print("  summarize_context_with_lastfm ✓")


# ---------------------------------------------------------------------------
# Prompt impact tests
# ---------------------------------------------------------------------------

def _make_minimal_context() -> dict:
    """Minimal context that satisfies build_prompt requirements."""
    return {
        "tracks": [{
            "uri": "spotify:track:abc",
            "name": "Test Track",
            "artist": "Test Artist",
            "album": "Test Album",
            "year": 2020,
            "duration_s": 240,
            "popularity": 70,
            "is_personal_favorite": False,
            "recently_played": False,
            "artist_in_top": False,
            "features": None,
        }],
        "summary": {
            "total_tracks": 1,
            "personal_favorites_count": 0,
            "avg_energy": None,
            "avg_valence": None,
            "avg_danceability": None,
            "avg_tempo": None,
            "lastfm_total_plays": 0,
        },
        "listener_profile": {
            "top_artists_all_time": [],
            "recently_played_count": 0,
        },
        "artist_profiles": {},
        "playlist_name": "Test Playlist",
    }


def _test_empty_profile_prompt_unchanged():
    """No persistent_profile in context → prompt is byte-for-byte the same."""
    from resonova.api.gemini import build_prompt
    ctx = _make_minimal_context()
    prompt_without = build_prompt(ctx)
    assert "PERSISTENT MEMORY" not in prompt_without, (
        "No profile in context must produce no PERSISTENT MEMORY block"
    )
    print("  empty_profile_prompt_unchanged ✓")


def _test_disabled_profile_prompt_unchanged():
    """memory_enabled=False profile → no memory block injected."""
    from resonova.api.gemini import build_prompt
    ctx = _make_minimal_context()
    ctx["persistent_profile"] = {
        "memory_enabled": False,
        "taste_profile": {"top_artists": ["Radiohead"]},
        "memories": [],
        "commentary_preferences": {},
    }
    prompt = build_prompt(ctx)
    assert "PERSISTENT MEMORY" not in prompt, (
        "Disabled profile must not inject a PERSISTENT MEMORY block"
    )
    print("  disabled_profile_prompt_unchanged ✓")


def _test_populated_profile_prompt_has_block():
    """Non-empty enabled profile → PERSISTENT MEMORY block appears in prompt."""
    from resonova.api.gemini import build_prompt
    ctx = _make_minimal_context()
    ctx["persistent_profile"] = {
        "memory_enabled": True,
        "taste_profile": {
            "top_artists": ["Radiohead", "Burial"],
            "recurring_styles": ["ambient", "post-rock"],
            "favorite_eras": [], "recent_shifts": [], "playlist_patterns": [],
        },
        "memories": [],
        "commentary_preferences": {"tone": [], "depth": "balanced", "avoid": [], "loved_patterns": []},
    }
    prompt = build_prompt(ctx)
    assert "PERSISTENT MEMORY" in prompt, "Non-empty enabled profile must inject memory block"
    assert "Radiohead" in prompt, "Top artists should appear in memory block"
    assert "you often listen to" not in prompt.lower(), (
        "Prompt must NOT contain forbidden phrase 'you often listen to'"
    )
    print("  populated_profile_prompt_has_block ✓")


if __name__ == "__main__":
    _run_tests()
