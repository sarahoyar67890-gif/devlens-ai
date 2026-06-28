"""
DevLens AI - FastAPI Application
"""
import asyncio
import json
from fastapi import FastAPI, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from loguru import logger
from datetime import datetime
import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backend.config import settings
from backend.models.database import init_db, get_db, AnalysisCache
from backend.core.pipeline import AnalysisPipeline
from backend.services.ai_service import AIAnalysisService

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "frontend", "templates"))

_progress_store: dict[str, list] = {}


@app.on_event("startup")
async def startup():
    init_db()
    os.makedirs("data", exist_ok=True)
    logger.info(f"DevLens AI v{settings.APP_VERSION} started")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/dashboard/{username}", response_class=HTMLResponse)
async def dashboard(request: Request, username: str):
    return templates.TemplateResponse("dashboard.html", {"request": request, "username": username})


class AnalyzeRequest(BaseModel):
    username: str
    force_refresh: bool = False


@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest, db: Session = Depends(get_db)):
    username = req.username.strip().lower()
    if not username:
        raise HTTPException(status_code=400, detail="Username required")

    if not req.force_refresh:
        cached = db.query(AnalysisCache).filter_by(github_username=username).first()
        if cached and cached.analysis_result:
            return {"status": "cached", "username": username, "data": cached.analysis_result}

    _progress_store[username] = []

    def on_progress(step: str, pct: int):
        _progress_store[username].append({"step": step, "pct": pct})

    pipeline = AnalysisPipeline()
    try:
        result = await pipeline.run(username, progress_callback=on_progress)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Pipeline error for {username}: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    existing = db.query(AnalysisCache).filter_by(github_username=username).first()
    if existing:
        existing.analysis_result = result
        existing.updated_at = datetime.utcnow()
    else:
        db.add(AnalysisCache(github_username=username, analysis_result=result))
    db.commit()

    return {"status": "ok", "username": username, "data": result}


@app.get("/api/progress/{username}")
async def progress_stream(username: str):
    async def generator():
        sent = 0
        for _ in range(120):
            events = _progress_store.get(username, [])
            while sent < len(events):
                ev = events[sent]
                yield f"data: {json.dumps(ev)}\n\n"
                sent += 1
            if events and events[-1].get("pct") == 100:
                yield 'data: {"done": true}\n\n'
                break
            await asyncio.sleep(1)
    return StreamingResponse(generator(), media_type="text/event-stream")


@app.get("/api/result/{username}")
async def get_result(username: str, db: Session = Depends(get_db)):
    cached = db.query(AnalysisCache).filter_by(github_username=username.lower()).first()
    if not cached or not cached.analysis_result:
        raise HTTPException(status_code=404, detail="No analysis found. Run /api/analyze first.")
    return {"status": "ok", "data": cached.analysis_result}


@app.post("/api/readme/{username}/{repo_name}")
async def generate_readme(username: str, repo_name: str, db: Session = Depends(get_db)):
    cached = db.query(AnalysisCache).filter_by(github_username=username.lower()).first()
    if not cached:
        raise HTTPException(status_code=404, detail="Analyze the profile first.")
    data = cached.analysis_result or {}
    repo = next((r for r in data.get("repos", []) if r["name"] == repo_name), None)
    if not repo:
        raise HTTPException(status_code=404, detail="Repo not found.")
    ai = AIAnalysisService()
    readme = await ai.generate_readme(repo, repo.get("analysis", {}))
    return {"readme": readme}


@app.get("/api/search/{username}")
async def semantic_search(username: str, q: str, db: Session = Depends(get_db)):
    cached = db.query(AnalysisCache).filter_by(github_username=username.lower()).first()
    if not cached:
        raise HTTPException(status_code=404, detail="No analysis found.")
    repos = cached.analysis_result.get("repos", [])
    q_lower = q.lower()
    results = [
        r for r in repos
        if q_lower in r.get("name", "").lower()
        or q_lower in r.get("description", "").lower()
        or q_lower in " ".join(r.get("topics", [])).lower()
        or q_lower in r.get("language", "").lower()
        or q_lower in " ".join(r.get("analysis", {}).get("tech_tags", [])).lower()
    ]
    return {"query": q, "results": results[:10]}


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}
