import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import MovieCard from '../components/MovieCard';
import SearchBar from '../components/SearchBar';
import { searchMovies, getMovies } from '../api/movies';

export default function Search() {
    const [searchParams] = useSearchParams();
    const q = searchParams.get('q') || '';
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(false);
    const [total, setTotal] = useState(0);

    useEffect(() => {
        if (!q) {
            // No query: show all movies
            setLoading(true);
            getMovies(null, 1, 50).then(d => {
                setResults(d.results);
                setTotal(d.total);
                setLoading(false);
            });
            return;
        }
        setLoading(true);
        searchMovies(q)
            .then(d => {
                setResults(d.results);
                setTotal(d.total);
                setLoading(false);
            })
            .catch(() => setLoading(false));
    }, [q]);

    return (
        <main className="search-page container">
            <div className="search-page__header">
                <SearchBar initialValue={q} />
            </div>

            {q ? (
                <h2 className="search-page__heading">
                    {loading ? 'Searching…' : `${total} results for "${q}"`}
                </h2>
            ) : (
                <h2 className="search-page__heading">All Movies</h2>
            )}

            {loading ? (
                <div className="loading-grid">
                    {Array.from({ length: 12 }).map((_, i) => (
                        <div key={i} className="skeleton" style={{ height: 280, borderRadius: 14 }} />
                    ))}
                </div>
            ) : results.length === 0 ? (
                <div className="search-page__empty">
                    <p>😕 No movies found for <strong>"{q}"</strong></p>
                    <p>Try a different title, genre, or actor name.</p>
                </div>
            ) : (
                <div className="movie-grid">
                    {results.map((m, i) => (
                        <MovieCard key={m.id} movie={m} delay={i * 25} />
                    ))}
                </div>
            )}
        </main>
    );
}
