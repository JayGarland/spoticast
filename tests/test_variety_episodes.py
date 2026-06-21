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


if __name__ == "__main__":
    _run_tests()
