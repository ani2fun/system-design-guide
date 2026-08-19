"""RedirectHandler — the GET /{code} read path (C4 code element).

Cache-aside read through the RedirectCache and LinkRepository ports, then emit a
click through the ClickPublisher port. The publisher owns fire-and-forget
delivery, so the domain simply awaits it and the redirect never blocks on
analytics.
"""

from __future__ import annotations

from domain.ports import ClickPublisher, LinkRepository, RedirectCache


class RedirectHandler:
    def __init__(
        self, cache: RedirectCache, repo: LinkRepository, clicks: ClickPublisher, ttl: int = 3600
    ) -> None:
        self._cache = cache
        self._repo = repo
        self._clicks = clicks
        self._ttl = ttl
        self.hits = 0
        self.misses = 0

    async def resolve(self, code: str) -> str | None:
        url = await self._cache.get(code)
        if url is not None:
            self.hits += 1
        else:
            self.misses += 1
            url = await self._repo.get(code)
            if url is None:
                return None
            await self._cache.set(code, url, self._ttl)
        await self._clicks.publish(code)
        return url

    def status(self) -> dict[str, float | int | None]:
        total = self.hits + self.misses
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_ratio": round(self.hits / total, 4) if total else None,
        }
