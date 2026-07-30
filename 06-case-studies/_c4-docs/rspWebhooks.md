---
title: Webhook receiver
kind: Service
technology: Python · FastAPI
---

## ⚙️ Webhook receiver

The **Webhook receiver** is where the PSP's truth arrives — late, asynchronously, and more than once. The card networks are asynchronous partners: a charge we timed out on may still be winding through authorization, and its outcome reaches us not in the original response but in a signed callback minutes later. This container is the reason `pending_verification` can be an honest state rather than a lie: something downstream is guaranteed to resolve it.

**Responsibilities**

- **Verify signatures** on every inbound callback — the payload claims money moved; the signature is what makes that claim authenticable rather than spoofable.
- **Flip pending intents**: the callback — not our optimistic bookkeeping at request time — is what moves `pending_verification` to `authorized` or `failed`, and `captured` to `settled`.
- **Append settlement postings** to the ledger as funds actually move — new entries, never edits, per the ledger's only rule.
- Stay **idempotent**: the networks deliver at-least-once, so callbacks re-arrive; processing an event twice must have the same effect as once — deep dive 1's lesson recursing inward, deduplicating by event ID exactly as we ask merchants to do with *our* outbound webhooks.

The design stance it embodies is the timeliness/integrity split: staleness is an annoyance that resolves itself; corruption is a catastrophe that doesn't. Merchants tolerate a `processing` badge; no one tolerates a wrong charge.

**Where it breaks.** A lost callback is silent — nothing errors, an intent just stays pending and the ledgers quietly diverge. That gap is precisely the reconciliation job's beat: this container handles the truth that arrives; reconciliation hunts the truth that didn't.
