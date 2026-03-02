import { useState, useEffect, useRef, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { createPredictSocket } from '../api/movies';

const EXAMPLES = [
    'A dark psychological thriller with an unreliable narrator',
    'Epic space opera with stunning visuals and a rebel hero',
    'Romantic comedy set in New York with a witty female lead',
    'Animated adventure for kids with talking animals',
    'Gritty crime drama about an undercover detective',
    'Supernatural horror in a haunted Victorian mansion',
];

const MAX_RETRIES = 5;

export default function Predict() {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState([]);
    const [streaming, setStreaming] = useState(false);
    const [status, setStatus] = useState('idle'); 
    const [totalFound, setTotalFound] = useState(null);
    const socketRef = useRef(null);
    const debounceRef = useRef(null);
    const abortRef = useRef(false);
    const retryCountRef = useRef(0);
    const retryTimerRef = useRef(null);

    // ── WebSocket lifecycle ────────────────────────────────────────
    const openSocket = useCallback((onReady) => {
        if (socketRef.current && socketRef.current.readyState <= 1) {
            if (onReady) socketRef.current.addEventListener('open', onReady, { once: true });
            return;
        }
        const ws = createPredictSocket();
        socketRef.current = ws;

        ws.onopen = () => {
            retryCountRef.current = 0;
            if (onReady) onReady();
        };

        ws.onmessage = (e) => {
            const data = JSON.parse(e.data);
            if (data.error) { setStatus('error'); setStreaming(false); return; }
            if (data.done) {
                setTotalFound(data.total ?? null);
                setStatus('done');
                setStreaming(false);
            } else if (data.movie && !abortRef.current) {
                setResults(prev => [...prev, data.movie]);
            }
        };

        ws.onerror = () => {};

        ws.onclose = () => {
            if (retryCountRef.current >= MAX_RETRIES) {
                setStatus('offline');
                setStreaming(false);
                return;
            }
            // Exponential backoff
            const delay = Math.min(1000 * 2 ** retryCountRef.current, 10000);
            retryCountRef.current += 1;
            retryTimerRef.current = setTimeout(() => openSocket(), delay);
        };
    }, []);

    useEffect(() => {
        openSocket();
        return () => {
            clearTimeout(retryTimerRef.current);
            socketRef.current?.close();
        };
    }, [openSocket]);

    // ── Send query via WebSocket ───────────────────────────────────
    const runPrediction = useCallback((q) => {
        if (!q.trim()) {
            setResults([]); setStatus('idle'); setStreaming(false);
            return;
        }
        abortRef.current = false;
        setResults([]);
        setTotalFound(null);
        setStreaming(true);
        setStatus('connecting');

        const doSend = () => {
            if (socketRef.current?.readyState === WebSocket.OPEN) {
                socketRef.current.send(JSON.stringify({ query: q, n: 10 }));
                setStatus('streaming');
            } else {
                setStatus('error');
                setStreaming(false);
            }
        };

        if (socketRef.current?.readyState === WebSocket.OPEN) {
            doSend();
        } else {
            openSocket(doSend);
        }
    }, [openSocket]);

    // ── Debounce input ────────────────────────────────────────────
    const handleInput = (val) => {
        setQuery(val);
        clearTimeout(debounceRef.current);
        if (!val.trim()) {
            abortRef.current = true;
            setResults([]); setStatus('idle'); setStreaming(false);
            return;
        }
        setStatus('connecting');
        debounceRef.current = setTimeout(() => runPrediction(val), 300);
    };

    const handleExample = (ex) => { setQuery(ex); runPrediction(ex); };

    const handleRetryConnect = () => {
        retryCountRef.current = 0;
        setStatus('idle');
        openSocket();
    };

    // ── Status label ──────────────────────────────────────────────
    const statusLabel = {
        idle: null,
        connecting: <span className="predict-status predict-status--pulse">⚡ Thinking…</span>,
        streaming: <span className="predict-status predict-status--pulse">🔮 Finding matches…</span>,
        done: <span className="predict-status predict-status--done">✓ {totalFound ?? results.length} match{(totalFound ?? results.length) !== 1 ? 'es' : ''} found</span>,
        error: <span className="predict-status predict-status--error">⚠ Could not reach backend</span>,
        offline: <span className="predict-status predict-status--error">⚠ Backend offline</span>,
    }[status];

    return (
        <main className="predict-page">
            <div className="container">
                {/* ── Header ── */}
                <div className="predict-header animate-fade-up">
                    <div className="predict-icon">🔮</div>
                    <h1 className="predict-title">Realtime Movie Predictor</h1>
                    <p className="predict-subtitle">
                        Describe what you want to watch — in plain English.<br />
                        Our AI predicts the best matches <em>as you type</em>.
                    </p>
                </div>

                {/* ── Offline banner ── */}
                {status === 'offline' && (
                    <div className="predict-offline-banner animate-fade-up">
                        <span>🔌 Backend is not reachable. Make sure uvicorn is running on port 8000.</span>
                        <button className="predict-retry-btn" onClick={handleRetryConnect}>↺ Retry</button>
                    </div>
                )}

                {/* ── Input ── */}
                <div className={`predict-input-wrap animate-fade-up ${status === 'offline' ? 'predict-input-wrap--disabled' : ''}`}>
                    <textarea
                        className="predict-textarea"
                        placeholder="e.g. A mind-bending sci-fi thriller with a dark twist ending…"
                        value={query}
                        onChange={e => handleInput(e.target.value)}
                        rows={3}
                        autoFocus
                        disabled={status === 'offline'}
                    />
                    <div className="predict-input-footer">
                        {statusLabel}
                        {query && status !== 'offline' && (
                            <button className="predict-clear-btn" onClick={() => handleInput('')}>✕ Clear</button>
                        )}
                    </div>
                </div>

                {/* ── Example prompts ── */}
                {!query && status !== 'offline' && (
                    <div className="predict-examples animate-fade-up">
                        <p className="predict-examples__label">✨ Try an example</p>
                        <div className="predict-examples__grid">
                            {EXAMPLES.map(ex => (
                                <button key={ex} className="predict-example-chip" onClick={() => handleExample(ex)}>
                                    "{ex}"
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {/* ── Results ── */}
                {results.length > 0 && (
                    <div className="predict-results">
                        <h2 className="predict-results__heading">
                            🎬 Top Predictions
                            {streaming && <span className="predict-live-badge">LIVE</span>}
                        </h2>
                        <div className="predict-cards">
                            {results.map((movie, i) => (
                                <PredictCard key={movie.id} movie={movie} rank={i + 1} />
                            ))}
                        </div>
                    </div>
                )}

                {/* ── Empty state ── */}
                {status === 'done' && results.length === 0 && (
                    <div className="predict-empty animate-fade-up">
                        <div className="predict-empty__icon">🎭</div>
                        <p>No strong matches found. Try different keywords or be more descriptive!</p>
                    </div>
                )}
            </div>
        </main>
    );
}

function PredictCard({ movie, rank }) {
    const confidence = movie.confidence ?? 0;
    const barColor = confidence > 75 ? '#22c55e' : confidence > 50 ? '#f59e0b' : '#e63b6f';

    return (
        <Link to={`/movie/${movie.id}`} className="predict-card animate-fade-up">
            <div className="predict-card__rank">#{rank}</div>
            <div className="predict-card__poster-wrap">
                {movie.poster ? (
                    <img src={movie.poster} alt={movie.title} className="predict-card__poster" />
                ) : (
                    <div className="predict-card__poster-placeholder">🎬</div>
                )}
            </div>
            <div className="predict-card__info">
                <h3 className="predict-card__title">{movie.title}</h3>
                <div className="predict-card__meta">
                    <span className="rating-badge">★ {movie.rating?.toFixed(1)}</span>
                    <span className="predict-card__year">{movie.year}</span>
                    {movie.genres?.slice(0, 2).map(g => (
                        <span key={g} className="genre-pill genre-pill--sm">{g}</span>
                    ))}
                </div>
                <p className="predict-card__overview">{movie.overview}</p>
                <div className="confidence-wrap">
                    <span className="confidence-label">Match confidence</span>
                    <span className="confidence-pct" style={{ color: barColor }}>{confidence.toFixed(1)}%</span>
                    <div className="confidence-bar">
                        <div className="confidence-bar__fill" style={{ width: `${confidence}%`, background: barColor }} />
                    </div>
                </div>
            </div>
        </Link>
    );
}

