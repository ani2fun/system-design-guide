"""DagOrchestrator — fan-out the task matrix, fan-in when complete (C4 code element).

Expands a video into segment×rendition tasks, runs each idempotent transcode,
then checks completeness from the rendition store itself (existence = done). If
every task is done it assembles manifests and goes live; otherwise the video
stays 'processing' and a later re-run retries only the missing tasks — retry at
task granularity, safe because tasks are idempotent.

`fail` simulates one task failing this run, to demonstrate task-granular retry.
"""

from __future__ import annotations

from pipeline.manifest_assembler import ManifestAssembler
from pipeline.model import Progress
from pipeline.ports import MetadataStore, RenditionStore
from pipeline.segment_transcoder import SegmentTranscoder


class DagOrchestrator:
    def __init__(
        self,
        transcoder: SegmentTranscoder,
        assembler: ManifestAssembler,
        store: RenditionStore,
        meta: MetadataStore,
    ) -> None:
        self._transcoder = transcoder
        self._assembler = assembler
        self._store = store
        self._meta = meta

    async def process(
        self,
        video: str,
        segments: int,
        renditions: list[str],
        fail: tuple[int, str] | None = None,
    ) -> Progress:
        total = segments * len(renditions)
        await self._meta.set_state(video, "processing")
        for segment in range(segments):
            for rendition in renditions:
                if fail is not None and (segment, rendition) == fail:
                    continue  # simulate this task failing on this run
                await self._transcoder.transcode(video, segment, rendition)

        done = await self._count_done(video, segments, renditions)
        if done == total:
            await self._assembler.assemble(video, segments, renditions)
            return Progress(video, total, done, "live")
        return Progress(video, total, done, "processing")

    async def _count_done(self, video: str, segments: int, renditions: list[str]) -> int:
        done = 0
        for segment in range(segments):
            for rendition in renditions:
                if await self._store.exists(SegmentTranscoder.key(video, segment, rendition)):
                    done += 1
        return done
