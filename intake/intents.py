"""Strict untrusted-input contracts for public submission intents."""

from __future__ import annotations

import re
import unicodedata
from typing import Annotated, Any, Literal, Union
from urllib.parse import urlsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


Intent = Literal[
    "installation_result",
    "documentation_citation",
    "data_correction",
]
ClaimType = Literal[
    "observed_identifier",
    "attribute",
    "installation_outcome",
    "document_assertion",
    "supersession_assertion",
    "correction",
]

_ABSOLUTE_URI_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
_URL_KEY_ALIASES = {"href", "link", "uri", "url", "website"}


class _StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def validate_https_url(value: str) -> str:
    """Accept a bounded HTTPS URL with no embedded user credentials."""
    if not isinstance(value, str):
        raise ValueError("invalid source URL")
    if len(value.encode("utf-8")) > 2048 or any(
        unicodedata.category(character).startswith("C") for character in value
    ):
        raise ValueError("invalid source URL")
    try:
        parsed = urlsplit(value)
        parsed.port
    except ValueError:
        raise ValueError("invalid source URL") from None
    if (
        parsed.scheme.lower() != "https"
        or not parsed.netloc
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError("invalid source URL")
    return value


def _canonical_key_tokens(key: str) -> tuple[str, ...]:
    normalized = unicodedata.normalize("NFKC", key)
    if any(unicodedata.category(character).startswith("C") for character in normalized):
        raise ValueError("invalid proposed claim")

    separated: list[str] = []
    for index, character in enumerate(normalized):
        previous = normalized[index - 1] if index else ""
        following = normalized[index + 1] if index + 1 < len(normalized) else ""
        if (
            separated
            and character.isupper()
            and (
                previous.islower()
                or previous.isdigit()
                or (previous.isupper() and following.islower())
            )
        ):
            separated.append("_")
        separated.append(character.casefold())

    tokens: list[str] = []
    pending: list[str] = []
    for character in "".join(separated):
        if character.isalnum():
            pending.append(character)
        elif pending:
            tokens.append("".join(pending))
            pending = []
    if pending:
        tokens.append("".join(pending))
    if not tokens:
        raise ValueError("invalid proposed claim")
    return tuple(tokens)


def _reject_prohibited_key(tokens: tuple[str, ...]) -> None:
    singular = tuple(token[:-1] if token.endswith("s") else token for token in tokens)
    compact = "".join(tokens)
    if any(token in {"canonical", "confidence", "graph", "tier"} for token in singular):
        raise ValueError("canonical and graph mutations are not accepted")
    if (
        "canonical" in compact
        or "confidence" in compact
        or "sourcetier" in compact
        or "observationid" in compact
        or "edgeid" in compact
        or compact.startswith("graph")
        or any(
            graph_namespace in compact
            for graph_namespace in ("graphchange", "graphmutation", "graphoperation")
        )
        or any(
            operation in compact
            for operation in ("createedge", "deleteedge", "updateedge")
        )
    ):
        raise ValueError("canonical and graph mutations are not accepted")
    if any(token == "mutation" for token in singular):
        raise ValueError("canonical and graph mutations are not accepted")
    pairs = set(zip(singular, singular[1:]))
    if pairs.intersection({("observation", "id"), ("edge", "id")}):
        raise ValueError("canonical and graph mutations are not accepted")
    if "edge" in singular and any(
        token in {"create", "delete", "operation", "update"} for token in singular
    ):
        raise ValueError("canonical and graph mutations are not accepted")


def _validate_url_like(tokens: tuple[str, ...], value: Any) -> None:
    compact = "".join(tokens)
    aliases = {token[:-1] if token.endswith("s") else token for token in tokens}
    if not (
        aliases.intersection(_URL_KEY_ALIASES)
        or any(compact.endswith((alias, f"{alias}s")) for alias in _URL_KEY_ALIASES)
    ):
        return
    if isinstance(value, list):
        for item in value:
            validate_https_url(item)
        return
    validate_https_url(value)


def _validate_url_shaped_string(value: str) -> None:
    candidate = value.lstrip()
    if candidate.startswith("//") or _ABSOLUTE_URI_SCHEME.match(candidate):
        validate_https_url(value)


def _validate_untrusted_value(value: Any) -> Any:
    if isinstance(value, dict):
        for key, nested in value.items():
            if not isinstance(key, str):
                raise ValueError("invalid proposed claim")
            tokens = _canonical_key_tokens(key)
            _reject_prohibited_key(tokens)
            _validate_url_like(tokens, nested)
            _validate_untrusted_value(nested)
    elif isinstance(value, list):
        for nested in value:
            _validate_untrusted_value(nested)
    elif isinstance(value, str):
        _validate_url_shaped_string(value)
    elif value is not None and not isinstance(value, (str, int, float, bool)):
        raise ValueError("invalid proposed claim")
    return value


class EdgeLocator(_StrictInput):
    """Stable logical edge identity, never a rebuildable row identifier."""

    type: str = Field(min_length=1, max_length=64)
    from_component_id: str = Field(min_length=1, max_length=128)
    to_component_id: str | None = Field(default=None, min_length=1, max_length=128)
    group_key: str | None = Field(default=None, min_length=1, max_length=128)

    @model_validator(mode="after")
    def require_one_destination(self):
        if (self.to_component_id is None) == (self.group_key is None):
            raise ValueError("edge locator requires exactly one destination")
        return self


class InstallationResultContext(_StrictInput):
    kind: Literal["installation_result"]
    outcome: Literal["success", "failure"]
    notes: str = Field(min_length=1, max_length=4000)


class DocumentationCitationContext(_StrictInput):
    kind: Literal["documentation_citation"]
    source_url: str
    document_title: str = Field(min_length=1, max_length=512)
    citation: str = Field(min_length=1, max_length=4000)

    _source_url = field_validator("source_url")(validate_https_url)


class DataCorrectionContext(_StrictInput):
    kind: Literal["data_correction"]
    reason: str = Field(min_length=20, max_length=4000)
    source_url: str | None = None

    @field_validator("source_url")
    @classmethod
    def validate_optional_source_url(cls, value: str | None) -> str | None:
        return None if value is None else validate_https_url(value)


SubmissionContext = Annotated[
    Union[
        InstallationResultContext,
        DocumentationCitationContext,
        DataCorrectionContext,
    ],
    Field(discriminator="kind"),
]


class ClaimInput(_StrictInput):
    claim_type: ClaimType
    proposed: dict[str, Any] = Field(min_length=1, max_length=50)

    @field_validator("proposed")
    @classmethod
    def reject_canonical_mutations(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _validate_untrusted_value(value)


class SubmissionMetadata(_StrictInput):
    intent: Intent
    summary: str = Field(min_length=20, max_length=4000)
    target_component_id: str | None = Field(default=None, min_length=1, max_length=128)
    target_edge: EdgeLocator | None = None
    target_namespace: str | None = Field(default=None, min_length=1, max_length=64)
    target_identifier: str | None = Field(default=None, min_length=1, max_length=256)
    priority: Literal["normal", "high", "safety"] = "normal"
    context: SubmissionContext
    claims: list[ClaimInput] = Field(min_length=1, max_length=50)
    terms_version: str = Field(min_length=1, max_length=64)
    evidence_license_version: str = Field(min_length=1, max_length=64)
    consented: Literal[True]
    turnstile_token: str = Field(min_length=1, max_length=4096)

    @model_validator(mode="after")
    def require_matching_context(self):
        if self.intent != self.context.kind:
            raise ValueError("submission context does not match intent")
        return self
