"""Episode persistence for generated Resonova cast sessions."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

_EPISODES_DIR = Path("generated") / "episodes"


def _ensure_dir() -> Path:
    _EPISODES_DIR.mkdir(parents=True, exist_ok=True)
    return _EPISODES_DIR


def _episode_dir(episode_id: str) -> Path:
    episodes_base = _EPISODES_DIR.resolve()
    ep_dir = (_EPISODES_DIR / episode_id).resolve()
    try:
        ep_dir.relative_to(episodes_base)
    except ValueError as exc:
        raise ValueError("Invalid episode id") from exc
    return ep_dir


def episode_audio_dir(episode_id: str) -> str:
    """Return the relative path (from generated/) for an episode's audio files."""
    return f"episodes/{episode_id}"


def save_episode(
    episode_id: str,
    name: str,
    playlist_uri: str,
    playlist_name: str,
    track_count: int,
    queue: list[dict],
    order_fingerprint: str | None = None,
    track_order_preview: list[str] | None = None,
    status: str = "complete",
) -> None:
    """
    Persist episode metadata.

    order_fingerprint  — 8-char hash of the selected track URI order (playlist episodes only).
    track_order_preview — first few "Artist – Track" strings for UI distinction (optional).
    status             — "complete" for finished episodes; "quota_failed" for partial saves.
    """
    _ensure_dir()
    meta: dict = {
        "id": episode_id,
        "name": name,
        "playlist_uri": playlist_uri,
        "playlist_name": playlist_name,
        "track_count": track_count,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "queue": queue,
    }
    if order_fingerprint is not None:
        meta["order_fingerprint"] = order_fingerprint
    if track_order_preview is not None:
        meta["track_order_preview"] = track_order_preview

    path = _episode_dir(episode_id) / "episode.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meta, indent=2))


def record_replay_event(
    episode_id: str,
    event: str,
    session_id: str,
    completed_segments: int,
    total_segments: int,
) -> str | None:
    """Record a replay event for a saved episode.

    Returns an error string on failure, or None on success.
    Raises ValueError for invalid episode id or event type.
    """
    if event not in ("start", "meaningful"):
        raise ValueError(f"Invalid event type: {event!r}")
    if not session_id:
        raise ValueError("session_id must not be empty")

    path = _episode_dir(episode_id) / "episode.json"
    if not path.exists():
        return "not_found"

    meta = json.loads(path.read_text())
    now_iso = datetime.now(timezone.utc).isoformat()

    # Private dedupe tracking. Kept in episode.json, never returned by API helpers.
    _sessions = meta.setdefault("_replay_sessions", {})

    if event == "start":
        sess = _sessions.get(session_id, {})
        if not sess.get("start"):
            sess["start"] = True
            _sessions[session_id] = sess
            meta["replay_started_count"] = meta.get("replay_started_count", 0) + 1
            meta["last_started_at"] = now_iso

    elif event == "meaningful":
        if total_segments <= 0 or completed_segments / total_segments < 0.5:
            return None  # threshold not met
        sess = _sessions.get(session_id, {})
        if sess.get("meaningful"):
            return None  # already counted meaningful for this session
        sess["meaningful"] = True
        _sessions[session_id] = sess
        meta["replay_count"] = meta.get("replay_count", 0) + 1
        meta["last_replayed_at"] = now_iso

    path.write_text(json.dumps(meta, indent=2))
    return None


def _replay_summary(meta: dict) -> dict:
    """Extract replay fields with safe defaults for old episodes."""
    return {
        "replay_count": meta.get("replay_count", 0),
        "replay_started_count": meta.get("replay_started_count", 0),
        "last_replayed_at": meta.get("last_replayed_at"),
        "last_started_at": meta.get("last_started_at"),
    }


def _public_episode(meta: dict, include_queue: bool = False) -> dict:
    """Return episode metadata without private replay-session internals."""
    result = {
        "id": meta["id"],
        "name": meta["name"],
        "playlist_uri": meta.get("playlist_uri", ""),
        "playlist_name": meta.get("playlist_name", ""),
        "track_count": meta.get("track_count", 0),
        "created_at": meta["created_at"],
        "order_fingerprint": meta.get("order_fingerprint"),
        "track_order_preview": meta.get("track_order_preview"),
        "status": meta.get("status", "complete"),
    }
    if include_queue:
        result["queue"] = meta.get("queue", [])
    result.update(_replay_summary(meta))
    return result


def list_episodes() -> list[dict]:
    """Return episode summaries (no queue), newest first, with run numbers."""
    if not _EPISODES_DIR.exists():
        return []

    episodes: list[dict] = []
    for ep_dir in _EPISODES_DIR.iterdir():
        meta_path = ep_dir / "episode.json"
        if not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text())
        except Exception:
            continue
        episodes.append(_public_episode(meta))

    episodes.sort(key=lambda e: e["created_at"], reverse=True)

    # Compute per-playlist run number (1-based, oldest first)
    # Group by playlist_uri; assign run numbers by ascending created_at.
    from collections import defaultdict
    playlist_episodes: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for ep in episodes:
        uri = ep["playlist_uri"]
        playlist_episodes[uri].append((ep["id"], ep["created_at"]))

    run_number_map: dict[str, int] = {}
    for uri, items in playlist_episodes.items():
        sorted_items = sorted(items, key=lambda x: x[1])
        for rank, (ep_id, _) in enumerate(sorted_items, start=1):
            run_number_map[ep_id] = rank

    for ep in episodes:
        ep["run_number"] = run_number_map.get(ep["id"], 1)

    return episodes


def get_episode(episode_id: str) -> dict | None:
    path = _episode_dir(episode_id) / "episode.json"
    if not path.exists():
        return None
    return _public_episode(json.loads(path.read_text()), include_queue=True)


def rename_episode(episode_id: str, new_name: str) -> dict | None:
    """
    Rename an episode. Returns updated summary dict, or None if not found.
    Raises ValueError for invalid names.
    """
    name = new_name.strip()
    if not name:
        raise ValueError("Episode name must not be empty")

    path = _episode_dir(episode_id) / "episode.json"
    if not path.exists():
        return None

    meta = json.loads(path.read_text())
    meta["name"] = name
    path.write_text(json.dumps(meta, indent=2))

    return _public_episode(meta)


def delete_episode(episode_id: str) -> bool:
    """
    Delete an episode directory. Returns True if deleted, False if not found.
    Scoped to _EPISODES_DIR; raises ValueError on path traversal attempt.
    """
    ep_dir = _episode_dir(episode_id)
    if not ep_dir.exists():
        return False

    shutil.rmtree(ep_dir)
    return True
