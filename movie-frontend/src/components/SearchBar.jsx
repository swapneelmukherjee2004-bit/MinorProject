import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import useMovieStore from '../store/useMovieStore';

export default function SearchBar({ initialValue = '' }) {
  const [value, setValue] = useState(initialValue);
  const [focused, setFocused] = useState(false);
  const inputRef = useRef(null);
  const navigate = useNavigate();
  const setSearchQuery = useMovieStore(s => s.setSearchQuery);

  useEffect(() => { setValue(initialValue); }, [initialValue]);

  const handleSubmit = (e) => {
    e.preventDefault();
    const q = value.trim();
    if (!q) return;
    setSearchQuery(q);
    navigate(`/search?q=${encodeURIComponent(q)}`);
    inputRef.current?.blur();
  };

  return (
    <form className={`search-bar ${focused ? 'focused' : ''}`} onSubmit={handleSubmit}>
      <span className="search-bar__icon">🔍</span>
      <input
        ref={inputRef}
        type="text"
        placeholder="Search movies, actors, genres…"
        value={value}
        onChange={e => setValue(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        className="search-bar__input"
      />
      {value && (
        <button
          type="button"
          className="search-bar__clear"
          onClick={() => { setValue(''); inputRef.current?.focus(); }}
        >
          ✕
        </button>
      )}
    </form>
  );
}
