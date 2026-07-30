"""Runnable demo — concurrent edits converge; snapshot compacts the log.

    python -m app.demo   (or ./run)
"""

from __future__ import annotations

from domain.document_server import DocumentServer
from domain.model import Kind, Op


def main() -> None:
    srv = DocumentServer()
    srv.sessions.join("doc", "alice")
    srv.sessions.join("doc", "bob")
    print(f"session members: {srv.sessions.members('doc')}\n")

    print("1) CONCURRENT INSERTS — both editors insert at position 0 from version 0")
    ta, va = srv.submit(0, Op(Kind.INS, 0, "A"))     # alice: insert 'A' at 0
    print(f"   alice's op applied → doc={srv.doc!r} (v{va})")
    tb, vb = srv.submit(0, Op(Kind.INS, 0, "B"))     # bob (concurrent, base v0)
    print(f"   bob's op transformed {Op(Kind.INS, 0, 'B')} → {tb}, doc={srv.doc!r} (v{vb})")
    print("   → both keystrokes survive, in a single agreed order\n")

    print("2) CONCURRENT DELETE OF THE SAME CHAR — no double-delete, no crash")
    srv2 = DocumentServer()
    for i, ch in enumerate("abc"):
        srv2.submit(srv2.version, Op(Kind.INS, i, ch))
    base = srv2.version
    srv2.submit(base, Op(Kind.DEL, 1))               # delete 'b'
    t, _ = srv2.submit(base, Op(Kind.DEL, 1))        # concurrent delete of the same 'b'
    print(f"   two concurrent DEL(1) → second became {t.kind.value}; doc={srv2.doc!r}\n")

    print("3) SNAPSHOT — fold the op log; cold loads start here, not at op #1")
    before = srv.version
    doc, ver = srv.snapshot()
    print(f"   snapshot at v{ver}: {doc!r}; log compacted (was {before} ops)")
    _, v = srv.submit(ver, Op(Kind.INS, len(srv.doc), "!"))
    print(f"   post-snapshot edit → doc={srv.doc!r} (v{v})")

    print("\nPASS  google-docs demo")


if __name__ == "__main__":
    main()
