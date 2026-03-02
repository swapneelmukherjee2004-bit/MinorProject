import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import MovieCard from '../components/MovieCard';
import GenreFilter from '../components/GenreFilter';
import { getTrending, getMovies, getGenres } from '../api/movies';
import useMovieStore from '../store/useMovieStore';

export default function Home() {
    const [trending, setTrending] = useState([]);
    const [filteredMovies, setFilteredMovies] = useState([]);
    const [genres, setGenres] = useState([]);
    const [featuredIdx, setFeaturedIdx] = useState(0);
    const [loading, setLoading] = useState(true);
    const { activeGenre, setActiveGenre } = useMovieStore();

    useEffect(() => {
        let cancelled = false;
        Promise.all([getTrending(20), getGenres()])
            .then(([t, g]) => {
                if (cancelled) return;
                setTrending(Array.isArray(t) ? t : []);
                setGenres(Array.isArray(g) ? g : []);
                setLoading(false);
            })
            .catch(() => setLoading(false));
        return () => { cancelled = true; };
    }, []);

    useEffect(() => {
        setLoading(true);
        getMovies(activeGenre, 1, 40)
            .then(d => {
     
                const results = Array.isArray(d) ? d : (d?.results ?? []);
                setFilteredMovies(results);
                setLoading(false);
            })
            .catch(() => setLoading(false));
    }, [activeGenre]);

    // Use first 5 trending movies as hero candidates, but only if they have images/overview
    const heroMovies = trending
        .filter(m => m.backdrop && m.overview)
        .slice(0, 5);

    // Cycle hero movie every 5s
    useEffect(() => {
        if (heroMovies.length === 0) return;
        const id = setInterval(() => setFeaturedIdx(i => (i + 1) % heroMovies.length), 5000);
        return () => clearInterval(id);
    }, [heroMovies.length]);

    const featured = heroMovies[featuredIdx] || null;

    return (
        <main className="home">
            {/* ── Hero ── */}
            {featured && (
                <section className="hero" style={{ backgroundImage: `url(${featured.backdrop})` }}>
                    <div className="hero__gradient" />
                    <div className="container hero__content animate-fade-up">
                        <div className="hero__genres">
                            {featured.genres?.slice(0, 3).map(g => (
                                <span key={g} className="genre-pill">{g}</span>
                            ))}
                        </div>
                        <h1 className="hero__title">{featured.title}</h1>
                        <p className="hero__overview">{featured.overview}</p>
                        <div className="hero__meta">
                            <span className="rating-badge">★ {featured.rating?.toFixed(1)}</span>
                            <span className="hero__year">{featured.year}</span>
                            {featured.runtime && <span className="hero__runtime">{featured.runtime} min</span>}
                        </div>
                        <div className="hero__actions">
                            <Link to={`/movie/${featured.id}`} className="btn btn--primary">
                                ▶ View Details
                            </Link>
                        </div>
                    </div>
                    <div className="hero__dots">
                        {heroMovies.map((_, i) => (
                            <button
                                key={i}
                                className={`hero__dot ${i === featuredIdx ? 'active' : ''}`}
                                onClick={() => setFeaturedIdx(i)}
                            />
                        ))}
                    </div>
                </section>
            )}

            <div className="container home__body">
                {/* ── Trending ── */}
                <section className="section">
                    <h2 className="section-title">🔥 Trending Now</h2>
                    <div className="home__trending-scroll">
                        {trending.slice(0, 10).map((m, i) => (
                            <MovieCard key={m.id} movie={m} delay={i * 40} />
                        ))}
                    </div>
                </section>

                {/* ── Browse by Genre ── */}
                <section className="section">
                    <h2 className="section-title">🎭 Browse by Genre</h2>
                    <GenreFilter genres={genres} activeGenre={activeGenre} onSelect={setActiveGenre} />

                    {loading ? (
                        <div className="loading-grid">
                            {Array.from({ length: 12 }).map((_, i) => (
                                <div key={i} className="skeleton" style={{ height: 280, borderRadius: 14 }} />
                            ))}
                        </div>
                    ) : (
                        <div className="movie-grid">
                            {filteredMovies.map((m, i) => (
                                <MovieCard key={m.id} movie={m} delay={i * 30} />
                            ))}
                        </div>
                    )}
                </section>
            </div>
        </main>
    );
}
