"""
Content-Based Movie Recommendation Engine (dynamic version)
Builds TF-IDF index from a provided list of movies (fetched from IMDB API).
Supports freeform text prediction with confidence scores.
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from typing import Optional

# Module-level mutable state; rebuilt at startup via build_index()
_movies: list[dict] = []
_id_to_idx: dict[str, int] = {}
_tfidf: Optional[TfidfVectorizer] = None
_tfidf_matrix = None
_cosine_sim = None


def _build_feature_string(movie: dict) -> str:
    """Concatenate weighted features into a single string for TF-IDF."""
    genres = " ".join(movie.get("genres", []))
    cast = " ".join((movie.get("cast") or [])[:3])
    director = (movie.get("director") or "").replace(" ", "")
    overview = movie.get("overview") or ""
    # Repeat high-signal fields for higher weight
    return f"{genres} {genres} {director} {director} {cast} {overview}"


def build_index(movies: list[dict]) -> None:
    """(Re)build the TF-IDF similarity matrix from a list of movie dicts.
    Call this at startup (or after refreshing the corpus).
    """
    global _movies, _id_to_idx, _tfidf, _tfidf_matrix, _cosine_sim

    if not movies:
        return

    _movies = movies
    _id_to_idx = {m["id"]: i for i, m in enumerate(movies)}

    feature_strings = [_build_feature_string(m) for m in movies]

    _tfidf = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    _tfidf_matrix = _tfidf.fit_transform(feature_strings)
    _cosine_sim = cosine_similarity(_tfidf_matrix, _tfidf_matrix)


def get_recommendations(movie_id: str, n: int = 10) -> list[dict]:
    """Return top-N content-similar movies for a given movie_id."""
    if _cosine_sim is None or movie_id not in _id_to_idx:
        return []
    idx = _id_to_idx[movie_id]
    sim_scores = list(enumerate(_cosine_sim[idx]))
    sim_scores.sort(key=lambda x: x[1], reverse=True)
    sim_scores = [s for s in sim_scores if s[0] != idx][:n]
    return [_movies[i] for i, _ in sim_scores]


def predict_from_text(query: str, n: int = 10) -> list[dict]:
    """Return top-N movies matching freeform text, with confidence scores."""
    if not query.strip() or _tfidf is None or _tfidf_matrix is None:
        return []

    query_vec = _tfidf.transform([query])
    sim_scores = cosine_similarity(query_vec, _tfidf_matrix).flatten()
    scored = sorted(enumerate(sim_scores), key=lambda x: x[1], reverse=True)

    max_score = scored[0][1] if scored else 1.0
    results = []
    for idx, score in scored[:n]:
        if score == 0:
            break
        movie = dict(_movies[idx])
        confidence = round(
            float(score / max(max_score, 1e-9)) * 85
            + (_movies[idx].get("rating", 0) / 10) * 15,
            1,
        )
        movie["confidence"] = min(confidence, 99.9)
        results.append(movie)
    return results


def search_movies(query: str, movies: Optional[list[dict]] = None) -> list[dict]:
    """Simple keyword search across title, overview, genres, cast, director."""
    pool = movies if movies is not None else _movies
    q = query.lower()
    matches = []
    for m in pool:
        if (
            q in (m.get("title") or "").lower()
            or q in (m.get("overview") or "").lower()
            or any(q in g.lower() for g in (m.get("genres") or []))
            or any(q in c.lower() for c in (m.get("cast") or []))
            or q in (m.get("director") or "").lower()
        ):
            matches.append(m)
    matches.sort(key=lambda x: (
        q not in (x.get("title") or "").lower(),
        -(x.get("rating") or 0),
    ))
    return matches
