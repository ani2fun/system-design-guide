"""SegmentTranscoder — one segment → one rendition, idempotent (C4 code element).

Output is **content-addressed** by (video, segment, rendition), so re-executing
a task overwrites with identical bytes — a retry or duplicate delivery is
harmless. (Real transcoding shells out to ffmpeg; here the 'rendition' is
deterministic placeholder bytes, which is all the DAG semantics need.)
"""

from __future__ import annotations

import hashlib

from pipeline.ports import RenditionStore


class SegmentTranscoder:
    def __init__(self, store: RenditionStore) -> None:
        self._store = store

    @staticmethod
    def key(video: str, segment: int, rendition: str) -> str:
        return hashlib.sha256(f"{video}:{segment}:{rendition}".encode()).hexdigest()

    async def transcode(self, video: str, segment: int, rendition: str) -> str:
        key = self.key(video, segment, rendition)
        if await self._store.exists(key):
            return key  # idempotent: already produced
        await self._store.put(key, f"{rendition} of {video} seg {segment}".encode())
        return key
