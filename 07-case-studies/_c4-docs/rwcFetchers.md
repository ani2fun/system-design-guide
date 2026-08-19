---
title: Fetcher fleet
kind: Worker
technology: Python workers
---

## 🛠️ Fetcher fleet

The **Fetcher fleet** is the muscle of the crawl — and deliberately nothing more. Each worker is **stateless**: it claims a URL, resolves DNS, performs the rate-limited HTTP GET against the open web, checkpoints the raw HTML into the page store, and hands a pointer onward for parsing. Everything a fetcher knows lives in the message it holds and the stores it writes; kill one mid-page and the system loses nothing.

**Responsibilities**

- **Claim, don't take**: receiving a URL starts a **visibility timeout** — the message is hidden from other workers, not deleted. The fetcher **acks (deletes) only after the HTML is durably stored**. A fetcher that dies mid-fetch simply never acks; the message reappears and another worker picks it up. Crash recovery is nobody's job — it's the queue's default behavior.
- Fetch politely: every request has already passed the frontier's per-host gate, so a thousand fetchers collectively behave like one polite visitor per site.
- Checkpoint before handing off: raw HTML to the page store (idempotent — keyed by normalized URL, a duplicate write overwrites itself), then enqueue for parsing.
- Give up gracefully: repeated failures ride exponential backoff (30 s → 2 m → 5 m → up to 15 m) and after 5 attempts drain to the DLQ.

**Where it breaks.** The claim/ack contract yields **at-least-once**, not exactly-once: store the HTML, die before deleting the message, and the URL is fetched twice. That's the accepted price — a duplicate fetch wastes bandwidth, and idempotent writes ensure it never corrupts the corpus. The fleet's real ceiling is bandwidth, not CPU: about four network-optimized machines cover the whole 5-day crawl.
