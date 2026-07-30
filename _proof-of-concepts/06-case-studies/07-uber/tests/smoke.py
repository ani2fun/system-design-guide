"""Matching smoke + concurrency (needs the stack up).

Proves exactly-once trip creation (idempotent retry) and that a scramble of
riders never double-books a driver — the offer lock serialises the contention.

    python tests/smoke.py [BASE_URL]
"""

import concurrent.futures
import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8380"

P1 = (-122.4194, 37.7749)   # 5 drivers cluster here
P2 = (-73.9857, 40.7484)    # 1 driver far away (for the idempotency case)


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    if data:
        req.add_header("content-type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        return e.code, None


def main() -> None:
    for i in range(1, 6):
        call("POST", f"/drivers/p1_d{i}/location", {"lon": P1[0] + i * 1e-4, "lat": P1[1]})
    call("POST", "/drivers/p2_solo/location", {"lon": P2[0], "lat": P2[1]})

    # exactly-once: match the same request twice → identical trip
    _, first = call("POST", "/match", {"request_id": "idem", "lon": P2[0], "lat": P2[1]})
    _, again = call("POST", "/match", {"request_id": "idem", "lon": P2[0], "lat": P2[1]})
    assert first is not None and again == first, (first, again)
    print(f"  ok  exactly-once: retry returned the same trip {first['trip_id']} / driver {first['driver_id']}")

    # contention: 8 riders, 5 drivers, all at P1, fired concurrently
    reqs = [{"request_id": f"c{i}", "lon": P1[0], "lat": P1[1]} for i in range(8)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        outcomes = list(ex.map(lambda b: call("POST", "/match", b), reqs))
    matched = [r for status, r in outcomes if status == 200 and r is not None]
    drivers = [r["driver_id"] for r in matched]
    assert len(matched) == 5, f"expected 5 matches for 5 drivers, got {len(matched)}"
    assert len(set(drivers)) == 5, f"a driver was double-booked: {drivers}"
    print(f"  ok  8 riders / 5 drivers → {len(matched)} matched, all distinct; {8 - len(matched)} got no-driver (409)")

    _, s = call("GET", "/stats")
    assert s is not None and s["trips"] == s["distinct_drivers_assigned"] + 0  # sanity: no dup driver in a trip set
    print(f"  ok  /stats: {s['trips']} trips across {s['distinct_drivers_assigned']} distinct drivers")
    print("PASS  uber smoke")


if __name__ == "__main__":
    main()
