"""Frontier smoke: dedup + robots, domain rotation, per-host politeness.

    python tests/smoke.py [BASE_URL]
"""

import json
import sys
import time
import urllib.request
from urllib.parse import urlsplit

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8390"


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    if data:
        req.add_header("content-type", "application/json")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def host(url):
    return urlsplit(url).hostname


def main() -> None:
    # dedup + robots
    call("POST", "/reset")
    r = call("POST", "/seed", {"urls": [
        "http://a.com/x", "http://a.com/x#frag", "HTTP://A.com/x/",   # all normalize to one
        "http://blocked.com/private/secret",                          # robots-disallowed
        "http://blocked.com/public/ok",                               # allowed
    ]})
    assert r["admitted"] == 2, r
    print(f"  ok  dedup + robots: 5 seeded → {r['admitted']} admitted ({r['rejected']} rejected)")

    # domain rotation
    call("POST", "/reset")
    call("POST", "/seed", {"urls": ["http://r1.com/1", "http://r2.com/1", "http://r3.com/1"]})
    hosts = [host(call("GET", "/next")["url"]) for _ in range(3)]
    assert sorted(hosts) == ["r1.com", "r2.com", "r3.com"], hosts
    print(f"  ok  domain rotation: /next visited distinct hosts {hosts}")

    # per-host politeness
    call("POST", "/reset")
    call("POST", "/seed", {"urls": ["http://p.com/1", "http://p.com/2"]})
    first = call("GET", "/next")["url"]
    gated = call("GET", "/next")["url"]
    assert first is not None and gated is None, (first, gated)
    print("  ok  politeness: second fetch of the same host is gated (None)")
    time.sleep(0.9)  # let the host window reopen (INTERVAL_MS=800)
    third = call("GET", "/next")["url"]
    assert third is not None and host(third) == "p.com", third
    print("  ok  politeness window reopened after the interval → p.com/2 dispatched")

    print("PASS  web-crawler smoke")


if __name__ == "__main__":
    main()
