"""Ports — the codec abstraction (Dependency Inversion).

`Codec` is an explicit `abc.ABC`: the tagged binary codec implements it, and a
real Avro/Protobuf-backed codec could too, without the demo changing.
"""

from __future__ import annotations

import abc

from domain.model import Record, Schema


class Codec(abc.ABC):
    @abc.abstractmethod
    def encode(self, record: Record, schema: Schema) -> bytes:
        """Serialize `record` per `schema` (the writer schema)."""

    @abc.abstractmethod
    def decode(self, data: bytes, reader: Schema) -> Record:
        """Deserialize `data` against `reader` (the reader schema) — resolving
        unknown fields and missing fields as evolution demands."""
