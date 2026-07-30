"""TimelineFanout — the write-half of the hybrid fan-out (C4 code element).

For a normal author, insert the post id into every follower's materialized
timeline. Celebrity authors are skipped — the read path merges their posts in
instead. Inserts are idempotent (the cache uses the post id as the sort member),
so an at-least-once redelivery is harmless. Depends on the FollowGraph and
TimelineCache ports.
"""

from __future__ import annotations

from domain.ports import FollowGraph, TimelineCache


class TimelineFanout:
    def __init__(
        self, graph: FollowGraph, cache: TimelineCache, threshold: int, timeline_max: int
    ) -> None:
        self._graph = graph
        self._cache = cache
        self._threshold = threshold
        self._max = timeline_max
        self.fanned_out = 0
        self.skipped_celebrity = 0
        self.inserts = 0

    async def fanout(self, post_id: int, author_id: int) -> None:
        if await self._graph.follower_count(author_id) >= self._threshold:
            self.skipped_celebrity += 1
            return
        followers = await self._graph.followers(author_id)
        if followers:
            await self._cache.add_to_many(followers, post_id, self._max)
            self.inserts += len(followers)
        self.fanned_out += 1
