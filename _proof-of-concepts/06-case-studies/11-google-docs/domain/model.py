"""Editing domain model — a single-character text operation (no I/O)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Kind(str, Enum):
    INS = "ins"    # insert `char` at `pos`
    DEL = "del"    # delete the char at `pos`
    NOOP = "noop"  # transformed away (e.g. both sides deleted the same char)


@dataclass(frozen=True, slots=True)
class Op:
    kind: Kind
    pos: int
    char: str = ""
