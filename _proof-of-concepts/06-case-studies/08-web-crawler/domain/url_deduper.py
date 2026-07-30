"""UrlDeduper — normalize + drop already-seen (C4 code element).

The loop-breaker. Normalization collapses trivially-different URLs to one key
(lowercase scheme/host, drop fragment and default ports, sort the query, trim a
trailing slash); the SeenStore answers exact membership so the frontier never
re-crawls the web into itself.
"""

from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

from domain.ports import SeenStore


class UrlDeduper:
    def __init__(self, seen: SeenStore) -> None:
        self._seen = seen

    @staticmethod
    def normalize(url: str) -> str:
        parts = urlsplit(url.strip())
        scheme = parts.scheme.lower() or "http"
        host = parts.hostname or ""
        port = parts.port
        netloc = host if port in (None, 80, 443) else f"{host}:{port}"
        path = parts.path.rstrip("/") or "/"
        query = "&".join(sorted(parts.query.split("&"))) if parts.query else ""
        return urlunsplit((scheme, netloc, path, query, ""))  # fragment dropped

    async def is_new(self, url: str) -> bool:
        return await self._seen.add_if_new(self.normalize(url))
