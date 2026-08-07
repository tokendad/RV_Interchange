"""api/schemas.py — Public API response shapes. Never includes interchange_code
(ARCHITECTURE-Interchange_Core.md §2 visibility rule) or any observation/candidate/review
internals (RV_Interchange_API_Design.md §10, "Hidden from public users"). Component
attributes are exposed via AttributeOut, which deliberately omits `provenance` and
`source_observation_id` — those stay internal even though the underlying
component_attributes row carries them."""

from typing import Optional

from pydantic import BaseModel


class IdentifierOut(BaseModel):
    ns: str
    value: str


class AttributeOut(BaseModel):
    name: str
    qualifier: str = ""
    value: str | float | bool
    unit: Optional[str] = None


class SearchResultItem(BaseModel):
    component_id: str
    label: str
    manufacturer: Optional[str] = None
    part_type: Optional[str] = None
    identifiers: list[IdentifierOut]
    attributes: list[AttributeOut] = []


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]


class ResolveResponse(BaseModel):
    component_id: str
    manufacturer: Optional[str] = None
    part_type: Optional[str] = None
    identifiers: list[IdentifierOut]
    attributes: list[AttributeOut] = []


class RequiredPartOut(BaseModel):
    ns: str
    value: str
    role: Optional[str] = None
    manufacturer: Optional[str] = None


class CaveatOut(BaseModel):
    text: str
    blocking: bool


class ReplacementItem(BaseModel):
    part: str
    fit: str
    rank: int
    required_parts: list[RequiredPartOut] = []
    caveats: list[CaveatOut] = []


class SupersessionItem(BaseModel):
    part: str
    note: Optional[str] = None


class ReplacementsResponse(BaseModel):
    source: str
    replacements: list[ReplacementItem]
    supersessions: list[SupersessionItem] = []
