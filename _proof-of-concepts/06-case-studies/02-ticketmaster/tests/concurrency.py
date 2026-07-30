"""The decisive test: N buyers stampede one seat; exactly one may win.

Runs against a live stack (./run up first). Fires many concurrent /confirm
requests for the SAME seat and asserts the no-double-booking invariant on the
SAFE (FOR UPDATE) path. Then repeats on the UNSAFE (no-lock) path to
*demonstrate* the anomaly the lock prevents.

    python3 tests/concurrency.py [BASE_URL] [N]
"""

import concurrent.futures
import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8320"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 25
SEAT = "show-1:S1"


def post(path, body):
    r = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode(), method="POST",
        headers={"content-type": "application/json"},
    )
    try:
        resp = urllib.request.urlopen(r)
        return resp.status
    except urllib.error.HTTPError as e:
        return e.code


def get(path):
    with urllib.request.urlopen(BASE + path) as resp:
        return json.loads(resp.read())


def stampede(unsafe: bool) -> tuple[int, int]:
    post("/reset", {})
    bodies = [
        {"seat_id": SEAT, "holder": f"buyer-{i}", "payment_key": f"pay-{i}", "unsafe": unsafe}
        for i in range(N)
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=N) as ex:
        codes = list(ex.map(lambda b: post("/confirm", b), bodies))
    wins = sum(1 for c in codes if c == 201)
    seat = get(f"/seats/{SEAT}")
    return wins, seat["orders"]


def main():
    print(f"stampede: {N} concurrent /confirm on {SEAT}")

    wins, orders = stampede(unsafe=False)
    print(f"  SAFE   (SELECT ... FOR UPDATE): {wins} confirmed, {orders} order(s) for the seat")
    assert wins == 1, f"expected exactly 1 winner, got {wins}"
    assert orders == 1, f"double-booking! {orders} orders for one seat"
    print("  ok  invariant held — exactly one buyer got the seat")

    wins_u, orders_u = stampede(unsafe=True)
    print(f"  UNSAFE (no row lock):           {wins_u} confirmed, {orders_u} order(s) for the seat")
    if orders_u > 1:
        print(f"  ⚠  demonstrated the anomaly: the seat was sold {orders_u} times without the lock")
    else:
        print("  (no double-sell surfaced this run — timing-dependent; the SAFE guarantee is the point)")

    # leave the seat clean
    post("/reset", {})
    print("PASS  ticketmaster concurrency — no double-booking on the locked path")


if __name__ == "__main__":
    main()
