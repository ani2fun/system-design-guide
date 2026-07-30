---
title: API gateway
kind: API gateway
technology: Gateway
---

## 🚪 API gateway

The **API gateway** fronts a deliberately small surface — three endpoints — and routes them to the Job service. In a design whose hard problems live in the tick and the workers, the gateway's job is to keep the *entry* boring: terminate clients, route, and enforce admission policy so nothing pathological reaches the scheduling core.

**Responsibilities**

- Route `POST /jobs` (register a definition), `GET /jobs?status=&cursor=` (the caller's executions, newest first), and `GET /jobs/{job_id}` (definition plus recent executions) to the Job service.
- Enforce **tenant quotas at admission** — cap jobs-created and executions-in-flight per tenant. A multi-tenant scheduler is one runaway loop away from a self-inflicted DoS, and the cheapest place to stop that is before the write path, with the same machinery as a standalone rate limiter.
- Keep schedule input honest: schedules arrive in UTC, and nothing downstream ever consults a client clock.

**Where it grows.** The gateway is stateless and scales horizontally ahead of the Job service; nothing here is a coordination point. The subtlety worth naming in an interview is what the gateway does *not* do: it cannot smooth the top-of-the-minute herd, because that spike is encoded in the cron expressions themselves — humans write `0 * * * *`. Splaying due times belongs where executions are materialized and dispatched, not at the front door; the gateway only ensures the herd that arrives is a *legitimate* one.
