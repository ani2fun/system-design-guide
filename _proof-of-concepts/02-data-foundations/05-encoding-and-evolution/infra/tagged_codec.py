"""TaggedCodec — a minimal Protobuf-style tag/type/value binary format.

Wire format per field: [tag:1][type:1][value]. INT ⇒ 8-byte big-endian; STR ⇒
[len:4][utf-8]. Records are just concatenated fields. The evolution rules fall
straight out of decoding against the *reader* schema:

  * unknown tag  → skip it            (forward compatibility: old reader, new data)
  * missing field → use its default    (backward compatibility: new reader, old data)
  * tag reused with a new type → raise  (the change that is NOT safe)
"""

from __future__ import annotations

import struct

from domain.errors import EvolutionError
from domain.model import FieldType, Record, Schema, Value
from domain.ports import Codec


class TaggedCodec(Codec):
    def encode(self, record: Record, schema: Schema) -> bytes:
        out = bytearray()
        for field in schema.fields:
            if field.name not in record:
                continue
            out.append(field.tag)
            out.append(field.type.value)
            value = record[field.name]
            if field.type is FieldType.INT:
                out += struct.pack(">q", int(value))
            else:
                encoded = str(value).encode()
                out += struct.pack(">I", len(encoded)) + encoded
        return bytes(out)

    def decode(self, data: bytes, reader: Schema) -> Record:
        by_tag = reader.by_tag()
        result: Record = {}
        pos = 0
        while pos < len(data):
            tag = data[pos]
            wire = FieldType(data[pos + 1])
            pos += 2
            value: Value
            if wire is FieldType.INT:
                (as_int,) = struct.unpack_from(">q", data, pos)
                pos += 8
                value = int(as_int)
            else:
                (length,) = struct.unpack_from(">I", data, pos)
                pos += 4
                value = data[pos : pos + length].decode()
                pos += length

            field = by_tag.get(tag)
            if field is None:
                continue  # forward compatibility: unknown field, skip it
            if field.type is not wire:
                raise EvolutionError(
                    f"tag {tag} was written as {wire.name} but the reader expects {field.type.name} "
                    f"— reusing a tag with a new type is not a safe change"
                )
            result[field.name] = value

        for field in reader.fields:  # backward compatibility: default the absentees
            if field.name not in result and field.default is not None:
                result[field.name] = field.default
        return result
