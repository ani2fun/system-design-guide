---
title: UrlDeduper
kind: Code
technology: Python
---

## 🧩 UrlDeduper

**UrlDeduper** is the loop-breaker. The crawler is a feedback loop — parsers discover links, links become fetches, fetches discover links — and without a membership check at the loop's entrance, the web's densely cross-linked graph would have the crawl re-crawling itself forever. Every discovered link passes through this class before it may enter the frontier.

**Responsibilities**

- `add_if_new(url) → bool`: **normalize first, then check-and-add** against the URL-seen set in one motion — returns `True` (admit to the scheduler) only for a genuinely new canonical URL.
- Normalization is the half that does the real work: lowercase scheme and host, strip fragments and default ports, resolve relative paths, canonicalize trailing slashes — so the seen-check compares canonical forms, not raw strings. `Example.com/a/` and `example.com/a#top` are one page; only normalization lets the set know it.
- Stay **exact**: the check is a point lookup against the seen store — no Bloom filter, because its false positives mean new pages silently skipped, and quiet data loss is the wrong trade for a corpus builder.

**The invariant it protects:** **normalize-then-check is the loop-breaker** — no URL enters the frontier twice under any spelling, which is the property that makes the crawl terminate.

**Where it breaks.** On what normalization can't see: session IDs and tracking parameters minting infinite *distinct-looking* URLs for one page defeat a naive canonicalizer — stripping known tracking parameters, depth caps, and per-domain budgets are the backstops. Lands in the forthcoming POC at `06-case-studies/examples/web-crawler/app/url_deduper.py`.
