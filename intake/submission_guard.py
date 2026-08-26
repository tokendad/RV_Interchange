"""Pre-body authentication and streaming limits for submission multipart input."""

from __future__ import annotations

import tempfile
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from python_multipart.exceptions import MultipartParseError
from python_multipart.multipart import MultipartParser, parse_options_header
from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from intake import db
from intake.artifacts import (
    MAX_UPLOAD_BYTES,
    READ_CHUNK_BYTES,
    ArtifactStorageError,
    ArtifactStore,
)
from intake.config import Settings
from intake.repositories import SessionRepository
from intake.security import TokenCodec


_SUBMISSION_PATH = "/submission/v1/submissions"
_SESSION_COOKIE = "rvi_contribution_session"
_MAX_FILES = 5
_MAX_TOTAL_FILE_BYTES = 25 * 1024 * 1024
_MAX_MULTIPART_BYTES = _MAX_TOTAL_FILE_BYTES + 1024 * 1024


class _RequestRejected(RuntimeError):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail


class _MultipartLimitExceeded(RuntimeError):
    pass


class _MultipartFileTracker:
    """Count only decoded multipart file content as parser chunks arrive."""

    def __init__(self):
        self.file_count = 0
        self.total_file_bytes = 0
        self._current_file_bytes = 0
        self._current_is_file = False
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

    def on_part_begin(self) -> None:
        self._current_file_bytes = 0
        self._current_is_file = False
        self._headers = {}

    def on_part_data(self, data: bytes, start: int, end: int) -> None:
        if not self._current_is_file:
            return
        size = end - start
        self._current_file_bytes += size
        self.total_file_bytes += size
        if (
            self._current_file_bytes > MAX_UPLOAD_BYTES
            or self.total_file_bytes > _MAX_TOTAL_FILE_BYTES
        ):
            raise _MultipartLimitExceeded("artifact limits exceeded")

    def on_part_end(self) -> None:
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
        if b"filename" not in options:
            return
        self._current_is_file = True
        self.file_count += 1
        if self.file_count > _MAX_FILES:
            raise _MultipartLimitExceeded("artifact limits exceeded")


class SubmissionUploadGuard:
    """Protect the submission endpoint before FastAPI resolves Form/File values."""

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

        try:
            self._authenticate(scope)
        except _RequestRejected as error:
            await self._respond(scope, receive, send, error.status_code, error.detail)
            return

        headers = Headers(scope=scope)
        if self._declared_too_large(headers):
            await self._respond(scope, receive, send, 413, "artifact limits exceeded")
            return

        try:
            artifact_root = ArtifactStore(self.settings.artifact_root).root
            with tempfile.SpooledTemporaryFile(
                max_size=1024 * 1024,
                mode="w+b",
                dir=artifact_root,
            ) as buffered:
                body_size = await self._consume(receive, headers, buffered)
                buffered.seek(0)
                replay = self._replay(buffered, body_size)
                await self.app(scope, replay, send)
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
        return (
            scope["type"] == "http"
            and scope.get("method") == "POST"
            and scope.get("path") == _SUBMISSION_PATH
        )

    def _authenticate(self, scope: Scope) -> None:
        now = self.clock()
        if not isinstance(now, datetime) or now.tzinfo is None:
            raise RuntimeError("application clock must return an aware datetime")
        now = now.astimezone(timezone.utc)
        request = Request(scope)
        codec = TokenCodec(self.settings.read_key("session"))
        try:
            raw_session = codec.verify_session(
                request.cookies.get(_SESSION_COOKIE), int(now.timestamp())
            )
        except ValueError:
            raise _RequestRejected(
                401, "active contribution session required"
            ) from None
        with db.connect(self.settings.database_path) as conn:
            session = SessionRepository(conn).authenticate(
                codec.digest(raw_session), now.isoformat()
            )
        if session is None:
            raise _RequestRejected(401, "active contribution session required")
        if not codec.verify_csrf(
            request.headers.get("X-CSRF-Token"), session["csrf_digest"]
        ):
            raise _RequestRejected(403, "invalid CSRF token")

    @staticmethod
    def _declared_too_large(headers: Headers) -> bool:
        value = headers.get("content-length")
        if value is None:
            return False
        try:
            return int(value) > _MAX_MULTIPART_BYTES
        except ValueError:
            return True

    async def _consume(
        self,
        receive: Receive,
        headers: Headers,
        buffered: Any,
    ) -> int:
        parser = self._parser(headers)
        body_size = 0
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
            if parser is not None:
                parser.write(body)
            buffered.write(body)
            if not message.get("more_body", False):
                break
        if parser is not None:
            parser.finalize()
        return body_size

    @staticmethod
    def _parser(headers: Headers) -> MultipartParser | None:
        content_type, options = parse_options_header(headers.get("content-type"))
        boundary = options.get(b"boundary")
        if content_type != b"multipart/form-data" or boundary is None:
            return None
        tracker = _MultipartFileTracker()
        return MultipartParser(boundary, tracker.callbacks)

    @staticmethod
    def _replay(buffered: Any, body_size: int) -> Receive:
        remaining = body_size
        empty_sent = False

        async def replay() -> Message:
            nonlocal remaining, empty_sent
            if remaining:
                body = buffered.read(min(READ_CHUNK_BYTES, remaining))
                remaining -= len(body)
                return {
                    "type": "http.request",
                    "body": body,
                    "more_body": remaining > 0,
                }
            if not empty_sent:
                empty_sent = True
                return {"type": "http.request", "body": b"", "more_body": False}
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
