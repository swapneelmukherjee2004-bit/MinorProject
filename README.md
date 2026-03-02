# CineMatch — Unlimited Movie Discovery & Recommendations

CineMatch is a premium movie discovery and recommendation platform. It leverages the official IMDb bulk dataset (250,000+ movies) to provide a lightning-fast, unlimited browsing experience combined with a sophisticated AI-powered recommendation engine.

![Hero Showcase](https://raw.githubusercontent.com/swapneelmukherjee2004-bit/MinorProject/main/movie-frontend/public/vite.svg) *Add your own screenshot here!*

## ✨ Key Features

- **🚀 Massive Local Database**: Powered by a local SQLite database containing over 47,000 high-quality IMDb titles.
- **🎨 Dark Glassmorphism UI**: A stunning, modern interface built with React and custom CSS.
- **🔍 Intelligent Search**: Real-time search across titles, genres, and overviews with prioritized visual results.
- **🤖 AI Recommendations**: Content-based filtering using **TF-IDF** and **Cosine Similarity** to suggest movies you'll actually love.
- **🖼️ Auto-Enrichment**: Dynamically fetches posters, backdrops, and cast info in the background from `imdbapi.dev`.
- **💖 Watchlist**: Save your favorites to a personalized list.

## 🛠️ Technology Stack

- **Frontend**: React 18, Vite, Lucide Icons
- **Backend**: FastAPI (Python 3), Uvicorn
- **Database**: SQLite
- **Machine Learning**: Scikit-Learn (TF-IDF Vectorizer)
- **API Client**: HTTPX (with robust retry logic)

## 🚦 Getting Started

### 1. Backend Setup
```bash
cd movie-backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Download and process the IMDb dataset (~1 min)
python download_dataset.py

# Start the API server
uvicorn main:app --reload
```

### 2. Frontend Setup
```bash
cd movie-frontend
npm install
npm run dev
```

Visit **http://localhost:5173** (or the port shown in your terminal) to start watching!

## 📦 Project Structure

```text
.
├── movie-backend/
│   ├── main.py            # FastAPI Entry Point
│   ├── db.py              # SQLite Query Layer
│   ├── recommender.py     # TF-IDF Engine
│   ├── imdb_client.py     # API Enrichment Wrapper
│   └── download_dataset.py# Data Processing Script
└── movie-frontend/
    ├── src/
    │   ├── pages/         # Home, Search, Predict, Watchlist
    │   └── components/    # Glassmorphism Components
    └── App.jsx            # Main Router
```

## 🛡️ License
Distributed under the MIT License. See `LICENSE` for more information.

---
Built with ❤️ by [Swapneel Mukherjee](https://github.com/swapneelmukherjee2004-bit)
