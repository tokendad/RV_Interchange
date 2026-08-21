"""Validated public request and response shapes for submission intake."""

from typing import Literal

from pydantic import BaseModel, Field

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


__all__ = [
    "SubmissionMetadata",
    "SubmissionReceipt",
    "VerificationExchange",
    "VerificationRequest",
    "VerificationRequested",
    "VerificationSession",
]
