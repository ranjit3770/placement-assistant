import asyncio
from collections.abc import Awaitable, Callable
from typing import cast

import httpx
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import Settings


class Dependencies:
    def __init__(self, settings: Settings) -> None:
        self.timeout = settings.dependency_timeout_seconds
        self.engine = create_async_engine(
            settings.database_url.get_secret_value(), pool_pre_ping=True, pool_timeout=self.timeout, pool_size=20, max_overflow=10
        )
        self.redis = Redis.from_url(
            settings.redis_url.get_secret_value(),
            socket_connect_timeout=self.timeout,
            socket_timeout=self.timeout,
        )
        self.http = httpx.AsyncClient(base_url=settings.qdrant_url, timeout=self.timeout)

    async def close(self) -> None:
        await self.engine.dispose()
        await self.redis.aclose()
        await self.http.aclose()

    async def postgres(self) -> None:
        async with self.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    async def cache(self) -> None:
        # Redis shares command annotations between sync and async clients.
        await cast(Awaitable[bool], self.redis.ping())

    async def vector(self) -> None:
        response = await self.http.get("/readyz")
        response.raise_for_status()

    async def check(self) -> dict[str, str]:
        async def probe(call: Callable[[], Awaitable[None]]) -> str:
            try:
                async with asyncio.timeout(self.timeout):
                    await call()
                return "up"
            except Exception:
                # Never return dependency URLs, credentials or exception messages.
                return "down"

        results = await asyncio.gather(
            *(probe(c) for c in (self.postgres, self.cache, self.vector))
        )
        return dict(zip(("postgres", "redis", "qdrant"), results, strict=True))
