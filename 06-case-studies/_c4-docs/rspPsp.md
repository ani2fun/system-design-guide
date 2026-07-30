---
title: PSP / card rails
kind: External system
technology: External — card networks, issuing & acquiring banks
---

## 🌐 PSP / card rails

The **PSP / card rails** box is everything we do not control: the card networks and the banks behind them. The design stance is to treat them as **asynchronous partners, not synchronous services** — they have their own queues, batch windows, and retry logic, so a charge we timed out on may still be winding through authorization, and one that succeeded instantly may have lost its response on the way back.

**Responsibilities** (as seen from our side)

- Answer `authorize` and `capture` calls — usually in seconds, sometimes not at all within our timeout.
- Deliver **signed asynchronous callbacks** as charges progress through settlement, chargebacks, and reversals — the truth, arriving late, and re-delivered, so our webhook receiver must be idempotent.
- Move actual money at **settlement**, a batch process days after capture — which is why the state machine keeps `settled` separate from `captured`.
- Publish periodic **settlement files**: comprehensive, strictly formatted records of everything processed in a window — the definitive account the reconciliation job diffs our ledger against.

The whole architecture bends around this boundary: pending states are first-class because this system's truth arrives late, and we spend timeliness (day-late settlement, batch reconciliation) to buy absolute integrity.

**Where it breaks.** It doesn't have to break to hurt us — a single lost callback or a settlement that never lands silently diverges our ledger from theirs. That is why reconciliation is a standing job, not an emergency: trust, but verify.
