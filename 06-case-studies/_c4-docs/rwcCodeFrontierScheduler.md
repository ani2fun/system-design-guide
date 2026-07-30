---
title: FrontierScheduler
kind: Code
technology: Python
---

## 🧩 FrontierScheduler

**FrontierScheduler** is the answer to the question that makes the frontier more than a queue: *which URL does this fetcher get next?* A FIFO would answer *"whatever arrived first"* — and since parsers enqueue a page's links together, discovery order clusters same-domain URLs, which is exactly the order politeness forbids consuming.

**Responsibilities**

- `next_url(fetcher) → URL`: hand the calling fetcher its next unit of work — **rotating across domains** rather than draining them in arrival order, so the fleet's throughput comes from breadth (thousands of hosts, one polite stream each) instead of futile depth on a rate-capped host.
- Ask **PolitenessGate** before releasing anything — *"may I fetch this host?"* — and, when a host's gate is closed, step past it: a blocked domain delays only its own lane, never the fleet.
- Accept new work only from **UrlDeduper** (*"fresh URLs only"*) — the scheduler never sees a URL the crawl already knows.

**The invariant it protects:** **no host starves the budget, and no fetcher hammers one site.** A million-page domain at 1 req/s needs ~11.6 days by itself — the scheduler's rotation is what keeps that arithmetic from becoming the crawl's fate, and its gate check is what keeps a thousand independent fetchers from dog-piling one origin.

**Where it breaks.** If rotation degrades to FIFO — a bug, or one domain flooding discovery — the frontier's head fills with URLs the gate keeps refusing, and workers spin on *"not yet"* instead of fetching. Lands in the forthcoming POC at `06-case-studies/examples/web-crawler/app/frontier_scheduler.py`.
