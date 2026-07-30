---
title: The Web
kind: External system
technology: Billions of external HTTP hosts
---

## 🌐 The Web

**The Web** is the external system every other box exists to survive. It is not ours, it made no promises, and it behaves accordingly: servers that are down, pages that have moved, connections that trickle one byte per second, *"pages"* that turn out to be 2 GB files, and malformed HTML that crashes parsers. Every earlier case study integrated with *one* third party under contract; this one integrates with **billions of strangers**.

**Responsibilities** (as the crawler must model them)

- Serve pages — at whatever latency, correctness, and mood each host chooses; fetch is the failure-richest stage in the pipeline precisely because this side of the arrow is uncontrolled.
- Publish the terms of engagement: **robots.txt** per host — disallowed paths and `Crawl-delay` — which the crawler fetches on first encounter and must honor.
- Push back when crawled too hard: rising latencies, 429/503 responses, and ultimately blocks — politeness at fleet scale is a reputational asset, and one abusive incident can get IP ranges blocked by CDNs fronting half the sites you need.
- Set traps, designed and accidental: self-linking page loops, calendars with a *"next month"* forever, session IDs and tracking parameters minting infinite distinct URLs for one page — the reason depth caps and aggressive URL normalization exist.

**Where it breaks the crawler.** Never in one place — that's the point. Hostility here arrives as a distribution, so the design answers with per-host gates, per-message retries, and a DLQ, rather than any assumption that a fetch will succeed.
