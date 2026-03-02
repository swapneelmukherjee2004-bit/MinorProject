import { create } from 'zustand';
import { persist } from 'zustand/middleware';

const useMovieStore = create(
    persist(
        (set, get) => ({
            watchlist: [],
            ratings: {},
            activeGenre: null,
            searchQuery: '',

            toggleWatchlist: (movie) => {
                const { watchlist } = get();
                const exists = watchlist.some(m => m.id === movie.id);
                set({
                    watchlist: exists
                        ? watchlist.filter(m => m.id !== movie.id)
                        : [...watchlist, movie],
                });
            },

            isInWatchlist: (movieId) => get().watchlist.some(m => m.id === movieId),

            setRating: (movieId, rating) =>
                set(state => ({ ratings: { ...state.ratings, [movieId]: rating } })),
            getRating: (movieId) => get().ratings[movieId] || 0,

            setActiveGenre: (genre) => set({ activeGenre: genre }),
            setSearchQuery: (q) => set({ searchQuery: q }),
        }),
        { name: 'cinematch-store' }
    )
);

export default useMovieStore;
