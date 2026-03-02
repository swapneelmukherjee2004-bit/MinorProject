import { useState } from 'react';

export default function StarRating({ movieId, initialRating = 0, onRate }) {
    const [hovered, setHovered] = useState(0);
    const [selected, setSelected] = useState(initialRating);

    const handleClick = (val) => {
        setSelected(val);
        onRate?.(movieId, val);
    };

    return (
        <div className="star-rating" role="group" aria-label="Rate this movie">
            {[1, 2, 3, 4, 5].map(star => (
                <button
                    key={star}
                    className={`star-rating__star ${star <= (hovered || selected) ? 'active' : ''}`}
                    onMouseEnter={() => setHovered(star)}
                    onMouseLeave={() => setHovered(0)}
                    onClick={() => handleClick(star)}
                    aria-label={`Rate ${star} star${star > 1 ? 's' : ''}`}
                >
                    ★
                </button>
            ))}
            {selected > 0 && (
                <span className="star-rating__label">{selected}/5 — Your Rating</span>
            )}
        </div>
    );
}
