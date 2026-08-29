from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


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


class DraftCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_type: Literal[
        "manufacturer_page", "manufacturer_pdf", "manual_measurement",
        "dataplate_photo", "dealer_call", "field_report", "other",
        "retailer_page", "retailer_prose", "forum_post",
    ]
    source_name: str = Field(min_length=1, max_length=300)
    source_url: HttpUrl | None = None
    raw_content: str = Field(min_length=1, max_length=12_000)
    extracted: dict[str, Any]
    claim_ids: list[str] = Field(min_length=1, max_length=100)
    artifact_ids: list[str] = Field(default_factory=list, max_length=100)
    idempotency_key: str = Field(min_length=1, max_length=200)

    @field_validator("claim_ids", "artifact_ids")
    @classmethod
    def ids_are_unique_nonempty_strings(cls, value: list[str]) -> list[str]:
        if any(not item for item in value) or len(value) != len(set(value)):
            raise ValueError("IDs must be unique nonempty strings")
        return value


class DraftReady(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(ge=1)
