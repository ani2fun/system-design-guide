---
title: Web Crawler
kind: System
technology: Queue-pipelined fetch/parse loop
---

## 🏢 Web Crawler

The **Web Crawler** takes a handful of seed URLs and turns them into a text corpus of **10 billion pages (~20 PB of raw HTML) inside a 5-day budget** — roughly 23,000 pages/second sustained — without ever hammering a single host. Those two goals pull opposite directions, and the whole architecture is the reconciliation: per-domain throughput is *capped* at ~1 request/second by politeness, so fleet speed can only come from **breadth** — thousands of domains crawled concurrently, one polite stream each.

**Responsibilities**

- Schedule: the **URL frontier** decides which URL a fetcher gets next — allowed by robots.txt and rate limits, worth crawling now — which makes it the system's brain, not its buffer.
- Fetch durably: stateless **fetchers** claim work under a visibility timeout and ack only after the HTML is safe in the **page store** — a crashed worker's message simply reappears for someone else.
- Extract and close the loop: **parsers** pull text and links from stored pages; discovered URLs pass through dedup back into the frontier.
- Remember: the **seen stores** answer *"have we met this URL / this content before?"* — the loop-breaker that keeps the crawl from re-crawling the web into itself.
- Fail sideways: transient errors retry with backoff; poison pages drain to the **DLQ** instead of blocking the pipeline.

**Where it breaks.** Delivery is at-least-once, never exactly-once — the design absorbs duplicates through idempotence (content-addressed writes, no-op status updates, the dedup check) so a double fetch costs bandwidth, never corpus corruption. The punchline of the numbers: four large machines suffice — this is a *bandwidth* problem, not a compute problem.
