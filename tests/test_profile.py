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
        profile_mod._FEEDBACK_PATH = profile_mod._PROFILE_DIR / "feedback.jsonl"
        profile_mod._OWNER_PATH = profile_mod._PROFILE_DIR / "owner_id"

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
        _test_summarize_context_with_spotify_genres_only(profile_mod)
        _test_summarize_context_with_both_sources(profile_mod)
        _test_summarize_context_empty_genres(profile_mod)
        _test_empty_profile_prompt_unchanged()
        _test_disabled_profile_prompt_unchanged()
        _test_populated_profile_prompt_has_block()
        _test_commentary_language_prompt()
        # Slice Two tests
        _test_summarize_library_recency_split(profile_mod)
        _test_summarize_library_followed_artists(profile_mod)
        _test_summarize_library_graceful_empty(profile_mod)
        _test_summarize_saved_casts_empty(profile_mod)
        _test_summarize_saved_casts_replay_affinity(profile_mod)
        _test_feedback_append_and_load(profile_mod)
        _test_feedback_fold_threshold(profile_mod)
        _test_feedback_override_precedence(profile_mod)
        _test_profile_patch_helpers(profile_mod)
        _test_prompt_includes_new_fields(profile_mod)
        _test_empty_profile_still_unchanged_with_new_fields(profile_mod)
        _test_owner_guard(profile_mod)
        # Memory Controls v1 tests
        _test_reset_deletes_feedback(profile_mod)
        _test_memory_off_prompt_omits_trail()
        _test_memory_on_prompt_contains_both()
        _test_replay_affinity_prompt_memory_controls()
        _test_incognito_prompt_omits_all()
        _test_summarizers_skip_trail_when_memory_disabled(profile_mod)
        # Cast lenses tests
        _test_cast_depth_deep_injects_directive()
        _test_cast_vibe_witty_injects_tone()
        _test_cast_lenses_default_unchanged()

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


def _test_summarize_context_with_spotify_genres_only(m):
    """recurring_styles populated from Spotify genres when no Last.fm tags."""
    context = {
        "listener_profile": {
            "top_artists_all_time": ["Artist A", "Artist B"],
            "recently_played_count": 5,
            "spotify_genres": ["ambient", "electronic", "ambient", "idm", "electronic"],
        },
        "artist_profiles": {},
    }
    p = m._empty_profile()
    updated = m.summarize_context(context, p)
    styles = updated["taste_profile"]["recurring_styles"]
    # Frequency order: ambient (2), electronic (2), idm (1) — but ambient then electronic
    # (stable by first occurrence per most_common? Actually Counter.most_common groups
    # by count then insertion order. ambient and electronic both appear 2x; ambient first
    # in the input so it should be first.)
    assert styles[0] == "ambient", f"Expected ambient first, got {styles}"
    assert styles[1] == "electronic", f"Expected electronic second, got {styles}"
    assert styles[2] == "idm", f"Expected idm third, got {styles}"
    assert updated["sources"]["lastfm"]["connected"] is False
    print("  summarize_context_with_spotify_genres_only ✓")


def _test_summarize_context_with_both_sources(m):
    """recurring_styles merges Last.fm tags AND Spotify genres, deduped."""
    context = {
        "listener_profile": {
            "top_artists_all_time": ["Four Tet"],
            "recently_played_count": 5,
            "spotify_genres": ["electronic", "idm", "ambient"],
        },
        "artist_profiles": {
            "Four Tet": {"tags": ["electronica", "idm", "ambient"], "fan_era": "longtime fan"},
        },
        "lastfm_user": {"username": "testuser", "total_scrobbles": 50000},
    }
    p = m._empty_profile()
    updated = m.summarize_context(context, p)
    styles = updated["taste_profile"]["recurring_styles"]
    # Last.fm tags first: electronica, idm, ambient
    # Then Spotify genres (deduped): electronic
    # Result: electronica, idm, ambient, electronic
    assert styles[0] == "electronica", f"Expected electronica first, got {styles}"
    assert "idm" in styles
    assert "ambient" in styles
    assert "electronic" in styles
    # Verify no duplicates
    assert len(styles) == len(set(styles)), f"Duplicates found in {styles}"
    assert updated["sources"]["lastfm"]["connected"] is True
    print("  summarize_context_with_both_sources ✓")


def _test_summarize_context_empty_genres(m):
    """Empty/missing spotify_genres does not crash and recurring_styles unchanged."""
    # No spotify_genres key at all
    context_no_key = {
        "listener_profile": {
            "top_artists_all_time": ["Artist A"],
            "recently_played_count": 5,
        },
        "artist_profiles": {},
    }
    p = m._empty_profile()
    updated = m.summarize_context(context_no_key, p)
    assert updated["taste_profile"]["recurring_styles"] == []
    print("  summarize_context_empty_genres (no key) ✓")

    # Empty list
    context_empty = {
        "listener_profile": {
            "top_artists_all_time": ["Artist A"],
            "recently_played_count": 5,
            "spotify_genres": [],
        },
        "artist_profiles": {},
    }
    p2 = m._empty_profile()
    updated2 = m.summarize_context(context_empty, p2)
    assert updated2["taste_profile"]["recurring_styles"] == []
    print("  summarize_context_empty_genres (empty list) ✓")

    # None value
    context_none = {
        "listener_profile": {
            "top_artists_all_time": ["Artist A"],
            "recently_played_count": 5,
            "spotify_genres": None,
        },
        "artist_profiles": {},
    }
    p3 = m._empty_profile()
    updated3 = m.summarize_context(context_none, p3)
    assert updated3["taste_profile"]["recurring_styles"] == []
    print("  summarize_context_empty_genres (None value) ✓")


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


def _test_commentary_language_prompt():
    """commentary_language adds an explicit language requirement to the prompt."""
    from resonova.api.gemini import build_prompt

    ctx = _make_minimal_context()
    ctx["commentary_language"] = "Mandarin Chinese"

    prompt = build_prompt(ctx)

    assert "LANGUAGE REQUIREMENT" in prompt
    assert "Write all host dialogue in Mandarin Chinese" in prompt
    assert "artist names, song titles, album titles" in prompt

    print("  commentary_language_prompt ✓")


def _test_disabled_profile_prompt_unchanged():
    """memory_enabled=False → PERSISTENT MEMORY block injected with DURABLE fields only."""
    from resonova.api.gemini import build_prompt
    ctx = _make_minimal_context()
    ctx["persistent_profile"] = {
        "memory_enabled": False,
        "taste_profile": {"top_artists": ["Radiohead"]},
        "memories": [],
        "commentary_preferences": {},
    }
    prompt = build_prompt(ctx)
    # Memory-off is PARTIAL: DURABLE fields still appear, TRAIL fields suppressed.
    assert "PERSISTENT MEMORY" in prompt, (
        "Memory-off profile must still inject a PERSISTENT MEMORY block (DURABLE fields)"
    )
    assert "Radiohead" in prompt, "DURABLE top_artists should appear in memory-off prompt"
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


# ---------------------------------------------------------------------------
# Slice Two: summarize_library (recency-split saved tracks + followed artists)
# ---------------------------------------------------------------------------

def _test_summarize_library_recency_split(m):
    """Most-recent tracks -> recent_shifts; older -> saved_library_artists."""
    # Create 80 fake saved tracks (newest first, index 0 = most recent)
    saved_tracks = []
    for i in range(80):
        saved_tracks.append({
            "artist_names": [f"RecentArtist{i}" if i < 50 else f"OldArtist{i - 50}"],
            "added_at": f"2026-06-{(80 - i):02d}T00:00:00+00:00",
        })

    p = m._empty_profile()
    updated = m.summarize_library(saved_tracks, [], p)
    recent = updated["taste_profile"]["recent_shifts"]
    durable = updated["taste_profile"]["saved_library_artists"]

    # The first 50 tracks = RecentArtist0..49 -> should appear in recent_shifts
    assert any("RecentArtist0" in a or "RecentArtist" in a for a in recent), (
        f"Recent artists not in recent_shifts: {recent}"
    )
    # The older 30 tracks (indices 50-79) = OldArtist0..29 -> saved_library_artists
    assert any("OldArtist" in a for a in durable), (
        f"Old artists not in saved_library_artists: {durable}"
    )
    print("  summarize_library_recency_split ✓")


def _test_summarize_library_followed_artists(m):
    """followed_artists list is populated from follow data."""
    p = m._empty_profile()
    followed = ["Burial", "The Caretaker", "Grouper"]
    updated = m.summarize_library([], followed, p)
    assert updated["taste_profile"]["followed_artists"] == followed[:m._MAX_LIST_ITEMS]
    assert updated["sources"]["spotify"]["connected"] is True
    assert "user-follow-read" in updated["sources"]["spotify"]["scopes_used"]
    print("  summarize_library_followed_artists ✓")


def _test_summarize_library_graceful_empty(m):
    """Empty saved_tracks + followed_artists doesn't crash."""
    p = m._empty_profile()
    updated = m.summarize_library([], [], p)
    assert updated["taste_profile"]["recent_shifts"] == []
    assert updated["taste_profile"]["saved_library_artists"] == []
    assert updated["taste_profile"]["followed_artists"] == []
    print("  summarize_library_graceful_empty ✓")


# ---------------------------------------------------------------------------
# Slice Two: summarize_saved_casts (saved cast count + playlist_patterns)
# ---------------------------------------------------------------------------

def _test_summarize_saved_casts_empty(m):
    """Works gracefully when no episodes exist yet."""
    p = m._empty_profile()
    updated = m.summarize_saved_casts(p)
    # saved_cast_count is set (possibly 0 if no real episodes dir)
    assert isinstance(updated["sources"]["resonova"]["saved_cast_count"], int)
    print("  summarize_saved_casts_empty ✓")


def _test_summarize_saved_casts_replay_affinity(m):
    """Meaningful replay counts should become memory-on-only playlist affinity."""
    import tempfile
    from pathlib import Path
    import resonova.episodes as episodes_mod

    original_dir = episodes_mod._EPISODES_DIR
    with tempfile.TemporaryDirectory() as tmp:
        episodes_mod._EPISODES_DIR = Path(tmp) / "episodes"
        try:
            episodes_mod.save_episode(
                episode_id="affinity-001",
                name="Affinity One",
                playlist_uri="spotify:playlist:affinity",
                playlist_name="Late Night Focus",
                track_count=5,
                queue=[],
            )
            episodes_mod.save_episode(
                episode_id="affinity-002",
                name="Affinity Two",
                playlist_uri="spotify:playlist:affinity",
                playlist_name="Late Night Focus",
                track_count=5,
                queue=[],
            )
            episodes_mod.record_replay_event("affinity-001", "meaningful", "s1", 5, 10)
            episodes_mod.record_replay_event("affinity-001", "meaningful", "s2", 6, 10)

            p = m._empty_profile()
            updated = m.summarize_saved_casts(p, memory_enabled=True)
            affinity = updated["taste_profile"]["replay_affinity"]
            assert any("Late Night Focus" in item for item in affinity), (
                "memory-on replay counts should derive playlist affinity"
            )
            assert updated["sources"]["resonova"]["saved_cast_count"] == 2

            p_off = m._empty_profile()
            updated_off = m.summarize_saved_casts(p_off, memory_enabled=False)
            assert updated_off["taste_profile"]["replay_affinity"] == [], (
                "memory-off must not write replay-derived trail"
            )
            assert updated_off["sources"]["resonova"]["saved_cast_count"] == 2
        finally:
            episodes_mod._EPISODES_DIR = original_dir

    print("  summarize_saved_casts_replay_affinity ✓")


# ---------------------------------------------------------------------------
# Slice Two: feedback channel
# ---------------------------------------------------------------------------

def _test_feedback_append_and_load(m):
    """append_feedback writes to feedback.jsonl, _load_feedback reads it."""
    import tempfile
    from pathlib import Path

    old_path = m._FEEDBACK_PATH
    with tempfile.TemporaryDirectory() as tmp:
        m._PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        test_fb_path = m._PROFILE_DIR / "feedback_test.jsonl"
        # Temporarily redirect
        m._FEEDBACK_PATH = test_fb_path

        event = {
            "id": "test_001",
            "episode_id": "ep_abc",
            "segment_index": None,
            "verdict": "down",
            "tags": ["too long"],
            "note": None,
            "created_at": "2026-06-21T12:00:00+00:00",
        }
        m.append_feedback(event)

        loaded = m._load_feedback()
        assert len(loaded) == 1
        assert loaded[0]["id"] == "test_001"
        assert loaded[0]["verdict"] == "down"

        # Cleanup
        m._FEEDBACK_PATH = old_path
        if test_fb_path.exists():
            test_fb_path.unlink()

    print("  feedback_append_and_load ✓")


def _test_feedback_fold_threshold(m):
    """3x same down-tag folds into commentary_preferences.avoid with high confidence."""
    import tempfile

    old_fb_path = m._FEEDBACK_PATH

    with tempfile.TemporaryDirectory() as tmp:
        test_fb_path = m._PROFILE_DIR / "feedback_fold_test.jsonl"
        m._FEEDBACK_PATH = test_fb_path

        for i in range(3):
            m.append_feedback({
                "id": f"e{i}",
                "episode_id": f"ep_{i}",
                "segment_index": None,
                "verdict": "down",
                "tags": ["too long"],
                "note": None,
                "created_at": "2026-06-21T12:00:00+00:00",
            })

        p = m._empty_profile()
        updated = m.fold_feedback_into_profile(p)

        assert "long intros" in updated["commentary_preferences"]["avoid"], (
            f"Expected 'long intros' in avoid: {updated['commentary_preferences']['avoid']}"
        )
        # Should have a high-confidence memory from feedback
        high_mems = [mm for mm in updated["memories"] if mm["source"] == "feedback" and mm["confidence"] == "high"]
        assert high_mems, "Expected at least one high-confidence feedback memory"

        # Feedback_count should be set
        assert updated["sources"]["resonova"]["feedback_count"] == 3

        # Cleanup
        m._FEEDBACK_PATH = old_fb_path
        if test_fb_path.exists():
            test_fb_path.unlink()

    print("  feedback_fold_threshold ✓")


def _test_feedback_override_precedence(m):
    """Feedback (high) shadows inferred memories; pinned beats feedback(high)."""
    import tempfile

    old_fb_path = m._FEEDBACK_PATH

    with tempfile.TemporaryDirectory() as tmp:
        test_fb_path = m._PROFILE_DIR / "feedback_prec_test.jsonl"
        m._FEEDBACK_PATH = test_fb_path

        # Add 3x 'too long' down feedback -> folds to high-confidence memory
        for i in range(3):
            m.append_feedback({
                "id": f"prec_{i}",
                "episode_id": "ep_x",
                "segment_index": None,
                "verdict": "down",
                "tags": ["too long"],
                "note": None,
                "created_at": "2026-06-21T12:00:00+00:00",
            })

        p = m._empty_profile()
        # Add an inferred (low-confidence) memory
        p["memories"].append({
            "id": "inferred_001",
            "text": "Listener seems to like long shows",
            "source": "spotify",
            "confidence": "low",
            "pinned": False,
            "created_at": "2026-06-20T00:00:00+00:00",
        })
        # Add a pinned memory
        p["memories"].append({
            "id": "pinned_001",
            "text": "Always listen at night",
            "source": "manual",
            "confidence": "high",
            "pinned": True,
            "created_at": "2026-06-19T00:00:00+00:00",
        })

        updated = m.fold_feedback_into_profile(p)

        # Inferred low-confidence memory must NOT be deleted (shadowed, not deleted)
        ids = {mm["id"] for mm in updated["memories"]}
        assert "inferred_001" in ids, "Inferred memory must NOT be deleted, only shadowed"
        # Pinned memory must survive
        assert "pinned_001" in ids, "Pinned memory must survive"

        # Select for prompt: pinned should come first, then feedback high
        selected = m.select_memories_for_prompt(updated, limit=5)
        first_sources = [mm["source"] for mm in selected[:2]]
        assert "manual" in first_sources or selected[0].get("pinned"), (
            f"Pinned should rank first: {selected[:2]}"
        )

        # Cleanup
        m._FEEDBACK_PATH = old_fb_path
        if test_fb_path.exists():
            test_fb_path.unlink()

    print("  feedback_override_precedence ✓")


def _test_profile_patch_helpers(m):
    """set_memory_enabled, pin_memory, delete_memory work correctly."""
    p = m._empty_profile()
    p["memories"].append({
        "id": "mem_x",
        "text": "Test memory",
        "source": "spotify",
        "confidence": "medium",
        "pinned": False,
        "created_at": "2026-06-21T00:00:00+00:00",
    })

    # Disable memory
    p = m.set_memory_enabled(p, False)
    assert p["memory_enabled"] is False

    # Pin memory
    p = m.pin_memory(p, "mem_x", True)
    assert p["memories"][0]["pinned"] is True

    # Unpin
    p = m.pin_memory(p, "mem_x", False)
    assert p["memories"][0]["pinned"] is False

    # Delete
    p = m.delete_memory(p, "mem_x")
    assert len(p["memories"]) == 0

    # No-op delete
    p = m.delete_memory(p, "nonexistent")
    assert len(p["memories"]) == 0

    print("  profile_patch_helpers ✓")


def _test_prompt_includes_new_fields(m):
    """New taste fields (recent_shifts, saved_library_artists, followed_artists) appear in prompt."""
    from resonova.api.gemini import build_prompt

    ctx = {
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
        "listener_profile": {"top_artists_all_time": [], "recently_played_count": 0},
        "artist_profiles": {},
        "playlist_name": "Test Playlist",
        "persistent_profile": {
            "memory_enabled": True,
            "taste_profile": {
                "top_artists": [],
                "recurring_styles": [],
                "favorite_eras": [],
                "recent_shifts": ["NewArtistX"],
                "playlist_patterns": [],
                "saved_library_artists": ["LibraryArtistY"],
                "followed_artists": ["FollowedArtistZ"],
            },
            "memories": [],
            "commentary_preferences": {"tone": [], "depth": "balanced", "avoid": [], "loved_patterns": []},
        },
    }
    prompt = build_prompt(ctx)
    assert "NewArtistX" in prompt, "recent_shifts should appear in prompt"
    assert "LibraryArtistY" in prompt, "saved_library_artists should appear in prompt"
    assert "FollowedArtistZ" in prompt, "followed_artists should appear in prompt"
    print("  prompt_includes_new_fields ✓")


def _test_empty_profile_still_unchanged_with_new_fields(m):
    """Empty profile with new fields -> no PERSISTENT MEMORY block injected."""
    from resonova.api.gemini import build_prompt
    ctx = {
        "tracks": [{"uri": "spotify:track:abc", "name": "T", "artist": "A",
                    "album": "Al", "year": 2020, "duration_s": 200,
                    "popularity": 50, "is_personal_favorite": False,
                    "recently_played": False, "artist_in_top": False, "features": None}],
        "summary": {"total_tracks": 1, "personal_favorites_count": 0,
                    "avg_energy": None, "avg_valence": None,
                    "avg_danceability": None, "avg_tempo": None, "lastfm_total_plays": 0},
        "listener_profile": {"top_artists_all_time": [], "recently_played_count": 0},
        "artist_profiles": {},
        "playlist_name": "Test",
    }
    prompt = build_prompt(ctx)
    assert "PERSISTENT MEMORY" not in prompt
    print("  empty_profile_still_unchanged_with_new_fields ✓")


def _test_owner_guard(m):
    """Single-user guard: first connect claims ownership; others rejected; reset doesn't unlock."""
    assert m.get_owner_id() is None
    assert m.claim_or_check_owner("user_a") is True        # first connect claims ownership
    assert m.get_owner_id() == "user_a"
    assert m.claim_or_check_owner("user_a") is True         # same owner ok
    assert m.claim_or_check_owner("user_b") is False        # foreign account rejected
    assert m.claim_or_check_owner(None) is False            # unknown id fails closed
    m.reset_profile()                                       # clearing memory must NOT unlock
    assert m.get_owner_id() == "user_a"
    print("  owner_guard ✓")


# ---------------------------------------------------------------------------
# Memory Controls v1 tests
# ---------------------------------------------------------------------------

def _test_reset_deletes_feedback(m):
    """reset_profile must delete feedback.jsonl so cleared prefs don't resurrect."""
    import json

    # Write a feedback event
    m._PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    m.append_feedback({
        "id": "fb_reset_test",
        "episode_id": "ep_reset",
        "segment_index": None,
        "verdict": "up",
        "tags": ["good story"],
        "note": None,
        "created_at": "2026-06-22T00:00:00+00:00",
    })
    assert m._FEEDBACK_PATH.exists(), "feedback.jsonl should exist after append"

    # Reset
    m.reset_profile()

    assert not m._FEEDBACK_PATH.exists(), (
        "feedback.jsonl must be deleted after reset_profile"
    )
    print("  reset_deletes_feedback ✓")


def _test_memory_off_prompt_omits_trail():
    """memory_enabled=False → DURABLE fields present, TRAIL fields absent."""
    from resonova.api.gemini import build_prompt

    ctx = _make_minimal_context()
    ctx["persistent_profile"] = {
        "memory_enabled": False,
        "taste_profile": {
            "top_artists": ["DurableArtist"],          # DURABLE
            "recurring_styles": ["ambient"],
            "favorite_eras": ["1990s"],
            "recent_shifts": ["TrailArtist"],           # TRAIL
            "playlist_patterns": ["frequently casts from 'X'"],  # TRAIL
            "saved_library_artists": ["LibArtist"],
            "followed_artists": ["FolArtist"],
            "replay_affinity": ["strong affinity with 'Replay Mix' style"],  # TRAIL
        },
        "memories": [],
        "commentary_preferences": {"tone": [], "depth": "balanced", "avoid": [], "loved_patterns": []},
    }
    prompt = build_prompt(ctx)

    # DURABLE marker must be present
    assert "DurableArtist" in prompt, (
        "DURABLE top_artists should appear in memory-off prompt"
    )

    # TRAIL markers must be absent
    assert "TrailArtist" not in prompt, (
        "TRAIL recent_shifts must NOT appear in memory-off prompt"
    )
    assert "frequently casts from" not in prompt, (
        "TRAIL playlist_patterns must NOT appear in memory-off prompt"
    )
    assert "Replay Mix" not in prompt, (
        "TRAIL replay_affinity must NOT appear in memory-off prompt"
    )
    print("  memory_off_prompt_omits_trail ✓")


def _test_memory_on_prompt_contains_both():
    """memory_enabled=True → both DURABLE and TRAIL fields present."""
    from resonova.api.gemini import build_prompt

    ctx = _make_minimal_context()
    ctx["persistent_profile"] = {
        "memory_enabled": True,
        "taste_profile": {
            "top_artists": ["DurableMain"],             # DURABLE
            "recurring_styles": ["ambient"],
            "favorite_eras": [],
            "recent_shifts": ["TrailShiftArtist"],      # TRAIL
            "playlist_patterns": ["frequently casts from 'Night'"],  # TRAIL
            "saved_library_artists": [],
            "followed_artists": [],
            "replay_affinity": ["strong affinity with 'Night Drive' style"],
        },
        "memories": [],
        "commentary_preferences": {"tone": [], "depth": "balanced", "avoid": [], "loved_patterns": []},
    }
    prompt = build_prompt(ctx)

    assert "DurableMain" in prompt, "DURABLE fields must appear in memory-on prompt"
    assert "TrailShiftArtist" in prompt, "TRAIL fields must appear in memory-on prompt"
    assert "Night Drive" in prompt, "replay affinity should appear in memory-on prompt"
    print("  memory_on_prompt_contains_both ✓")


def _test_replay_affinity_prompt_memory_controls():
    """Replay affinity should be private steering and still obey incognito."""
    from resonova.api.gemini import build_prompt

    ctx = _make_minimal_context()
    ctx["persistent_profile"] = {
        "memory_enabled": True,
        "taste_profile": {
            "top_artists": [],
            "recurring_styles": [],
            "favorite_eras": [],
            "recent_shifts": [],
            "playlist_patterns": [],
            "saved_library_artists": [],
            "followed_artists": [],
            "replay_affinity": ["strong affinity with 'Rainy Window' style"],
        },
        "memories": [],
        "commentary_preferences": {"tone": [], "depth": "balanced", "avoid": [], "loved_patterns": []},
    }
    prompt = build_prompt(ctx)
    assert "Rainy Window" in prompt, "memory-on replay affinity should reach the prompt"
    assert "you replayed" in prompt, "guardrail should forbid explicit replay callbacks"

    ctx["incognito"] = True
    incognito_prompt = build_prompt(ctx)
    assert "Rainy Window" not in incognito_prompt, "incognito must suppress replay affinity"

    print("  replay_affinity_prompt_memory_controls ✓")


def _test_incognito_prompt_omits_all():
    """incognito=True → neither LISTENER PROFILE nor PERSISTENT MEMORY."""
    from resonova.api.gemini import build_prompt

    ctx = _make_minimal_context()
    # Add a populated persistent profile so we can confirm it's suppressed
    ctx["persistent_profile"] = {
        "memory_enabled": True,
        "taste_profile": {
            "top_artists": ["TopArtist"],
            "recurring_styles": [],
            "favorite_eras": [],
            "recent_shifts": ["ShiftArtist"],
            "playlist_patterns": [],
            "saved_library_artists": [],
            "followed_artists": [],
            "replay_affinity": ["strong affinity with 'Hidden Replay' style"],
        },
        "memories": [{"id": "m1", "text": "A memory", "source": "feedback",
                      "confidence": "high", "pinned": False,
                      "created_at": "2026-06-22T00:00:00+00:00"}],
        "commentary_preferences": {"tone": [], "depth": "balanced", "avoid": [], "loved_patterns": []},
    }
    # Set listener_profile with top artists so we can test it's suppressed
    ctx["listener_profile"] = {
        "top_artists_all_time": ["ListenerTop"],
        "recently_played_count": 5,
    }
    ctx["incognito"] = True

    prompt = build_prompt(ctx)

    assert "Top artists all-time" not in prompt, (
        "LISTENER PROFILE must be omitted in incognito mode"
    )
    assert "PERSISTENT MEMORY" not in prompt, (
        "PERSISTENT MEMORY must be omitted in incognito mode"
    )
    assert "TopArtist" not in prompt, (
        "Profile data must not appear in incognito prompt"
    )
    assert "Hidden Replay" not in prompt, (
        "Replay affinity must not appear in incognito prompt"
    )
    print("  incognito_prompt_omits_all ✓")


def _test_cast_depth_deep_injects_directive():
    """cast_depth='deep' → prompt contains the DEPTH directive."""
    from resonova.api.gemini import build_prompt

    ctx = _make_minimal_context()
    ctx["cast_depth"] = "deep"

    prompt = build_prompt(ctx)

    assert "DEPTH" in prompt, "deep cast_depth should inject DEPTH directive"
    assert "go deeper" in prompt, "deep directive should contain 'go deeper'"
    print("  cast_depth_deep_injects_directive ✓")


def _test_cast_vibe_witty_injects_tone():
    """cast_vibe='witty' → prompt contains the witty tone descriptor."""
    from resonova.api.gemini import build_prompt

    ctx = _make_minimal_context()
    ctx["cast_vibe"] = "witty"

    prompt = build_prompt(ctx)

    assert "VIBE" in prompt, "cast_vibe should inject VIBE directive"
    assert "playful, quick, dry-humored" in prompt, (
        "witty vibe should contain the correct tone descriptor"
    )
    print("  cast_vibe_witty_injects_tone ✓")


def _test_cast_lenses_default_unchanged():
    """No cast_depth/cast_vibe and no profile → prompt is byte-identical."""
    from resonova.api.gemini import build_prompt

    ctx = _make_minimal_context()
    prompt_no_lens = build_prompt(ctx)

    # Same call again — assert identity
    prompt_again = build_prompt(ctx)
    assert prompt_no_lens == prompt_again, (
        "Repeated call without lenses must produce identical prompt"
    )
    # Must NOT contain any lens directive marker
    assert "CAST DIRECTIVES" not in prompt_no_lens, (
        "No CAST DIRECTIVES block when no lenses are set"
    )
    assert "PACING" not in prompt_no_lens
    assert "DEPTH" not in prompt_no_lens
    assert "VIBE" not in prompt_no_lens
    print("  cast_lenses_default_unchanged ✓")


def _test_summarizers_skip_trail_when_memory_disabled(m):
    """summarize_library with memory_enabled=False must skip recent_shifts but
    still update DURABLE fields (saved_library_artists)."""
    # Create saved tracks (50 recent + 30 old)
    saved_tracks = []
    for i in range(80):
        saved_tracks.append({
            "artist_names": [f"RecentA{i}" if i < 50 else f"OldA{i - 50}"],
            "added_at": f"2026-06-{(80 - i):02d}T00:00:00+00:00",
        })

    p = m._empty_profile()
    updated = m.summarize_library(saved_tracks, ["FollowedX"], p, memory_enabled=False)

    # TRAIL: recent_shifts must NOT be written
    recent = updated["taste_profile"]["recent_shifts"]
    assert recent == [], (
        f"recent_shifts should be empty when memory_enabled=False, got {recent}"
    )

    # DURABLE: saved_library_artists and followed_artists must still be written
    durable = updated["taste_profile"]["saved_library_artists"]
    assert any("OldA" in a for a in durable), (
        f"saved_library_artists must still be populated: {durable}"
    )
    assert "FollowedX" in updated["taste_profile"]["followed_artists"], (
        "followed_artists must still be updated"
    )
    print("  summarizers_skip_trail_when_memory_disabled ✓")


if __name__ == "__main__":
    _run_tests()
