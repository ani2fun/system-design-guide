"""Rate-limiter smoke: fixed window, rule tiers, atomicity, token-bucket burst.

    python tests/smoke.py [BASE_URL]
"""

import concurrent.futures
import json
import sys
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8400"


def allow(key):
    req = urllib.request.Request(
        BASE + "/allow", data=json.dumps({"key": key}).encode(), method="POST",
        headers={"content-type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def main() -> None:
    # fixed window: limit 5 → 5 allowed, then denied
    allowed = sum(1 for _ in range(6) if allow("free:alice")["allowed"])
    assert allowed == 5, allowed
    print(f"  ok  fixed window (limit 5): {allowed}/6 allowed")

    # rule tiers: vip has limit 100 → all allowed
    assert all(allow("vip:bob")["allowed"] for _ in range(6))
    print("  ok  rule resolution: vip: tier (limit 100) admits all 6")

    # atomicity: 20 concurrent requests, limit 5 → exactly 5 admitted (no over-admit)
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
        results = list(ex.map(lambda _: allow("free:carol"), range(20)))
    admitted = sum(1 for r in results if r["allowed"])
    assert admitted == 5, f"atomic check-and-increment failed: {admitted} admitted, expected 5"
    print(f"  ok  atomicity: 20 concurrent → exactly {admitted} admitted")

    # token bucket: capacity 3 → burst of 3 allowed, 4th denied
    burst = [allow("bucket:dave")["allowed"] for _ in range(4)]
    assert burst[:3] == [True, True, True] and burst[3] is False, burst
    print(f"  ok  token bucket (capacity 3): burst {burst}")

    print("PASS  rate-limiter smoke")


if __name__ == "__main__":
    main()
