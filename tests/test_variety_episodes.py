"""
Smoke tests for variety.py and episodes.py pure functions.

Run with:
    uv run python tests/test_variety_episodes.py

No Spotify / Gemini network calls required.
"""
from __future__ import annotations

import json
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


# ---------------------------------------------------------------------------
# Patch variety._VARIETY_DIR and episodes._EPISODES_DIR to a temp dir
# ---------------------------------------------------------------------------

def _run_tests() -> None:
    import resonova.variety as variety
    import resonova.episodes as episodes

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        variety._VARIETY_DIR = tmp_path / "variety"
        episodes._EPISODES_DIR = tmp_path / "episodes"

        _test_fingerprint_stable()
        _test_select_produces_variety(variety)
        _test_select_short_playlist(variety)
        _test_pasted_track_order_not_affected()
        _test_save_variety_memory(variety)
        _test_episodes_lifecycle(episodes)
        _test_episodes_backward_compat(episodes)
        _test_run_number(episodes)
        _test_episode_path_traversal_rejected(episodes)
        _test_server_track_ready_metadata_shape()
        _test_quota_error_classification()
        _test_retry_after_formatting()
        _test_failed_episode_save(episodes)
        _test_generate_route_accepts_json_body()
        _test_cooldown_guard_in_server()

    print("All tests passed ✓")


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
        selected = variety.select_tracks_for_episode(tracks, playlist_uri, max_tracks)
        assert len(selected) == max_tracks, f"Expected {max_tracks} tracks, got {len(selected)}"
        fp = variety.compute_fingerprint([t.uri for t in selected])
        seen_fingerprints.add(fp)
        variety.save_variety_memory(playlist_uri, [t.uri for t in selected])

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
        variety.save_variety_memory(playlist_uri, [t.uri for t in tracks])  # fill memory
    selected = variety.select_tracks_for_episode(tracks, playlist_uri, 5)
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

    variety.save_variety_memory(playlist_uri, uris_a)
    mem = variety.load_variety_memory(playlist_uri)
    assert len(mem["recent_orders"]) == 1
    assert mem["recent_orders"][0]["track_uris"] == uris_a

    # Fill to max + 2 and confirm cap
    for i in range(variety._MAX_RECENT + 2):
        variety.save_variety_memory(playlist_uri, [f"spotify:track:cap{i}_{j}" for j in range(3)])
    mem = variety.load_variety_memory(playlist_uri)
    assert len(mem["recent_orders"]) == variety._MAX_RECENT, (
        f"Expected {variety._MAX_RECENT} orders, got {len(mem['recent_orders'])}"
    )
    print("  save_variety_memory ✓")


def _test_episodes_lifecycle(episodes):
    ep_id = "test-ep-001"
    queue = [{"type": "audio", "url": "/audio/ep/intro.mp3"}]
    episodes.save_episode(
        episode_id=ep_id,
        name="Test Episode",
        playlist_uri="spotify:playlist:abc",
        playlist_name="My Playlist",
        track_count=5,
        queue=queue,
        order_fingerprint="abc12345",
        track_order_preview=["Artist A – Track 1", "Artist B – Track 2"],
    )

    ep = episodes.get_episode(ep_id)
    assert ep is not None
    assert ep["name"] == "Test Episode"
    assert ep["order_fingerprint"] == "abc12345"
    assert ep["track_order_preview"][0] == "Artist A – Track 1"

    # List episodes
    lst = episodes.list_episodes()
    assert any(e["id"] == ep_id for e in lst)
    found = next(e for e in lst if e["id"] == ep_id)
    assert found["order_fingerprint"] == "abc12345"
    assert found["track_order_preview"] == ["Artist A – Track 1", "Artist B – Track 2"]

    # Rename
    updated = episodes.rename_episode(ep_id, "  Renamed Episode  ")
    assert updated is not None
    assert updated["name"] == "Renamed Episode"
    ep2 = episodes.get_episode(ep_id)
    assert ep2["name"] == "Renamed Episode"

    # Delete
    deleted = episodes.delete_episode(ep_id)
    assert deleted is True
    assert episodes.get_episode(ep_id) is None
    deleted_again = episodes.delete_episode(ep_id)
    assert deleted_again is False

    print("  episodes_lifecycle ✓")


def _test_episodes_backward_compat(episodes):
    """Old episodes without new fields must still load and list without error."""
    ep_id = "old-ep-001"
    ep_dir = episodes._EPISODES_DIR / ep_id
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

    lst = episodes.list_episodes()
    found = next((e for e in lst if e["id"] == ep_id), None)
    assert found is not None, "Old episode must appear in list"
    assert found.get("order_fingerprint") is None, "order_fingerprint should be None for old episodes"
    assert found.get("track_order_preview") is None, "track_order_preview should be None for old episodes"
    assert found["run_number"] >= 1, "run_number must be assigned"
    print("  episodes_backward_compat ✓")


def _test_run_number(episodes):
    """Episodes from the same playlist should get sequential run numbers."""
    import time
    playlist_uri = "spotify:playlist:runtest"
    for i in range(3):
        episodes.save_episode(
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
        episode_id="run-ep-other",
        name="Other",
        playlist_uri="spotify:playlist:other",
        playlist_name="Other Playlist",
        track_count=2,
        queue=[],
    )

    lst = episodes.list_episodes()
    run_eps = sorted(
        [e for e in lst if e["playlist_uri"] == playlist_uri],
        key=lambda e: e["created_at"],
    )
    run_numbers = [e["run_number"] for e in run_eps]
    assert run_numbers == [1, 2, 3], f"Expected [1, 2, 3], got {run_numbers}"

    other_ep = next(e for e in lst if e["id"] == "run-ep-other")
    assert other_ep["run_number"] == 1, "Different playlist → independent run number"
    print("  run_number ✓")


def _test_episode_path_traversal_rejected(episodes):
    """Episode mutation helpers must stay scoped to generated/episodes."""
    for bad_id in ("../escape", "..\\escape", "/tmp/escape"):
        try:
            episodes.get_episode(bad_id)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected ValueError for get_episode({bad_id!r})")

        try:
            episodes.rename_episode(bad_id, "Bad")
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected ValueError for rename_episode({bad_id!r})")

        try:
            episodes.delete_episode(bad_id)
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
        episode_id=ep_id,
        name="Incomplete Cast",
        playlist_uri="spotify:playlist:xyz",
        playlist_name="My Playlist",
        track_count=5,
        queue=queue,
        status="quota_failed",
    )

    # Raw metadata should have status field
    ep = episodes.get_episode(ep_id)
    assert ep is not None
    assert ep.get("status") == "quota_failed", f"Expected 'quota_failed', got {ep.get('status')}"
    assert ep["queue"] == queue

    # list_episodes must expose the status field
    lst = episodes.list_episodes()
    found = next((e for e in lst if e["id"] == ep_id), None)
    assert found is not None, "Quota-failed episode must appear in list"
    assert found.get("status") == "quota_failed", "list_episodes must expose status"

    # Rename must preserve status
    updated = episodes.rename_episode(ep_id, "Renamed Incomplete")
    assert updated is not None
    assert updated.get("status") == "quota_failed", "rename must not clear status"

    # Normal complete episode must default to 'complete'
    episodes.save_episode(
        episode_id="complete-ep-001",
        name="Full Cast",
        playlist_uri="spotify:playlist:xyz",
        playlist_name="My Playlist",
        track_count=5,
        queue=[],
    )
    complete_ep = episodes.get_episode("complete-ep-001")
    assert complete_ep.get("status") == "complete", "Default status must be 'complete'"

    # Clean up
    episodes.delete_episode(ep_id)
    episodes.delete_episode("complete-ep-001")
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
            json={"playlist_uri": "spotify:playlist:test001"},
        )
        assert response.status_code == 401, (
            f"Expected JSON body to reach endpoint auth check, got {response.status_code}: "
            f"{response.text}"
        )
        assert "query" not in response.text, "Generate JSON body must not fail as missing query req"
    finally:
        server_mod.spotify_api.get_current_token = original_get_current_token

    print("  generate_route_accepts_json_body ✓")


if __name__ == "__main__":
    _run_tests()
