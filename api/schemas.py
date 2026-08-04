"""api/schemas.py — Public API response shapes. Never includes interchange_code
(ARCHITECTURE-Interchange_Core.md §2 visibility rule) or any observation/candidate/review
internals (RV_Interchange_API_Design.md §10, "Hidden from public users")."""

from typing import Optional

from pydantic import BaseModel


class IdentifierOut(BaseModel):
    ns: str
    value: str


class SearchResultItem(BaseModel):
    component_id: str
    label: str
    identifiers: list[IdentifierOut]


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]


class ResolveResponse(BaseModel):
    component_id: str
    identifiers: list[IdentifierOut]


class ReplacementItem(BaseModel):
    part: str
    fit: str
    rank: int
    summary: Optional[str] = None


class SupersessionItem(BaseModel):
    part: str
    note: Optional[str] = None


class ReplacementsResponse(BaseModel):
    source: str
    replacements: list[ReplacementItem]
    supersessions: list[SupersessionItem] = []
