"""Streaming-aggregation smoke: dedup, event-time windows, watermark, late correction.

    python tests/smoke.py [BASE_URL]
"""

import json
import sys
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8410"


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    if data:
        req.add_header("content-type", "application/json")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def click(ad, imp, t):
    return call("POST", "/clicks", {"ad_id": ad, "impression_id": imp, "event_time_ms": t})


def windows(ad):
    return {w["window_start_ms"]: w["count"] for w in call("GET", f"/metrics/{ad}")["windows"]}


def main() -> None:
    call("POST", "/reset")

    # window [0,1000): i1,i2 ; window [1000,2000): i3 ; i4 at 2500 advances the watermark
    click("A", "i1", 100)
    click("A", "i2", 200)
    click("A", "i3", 1500)
    click("A", "i4", 2500)          # watermark → 2500, closing windows 0 and 1000
    w = windows("A")
    assert w == {0: 2, 1000: 1}, w   # window [2000,3000) not closed yet
    print(f"  ok  event-time windows: {w} (window 2000 held back by the watermark)")

    # dedup: replay i1 → not counted, counts unchanged
    assert click("A", "i1", 100)["counted"] is False
    assert windows("A") == {0: 2, 1000: 1}
    print("  ok  dedup: replayed impression i1 dropped, counts unchanged")

    # late click into an already-emitted window → correction (upsert), not a lost count
    click("A", "i5", 500)            # window [0,1000), already emitted
    w = windows("A")
    assert w[0] == 3, w
    print(f"  ok  late correction: window 0 upserted 2 → {w[0]}")

    print("PASS  ad-click-aggregator smoke")


if __name__ == "__main__":
    main()
