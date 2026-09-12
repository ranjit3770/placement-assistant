"""Foundation worker heartbeat; business jobs are introduced in later milestones."""

import asyncio
import logging
import signal

from redis.asyncio import Redis

from app.core.config import Settings
from app.core.logging import configure_logging


async def run() -> None:
    settings = Settings()  # type: ignore[call-arg]
    configure_logging()
    logger = logging.getLogger("placement")
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)
    async with Redis.from_url(
        settings.redis_url.get_secret_value(), socket_timeout=2, socket_connect_timeout=2
    ) as redis:
        while not stop.is_set():
            try:
                await redis.set("placement:worker:heartbeat", "alive", ex=30)
            except Exception:
                logger.warning("worker_dependency_unavailable")
            try:
                await asyncio.wait_for(stop.wait(), timeout=10)
            except TimeoutError:
                pass


if __name__ == "__main__":
    asyncio.run(run())
