"""Fan-out worker composition root: consume post events, materialize timelines.

Wires the write-path adapters into the fan-out pipeline domain services and runs
the consume loop. Same image as the API, different command:

    python -m worker.main
"""

from __future__ import annotations

import asyncio

from redis.asyncio import Redis, from_url

from app.config import CELEB_THRESHOLD, GROUP, PG_DSN, REDIS_URL, STREAM, TIMELINE_MAX
from domain.fanout_consumer import FanoutConsumer
from domain.timeline_fanout import TimelineFanout
from infra.db import create_pool
from infra.postgres import PostgresFollowGraph
from infra.redis_ import RedisFanoutQueue, RedisTimelineCache


async def main() -> None:
    pool = await create_pool(PG_DSN, ensure_schema=False)  # API creates the schema
    redis: Redis = from_url(REDIS_URL, decode_responses=True)  # type: ignore[no-untyped-call]

    fanout = TimelineFanout(
        PostgresFollowGraph(pool), RedisTimelineCache(redis), CELEB_THRESHOLD, TIMELINE_MAX
    )
    queue = RedisFanoutQueue(redis, STREAM, GROUP)
    consumer = FanoutConsumer(queue, fanout)

    await queue.ensure_group()
    print(f"fan-out worker started (stream={STREAM} group={GROUP})", flush=True)
    while True:
        processed = await consumer.run_once()
        if processed:
            print(
                f"fanned_out={fanout.fanned_out} skipped_celebrity={fanout.skipped_celebrity} "
                f"inserts={fanout.inserts}",
                flush=True,
            )


if __name__ == "__main__":
    asyncio.run(main())
