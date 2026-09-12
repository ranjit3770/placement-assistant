import pytest

from app.core.config import Settings


@pytest.fixture
def settings():
    return Settings(
        _env_file=None,
        app_env="test",
        database_url="postgresql+psycopg://test:test@127.0.0.1:1/test",
        redis_url="redis://127.0.0.1:1/0",
        qdrant_url="http://127.0.0.1:1",
        jwt_secret="test-only-" + "x" * 40,
        dependency_timeout_seconds=0.1,
    )
