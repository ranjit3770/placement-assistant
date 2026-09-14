"""Phase 1: real HTTP/JWT/lifespan/PostgreSQL, with only the model provider mocked.

Run with M8_TEST_DATABASE_URL pointing to a migrated disposable test database.
No principal override, mocked database, or session-injecting middleware is used.
"""

import os
import time
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.agent.context import ToolContext
from app.core.config import Settings
from app.infrastructure.models.conversation import ConversationMessage, ConversationSession
from app.infrastructure.models.students import Institution, Student, User
from app.main import create_app


@dataclass(frozen=True)
class Identity:
    user_id: UUID
    student_id: UUID
    institution_id: UUID


@pytest.fixture
def harness():
    url = os.environ.get("M8_TEST_DATABASE_URL")
    if not url:
        pytest.skip("M8_TEST_DATABASE_URL required for PostgreSQL HTTP authorization")
    engine = create_engine(url)
    try:
        with Session(engine, expire_on_commit=False) as db:
            tenants = [
                Institution(code=f"M8HTTP-{uuid4().hex}", name="Synthetic HTTP tenant")
                for _ in range(2)
            ]
            db.add_all(tenants)
            db.flush()
            identities = []
            for tenant in (tenants[0], tenants[0], tenants[1]):
                user = User(
                    institution_id=tenant.id,
                    login=f"{uuid4().hex}@example.invalid",
                    status="ACTIVE",
                    source_type="SYSTEM",
                    source_reference="m8-http",
                )
                db.add(user)
                db.flush()
                student = Student(
                    institution_id=tenant.id,
                    user_id=user.id,
                    roll_number=uuid4().hex,
                    source_type="SYSTEM",
                    source_reference="m8-http",
                )
                db.add(student)
                db.flush()
                identities.append(Identity(user.id, student.id, tenant.id))
            db.commit()
        settings = Settings(
            _env_file=None,
            app_env="test",
            database_url=url,
            redis_url="redis://127.0.0.1:1/0",
            qdrant_url="http://127.0.0.1:1",
            jwt_secret="m8-http-test-only-" + "x" * 40,
        )
        app = create_app(settings)
        provider = AsyncMock()
        provider.chat.completions.create.return_value = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(tool_calls=None, content="Unverified model text")
                )
            ]
        )
        with (
            patch("app.api.routers.agent.AsyncOpenAI", return_value=provider) as factory,
            patch("app.api.routers.agent.ToolContext", wraps=ToolContext) as principal_probe,
            TestClient(app) as client,
        ):
            assert app.dependency_overrides == {}
            yield SimpleNamespace(
                engine=engine,
                settings=settings,
                client=client,
                identities=identities,
                factory=factory,
                provider=provider,
                principal_probe=principal_probe,
            )
    finally:
        engine.dispose()


def token(h, identity, *, changes=None, signing_key=None):
    now = int(time.time())
    claims = {
        "sub": str(identity.user_id),
        "institution_id": str(identity.institution_id),
        "role": "STUDENT",
        "iss": h.settings.jwt_issuer,
        "aud": h.settings.jwt_audience,
        "iat": now,
        "exp": now + 300,
    }
    claims.update(changes or {})
    return jwt.encode(
        claims, signing_key or h.settings.jwt_secret.get_secret_value(), algorithm="HS256"
    )


def headers(h, identity):
    return {"Authorization": "Bearer " + token(h, identity)}


def snapshot(h):
    """Read committed DB state via a separate connection, not ORM identity cache."""
    tenant_ids = {identity.institution_id for identity in h.identities}
    with Session(h.engine) as db:
        sessions = (
            db.execute(
                select(ConversationSession.__table__)
                .where(ConversationSession.institution_id.in_(tenant_ids))
                .order_by(ConversationSession.id)
            )
            .mappings()
            .all()
        )
        messages = (
            db.execute(
                select(ConversationMessage.__table__)
                .join(ConversationSession, ConversationSession.id == ConversationMessage.session_id)
                .where(ConversationSession.institution_id.in_(tenant_ids))
                .order_by(ConversationMessage.id)
            )
            .mappings()
            .all()
        )
        return [dict(row) for row in sessions], [dict(row) for row in messages]


def post(h, conversation_id, request_headers=None, **extra):
    return h.client.post(
        "/api/v1/agent/chat",
        headers=request_headers or {},
        json={
            "conversation_id": str(conversation_id),
            "query": "Check my placement status",
            **extra,
        },
    )


def assert_denied(h, response, before, status=403, provider_calls=0):
    assert response.status_code == status
    assert response.json()["error"]["code"] == ("UNAUTHORIZED" if status == 401 else "FORBIDDEN")
    assert snapshot(h) == before, "Denied HTTP requests must not create or mutate conversation rows"
    assert h.factory.call_count == provider_calls
    assert h.provider.chat.completions.create.await_count == provider_calls


@pytest.mark.parametrize(
    "case", ["missing", "malformed", "signature", "expired", "issuer", "audience"]
)
def test_m8_http_jwt_rejection_has_no_side_effects(harness, case):
    h = harness
    identity = h.identities[0]
    request_headers = {}
    if case == "malformed":
        request_headers = {"Authorization": "Bearer invalid"}
    elif case != "missing":
        changes = {
            "expired": {"exp": int(time.time()) - 60},
            "issuer": {"iss": "untrusted"},
            "audience": {"aud": "untrusted"},
        }.get(case)
        signed = token(
            h,
            identity,
            changes=changes,
            signing_key="wrong-test-key-" + "z" * 40 if case == "signature" else None,
        )
        request_headers = {"Authorization": "Bearer " + signed}
    before = snapshot(h)
    response = post(h, uuid4(), request_headers)
    assert_denied(h, response, before, status=401)
    assert response.headers["WWW-Authenticate"] == "Bearer"
    h.principal_probe.assert_not_called()


def test_m8_http_own_conversation_persists_jwt_identity(harness):
    h = harness
    owner = h.identities[0]
    conversation_id = uuid4()
    for _ in range(2):
        response = post(h, conversation_id, headers(h, owner))
        assert response.status_code == 200
    rows, messages = snapshot(h)
    assert len(rows) == 1
    assert rows[0]["id"] == conversation_id
    assert rows[0]["student_id"] == owner.student_id != owner.user_id
    assert rows[0]["institution_id"] == owner.institution_id
    assert len([row for row in messages if row["role"] == "user"]) == 2
    assert sorted(row["sequence_number"] for row in messages) == list(range(1, len(messages) + 1))
    for observed in h.principal_probe.call_args_list:
        principal = observed.kwargs["principal"]
        assert principal.sub == owner.user_id
        assert principal.institution_id == owner.institution_id
        assert principal.role == "STUDENT"


@pytest.mark.parametrize("victim_index", [1, 2], ids=["cross-student", "cross-tenant"])
def test_m8_http_foreign_conversation_id_is_denied(harness, victim_index):
    h = harness
    attacker, victim = h.identities[0], h.identities[victim_index]
    conversation_id = uuid4()
    assert post(h, conversation_id, headers(h, victim)).status_code == 200
    before = snapshot(h)
    response = post(h, conversation_id, headers(h, attacker))
    assert_denied(h, response, before, provider_calls=1)
    principal = h.principal_probe.call_args.kwargs["principal"]
    assert principal.sub == attacker.user_id
    assert principal.institution_id == attacker.institution_id


def test_m8_http_forged_headers_cannot_change_owner_or_request_id(harness):
    h = harness
    owner, foreign = h.identities[0], h.identities[2]
    forged_request_id = str(uuid4())
    request_headers = {
        **headers(h, owner),
        "X-Student-ID": str(foreign.student_id),
        "X-User-ID": str(foreign.user_id),
        "X-Tenant-ID": str(foreign.institution_id),
        "X-Institution-ID": str(foreign.institution_id),
        "X-Role": "ADMIN",
        "X-Request-ID": forged_request_id,
    }
    response = post(h, uuid4(), request_headers)
    assert response.status_code == 200
    rows, _ = snapshot(h)
    assert len(rows) == 1
    assert rows[0]["student_id"] == owner.student_id
    assert rows[0]["institution_id"] == owner.institution_id
    observed = h.principal_probe.call_args.kwargs
    assert observed["principal"].sub == owner.user_id
    assert observed["principal"].role == "STUDENT"
    assert observed["request_id"] == response.headers["X-Request-ID"] != forged_request_id


@pytest.mark.parametrize(
    "case", ["coordinator", "admin", "unknown-user", "wrong-tenant", "disabled"]
)
def test_m8_http_unentitled_principal_is_denied_before_provider(harness, case):
    h = harness
    owner = h.identities[0]
    changes = {}
    if case in {"coordinator", "admin"}:
        changes["role"] = case.upper()
    elif case == "unknown-user":
        changes["sub"] = str(uuid4())
    elif case == "wrong-tenant":
        changes["institution_id"] = str(h.identities[2].institution_id)
    else:
        with Session(h.engine) as db:
            user = db.get(User, owner.user_id)
            user.status = "DISABLED"
            db.commit()
    before = snapshot(h)
    response = post(h, uuid4(), {"Authorization": "Bearer " + token(h, owner, changes=changes)})
    assert_denied(h, response, before)


def test_m8_http_forged_body_identity_is_rejected(harness):
    h = harness
    before = snapshot(h)
    response = post(
        h,
        uuid4(),
        headers(h, h.identities[0]),
        student_id=str(h.identities[2].student_id),
        institution_id=str(h.identities[2].institution_id),
    )
    assert response.status_code == 422
    assert snapshot(h) == before
    h.factory.assert_not_called()
