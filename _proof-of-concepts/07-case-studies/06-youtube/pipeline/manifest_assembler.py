"""ManifestAssembler — the fan-in (C4 code element).

Once every rendition of every segment exists, write one adaptive manifest per
rendition (the ordered list of its segment keys) and flip the video to 'live'.
"""

from __future__ import annotations

from pipeline.ports import MetadataStore
from pipeline.segment_transcoder import SegmentTranscoder


class ManifestAssembler:
    def __init__(self, meta: MetadataStore) -> None:
        self._meta = meta

    async def assemble(self, video: str, segments: int, renditions: list[str]) -> None:
        for rendition in renditions:
            keys = [SegmentTranscoder.key(video, s, rendition) for s in range(segments)]
            await self._meta.put_manifest(video, rendition, keys)
        await self._meta.set_state(video, "live")
