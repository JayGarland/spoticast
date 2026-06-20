"""Memory-aware playlist track selection to improve episode variety."""

from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_VARIETY_DIR = Path("generated") / "variety"
_MAX_RECENT = 5
_NUM_CANDIDATES = 20


def _safe_playlist_key(playlist_uri: str) -> str:
    return hashlib.sha1(playlist_uri.encode()).hexdigest()


def compute_fingerprint(track_uris: list[str]) -> str:
    """Return a short stable fingerprint for an ordered list of track URIs."""
    return hashlib.sha1("|".join(track_uris).encode()).hexdigest()[:8]


def _variety_path(playlist_uri: str) -> Path:
    return _VARIETY_DIR / f"{_safe_playlist_key(playlist_uri)}.json"


def load_variety_memory(playlist_uri: str) -> dict:
    path = _variety_path(playlist_uri)
    if not path.exists():
        return {"playlist_uri": playlist_uri, "recent_orders": []}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {"playlist_uri": playlist_uri, "recent_orders": []}


def save_variety_memory(playlist_uri: str, selected_uris: list[str]) -> None:
    """Persist a selected order to memory. Call after successful episode save."""
    _VARIETY_DIR.mkdir(parents=True, exist_ok=True)
    memory = load_variety_memory(playlist_uri)
    recent = memory.get("recent_orders", [])
    recent.append({
        "created_at": datetime.now(timezone.utc).isoformat(),
        "track_uris": selected_uris,
        "fingerprint": compute_fingerprint(selected_uris),
    })
    memory["recent_orders"] = recent[-_MAX_RECENT:]
    _variety_path(playlist_uri).write_text(json.dumps(memory, indent=2))


def _score_candidate(
    candidate_uris: list[str],
    recent_fingerprints: set[str],
    recent_openers: set[str],
    recent_closers: set[str],
    recently_used_uris: set[str],
    tracks_by_uri: dict[str, Any],
) -> int:
    """Lower score = better candidate."""
    score = 0

    if compute_fingerprint(candidate_uris) in recent_fingerprints:
        score += 1000

    if candidate_uris and candidate_uris[0] in recent_openers:
        score += 20

    if candidate_uris and candidate_uris[-1] in recent_closers:
        score += 10

    for uri in candidate_uris:
        if uri in recently_used_uris:
            score += 1

    # Penalise adjacent same-artist or same-album
    for i in range(len(candidate_uris) - 1):
        t1 = tracks_by_uri.get(candidate_uris[i])
        t2 = tracks_by_uri.get(candidate_uris[i + 1])
        if t1 and t2:
            if t1.artist == t2.artist:
                score += 5
            elif t1.album == t2.album:
                score += 2

    return score


def _repair_adjacency(uris: list[str], tracks_by_uri: dict[str, Any]) -> list[str]:
    """Light swap pass to reduce same-artist back-to-back placement."""
    result = list(uris)
    for i in range(len(result) - 1):
        t1 = tracks_by_uri.get(result[i])
        t2 = tracks_by_uri.get(result[i + 1])
        if t1 and t2 and t1.artist == t2.artist:
            for j in range(i + 2, min(i + 6, len(result))):
                t3 = tracks_by_uri.get(result[j])
                if t3 and t3.artist != t1.artist:
                    result[i + 1], result[j] = result[j], result[i + 1]
                    break
    return result


def select_tracks_for_episode(
    tracks: list[Any],
    playlist_uri: str,
    max_tracks: int,
) -> list[Any]:
    """
    Return a memory-aware varied order of tracks for a playlist episode.

    Tracks must have .uri, .artist, .album attributes (SpotifyTrackInfo).
    Pasted track-list inputs bypass this function entirely (handled in server.py).
    """
    if not tracks:
        return []

    tracks_by_uri: dict[str, Any] = {t.uri: t for t in tracks}
    memory = load_variety_memory(playlist_uri)
    recent_orders = memory.get("recent_orders", [])

    recent_fingerprints = {o["fingerprint"] for o in recent_orders if o.get("fingerprint")}
    recent_openers = {o["track_uris"][0] for o in recent_orders if o.get("track_uris")}
    recent_closers = {o["track_uris"][-1] for o in recent_orders if o.get("track_uris")}

    recently_used_uris: set[str] = set()
    for o in recent_orders:
        recently_used_uris.update(o.get("track_uris", []))

    all_uris = [t.uri for t in tracks]
    # Only penalise recently-used track sets when playlist is bigger than max_tracks
    penalise_used = len(all_uris) > max_tracks

    best_candidate: list[str] | None = None
    best_score: float = float("inf")

    for _ in range(_NUM_CANDIDATES):
        shuffled = list(all_uris)
        random.shuffle(shuffled)
        candidate = shuffled[:max_tracks]
        candidate = _repair_adjacency(candidate, tracks_by_uri)
        score = _score_candidate(
            candidate,
            recent_fingerprints,
            recent_openers,
            recent_closers,
            recently_used_uris if penalise_used else set(),
            tracks_by_uri,
        )
        if score < best_score:
            best_score = score
            best_candidate = candidate
        if score < 20:
            break

    if best_candidate is None:
        best_candidate = all_uris[:max_tracks]

    return [tracks_by_uri[uri] for uri in best_candidate if uri in tracks_by_uri]
