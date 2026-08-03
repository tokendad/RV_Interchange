"""
api/main.py — the Public API (Docs/Inital_Design/Stage 2 (Frontend)/
RV_Interchange_API_Design.md §4). Read-only, anonymous, query-oriented.
No Dealer API, no auth, no write endpoints — see this plan's Phases section
for why those are deferred.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "Docs" / "Tools"))

from fastapi import Depends, FastAPI, HTTPException
from interchange_schema import init_db

from api.services import IdentifierService, ReplacementService
from api.schemas import ReplacementsResponse, ResolveResponse

DB_PATH = str(Path(__file__).resolve().parent.parent / "Docs" / "Tools" / "components.db")

app = FastAPI(title="RV Interchange Public API", version="1")


def get_conn():
    conn = init_db(DB_PATH)
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
    result = ReplacementService.get_replacements(conn, resolved["component_id"])
    if result is None:
        raise HTTPException(status_code=404, detail="identifier not found")
    return result
