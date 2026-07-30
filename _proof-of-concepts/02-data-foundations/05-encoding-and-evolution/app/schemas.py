"""The schema versions the demo and tests evolve between."""

from __future__ import annotations

from domain.model import Field, FieldType, Schema

# v1: the original record.
V1 = Schema(
    (
        Field("name", tag=1, type=FieldType.STR),
        Field("email", tag=2, type=FieldType.STR),
    )
)

# v2: adds an `age` field on a NEW tag, with a default — the safe way to grow.
V2 = Schema(
    (
        Field("full_name", tag=1, type=FieldType.STR),  # renamed name → full_name (tag unchanged: fine)
        Field("email", tag=2, type=FieldType.STR),
        Field("age", tag=3, type=FieldType.INT, default=0),
    )
)

# BROKEN: reuses tag 2 for a different type — the change evolution can't survive.
V_BROKEN = Schema(
    (
        Field("name", tag=1, type=FieldType.STR),
        Field("email", tag=2, type=FieldType.INT),  # was STR at tag 2!
    )
)
