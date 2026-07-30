"""End-to-end smoke test against a running stack (./run up first).

Exercises every code path the design cares about:
  - create a link  (LinkCreator + RangeLease + Base62Codec)
  - follow it -> 302 with the right Location  (RedirectHandler, cache MISS)
  - follow it again -> served from cache  (RedirectHandler, cache HIT)
  - custom alias + duplicate-alias 409
  - unknown code -> 404
  - /stats reflects hit ratio, ranges leased, link count

Uses only the stdlib so it runs on the host with no extra deps:
    python3 tests/smoke.py [BASE_URL]
"""

import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8310"


def req(method, path, body=None, expect=None, follow=True):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method)
    if data:
        r.add_header("content-type", "application/json")
    opener = urllib.request.build_opener(
        urllib.request.HTTPRedirectHandler if follow else _NoRedirect()
    )
    try:
        resp = opener.open(r)
        status, raw_headers, payload = resp.status, resp.headers, resp.read()
    except urllib.error.HTTPError as e:
        status, raw_headers, payload = e.code, e.headers, e.read()
    # Case-insensitive header dict (HTTP header names are case-insensitive).
    headers = {k.lower(): v for k, v in raw_headers.items()}
    if expect is not None and status != expect:
        raise AssertionError(f"{method} {path}: expected {expect}, got {status}: {payload[:200]!r}")
    try:
        body = json.loads(payload)
    except (ValueError, TypeError):
        body = payload
    return status, headers, body


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def main():
    long_url = "https://example.com/a/very/long/path?q=1&r=2"

    # create
    _, _, created = req("POST", "/links", {"url": long_url}, expect=201)
    code = created["code"]
    assert created["long_url"] == long_url
    print(f"  ok  created {long_url!r} -> /{code}")

    # follow (miss) — do NOT follow the 302, assert on Location
    status, headers, _ = req("GET", f"/{code}", expect=302, follow=False)
    loc = headers.get("location")
    assert loc == long_url, loc
    print(f"  ok  GET /{code} -> 302 {loc}  (cache miss)")

    # follow again (hit)
    req("GET", f"/{code}", expect=302, follow=False)
    print(f"  ok  GET /{code} -> 302  (cache hit)")

    # custom alias + duplicate
    _, _, aliased = req("POST", "/links", {"url": long_url, "alias": "smoke-alias"}, expect=201)
    assert aliased["code"] == "smoke-alias"
    req("POST", "/links", {"url": long_url, "alias": "smoke-alias"}, expect=409)
    print("  ok  custom alias + duplicate-alias 409")

    # invalid url
    req("POST", "/links", {"url": "not-a-url"}, expect=422)
    print("  ok  invalid url -> 422")

    # unknown code
    req("GET", "/zzzzzzzz", expect=404, follow=False)
    print("  ok  unknown code -> 404")

    # stats
    _, _, stats = req("GET", "/stats", expect=200)
    rl = stats["range_lease"]
    rd = stats["redirect"]
    assert stats["total_links"] >= 2
    assert rl["ranges_leased"] >= 1 and rl["ids_issued"] >= 1
    assert rd["hits"] >= 1 and rd["misses"] >= 1
    print(f"  ok  /stats: links={stats['total_links']} "
          f"ranges_leased={rl['ranges_leased']} hit_ratio={rd['hit_ratio']}")

    print("PASS  url-shortener smoke")


if __name__ == "__main__":
    main()
