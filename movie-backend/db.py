"""
db.py — SQLite query layer for the local IMDb movie database.

The database is built by download_dataset.py.
Posters/overviews/cast are lazily enriched from imdbapi.dev on first access.
"""
import sqlite3
import os
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "movies.db")



def _con() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def db_exists() -> bool:
    """Return True if the DB file exists and has at least one movie."""
    if not os.path.exists(DB_PATH):
        return False
    try:
        with _con() as con:
            count = con.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
            return count > 0
    except Exception:
        return False


# ── Row → dict ─────────────────────────────────────────────────────────────────

def _row(row: sqlite3.Row) -> dict:
    d = dict(row)
    # Genres stored as comma-separated string → list
    d["genres"] = [g.strip() for g in d.get("genres", "").split(",") if g.strip()]
    # Cast stored as comma-separated string → list
    d["cast"] = [c.strip() for c in d.get("cast", "").split(",") if c.strip()]
    return d


# ── Queries ────────────────────────────────────────────────────────────────────

def get_movie_count() -> int:
    with _con() as con:
        return con.execute("SELECT COUNT(*) FROM movies").fetchone()[0]


def get_trending(limit: int = 20) -> list[dict]:
    """Top movies by a combined popularity score (rating × log votes).
    Prioritises movies that already have posters enriched.
    """
    with _con() as con:
        rows = con.execute(
            """SELECT *, 
               (rating * MIN(vote_count / 100000.0, 1.0)) AS score,
               CASE WHEN poster IS NOT NULL AND poster != '' THEN 1 ELSE 0 END AS has_poster
               FROM movies
               WHERE rating > 0 AND vote_count > 0
               ORDER BY has_poster DESC, score DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
    return [_row(r) for r in rows]


def get_movies(
    genre: Optional[str] = None,
    sort_by: str = "rating",
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """List movies with optional genre filter, sort, and pagination.
    Prioritises movies with posters.
    """
    order_map = {
        "rating":     "rating DESC",
        "popularity": "vote_count DESC",
        "year":       "year DESC",
        "title":      "title ASC",
    }
    order = order_map.get(sort_by, "rating DESC")

    with _con() as con:
        if genre:
            where = "WHERE genres LIKE ?"
            params_count = (f"%{genre}%",)
            params_rows  = (f"%{genre}%", limit, offset)
            total = con.execute(f"SELECT COUNT(*) FROM movies {where}", params_count).fetchone()[0]
            rows  = con.execute(
                f"""SELECT *, CASE WHEN poster IS NOT NULL AND poster != '' THEN 1 ELSE 0 END AS has_poster 
                   FROM movies {where} 
                   ORDER BY has_poster DESC, {order} 
                   LIMIT ? OFFSET ?""",
                params_rows,
            ).fetchall()
        else:
            total = con.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
            rows  = con.execute(
                f"""SELECT *, CASE WHEN poster IS NOT NULL AND poster != '' THEN 1 ELSE 0 END AS has_poster 
                   FROM movies 
                   ORDER BY has_poster DESC, {order} 
                   LIMIT ? OFFSET ?""",
                (limit, offset),
            ).fetchall()

    return {
        "total":   total,
        "limit":   limit,
        "offset":  offset,
        "results": [_row(r) for r in rows],
    }


def get_movie(movie_id: str) -> Optional[dict]:
    """Fetch a single movie by IMDb ID."""
    with _con() as con:
        row = con.execute("SELECT * FROM movies WHERE id = ?", (movie_id,)).fetchone()
    return _row(row) if row else None


def search_movies(query: str, limit: int = 50) -> list[dict]:
    """Full-text title search (LIKE). Prioritises title matches, then genre/overview.
    Also prioritises movies with posters.
    """
    q = f"%{query}%"
    with _con() as con:
        rows = con.execute(
            """SELECT *, 
               CASE WHEN title LIKE ? THEN 3
                    WHEN genres LIKE ? THEN 2
                    WHEN overview LIKE ? THEN 1
                    ELSE 0 END AS relevance,
               CASE WHEN poster IS NOT NULL AND poster != '' THEN 1 ELSE 0 END AS has_poster
               FROM movies
               WHERE title LIKE ? OR genres LIKE ? OR overview LIKE ?
               ORDER BY has_poster DESC, relevance DESC, vote_count DESC
               LIMIT ?""",
            (f"%{query}%", q, q, q, q, q, limit),
        ).fetchall()
    return [_row(r) for r in rows]


def get_genres() -> list[str]:
    """Return all distinct genres present in the DB."""
    with _con() as con:
        rows = con.execute("SELECT DISTINCT genres FROM movies WHERE genres != ''").fetchall()
    genre_set: set[str] = set()
    for r in rows:
        for g in r[0].split(","):
            g = g.strip()
            if g:
                genre_set.add(g)
    return sorted(genre_set)


def get_by_genres(genres: list[str], exclude_id: str = "", limit: int = 15) -> list[dict]:
    """Fetch top-rated movies that share at least one genre."""
    with _con() as con:
        conditions = " OR ".join(["genres LIKE ?" for _ in genres])
        params = [f"%{g}%" for g in genres]
        if exclude_id:
            conditions += " AND id != ?"
            params.append(exclude_id)
        params.append(limit)
        rows = con.execute(
            f"SELECT * FROM movies WHERE ({conditions}) ORDER BY rating DESC LIMIT ?",
            params,
        ).fetchall()
    return [_row(r) for r in rows]


def update_enrichment(
    movie_id: str,
    *,
    overview: str = "",
    director: str = "",
    cast: str = "",
    poster: str = "",
    backdrop: str = "",
) -> None:
    """Persist poster/overview/cast fetched lazily from imdbapi.dev."""
    with _con() as con:
        fields, params = [], []
        if overview:  fields.append("overview = ?");  params.append(overview)
        if director:  fields.append("director = ?");  params.append(director)
        if cast:      fields.append("cast = ?");      params.append(cast)
        if poster:    fields.append("poster = ?");    params.append(poster)
        if backdrop:  fields.append("backdrop = ?");  params.append(backdrop)
        if not fields:
            return
        params.append(movie_id)
        con.execute(f"UPDATE movies SET {', '.join(fields)} WHERE id = ?", params)
        con.commit()


def get_corpus(limit: int = 10_000) -> list[dict]:
    """Return top movies for TF-IDF index, ordered by quality score."""
    with _con() as con:
        rows = con.execute(
            """SELECT * FROM movies
               WHERE rating > 0 AND vote_count > 0
               ORDER BY (rating * MIN(vote_count / 100000.0, 1.0)) DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
    return [_row(r) for r in rows]
