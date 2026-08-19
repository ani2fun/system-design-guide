"""Chunker — split a file into content-addressed chunks (C4 code element).

Fixed-size chunks, each named by the hash of its bytes. Because the hash *is*
the identity, dedup and resume fall out for free: an identical chunk anywhere
has the same name. (Real Dropbox uses content-defined chunking at ~4 MB; this
toy uses small fixed chunks so a short file still has several.)
"""

from __future__ import annotations

import hashlib

from agent.model import Chunk


class Chunker:
    def __init__(self, chunk_size: int = 64) -> None:
        self._size = chunk_size

    def chunk(self, data: bytes) -> list[Chunk]:
        return [
            Chunk(hashlib.sha256(block).hexdigest(), block)
            for block in (data[i : i + self._size] for i in range(0, len(data), self._size))
        ]
