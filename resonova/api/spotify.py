"""Spotify OAuth and data fetching."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from pathlib import Path

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from resonova.config import settings

_OAUTH_CACHE = ".research_cache/.spotify_oauth"

# Module-level OAuth manager (stateful: caches token to .research_cache/.spotify_oauth)
_oauth: SpotifyOAuth | None = None
_client: spotipy.Spotify | None = None

# In-memory caches keyed by URI — survive across regenerations within the same process
_track_cache: dict[str, TrackInfo] = {}
_features_cache: dict[str, AudioFeatures] = {}


def get_oauth(redirect_uri: str | None = None) -> SpotifyOAuth:
    global _oauth
    # When an explicit redirect_uri is provided (e.g. from a request's Host
    # header), create a fresh OAuth instance so the redirect_uri matches the
    # access URL.  The cached instance is only used for the default URI.
    if redirect_uri is not None:
        Path(_OAUTH_CACHE).parent.mkdir(parents=True, exist_ok=True)
        return SpotifyOAuth(
            client_id=settings.spotify_client_id,
            client_secret=settings.spotify_client_secret,
            redirect_uri=redirect_uri,
            scope=settings.spotify_scopes,
            open_browser=False,
            cache_path=_OAUTH_CACHE,
        )
    if _oauth is None:
        Path(_OAUTH_CACHE).parent.mkdir(parents=True, exist_ok=True)
        _oauth = SpotifyOAuth(
            client_id=settings.spotify_client_id,
            client_secret=settings.spotify_client_secret,
            redirect_uri=settings.redirect_uri,
            scope=settings.spotify_scopes,
            open_browser=False,
            cache_path=_OAUTH_CACHE,
        )
    return _oauth


def get_client() -> spotipy.Spotify:
    global _client
    oauth = get_oauth()
    token_info = oauth.get_cached_token()
    if not token_info:
        raise RuntimeError("Not authenticated — no cached token")
    if oauth.is_token_expired(token_info):
        token_info = oauth.refresh_access_token(token_info["refresh_token"])
    _client = spotipy.Spotify(auth=token_info["access_token"], requests_timeout=15)
    return _client


def get_auth_url(redirect_uri: str | None = None) -> str:
    return get_oauth(redirect_uri).get_authorize_url()


def handle_callback(code: str, redirect_uri: str | None = None) -> dict:
    oauth = get_oauth(redirect_uri)
    token_info = oauth.get_access_token(code, as_dict=True)
    return token_info


def get_current_token() -> str | None:
    oauth = get_oauth()
    token_info = oauth.get_cached_token()
    if not token_info:
        return None
    if oauth.is_token_expired(token_info):
        try:
            token_info = oauth.refresh_access_token(token_info["refresh_token"])
        except Exception:
            return None
    return token_info["access_token"]


@dataclass
class TrackInfo:
    uri: str
    name: str
    artist: str
    album: str
    release_year: str
    duration_ms: int
    popularity: int


@dataclass
class AudioFeatures:
    uri: str
    energy: float
    valence: float
    danceability: float
    tempo: float
    key: int
    mode: int  # 0 = minor, 1 = major
    acousticness: float
    instrumentalness: float


@dataclass
class UserContext:
    top_tracks_short: list[str]   # track URIs
    top_tracks_medium: list[str]
    top_tracks_long: list[str]
    top_artists_short: list[str]  # artist names
    top_artists_medium: list[str]
    top_artists_long: list[str]
    recently_played: list[str]    # track URIs
    top_genres: list[str]         # frequency-ranked, de-duplicated genre strings


_KEY_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _parse_track(item: dict) -> TrackInfo:
    # Spotify API has two response shapes for playlist items:
    #   Old: {"track": {actual_track_object}}  — "track" is a nested dict
    #   New: {"track": true, "artists": [...], ...}  — "track" is a bool type flag,
    #        and the actual track fields are at the top level of `item`.
    # For /tracks (sp.tracks()), there is no "track" key at all.
    raw = item.get("track", item)
    track = raw if isinstance(raw, dict) else item
    artists = ", ".join(a["name"] for a in track["artists"])
    release_date = track["album"].get("release_date", "")
    year = release_date[:4] if release_date else "Unknown"
    return TrackInfo(
        uri=track["uri"],
        name=track["name"],
        artist=artists,
        album=track["album"]["name"],
        release_year=year,
        duration_ms=track["duration_ms"],
        popularity=track.get("popularity", 0),
    )


def fetch_playlist_name(playlist_uri: str) -> str:
    """Fetch just the playlist name — lightweight single API call."""
    sp = get_client()
    result = sp.playlist(playlist_uri, fields="name")
    return result.get("name", "")


def fetch_playlist(playlist_uri: str) -> list[TrackInfo]:
    sp = get_client()
    tracks: list[TrackInfo] = []
    results = sp.playlist_tracks(playlist_uri, limit=100)
    while results:
        for item in results["items"]:
            if item and item.get("item") and item["item"].get("uri"):
                if not item["item"]["uri"].startswith("spotify:local:"):
                    t = _parse_track(item["item"])
                    _track_cache[t.uri] = t
                    tracks.append(t)
        results = sp.next(results) if results.get("next") else None
    return tracks


def fetch_tracks(track_uris: list[str]) -> list[TrackInfo]:
    """Fetch track metadata for a list of track URIs, using cache where possible."""
    sp = get_client()
    tracks: list[TrackInfo] = []
    uncached: list[tuple[int, str]] = []  # (index, uri)
    # Pre-fill from cache
    for i, uri in enumerate(track_uris):
        if uri in _track_cache:
            tracks.append(_track_cache[uri])
        else:
            tracks.append(None)  # type: ignore[arg-type]
            uncached.append((i, uri))
    # Batch-fetch uncached in groups of 50
    for batch_start in range(0, len(uncached), 50):
        batch = uncached[batch_start:batch_start + 50]
        ids = [uri.split(":")[-1] for _, uri in batch]
        results = sp.tracks(ids)
        if not results:
            continue
        for (idx, uri), t in zip(batch, results["tracks"]):
            if t and t.get("uri"):
                info = _parse_track(t)
                _track_cache[info.uri] = info
                tracks[idx] = info
    return [t for t in tracks if t is not None]


def fetch_audio_features(track_uris: list[str]) -> dict[str, AudioFeatures]:
    """Audio-features endpoint is deprecated (403 for Dev Mode apps) — skip network call.

    Returns an empty dict. Downstream code already handles empty features gracefully.
    """
    return {}


def fetch_user_context() -> UserContext:
    """Best-effort personalization fetch.

    Each Spotify sub-call is individually wrapped in try/except so a single
    ReadTimeout or transient error yields [] for THAT signal instead of
    aborting the entire fetch.  Returns a valid (possibly empty) UserContext.
    """
    import logging
    _log = logging.getLogger(__name__)
    sp = get_client()

    def _top_tracks(term: str) -> list[str]:
        try:
            r = sp.current_user_top_tracks(limit=50, time_range=term)
            return [t["uri"] for t in r["items"]] if r else []
        except Exception as exc:
            _log.warning("top_tracks(%s) failed (%s) — returning []", term, exc)
            return []

    def _top_artists(term: str) -> tuple[list[str], list[str]]:
        try:
            r = sp.current_user_top_artists(limit=50, time_range=term)
            if not r:
                return [], []
            names = [a["name"] for a in r["items"]]
            all_genres: list[str] = []
            for a in r["items"]:
                all_genres.extend(a.get("genres") or [])
            return names, all_genres
        except Exception as exc:
            _log.warning("top_artists(%s) failed (%s) — returning []", term, exc)
            return [], []

    def _recent() -> list[str]:
        try:
            r = sp.current_user_recently_played(limit=50)
            return [item["track"]["uri"] for item in r["items"]] if r else []
        except Exception as exc:
            _log.warning("recently_played failed (%s) — returning []", exc)
            return []

    names_short, genres_short = _top_artists("short_term")
    names_medium, genres_medium = _top_artists("medium_term")
    names_long, genres_long = _top_artists("long_term")

    # Aggregate genres across all time ranges, frequency-ranked, de-duplicated
    genre_counter: Counter = Counter()
    for g in genres_short:
        genre_counter[g] += 1
    for g in genres_medium:
        genre_counter[g] += 1
    for g in genres_long:
        genre_counter[g] += 1
    aggregated_genres = [g for g, _ in genre_counter.most_common()]

    return UserContext(
        top_tracks_short=_top_tracks("short_term"),
        top_tracks_medium=_top_tracks("medium_term"),
        top_tracks_long=_top_tracks("long_term"),
        top_artists_short=names_short,
        top_artists_medium=names_medium,
        top_artists_long=names_long,
        recently_played=_recent(),
        top_genres=aggregated_genres,
    )


def fetch_saved_tracks(limit_total: int = 200) -> list[dict]:
    """Fetch the user's liked/saved tracks (user-library-read scope).

    Returns a list of dicts with artist_names and added_at, ordered newest-first
    (Spotify returns them in that order). Capped at *limit_total*.
    Degrades gracefully on 401/403: returns [].
    """
    import logging
    _log = logging.getLogger(__name__)
    try:
        sp = get_client()
        results: list[dict] = []
        page_size = 50
        offset = 0
        while len(results) < limit_total:
            batch = sp.current_user_saved_tracks(limit=page_size, offset=offset)
            if not batch or not batch.get("items"):
                break
            for item in batch["items"]:
                if len(results) >= limit_total:
                    break
                track = item.get("track")
                if not track:
                    continue
                results.append({
                    "artist_names": [a["name"] for a in track.get("artists", [])],
                    "added_at": item.get("added_at", ""),
                })
            if not batch.get("next"):
                break
            offset += page_size
        return results
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(
            "fetch_saved_tracks unavailable (%s) — returning empty", exc
        )
        return []


def fetch_followed_artists(limit_total: int = 200) -> list[str]:
    """Fetch the artist names the user follows (user-follow-read scope).

    Cursor-paginated (after cursor). Capped at *limit_total*.
    Degrades gracefully on 401/403: returns [].
    Returns a list of artist name strings.
    """
    try:
        sp = get_client()
        results: list[str] = []
        page_size = 50
        after: str | None = None
        while len(results) < limit_total:
            # spotipy's current_user_followed_artists(limit, after) hardcodes
            # type=artist internally and does NOT accept a `type` kwarg — passing
            # one raises TypeError, which the except below swallowed, so this fetch
            # silently returned [] for every user. Do not re-add `type` here.
            kwargs: dict = {"limit": page_size}
            if after:
                kwargs["after"] = after
            batch = sp.current_user_followed_artists(**kwargs)
            if not batch:
                break
            artists_page = batch.get("artists", {})
            items = artists_page.get("items", [])
            if not items:
                break
            for artist in items:
                if len(results) >= limit_total:
                    break
                results.append(artist["name"])
            cursor = artists_page.get("cursors", {})
            after = cursor.get("after")
            if not after:
                break
        return results
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(
            "fetch_followed_artists unavailable (%s) — returning empty", exc
        )
        return []


def fetch_recent_plays() -> list[dict]:
    sp = get_client()
    results = sp.current_user_recently_played(limit=50)
    if not results:
        return []
    seen: set[str] = set()
    playlists: list[dict] = []
    for item in results["items"]:
        ctx = item.get("context")
        if not ctx or ctx.get("type") != "playlist":
            continue
        uri = ctx["uri"]
        if uri in seen:
            continue
        seen.add(uri)
        try:
            pl = sp.playlist(
                uri,
                fields="uri,name,images,owner.display_name,tracks.total",
            )
            images = pl.get("images", [])
            playlists.append({
                "uri": pl["uri"],
                "name": pl["name"],
                "image": images[0]["url"] if images else None,
                "track_count": pl.get("tracks", {}).get("total", 0),
                "owner": pl["owner"]["display_name"],
            })
        except Exception:
            # Algorithmic playlists (DW, RR, Daily Mixes) return 404 — skip
            continue
    return playlists


def fetch_featured_playlists() -> list[dict]:
    """Return Spotify-curated playlists from the user's library."""
    sp = get_client()
    # Owners known to be Spotify editorial / algorithmic curators
    curated_owners = {"spotify"}
    playlists: list[dict] = []
    results = sp.current_user_playlists(limit=50)
    while results:
        for item in results["items"]:
            owner = item["owner"]["display_name"].lower()
            if owner in curated_owners:
                images = item.get("images", [])
                playlists.append({
                    "uri": item["uri"],
                    "name": item["name"],
                    "description": item.get("description", ""),
                    "image": images[0]["url"] if images else None,
                    "track_count": item.get("tracks", {}).get("total", 0),
                    "owner": item["owner"]["display_name"],
                })
        results = sp.next(results) if results.get("next") else None
    return playlists


def current_user_id() -> str | None:
    """Return the connected Spotify user's id, or None if unavailable.

    Used by the single-user guard to detect a foreign account connecting to an
    instance that already belongs to someone else.
    """
    try:
        sp = get_client()
        me = sp.current_user()
        return me.get("id") if me else None
    except Exception as exc:  # noqa: BLE001 - identity check must fail closed
        import logging
        logging.getLogger(__name__).warning("current_user_id unavailable (%s)", exc)
        return None


def fetch_user_playlists(limit: int = 50, offset: int = 0) -> dict:
    """Return a page of playlists owned by the current user (not followed ones)."""
    sp = get_client()
    me = sp.current_user()
    my_id = me["id"]
    results = sp.current_user_playlists(limit=limit, offset=offset)
    items: list[dict] = []
    for item in results["items"]:
        if item["owner"]["id"] != my_id:
            continue
        images = item.get("images", [])
        items.append({
            "uri": item["uri"],
            "name": item["name"],
            "description": item.get("description", ""),
            "image": images[0]["url"] if images else None,
            "track_count": item.get("tracks", {}).get("total", 0),
            "owner": item["owner"]["display_name"],
        })
    return {
        "items": items,
        "total": results["total"],
        "offset": offset,
        "limit": limit,
    }


def build_playlist_context(
    tracks: list[TrackInfo],
    features: dict[str, AudioFeatures],
    user_ctx: UserContext,
) -> dict[str, Any]:
    """Combine Spotify data into a compact context dict for script generation."""
    all_top_uris = set(
        user_ctx.top_tracks_short
        + user_ctx.top_tracks_medium
        + user_ctx.top_tracks_long
    )
    all_top_artists = set(
        user_ctx.top_artists_short
        + user_ctx.top_artists_medium
        + user_ctx.top_artists_long
    )
    recent_set = set(user_ctx.recently_played)

    track_data = []
    for t in tracks:
        feat = features.get(t.uri)
        track_data.append({
            "uri": t.uri,
            "name": t.name,
            "artist": t.artist,
            "album": t.album,
            "year": t.release_year,
            "duration_s": round(t.duration_ms / 1000),
            "popularity": t.popularity,
            "is_personal_favorite": t.uri in all_top_uris,
            "recently_played": t.uri in recent_set,
            "artist_in_top": any(
                a.strip() in all_top_artists for a in t.artist.split(",")
            ),
            "features": {
                "energy": round(feat.energy, 2),
                "valence": round(feat.valence, 2),
                "danceability": round(feat.danceability, 2),
                "tempo": round(feat.tempo),
                "key": _KEY_NAMES[feat.key] if feat.key >= 0 else "?",
                "mode": "major" if feat.mode == 1 else "minor",
                "acousticness": round(feat.acousticness, 2),
                "instrumentalness": round(feat.instrumentalness, 2),
            } if feat else None,
        })

    feat_values = [f for f in features.values()]
    avg = lambda key: round(sum(getattr(f, key) for f in feat_values) / len(feat_values), 2) if feat_values else None

    return {
        "tracks": track_data,
        "summary": {
            "total_tracks": len(tracks),
            "personal_favorites_count": sum(1 for t in track_data if t["is_personal_favorite"]),
            "avg_energy": avg("energy"),
            "avg_valence": avg("valence"),
            "avg_danceability": avg("danceability"),
            "avg_tempo": avg("tempo"),
        },
        "listener_profile": {
            "top_artists_all_time": list(all_top_artists)[:20],
            "recently_played_count": len(recent_set),
            "spotify_genres": user_ctx.top_genres,
        },
    }
