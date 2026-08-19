---
title: "Capstone: Design Synapse — the Platform You're Reading"
summary: "The capstone inverts the book: design the interactive learning platform serving you this page — cache-first reads keyed by a git SHA, a sandbox that runs strangers' code without trusting a byte of it, async judging, and the honest napkin math from hundreds of users to millions."
essential: true
---

# 🎓 Capstone: Design Synapse — the Platform You're Reading

> **Prerequisites:** all of [Foundations](/synapse/system-design-from-first-principles/foundations/thinking-in-tradeoffs), [Caching](/synapse/system-design-from-first-principles/building-blocks/caching), [Design a Rate Limiter](/synapse/system-design-from-first-principles/case-studies/rate-limiter) | **You'll be able to:** run the delivery framework on a system you can actually inspect — every claim in this lesson is checkable against the live platform and its public repository; classify a workload into traffic classes and let that classification drive the whole architecture; and defend the two decisions that carry this design: content as version-addressed derived data, and untrusted code execution as a security tier, not a feature.

---

## 🧨 The problem (why this exists)

Design an **interactive learning platform**: books of technical lessons with rendered diagrams,
code the reader can edit and **run in the browser page**, and practice problems judged against a
**hidden test suite**. Authors write lessons as Markdown in a git repository; readers get a fast,
searchable reading experience anywhere in the world.

This is the fourteenth and final case study, and it plays by different rules than the other
thirteen: it is the system **serving you this page**. Every design decision below is not an
interview sketch but a decision that was actually made, shipped, and in several cases corrected in
production — and where the honest answer is *"we got this wrong first,"* the lesson says so. The
implementation is public ([ani2fun/synapse](https://github.com/ani2fun/synapse)), so unlike
YouTube's or Uber's internals, you can check the arithmetic and read the code.

**Functional requirements:**

1. Readers browse books and read lessons — prose, rendered diagrams, syntax-highlighted code.
2. Readers run code blocks (multiple languages) and see stdout/stderr, time, and memory.
3. Readers solve practice problems: edit a starter, run against visible cases, **submit** against a
   hidden suite, and get a verdict (accepted / wrong answer / first failing case revealed).
4. Authors publish by pushing Markdown to git — no CMS, no redeploy.
5. Sign-in (OIDC) gates editing and submitting; **reading never requires an account**.

*Below the line:* comments and social features; multi-tenant orgs; paid seats. An AI tutor exists
in the real system but is deliberately out of this lesson's scope.

**Non-functional requirements — quantified:**

1. Reads are fast globally: **≤ 200 ms TTFB** for lesson content from any region.
2. A code run feels interactive: **p95 ≤ 2 s** from click to output.
3. Availability priorities are explicit and unequal: reads 99.9%, runs 99.5% — **degrade runs
   before reads, never the reverse.**
4. Scale target: **1M MAU** without a redesign.
5. The one that makes this design interesting: requirement 2 means executing **arbitrary untrusted
   code, submitted by anonymous strangers, on your own hardware** — and doing so must never
   compromise the platform. Security is a first-class NFR here, not a compliance afterthought.

---

## 💡 Intuition first

The naive build is one server: render Markdown per request, and when a reader clicks Run, execute
their code with something like `exec()` in the server's own process. Say it out loud in an
interview and then dismantle it, because each half fails differently — and the two failure modes
are the two big ideas of this design.

**The read half is wasteful, not dangerous.** Rendering the same lesson on every request recomputes
an answer that changes only when an author pushes. A lesson is **derived data**: a pure function of
the content repository at a specific commit. That observation does all the heavy lifting — if
content is a function of a git SHA, then a cached copy tagged with that SHA is *correct by
construction*, and the entire read path becomes a cache-design problem. You never *"invalidate"* so
much as *advance the version*.

**The run half is dangerous, not wasteful.** `exec()` in-process hands your machine to whoever
types in the editor: read your environment, open sockets, fork-bomb the host, mine coins. The
instinct that saves the design: **the sandbox is a tier, not a library call** — a separately
deployed, separately failing, separately scaled component whose *job* is to be the only place
untrusted code ever touches, with nothing worth stealing inside it.

Split the workload along those lines and the traffic classes fall out:

| Class | Share | Character | Scaling lever |
|---|---|---|---|
| Reads (lessons, index, media, the pages themselves) | ~99% | public, cacheable, version-addressed | the CDN |
| Runs (`POST /run`) | ~1% | CPU-bound, interactive, **untrusted** | a sandbox fleet |
| Writes (submissions, account, grants) | «1% | small rows, judged asynchronously | one Postgres, barely |

Ninety-nine percent of the traffic is a caching problem. The compute bill and the threat model both
live in the 1%. Design accordingly.

---

## ⚙️ How it works

### 🧱 Core entities

- **Book / Lesson** — content, versioned by the git SHA of the content repository. Not rows in a
  database: files in a repo, with a derived read model (parsed index + per-lesson payloads).
- **User** — an OIDC identity; the platform stores no passwords, ever.
- **Run** — ephemeral: source + language + stdin in, output + status + cost out. Deliberately not
  persisted; a run is a conversation, not a record.
- **Submission** — the durable one: user, problem, source, verdict, per-case results. The only
  entity that ever grows.
- **Grant** — an allowlist row: which users may *save* submissions (an abuse valve for a platform
  where anonymous strangers can execute code).

### 🔌 The API

```
GET  /api/synapse/index                  → the catalog tree            (public, cacheable)
GET  /api/synapse/{book}/{ch}/{lesson}   → one lesson's payload        (public, cacheable)
POST /api/run          {language, source, stdin}  → 200 {output, status, time, memory}   (rate-limited)
POST /api/submissions  {problem, language, source} → 202 {id}          (auth + allowlist)
GET  /api/submissions/{id}               → {status, verdict?, firstFailure?}   (poll)
GET  /api/me                             → the verified caller         (auth)
```

Two contract decisions worth defending. **Run is synchronous** — a run is interactive feedback, and
putting a queue inside a 2-second budget adds a hop that helps the operator, not the reader;
back-pressure is a `429` with honest UX, not a queue position. **Submit is asynchronous** — judging
runs a hidden suite (N sandbox executions), so the API acknowledges with `202` + an id and the
client polls; a verdict arriving in 4 s instead of 2 s costs nothing on a path whose product
value is the verdict itself. Same sandbox underneath, opposite contracts on top — because the
*latency budgets* differ, not the technology.

### 🗺️ High-level design

Five components carry the whole system:

1. **The web tier** — this reader, server-rendered: the prose you are reading arrived as HTML in
   the response, and the interactive parts — the code editor, diagrams, the algorithm visualiser —
   hydrate as **islands**, lazy per-feature bundles that only load on pages that use them. A
   lesson costs tens of KiB of eager JavaScript, not an application bootstrap; reading works
   before (and without) any of it. This tier renders from the same public content API below —
   it holds no state and no secrets of its own.
2. **The origin API** — stateless: verifies JWTs against cached IdP keys (no sessions, no sticky
   anything), serves the content read model, fronts the sandbox for runs, owns submissions. Any
   replica can serve any request; scaling is a replica count.
3. **The content pipeline** — a git-sync sidecar pulls the content repo; the origin re-reads the
   checkout's HEAD SHA per request and exposes it as `contentVersion`. An author's `git push` *is*
   the deploy: no image build, no restart, and every cache below picks up the new version by key,
   not by purge.
4. **The sandbox** ([go-judge](https://github.com/criyle/go-judge)) — its own deployment: Linux
   namespaces + cgroups, no network, hard CPU/memory/time quotas, a process pool. The origin talks
   to it over a private interface; readers never do.
5. **Postgres + the IdP (Keycloak)** — submissions and grants in Postgres; identity delegated
   entirely to OIDC. The app verifies tokens locally (JWKS cached), so the IdP is on the login
   path only — never on the request path.

In front of everything, a CDN (Cloudflare): static assets cache as immutable, content JSON as
`max-age=60, stale-while-revalidate=600` — one minute of author-visible staleness bought the read
path's independence from origin capacity.

The whole design in C4 Container notation — pan and zoom, click any element for its doc (rendered
live from this module's `synapse-capstone.c4` model):

<iframe
  src="/c4/view/sdfp_synapse_container"
  width="100%"
  height="560"
  style="border: 1px solid var(--border, #2b2b2b); border-radius: 8px;"
  loading="lazy"
  title="Synapse — C4 Container view"
></iframe>

---

## 🤿 Deep dives

### 📦 The sandbox: running strangers' code without trusting a byte of it

The threat model is blunt: **assume the code is hostile.** Every design choice follows.

**Isolation is layered, and each layer assumes the previous one failed.** Inside: go-judge runs
each program in fresh Linux namespaces (PID, mount, network, IPC) under cgroup quotas — a hard CPU
ceiling, a memory ceiling, a wall-clock timeout, an output cap (a `yes`-loop is an attack on your
disk), and **no network interface at all**, which kills exfiltration, coin miners, and "download
the real payload" in one stroke. Around it: the sandbox is its own pod on a tainted node pool with
`NetworkPolicy` egress-deny, so even a full container escape lands somewhere with nothing to read
and nowhere to call. At the fleet stage, the outer wall is upgraded to gVisor/Firecracker-class
isolation — the *ratchet rule*: every stage that adds sandbox capacity ships matching isolation
hardening in the same step.

**Blast radius is a budget you spend deliberately.** The platform's own audit found the app pod
holding an IdP **master-realm** credential for account deletion — meaning a compromised pod could
administer *every* realm. The fix (shipped, not hypothetical) was a service-account client scoped
to exactly one permission on exactly one realm: post-compromise, an attacker can at worst delete
users in that realm — bad, bounded, recoverable. Generalize it: for each credential a component
holds, name what an attacker does with it; if the sentence contains *"everything,"* re-scope.

**Capacity math, so the fleet is a number and not a vibe.** At 1M MAU: ~10k concurrent peak, of
whom perhaps 2k are actively coding, one run per ~5 min each → **~7 runs/s peak**, at ~1
CPU-second per run → 10–20 dedicated cores with 5× burst headroom. Autoscale on in-flight runs,
keep **warm pools per language** (cold interpreter start is the p95's enemy), and cap per-user
concurrency so one griefer can't occupy the fleet. The run path is the only line in the budget
that grows superlinearly with engagement — it gets its own dashboard.

### 📄 Content as derived data: the read path that never needed a database

Content lives in git; the running system holds a **checkout**, not a copy in Postgres. The origin
re-reads the checkout's HEAD SHA on each request and stamps every content response with it. Three
consequences do all the work:

1. **Publishing is `git push`.** The sidecar pulls, the SHA advances, and every layer that keyed on
   the old SHA is simply *out of date by key* — no purge fan-out, no *"did the cache clear?"* on-call
   page. (Proven mechanically in this deployment: re-pointing the sidecar at a scratch clone
   re-indexed the live site with zero redeploys.)
2. **Caching has a correctness proof.** A cached lesson tagged with SHA `abc123` is the right
   answer for as long as the version *is* `abc123` — TTLs become a freshness dial (how long until
   readers see a new push), not a correctness gamble. Today the dial reads 60 s + SWR; the
   million-user version makes URLs SHA-addressed and the objects immutable (`max-age=1y`), at which
   point the origin serves each lesson roughly **once per push per region** and reads become
   origin-less. That's the same IDs-then-hydrate energy as the [news
   feed](/synapse/system-design-from-first-principles/case-studies/news-feed)'s materialized
   timelines — precompute the derived form, serve it from the cheapest tier that can hold it.
3. **Consistency is trivially cheap.** Content has **one writer** (git) and infinitely many
   readers; there is no multi-writer story, no conflict resolution, no replication protocol to
   design. The hardest consistency question is *"may an author see their push within a minute?"* —
   and the NFR says yes, 60 s is fine. Compare what the other case studies paid for multi-writer
   semantics, and appreciate a workload that lets you *not* buy it.

### ⚖️ Judging: the write path that stays boring on purpose

Submit → `202 {id}` → the judge runs the hidden suite in the sandbox, case by case → the row
advances `pending → completed` with a verdict → the client's poll picks it up. Design points worth
naming in an interview:

- **The hidden suite never leaves the server.** It isn't in the lesson payload, any client bundle, or
  any response — a wrong-answer verdict reveals *one* failing case as a teaching aid, and that
  revelation is a deliberate, server-side choice. The moment hidden tests ride a client payload
  *"for speed,"* they're public.
- **Polling, not WebSockets.** A verdict lands in single-digit seconds and the poll interval is
  ~1 s; a persistent connection buys nothing but state on the server (and this origin is proudly
  stateless). Polling an async job at this cadence is the honest default — see the same shape in
  every accepted answer since.
- **The failure story is derived-data thinking again.** If the judge dies mid-suite, the row is
  still `pending`; a reaper re-enqueues stale pending rows and judging re-runs from the top —
  verdict computation is **idempotent** (same source, same suite, same verdict), so at-least-once
  execution converges. No exactly-once machinery needed, because the *effect* is naturally
  idempotent. Write volume at target scale (<1/s) means one partitioned Postgres primary carries
  this for years; the sharding conversation has a trigger (*"write volume breaks the napkin math"*),
  and until the trigger fires, it doesn't happen.

### 🪪 Identity off the hot path

Sign-in is a full OIDC dance (authorization code + PKCE) against Keycloak — but that happens once
per session. Per *request*, the origin verifies the JWT's signature against the IdP's public keys,
cached; **no identity network call ever rides a read, run, or submit**. The IdP can be sized for
login bursts and even fall over without taking reading down (requirement: reads never require an
account — an availability decision disguised as a product decision). One correction from this
system's own audit is worth carrying to interviews: usernames compare **canonicalized** (lowercase)
everywhere, or `Alice` and `alice` are silently two people — the class of bug that only surfaces as
a confusing 403 six weeks later.

---

## ⚖️ Trade-offs

| Decision | Chosen | The price, paid knowingly |
|---|---|---|
| Run contract | synchronous, rate-limited | a 429 under burst instead of a queue — protects interactivity, sheds load honestly |
| Submit contract | async 202 + poll | client complexity (poll loop) for a stateless origin and a spike-proof write path |
| Content store | git + derived read model | ~60 s publish latency (until SHA-addressed URLs); no CMS ergonomics |
| Deployment unit | modular monolith (hexagonal contexts) | one blast radius per deploy — but extraction seams are package boundaries, exercised only when a context's scaling diverges (the sandbox path first) |
| Identity | delegated OIDC, local JWT verification | you own zero passwords and no auth hot path; you inherit the IdP's availability on *login* only |
| Database | one Postgres (partitioned later) | a deliberate refusal of distributed-database complexity that the write volume never justified |

---

## 🔢 Numbers that matter

The napkin math the architecture is sized against (derive these live in an interview — they're the
argument):

- 1M MAU → ~100k DAU → **~10k concurrent peak**.
- Reads: a lesson per ~2 min per concurrent reader ≈ **80 loads/s peak**; ≥95% CDN-served → the
  origin sees **single digits/s**. A read replica of *anything* would be decoration.
- Runs: **~7/s peak** × ~1 CPU-second → **10–20 sandbox cores** + 5× burst headroom.
- Submissions: **<1/s**, ~2 KB/row → ~400 MB/day worst case; years on one partitioned primary.
- Auth: verification is local crypto (~µs); the IdP sees only logins — **tens/s** even at peak.

The asymmetry is the lesson: five orders of magnitude between read traffic and write traffic, and
the only component whose cost grows superlinearly with engagement is the sandbox fleet.

---

## 🏭 In production

This design runs at [synapse.kakde.eu](https://synapse.kakde.eu) — currently Stage 0 of its own
scaling plan: one k3s node, one origin pod, GitOps end-to-end (push → CI → registry → promote →
ArgoCD), Cloudflare at the edge. Field notes from operating it, because production always grades
the homework:

- **The CSP ate the diagrams.** A security-hardening pass shipped a strict `Content-Security-Policy`
  validated against sign-in — and broke fonts, the code editor's worker, and (a second incident)
  every D2 diagram: the diagram library spawns a `blob:` worker, which *inherits the page CSP*, and
  evaluates its embedded layout engine via `new Function` — needing `'unsafe-eval'`, which
  `'wasm-unsafe-eval'` does not cover. Two morals: validate a CSP against your *heaviest* pages,
  and dev environments that serve without prod headers will hide exactly this class of breakage.
- **Non-root broke the launcher.** The pod was hardened to run as an unprivileged UID — and
  crash-looped on rollout because the staged binary was `0744`: executable by owner, and the owner
  was no longer the runtime UID. Least-privilege changes fail at *file permissions*, not concepts.
- **The cheapest wins were cache headers.** Static assets as immutable + content JSON at
  `max-age=60, stale-while-revalidate=600` moved the read path to the edge for the cost of two
  headers — the highest leverage-per-line change in the deployment.
- **The read path got rebuilt once, and the measurement drove it.** The first reader shipped as a
  client-rendered app: correct, complete — and content-readable at ~7 s on a mid-range phone,
  because a multi-hundred-KiB bundle stood between the reader and 2 KiB of prose. The rebuild
  inverted it to server-rendered pages with lazy islands; per-page eager JS now measures in the
  tens of KiB, and CI enforces a **per-page** budget so a regression is a failed build, not a slow
  reader. The moral is the one this book keeps repeating: the workload table said reads are 99%
  of traffic — the architecture of the read path had to answer to that number, and eventually did.

The full growth ladder — triggers, stages, and what deliberately never changes — is documented as
the repo's [scaling plan](https://github.com/ani2fun/synapse/blob/main/docs/architecture/scaling-plan.md); this
lesson is its narrative form.

---

## 🪤 Pitfalls & interview traps

**Treating code execution as a feature instead of a threat.** The interviewer who asks "and how do
you run the code?" is not asking about subprocess APIs. The graded answer names isolation layers
(namespaces/cgroups → no network → node-level containment → what a stolen credential reaches) and
*assumes escape* when sizing blast radius. `docker run` alone is a mid-level answer; containers
share the host kernel, and the question is what happens when that's not enough.

**Queueing the interactive path.** Putting Run behind a queue *"for scalability"* trades the
product's feel for operator comfort inside a 2-second budget. Back-pressure belongs at the edge
(429 + UX) on interactive paths; queues belong where latency is already forgiven (judging).

**Purging caches instead of versioning them.** If your content story includes "and then we
invalidate the CDN," you've signed up for purge fan-out, race windows, and stale-forever edge
cases. Version-addressed data makes staleness a *dial* and correctness a *key* — say
*"content-addressed, immutable, TTL on the pointer, not the data"* and watch the interview change
tone.

**Shipping the hidden tests.** Any design where the client judges — "run the suite locally for
speed" — has published its answer key. Judging is a server-side trust boundary, same reasoning as
price calculations in checkout flows.

**The leveling bar.** Mid-level: clean API split (sync run / async submit), a sandbox that exists,
content cached somehow. Senior: the traffic-class table drives the design; isolation is layered
with blast radius named; caching is version-addressed with the consistency argument. Staff+: the
napkin math produces the fleet size, the degradation order is a written product decision, and the
monolith/extraction call is defended by measurement triggers, not fashion.

---

## ✅ Check yourself

```quiz
{"prompt": "Synapse serves lesson JSON with a 60-second TTL. An author pushes a fix. What makes the cached copies safe to keep serving until they expire?", "options": ["The CDN purges them automatically on push", "Every cached response is keyed to the content version (a git SHA) it was derived from — it stays a correct answer for that version", "Postgres replication propagates the change to the edge", "They are not safe — a 60s TTL always risks serving wrong data"], "answer": "Every cached response is keyed to the content version (a git SHA) it was derived from — it stays a correct answer for that version"}
```

```quiz
{"prompt": "Why is POST /run synchronous while POST /submissions returns 202 + poll, when both execute code in the same sandbox?", "options": ["Runs are cheaper to execute than submissions", "Their latency budgets differ: a run is interactive feedback inside ~2s, a verdict is a result the reader will wait a few seconds for", "Submissions require authentication, which forces async processing", "The sandbox can only execute one submission at a time"], "answer": "Their latency budgets differ: a run is interactive feedback inside ~2s, a verdict is a result the reader will wait a few seconds for"}
```

```quiz
{"prompt": "The judge crashes halfway through a submission's hidden suite. What makes 'just re-run it from the top' a complete recovery story?", "options": ["The queue guarantees exactly-once delivery", "Each case's result was checkpointed, so it resumes mid-suite", "Verdict computation is idempotent — same source, same suite, same verdict — so at-least-once re-execution converges on the right answer", "Submissions are lost on crash and the user must resubmit"], "answer": "Verdict computation is idempotent — same source, same suite, same verdict — so at-least-once re-execution converges on the right answer"}
```

```quiz
{"prompt": "At 1M MAU the napkin math says ~80 lesson loads/s and ~7 runs/s at peak. Where does the engineering effort go, and why?", "options": ["Reads — 80/s is more than 7/s, so the read path needs sharding first", "Runs — reads are ≥95% CDN-served (origin sees single digits/s), while the sandbox fleet is real CPU, real cost, and a real threat model", "Both equally — traffic classes should be scaled together", "Neither — Postgres is the bottleneck at this scale"], "answer": "Runs — reads are ≥95% CDN-served (origin sees single digits/s), while the sandbox fleet is real CPU, real cost, and a real threat model"}
```

<details>
<summary><strong>Q:</strong> A security review assumes an attacker fully escapes the code sandbox. Walk the containment story outward and name the design rule that limits the damage.</summary>

**A:** Outward by layers: the escaped process is in a pod with a `NetworkPolicy` denying egress —
nothing to call home to; the pod runs on a tainted, dedicated node pool — no co-tenant workloads to
attack; the pod's service account and mounted credentials are the real question, and the design
rule is **least-privilege by named blast radius**: for every credential a component holds, state
what an attacker does with it, and re-scope until the sentence stops containing "everything." The
platform's own audit applied exactly this — replacing an IdP master-realm credential with a
service-account client scoped to one permission on one realm, converting "administer every realm"
into "delete users in this realm." The senior signal is designing for *when* the sandbox fails,
not arguing it won't.

</details>

---

## 🔬 PoC — Proof of concepts

This capstone is unusual: the proof of concept is not a toy in `_proof-of-concepts/` but the *entire
platform you are reading this on*. Every repository below is public, and there is a whole book that
designs them from first principles.

- [ani2fun/synapse](https://github.com/ani2fun/synapse) — the application: the Rust axum server, the
  Astro web tier, the visualisation engine and the sandbox/judging/identity contexts this case study
  discusses.
- [ani2fun/system-design-guide](https://github.com/ani2fun/system-design-guide) — this book, and the
  [`_proof-of-concepts/`](https://github.com/ani2fun/system-design-guide/tree/main/_proof-of-concepts)
  directory that backs every *other* case study above.
- [ani2fun/synapse-content](https://github.com/ani2fun/synapse-content) — the content spine: the blog,
  the category declarations and the one shared C4 specification every diagram in this book depends on.
  The platform reads its library from several repositories at once and merges them into a single
  catalog, which is how this book is maintained on its own without its URL moving.
- [Synapse App From Scratch](/synapse/synapse-app-from-scratch/index) — the companion book that
  documents this exact system in depth: architecture, the ten bounded contexts, the measured numbers,
  and the content pipeline that turned this lesson into a page.

---

## 📚 Sources

- [ani2fun/synapse](https://github.com/ani2fun/synapse) — the implementation this lesson describes:
  the architecture decision records (`docs/adr/`), the architecture docs (`docs/architecture/`), and
  the [scaling plan](https://github.com/ani2fun/synapse/blob/main/docs/architecture/scaling-plan.md) whose
  napkin math this lesson shares.
- [go-judge](https://github.com/criyle/go-judge) — the sandbox: namespace/cgroup isolation, process
  pooling, and the quota model the run path builds on.
- [Design a News Feed](/synapse/system-design-from-first-principles/case-studies/news-feed) — the
  derived-data and materialized-view reasoning this lesson applies to content
  (per DDIA2's home-timeline case study).
- Production incidents referenced (CSP vs the diagram worker, the non-root launcher, cache
  headers) are from this deployment's own build log — documented forward in the repo's build book.
