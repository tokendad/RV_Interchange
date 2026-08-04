"""
api/main.py — the Public API (Docs/Inital_Design/Stage 2 (Frontend)/
RV_Interchange_API_Design.md §4). Read-only, anonymous, query-oriented.
No Dealer API, no auth, no write endpoints — see this plan's Phases section
for why those are deferred.
"""

import logging
import os
import sqlite3
import sys
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "Docs" / "Tools"))

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.services import IdentifierService, ReplacementService, SearchService
from api.schemas import ReplacementsResponse, ResolveResponse, SearchResponse

DB_PATH = str(Path(__file__).resolve().parent.parent / "Docs" / "Tools" / "components.db")

# Defaults to a repo-local `logs/` dir so tests and local `uvicorn api.main:app` runs
# work without root permissions; the Docker image overrides this to /app/logs, a
# mounted volume, via the RVI_LOG_DIR env var (see api/Dockerfile and docker-compose.yaml).
LOG_DIR = Path(os.environ.get(
    "RVI_LOG_DIR", str(Path(__file__).resolve().parent.parent / "logs")))
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("rvinterchange.api")
logger.setLevel(logging.INFO)
if not logger.handlers:
    file_handler = RotatingFileHandler(
        LOG_DIR / "api.log", maxBytes=1_000_000, backupCount=3)
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(file_handler)
    logger.addHandler(logging.StreamHandler())

app = FastAPI(title="RV Interchange Public API", version="1")

# Personal-use-only CORS: the test website (Task 10) is the one and only browser
# caller, always on this fixed local port, reachable from localhost or the LAN. Not
# "*" — see the Docker deployment plan's note that this stack is not public.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8485", "http://127.0.0.1:8485"],
    allow_origin_regex=r"http://(192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}):8485",
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = (time.monotonic() - start) * 1000
    logger.info("%s %s -> %s (%.1fms)",
                request.method, request.url.path, response.status_code, duration_ms)
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "internal error"})


def _readonly_connection(path):
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def get_conn():
    conn = _readonly_connection(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


@app.get("/public/v1/resolve", response_model=ResolveResponse)
def resolve(ns: str, identifier: str, conn=Depends(get_conn)):
    result = IdentifierService.resolve(conn, ns, identifier)
    if result is None:
        raise HTTPException(status_code=404, detail="identifier not found")
    return result


@app.get("/public/v1/replacements", response_model=ReplacementsResponse)
def replacements(ns: str, identifier: str, conn=Depends(get_conn)):
    resolved = IdentifierService.resolve(conn, ns, identifier)
    if resolved is None:
        raise HTTPException(status_code=404, detail="identifier not found")
    result = ReplacementService.get_replacements(conn, resolved["component_id"], ns)
    if result is None:
        raise HTTPException(status_code=404, detail="identifier not found")
    return result


@app.get("/public/v1/search", response_model=SearchResponse)
def search(q: str, limit: int = Query(20, ge=1, le=100), conn=Depends(get_conn)):
    return SearchService.search(conn, q, limit=limit)
