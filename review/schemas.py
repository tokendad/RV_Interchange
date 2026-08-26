from typing import Literal

from pydantic import BaseModel, Field


class ClaimDecision(BaseModel):
    action: Literal["accepted", "rejected", "duplicate"]
    reason_code: str = Field(min_length=1, max_length=80)
    note: str | None = Field(default=None, max_length=2_000)
    idempotency_key: str = Field(min_length=1, max_length=200)


class InformationRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2_000)
    idempotency_key: str = Field(min_length=1, max_length=200)


class Assessment(BaseModel):
    assessment: Literal["endorse", "dispute", "spam"]
    reason: str = Field(min_length=1, max_length=2_000)
    idempotency_key: str = Field(min_length=1, max_length=200)
