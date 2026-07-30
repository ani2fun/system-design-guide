"""TimelineReader — GET /feed: read materialized ids, merge celebrities, hydrate (C4 code element).

Reads the pre-materialized post-id list from the TimelineCache (built by the
fan-out workers), merges in celebrity posts from the CelebrityMerger, sorts by id
(≈ time), then hydrates bodies from the PostRepository. Each post carries its
`source` so the hybrid is visible. Depends only on ports + the merger.
"""

from __future__ import annotations

from domain.celebrity_merger import CelebrityMerger
from domain.ports import PostRepository, TimelineCache


class TimelineReader:
    def __init__(self, cache: TimelineCache, posts: PostRepository, merger: CelebrityMerger) -> None:
        self._cache = cache
        self._posts = posts
        self._merger = merger

    async def read(self, user_id: int, limit: int) -> list[dict[str, object]]:
        materialized = set(await self._cache.recent_ids(user_id, limit))
        celebrity = set(await self._merger.recent_ids(user_id, limit))

        merged = sorted(materialized | celebrity, reverse=True)[:limit]
        if not merged:
            return []

        by_id = {p.id: p for p in await self._posts.hydrate(merged)}
        out: list[dict[str, object]] = []
        for pid in merged:
            post = by_id.get(pid)
            if post is None:
                continue
            out.append(
                {
                    "id": post.id,
                    "author_id": post.author_id,
                    "content": post.content,
                    "source": "materialized" if pid in materialized else "celebrity-merge",
                }
            )
        return out
