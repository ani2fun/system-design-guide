"""OT correctness + convergence + snapshot tests.

    python tests/test_ot.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from domain.document_server import DocumentServer, StaleBaseError  # noqa: E402
from domain.model import Kind, Op  # noqa: E402
from domain.ot_engine import OtEngine  # noqa: E402


def test_apply() -> None:
    e = OtEngine()
    assert e.apply("hello", Op(Kind.INS, 0, "X")) == "Xhello"
    assert e.apply("hello", Op(Kind.DEL, 0)) == "ello"


def test_transform_insert_vs_insert() -> None:
    e = OtEngine()
    # incoming ins(0,'B') against a concurrent ins(0,'A') → shifts right
    assert e.transform(Op(Kind.INS, 0, "B"), [Op(Kind.INS, 0, "A")]) == Op(Kind.INS, 1, "B")


def test_concurrent_inserts_converge() -> None:
    srv = DocumentServer()
    srv.submit(0, Op(Kind.INS, 0, "A"))
    srv.submit(0, Op(Kind.INS, 0, "B"))   # concurrent from v0
    assert srv.doc == "AB", srv.doc       # both survive, deterministic order


def test_concurrent_delete_same_char() -> None:
    srv = DocumentServer()
    for i, ch in enumerate("abc"):
        srv.submit(srv.version, Op(Kind.INS, i, ch))
    base = srv.version
    srv.submit(base, Op(Kind.DEL, 1))
    transformed, _ = srv.submit(base, Op(Kind.DEL, 1))  # concurrent delete of same char
    assert transformed.kind is Kind.NOOP
    assert srv.doc == "ac", srv.doc                     # 'b' removed exactly once


def test_snapshot_compacts_and_continues() -> None:
    srv = DocumentServer()
    for i, ch in enumerate("hello"):
        srv.submit(srv.version, Op(Kind.INS, i, ch))
    doc, ver = srv.snapshot()
    assert doc == "hello" and ver == 5
    srv.submit(ver, Op(Kind.INS, 5, "!"))
    assert srv.doc == "hello!"


def test_stale_base_after_snapshot_rejected() -> None:
    srv = DocumentServer()
    srv.submit(0, Op(Kind.INS, 0, "x"))
    srv.snapshot()
    try:
        srv.submit(0, Op(Kind.INS, 0, "y"))  # base predates the snapshot
    except StaleBaseError:
        return
    raise AssertionError("expected StaleBaseError")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"PASS  {len(fns)} OT tests")
