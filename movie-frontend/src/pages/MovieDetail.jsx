import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import MovieCard from '../components/MovieCard';
import StarRating from '../components/StarRating';
import { getMovieDetail, getRecommendations } from '../api/movies';
import useMovieStore from '../store/useMovieStore';

export default function MovieDetail() {
    const { id } = useParams();
    const movieId = id; // IMDb IDs are strings like 'tt0468569'
    const [movie, setMovie] = useState(null);
    const [recs, setRecs] = useState([]);
    const [loading, setLoading] = useState(true);
    const { toggleWatchlist, isInWatchlist, setRating, getRating } = useMovieStore();

    useEffect(() => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
        setLoading(true);
        setMovie(null);
        setRecs([]);
        Promise.all([getMovieDetail(movieId), getRecommendations(movieId, 10)])
            .then(([m, r]) => {
                setMovie(m);
                setRecs(r.recommendations || []);
                setLoading(false);
            })
            .catch(() => setLoading(false));
    }, [movieId]);

    if (loading) {
        return (
            <div className="detail-loading">
                <div className="spinner" />
                <p>Loading movie…</p>
            </div>
        );
    }

    if (!movie) {
        return (
            <div className="detail-error">
                <h2>Movie not found</h2>
                <Link to="/" className="btn btn--primary">← Back to Home</Link>
            </div>
        );
    }

    const inList = isInWatchlist(movieId);
    const userRating = getRating(movieId);

    // Progress bar fill (0-100%)
    const ratingPct = ((movie.rating - 5) / 4.3) * 100;

    return (
        <article className="detail animate-fade-in">
            {/* ── BACKDROP ── */}
            <div className="detail__backdrop" style={{ backgroundImage: `url(${movie.backdrop})` }}>
                <div className="detail__backdrop-grad" />
            </div>

            <div className="container detail__layout">
                {/* ── Poster ── */}
                <aside className="detail__poster-col animate-scale-in">
                    <img
                        src={movie.poster}
                        alt={movie.title}
                        className="detail__poster"
                        onError={e => { e.target.src = 'https://via.placeholder.com/300x450/12121a/9090a8?text=No+Poster'; }}
                    />
                    <div className="detail__actions">
                        <button
                            className={`btn ${inList ? 'btn--secondary active' : 'btn--primary'}`}
                            onClick={() => toggleWatchlist(movie)}
                        >
                            {inList ? '♥ In Watchlist' : '♡ Add to Watchlist'}
                        </button>
                    </div>
                    <div className="detail__user-rating">
                        <p>Your Rating</p>
                        <StarRating
                            movieId={movieId}
                            initialRating={userRating}
                            onRate={setRating}
                        />
                    </div>
                </aside>

                {/* ── Info ── */}
                <div className="detail__info animate-fade-up">
                    <div className="detail__genres">
                        {movie.genres?.map(g => <span key={g} className="genre-pill">{g}</span>)}
                    </div>
                    <h1 className="detail__title">{movie.title}</h1>

                    <div className="detail__meta-row">
                        <span className="rating-badge">★ {movie.rating?.toFixed(1)}</span>
                        <span className="detail__meta-item">📅 {movie.year}</span>
                        <span className="detail__meta-item">⏱ {movie.runtime} min</span>
                        <span className="detail__meta-item">🗳 {(movie.vote_count / 1000).toFixed(0)}K votes</span>
                    </div>

                    <div className="detail__rating-bar">
                        <div className="detail__rating-bar__fill" style={{ width: `${Math.max(10, ratingPct)}%` }} />
                    </div>

                    <p className="detail__overview">{movie.overview}</p>

                    <div className="detail__credits">
                        <div className="detail__credit">
                            <span className="detail__credit-label">Director</span>
                            <span className="detail__credit-value">{movie.director}</span>
                        </div>
                        <div className="detail__credit">
                            <span className="detail__credit-label">Cast</span>
                            <div className="detail__cast">
                                {movie.cast?.map(actor => (
                                    <span key={actor} className="detail__cast-chip">{actor}</span>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* ── Recommendations ── */}
            {recs.length > 0 && (
                <section className="container detail__recs">
                    <h2 className="section-title">✨ You Might Also Like</h2>
                    <div className="detail__recs-scroll">
                        {recs.map((m, i) => (
                            <MovieCard key={m.id} movie={m} delay={i * 40} />
                        ))}
                    </div>
                </section>
            )}
        </article>
    );
}
