"""Private, metadata-free storage for untrusted submission images."""

from __future__ import annotations

import hashlib
import os
import tempfile
import unicodedata
import uuid
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Iterable, Protocol

from PIL import Image, UnidentifiedImageError


MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_IMAGE_DIMENSION = 12_000
READ_CHUNK_BYTES = 1024 * 1024
SPOOL_MEMORY_BYTES = 1024 * 1024

_FORMATS = {
    "JPEG": ("image/jpeg", ".jpg"),
    "PNG": ("image/png", ".png"),
    "WEBP": ("image/webp", ".webp"),
}
_SAFE_MODES = {"1", "L", "LA", "P", "RGB", "RGBA"}


class ArtifactRejected(ValueError):
    """An upload is not an acceptable quarantine image."""


class ArtifactStorageError(RuntimeError):
    """A sanitized artifact could not be stored privately."""


class _Upload(Protocol):
    filename: str | None
    content_type: str | None
    file: BinaryIO


@dataclass(frozen=True)
class StoredArtifact:
    """Repository metadata for one sanitized derivative."""

    storage_key: str
    original_name: str
    declared_media_type: str
    detected_media_type: str
    raw_sha256: str
    stored_sha256: str
    size_bytes: int
    width: int
    height: int


class ArtifactStore:
    """Sanitize images into a fixed private filesystem root."""

    def __init__(self, root: Path):
        root = Path(root)
        try:
            root.mkdir(mode=0o700, parents=True, exist_ok=True)
            self._root = root.resolve(strict=True)
        except OSError:
            raise ArtifactStorageError("artifact storage unavailable") from None
        if not self._root.is_dir():
            raise ArtifactStorageError("artifact storage unavailable")

    @property
    def root(self) -> Path:
        return self._root

    def sanitize(self, upload: _Upload, submission_id: str) -> StoredArtifact:
        """Fully decode and atomically store a metadata-free image derivative."""
        submission_uuid = _submission_uuid(submission_id)
        original_name = _display_name(upload.filename)
        declared_media_type = upload.content_type
        if declared_media_type not in {value[0] for value in _FORMATS.values()}:
            raise ArtifactRejected("artifact rejected")

        try:
            source = upload.file
        except AttributeError:
            raise ArtifactRejected("artifact rejected") from None

        try:
            with tempfile.SpooledTemporaryFile(
                max_size=SPOOL_MEMORY_BYTES, dir=self._root
            ) as spool:
                raw_sha256 = _copy_bounded(source, spool)
                image_format, width, height, clean = _decode_clean_image(spool)
        except (ArtifactRejected, ArtifactStorageError):
            raise
        except OSError:
            raise ArtifactStorageError("artifact storage unavailable") from None

        detected_media_type, extension = _FORMATS[image_format]
        if declared_media_type != detected_media_type:
            clean.close()
            raise ArtifactRejected("artifact rejected")

        storage_key = f"{submission_uuid}/{uuid.uuid4()}{extension}"
        destination = self.resolve(storage_key)
        try:
            stored_sha256, size_bytes = _write_derivative(
                clean, image_format, destination
            )
        finally:
            clean.close()

        return StoredArtifact(
            storage_key=storage_key,
            original_name=original_name,
            declared_media_type=declared_media_type,
            detected_media_type=detected_media_type,
            raw_sha256=raw_sha256,
            stored_sha256=stored_sha256,
            size_bytes=size_bytes,
            width=width,
            height=height,
        )

    def resolve(self, storage_key: str) -> Path:
        """Resolve a server key only when its real path remains under the root."""
        if not isinstance(storage_key, str):
            raise ValueError("invalid storage key")
        relative = Path(storage_key)
        if (
            not storage_key
            or relative.is_absolute()
            or any(part in {"", ".", ".."} for part in relative.parts)
        ):
            raise ValueError("invalid storage key")
        try:
            candidate = (self._root / relative).resolve(strict=False)
            candidate.relative_to(self._root)
        except (OSError, ValueError):
            raise ValueError("invalid storage key") from None
        return candidate

    def discard(self, storage_keys: Iterable[str]) -> None:
        """Delete derivatives, such as after a database transaction rolls back."""
        for storage_key in storage_keys:
            path = self.resolve(storage_key)
            try:
                path.unlink(missing_ok=True)
            except FileNotFoundError:
                continue
            except OSError:
                raise ArtifactStorageError("artifact storage unavailable") from None
            if path.parent != self._root:
                try:
                    path.parent.rmdir()
                except OSError:
                    pass


def _submission_uuid(submission_id: str) -> str:
    try:
        parsed = uuid.UUID(submission_id)
    except (AttributeError, TypeError, ValueError):
        raise ValueError("invalid submission id") from None
    if str(parsed) != submission_id:
        raise ValueError("invalid submission id")
    return str(parsed)


def _display_name(filename: str | None) -> str:
    if not isinstance(filename, str):
        raise ArtifactRejected("artifact rejected")
    normalized = unicodedata.normalize("NFKC", filename).strip()
    if (
        not normalized
        or len(normalized) > 255
        or normalized in {".", ".."}
        or "/" in normalized
        or "\\" in normalized
        or any(
            unicodedata.category(character).startswith("C") for character in normalized
        )
    ):
        raise ArtifactRejected("artifact rejected")
    return normalized


def _copy_bounded(source: BinaryIO, spool: BinaryIO) -> str:
    digest = hashlib.sha256()
    size = 0
    while True:
        try:
            chunk = source.read(READ_CHUNK_BYTES)
        except Exception:
            raise ArtifactRejected("artifact rejected") from None
        if not chunk:
            break
        if not isinstance(chunk, bytes):
            raise ArtifactRejected("artifact rejected")
        size += len(chunk)
        if size > MAX_UPLOAD_BYTES:
            raise ArtifactRejected("artifact rejected")
        digest.update(chunk)
        try:
            spool.write(chunk)
        except OSError:
            raise ArtifactStorageError("artifact storage unavailable") from None
    if size == 0:
        raise ArtifactRejected("artifact rejected")
    spool.flush()
    return digest.hexdigest()


def _decode_clean_image(spool: BinaryIO) -> tuple[str, int, int, Image.Image]:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            spool.seek(0)
            with Image.open(spool) as probe:
                image_format = probe.format
                width, height = probe.size
                if image_format not in _FORMATS:
                    raise ArtifactRejected("artifact rejected")
                if getattr(probe, "n_frames", 1) != 1:
                    raise ArtifactRejected("artifact rejected")
                _check_dimensions(width, height)
                probe.verify()

            spool.seek(0)
            with Image.open(spool) as decoded:
                if decoded.format != image_format or decoded.size != (width, height):
                    raise ArtifactRejected("artifact rejected")
                if getattr(decoded, "n_frames", 1) != 1:
                    raise ArtifactRejected("artifact rejected")
                decoded.load()
                if decoded.mode not in _SAFE_MODES:
                    raise ArtifactRejected("artifact rejected")
                clean = _copy_pixels(decoded, image_format)
    except ArtifactRejected:
        raise
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        UnidentifiedImageError,
        OSError,
        SyntaxError,
        ValueError,
    ):
        raise ArtifactRejected("artifact rejected") from None
    return image_format, width, height, clean


def _check_dimensions(width: int, height: int) -> None:
    if (
        width < 1
        or height < 1
        or width > MAX_IMAGE_DIMENSION
        or height > MAX_IMAGE_DIMENSION
    ):
        raise ArtifactRejected("artifact rejected")


def _copy_pixels(decoded: Image.Image, image_format: str) -> Image.Image:
    mode = decoded.mode
    if mode == "P":
        mode = "RGBA" if "transparency" in decoded.info else "RGB"
    elif mode == "1":
        mode = "L"
    if image_format == "JPEG" and mode not in {"L", "RGB"}:
        mode = "RGB"

    converted = decoded.convert(mode)
    try:
        clean = Image.new(mode, decoded.size)
        clean.paste(converted)
    finally:
        converted.close()
    return clean


def _write_derivative(
    image: Image.Image, image_format: str, destination: Path
) -> tuple[str, int]:
    temporary_path: Path | None = None
    published = False
    try:
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".artifact-", suffix=".tmp", dir=destination.parent
        )
        temporary_path = Path(temporary_name)
        with os.fdopen(descriptor, "w+b") as output:
            os.fchmod(output.fileno(), 0o600)
            save_options = {"quality": 90} if image_format in {"JPEG", "WEBP"} else {}
            image.save(output, format=image_format, **save_options)
            output.flush()
            os.fsync(output.fileno())
            size_bytes = output.tell()
            output.seek(0)
            stored_digest = hashlib.sha256()
            while chunk := output.read(READ_CHUNK_BYTES):
                stored_digest.update(chunk)
            stored_sha256 = stored_digest.hexdigest()
        os.replace(temporary_path, destination)
        temporary_path = None
        published = True
        directory_descriptor = os.open(destination.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
        return stored_sha256, size_bytes
    except (OSError, ValueError):
        if published:
            try:
                destination.unlink(missing_ok=True)
            except OSError:
                pass
        raise ArtifactStorageError("artifact storage unavailable") from None
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
