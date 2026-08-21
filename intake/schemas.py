"""Validated public request and response shapes for submission intake."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from intake.intents import SubmissionMetadata


class VerificationRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    turnstile_token: str = Field(min_length=1, max_length=4096)


class VerificationExchange(BaseModel):
    token: str = Field(min_length=32, max_length=512)


class VerificationRequested(BaseModel):
    status: Literal["verification_requested"]


class VerificationSession(BaseModel):
    csrf_token: str


class SubmissionCapabilities(BaseModel):
    status: str
    follow_up: str
    withdrawal: str


class SubmissionReceipt(BaseModel):
    submission_id: str
    status: Literal["received"]
    capabilities: SubmissionCapabilities


class _StrictCapabilityInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class StatusQuery(_StrictCapabilityInput):
    submission_id: str = Field(min_length=1, max_length=64)
    capability: str = Field(min_length=32, max_length=512)


class FollowUpMetadata(_StrictCapabilityInput):
    capability: str = Field(min_length=32, max_length=512)
    message: str = Field(min_length=1, max_length=4000)


class WithdrawalRequest(_StrictCapabilityInput):
    capability: str = Field(min_length=32, max_length=512)


class PublicSubmissionStatus(BaseModel):
    submission_id: str
    status: str
    public_reason: str | None
    evidence_state: str
    integration_state: str
    updated_at: str


class OwnerMutationReceipt(BaseModel):
    submission_id: str
    status: Literal["under_review", "withdrawn"]


__all__ = [
    "FollowUpMetadata",
    "OwnerMutationReceipt",
    "PublicSubmissionStatus",
    "StatusQuery",
    "SubmissionMetadata",
    "SubmissionReceipt",
    "VerificationExchange",
    "VerificationRequest",
    "VerificationRequested",
    "VerificationSession",
    "WithdrawalRequest",
]
