import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useState, useEffect } from 'react';
import SearchBar from './SearchBar';
import useMovieStore from '../store/useMovieStore';

export default function Navbar() {
    const [scrolled, setScrolled] = useState(false);
    const [menuOpen, setMenuOpen] = useState(false);
    const watchlist = useMovieStore(s => s.watchlist);
    const location = useLocation();
    const isHome = location.pathname === '/';

    useEffect(() => {
        const onScroll = () => setScrolled(window.scrollY > 40);
        window.addEventListener('scroll', onScroll);
        return () => window.removeEventListener('scroll', onScroll);
    }, []);

    useEffect(() => { setMenuOpen(false); }, [location]);

    return (
        <header className={`navbar ${scrolled || !isHome ? 'navbar--solid' : ''}`}>
            <div className="container navbar__inner">
                <Link to="/" className="navbar__logo">
                    🎬 <span>CineMatch</span>
                </Link>

                <div className="navbar__search">
                    <SearchBar />
                </div>

                <nav className={`navbar__nav ${menuOpen ? 'open' : ''}`}>
                    <Link to="/" className="navbar__link">Home</Link>
                    <Link to="/search?q=action" className="navbar__link">Action</Link>
                    <Link to="/search?q=drama" className="navbar__link">Drama</Link>
                    <Link to="/predict" className="navbar__link navbar__predict-btn">🔮 Predict</Link>
                    <Link to="/watchlist" className="navbar__link navbar__wl-btn">
                        ♥ <span>{watchlist.length > 0 ? watchlist.length : ''}</span> Watchlist
                    </Link>
                </nav>

                <button
                    className="navbar__hamburger"
                    onClick={() => setMenuOpen(m => !m)}
                    aria-label="Toggle menu"
                >
                    {menuOpen ? '✕' : '☰'}
                </button>
            </div>
        </header>
    );
}
