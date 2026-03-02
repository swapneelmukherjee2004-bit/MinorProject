import gzip
import io
import os
import sqlite3
import sys
import time
import httpx

DB_PATH = os.path.join(os.path.dirname(__file__), "movies.db")

BASICS_URL  = "https://datasets.imdbws.com/title.basics.tsv.gz"
RATINGS_URL = "https://datasets.imdbws.com/title.ratings.tsv.gz"

MIN_VOTES   = 1000    
ADULT_FILTER = True   


# ── Download helpers ──────────────────────────────────────────────────────────

def _download(url: str, label: str) -> bytes:
    print(f"  Downloading {label}…", end=" ", flush=True)
    start = time.time()
    chunks = []
    total = 0
    downloaded = 0
    with httpx.stream("GET", url, follow_redirects=True, timeout=120) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        for chunk in resp.iter_bytes(chunk_size=65536):
            chunks.append(chunk)
            downloaded += len(chunk)
            if total:
                pct = downloaded * 100 // total
                print(f"\r  Downloading {label}… {pct:3d}%", end="", flush=True)
    data = b"".join(chunks)
    elapsed = time.time() - start
    print(f"\r  Downloaded  {label}  ({len(data)/1_048_576:.1f} MB, {elapsed:.0f}s)")
    return data



def _iter_tsv(gz_bytes: bytes):
    """Yield dicts from a gzip-compressed TSV file (first row = header)."""
    with gzip.open(io.BytesIO(gz_bytes), "rt", encoding="utf-8") as f:
        headers = f.readline().rstrip("\n").split("\t")
        for line in f:
            values = line.rstrip("\n").split("\t")
            yield dict(zip(headers, values))


# ── Build SQLite ──────────────────────────────────────────────────────────────

def build_database():
    print("\n📦  Building IMDb SQLite database…")

    # 1. Download
    print("\n[1/4] Fetching data files…")
    basics_gz  = _download(BASICS_URL,  "title.basics")
    ratings_gz = _download(RATINGS_URL, "title.ratings")

    # 2. Parse ratings into a dict for fast lookup
    print("\n[2/4] Parsing ratings…", flush=True)
    ratings: dict[str, tuple[float, int]] = {}
    for row in _iter_tsv(ratings_gz):
        try:
            votes = int(row["numVotes"])
            if votes >= MIN_VOTES:
                ratings[row["tconst"]] = (float(row["averageRating"]), votes)
        except (ValueError, KeyError):
            continue
    print(f"  {len(ratings):,} titles have ≥{MIN_VOTES} votes")
    del ratings_gz

    # 3. Parse basics, filter, join with ratings
    print("\n[3/4] Parsing titles and joining with ratings…", flush=True)
    movies: list[dict] = []
    for row in _iter_tsv(basics_gz):
        if row.get("titleType") != "movie":
            continue
        if ADULT_FILTER and row.get("isAdult") == "1":
            continue
        tid = row.get("tconst", "")
        if tid not in ratings:
            continue

        avg_rating, vote_count = ratings[tid]
        year_raw = row.get("startYear", r"\N")
        runtime_raw = row.get("runtimeMinutes", r"\N")
        genres_raw = row.get("genres", r"\N")

        movies.append({
            "id":         tid,
            "title":      row.get("primaryTitle", ""),
            "year":       int(year_raw) if year_raw != r"\N" else None,
            "runtime":    int(runtime_raw) if runtime_raw != r"\N" else None,
            "genres":     genres_raw if genres_raw != r"\N" else "",
            "rating":     avg_rating,
            "vote_count": vote_count,
            # enriched fields (populated lazily via imdbapi.dev)
            "overview":   "",
            "director":   "",
            "cast":       "",
            "poster":     "",
            "backdrop":   "",
        })
    del basics_gz
    print(f"  {len(movies):,} movies after filtering")

    # 4. Write to SQLite
    print(f"\n[4/4] Writing to SQLite → {DB_PATH}  …", flush=True)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.executescript("""
        DROP TABLE IF EXISTS movies;
        CREATE TABLE movies (
            id          TEXT PRIMARY KEY,
            title       TEXT NOT NULL,
            year        INTEGER,
            runtime     INTEGER,
            genres      TEXT DEFAULT '',
            rating      REAL DEFAULT 0,
            vote_count  INTEGER DEFAULT 0,
            overview    TEXT DEFAULT '',
            director    TEXT DEFAULT '',
            cast        TEXT DEFAULT '',
            poster      TEXT DEFAULT '',
            backdrop    TEXT DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_rating     ON movies(rating DESC);
        CREATE INDEX IF NOT EXISTS idx_votes      ON movies(vote_count DESC);
        CREATE INDEX IF NOT EXISTS idx_year       ON movies(year DESC);
        CREATE INDEX IF NOT EXISTS idx_title      ON movies(title);
    """)

    cur.executemany(
        """INSERT OR REPLACE INTO movies
           (id,title,year,runtime,genres,rating,vote_count,overview,director,cast,poster,backdrop)
           VALUES (:id,:title,:year,:runtime,:genres,:rating,:vote_count,
                   :overview,:director,:cast,:poster,:backdrop)""",
        movies,
    )
    con.commit()
    count = cur.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
    con.close()

    print(f"  ✅  {count:,} movies written to {DB_PATH}")
    return count


if __name__ == "__main__":
    t0 = time.time()
    count = build_database()
    elapsed = time.time() - t0
    print(f"\n🎬  Done in {elapsed:.0f}s — {count:,} movies available in SQLite.")
    print(f"    Database: {DB_PATH}\n")
