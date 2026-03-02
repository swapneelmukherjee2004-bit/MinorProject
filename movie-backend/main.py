"""
FastAPI Movie Recommendation Service
- Primary data: local SQLite (built from IMDb bulk TSV datasets — 250k+ movies)
- Enrichment:   imdbapi.dev (posters, overview, cast/director) — lazy, cached to DB
"""
import asyncio
import json
import logging
import os

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

import db
from imdb_client import fetch_title, fetch_genres as _api_genres
from recommender import build_index, predict_from_text

logger = logging.getLogger("cinematch")

app = FastAPI(
    title="CineMatch API",
    description="Movie Recommendation System — 250k+ IMDb movies",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    if not db.db_exists():
        logger.warning(
            "movies.db not found. Run: ./venv/bin/python download_dataset.py\n"
            "Falling back to live API corpus (200 movies)."
        )
        # Fallback: build TF-IDF from small live corpus
        from imdb_client import fetch_popular_corpus
        try:
            corpus = await fetch_popular_corpus(n=200)
            build_index(corpus)
            logger.info(f"Fallback TF-IDF index built ({len(corpus)} movies).")
        except Exception as e:
            logger.warning(f"Fallback corpus failed: {e}")
        return

    count = db.get_movie_count()
    logger.info(f"SQLite DB ready — {count:,} movies available.")

    # Build TF-IDF index from top 10k quality movies in DB
    logger.info("Building TF-IDF predict index…")
    corpus = await asyncio.get_event_loop().run_in_executor(None, db.get_corpus, 10_000)
    build_index(corpus)
    logger.info(f"TF-IDF index built on {len(corpus):,} movies.")


# ── Lazy enrichment ───────────────────────────────────────────────────────────

async def _enrich_one(movie_id: str):
    """Enrich a single movie ID in the background."""
    try:
        live = await fetch_title(movie_id)
        updates = {
            "poster": live.get("poster", ""),
            "backdrop": live.get("backdrop", ""),
            "overview": live.get("overview", ""),
            "director": live.get("director", ""),
            "cast": ",".join(live.get("cast", []))
        }
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: db.update_enrichment(movie_id, **updates)
        )
    except Exception:
        pass


async def _enrich_batch(movie_ids: List[str]):
    """Enrich multiple movies in the background."""
    # Process in small chunks to avoid API hammering
    chunk_size = 5
    for i in range(0, len(movie_ids), chunk_size):
        chunk = movie_ids[i:i+chunk_size]
        tasks = [fetch_title(mid) for mid in chunk]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Write to DB
        def write_updates(batch_data):
            for mid, res in batch_data:
                if isinstance(res, dict):
                    db.update_enrichment(mid, 
                        poster=res.get("poster", ""),
                        backdrop=res.get("backdrop", ""),
                        overview=res.get("overview", ""),
                        director=res.get("director", ""),
                        cast=",".join(res.get("cast", []))
                    )

        batch_pairs = list(zip(chunk, results))
        await asyncio.get_event_loop().run_in_executor(None, write_updates, batch_pairs)
        await asyncio.sleep(0.5)


async def _enrich(movie: dict) -> dict:
    """If poster/overview/cast are missing, fetch from imdbapi.dev and cache to DB."""
    if movie.get("poster") and movie.get("overview"):
        return movie  # already enriched

    try:
        live = await fetch_title(movie["id"])
        updates = {}
        if not movie.get("poster")   and live.get("poster"):   updates["poster"]   = live["poster"]
        if not movie.get("backdrop") and live.get("backdrop"):  updates["backdrop"] = live["backdrop"]
        if not movie.get("overview") and live.get("overview"):  updates["overview"] = live["overview"]
        if not movie.get("director") and live.get("director"):  updates["director"] = live["director"]
        if not movie.get("cast")     and live.get("cast"):      updates["cast"]     = ",".join(live["cast"])

        if updates:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: db.update_enrichment(movie["id"], **updates)
            )
            movie = {**movie, **updates}
            if isinstance(movie.get("cast"), str):
                movie["cast"] = [c.strip() for c in movie["cast"].split(",") if c.strip()]
    except Exception:
        pass

    return movie


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    count = db.get_movie_count() if db.db_exists() else "N/A (no DB yet)"
    return {
        "message": "CineMatch API is running 🎬",
        "version": "3.1.0",
        "movies_in_db": count,
        "source": "IMDb bulk datasets + background enrichment",
    }


@app.get("/genres")
async def list_genres():
    """All distinct genres in the local DB."""
    if db.db_exists():
        genres = await asyncio.get_event_loop().run_in_executor(None, db.get_genres)
        return genres
    return await _api_genres()


@app.get("/trending")
async def trending(background_tasks: BackgroundTasks, limit: int = Query(default=20, ge=1, le=100)):
    """Top movies by combined rating × popularity score."""
    if db.db_exists():
        movies = await asyncio.get_event_loop().run_in_executor(
            None, db.get_trending, limit
        )
        # Background enrichment for missing posters
        to_enrich = [m["id"] for m in movies if not m.get("poster")]
        if to_enrich:
            background_tasks.add_task(_enrich_batch, to_enrich)
        return movies
    
    from imdb_client import fetch_titles
    data = await fetch_titles(sort_by="SORT_BY_USER_RATING", sort_order="DESC",
                               min_votes=500000, limit=limit)
    return data["results"]


@app.get("/movies")
async def list_movies(
    background_tasks: BackgroundTasks,
    genre:     Optional[str] = Query(default=None),
    page:      int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by:   str = Query(default="rating"),
):
    """List movies with optional genre filter, pagination, and sort."""
    offset = (page - 1) * page_size
    if db.db_exists():
        data = await asyncio.get_event_loop().run_in_executor(
            None, lambda: db.get_movies(genre=genre, sort_by=sort_by,
                                        limit=page_size, offset=offset)
        )
        # Background enrichment
        to_enrich = [m["id"] for m in data["results"] if not m.get("poster")]
        if to_enrich:
            background_tasks.add_task(_enrich_batch, to_enrich)
        return {**data, "page": page, "page_size": page_size}

    from imdb_client import fetch_titles
    data = await fetch_titles(sort_by="SORT_BY_USER_RATING", sort_order="DESC",
                               min_votes=10000, genres=[genre] if genre else None,
                               limit=page_size)
    return {"total": data.get("total", 0), "page": page, "page_size": page_size,
            "results": data["results"]}


@app.get("/movies/{movie_id}")
async def movie_detail(movie_id: str):
    """Full details for a single movie, enriched with poster/cast from imdbapi.dev."""
    if db.db_exists():
        movie = await asyncio.get_event_loop().run_in_executor(
            None, db.get_movie, movie_id
        )
        if not movie:
            raise HTTPException(status_code=404, detail="Movie not found")
        return await _enrich(movie)

    try:
        return await fetch_title(movie_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/movies/{movie_id}/recommendations")
async def movie_recommendations(movie_id: str, n: int = Query(default=10, ge=1, le=20)):
    """Genre-based recommendations for a given movie."""
    if db.db_exists():
        movie = await asyncio.get_event_loop().run_in_executor(
            None, db.get_movie, movie_id
        )
        if not movie:
            raise HTTPException(status_code=404, detail="Movie not found")
        recs = await asyncio.get_event_loop().run_in_executor(
            None, lambda: db.get_by_genres(movie["genres"], exclude_id=movie_id, limit=n)
        )
        return {"movie_id": movie_id, "recommendations": recs}

    from imdb_client import fetch_recommendations
    recs = await fetch_recommendations(movie_id, n=n)
    return {"movie_id": movie_id, "recommendations": recs}


@app.get("/search")
async def search(background_tasks: BackgroundTasks, q: str = Query(..., min_length=1)):
    """Full-text search across title, genre, and overview."""
    if db.db_exists():
        results = await asyncio.get_event_loop().run_in_executor(
            None, lambda: db.search_movies(q, limit=50)
        )
        # Background enrichment for the top 10 search results
        to_enrich = [m["id"] for m in results if not m.get("poster")]
        if to_enrich:
            background_tasks.add_task(_enrich_batch, to_enrich[:10])
        return {"query": q, "total": len(results), "results": results}

    from imdb_client import search_titles
    results = await search_titles(q)
    return {"query": q, "total": len(results), "results": results}


# ── Realtime Prediction ───────────────────────────────────────────────────────

class PredictRequest(BaseModel):
    query: str
    n: int = 10


@app.post("/predict")
def predict(req: PredictRequest):
    """TF-IDF freeform text → ranked movies with confidence scores."""
    if not req.query.strip():
        return {"query": req.query, "results": []}
    results = predict_from_text(req.query, n=req.n)
    return {"query": req.query, "total": len(results), "results": results}


@app.websocket("/predict/stream")
async def predict_stream(websocket: WebSocket):
    """Stream TF-IDF movie predictions one-by-one as they are computed."""
    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            query = data.get("query", "").strip()
            n = int(data.get("n", 10))

            if not query:
                await websocket.send_json({"done": True, "results": []})
                continue

            results = await asyncio.get_event_loop().run_in_executor(
                None, predict_from_text, query, n
            )

            for movie in results:
                await websocket.send_json({"done": False, "movie": movie})
                await asyncio.sleep(0.08)

            await websocket.send_json({"done": True, "total": len(results)})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"error": str(e), "done": True})
        except Exception:
            pass
