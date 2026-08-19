"""Domain model — entities and value objects (no I/O, no framework).

`LongUrl` is a value object that enforces its own invariant (a valid absolute
http(s) URL) at construction, so an invalid URL can never exist in the domain.
`Link` is the aggregate the write path produces.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from domain.errors import InvalidURLError


@dataclass(frozen=True, slots=True)
class LongUrl:
    """A validated absolute http(s) URL (value object)."""

    value: str

    def __post_init__(self) -> None:
        parsed = urlparse(self.value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise InvalidURLError(f"not an absolute http(s) URL: {self.value!r}")


@dataclass(frozen=True, slots=True)
class Link:
    """A short code bound to its destination (aggregate root of the write path)."""

    code: str
    long_url: LongUrl
