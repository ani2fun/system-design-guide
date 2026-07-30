"""End-to-end transcode-DAG smoke (needs the pipeline up).

    python tests/smoke.py [BASE_URL]
"""

import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8370"


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    if data:
        req.add_header("content-type", "application/json")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def main() -> None:
    # full run: 3 segments × 3 renditions = 9 tasks → live
    p = call("POST", "/videos", {"video_id": "v1", "segments": 3, "renditions": ["240p", "480p", "720p"]})
    assert p["tasks_total"] == 9 and p["tasks_done"] == 9 and p["state"] == "live", p
    print(f"  ok  v1 processed: {p['tasks_done']}/{p['tasks_total']} tasks → {p['state']}")

    v = call("GET", "/videos/v1")
    assert v["state"] == "live" and len(v["manifests"]) == 3, v
    assert all(len(keys) == 3 for keys in v["manifests"].values()), v
    print("  ok  3 adaptive manifests, 3 segments each")

    p2 = call("POST", "/videos", {"video_id": "v1", "segments": 3, "renditions": ["240p", "480p", "720p"]})
    assert p2["tasks_done"] == 9 and p2["state"] == "live", p2
    print("  ok  idempotent re-run: still 9/9, no error")

    # one task fails → DAG incomplete → processing
    f = call("POST", "/videos", {"video_id": "v2", "segments": 3, "renditions": ["240p", "480p", "720p"],
                                 "fail_segment": 1, "fail_rendition": "480p"})
    assert f["tasks_done"] == 8 and f["state"] == "processing", f
    print(f"  ok  injected failure: {f['tasks_done']}/9 → {f['state']}")

    # retry — only the missing task runs; the other 8 are idempotently skipped
    r = call("POST", "/videos", {"video_id": "v2", "segments": 3, "renditions": ["240p", "480p", "720p"]})
    assert r["tasks_done"] == 9 and r["state"] == "live", r
    print("  ok  task-granular retry: v2 completes → live")

    print("PASS  youtube smoke")


if __name__ == "__main__":
    main()
