import hashlib
import io
import sqlite3
import warnings
from pathlib import Path

import pytest
from PIL import Image
from starlette.datastructures import Headers, UploadFile

from intake.artifacts import ArtifactRejected, ArtifactStore


SUBMISSION_ID = "133d2098-8fc1-4c01-9e8d-ffb51f089982"


def _image_bytes(
    image_format: str,
    *,
    mode: str = "RGB",
    size: tuple[int, int] = (7, 5),
    exif: Image.Exif | None = None,
) -> bytes:
    buffer = io.BytesIO()
    color = 17 if mode in {"1", "L", "I"} else (17, 34, 51, 255)[: len(mode)]
    save_options = {"exif": exif} if exif is not None else {}
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore", message="Saving I mode images as PNG is deprecated"
        )
        Image.new(mode, size, color).save(buffer, format=image_format, **save_options)
    return buffer.getvalue()


def _upload(
    content: bytes,
    *,
    filename: str = "evidence.jpg",
    content_type: str = "image/jpeg",
) -> UploadFile:
    return UploadFile(
        io.BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


@pytest.fixture
def store(tmp_path: Path) -> ArtifactStore:
    return ArtifactStore(tmp_path / "private-artifacts")


@pytest.mark.parametrize(
    ("image_format", "declared_type", "extension"),
    [
        ("JPEG", "image/jpeg", ".jpg"),
        ("PNG", "image/png", ".png"),
        ("WEBP", "image/webp", ".webp"),
    ],
)
def test_sanitize_accepts_only_supported_decoded_image_formats(
    store: ArtifactStore,
    image_format: str,
    declared_type: str,
    extension: str,
):
    raw = _image_bytes(image_format)

    result = store.sanitize(
        _upload(raw, filename="camera.data", content_type=declared_type),
        SUBMISSION_ID,
    )

    assert result.storage_key.startswith(f"{SUBMISSION_ID}/")
    assert result.storage_key.endswith(extension)
    assert result.original_name == "camera.data"
    assert result.declared_media_type == declared_type
    assert result.detected_media_type == declared_type
    assert result.raw_sha256 == hashlib.sha256(raw).hexdigest()
    assert result.size_bytes == store.resolve(result.storage_key).stat().st_size
    assert result.width == 7
    assert result.height == 5
    with Image.open(store.resolve(result.storage_key)) as derivative:
        derivative.load()
        assert derivative.format == image_format


def test_sanitize_hashes_the_stored_derivative(store: ArtifactStore):
    result = store.sanitize(
        _upload(_image_bytes("PNG"), filename="evidence.png", content_type="image/png"),
        SUBMISSION_ID,
    )

    stored = store.resolve(result.storage_key).read_bytes()
    assert result.stored_sha256 == hashlib.sha256(stored).hexdigest()


def test_sanitize_uses_random_server_keys(store: ArtifactStore):
    raw = _image_bytes("PNG")

    first = store.sanitize(
        _upload(raw, filename="same.png", content_type="image/png"), SUBMISSION_ID
    )
    second = store.sanitize(
        _upload(raw, filename="same.png", content_type="image/png"), SUBMISSION_ID
    )

    assert first.storage_key != second.storage_key
    assert Path(first.storage_key).name != "same.png"
    assert Path(second.storage_key).name != "same.png"


@pytest.mark.parametrize(
    "filename",
    ["../secret.png", "folder/secret.png", r"folder\secret.png", "/secret.png"],
)
def test_sanitize_rejects_traversal_filenames_without_disclosing_them(
    store: ArtifactStore, filename: str
):
    with pytest.raises(ArtifactRejected) as error:
        store.sanitize(
            _upload(_image_bytes("PNG"), filename=filename, content_type="image/png"),
            SUBMISSION_ID,
        )

    assert filename not in str(error.value)
    assert not any(path.is_file() for path in store.root.rglob("*"))


def test_sanitize_rejects_declared_mime_mismatch(store: ArtifactStore):
    with pytest.raises(ArtifactRejected, match="artifact rejected"):
        store.sanitize(
            _upload(
                _image_bytes("PNG"),
                filename="disguised.jpg",
                content_type="image/jpeg",
            ),
            SUBMISSION_ID,
        )


@pytest.mark.parametrize(
    ("content", "content_type"),
    [
        (b"not an image", "image/png"),
        (_image_bytes("PNG")[:-8], "image/png"),
        (_image_bytes("GIF"), "image/gif"),
    ],
    ids=["garbage", "truncated", "unsupported-format"],
)
def test_sanitize_rejects_corrupt_or_unsupported_content(
    store: ArtifactStore, content: bytes, content_type: str
):
    with pytest.raises(ArtifactRejected, match="artifact rejected"):
        store.sanitize(
            _upload(content, filename="upload.bin", content_type=content_type),
            SUBMISSION_ID,
        )

    assert not any(path.is_file() for path in store.root.rglob("*"))


def test_sanitize_rejects_unsupported_decoded_mode(store: ArtifactStore):
    with pytest.raises(ArtifactRejected, match="artifact rejected"):
        store.sanitize(
            _upload(
                _image_bytes("PNG", mode="I"),
                filename="integer.png",
                content_type="image/png",
            ),
            SUBMISSION_ID,
        )


def test_sanitize_rejects_multiframe_images(store: ArtifactStore):
    buffer = io.BytesIO()
    frames = [Image.new("RGB", (4, 4), color) for color in ("red", "blue")]
    frames[0].save(
        buffer,
        format="WEBP",
        save_all=True,
        append_images=frames[1:],
        duration=100,
        loop=0,
    )

    with pytest.raises(ArtifactRejected, match="artifact rejected"):
        store.sanitize(
            _upload(
                buffer.getvalue(),
                filename="animated.webp",
                content_type="image/webp",
            ),
            SUBMISSION_ID,
        )


class _NoUnboundedRead(io.BytesIO):
    def read(self, size: int = -1) -> bytes:
        assert 0 <= size <= 1024 * 1024
        return super().read(size)


def test_sanitize_streams_into_a_bounded_spool_and_rejects_over_10_mib(
    store: ArtifactStore,
):
    upload = UploadFile(
        _NoUnboundedRead(b"x" * (10 * 1024 * 1024 + 1)),
        filename="large.png",
        headers=Headers({"content-type": "image/png"}),
    )

    with pytest.raises(ArtifactRejected, match="artifact rejected"):
        store.sanitize(upload, SUBMISSION_ID)


def test_sanitize_rejects_decoded_dimensions_over_12000(store: ArtifactStore):
    raw = _image_bytes("PNG", size=(12_001, 1))

    with pytest.raises(ArtifactRejected, match="artifact rejected"):
        store.sanitize(
            _upload(raw, filename="wide.png", content_type="image/png"),
            SUBMISSION_ID,
        )


def test_sanitize_rejects_pillow_decompression_bomb_warning(
    store: ArtifactStore, monkeypatch
):
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 10)

    with pytest.raises(ArtifactRejected, match="artifact rejected"):
        store.sanitize(
            _upload(
                _image_bytes("PNG", size=(4, 4)),
                filename="bomb.png",
                content_type="image/png",
            ),
            SUBMISSION_ID,
        )


def test_sanitized_derivative_removes_exif_gps_and_profiles(store: ArtifactStore):
    exif = Image.Exif()
    exif[0x010F] = "private camera"
    exif[0x8825] = {1: "N"}
    raw = _image_bytes("JPEG", exif=exif)
    with Image.open(io.BytesIO(raw)) as original:
        assert original.getexif().get_ifd(0x8825) == {1: "N"}

    result = store.sanitize(
        _upload(raw, filename="location.jpg", content_type="image/jpeg"),
        SUBMISSION_ID,
    )

    with Image.open(store.resolve(result.storage_key)) as image:
        assert image.getexif() == {}
        assert "icc_profile" not in image.info
        assert "xmp" not in image.info


def test_discard_removes_derivatives_after_database_failure(store: ArtifactStore):
    result = store.sanitize(
        _upload(_image_bytes("WEBP"), filename="photo.webp", content_type="image/webp"),
        SUBMISSION_ID,
    )

    try:
        raise sqlite3.IntegrityError("simulated database failure")
    except sqlite3.IntegrityError:
        store.discard([result.storage_key])

    assert not store.resolve(result.storage_key).exists()


def test_discard_one_derivative_leaves_other_submission_artifacts(
    store: ArtifactStore,
):
    raw = _image_bytes("PNG")
    first = store.sanitize(
        _upload(raw, filename="first.png", content_type="image/png"), SUBMISSION_ID
    )
    second = store.sanitize(
        _upload(raw, filename="second.png", content_type="image/png"), SUBMISSION_ID
    )

    store.discard([first.storage_key])

    assert not store.resolve(first.storage_key).exists()
    assert store.resolve(second.storage_key).is_file()


def test_resolve_rejects_paths_outside_the_fixed_root(
    store: ArtifactStore, tmp_path: Path
):
    outside = tmp_path / "outside"
    outside.mkdir()
    (store.root / "escape").symlink_to(outside, target_is_directory=True)

    for key in ("../outside/file.png", "/tmp/file.png", "escape/file.png"):
        with pytest.raises(ValueError, match="invalid storage key") as error:
            store.resolve(key)
        assert key not in str(error.value)


@pytest.mark.parametrize("submission_id", ["../outside", "not-a-uuid"])
def test_sanitize_requires_a_uuid_submission_directory(
    store: ArtifactStore, submission_id: str
):
    with pytest.raises(ValueError, match="invalid submission id"):
        store.sanitize(
            _upload(
                _image_bytes("PNG"), filename="photo.png", content_type="image/png"
            ),
            submission_id,
        )
