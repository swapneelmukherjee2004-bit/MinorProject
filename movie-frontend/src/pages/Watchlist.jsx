import { Link } from 'react-router-dom';
import MovieCard from '../components/MovieCard';
import useMovieStore from '../store/useMovieStore';

export default function Watchlist() {
  const watchlist = useMovieStore(s => s.watchlist);

  return (
    <main className="container watchlist-page">
      <h1 className="section-title" style={{ marginTop: 100 }}>♥ My Watchlist</h1>

      {watchlist.length === 0 ? (
        <div className="watchlist-page__empty">
          <p>Your watchlist is empty.</p>
          <Link to="/" className="btn btn--primary" style={{ marginTop: 16 }}>Discover Movies</Link>
        </div>
      ) : (
        <>
          <p style={{ color: 'var(--text-secondary)', marginBottom: 24 }}>
            {watchlist.length} movie{watchlist.length !== 1 ? 's' : ''} saved
          </p>
          <div className="movie-grid">
            {watchlist.map((m, i) => (
              <MovieCard key={m.id} movie={m} delay={i * 30} />
            ))}
          </div>
        </>
      )}
    </main>
  );
}
