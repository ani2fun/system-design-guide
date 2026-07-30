---
title: Operator
kind: Actor
technology: Human · crawl operations
---

## 👤 Operator

The **Operator** is the only human in a system whose *"users"* are ten billion web pages. Unlike the rider or the uploader of earlier case studies, they don't sit inside the request path — they set the crawl's *constitution* and then watch it govern itself: seed URLs (usually given — major directories, news sites, popular domains), the hard **5-day time budget**, and the politeness policy (the 1 request/second/domain norm, honoring robots.txt).

**Responsibilities**

- Seed the frontier and declare *"done"*: a one-shot corpus crawl has a bounded job with an end, not an SLA that runs forever.
- Set policy the machines enforce — the time budget that fixes the ~23,000 pages/second fleet rate, and the politeness rules that cap any single host at one polite stream.
- Watch the dashboards that say whether the loop is healthy: **fetch success rate** (a fleet-wide dip is *our* problem — DNS, egress, IP reputation; a domain-scoped dip is *theirs* — skip it), **DLQ depth** (how much web we're writing off), **frontier depth and its growth derivative**, crawl rate against the budget line, and the **duplicate ratio** (a spike usually means a trap or a normalization bug, not a suddenly repetitive internet).
- Triage the dead-letter queue — the DLQ exists to be *monitored*, and declaring a site offline and unscrapable is a human judgment.

**Where it grows.** The moment the corpus must stay fresh, the operator's one-shot job becomes a scheduling policy — recrawl by last-crawl time and importance — and this actor starts owning a continuous system instead of a deadline.
