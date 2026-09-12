"""Read-only smoke checks through the public reverse proxy."""

import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

port = os.environ.get("HTTP_PORT", "8080")
env_file = Path(__file__).resolve().parents[2] / ".env"
if "HTTP_PORT" not in os.environ and env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.startswith("HTTP_PORT="):
            port = line.partition("=")[2].strip()
base = os.environ.get("SMOKE_URL", f"http://127.0.0.1:{port}")
with urlopen(base + "/", timeout=10) as response:
    assert b"Your next opportunity" in response.read()
with urlopen(base + "/health", timeout=10) as response:
    assert json.load(response)["status"] == "ok"
    assert response.headers["X-Request-ID"]
with urlopen(base + "/ready", timeout=10) as response:
    result = json.load(response)
    assert result["status"] == "ready", result
    assert all(value == "up" for value in result["dependencies"].values()), result
try:
    urlopen(base + "/api/v1/auth/me", timeout=10)
except HTTPError as error:
    assert error.code == 401
    assert json.load(error)["error"]["code"] == "UNAUTHORIZED"
else:
    raise AssertionError("Anonymous authentication request was accepted")
print("PASS: web, API liveness, all dependencies, anonymous access denial")
