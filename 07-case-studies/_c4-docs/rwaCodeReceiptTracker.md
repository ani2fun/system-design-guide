---
title: ReceiptTracker
kind: Code
technology: Python
---

## 🧩 ReceiptTracker

**ReceiptTracker** drives the sent → delivered → read ladder — and its whole design insight is that it contains almost no machinery of its own. **A receipt is just a tiny message flowing the other way:** to tell Alice her message was delivered, publish a `receiptUpdate` to *Alice's* channel and let the same `MessageRouter` paths carry it. No second delivery system, no separate receipt pipeline.

**Responsibilities**

- `on_sent(message_id)`: fire the single tick when the Message + Inbox transaction commits — *"sent"* means *the system can no longer lose it*, not *"the recipient has it"*.
- `on_delivered(message_id)`: fire the double tick when the recipient client's **application-level ack** arrives — only that, because TCP buffering the bytes proves nothing about the app having them.
- `on_read(message_id)`: the same machinery one level up — the client emits a read event when the message renders, and the same reverse-message pipe carries a different verb.

**The invariant it maintains:** every tick is pinned to a **machine-checkable event** — a transaction commit, an application ack, a render event. No receipt is ever inferred from a lower layer's success.

**Where it grows.** The fan-out runs backwards: a message to N group participants generates on the order of N delivered and N read receipts converging on the sender — real messengers batch or throttle that fan-in. In a group, *"delivered"* is a *set* of per-participant, per-device facts aggregated in the sender's UI, not one boolean. Lands in the forthcoming POC at `06-case-studies/examples/whatsapp/app/receipt_tracker.py`.
