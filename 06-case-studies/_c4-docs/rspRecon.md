---
title: Reconciliation job
kind: Batch job
technology: Batch job
---

## 🏗️ Reconciliation job

The **Reconciliation job** is *"trust, but verify"* made operational. However good the flows, our ledger and the networks' records *will* diverge — a lost callback, a bug in either system, a settlement that never lands. At sufficient scale even very unlikely corruptions happen, so integrity must be **checked, not assumed**; auditability is prized in finance precisely because everyone knows mistakes happen and must be detectable and fixable. This is a standing job, not an emergency.

**Responsibilities**

- Consume attempt and timeout events off the CDC stream, and **proactively query the network** for anything stuck in `pending_verification` — resolving the *"I don't know yet"* states the webhooks never resolved.
- Systematically **diff each settlement file** — the networks' comprehensive, strictly formatted record of everything they processed in a window — against our ledger. Matches confirm integrity; mismatches open cases.
- Surface every break instead of absorbing it; each fix is an appended correcting entry, never an edit.

The checking is deliberately **end-to-end**: verify the whole derived pipeline against the counterparty's definitive account and you have implicitly verified every disk, network hop, and service along it. And the event-sourced core is what makes the audit *possible* — replaying the same log through the same deterministic code reproduces the same state, so a ledger system can *prove* what right is, where a mutable-balance system can only be told it's wrong.

**Where it breaks.** It trades timeliness for integrity by construction: settlement files arrive in daily batches, so a divergence can sit undetected for hours. That is the accepted cost — money may be slow, never wrong.
