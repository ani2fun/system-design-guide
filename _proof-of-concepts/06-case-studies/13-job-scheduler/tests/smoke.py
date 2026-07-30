"""Scheduler smoke: leader election + fencing, effectively-once claim, redelivery.

    python tests/smoke.py [BASE_URL]
"""

import concurrent.futures
import json
import sys
import time
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8430"


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    if data:
        req.add_header("content-type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, None


def main() -> None:
    # leader election: only one leader; a new leadership mints a higher epoch
    _, a = call("POST", "/leader/acquire", {"node": "A"})
    _, b = call("POST", "/leader/acquire", {"node": "B"})
    assert a["leader"] is True and b["leader"] is False, (a, b)
    e1 = a["epoch"]
    print(f"  ok  leader election: A leads (epoch {e1}); B rejected while A holds the lease")

    call("POST", "/executions", {"execution_id": "d1", "due_ms": 0})
    time.sleep(0.7)  # lease TTL (600ms) lapses
    _, b2 = call("POST", "/leader/acquire", {"node": "B"})
    assert b2["leader"] is True and b2["epoch"] > e1, b2
    print(f"  ok  fencing epoch is monotonic: new leader B got epoch {b2['epoch']} > {e1}")

    stale, _ = call("POST", "/dispatch", {"execution_id": "d1", "epoch": e1})
    fresh, _ = call("POST", "/dispatch", {"execution_id": "d1", "epoch": b2["epoch"]})
    assert stale == 409 and fresh == 200, (stale, fresh)
    print("  ok  double-fire guard: stale-epoch dispatch rejected (409); current-epoch accepted")

    # effectively-once: at-least-once delivery, one winner
    call("POST", "/executions", {"execution_id": "e1", "due_ms": 0})
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        outcomes = list(ex.map(lambda i: call("POST", "/claim", {"execution_id": "e1", "worker": f"w{i}"}), range(10)))
    claimed = sum(1 for _, r in outcomes if r and r["claimed"])
    assert claimed == 1, f"expected exactly one claim, got {claimed}"
    print(f"  ok  effectively-once: 10 workers raced to claim → exactly {claimed} won")

    # heartbeat/redelivery: a silent worker's execution is reclaimed
    call("POST", "/executions", {"execution_id": "e2", "due_ms": 0})
    _, c1 = call("POST", "/claim", {"execution_id": "e2", "worker": "W1"})
    assert c1["claimed"] is True
    time.sleep(0.6)  # visibility (500ms) lapses without a heartbeat
    _, rec = call("POST", "/reclaim", None)
    assert rec["reclaimed"] >= 1, rec
    _, c2 = call("POST", "/claim", {"execution_id": "e2", "worker": "W2"})
    assert c2["claimed"] is True
    print("  ok  redelivery: silent worker's execution reclaimed → claimed by a healthy worker")

    print("PASS  job-scheduler smoke")


if __name__ == "__main__":
    main()
