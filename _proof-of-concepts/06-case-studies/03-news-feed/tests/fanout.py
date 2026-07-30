"""The decisive test: the HYBRID fan-out.

Reader R follows a normal author N and a celebrity C (>= CELEB_THRESHOLD
followers). Proves:
  - N's post is FANNED OUT on write  -> lands in R's materialized timeline
  - C's post is NOT fanned out (skipped) -> absent from R's materialized timeline
  - yet C's post appears in R's /feed via the read-time CELEBRITY MERGE
  - /feed returns both, correctly time-ordered, each tagged with its source

    python3 tests/fanout.py [BASE_URL]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _http import call, poll  # noqa: E402

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8330"

R = 500          # reader
N = 501          # normal author (few followers)
C = 502          # celebrity author
CROWD = [500, 601, 602]  # 3 followers for C -> celebrity at threshold 3


def timeline_ids(user):
    _, t = call(BASE, "GET", f"/timeline/{user}")
    return set(t["materialized_ids"])


def main():
    # R follows N (normal) and C (celebrity); give C enough followers to qualify
    call(BASE, "POST", "/follow", {"follower_id": R, "followee_id": N}, expect=201)
    for f in CROWD:
        call(BASE, "POST", "/follow", {"follower_id": f, "followee_id": C}, expect=201)

    _, cel = call(BASE, "GET", "/celebrities", expect=200)
    assert any(c["author_id"] == C for c in cel["celebrities"]), cel
    assert all(c["author_id"] != N for c in cel["celebrities"]), cel
    print(f"  ok  author {C} is a celebrity (>= {cel['threshold']} followers); {N} is normal")

    # normal author posts -> should FAN OUT to R's timeline
    _, pn = call(BASE, "POST", "/posts", {"author_id": N, "content": "from normal"}, expect=201)
    pn = pn["post_id"]
    assert poll(lambda: pn in timeline_ids(R)), f"normal post {pn} never fanned out"
    print(f"  ok  normal post {pn} was FANNED OUT into R's materialized timeline")

    # celebrity posts -> should be SKIPPED by the worker (never materialized)
    _, pc = call(BASE, "POST", "/posts", {"author_id": C, "content": "from celeb"}, expect=201)
    pc = pc["post_id"]
    # give the worker time to (not) process it, then assert it is absent
    assert poll(lambda: pc in timeline_ids(R), timeout=3.0) is None, \
        f"celebrity post {pc} was materialized but should have been skipped"
    print(f"  ok  celebrity post {pc} was SKIPPED (absent from R's materialized timeline)")

    # ...yet R's /feed shows BOTH, via the read-time merge, newest first
    _, feed = call(BASE, "GET", f"/feed?user_id={R}", expect=200)
    posts = {p["id"]: p for p in feed["posts"]}
    assert pn in posts and posts[pn]["source"] == "materialized", feed
    assert pc in posts and posts[pc]["source"] == "celebrity-merge", feed
    order = [p["id"] for p in feed["posts"]]
    assert order.index(pc) < order.index(pn), f"expected celebrity post first (newer): {order}"
    print(f"  ok  /feed merges both: {pc}=celebrity-merge before {pn}=materialized")
    print("PASS  news-feed hybrid fan-out (write-fanout for normal, read-merge for celebrity)")


if __name__ == "__main__":
    main()
