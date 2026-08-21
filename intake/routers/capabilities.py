"""Purpose-bound owner capability routes for quarantined submissions."""

from __future__ import annotations

import tempfile
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from pydantic import ValidationError
from python_multipart.exceptions import MultipartParseError
from python_multipart.multipart import MultipartParser, parse_options_header
from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from intake import db
from intake.artifacts import (
    MAX_UPLOAD_BYTES,
    READ_CHUNK_BYTES,
    ArtifactRejected,
    ArtifactStorageError,
    ArtifactStore,
    StoredArtifact,
)
from intake.config import Settings
from intake.repositories import (
    ArtifactRepository,
    CapabilityRepository,
    RepositoryConflict,
    SubmissionRepository,
)
from intake.schemas import (
    FollowUpMetadata,
    OwnerMutationReceipt,
    PublicSubmissionStatus,
    StatusQuery,
    WithdrawalRequest,
)
from intake.security import TokenCodec


router = APIRouter(prefix="/submission/v1")

_MAX_ARTIFACTS = 5
_MAX_TOTAL_FILE_BYTES = 25 * 1024 * 1024
_MAX_MULTIPART_BYTES = _MAX_TOTAL_FILE_BYTES + 1024 * 1024
_MAX_MEMORY_PREFIX_BYTES = 16 * 1024
_UNVERIFIED_RETENTION = timedelta(days=7)
_NOT_FOUND_DETAIL = "capability not found"


def _now(request: Request) -> datetime:
    value = request.app.state.clock()
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise RuntimeError("application clock must return an aware datetime")
    return value.astimezone(timezone.utc)


def _not_found() -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, _NOT_FOUND_DETAIL)


def _capability_secret(value: Any) -> str:
    if not isinstance(value, str) or not 32 <= len(value) <= 512:
        raise _not_found()
    return value


def _digest(request: Request, capability: Any) -> str:
    secret = _capability_secret(capability)
    return TokenCodec(request.app.state.settings.read_key("token")).digest(secret)


def _require_capability(
    repository: CapabilityRepository,
    submission_id: str,
    purpose: str,
    token_digest: str,
    now: str,
    *,
    consume: bool = False,
) -> None:
    if (
        repository.authorize(
            submission_id, purpose, token_digest, now, consume=consume
        )
        is None
    ):
        raise _not_found()


def _parse_follow_up(raw: str) -> FollowUpMetadata:
    try:
        return FollowUpMetadata.model_validate_json(raw)
    except ValidationError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "invalid follow-up metadata",
        ) from None


def _upload_size(upload: UploadFile) -> int:
    if isinstance(upload.size, int):
        return upload.size
    try:
        position = upload.file.tell()
        upload.file.seek(0, 2)
        size = upload.file.tell()
        upload.file.seek(position)
    except (AttributeError, OSError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "artifact rejected") from None
    if not isinstance(size, int) or size < 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "artifact rejected")
    return size


def _check_upload_limits(artifacts: list[UploadFile]) -> None:
    if len(artifacts) > _MAX_ARTIFACTS:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE, "artifact limits exceeded"
        )
    sizes = [_upload_size(upload) for upload in artifacts]
    if any(size > MAX_UPLOAD_BYTES for size in sizes) or sum(sizes) > (
        _MAX_TOTAL_FILE_BYTES
    ):
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE, "artifact limits exceeded"
        )


def _artifact_values(artifact: StoredArtifact, now: datetime) -> dict[str, object]:
    return {
        "storage_key": artifact.storage_key,
        "original_name": artifact.original_name,
        "declared_media_type": artifact.declared_media_type,
        "detected_media_type": artifact.detected_media_type,
        "raw_sha256": artifact.raw_sha256,
        "stored_sha256": artifact.stored_sha256,
        "size_bytes": artifact.size_bytes,
        "width": artifact.width,
        "height": artifact.height,
        "scan_status": "clean",
        "retention_class": "unverified",
        "created_at": now.isoformat(),
        "purge_after": (now + _UNVERIFIED_RETENTION).isoformat(),
    }


def _discard(store: ArtifactStore, stored: list[StoredArtifact]) -> None:
    store.discard(artifact.storage_key for artifact in stored)


@router.post("/status-queries", response_model=PublicSubmissionStatus)
def status_query(request: Request, payload: StatusQuery):
    now = _now(request).isoformat()
    token_digest = _digest(request, payload.capability)
    with db.connect(request.app.state.settings.database_path) as conn:
        _require_capability(
            CapabilityRepository(conn),
            payload.submission_id,
            "status",
            token_digest,
            now,
        )
        public_status = SubmissionRepository(conn).public_status(payload.submission_id)
    if public_status is None:
        raise _not_found()
    return public_status


@router.post(
    "/submissions/{submission_id}/follow-ups",
    status_code=status.HTTP_201_CREATED,
    response_model=OwnerMutationReceipt,
)
def create_follow_up(
    request: Request,
    submission_id: str,
    metadata: Annotated[str, Form()],
    artifacts: Annotated[list[UploadFile], File()] = [],
):
    payload = _parse_follow_up(metadata)
    now = _now(request)
    now_text = now.isoformat()
    settings = request.app.state.settings
    token_digest = _digest(request, payload.capability)

    with db.connect(settings.database_path) as conn:
        _require_capability(
            CapabilityRepository(conn),
            submission_id,
            "follow_up",
            token_digest,
            now_text,
        )

    _check_upload_limits(artifacts)
    artifact_store = ArtifactStore(settings.artifact_root)
    stored_artifacts: list[StoredArtifact] = []
    try:
        for upload in artifacts:
            stored_artifacts.append(artifact_store.sanitize(upload, submission_id))
        with db.connect(settings.database_path) as conn:
            with db.transaction(conn):
                mutation_now_text = _now(request).isoformat()
                _require_capability(
                    CapabilityRepository(conn),
                    submission_id,
                    "follow_up",
                    token_digest,
                    mutation_now_text,
                    consume=True,
                )
                artifact_repository = ArtifactRepository(conn)
                artifact_ids = [
                    artifact_repository.create(
                        submission_id, _artifact_values(artifact, now)
                    )
                    for artifact in stored_artifacts
                ]
                SubmissionRepository(conn).append_follow_up(
                    submission_id,
                    {"message": payload.message, "artifact_ids": artifact_ids},
                    mutation_now_text,
                )
    except ArtifactRejected:
        _discard(artifact_store, stored_artifacts)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "artifact rejected") from None
    except ArtifactStorageError:
        _discard(artifact_store, stored_artifacts)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "artifact storage unavailable"
        ) from None
    except RepositoryConflict:
        _discard(artifact_store, stored_artifacts)
        raise HTTPException(
            status.HTTP_409_CONFLICT, "submission does not accept follow-up"
        ) from None
    except BaseException:
        _discard(artifact_store, stored_artifacts)
        raise

    return {"submission_id": submission_id, "status": "under_review"}


@router.post(
    "/submissions/{submission_id}/withdrawals",
    response_model=OwnerMutationReceipt,
)
def withdraw_submission(
    request: Request, submission_id: str, payload: WithdrawalRequest
):
    token_digest = _digest(request, payload.capability)
    try:
        with db.connect(request.app.state.settings.database_path) as conn:
            with db.transaction(conn):
                mutation_now_text = _now(request).isoformat()
                _require_capability(
                    CapabilityRepository(conn),
                    submission_id,
                    "withdrawal",
                    token_digest,
                    mutation_now_text,
                    consume=True,
                )
                SubmissionRepository(conn).withdraw(submission_id, mutation_now_text)
    except RepositoryConflict:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "submission cannot be withdrawn"
        ) from None
    return {"submission_id": submission_id, "status": "withdrawn"}


class _MultipartLimitExceeded(RuntimeError):
    pass


class _GuardRejected(RuntimeError):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail


class _FileLimitTracker:
    def __init__(
        self,
        settings: Settings,
        clock: Callable[[], datetime],
        submission_id: str,
    ):
        self.settings = settings
        self.clock = clock
        self.submission_id = submission_id
        self.file_count = 0
        self.total_file_bytes = 0
        self._current_file_bytes = 0
        self._current_is_file = False
        self._current_field: bytes | None = None
        self._metadata = bytearray()
        self._authenticated = False
        self._header_field = bytearray()
        self._header_value = bytearray()
        self._headers: dict[bytes, bytes] = {}

    @property
    def callbacks(self) -> dict[str, Callable[..., None]]:
        return {
            "on_part_begin": self.on_part_begin,
            "on_part_data": self.on_part_data,
            "on_part_end": self.on_part_end,
            "on_header_field": self.on_header_field,
            "on_header_value": self.on_header_value,
            "on_header_end": self.on_header_end,
            "on_headers_finished": self.on_headers_finished,
        }

    @property
    def authenticated(self) -> bool:
        return self._authenticated

    def on_part_begin(self) -> None:
        self._current_file_bytes = 0
        self._current_is_file = False
        self._current_field = None
        self._headers = {}

    def on_part_data(self, data: bytes, start: int, end: int) -> None:
        if self._current_is_file:
            size = end - start
            self._current_file_bytes += size
            self.total_file_bytes += size
            if (
                self._current_file_bytes > MAX_UPLOAD_BYTES
                or self.total_file_bytes > _MAX_TOTAL_FILE_BYTES
            ):
                raise _MultipartLimitExceeded("artifact limits exceeded")
            return
        if self._current_field != b"metadata" or self._authenticated:
            return
        self._metadata.extend(data[start:end])
        if len(self._metadata) > 8192:
            raise _GuardRejected(404, _NOT_FOUND_DETAIL)

    def on_part_end(self) -> None:
        if self._current_field == b"metadata" and not self._current_is_file:
            self._authorize_metadata()
        self._current_is_file = False

    def on_header_field(self, data: bytes, start: int, end: int) -> None:
        self._header_field.extend(data[start:end])

    def on_header_value(self, data: bytes, start: int, end: int) -> None:
        self._header_value.extend(data[start:end])

    def on_header_end(self) -> None:
        self._headers[bytes(self._header_field).lower()] = bytes(self._header_value)
        self._header_field.clear()
        self._header_value.clear()

    def on_headers_finished(self) -> None:
        disposition = self._headers.get(b"content-disposition")
        _, options = parse_options_header(disposition)
        self._current_field = options.get(b"name")
        if b"filename" not in options:
            if self._current_field != b"metadata" or self._authenticated:
                raise _GuardRejected(422, "invalid follow-up metadata")
            return
        if not self._authenticated:
            raise _GuardRejected(404, _NOT_FOUND_DETAIL)
        self._current_is_file = True
        self.file_count += 1
        if self.file_count > _MAX_ARTIFACTS:
            raise _MultipartLimitExceeded("artifact limits exceeded")

    def _authorize_metadata(self) -> None:
        try:
            payload = FollowUpMetadata.model_validate_json(bytes(self._metadata))
        except ValidationError:
            raise _GuardRejected(422, "invalid follow-up metadata") from None
        now = self.clock()
        if not isinstance(now, datetime) or now.tzinfo is None:
            raise RuntimeError("application clock must return an aware datetime")
        now_text = now.astimezone(timezone.utc).isoformat()
        codec = TokenCodec(self.settings.read_key("token"))
        try:
            secret = _capability_secret(payload.capability)
        except HTTPException:
            raise _GuardRejected(404, _NOT_FOUND_DETAIL) from None
        with db.connect(self.settings.database_path) as conn:
            capability = CapabilityRepository(conn).authorize(
                self.submission_id,
                "follow_up",
                codec.digest(secret),
                now_text,
            )
        if capability is None:
            raise _GuardRejected(404, _NOT_FOUND_DETAIL)
        self._authenticated = True


class FollowUpUploadGuard:
    """Bound multipart follow-ups before framework form/file parsing."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        settings: Settings,
        clock: Callable[[], datetime],
    ):
        self.app = app
        self.settings = settings
        self.clock = clock

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self._protects(scope):
            await self.app(scope, receive, send)
            return
        headers = Headers(scope=scope)
        boundary = self._boundary(headers)
        if boundary is None:
            await self._respond(
                scope, receive, send, 400, "invalid multipart body"
            )
            return
        if self._declared_too_large(headers):
            await self._respond(scope, receive, send, 413, "artifact limits exceeded")
            return
        try:
            artifact_root = ArtifactStore(self.settings.artifact_root).root
            with tempfile.SpooledTemporaryFile(
                max_size=1024 * 1024, mode="w+b", dir=artifact_root
            ) as buffered:
                prefix, buffered_size = await self._consume(
                    scope, receive, boundary, buffered
                )
                buffered.seek(0)
                await self.app(
                    scope,
                    self._replay(prefix, buffered, buffered_size),
                    send,
                )
        except _GuardRejected as error:
            await self._respond(
                scope, receive, send, error.status_code, error.detail
            )
        except _MultipartLimitExceeded:
            await self._respond(scope, receive, send, 413, "artifact limits exceeded")
        except MultipartParseError:
            await self._respond(scope, receive, send, 400, "invalid multipart body")
        except ArtifactStorageError:
            await self._respond(
                scope, receive, send, 503, "artifact storage unavailable"
            )

    @staticmethod
    def _protects(scope: Scope) -> bool:
        if scope["type"] != "http" or scope.get("method") != "POST":
            return False
        path = scope.get("path", "")
        prefix = "/submission/v1/submissions/"
        suffix = "/follow-ups"
        middle = path[len(prefix) : -len(suffix)]
        return path.startswith(prefix) and path.endswith(suffix) and bool(middle) and (
            "/" not in middle
        )

    @staticmethod
    def _declared_too_large(headers: Headers) -> bool:
        value = headers.get("content-length")
        if value is None:
            return False
        try:
            return int(value) > _MAX_MULTIPART_BYTES
        except ValueError:
            return True

    @staticmethod
    def _boundary(headers: Headers) -> bytes | None:
        content_type, options = parse_options_header(headers.get("content-type"))
        boundary = options.get(b"boundary")
        if (
            content_type != b"multipart/form-data"
            or not isinstance(boundary, bytes)
            or not boundary
        ):
            return None
        return boundary

    async def _consume(
        self,
        scope: Scope,
        receive: Receive,
        boundary: bytes,
        buffered: Any,
    ) -> tuple[bytes, int]:
        tracker = self._tracker(scope)
        parser = MultipartParser(boundary, tracker.callbacks)
        open_marker = b"\r\n--" + boundary + b"\r\n"
        close_marker = b"\r\n--" + boundary + b"--"
        prefix = bytearray()
        prefix_complete = False
        body_size = 0
        buffered_size = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                raise MultipartParseError("incomplete multipart body")
            body = message.get("body", b"")
            if not isinstance(body, bytes):
                raise MultipartParseError("invalid multipart body")
            body_size += len(body)
            if body_size > _MAX_MULTIPART_BYTES:
                raise _MultipartLimitExceeded("artifact limits exceeded")
            if not prefix_complete:
                prefix.extend(body)
                split_end = self._first_boundary_end(
                    prefix, open_marker, close_marker
                )
                if split_end is None:
                    if len(prefix) > _MAX_MEMORY_PREFIX_BYTES:
                        raise _GuardRejected(404, _NOT_FOUND_DETAIL)
                else:
                    suffix = bytes(prefix[split_end:])
                    del prefix[split_end:]
                    parser.write(prefix)
                    if not tracker.authenticated:
                        raise _GuardRejected(404, _NOT_FOUND_DETAIL)
                    prefix_complete = True
                    if suffix:
                        parser.write(suffix)
                        buffered.write(suffix)
                        buffered_size += len(suffix)
            else:
                parser.write(body)
                buffered.write(body)
                buffered_size += len(body)
            if not message.get("more_body", False):
                break
        if not prefix_complete:
            raise MultipartParseError("invalid multipart body")
        parser.finalize()
        return bytes(prefix), buffered_size

    def _tracker(self, scope: Scope) -> _FileLimitTracker:
        path = scope["path"]
        prefix = "/submission/v1/submissions/"
        suffix = "/follow-ups"
        submission_id = path[len(prefix) : -len(suffix)]
        return _FileLimitTracker(self.settings, self.clock, submission_id)

    @staticmethod
    def _first_boundary_end(
        prefix: bytearray,
        open_marker: bytes,
        close_marker: bytes,
    ) -> int | None:
        positions = [
            (index, len(marker))
            for marker in (open_marker, close_marker)
            if (index := prefix.find(marker)) >= 0
        ]
        if not positions:
            return None
        index, marker_length = min(positions)
        return index + marker_length

    @staticmethod
    def _replay(prefix: bytes, buffered: Any, buffered_size: int) -> Receive:
        prefix_pending = True
        remaining = buffered_size

        async def replay() -> Message:
            nonlocal prefix_pending, remaining
            if prefix_pending:
                prefix_pending = False
                return {
                    "type": "http.request",
                    "body": prefix,
                    "more_body": remaining > 0,
                }
            if remaining:
                body = buffered.read(min(READ_CHUNK_BYTES, remaining))
                remaining -= len(body)
                return {
                    "type": "http.request",
                    "body": body,
                    "more_body": remaining > 0,
                }
            return {"type": "http.disconnect"}

        return replay

    @staticmethod
    async def _respond(
        scope: Scope,
        receive: Receive,
        send: Send,
        status_code: int,
        detail: str,
    ) -> None:
        await JSONResponse({"detail": detail}, status_code=status_code)(
            scope, receive, send
        )
