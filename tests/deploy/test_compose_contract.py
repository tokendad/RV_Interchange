import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "deploy" / "docker-compose.yaml"


def rendered_compose(*profiles):
    if shutil.which("docker") is None:
        pytest.skip("docker compose is required for the deployment contract test")
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
        env={**os.environ, "RVINTERCHANGE_TUNNEL_TOKEN": "test-token"},
    )
    return json.loads(result.stdout)


def test_production_compose_network_and_mount_boundaries():
    default_config = rendered_compose()
    assert set(default_config["services"]) == {
        "rvinterchange-api",
        "rvinterchange-review",
        "rvinterchange-web",
    }

    config = rendered_compose("tunnel")
    services = config["services"]
    assert set(services) == {
        "rvinterchange-api",
        "rvinterchange-cloudflared",
        "rvinterchange-review",
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
