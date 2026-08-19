"""CelebrityMerger — the read-half of the hybrid fan-out (C4 code element).

Celebrity posts are never fanned out, so the reader pulls them live: the recent
posts of the celebrity accounts this user follows. Depends on the FeedQueries
port.
"""

from __future__ import annotations

from domain.ports import FeedQueries


class CelebrityMerger:
    def __init__(self, queries: FeedQueries, threshold: int) -> None:
        self._queries = queries
        self._threshold = threshold

    async def recent_ids(self, user_id: int, limit: int) -> list[int]:
        return await self._queries.celebrity_recent_post_ids(user_id, self._threshold, limit)
