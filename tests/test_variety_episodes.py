"""
Smoke tests for variety.py and episodes.py pure functions.

Run with:
    uv run python tests/test_variety_episodes.py

No Spotify / Gemini network calls required.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


# ---------------------------------------------------------------------------
# Minimal stub for a track object that matches what variety.py expects
# ---------------------------------------------------------------------------

@dataclass
class FakeTrack:
    uri: str
    artist: str
    album: str
    name: str = ""
    popularity: int = 50


# ---------------------------------------------------------------------------
# Test user id — all path helpers are now per-user
# ---------------------------------------------------------------------------

TEST_USER_ID = "test_user"


# ---------------------------------------------------------------------------
# Run all tests inside a temp dir (path helpers use Path("generated/..."))
# ---------------------------------------------------------------------------

def _run_tests() -> None:
    import resonova.variety as variety
    import resonova.episodes as episodes

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp).resolve()

        # Change CWD to the temp dir so Path("generated") resolves inside it
        original_cwd = os.getcwd()
        os.chdir(str(tmp_path))

        try:
            _test_fingerprint_stable()
            _test_select_produces_variety(variety)
            _test_select_short_playlist(variety)
            _test_pasted_track_order_not_affected()
            _test_save_variety_memory(variety)
            _test_episodes_lifecycle(episodes)
            _test_episodes_backward_compat(episodes)
            _test_run_number(episodes)
            _test_replay_event_counts(episodes)
            _test_episode_path_traversal_rejected(episodes)
            _test_server_track_ready_metadata_shape()
            _test_quota_error_classification()
            _test_retry_after_formatting()
            _test_failed_episode_save(episodes)
            _test_generate_route_accepts_json_body()
            _test_playlist_card_quick_generate()
            _test_replay_tracking_frontend_shape()
            _test_mobile_hidden_spotify_attempts_before_deferring()
            _test_cooldown_guard_in_server()
            _test_taste_bias_works(variety)
            _test_taste_still_varied(variety)
            _test_no_taste_unchanged(variety)
            _test_episode_tagline_roundtrip(episodes)
            _test_episode_tagline_backward_compat(episodes)
            _test_parse_episode_identity_two_lines()
            _test_parse_episode_identity_one_line()
        finally:
            os.chdir(original_cwd)

    print("All tests passed ✓")


def _test_episode_tagline_roundtrip(episodes):
    """Save episode with tagline → list/get returns it."""
    ep_id = "tagline-test-001"
    queue = [{"type": "audio", "url": "/audio/ep/intro.mp3"}]
    episodes.save_episode(
        user_id=TEST_USER_ID,
        episode_id=ep_id,
        name="Test Episode",
        tagline="Late-night soul for the long drive home",
        playlist_uri="spotify:playlist:tagtest",
        playlist_name="Tag Test Playlist",
        track_count=5,
        queue=queue,
    )
    ep = episodes.get_episode(TEST_USER_ID, ep_id)
    assert ep is not None
    assert ep["tagline"] == "Late-night soul for the long drive home", f"Expected tagline, got {ep.get('tagline')}"

    lst = episodes.list_episodes(TEST_USER_ID)
    found = next((e for e in lst if e["id"] == ep_id), None)
    assert found is not None
    assert found["tagline"] == "Late-night soul for the long drive home", f"Listed tagline mismatch: {found.get('tagline')}"

    episodes.delete_episode(TEST_USER_ID, ep_id)
    print("  episode_tagline_roundtrip ✓")


def _test_episode_tagline_backward_compat(episodes):
    """Old episodes without tagline must still load with tagline=None."""
    ep_id = "old-no-tagline"
    ep_dir = Path("generated") / "users" / TEST_USER_ID / "episodes" / ep_id
    ep_dir.mkdir(parents=True, exist_ok=True)
    old_meta = {
        "id": ep_id,
        "name": "Old No Tagline",
        "playlist_uri": "spotify:playlist:old",
        "playlist_name": "Old Playlist",
        "track_count": 3,
        "created_at": "2025-01-01T00:00:00+00:00",
        "queue": [],
    }
    (ep_dir / "episode.json").write_text(json.dumps(old_meta))

    lst = episodes.list_episodes(TEST_USER_ID)
    found = next((e for e in lst if e["id"] == ep_id), None)
    assert found is not None, "Old episode must appear in list"
    assert found.get("tagline") is None, "tagline should be None for old episodes without it"

    ep = episodes.get_episode(TEST_USER_ID, ep_id)
    assert ep is not None
    assert ep.get("tagline") is None, "tagline should be None via get_episode too"

    episodes.delete_episode(TEST_USER_ID, ep_id)
    print("  episode_tagline_backward_compat ✓")


def _test_parse_episode_identity_two_lines():
    """_parse_episode_identity splits two lines correctly."""
    from resonova.api.gemini import _parse_episode_identity
    result = _parse_episode_identity(
        "Berlin Nights\nLate-night techno for the urban commute"
    )
    assert result["title"] == "Berlin Nights", f"Expected 'Berlin Nights', got {result['title']!r}"
    assert result["tagline"] == "Late-night techno for the urban commute", f"Unexpected tagline: {result['tagline']!r}"
    print("  parse_episode_identity_two_lines ✓")


def _test_parse_episode_identity_one_line():
    """_parse_episode_identity returns empty tagline when only one line."""
    from resonova.api.gemini import _parse_episode_identity
    result = _parse_episode_identity("Berlin Nights")
    assert result["title"] == "Berlin Nights"
    assert result["tagline"] == "", f"Expected empty tagline, got {result['tagline']!r}"
    print("  parse_episode_identity_one_line ✓")


def _test_fingerprint_stable():
    from resonova.variety import compute_fingerprint
    uris = ["spotify:track:a", "spotify:track:b", "spotify:track:c"]
    fp1 = compute_fingerprint(uris)
    fp2 = compute_fingerprint(uris)
    assert fp1 == fp2, "Fingerprint should be stable"
    assert len(fp1) == 8, "Fingerprint should be 8 chars"
    fp3 = compute_fingerprint(list(reversed(uris)))
    assert fp1 != fp3, "Different order → different fingerprint"
    print("  fingerprint_stable ✓")


def _test_select_produces_variety(variety):
    tracks = [FakeTrack(f"spotify:track:{i}", f"Artist{i % 4}", f"Album{i % 6}") for i in range(20)]
    playlist_uri = "spotify:playlist:test001"
    max_tracks = 8

    seen_fingerprints = set()
    for _ in range(6):
        selected = variety.select_tracks_for_episode(tracks, playlist_uri, max_tracks, user_id=TEST_USER_ID)
        assert len(selected) == max_tracks, f"Expected {max_tracks} tracks, got {len(selected)}"
        fp = variety.compute_fingerprint([t.uri for t in selected])
        seen_fingerprints.add(fp)
        variety.save_variety_memory(playlist_uri, TEST_USER_ID, [t.uri for t in selected])

    # After 6 runs we expect at least 3 distinct orders (20 tracks >> 8, many combos possible)
    assert len(seen_fingerprints) >= 3, (
        f"Expected variety across 6 runs, got only {len(seen_fingerprints)} distinct orders"
    )
    print("  select_produces_variety ✓")


def _test_select_short_playlist(variety):
    # Only 3 tracks available, max 5 — should not fail
    tracks = [FakeTrack(f"spotify:track:x{i}", "ArtistA", "AlbumA") for i in range(3)]
    playlist_uri = "spotify:playlist:short"
    for _ in range(10):
        variety.save_variety_memory(playlist_uri, TEST_USER_ID, [t.uri for t in tracks])  # fill memory
    selected = variety.select_tracks_for_episode(tracks, playlist_uri, 5, user_id=TEST_USER_ID)
    assert len(selected) <= 3, "Should return all available tracks (3) not 5"
    print("  select_short_playlist ✓")


def _test_pasted_track_order_not_affected():
    # server.py only calls select_tracks_for_episode for playlist URIs (not track_uris).
    # Here we simply verify our variety module is not invoked for pasted inputs.
    # The guard is in server.py (if job.track_uris → no call to variety).
    # We verify this by inspecting server.py code at a basic level.
    import inspect
    import resonova.server as server_mod
    src = inspect.getsource(server_mod._run_generation)
    assert "_select_playlist_tracks_for_episode" in src
    assert "if job.track_uris" in src
    # Confirm variety is only called in the else branch (after the playlist fetch)
    else_idx = src.index("else:")
    variety_idx = src.index("_select_playlist_tracks_for_episode")
    assert variety_idx > else_idx, "variety selection must be in the else (playlist) branch"
    print("  pasted_track_order_not_affected ✓")


def _test_save_variety_memory(variety):
    playlist_uri = "spotify:playlist:memtest"
    uris_a = [f"spotify:track:a{i}" for i in range(5)]

    variety.save_variety_memory(playlist_uri, TEST_USER_ID, uris_a)
    mem = variety.load_variety_memory(playlist_uri, TEST_USER_ID)
    assert len(mem["recent_orders"]) == 1
    assert mem["recent_orders"][0]["track_uris"] == uris_a

    # Fill to max + 2 and confirm cap
    for i in range(variety._MAX_RECENT + 2):
        variety.save_variety_memory(playlist_uri, TEST_USER_ID, [f"spotify:track:cap{i}_{j}" for j in range(3)])
    mem = variety.load_variety_memory(playlist_uri, TEST_USER_ID)
    assert len(mem["recent_orders"]) == variety._MAX_RECENT, (
        f"Expected {variety._MAX_RECENT} orders, got {len(mem['recent_orders'])}"
    )
    print("  save_variety_memory ✓")


def _test_episodes_lifecycle(episodes):
    ep_id = "test-ep-001"
    queue = [{"type": "audio", "url": "/audio/ep/intro.mp3"}]
    episodes.save_episode(
        user_id=TEST_USER_ID,
        episode_id=ep_id,
        name="Test Episode",
        playlist_uri="spotify:playlist:abc",
        playlist_name="My Playlist",
        track_count=5,
        queue=queue,
        order_fingerprint="abc12345",
        track_order_preview=["Artist A – Track 1", "Artist B – Track 2"],
    )

    ep = episodes.get_episode(TEST_USER_ID, ep_id)
    assert ep is not None
    assert ep["name"] == "Test Episode"
    assert ep["order_fingerprint"] == "abc12345"
    assert ep["track_order_preview"][0] == "Artist A – Track 1"

    # List episodes
    lst = episodes.list_episodes(TEST_USER_ID)
    assert any(e["id"] == ep_id for e in lst)
    found = next(e for e in lst if e["id"] == ep_id)
    assert found["order_fingerprint"] == "abc12345"
    assert found["track_order_preview"] == ["Artist A – Track 1", "Artist B – Track 2"]

    # Rename
    updated = episodes.rename_episode(TEST_USER_ID, ep_id, "  Renamed Episode  ")
    assert updated is not None
    assert updated["name"] == "Renamed Episode"
    ep2 = episodes.get_episode(TEST_USER_ID, ep_id)
    assert ep2["name"] == "Renamed Episode"

    # Delete
    deleted = episodes.delete_episode(TEST_USER_ID, ep_id)
    assert deleted is True
    assert episodes.get_episode(TEST_USER_ID, ep_id) is None
    deleted_again = episodes.delete_episode(TEST_USER_ID, ep_id)
    assert deleted_again is False

    print("  episodes_lifecycle ✓")


def _test_episodes_backward_compat(episodes):
    """Old episodes without new fields must still load and list without error."""
    ep_id = "old-ep-001"
    ep_dir = Path("generated") / "users" / TEST_USER_ID / "episodes" / ep_id
    ep_dir.mkdir(parents=True, exist_ok=True)
    old_meta = {
        "id": ep_id,
        "name": "Old Episode",
        "playlist_uri": "spotify:playlist:old",
        "playlist_name": "Old Playlist",
        "track_count": 3,
        "created_at": "2025-01-01T00:00:00+00:00",
        "queue": [],
    }
    (ep_dir / "episode.json").write_text(json.dumps(old_meta))

    lst = episodes.list_episodes(TEST_USER_ID)
    found = next((e for e in lst if e["id"] == ep_id), None)
    assert found is not None, "Old episode must appear in list"
    assert found.get("order_fingerprint") is None, "order_fingerprint should be None for old episodes"
    assert found.get("track_order_preview") is None, "track_order_preview should be None for old episodes"
    assert found["run_number"] >= 1, "run_number must be assigned"
    assert found["replay_count"] == 0, "old episodes should default replay_count to 0"
    assert found["replay_started_count"] == 0, "old episodes should default replay_started_count to 0"
    print("  episodes_backward_compat ✓")


def _test_run_number(episodes):
    """Episodes from the same playlist should get sequential run numbers."""
    import time
    playlist_uri = "spotify:playlist:runtest"
    for i in range(3):
        episodes.save_episode(
            user_id=TEST_USER_ID,
            episode_id=f"run-ep-{i:03d}",
            name=f"Run {i}",
            playlist_uri=playlist_uri,
            playlist_name="Run Playlist",
            track_count=5,
            queue=[],
            order_fingerprint=f"fp{i:04x}",
        )
        time.sleep(0.01)  # ensure distinct created_at timestamps
    # Also add an episode from a different playlist
    episodes.save_episode(
        user_id=TEST_USER_ID,
        episode_id="run-ep-other",
        name="Other",
        playlist_uri="spotify:playlist:other",
        playlist_name="Other Playlist",
        track_count=2,
        queue=[],
    )

    lst = episodes.list_episodes(TEST_USER_ID)
    run_eps = sorted(
        [e for e in lst if e["playlist_uri"] == playlist_uri],
        key=lambda e: e["created_at"],
    )
    run_numbers = [e["run_number"] for e in run_eps]
    assert run_numbers == [1, 2, 3], f"Expected [1, 2, 3], got {run_numbers}"

    other_ep = next(e for e in lst if e["id"] == "run-ep-other")
    assert other_ep["run_number"] == 1, "Different playlist → independent run number"
    print("  run_number ✓")


def _test_replay_event_counts(episodes):
    """Replay events should dedupe by session and count only meaningful listens."""
    ep_id = "replay-ep-001"
    episodes.save_episode(
        user_id=TEST_USER_ID,
        episode_id=ep_id,
        name="Replay Test",
        playlist_uri="spotify:playlist:replay",
        playlist_name="Replay Playlist",
        track_count=4,
        queue=[{"type": "audio", "url": "/audio/a.mp3"} for _ in range(10)],
    )

    assert episodes.record_replay_event(TEST_USER_ID, ep_id, "start", "session-a", 0, 10) is None
    assert episodes.record_replay_event(TEST_USER_ID, ep_id, "start", "session-a", 0, 10) is None
    listed = next(e for e in episodes.list_episodes(TEST_USER_ID) if e["id"] == ep_id)
    assert listed["replay_started_count"] == 1, "start should dedupe per session"
    assert listed["replay_count"] == 0, "start must not count as meaningful replay"

    assert episodes.record_replay_event(TEST_USER_ID, ep_id, "meaningful", "session-a", 4, 10) is None
    listed = next(e for e in episodes.list_episodes(TEST_USER_ID) if e["id"] == ep_id)
    assert listed["replay_count"] == 0, "below 50% must not count"

    assert episodes.record_replay_event(TEST_USER_ID, ep_id, "meaningful", "session-a", 5, 10) is None
    assert episodes.record_replay_event(TEST_USER_ID, ep_id, "meaningful", "session-a", 8, 10) is None
    ep = episodes.get_episode(TEST_USER_ID, ep_id)
    assert ep["replay_count"] == 1, "meaningful replay should dedupe per session"
    assert ep["last_replayed_at"], "meaningful replay should stamp last_replayed_at"
    assert "_replay_sessions" not in ep, "public episode payload must not expose session ids"

    try:
        episodes.record_replay_event(TEST_USER_ID, ep_id, "bogus", "session-b", 0, 10)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid replay event should raise ValueError")

    assert episodes.record_replay_event(TEST_USER_ID, "missing-episode", "start", "session-c", 0, 1) == "not_found"
    print("  replay_event_counts ✓")


def _test_episode_path_traversal_rejected(episodes):
    """Episode mutation helpers must stay scoped to generated/episodes."""
    for bad_id in ("../escape", "..\\escape", "/tmp/escape"):
        try:
            episodes.get_episode(TEST_USER_ID, bad_id)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected ValueError for get_episode({bad_id!r})")

        try:
            episodes.rename_episode(TEST_USER_ID, bad_id, "Bad")
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected ValueError for rename_episode({bad_id!r})")

        try:
            episodes.delete_episode(TEST_USER_ID, bad_id)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected ValueError for delete_episode({bad_id!r})")

    print("  episode_path_traversal_rejected ✓")


def _test_server_track_ready_metadata_shape():
    """Generation should attach track metadata before the Spotify segment starts."""
    import inspect
    import resonova.server as server_mod

    src = inspect.getsource(server_mod._run_generation)
    assert "tracks_by_uri" in src, "server should map selected track metadata by URI"
    assert '"track_name": track_meta.name' in src, "track_ready should include display title"
    assert '"artist": track_meta.artist' in src, "track_ready should include display artist"
    assert '"duration_ms": track_meta.duration_ms' in src, "track_ready should include duration"
    assert "saved_queue.append(spotify_item)" in src, "saved episodes should persist Spotify metadata"
    print("  server_track_ready_metadata_shape ✓")


def _test_quota_error_classification():
    """_parse_quota_error should detect RESOURCE_EXHAUSTED / 429 and return structured dict."""
    from resonova.api.tts import _parse_quota_error

    # Simulate API JSON error message with retryDelay
    exc_with_delay = Exception(
        '429 RESOURCE_EXHAUSTED Quota exceeded for metric: '
        'generativelanguage.googleapis.com/generate_requests_per_model_per_day '
        '"retryDelay": "31678s" "model": "gemini-3.1-flash-tts-preview"'
    )
    result = _parse_quota_error(exc_with_delay)
    assert result is not None, "Should detect RESOURCE_EXHAUSTED"
    assert result["code"] == "tts_quota_exhausted"
    assert result["retry_after_seconds"] == 31678
    assert "quota" in result["message"].lower()

    # Simulate the Python dict-style error shape seen in the customer report
    exc_reported = Exception(
        "429 RESOURCE_EXHAUSTED. {'error': {'message': 'Please retry in 8h47m58.5s.', "
        "'details': [{'@type': 'type.googleapis.com/google.rpc.RetryInfo', "
        "'retryDelay': '31678s'}], 'quotaDimensions': {'model': 'gemini-3.1-flash-tts'}}}"
    )
    reported = _parse_quota_error(exc_reported)
    assert reported is not None, "Should detect Python dict-style RESOURCE_EXHAUSTED"
    assert reported["retry_after_seconds"] == 31678
    assert reported["model"] == "gemini-3.1-flash-tts"

    # Simulate error with plain-text retryDelay
    exc_plain = Exception("429 RESOURCE_EXHAUSTED retryDelay ~= 8h47m")
    result2 = _parse_quota_error(exc_plain)
    assert result2 is not None
    expected_secs = 8 * 3600 + 47 * 60
    assert result2["retry_after_seconds"] == expected_secs, (
        f"Expected {expected_secs}s, got {result2['retry_after_seconds']}"
    )

    # Unrelated error should return None
    exc_unrelated = Exception("503 Service Unavailable")
    assert _parse_quota_error(exc_unrelated) is None, "Non-quota error should return None"

    # ResourceExhausted in exception type name
    class FakeResourceExhausted(Exception):
        pass
    FakeResourceExhausted.__name__ = "ResourceExhausted"
    exc_type = FakeResourceExhausted("quota limit hit")
    assert _parse_quota_error(exc_type) is not None, "ResourceExhausted class name should be detected"

    print("  quota_error_classification ✓")


def _test_retry_after_formatting():
    """format_duration should produce human-readable strings."""
    from resonova.api.tts import format_duration

    assert format_duration(0) == "0s"
    assert format_duration(45) == "45s"
    assert format_duration(60) == "1m"
    assert format_duration(90) == "1m"
    assert format_duration(3600) == "1h"
    assert format_duration(31678) == "8h 47m"
    assert format_duration(7200) == "2h"
    assert format_duration(7260) == "2h 1m"
    print("  retry_after_formatting ✓")


def _test_failed_episode_save(episodes):
    """save_episode with status='quota_failed' must not appear as complete."""
    ep_id = "quota-ep-001"
    queue = [{"type": "audio", "url": "/audio/episodes/quota-ep-001/intro.mp3"}]
    episodes.save_episode(
        user_id=TEST_USER_ID,
        episode_id=ep_id,
        name="Incomplete Cast",
        playlist_uri="spotify:playlist:xyz",
        playlist_name="My Playlist",
        track_count=5,
        queue=queue,
        status="quota_failed",
    )

    # Raw metadata should have status field
    ep = episodes.get_episode(TEST_USER_ID, ep_id)
    assert ep is not None
    assert ep.get("status") == "quota_failed", f"Expected 'quota_failed', got {ep.get('status')}"
    assert ep["queue"] == queue

    # list_episodes must expose the status field
    lst = episodes.list_episodes(TEST_USER_ID)
    found = next((e for e in lst if e["id"] == ep_id), None)
    assert found is not None, "Quota-failed episode must appear in list"
    assert found.get("status") == "quota_failed", "list_episodes must expose status"

    # Rename must preserve status
    updated = episodes.rename_episode(TEST_USER_ID, ep_id, "Renamed Incomplete")
    assert updated is not None
    assert updated.get("status") == "quota_failed", "rename must not clear status"

    # Normal complete episode must default to 'complete'
    episodes.save_episode(
        user_id=TEST_USER_ID,
        episode_id="complete-ep-001",
        name="Full Cast",
        playlist_uri="spotify:playlist:xyz",
        playlist_name="My Playlist",
        track_count=5,
        queue=[],
    )
    complete_ep = episodes.get_episode(TEST_USER_ID, "complete-ep-001")
    assert complete_ep.get("status") == "complete", "Default status must be 'complete'"

    # Clean up
    episodes.delete_episode(TEST_USER_ID, ep_id)
    episodes.delete_episode(TEST_USER_ID, "complete-ep-001")
    print("  failed_episode_save ✓")


def _test_cooldown_guard_in_server():
    """Server module must have cooldown guard functions and GeminiTTSQuotaError catch."""
    import inspect
    import resonova.server as server_mod

    # GeminiTTSQuotaError must be imported
    assert hasattr(server_mod, "GeminiTTSQuotaError"), "GeminiTTSQuotaError must be importable from server"

    # Cooldown functions must exist
    assert hasattr(server_mod, "_get_tts_cooldown"), "_get_tts_cooldown must exist"
    assert hasattr(server_mod, "_set_tts_cooldown"), "_set_tts_cooldown must exist"
    server_mod._set_tts_cooldown(60, "gemini-3.1-flash-tts")
    cooldown = server_mod._get_tts_cooldown()
    assert cooldown is not None
    assert cooldown["model"] == "gemini-3.1-flash-tts"

    # _run_generation must handle GeminiTTSQuotaError
    src = inspect.getsource(server_mod._run_generation)
    assert "GeminiTTSQuotaError" in src, "_run_generation must catch GeminiTTSQuotaError"
    assert "_set_tts_cooldown" in src, "_run_generation must call _set_tts_cooldown"
    assert "status=\"quota_failed\"" in src or "status='quota_failed'" in src, (
        "_run_generation must save episode with status='quota_failed'"
    )

    # generate route must check cooldown
    src_gen = inspect.getsource(server_mod.generate)
    assert "_get_tts_cooldown" in src_gen, "generate route must check cooldown"

    print("  cooldown_guard_in_server ✓")


def _test_generate_route_accepts_json_body():
    """FastAPI must parse /generate payload as JSON body, not query parameter req."""
    from fastapi.testclient import TestClient
    import resonova.server as server_mod

    route = next(
        r for r in server_mod.app.routes
        if getattr(r, "path", None) == "/generate"
    )
    body_names = [param.name for param in route.dependant.body_params]
    query_names = [param.name for param in route.dependant.query_params]

    assert "req" in body_names, "/generate must accept req from JSON body"
    assert "req" not in query_names, "/generate must not require query parameter req"

    original_get_current_token = server_mod.spotify_api.get_current_token
    try:
        server_mod.spotify_api.get_current_token = lambda: None
        response = TestClient(server_mod.app).post(
            "/generate",
            json={
                "playlist_uri": "spotify:playlist:test001",
                "commentary_language": "Mandarin Chinese",
            },
        )
        assert response.status_code == 401, (
            f"Expected JSON body to reach endpoint auth check, got {response.status_code}: "
            f"{response.text}"
        )
        assert "query" not in response.text, "Generate JSON body must not fail as missing query req"
    finally:
        server_mod.spotify_api.get_current_token = original_get_current_token

    print("  generate_route_accepts_json_body ✓")


def _test_playlist_card_quick_generate():
    """Playlist cards quick-generate via the form submit handler, which reads the
    current language/incognito options — so the one-click action still respects them."""
    import re

    src = (Path(__file__).parent.parent / "resonova/web/player.js").read_text(encoding="utf-8")
    match = re.search(r"_handlePlaylistClick\(uri\) \{(?P<body>.*?)\n  \}", src, re.S)
    assert match, "_handlePlaylistClick must exist"
    body = match.group("body")

    assert "requestSubmit" in body, (
        "Playlist-card clicks should quick-generate (requestSubmit) — the form submit handler "
        "calls generate(), which reads the language/incognito options, so they are respected."
    )

    print("  playlist_card_quick_generate ✓")


def _test_replay_tracking_frontend_shape():
    """Saved-cast replay tracking should be opt-in and non-blocking in player.js."""
    src = (Path(__file__).parent.parent / "resonova/web/player.js").read_text(encoding="utf-8")

    assert "replayEpisodeId" in src, "saved-cast playback must opt in to replay tracking"
    assert "_maybeReportMeaningfulReplay" in src, "frontend must report meaningful replay threshold"
    assert "completedItems / total < 0.5" in src, "meaningful replay threshold must be 50%"
    assert "event: 'start'" in src and "event: 'meaningful'" in src, (
        "frontend must send both start and meaningful replay events"
    )
    assert "Replayed ${ep.replay_count}x" in src, "episode cards must render replay counts"

    print("  replay_tracking_frontend_shape ✓")


def _test_mobile_hidden_spotify_attempts_before_deferring():
    """Hidden mobile playback should try Spotify before falling back to unlock/return copy."""
    src = (Path(__file__).parent.parent / "resonova/web/player.js").read_text(encoding="utf-8")

    assert "play:spotify:pending-unlock" not in src, (
        "Spotify segments should not be preemptively deferred just because the page is hidden."
    )
    assert "play:spotify:connect-missing-hidden" in src, (
        "Hidden-page Spotify Connect failure still needs a fallback that resumes on foreground."
    )

    print("  mobile_hidden_spotify_attempts_before_deferring ✓")


def _test_taste_bias_works(variety):
    """With a taste bundle whose artist_affinity contains a specific artist,
    that artist's track should open notably more often than without taste."""
    # Create tracks with one distinctive artist to bias toward
    fake_uri = "spotify:track:favorite"
    tracks = [FakeTrack(f"spotify:track:{i}", f"Artist{i}", f"Album{i}", popularity=50) for i in range(12)]
    tracks.append(FakeTrack(fake_uri, "FavoriteArtist", "FavAlbum", popularity=80))
    # Total 13 tracks, max 8 — the fav artist track is one of many
    playlist_uri = "spotify:playlist:taste_bias"
    max_tracks = 8

    taste = {"artist_affinity": {"favoriteartist"}}

    # Run many times without taste
    bias_count = 0
    total_runs = 50
    for _ in range(total_runs):
        selected = variety.select_tracks_for_episode(tracks, playlist_uri, max_tracks, user_id=TEST_USER_ID)
        if selected and selected[0].uri == fake_uri:
            bias_count += 1
    no_taste_count = bias_count

    # Run many times with taste
    bias_count = 0
    for _ in range(total_runs):
        selected = variety.select_tracks_for_episode(tracks, playlist_uri, max_tracks, taste=taste, user_id=TEST_USER_ID)
        if selected and selected[0].uri == fake_uri:
            bias_count += 1
    taste_count = bias_count

    # The taste-bias runs should open with FavoriteArtist notably more often
    # (statistical, not every run).  With 20 random candidates and a small
    # reward (-8), the effect is modest but measurable over 50 trials.
    print(f"  taste_bias: no_taste={no_taste_count}/{total_runs}, taste={taste_count}/{total_runs}")
    assert taste_count > no_taste_count, (
        f"Expected taste to increase opener rate, got {taste_count} vs {no_taste_count}"
    )
    print("  taste_bias_works ✓")


def _test_taste_still_varied(variety):
    """Even with the same taste, order fingerprints must differ across runs."""
    tracks = [FakeTrack(f"spotify:track:{i}", f"Artist{i}", f"Album{i}", popularity=50) for i in range(20)]
    playlist_uri = "spotify:playlist:taste_varied"
    max_tracks = 8
    taste = {"artist_affinity": {"artist1", "artist3", "artist5"}}

    seen_fingerprints = set()
    for _ in range(30):
        selected = variety.select_tracks_for_episode(tracks, playlist_uri, max_tracks, taste=taste, user_id=TEST_USER_ID)
        fp = variety.compute_fingerprint([t.uri for t in selected])
        seen_fingerprints.add(fp)

    assert len(seen_fingerprints) > 1, (
        f"Expected multiple distinct orders with taste bias, got only {len(seen_fingerprints)}"
    )
    print(f"  taste_still_varied: {len(seen_fingerprints)} distinct orders across 30 runs ✓")


def _test_no_taste_unchanged(variety):
    """With taste=None, the selection behaves exactly as before — same scoring."""
    tracks = [FakeTrack(f"spotify:track:{i}", f"Artist{i % 4}", f"Album{i % 6}", popularity=50) for i in range(20)]
    playlist_uri = "spotify:playlist:no_taste"
    max_tracks = 8

    # Seed the RNG so we get repeatable sequences
    import random as rng_mod
    rng_mod.seed(42)
    selected_seeded = variety.select_tracks_for_episode(tracks, playlist_uri, max_tracks, taste=None, user_id=TEST_USER_ID)
    seeded_order = [t.uri for t in selected_seeded]

    rng_mod.seed(42)
    selected_old = variety.select_tracks_for_episode(tracks, playlist_uri, max_tracks, user_id=TEST_USER_ID)
    old_order = [t.uri for t in selected_old]

    assert seeded_order == old_order, (
        "taste=None and no taste arg should produce identical output with same RNG seed"
    )
    print("  no_taste_unchanged ✓")


if __name__ == "__main__":
    _run_tests()
