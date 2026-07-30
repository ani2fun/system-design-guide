"""Tiny stdlib HTTP helpers shared by the news-feed tests."""

import json
import time
import urllib.error
import urllib.request


def call(base, method, path, body=None, expect=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(base + path, data=data, method=method)
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


def poll(fn, timeout=15.0, interval=0.3):
    """Call fn() until it returns truthy or timeout; returns the value or None."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        v = fn()
        if v:
            return v
        time.sleep(interval)
    return None
