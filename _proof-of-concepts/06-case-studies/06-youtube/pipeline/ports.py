"""Ports — the abstractions the pipeline depends on (Dependency Inversion).

`RenditionStore` is content-addressed (a rendition's *existence* is the DAG's
record that its task is done). `MetadataStore` holds the video state machine and
the assembled manifests. The pipeline never imports redis.
"""

from __future__ import annotations

import abc


class RenditionStore(abc.ABC):
    @abc.abstractmethod
    async def exists(self, key: str) -> bool: ...

    @abc.abstractmethod
    async def put(self, key: str, data: bytes) -> None: ...


class MetadataStore(abc.ABC):
    @abc.abstractmethod
    async def set_state(self, video: str, state: str) -> None: ...

    @abc.abstractmethod
    async def get_state(self, video: str) -> str: ...

    @abc.abstractmethod
    async def put_manifest(self, video: str, rendition: str, keys: list[str]) -> None: ...

    @abc.abstractmethod
    async def manifests(self, video: str) -> dict[str, list[str]]: ...
