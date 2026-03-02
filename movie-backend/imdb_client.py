"""
IMDB API Client — wraps api.imdbapi.dev (free, no key required)
Normalises responses into the internal movie dict shape used throughout the app.
Provides an in-process TTL cache to respect rate limits.
"""
import asyncio
import time
from functools import lru_cache
from typing import Optional
import httpx

BASE_URL = "https://api.imdbapi.dev"
POSTER_PLACEHOLDER = ""


_client: Optional[httpx.AsyncClient] = None

def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            base_url=BASE_URL,
            timeout=15.0,
            headers={"Accept": "application/json"},
        )
    return _client


# ── Simple TTL Cache ──────────────────────────────────────────────────────────

_cache: dict[str, tuple[float, object]] = {}
_CACHE_TTL = 600  # 10 minutes

def _cache_get(key: str):
    if key in _cache:
        ts, val = _cache[key]
        if time.monotonic() - ts < _CACHE_TTL:
            return val
        del _cache[key]
    return None

def _cache_set(key: str, val):
    _cache[key] = (time.monotonic(), val)


# ── Normalise IMDB API → internal movie dict ──────────────────────────────────

def _runtime_min(seconds: Optional[int]) -> Optional[int]:
    return round(seconds / 60) if seconds else None


def _poster_url(image: Optional[dict]) -> Optional[str]:
    """Return a resized poster URL (w500 equivalent) from the raw full-res URL."""
    if not image or not image.get("url"):
        return None
    url: str = image["url"]
    # Amazon image resize trick: append ._V1_UX500_.jpg
    if "m.media-amazon.com" in url and "._V1_" in url:
        base = url.split("._V1_")[0]
        return base + "._V1_UX500_.jpg"
    return url


def _backdrop_url(image: Optional[dict]) -> Optional[str]:
    """Return a wider backdrop/hero URL."""
    if not image or not image.get("url"):
        return None
    url: str = image["url"]
    if "m.media-amazon.com" in url and "._V1_" in url:
        base = url.split("._V1_")[0]
        return base + "._V1_UX1280_.jpg"
    return url


def _normalise(raw: dict, credits: Optional[list] = None) -> dict:
    """Convert an IMDB API title object into our internal movie dict."""
    rating_obj = raw.get("rating") or {}
    cast = []
    director = ""
    if credits:
        for c in credits:
            name_obj = c.get("name") or {}
            display = name_obj.get("displayName", "")
            cat = c.get("category", "")
            if cat == "director" and not director:
                director = display
            elif cat == "actor" and len(cast) < 5:
                cast.append(display)

    img = raw.get("primaryImage")
    return {
        "id": raw.get("id", ""),               # tt-prefixed IMDb ID string
        "title": raw.get("primaryTitle", raw.get("originalTitle", "")),
        "year": raw.get("startYear"),
        "genres": raw.get("genres", []),
        "overview": raw.get("plot", ""),
        "cast": cast,
        "director": director,
        "rating": float(rating_obj.get("aggregateRating", 0) or 0),
        "vote_count": int(rating_obj.get("voteCount", 0) or 0),
        "runtime": _runtime_min(raw.get("runtimeSeconds")),
        "poster": _poster_url(img),
        "backdrop": _backdrop_url(img),
    }


# ── API Calls ─────────────────────────────────────────────────────────────────

async def fetch_titles(
    *,
    sort_by: str = "SORT_BY_USER_RATING",
    sort_order: str = "DESC",
    min_votes: int = 50000,
    min_rating: float = 0.0,
    genres: Optional[list[str]] = None,
    page_token: Optional[str] = None,
    limit: int = 20,
    retries: int = 3,
) -> dict:
    """Fetch a page of movies from /titles with optional filters."""
    cache_key = f"titles:{sort_by}:{sort_order}:{min_votes}:{min_rating}:{genres}:{page_token}:{limit}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    params: dict = {
        "types": "MOVIE",
        "sortBy": sort_by,
        "sortOrder": sort_order,
        "minVoteCount": min_votes,
    }
    if min_rating > 0:
        params["minAggregateRating"] = min_rating
    if genres:
        params["genres"] = genres
    if page_token:
        params["pageToken"] = page_token

    client = get_client()
    for attempt in range(retries):
        try:
            resp = await client.get("/titles", params=params)
            if resp.status_code == 429:
                wait = (2 ** attempt) + 1
                logger.warning(f"IMDb API Rate Limit (429). Retrying in {wait}s...")
                await asyncio.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            break
        except Exception as e:
            if attempt == retries - 1:
                raise e
            await asyncio.sleep(1)

    titles_raw = data.get("titles", [])[:limit]
    movies = [_normalise(t) for t in titles_raw]
    result = {
        "results": movies,
        "total": data.get("totalCount", len(movies)),
        "nextPageToken": data.get("nextPageToken"),
    }
    _cache_set(cache_key, result)
    return result


async def fetch_title(title_id: str, retries: int = 3) -> dict:
    """Fetch a single title by IMDb ID (e.g. 'tt0468569') with credits."""
    cache_key = f"title:{title_id}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    client = get_client()
    raw, credits_data = None, []
    
    for attempt in range(retries):
        try:
            # Fetch title and credits concurrently
            title_resp, credits_resp = await asyncio.gather(
                client.get(f"/titles/{title_id}"),
                client.get(f"/titles/{title_id}/credits", params={
                    "categories": ["director", "actor"],
                    "pageSize": 10,
                }),
                return_exceptions=True
            )
            
            # Handle title response
            if isinstance(title_resp, httpx.Response):
                if title_resp.status_code == 429:
                    wait = (2 ** attempt) + 1
                    await asyncio.sleep(wait)
                    continue
                title_resp.raise_for_status()
                raw = title_resp.json()
            else:
                raise title_resp
                
            # Handle credits
            if isinstance(credits_resp, httpx.Response) and credits_resp.is_success:
                credits_data = credits_resp.json().get("credits", [])
            
            if raw: break
        except Exception as e:
            if attempt == retries - 1:
                raise e
            await asyncio.sleep(1)

    if not raw:
        raise Exception(f"Failed to fetch title {title_id} after {retries} retries")

    movie = _normalise(raw, credits=credits_data)
    _cache_set(cache_key, movie)
    return movie


async def fetch_genres() -> list[str]:
    """Return a deduplicated sorted list of movie genres.
    Since IMDB API doesn't have a /genres endpoint we fetch top titles and aggregate.
    """
    cache_key = "genres"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    data = await fetch_titles(sort_by="SORT_BY_POPULARITY", min_votes=10000, limit=50)
    genres: set[str] = set()
    for m in data["results"]:
        genres.update(m.get("genres", []))
    # Add common ones that might not appear in top-50
    genres.update(["Action", "Comedy", "Drama", "Horror", "Romance", "Sci-Fi",
                   "Thriller", "Animation", "Crime", "Adventure", "Fantasy", "Mystery"])
    result = sorted(genres)
    _cache_set(cache_key, result)
    return result


async def search_titles(query: str) -> list[dict]:
    """Search movies by title. Falls back to /titles with name filter if no results."""
    # imdbapi.dev doesn't have a free-text search endpoint, so we fetch popular movies
    # and filter client-side, plus do a targeted fetch by genre keywords.
    cache_key = f"search:{query.lower().strip()}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    q = query.lower().strip()
    # Fetch candidates from multiple sorted buckets in parallel
    tasks = [
        fetch_titles(sort_by="SORT_BY_USER_RATING", sort_order="DESC", min_votes=10000, limit=50),
        fetch_titles(sort_by="SORT_BY_POPULARITY", sort_order="DESC", min_votes=5000, limit=50),
        fetch_titles(sort_by="SORT_BY_RELEASE_DATE", sort_order="DESC", min_votes=5000, limit=50),
    ]
    results_list = await asyncio.gather(*tasks)
    seen: set = set()
    all_movies: list[dict] = []
    for r in results_list:
        for m in r["results"]:
            if m["id"] not in seen:
                seen.add(m["id"])
                all_movies.append(m)

    # Score-based filter
    matches = []
    for m in all_movies:
        title_lower = (m.get("title") or "").lower()
        overview_lower = (m.get("overview") or "").lower()
        genres_lower = " ".join(m.get("genres") or []).lower()
        director_lower = (m.get("director") or "").lower()
        cast_lower = " ".join(m.get("cast") or []).lower()

        score = 0
        if q in title_lower:
            score += 10
            if title_lower.startswith(q):
                score += 5
        if q in overview_lower:
            score += 3
        if q in genres_lower:
            score += 4
        if q in director_lower:
            score += 5
        if q in cast_lower:
            score += 4

        if score > 0:
            m["_score"] = score
            matches.append(m)

    matches.sort(key=lambda x: (-x.pop("_score", 0), -x.get("rating", 0)))
    _cache_set(cache_key, matches)
    return matches


async def fetch_recommendations(title_id: str, n: int = 10) -> list[dict]:
    """Fetch genre-based recommendations for a given title id.
    Since imdbapi.dev has no recommendations endpoint, we fetch top movies
    in the same genres and exclude the current title.
    """
    cache_key = f"recs:{title_id}:{n}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    movie = await fetch_title(title_id)
    genres = movie.get("genres", [])
    if not genres:
        data = await fetch_titles(sort_by="SORT_BY_USER_RATING", min_votes=100000, limit=n + 1)
        recs = [m for m in data["results"] if m["id"] != title_id][:n]
        _cache_set(cache_key, recs)
        return recs

    data = await fetch_titles(
        sort_by="SORT_BY_USER_RATING",
        sort_order="DESC",
        min_votes=50000,
        genres=genres[:2],
        limit=n + 5,
    )
    recs = [m for m in data["results"] if m["id"] != title_id][:n]
    _cache_set(cache_key, recs)
    return recs


async def _fetch_pages(
    *,
    sort_by: str,
    genres: Optional[list[str]] = None,
    min_votes: int = 5000,
    target: int = 50,
    seen: set,
) -> list[dict]:
    """Paginate /titles until we collect `target` unique movies via nextPageToken."""
    collected: list[dict] = []
    page_token: Optional[str] = None

    while len(collected) < target:
        params: dict = {
            "types": "MOVIE",
            "sortBy": sort_by,
            "sortOrder": "DESC",
            "minVoteCount": min_votes,
        }
        if genres:
            params["genres"] = genres
        if page_token:
            params["pageToken"] = page_token

        try:
            client = get_client()
            resp = await client.get("/titles", params=params)
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            break

        for raw in data.get("titles", []):
            m = _normalise(raw)
            if m["id"] and m["id"] not in seen:
                seen.add(m["id"])
                collected.append(m)

        page_token = data.get("nextPageToken")
        if not page_token:
            break  # no more pages for this stream

    return collected


async def fetch_popular_corpus(n: int = 1000) -> list[dict]:
    """Fetch a large diverse corpus of movies for TF-IDF predict index.

    Strategy — 3 layers of parallelism:
    - 12 genres  x  3 sort orders  =  36 genre-specific streams
    - 4 unfiltered sweeps for broad coverage
    - Each stream paginates via nextPageToken until it collects ~30 unique movies
    - Final dedup + quality sort gives 1000+ diverse movies
    """
    GENRES = [
        ["Action"], ["Drama"], ["Comedy"], ["Crime"],
        ["Thriller"], ["Sci-Fi"], ["Horror"], ["Romance"],
        ["Adventure"], ["Animation"], ["Mystery"], ["Biography"],
    ]
    SORT_BUCKETS = [
        "SORT_BY_USER_RATING",
        "SORT_BY_POPULARITY",
        "SORT_BY_USER_RATING_COUNT",
    ]

    seen: set = set()  # shared; _fetch_pages mutates it safely (single thread)
    per_stream = max(30, n // (len(GENRES) * len(SORT_BUCKETS) + 4))

    # 36 genre-specific streams
    tasks = [
        _fetch_pages(sort_by=sort_by, genres=genre, min_votes=1000,
                     target=per_stream, seen=seen)
        for sort_by in SORT_BUCKETS
        for genre in GENRES
    ]
    # 4 unfiltered broad sweeps
    tasks += [
        _fetch_pages(sort_by="SORT_BY_USER_RATING",       min_votes=50000,  target=150, seen=seen),
        _fetch_pages(sort_by="SORT_BY_POPULARITY",         min_votes=20000,  target=150, seen=seen),
        _fetch_pages(sort_by="SORT_BY_USER_RATING_COUNT",  min_votes=10000,  target=150, seen=seen),
        _fetch_pages(sort_by="SORT_BY_RELEASE_DATE",       min_votes=5000,   target=150, seen=seen),
    ]

    results_list = await asyncio.gather(*tasks, return_exceptions=True)

    corpus: list[dict] = []
    for r in results_list:
        if isinstance(r, list):
            corpus.extend(r)

    # Sort best quality first: rating weighted by vote popularity
    corpus.sort(key=lambda m: -(m.get("rating", 0) * min(m.get("vote_count", 0) / 100_000, 1)))
    return corpus[:n]

