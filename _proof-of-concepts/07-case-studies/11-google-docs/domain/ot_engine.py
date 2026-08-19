"""OtEngine — Operational Transformation (C4 code element).

Rewrites an incoming op against the concurrent ops it hasn't seen, so applying
the canonical sequence yields the same document everywhere. `transform` folds an
op through each concurrent op in canonical order; `apply` executes an op against
a string. Convergence is the whole point: two editors typing at once never lose
a keystroke and never diverge.
"""

from __future__ import annotations

from dataclasses import replace

from domain.model import Kind, Op


class OtEngine:
    def transform(self, op: Op, concurrent: list[Op]) -> Op:
        for other in concurrent:
            op = self._transform_one(op, other)
        return op

    @staticmethod
    def _transform_one(a: Op, b: Op) -> Op:
        if a.kind is Kind.NOOP or b.kind is Kind.NOOP:
            return a
        if a.kind is Kind.INS and b.kind is Kind.INS:
            return replace(a, pos=a.pos + 1) if b.pos <= a.pos else a
        if a.kind is Kind.INS and b.kind is Kind.DEL:
            return replace(a, pos=a.pos - 1) if b.pos < a.pos else a
        if a.kind is Kind.DEL and b.kind is Kind.INS:
            return replace(a, pos=a.pos + 1) if b.pos <= a.pos else a
        # DEL vs DEL
        if b.pos < a.pos:
            return replace(a, pos=a.pos - 1)
        if b.pos == a.pos:
            return replace(a, kind=Kind.NOOP)  # the char is already gone
        return a

    @staticmethod
    def apply(doc: str, op: Op) -> str:
        if op.kind is Kind.INS:
            return doc[: op.pos] + op.char + doc[op.pos :]
        if op.kind is Kind.DEL:
            return doc[: op.pos] + doc[op.pos + 1 :]
        return doc
