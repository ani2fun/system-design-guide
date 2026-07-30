"""PolitenessGate — robots rules + per-host rate limit (C4 code element).

Two checks: a static robots policy (disallowed path prefixes per host, evaluated
at admit time) and a per-host rate gate (evaluated at dispatch time). A URL only
leaves the frontier when its host's gate opens.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from domain.ports import HostGate


class PolitenessGate:
    def __init__(
        self, gate: HostGate, disallow: dict[str, list[str]], interval_ms: int = 800
    ) -> None:
        self._gate = gate
        self._disallow = disallow
        self._interval = interval_ms

    def allowed_by_robots(self, url: str) -> bool:
        parts = urlsplit(url)
        host = parts.hostname or ""
        return not any(parts.path.startswith(prefix) for prefix in self._disallow.get(host, []))

    async def try_open(self, host: str) -> bool:
        return await self._gate.try_open(host, self._interval)
