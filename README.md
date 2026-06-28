# ⬡ DevLens AI — GitHub Portfolio Analyzer

> AI-powered GitHub profile analyzer. Drop a username, get a complete developer profile with skills, repo rankings, internship readiness scores, career roadmap, and more. 100% local. No paid APIs.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🧠 AI Repo Analysis | Every repo gets purpose, architecture, complexity, quality scores via local LLM |
| 📡 Skill Radar | Beautiful radar chart across 10 dimensions |
| 💼 Internship Readiness | Scores 0–100 for 7 different roles |
| 🗺️ Career Roadmap | Personalized next steps, courses, books, timeline |
| 🏆 Repo Rankings | Most popular, complex, documented, original |
| 📝 README Generator | AI writes professional README for any repo |
| 🔍 Semantic Search | Search repos by intent/tech |
| 📅 Dev Timeline | Visual growth chart over time |
| 💾 SQLite Caching | Results cached — no re-fetching |

---

## 🛠 Tech Stack

- **Backend**: Python 3.12 + FastAPI
- **Frontend**: HTML + CSS + Vanilla JS (no frameworks)
- **AI**: Ollama (local LLM — Llama3/Qwen/Gemma)
- **Database**: SQLite
- **Charts**: Chart.js
- **Data**: GitHub REST API

---

## 🚀 Quick Start

### 1. Clone & setup
```bash
git clone <repo>
cd devlens
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure (optional — improves GitHub rate limit)
```bash
cp .env.example .env
# Edit .env and add your GitHub token
```

### 3. Setup Ollama (optional — for full AI features)
```bash
# Install Ollama from https://ollama.com
ollama pull llama3
# or: ollama pull qwen2 / ollama pull gemma
```

### 4. Run
```bash
python run.py
```

Open → [http://localhost:8000](http://localhost:8000)

---

## 📁 Project Structure

```
devlens/
├── main.py                    # FastAPI app + all routes
├── run.py                     # Startup script
├── requirements.txt
├── .env.example
├── backend/
│   ├── config.py              # App settings
│   ├── core/
│   │   └── pipeline.py        # Analysis orchestrator
│   ├── services/
│   │   ├── github_service.py  # GitHub API fetching
│   │   └── ai_service.py      # AI analysis + fallbacks
│   └── models/
│       └── database.py        # SQLite models
├── frontend/
│   ├── templates/
│   │   ├── index.html         # Landing page
│   │   └── dashboard.html     # Results dashboard
│   └── static/
│       ├── css/
│       │   ├── main.css       # Landing styles
│       │   └── dashboard.css  # Dashboard styles
│       └── js/
│           ├── main.js        # Landing page JS
│           └── dashboard.js   # Dashboard + charts JS
└── data/                      # SQLite DB (auto-created)
```

---

## ⚙️ Configuration

| Variable | Default | Description |
|---|---|---|
| `GITHUB_TOKEN` | `` | GitHub personal access token (raises rate limit 60→5000/hr) |
| `OLLAMA_MODEL` | `llama3` | Ollama model name (`llama3`, `qwen2`, `gemma`) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `APP_PORT` | `8000` | Server port |

---

## 🤖 Without Ollama

The app works **without Ollama**. It falls back to rule-based analysis using:
- GitHub API data (stars, size, topics, languages, README presence)
- Heuristic scoring for complexity, quality, documentation
- Keyword-based skill detection

With Ollama you get: richer descriptions, smarter summaries, better README generation.

---

## 🔑 Getting GitHub Token

1. Go to [github.com/settings/tokens](https://github.com/settings/tokens)
2. Generate new token (classic)
3. Select scope: `public_repo`
4. Copy token → paste in `.env` as `GITHUB_TOKEN`

---

## 📊 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Landing page |
| `GET` | `/dashboard/{username}` | Dashboard page |
| `POST` | `/api/analyze` | Start analysis |
| `GET` | `/api/result/{username}` | Get cached result |
| `GET` | `/api/progress/{username}` | SSE progress stream |
| `POST` | `/api/readme/{username}/{repo}` | Generate README |
| `GET` | `/api/search/{username}?q=` | Search repos |

---

## 👨‍💻 Built by

Hamza — CS Student, ML & AI Engineer in training.

> "Built for developers who want real insight into their own GitHub portfolio."
