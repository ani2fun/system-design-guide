---
title: PolitenessGate
kind: Code
technology: Python
---

## 🧩 PolitenessGate

**PolitenessGate** encodes the crawl's manners as code: the published rules a site declares, and the rate discipline the fleet imposes on itself. Politeness is **per-host** by nature — robots.txt is a per-host document, crawl-delay is a per-host promise, and a thousand fetchers must collectively look like *one* polite visitor to each site — so the gate keys everything by host, never globally, never per-fetcher.

**Responsibilities**

- `robots(host) → Rules`: on first encounter with a host, fetch and parse its robots.txt (this design assumes a one-time download; real crawlers refresh periodically) and remember the disallowed paths and `Crawl-delay`.
- `allow(host) → bool`: the composite verdict — path not disallowed, crawl-delay elapsed since the host's last fetch, and the per-host rate window (the ~1 req/s norm) open. Enforced **centrally**, because N fetchers checking independently is how N simultaneous requests hit one origin.
- Refuse without blocking: a *"no"* delays that host's lane only — the scheduler steps past it and everyone else's flow continues.

**The invariant it protects:** **a URL leaves the frontier only when its host's gate opens.** No path around it — fetchers never rate-limit themselves, they trust the gate.

**Where it breaks.** On the stampede: many fetchers waiting on one host's window will all retry the instant it resets, one wins, the rest re-stampede in lockstep — the fix is **jitter**, a small random delay per fetcher. Lands in the forthcoming POC at `06-case-studies/examples/web-crawler/app/politeness_gate.py`.
