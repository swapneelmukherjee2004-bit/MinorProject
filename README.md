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

## 🚦 Deployment

### **Backend (Hugging Face — Truly Free)**
1.  Go to [huggingface.co/spaces](https://huggingface.co/new-space).
2.  **SDK**: Select **Docker**.
3.  **Upload**: Drag and drop all files from your `movie-backend` folder (including the new `Dockerfile`).
4.  **Automatic**: It will build and give you a public URL (e.g., `https://user-cinematch-api.hf.space`).

### **Backend Alternatives (Koyeb/Railway)**
*Note: These may require a credit card for verification.*
-   **Koyeb**: Root Directory: `/movie-backend`.
-   **Railway**: Root Directory: `movie-backend`.

### **Frontend (Vercel)**
1.  Connect repo -> Root Directory: `movie-frontend`.
2.  Add Environment Variable: `VITE_API_URL` = your Hugging Face (or other) backend URL.

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
