"""Payment smoke: idempotency (incl. concurrent), state machine, double-entry.

    python tests/smoke.py [BASE_URL]
"""

import concurrent.futures
import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8420"


def call(method, path, body=None, expect=None):
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
    # idempotency: same key ⇒ same payment, charged once
    _, a = call("POST", "/charge", {"idempotency_key": "k1", "amount": 1000, "merchant": "m1"})
    _, b = call("POST", "/charge", {"idempotency_key": "k1", "amount": 1000, "merchant": "m1"})
    assert a["payment_id"] == b["payment_id"] and a["state"] == "captured", (a, b)
    _, bal = call("GET", "/balance/merchant:m1")
    assert bal["balance"] == 1000, bal          # charged once, not twice
    print(f"  ok  idempotency: retry replayed payment {a['payment_id']}; merchant balance {bal['balance']}")

    # concurrent retries of one key ⇒ one charge
    def fire(_):
        return call("POST", "/charge", {"idempotency_key": "k2", "amount": 500, "merchant": "m2"})[1]
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        results = list(ex.map(fire, range(10)))
    ids = {r["payment_id"] for r in results}
    _, bal2 = call("GET", "/balance/merchant:m2")
    assert len(ids) == 1 and bal2["balance"] == 500, (ids, bal2)
    print(f"  ok  10 concurrent charges of one key → one payment {ids}, balance {bal2['balance']}")

    # state machine: illegal transition rejected
    status, _ = call("POST", "/transition", {"state": "created", "event": "capture"})
    assert status == 409
    _, ok = call("POST", "/transition", {"state": "created", "event": "authorize"})
    assert ok["to_state"] == "authorized"
    print("  ok  state machine: created→capture rejected (409); created→authorize allowed")

    # double-entry: every posting nets to zero
    _, s = call("GET", "/stats")
    assert s["ledger_sum"] == 0, s
    print(f"  ok  double-entry: {s['payments']} payments, ledger sums to {s['ledger_sum']}")

    print("PASS  stripe-payments smoke")


if __name__ == "__main__":
    main()
