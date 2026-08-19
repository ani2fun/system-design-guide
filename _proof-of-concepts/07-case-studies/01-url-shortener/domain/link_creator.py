"""LinkCreator — the POST /links write path (C4 code element).

Orchestrates the domain: validate the URL (via the LongUrl value object), take
the next id from the RangeLease, encode it, and persist through the
LinkRepository port. Depends on abstractions only.
"""

from __future__ import annotations

from domain.base62_codec import Base62Codec
from domain.model import Link, LongUrl
from domain.ports import LinkRepository
from domain.range_lease import RangeLease


class LinkCreator:
    def __init__(self, repo: LinkRepository, range_lease: RangeLease, codec: Base62Codec) -> None:
        self._repo = repo
        self._range = range_lease
        self._codec = codec

    async def create(self, long_url: str, custom_alias: str | None = None) -> str:
        url = LongUrl(long_url)  # raises InvalidURLError on a bad URL
        code = custom_alias if custom_alias else self._codec.encode(await self._range.next_id())
        # repo.add raises DuplicateCodeError if the code/alias is taken.
        await self._repo.add(Link(code=code, long_url=url))
        return code
