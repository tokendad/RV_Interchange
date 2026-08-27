import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


def test_review_api_image_can_verify_rs256_access_tokens():
    if shutil.which("docker") is None:
        pytest.skip("docker is required for the review API image contract test")

    build = subprocess.run(
        [
            "docker",
            "build",
            "--quiet",
            "--file",
            str(ROOT / "review" / "api.Dockerfile"),
            str(ROOT),
        ],
        text=True,
        capture_output=True,
        check=True,
    )
    image = build.stdout.strip().splitlines()[-1]
    runtime = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            image,
            "python3",
            "-c",
            "import jwt.algorithms; assert jwt.algorithms.has_crypto",
        ],
        text=True,
        capture_output=True,
    )

    assert runtime.returncode == 0, runtime.stderr
