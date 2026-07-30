"""End-to-end two-device sync over HTTP (needs the file service up).

    python tests/smoke.py [BASE_URL]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.chunker import Chunker  # noqa: E402
from agent.sync_engine import SyncEngine  # noqa: E402
from client.http_client import HttpFileService  # noqa: E402

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8360"


def main() -> None:
    svc = HttpFileService(BASE)
    device_a = SyncEngine(svc, Chunker(64))
    device_b = SyncEngine(svc, Chunker(64))

    original = b"content-addressed sync means only changed chunks travel. " * 6
    r1 = device_a.push("report.txt", original)
    print(f"  ok  device A pushed report.txt: {r1.chunks_total} chunks, {r1.uploaded} uploaded")

    assert device_b.pull("report.txt") == original
    print("  ok  device B pulled an identical file")

    edited = original[:64] + b"EDITED-TAIL " * 6            # change only the tail
    r2 = device_a.push("report.txt", edited)
    assert r2.changed >= 1 and r2.uploaded == r2.changed and r2.uploaded < r2.chunks_total
    print(f"  ok  delta sync: {r2.chunks_total} chunks, only {r2.uploaded} changed chunk(s) uploaded")
    assert device_b.pull("report.txt") == edited
    print("  ok  device B pulled the edited file")

    r3 = device_a.push("copy.txt", edited)                  # same content, new path
    assert r3.uploaded == 0
    print("  ok  global dedup: identical content at a new path uploaded 0 chunks")

    print("PASS  dropbox smoke")


if __name__ == "__main__":
    main()
