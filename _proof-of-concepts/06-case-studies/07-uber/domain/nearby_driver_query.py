"""NearbyDriverQuery — radius query + ranking (C4 code element).

Read-only against the geo index; freshness is the index's job (TTL'd positions).
The geo index already returns nearest-first, which is the ranking this toy uses.
"""

from __future__ import annotations

from domain.ports import GeoIndex


class NearbyDriverQuery:
    def __init__(self, geo: GeoIndex) -> None:
        self._geo = geo

    async def query(self, lon: float, lat: float, radius_km: float, count: int) -> list[str]:
        return await self._geo.nearby(lon, lat, radius_km, count)
