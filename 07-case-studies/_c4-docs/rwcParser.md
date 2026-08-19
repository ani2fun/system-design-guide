---
title: Parser / extractor
kind: Worker
technology: Python workers
---

## 🛠️ Parser / extractor

The **Parser / extractor** turns raw HTML into the two things the system actually wants: the **text corpus** and the **next generation of URLs**. It is a separate stage from fetching on purpose — the stage boundary means a parser crash never costs a re-fetch, and when the ML team later wants alt-text included, you rerun this cheap stage over stored HTML without touching the web again.

**Responsibilities**

- Read raw HTML back from the page store (the queue carries pointers, never 2 MB payloads), extract the text, and write it to the page store — then ack its message, same claim/ack contract as the fetchers.
- **Content-hash dedup**: hash the fetched page's content and check it against the seen stores. Different URLs routinely serve identical bytes — `example.com` vs `www.example.com`, mirrors, syndicated articles — and URL-level dedup cannot see this; *only the bytes can*. A hash match means skip storage and just harvest the links. For an LLM corpus this pays twice, since near-duplicates get scrubbed in data prep anyway.
- Close the loop: **normalize** every discovered link, seen-check it, and enqueue only the unseen into the frontier — this feedback edge is what makes the crawler a self-sustaining loop rather than a batch job over seeds.

**Where it breaks.** Poison pages — malformed HTML that crashes the worker on every retry — would redeliver forever; capped retries and the DLQ turn them into a triage list instead. And the fleet needs no capacity math: autoscale on queue depth and let it track the fetchers' actual output.
