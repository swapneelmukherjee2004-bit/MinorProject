import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import Home from './pages/Home';
import MovieDetail from './pages/MovieDetail';
import Search from './pages/Search';
import Watchlist from './pages/Watchlist';
import Predict from './pages/Predict';
import './index.css';
import './App.css';

export default function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <Routes>
        <Route path="/"           element={<Home />} />
        <Route path="/movie/:id"  element={<MovieDetail />} />
        <Route path="/search"     element={<Search />} />
        <Route path="/watchlist"  element={<Watchlist />} />
        <Route path="/predict"    element={<Predict />} />
      </Routes>
      <footer className="footer">
        <div className="container footer__inner">
          <span className="footer__logo">🎬 CineMatch</span>
          <p className="footer__copy">© 2026 CineMatch — Powered by AI Recommendations</p>
        </div>
      </footer>
    </BrowserRouter>
  );
}
