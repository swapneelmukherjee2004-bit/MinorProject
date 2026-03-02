import { Link } from 'react-router-dom';
import useMovieStore from '../store/useMovieStore';

const FALLBACK = 'https://via.placeholder.com/200x300/12121a/9090a8?text=No+Poster';

export default function MovieCard({ movie, delay = 0 }) {
    const { toggleWatchlist, isInWatchlist } = useMovieStore();
    const inList = isInWatchlist(movie.id);

    return (
        <Link
            to={`/movie/${movie.id}`}
            className="movie-card"
            style={{ animationDelay: `${delay}ms` }}
        >
            <div className="movie-card__poster-wrap">
                <img
                    src={movie.poster || FALLBACK}
                    alt={movie.title}
                    className="movie-card__poster"
                    onError={e => { e.target.src = FALLBACK; }}
                    loading="lazy"
                />
                <div className="movie-card__overlay">
                    <button
                        className={`movie-card__wl-btn ${inList ? 'active' : ''}`}
                        onClick={e => { e.preventDefault(); toggleWatchlist(movie); }}
                        title={inList ? 'Remove from Watchlist' : 'Add to Watchlist'}
                    >
                        {inList ? '♥' : '♡'}
                    </button>
                </div>
                <div className="movie-card__rating">
                    ★ {movie.rating?.toFixed(1)}
                </div>
            </div>
            <div className="movie-card__info">
                <h3 className="movie-card__title">{movie.title}</h3>
                <div className="movie-card__meta">
                    <span className="movie-card__year">{movie.year}</span>
                    {movie.genres?.[0] && (
                        <span className="genre-pill" style={{ fontSize: '0.65rem', padding: '2px 8px' }}>
                            {movie.genres[0]}
                        </span>
                    )}
                </div>
            </div>
        </Link>
    );
}
