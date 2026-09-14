import os
from uuid import uuid4
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import jwt
import time

from app.infrastructure.models.students import Institution, Student, User
from app.main import create_app
from fastapi.testclient import TestClient

@pytest.fixture
def harness():
    url = os.environ.get("M8_TEST_DATABASE_URL")
    if not url:
        pytest.skip("M8_TEST_DATABASE_URL required")
    engine = create_engine(url)
    
    with Session(engine, expire_on_commit=False) as db:
        tenants = [
            Institution(code=f"M9-{uuid4().hex}", name="M9 Test Tenant 1"),
            Institution(code=f"M9-{uuid4().hex}", name="M9 Test Tenant 2"),
        ]
        db.add_all(tenants)
        db.flush()
        
        users = []
        students = []
        for tenant in tenants:
            u = User(id=uuid4(), institution_id=tenant.id, login=f"{uuid4().hex}@test.com", status="ACTIVE", source_type="SYSTEM", source_reference="m9-test")
            db.add(u)
            db.flush()
            s = Student(id=uuid4(), user_id=u.id, institution_id=tenant.id, roll_number=f"ENR-{uuid4().hex}", source_type="SYSTEM", source_reference="m9-test")
            db.add(s)
            db.flush()
            users.append(u)
            students.append(s)
            
        db.commit()
        
        class Harness:
            def __init__(self):
                self.app = create_app()
                self.client = None # Will be set below
                self.t1 = tenants[0]
                self.t2 = tenants[1]
                self.u1 = users[0]
                self.s1 = students[0]
                self.u2 = users[1]
                self.s2 = students[1]
                self.settings = self.app.state.settings
                
            def token(self, user, student, institution):
                payload = {
                    "sub": str(user.id),
                    "role": "STUDENT",
                        "iss": self.settings.jwt_issuer,
                        "aud": self.settings.jwt_audience,
                    "institution_id": str(institution.id),
                    "student_id": str(student.id),
                        "iat": int(time.time()),
                        "exp": int(time.time()) + 300
                }
                return jwt.encode(payload, self.settings.jwt_secret.get_secret_value(), algorithm="HS256")
                
        harness = Harness()
        with TestClient(harness.app) as client:
            harness.client = client
            yield harness

@patch("app.api.routers.copilot.AsyncOpenAI")
def test_m9_11_unauthenticated(mock_openai, harness):
    res = harness.client.get("/api/v1/copilot/conversations")
    assert res.status_code == 401

@patch("app.api.routers.copilot.AsyncOpenAI")
def test_m9_12_cross_student(mock_openai, harness):
    # Student 1 creates conv
    tok1 = harness.token(harness.u1, harness.s1, harness.t1)
    res = harness.client.post("/api/v1/copilot/conversations", headers={"Authorization": f"Bearer {tok1}"})
    assert res.status_code == 200
    conv_id = res.json()["id"]
    
    # Student 2 tries to read it
    tok2 = harness.token(harness.u2, harness.s2, harness.t2)
    res2 = harness.client.get(f"/api/v1/copilot/conversations/{conv_id}", headers={"Authorization": f"Bearer {tok2}"})
    assert res2.status_code == 403

@patch("app.api.routers.copilot.AsyncOpenAI")
def test_m9_flow(mock_openai, harness):
    tok = harness.token(harness.u1, harness.s1, harness.t1)
    # Create conversation
    res = harness.client.post("/api/v1/copilot/conversations", headers={"Authorization": f"Bearer {tok}"})
    assert res.status_code == 200
    conv_id = res.json()["id"]
    
    # List conversations
    res2 = harness.client.get("/api/v1/copilot/conversations", headers={"Authorization": f"Bearer {tok}"})
    assert res2.status_code == 200
    assert len(res2.json()) >= 1
    
    # Get history
    res3 = harness.client.get(f"/api/v1/copilot/conversations/{conv_id}", headers={"Authorization": f"Bearer {tok}"})
    assert res3.status_code == 200
    assert res3.json() == []

