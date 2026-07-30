---
title: Job owner
kind: Actor
technology: Human · API client
---

## 👤 Job owner

The **Job owner** is anyone with work that must happen later — a one-off *"send this report at 10:00"* or a recurring *"bill every customer daily."* Their contract with the system is deceptively short: run it **within seconds of due, never miss it, never run it twice**. Every container downstream exists to keep one clause of that sentence true while machines crash underneath it.

**Responsibilities**

- Register jobs via `POST /jobs` — a task id, parameters, and a schedule (one-shot timestamp or cron expression), expressed in **UTC**: the server's NTP-disciplined clocks decide when 10:00 is, never the owner's device clock, which cannot be trusted.
- Check outcomes via the status API — served by the `user_id` GSI on Executions, so *"show me my jobs"* never scans the time-bucketed base table.
- Declare (ideally) a **misfire policy** per job — run late or skip when the system couldn't fire on time. Billing must run late; a cache warm should skip. It's a product decision only the owner can make.

**Where it breaks.** The owner is also the load pattern: humans write `0 * * * *`, so demand spikes violently at the top of every minute and hour — the thundering herd lives in the *schedules*, not the infrastructure. And a multi-tenant scheduler is one `while(true) { schedule(now) }` away from a self-inflicted DoS, which is why admission quotas sit at the gateway, not deeper in.
