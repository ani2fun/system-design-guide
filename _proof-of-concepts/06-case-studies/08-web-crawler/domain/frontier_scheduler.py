"""FrontierScheduler — which URL a fetcher gets next (C4 code element).

Admit: dedup + robots, then enqueue by host. Next: rotate over hosts (so no host
starves the budget and no fetcher hammers one site), skipping any host whose
politeness gate is closed, and pop the first eligible URL.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from domain.politeness_gate import PolitenessGate
from domain.ports import Frontier
from domain.url_deduper import UrlDeduper


class FrontierScheduler:
    def __init__(self, frontier: Frontier, deduper: UrlDeduper, gate: PolitenessGate) -> None:
        self._frontier = frontier
        self._deduper = deduper
        self._gate = gate
        self._last_host: str | None = None
        self.admitted = 0
        self.rejected = 0

    async def admit(self, url: str) -> bool:
        if not self._gate.allowed_by_robots(url) or not await self._deduper.is_new(url):
            self.rejected += 1
            return False
        host = urlsplit(UrlDeduper.normalize(url)).hostname or ""
        await self._frontier.enqueue(host, UrlDeduper.normalize(url))
        self.admitted += 1
        return True

    async def next(self) -> str | None:
        hosts = sorted(await self._frontier.hosts())
        if not hosts:
            return None
        start = hosts.index(self._last_host) + 1 if self._last_host in hosts else 0
        for offset in range(len(hosts)):
            host = hosts[(start + offset) % len(hosts)]
            if await self._frontier.size(host) > 0 and await self._gate.try_open(host):
                self._last_host = host
                return await self._frontier.pop(host)
        return None  # everything queued is politeness-gated right now
