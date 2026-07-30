"""Domain model — schemas as ordered, tagged fields (no I/O).

Every field carries a **numeric tag** (the thing that survives renames) and a
type. A reader schema may add fields (with defaults) or drop fields it no longer
cares about; the tag is the stable contract, exactly as in Protobuf/Thrift.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

Value = int | str
Record = dict[str, Value]


class FieldType(Enum):
    INT = 1
    STR = 2


@dataclass(frozen=True, slots=True)
class Field:
    name: str
    tag: int                 # the stable identity — rename the name freely, never reuse the tag
    type: FieldType
    default: Value | None = None


@dataclass(frozen=True, slots=True)
class Schema:
    fields: tuple[Field, ...]

    def by_tag(self) -> dict[int, Field]:
        return {f.tag: f for f in self.fields}
