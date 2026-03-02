export default function GenreFilter({ genres, activeGenre, onSelect }) {
    return (
        <div className="genre-filter">
            <button
                className={`genre-pill ${!activeGenre ? 'active' : ''}`}
                onClick={() => onSelect(null)}
            >
                All
            </button>
            {genres.map(g => (
                <button
                    key={g}
                    className={`genre-pill ${activeGenre === g ? 'active' : ''}`}
                    onClick={() => onSelect(g === activeGenre ? null : g)}
                >
                    {g}
                </button>
            ))}
        </div>
    );
}
