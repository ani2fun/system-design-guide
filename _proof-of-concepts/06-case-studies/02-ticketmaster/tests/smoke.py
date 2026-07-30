"""End-to-end smoke test against a running stack (./run up first).

    python3 tests/smoke.py [BASE_URL]
"""

import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8320"


def call(method, path, body=None, expect=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method)
    if data:
        r.add_header("content-type", "application/json")
    try:
        resp = urllib.request.urlopen(r)
        status, payload = resp.status, resp.read()
    except urllib.error.HTTPError as e:
        status, payload = e.code, e.read()
    if expect is not None and status != expect:
        raise AssertionError(f"{method} {path}: expected {expect}, got {status}: {payload[:200]!r}")
    try:
        return status, json.loads(payload)
    except (ValueError, TypeError):
        return status, payload


def main():
    call("POST", "/reset", {}, expect=200)
    seat = "show-1:S7"

    # hold, then a second holder is rejected
    call("POST", "/holds", {"seat_id": seat, "holder": "alice"}, expect=201)
    call("POST", "/holds", {"seat_id": seat, "holder": "bob"}, expect=409)
    print("  ok  hold acquired by alice; bob rejected (409)")

    # confirm the sale
    _, order = call("POST", "/confirm",
                    {"seat_id": seat, "holder": "alice", "payment_key": "pk-1"}, expect=201)
    assert order["order_id"]
    print(f"  ok  confirmed -> order {order['order_id']}")

    # the seat is now sold; a second confirm is rejected
    call("POST", "/confirm",
         {"seat_id": seat, "holder": "carol", "payment_key": "pk-2"}, expect=409)
    print("  ok  second confirm on a sold seat rejected (409)")

    # seat probe + stats
    _, s = call("GET", f"/seats/{seat}", expect=200)
    assert s["status"] == "sold" and s["orders"] == 1, s
    _, stats = call("GET", "/stats", expect=200)
    assert stats["double_sold_seats"] == 0, stats
    print(f"  ok  seat sold to {s['sold_to']}, {s['orders']} order, double_sold_seats=0")

    call("POST", "/reset", {}, expect=200)
    print("PASS  ticketmaster smoke")


if __name__ == "__main__":
    main()
