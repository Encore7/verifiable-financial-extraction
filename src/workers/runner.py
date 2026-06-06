"""Worker entrypoint for scheduled ingestion jobs (run as ``python -m workers.runner``).

M0 placeholder: ingestion jobs land in M1. For now this gives the worker image a real,
runnable entrypoint that starts, logs, and shuts down cleanly on SIGINT/SIGTERM — the
behaviour a container orchestrator expects.
"""

import asyncio
import signal

import structlog

from db.engine import dispose_engine

log = structlog.get_logger()


async def run() -> None:
    log.info("worker.started")
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    try:
        await stop.wait()
    finally:
        await dispose_engine()
        log.info("worker.stopped")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
