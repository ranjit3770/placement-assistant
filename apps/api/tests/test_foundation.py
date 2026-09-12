import asyncio
import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.logging import JsonFormatter
from app.infrastructure.dependencies import Dependencies
from app.main import create_app


def test_liveness_and_error_redaction(settings):
    app = create_app(settings)

    @app.get("/explode")
    async def explode():
        raise RuntimeError("database-password-do-not-disclose")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/health", headers={"X-Request-ID": "untrusted"})
        assert response.status_code == 200
        UUID(response.headers["X-Request-ID"])
        assert response.json()["status"] == "ok"
        assert client.get("/missing").json()["error"]["code"] == "NOT_FOUND"
        response = client.get("/explode")
        assert response.status_code == 500
        assert "database-password" not in response.text
        assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]


@pytest.mark.parametrize(
    "postgres,redis,qdrant,status,degraded",
    [
        ("up", "up", "up", 200, False),
        ("down", "up", "up", 503, True),
        ("up", "down", "down", 200, True),
    ],
)
def test_readiness(settings, postgres, redis, qdrant, status, degraded):
    app = create_app(settings)
    with TestClient(app) as client:
        app.state.dependencies.check = AsyncMock(
            return_value={
                "postgres": postgres,
                "redis": redis,
                "qdrant": qdrant,
            }
        )
        response = client.get("/ready")
        assert response.status_code == status
        assert response.json()["degraded"] is degraded


def test_dependency_probes_timeout_and_hide_exceptions(settings):
    async def scenario():
        dependencies = Dependencies(settings)

        async def slow():
            await asyncio.sleep(10)

        dependencies.postgres = slow
        dependencies.cache = AsyncMock(side_effect=RuntimeError("secret"))
        dependencies.vector = AsyncMock()
        try:
            result = await asyncio.wait_for(dependencies.check(), timeout=1)
            assert result == {"postgres": "down", "redis": "down", "qdrant": "up"}
        finally:
            await dependencies.close()

    asyncio.run(scenario())


def token(settings, **updates):
    now = datetime.now(UTC)
    claims = {
        "sub": str(uuid4()),
        "institution_id": str(uuid4()),
        "role": "STUDENT",
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    claims.update(updates)
    return jwt.encode(claims, settings.jwt_secret.get_secret_value(), algorithm="HS256")


@pytest.mark.parametrize(
    "kind",
    [
        "absent",
        "malformed",
        "expired",
        "issuer",
        "audience",
        "role",
        "signature",
        "institution",
        "missing_exp",
    ],
)
def test_invalid_authentication(settings, kind):
    updates = {
        "expired": {"exp": datetime.now(UTC) - timedelta(seconds=1)},
        "issuer": {"iss": "other"},
        "audience": {"aud": "other"},
        "role": {"role": "SUPERUSER"},
        "institution": {"institution_id": "not-a-uuid"},
    }
    value = token(settings, **updates.get(kind, {}))
    if kind == "malformed":
        value = "not-a-token"
    if kind == "signature":
        claims = jwt.decode(value, options={"verify_signature": False})
        value = jwt.encode(claims, "wrong-secret" * 5, algorithm="HS256")
    if kind == "missing_exp":
        claims = jwt.decode(value, options={"verify_signature": False})
        claims.pop("exp")
        value = jwt.encode(claims, settings.jwt_secret.get_secret_value(), algorithm="HS256")
    with TestClient(create_app(settings)) as client:
        headers = {} if kind == "absent" else {"Authorization": f"Bearer {value}"}
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"
        assert value not in response.text


def test_valid_principal(settings):
    with TestClient(create_app(settings)) as client:
        response = client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token(settings)}"}
        )
        assert response.status_code == 200
        assert response.json()["role"] == "STUDENT"
        assert set(response.json()) == {"sub", "institution_id", "role"}


def test_production_docs_disabled(settings):
    settings.app_env = "production"
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/v1/docs").status_code == 404
        assert client.get("/api/v1/openapi.json").status_code == 404


def test_configuration_rejects_short_secret(settings):
    with pytest.raises(ValidationError):
        type(settings)(**{**settings.model_dump(), "jwt_secret": "short"})


def test_logs_have_structured_operational_fields():
    import logging

    record = logging.LogRecord("placement", logging.INFO, "", 0, "request", (), None)
    record.fields = {"request_id": "abc", "status": 200}
    result = json.loads(JsonFormatter().format(record))
    assert result["request_id"] == "abc"
    assert result["service"] == "api"
    assert "timestamp" in result
