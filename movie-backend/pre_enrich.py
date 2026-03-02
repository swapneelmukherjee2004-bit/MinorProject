"""
pre_enrich.py
Enriches the top 100 movies with posters and overviews from the API.
This ensures the Home page and initial search results look great immediately.
"""
import asyncio
import logging
import sqlite3
import os
from imdb_client import fetch_title
import db

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pre_enrich")

async def enrich_ids(movie_ids: list[str]):
    """Enrich a specific list of movie IDs."""
    if not db.db_exists():
        logger.error("movies.db not found.")
        return

    logger.info(f"Enriching {len(movie_ids)} movies...")
    
    # Enrich in small batches to respect rate limits
    batch_size = 5
    for i in range(0, len(movie_ids), batch_size):
        batch = movie_ids[i:i+batch_size]
        logger.info(f"  Processing batch {i//batch_size + 1}/{(len(movie_ids)-1)//batch_size + 1}...")
        
        tasks = [fetch_title(mid) for mid in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        with sqlite3.connect(db.DB_PATH) as con:
            for mid, res in zip(batch, results):
                if isinstance(res, dict):
                    updates = {
                        "poster": res.get("poster", ""),
                        "backdrop": res.get("backdrop", ""),
                        "overview": res.get("overview", ""),
                        "director": res.get("director", ""),
                        "cast": ",".join(res.get("cast", []))
                    }
                    
                    fields = [f"{k} = ?" for k in updates.keys()]
                    params = list(updates.values()) + [mid]
                    con.execute(f"UPDATE movies SET {', '.join(fields)} WHERE id = ?", params)
            con.commit()
            
        # Small delay between batches
        await asyncio.sleep(0.5)

async def enrich_top_n(n: int = 100):
    logger.info(f"Fetching top {n} movies for enrichment check...")
    top_movies = db.get_trending(limit=n)
    to_enrich = [m["id"] for m in top_movies if not m.get("poster") or not m.get("overview")]
    
    if not to_enrich:
        logger.info("All top movies are already enriched! ✅")
        return

    await enrich_ids(to_enrich)

if __name__ == "__main__":
    asyncio.run(enrich_top_n(100))
