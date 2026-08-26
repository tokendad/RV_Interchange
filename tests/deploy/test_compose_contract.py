import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "deploy" / "docker-compose.yaml"


def rendered_compose(
    *profiles, configure_intake_secrets=True, environment=None
):
    if shutil.which("docker") is None:
        pytest.skip("docker compose is required for the deployment contract test")
    env = os.environ.copy()
    env.pop("COMPOSE_PROFILES", None)
    env["RVINTERCHANGE_TUNNEL_TOKEN"] = "test-token"
    if configure_intake_secrets:
        for variable in (
            "RVI_CONTACT_KEY_FILE",
            "RVI_TOKEN_KEY_FILE",
            "RVI_SESSION_KEY_FILE",
            "RVI_IP_KEY_FILE",
            "RVI_TURNSTILE_SECRET_FILE",
        ):
            env[variable] = "/dev/null"
    env.update(environment or {})
    command = ["docker", "compose", "-f", str(COMPOSE)]
    for profile in profiles:
        command.extend(["--profile", profile])
    command.extend(["config", "--format", "json"])
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
        env=env,
    )
    return json.loads(result.stdout)


def test_production_compose_network_and_mount_boundaries():
    default_config = rendered_compose()
    assert set(default_config["services"]) == {
        "rvinterchange-api",
        "rvinterchange-review-api",
        "rvinterchange-review",
        "rvinterchange-web",
    }

    config = rendered_compose("tunnel")
    services = config["services"]
    assert set(services) == {
        "rvinterchange-api",
        "rvinterchange-cloudflared",
        "rvinterchange-review",
        "rvinterchange-review-api",
        "rvinterchange-web",
    }
    assert "ports" not in services["rvinterchange-api"]
    assert services["rvinterchange-web"]["ports"][0]["host_ip"] == "127.0.0.1"
    assert services["rvinterchange-review"]["ports"][0]["host_ip"] == "127.0.0.1"
    tool_mount = next(
        mount for mount in services["rvinterchange-api"]["volumes"]
        if mount["target"] == "/app/Docs/Tools"
    )
    assert tool_mount["read_only"] is True
    assert services["rvinterchange-cloudflared"]["profiles"] == ["tunnel"]


def test_intake_profile_isolated_from_public_and_canonical_paths():
    default_config = rendered_compose()
    intake_config = rendered_compose("intake")

    assert set(intake_config["services"]) == set(default_config["services"]) | {
        "rvinterchange-intake"
    }

    intake = intake_config["services"]["rvinterchange-intake"]
    assert intake["profiles"] == ["intake"]
    assert "ports" not in intake
    assert {
        mount["target"]
        for mount in intake["volumes"]
        if not mount.get("read_only", False)
    } == {"/app/data", "/app/artifacts"}
    assert "/app/Docs/Tools" not in {mount["target"] for mount in intake["volumes"]}
    assert all("components.db" not in mount["source"] for mount in intake["volumes"])
    assert all(mount.get("read_only", True) for mount in intake["secrets"])


def test_non_intake_profiles_do_not_require_intake_secret_configuration():
    default_config = rendered_compose(configure_intake_secrets=False)
    tunnel_config = rendered_compose(
        "tunnel", configure_intake_secrets=False
    )

    assert "rvinterchange-intake" not in default_config["services"]
    assert "rvinterchange-intake" not in tunnel_config["services"]


def test_intake_storage_sources_can_be_isolated_for_restore_drills(tmp_path):
    data_dir = tmp_path / "data"
    artifact_dir = tmp_path / "artifacts"
    config = rendered_compose(
        "intake",
        environment={
            "RVI_INTAKE_DATA_DIR": str(data_dir),
            "RVI_INTAKE_ARTIFACT_DIR": str(artifact_dir),
        },
    )

    intake = config["services"]["rvinterchange-intake"]
    assert "container_name" not in intake
    writable = {
        mount["target"]: mount["source"]
        for mount in intake["volumes"]
        if not mount.get("read_only", False)
    }
    assert writable == {
        "/app/data": str(data_dir),
        "/app/artifacts": str(artifact_dir),
    }
