import axios from 'axios';

const BASE = 'http://localhost:8000';

const api = axios.create({
    baseURL: BASE,
    timeout: 10000,
});

export const getGenres = () => api.get('/genres').then(r => r.data);
export const getTrending = (limit = 20) => api.get(`/trending?limit=${limit}`).then(r => r.data);
export const getMovies = (genre = null, page = 1, pageSize = 20) =>
    api.get('/movies', { params: { genre, page, page_size: pageSize } }).then(r => r.data);
export const getMovieDetail = (id) => api.get(`/movies/${id}`).then(r => r.data);
export const getRecommendations = (id, n = 10) =>
    api.get(`/movies/${id}/recommendations?n=${n}`).then(r => r.data);
export const searchMovies = (q) => api.get(`/search?q=${encodeURIComponent(q)}`).then(r => r.data);

// ── Realtime Prediction ────────────────────────────────────────────
export const predictMovies = (query, n = 10) =>
    api.post('/predict', { query, n }).then(r => r.data);

export const createPredictSocket = () =>
    new WebSocket(`ws://localhost:8000/predict/stream`);
