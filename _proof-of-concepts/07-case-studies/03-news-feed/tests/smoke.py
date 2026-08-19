"""End-to-end smoke: follow -> post -> the fan-out worker materializes the feed.

    python3 tests/smoke.py [BASE_URL]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _http import call, poll  # noqa: E402

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8330"


def main():
    # user 100 follows author 200
    call(BASE, "POST", "/follow", {"follower_id": 100, "followee_id": 200}, expect=201)

    _, post = call(BASE, "POST", "/posts", {"author_id": 200, "content": "smoke post"}, expect=201)
    pid = post["post_id"]
    print(f"  ok  author 200 posted -> id {pid}")

    # the worker fans out asynchronously; poll the follower's raw timeline
    def in_timeline():
        _, t = call(BASE, "GET", "/timeline/100")
        return pid in t["materialized_ids"]

    assert poll(in_timeline), f"post {pid} never fanned out to follower 100's timeline"
    print("  ok  worker materialized the post into follower 100's timeline")

    _, feed = call(BASE, "GET", "/feed?user_id=100", expect=200)
    assert any(p["id"] == pid for p in feed["posts"]), feed
    print(f"  ok  GET /feed returns the post ({len(feed['posts'])} item(s))")

    _, stats = call(BASE, "GET", "/stats", expect=200)
    assert stats["posts"] >= 1 and stats["follows"] >= 1
    print(f"  ok  /stats: posts={stats['posts']} follows={stats['follows']}")
    print("PASS  news-feed smoke")


if __name__ == "__main__":
    main()
