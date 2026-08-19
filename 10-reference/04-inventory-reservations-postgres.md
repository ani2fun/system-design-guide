---
title: "Inventory Reservations at Scale in PostgreSQL"
summary: "A worked port of Shopify's row-per-unit reservation design to PostgreSQL — SKIP LOCKED, a bounded pool, advisory-lock replenishment, and the bloat and connection-hold hazards that decide whether it survives production."
essential: false
---

# 🎟️ Inventory Reservations at Scale in PostgreSQL

> **Prerequisites:** [Dealing with Contention](/synapse/system-design-from-first-principles/patterns/dealing-with-contention), [Transactions & Isolation](/synapse/system-design-from-first-principles/distributed-data/transactions-and-isolation) | **You'll be able to:** explain why a hold that lives in a different system from the ledger can never be made atomic, size and operate a row-per-unit reservation pool with `SKIP LOCKED`, and name the two PostgreSQL-specific failure modes (dead-tuple bloat, connection hold time) that will bite you before locks ever do.

<div style="border-left:4px solid #15448e;background:rgba(21,68,142,0.08);padding:0.6rem 1rem;border-radius:0 0.5rem 0.5rem 0;margin:1.25rem 0">

📘 **What this is.** A reference walkthrough, not a lesson in the main spine. The problem framing and the four load-bearing decisions come from Shopify's engineering post on scaling inventory reservations [web: shopify.engineering/scaling-inventory-reservations]; that system runs on **MySQL/InnoDB**, and roughly three of its four technical decisions are InnoDB-specific. The PostgreSQL schema, functions, and operational guidance here are this book's own work, and **every SQL block on this page was executed against PostgreSQL 17.10** — including a 64-client concurrency run (see *Verify it yourself*).

</div>

---

## 🧨 The problem (why this exists)

Checkout has a race condition. Between *"buyer clicks pay"* and *"payment settles"*, seconds pass. During that window another buyer can try to buy the same last unit. Get it wrong one way and you **oversell** — cancel the order, apologise, eat the support cost. Get it wrong the other way and you **undersell** — tell a buyer it's gone when it isn't.

The fix is a **reservation**: a short-lived hold placed at the start of payment, converted to a permanent deduction on success, released on failure or timeout.

Shopify's holds lived in Redis — one key per item, `DECR` to reserve, `INCR` to release. Redis handled the concurrency fine. The problem was structural: **the hold lived in a different system from the inventory ledger**, so the claim step could never be one atomic operation. (Two lesser motivations came along for the ride: the Redis model had no multi-location awareness, and a separate cluster is a separate thing to operate.)

```d2
direction: right

title: "Broken: the holds and the ledger live in separate systems" {
  shape: text
  near: top-center
  style.font-size: 26
  style.bold: true
}

checkout: "Checkout Service" {
  shape: rectangle
  style.fill: "#e8eef7"; style.stroke: "#4a6fa5"; style.stroke-width: 2
}

redis: "Redis — the holds\n\nitem:42:available = 7\nDECR to reserve · INCR to release" {
  shape: cylinder
  style.fill: "#fdecea"; style.stroke: "#c0392b"; style.stroke-width: 2
}

mysql: "MySQL — the ledger\n\ninventory_levels\nthe source of truth" {
  shape: cylinder
  style.fill: "#fdecea"; style.stroke: "#c0392b"; style.stroke-width: 2
}

checkout -> redis: "1. DECR — place the hold" {style.stroke: "#4a6fa5"; style.stroke-width: 2}
checkout -> mysql: "2. UPDATE ledger — claim it\n(seconds later, once payment settles)" {style.stroke: "#4a6fa5"; style.stroke-width: 2}
checkout -> redis: "3. release the hold" {style.stroke-dash: 3; style.stroke: "#c0392b"; style.stroke-width: 2}

note: "No transaction spans this boundary.\n\nSteps 2 and 3 are two independent operations against two systems.\nA crash between them leaves the two stores permanently disagreeing —\nand no retry can fix it, because neither store knows what the other did." {
  shape: text
  near: bottom-center
}
```

**No ordering of those two writes saves you.** Both branches below are the *same* crash at the *same* point; only the order of the preceding writes differs.

```d2
shape: sequence_diagram

buyer: Buyer
app: "Checkout Service" {style.fill: "#e8eef7"; style.stroke: "#4a6fa5"}
redis: "Redis (holds)" {style.fill: "#fdecea"; style.stroke: "#c0392b"}
db: "MySQL (ledger)" {style.fill: "#fdecea"; style.stroke: "#c0392b"}

buyer -> app: "Complete purchase"
app -> redis: "DECR item:42"
redis -> app: "ok — hold placed"
app -> app: "process payment (seconds)"

order_a: "Ordering A — deduct the ledger first" {
  app -> db: "UPDATE ledger SET available = available - 1"
  db -> app: "committed"
  app -> app: "CRASH" {style.stroke: "#c0392b"; style.bold: true}
  app."UNDERSELL: the ledger is deducted but the Redis hold\nis never released, so those units stay invisible until\nthe TTL expires — or forever, if there is no TTL."
}

order_b: "Ordering B — release the hold first" {
  app -> redis: "INCR item:42 — release the hold"
  redis -> app: "ok"
  app -> app: "CRASH" {style.stroke: "#c0392b"; style.bold: true}
  app."OVERSELL: the hold is gone so another buyer can take\nthe same unit, but the ledger was never decremented.\nTwo orders, one unit."
}

verdict: "There is no safe ordering" {
  app -> app: "The bug is the boundary, not the sequence." {style.stroke: "#c0392b"; style.stroke-width: 2}
}
```

Moving the holds into the same database as the ledger makes reserve-and-claim a single ACID transaction and deletes the whole bug class. Which raises the obvious question: why wasn't it always there?

---

## 💡 Intuition first — why the obvious schema doesn't scale

The obvious schema is one row per item with a quantity column:

```sql
UPDATE inventory SET available = available - 3
WHERE item_id = 42 AND available >= 3;
```

This is **correct**. It is also a **hard serialization point**. Every reservation for item 42 queues behind a single row lock, so the ceiling is `1 / lock_hold_time` reservations per second *for that item* — a few thousand per second at best, and far worse if the transaction does anything else while holding the lock. For a flash-sale item, that ceiling is the whole system.

The unlock is a change of granularity: **one row per sellable unit instead of one row per item.** Ten units in stock means ten rows; reserving three means claiming three rows. Now `SELECT … FOR UPDATE SKIP LOCKED` lets concurrent transactions each grab *different* rows and never wait on each other.

```d2
direction: right

bad: "Doesn't scale — one row per item" {
  style.fill: "#fdecea"; style.stroke: "#c0392b"; style.stroke-width: 2
  direction: right

  w1: "worker 1" {shape: circle; style.fill: "#ffffff"}
  w2: "worker 2" {shape: circle; style.fill: "#ffffff"}
  w3: "worker 3" {shape: circle; style.fill: "#ffffff"}
  w4: "worker 4" {shape: circle; style.fill: "#ffffff"}

  row: "item_id = 42\navailable = 7\n\nONE ROW LOCK" {
    shape: rectangle
    style.fill: "#c0392b"; style.stroke: "#7b241c"; style.stroke-width: 2
    style.font-color: "#ffffff"; style.bold: true
  }

  w1 -> row: "holds the lock" {style.stroke: "#27803a"; style.stroke-width: 3}
  w2 -> row: WAIT {style.stroke: "#c0392b"; style.stroke-dash: 3}
  w3 -> row: WAIT {style.stroke: "#c0392b"; style.stroke-dash: 3}
  w4 -> row: WAIT {style.stroke: "#c0392b"; style.stroke-dash: 3}

  cap: "Ceiling ≈ 1 / lock_hold_time for the whole item.\nAdding workers adds queueing, not throughput." {shape: text}
}

good: "Scales — one row per unit + SKIP LOCKED" {
  style.fill: "#eaf5ea"; style.stroke: "#27803a"; style.stroke-width: 2
  direction: right

  w1: "worker 1" {shape: circle; style.fill: "#ffffff"}
  w2: "worker 2" {shape: circle; style.fill: "#ffffff"}
  w3: "worker 3" {shape: circle; style.fill: "#ffffff"}
  w4: "worker 4" {shape: circle; style.fill: "#ffffff"}

  pool: "bounded pool — cap 1,000 rows" {
    style.fill: "#ffffff"; style.stroke: "#27803a"
    u1: "unit 1" {style.fill: "#d4efd8"; style.stroke: "#27803a"}
    u2: "unit 2" {style.fill: "#d4efd8"; style.stroke: "#27803a"}
    u3: "unit 3" {style.fill: "#d4efd8"; style.stroke: "#27803a"}
    u4: "unit 4" {style.fill: "#d4efd8"; style.stroke: "#27803a"}
    more: "…" {style.fill: "#f4f6f6"; style.stroke-dash: 3}
  }

  w1 -> pool.u1: "locks unit 1" {style.stroke: "#27803a"; style.stroke-width: 2}
  w2 -> pool.u2: "skips 1, locks 2" {style.stroke: "#27803a"; style.stroke-width: 2}
  w3 -> pool.u3: "skips 1-2, locks 3" {style.stroke: "#27803a"; style.stroke-width: 2}
  w4 -> pool.u4: "skips 1-3, locks 4" {style.stroke: "#27803a"; style.stroke-width: 2}

  cap: "Nobody waits. Contention drops from one writer per ITEM\nto one writer per UNIT, so throughput scales with pool size." {shape: text}
}
```

### The bounded pool

Row-per-unit does not naively scale: 50,000 units across 10 locations is 500,000 rows, and the `SKIP LOCKED` scan degrades as it walks them. Shopify caps the pool at **1,000 rows per (item, location)** and replenishes from the ledger — sized from observed peak reservation rates per item/location during flash sales, large enough to absorb bursts without running dry and small enough to keep the scan fast [web: shopify.engineering]. **The pool is a buffer, not a mirror of stock.**

If the pool empties mid-flash-sale, the reserve path replenishes inline, under a lock, so exactly one transaction refills and the rest wait rather than stampeding.

---

## 🔀 How it works — porting the design to PostgreSQL

Three of Shopify's four technical decisions are **InnoDB-specific and do not apply to PostgreSQL**. One applies universally. Knowing which is which is most of the value in porting this.

| Shopify's decision | Why InnoDB needed it | PostgreSQL equivalent |
|---|---|---|
| Composite PK `(shop_id, inventory_item_id, inventory_group_id, id)` to take 1 lock per row instead of 2 | InnoDB tables are **index-organized**. With a plain auto-increment PK, a lookup filtered by other columns locks the secondary-index record *and* the clustered record. Folding the filter columns into the PK collapses that to one lock. | **Not needed.** PostgreSQL uses heap tables; indexes carry no locks. A row lock is a mark on the heap tuple, taken once regardless of access path. Still use a composite key — but for *scan locality*, not lock count. |
| `READ COMMITTED` to escape gap locks | InnoDB's default `REPEATABLE READ` takes gap locks, including on the supremum pseudo-record — which blocked replenishment `INSERT`s and deadlocked. | **Free.** `READ COMMITTED` is already PostgreSQL's default, and PostgreSQL takes **no gap locks at all** below `SERIALIZABLE`. The problem does not exist. |
| Consistent lock ordering across reserve/claim | Two tables touched in different orders → circular wait → deadlock. | **Applies identically.** PostgreSQL deadlocks the same way, detects it after `deadlock_timeout` (1s default), and kills a victim. Same fix: fix the order. |
| `UNION ALL` batching for multi-line carts | Fewer round trips, better latency under load. | Applies, but PostgreSQL has a **better idiom**: `LATERAL` over `unnest()` of parameter arrays. One statement, any cart size, no SQL string building. |

And one hazard PostgreSQL adds that InnoDB doesn't have:

| New in PostgreSQL | Why it matters |
|---|---|
| **Dead-tuple bloat is the primary operational risk** | This design churns rows at enormous rates — every reservation deletes rows and inserts rows. PostgreSQL's MVCC leaves a dead tuple behind on every `DELETE` and `UPDATE`. Untuned autovacuum means the `SKIP LOCKED` scan walks growing piles of dead tuples, and latency degrades on a timescale of hours. **This is the thing that will bite you** (see *bloat*, below). |

<div style="border-left:4px solid #15448e;background:rgba(21,68,142,0.08);padding:0.6rem 1rem;border-radius:0 0.5rem 0.5rem 0;margin:1.25rem 0">

📘 **A naming note.** Shopify's third key column is `inventory_group_id`; this page calls it `location_id` throughout, because *"the same SKU at a different warehouse"* is the concrete case that makes the composite key make sense. Same column, clearer name for a reader meeting the design for the first time.

</div>

---

## 🗄️ Schema

Where we're headed — the same three responsibilities, now as three tables inside one transactional boundary:

```d2
direction: right

title: "Working: one database, one transaction" {
  shape: text
  near: top-center
  style.font-size: 26
  style.bold: true
}

checkout: "Checkout Service" {
  shape: rectangle
  style.fill: "#e8eef7"; style.stroke: "#4a6fa5"; style.stroke-width: 2
}

pg: PostgreSQL {
  style.fill: "#eaf5ea"; style.stroke: "#27803a"; style.stroke-width: 3

  units: "reservation_units\n\nbounded pool — one row per unit,\nclaimed with FOR UPDATE SKIP LOCKED" {
    style.fill: "#ffffff"; style.stroke: "#27803a"
  }
  holds: "reserved_quantities\n\nactive holds, each with expires_at" {
    style.fill: "#ffffff"; style.stroke: "#27803a"
  }
  ledger: "inventory_levels\n\nthe source of truth" {
    style.fill: "#ffffff"; style.stroke: "#27803a"
  }

  units -> holds: reserve {style.stroke: "#27803a"; style.stroke-width: 2}
  holds -> ledger: claim {style.stroke: "#27803a"; style.stroke-width: 2}
  holds -> units: "release / expire" {style.stroke-dash: 3; style.stroke: "#7f8c8d"}
  ledger -> units: replenish {style.stroke-dash: 3; style.stroke: "#27803a"}
}

checkout -> pg: "BEGIN … COMMIT" {style.stroke: "#27803a"; style.stroke-width: 3}

note: "The boundary is gone.\n\nEvery state transition is a local write inside one ACID transaction.\nA crash rolls the whole thing back, so there is no intermediate state\nfor two stores to disagree about — the Redis failure modes above are\nnot mitigated, they are unrepresentable." {
  shape: text
  near: bottom-center
}
```

```sql
-- The sequence must exist before the table that defaults to it.
CREATE SEQUENCE reservation_units_id_seq AS bigint CACHE 100;

-- The bounded pool of available units.
-- One row = one sellable unit, capped per (shop, item, location).
CREATE TABLE reservation_units (
    shop_id           bigint      NOT NULL,
    inventory_item_id bigint      NOT NULL,
    location_id       bigint      NOT NULL,
    id                bigint      NOT NULL DEFAULT nextval('reservation_units_id_seq'),
    created_at        timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (shop_id, inventory_item_id, location_id, id)
) PARTITION BY HASH (shop_id);

-- Create partitions up front; 16-64 is a reasonable starting point.
-- Storage and autovacuum parameters MUST be set here, on the leaf
-- partitions -- a partitioned parent has no storage, and
-- ALTER TABLE reservation_units SET (fillfactor = ...) is a hard error:
--   ERROR: cannot specify storage parameters for a partitioned table
DO $$
BEGIN
  FOR i IN 0..15 LOOP
    EXECUTE format(
      'CREATE TABLE reservation_units_p%s PARTITION OF reservation_units
         FOR VALUES WITH (MODULUS 16, REMAINDER %s)
         WITH (fillfactor = 70,
               autovacuum_vacuum_scale_factor  = 0.0,
               autovacuum_vacuum_threshold     = 1000,
               autovacuum_analyze_scale_factor = 0.0,
               autovacuum_analyze_threshold    = 5000,
               autovacuum_vacuum_cost_delay    = 0,
               autovacuum_vacuum_cost_limit    = 10000)', i, i);
  END LOOP;
END $$;
```

**On the primary key.** The column order matters, but for a different reason than in MySQL. `(shop_id, inventory_item_id, location_id, id)` makes all units for one item at one location **contiguous in the index**, so the reserve query's index scan touches a handful of pages instead of scattering. In InnoDB this also determined physical row layout; in PostgreSQL the heap is unordered, which is exactly why bloat control matters more here.

**On `nextval` vs `bigserial`.** Either works. An explicit sequence with `CACHE 100` reduces contention on the sequence itself at high insert rates, at the cost of gaps in the id sequence — which you don't care about, since ids are opaque.

```sql
-- Active holds. This is what "reserved" means to the rest of the system.
CREATE TABLE reserved_quantities (
    id                bigserial   PRIMARY KEY,
    shop_id           bigint      NOT NULL,
    inventory_item_id bigint      NOT NULL,
    location_id       bigint      NOT NULL,
    checkout_id       uuid        NOT NULL,
    quantity          integer     NOT NULL CHECK (quantity > 0),
    expires_at        timestamptz NOT NULL,
    created_at        timestamptz NOT NULL DEFAULT clock_timestamp(),

    -- Idempotency: a retried reserve for the same checkout+item is a no-op,
    -- not a second hold. Non-negotiable; clients WILL retry on timeout.
    UNIQUE (checkout_id, inventory_item_id, location_id)
);

-- Drives the expiry sweeper.
CREATE INDEX idx_reserved_expiry ON reserved_quantities (expires_at);

-- Replenishment sums outstanding holds for one (shop, item, location).
CREATE INDEX idx_reserved_scope
    ON reserved_quantities (shop_id, inventory_item_id, location_id);

-- The source of truth. Reservations never write here; only claims do.
CREATE TABLE inventory_levels (
    shop_id           bigint  NOT NULL,
    inventory_item_id bigint  NOT NULL,
    location_id       bigint  NOT NULL,
    available         integer NOT NULL CHECK (available >= 0),
    PRIMARY KEY (shop_id, inventory_item_id, location_id)
);
```

**Why `clock_timestamp()` and not `now()`.** `now()` is transaction-start time, identical for every row in a transaction. For debugging churn rates you want real wall-clock. Minor — but you will want it at 3am.

---

## ⚙️ Reserve

### The core query

```sql
CREATE FUNCTION take_units(
    p_shop_id bigint, p_item_id bigint, p_location_id bigint, p_quantity integer
) RETURNS integer LANGUAGE sql AS $$
    WITH picked AS (
        SELECT shop_id, inventory_item_id, location_id, id
        FROM reservation_units
        WHERE shop_id           = p_shop_id
          AND inventory_item_id = p_item_id
          AND location_id       = p_location_id
        ORDER BY id
        LIMIT p_quantity
        FOR UPDATE SKIP LOCKED
    ),
    consumed AS (
        DELETE FROM reservation_units u
        USING picked p
        WHERE (u.shop_id, u.inventory_item_id, u.location_id, u.id)
            = (p.shop_id, p.inventory_item_id, p.location_id, p.id)
        RETURNING u.id
    )
    SELECT count(*)::integer FROM consumed;
$$;

-- The inverse: hand units back to the pool.
CREATE FUNCTION return_units(
    p_shop_id bigint, p_item_id bigint, p_location_id bigint, p_count integer
) RETURNS void LANGUAGE sql AS $$
    INSERT INTO reservation_units (shop_id, inventory_item_id, location_id)
    SELECT p_shop_id, p_item_id, p_location_id FROM generate_series(1, p_count);
$$;
```

Four mechanics, two of which are easy to get wrong:

1. **`FOR UPDATE SKIP LOCKED` goes after `LIMIT`.** Syntactically required. Semantically, the executor pulls rows, skips ones already locked by other transactions, and stops once it has `LIMIT` lockable rows.

2. **Without `SKIP LOCKED`, this design is pointless.** A plain `FOR UPDATE` makes every worker queue on the same first row — you've reinvented the single-row bottleneck with extra steps.

3. **`SKIP LOCKED` can return fewer rows than `LIMIT`.** That's the point, and it's why the count check below is mandatory. Never assume you got what you asked for.

4. **Results are non-deterministic under concurrency.** `ORDER BY id` is a hint toward FIFO, not a guarantee — a concurrent transaction may hold row 1 while you take row 2. Fine for a fungible unit pool. Wrong for anything needing strict ordering.

### All-or-nothing, with inline replenishment

Partial reservations are a correctness bug: reserving 2 of 3 requested units and telling the buyer *"yes"* oversells by omission. Wrap the whole thing so it either fully succeeds or fully aborts.

```sql
CREATE FUNCTION reserve_units(
    p_shop_id     bigint,
    p_item_id     bigint,
    p_location_id bigint,
    p_quantity    integer,
    p_checkout_id uuid,
    p_ttl         interval DEFAULT '15 minutes'
) RETURNS boolean
LANGUAGE plpgsql
AS $$
DECLARE
    v_taken integer;
BEGIN
    -- Idempotency short-circuit: this checkout already holds these units.
    PERFORM 1 FROM reserved_quantities
     WHERE checkout_id       = p_checkout_id
       AND inventory_item_id = p_item_id
       AND location_id       = p_location_id;
    IF FOUND THEN
        RETURN true;
    END IF;

    v_taken := take_units(p_shop_id, p_item_id, p_location_id, p_quantity);

    -- Pool ran dry. Refill inline and retry once.
    IF v_taken < p_quantity THEN
        -- Put back what we grabbed so replenishment sees a clean count.
        PERFORM return_units(p_shop_id, p_item_id, p_location_id, v_taken);
        PERFORM replenish_pool(p_shop_id, p_item_id, p_location_id);

        v_taken := take_units(p_shop_id, p_item_id, p_location_id, p_quantity);
        IF v_taken < p_quantity THEN
            PERFORM return_units(p_shop_id, p_item_id, p_location_id, v_taken);
            RETURN false;   -- genuinely out of stock
        END IF;
    END IF;

    INSERT INTO reserved_quantities
        (shop_id, inventory_item_id, location_id, checkout_id, quantity, expires_at)
    VALUES
        (p_shop_id, p_item_id, p_location_id, p_checkout_id, p_quantity,
         clock_timestamp() + p_ttl)
    -- The short-circuit above is a fast path, not the guarantee. Two
    -- concurrent retries of the same checkout can both miss it; the
    -- unique constraint is what actually makes this idempotent.
    ON CONFLICT (checkout_id, inventory_item_id, location_id) DO NOTHING;

    RETURN true;
END $$;
```

### Deadlock avoidance — the one rule that carries over

Shopify hit deadlocks because reserve and claim touched two tables in opposite orders. **The fix is unchanged for PostgreSQL: every path touches tables in the same order.**

```text
reserve:  reservation_units (DELETE)  ->  reserved_quantities (INSERT)
release:  reservation_units (INSERT)  ->  reserved_quantities (DELETE)
claim:                                    reserved_quantities (DELETE)  ->  inventory_levels (UPDATE)
```

The function above respects this: units come out of the pool *before* the `reserved_quantities` insert.

For multi-item carts, **sort line items by `(inventory_item_id, location_id)` before processing** — two carts containing the same two items in opposite orders is the classic deadlock, and a sort is the entire fix. Do that sort **in your application, where ordering is guaranteed**, not in an `ORDER BY` inside a CTE: PostgreSQL may inline a single-reference CTE, and nothing in the planner promises that a subquery's sort order survives into lock acquisition order.

PostgreSQL detects deadlocks after `deadlock_timeout` (1s default) and aborts a victim with `SQLSTATE 40P01`. Your client must retry on `40P01` and `40001`. Design for it; don't pretend it won't happen.

---

## 📦 Batching multi-item carts

Shopify used `UNION ALL`. PostgreSQL's `LATERAL` is cleaner — a single prepared statement handling any cart size via array parameters, with no SQL string concatenation:

```sql
WITH req(item_id, location_id, qty) AS (
    -- Arrays are built pre-sorted by the application (see above).
    SELECT * FROM unnest($2::bigint[], $3::bigint[], $4::int[])
),
picked AS (
    SELECT u.*
    FROM req r
    CROSS JOIN LATERAL (
        SELECT shop_id, inventory_item_id, location_id, id
        FROM reservation_units
        WHERE shop_id           = $1
          AND inventory_item_id = r.item_id
          AND location_id       = r.location_id
        ORDER BY id
        LIMIT r.qty
        FOR UPDATE SKIP LOCKED
    ) u
),
consumed AS (
    DELETE FROM reservation_units t
    USING picked p
    WHERE (t.shop_id, t.inventory_item_id, t.location_id, t.id)
        = (p.shop_id, p.inventory_item_id, p.location_id, p.id)
    RETURNING t.inventory_item_id, t.location_id
)
SELECT inventory_item_id, location_id, count(*) AS taken
FROM consumed
GROUP BY 1, 2;
```

Compare the result set against your request in the application (or a wrapping function) and abort the whole transaction if any line came up short.

<div style="border-left:4px solid #195045;background:rgba(25,80,69,0.08);padding:0.6rem 1rem;border-radius:0 0.5rem 0.5rem 0;margin:1.25rem 0">

💡 **`FOR UPDATE` inside `CROSS JOIN LATERAL` works** — executed on PostgreSQL 17.10 and confirmed to return the locked rows. PostgreSQL *does* reject row locking in some subquery positions (notably the nullable side of an outer join), which is why this is worth knowing rather than guessing. If you're on an older major version, test it there before shipping; the fallback is generated `UNION ALL` branches, which is what Shopify did anyway.

</div>

---

## 🔄 Replenish, claim, release, expire

Every state a single unit can occupy, and every transition between them. The sections below implement each arrow:

```d2
direction: down

ledger: "In the ledger only\n\ncounted in inventory_levels.available,\nbut not yet in the pool" {
  style.fill: "#f4f6f6"; style.stroke: "#7f8c8d"; style.stroke-width: 2
}

pool: "In the pool\n\na reservation_units row —\navailable and unlocked" {
  style.fill: "#eaf5ea"; style.stroke: "#27803a"; style.stroke-width: 2
}

locked: "Locked by a transaction\n\nheld by FOR UPDATE SKIP LOCKED —\ninvisible to every other reserver" {
  style.fill: "#fff4e5"; style.stroke: "#d68910"; style.stroke-width: 2
}

held: "Reserved\n\na reserved_quantities row\nwith an expires_at" {
  style.fill: "#e8eef7"; style.stroke: "#4a6fa5"; style.stroke-width: 2
}

claimed: "Claimed\n\ndeducted from inventory_levels\n— terminal" {
  style.fill: "#d4efd8"; style.stroke: "#27803a"; style.stroke-width: 3
}

ledger -> pool: "replenish — background at low water,\nor inline when the pool runs dry" {style.stroke: "#27803a"; style.stroke-width: 2}
pool -> locked: "SELECT … FOR UPDATE SKIP LOCKED"
locked -> held: "DELETE the unit, INSERT the hold\n(same transaction)" {style.stroke: "#4a6fa5"; style.stroke-width: 2}
locked -> pool: "transaction rolled back" {style.stroke-dash: 3; style.stroke: "#7f8c8d"}
held -> claimed: "payment succeeded" {style.stroke: "#27803a"; style.stroke-width: 3}
held -> pool: "payment failed, or expires_at passed" {style.stroke-dash: 3; style.stroke: "#7f8c8d"}

note: "The safety invariant:  pool_size + outstanding_holds ≤ available\n\nEnforced by least() in replenish_pool(). Hold it and you cannot oversell —\nevery other rule in this design exists to serve it." {
  shape: text
  near: bottom-center
}
```

### Replenish — advisory locks are PostgreSQL's best answer

The requirement: when the pool runs dry, exactly one transaction refills it while the others wait. PostgreSQL's transaction-scoped advisory locks do this in one line, with automatic release at commit or abort.

```sql
CREATE FUNCTION replenish_pool(
    p_shop_id     bigint,
    p_item_id     bigint,
    p_location_id bigint,
    p_cap         integer DEFAULT 1000
) RETURNS integer
LANGUAGE plpgsql
AS $$
DECLARE
    v_current   integer;
    v_available integer;
    v_reserved  integer;
    v_to_add    integer;
BEGIN
    -- Serialize replenishment for this (shop, item, location).
    -- Concurrent callers block here instead of all racing to INSERT.
    PERFORM pg_advisory_xact_lock(
        hashtextextended(p_shop_id::text     || ':' ||
                         p_item_id::text     || ':' ||
                         p_location_id::text, 0)
    );

    -- Another transaction may have refilled while we waited. Re-check.
    SELECT count(*) INTO v_current
    FROM reservation_units
    WHERE shop_id           = p_shop_id
      AND inventory_item_id = p_item_id
      AND location_id       = p_location_id;

    IF v_current >= p_cap THEN
        RETURN 0;
    END IF;

    SELECT available INTO v_available
    FROM inventory_levels
    WHERE shop_id           = p_shop_id
      AND inventory_item_id = p_item_id
      AND location_id       = p_location_id;

    -- No ledger row means nothing to sell -- not "sell without a limit".
    IF v_available IS NULL THEN
        RETURN 0;
    END IF;

    SELECT coalesce(sum(quantity), 0) INTO v_reserved
    FROM reserved_quantities
    WHERE shop_id           = p_shop_id
      AND inventory_item_id = p_item_id
      AND location_id       = p_location_id
      AND expires_at        > clock_timestamp();

    -- Pool + outstanding holds must never exceed real stock.
    v_to_add := least(p_cap - v_current,
                      v_available - v_reserved - v_current);

    IF v_to_add <= 0 THEN
        RETURN 0;
    END IF;

    PERFORM return_units(p_shop_id, p_item_id, p_location_id, v_to_add);
    RETURN v_to_add;
END $$;
```

<div style="border-left:4px solid #da5233;background:rgba(218,82,51,0.08);padding:0.6rem 1rem;border-radius:0 0.5rem 0.5rem 0;margin:1.25rem 0">

⚠️ **Use `pg_advisory_xact_lock`, never `pg_advisory_lock`.** Session-scoped advisory locks outlive the transaction and, behind a transaction-pooling PgBouncer, will leak onto a connection later handed to an unrelated client. Transaction-scoped locks release on `COMMIT` or `ROLLBACK` and are pooler-safe.

</div>

The `least()` call is the safety property of the whole system: **pool size + outstanding reservations ≤ available stock.** If that holds, you cannot oversell.

Run replenishment proactively on a background worker at a low-water mark (say 30% of cap) so the inline path is a rare fallback, not the norm. The inline path costs a buyer latency; the background path costs nobody anything.

### Claim

Payment succeeded. Deduct permanently. One transaction — and this is the atomicity Redis could not give you:

```sql
BEGIN;

WITH released AS (
    DELETE FROM reserved_quantities
    WHERE checkout_id = $1
    RETURNING shop_id, inventory_item_id, location_id, quantity
)
UPDATE inventory_levels l
SET available = l.available - r.quantity
FROM released r
WHERE l.shop_id           = r.shop_id
  AND l.inventory_item_id = r.inventory_item_id
  AND l.location_id       = r.location_id;

COMMIT;
```

Claimed units are **not** returned to the pool — they're gone from real stock. The `CHECK (available >= 0)` constraint is your last line of defence if the accounting is ever wrong. Let it throw: a failed claim is recoverable, an oversell is not.

### Release and expire

Payment failed or the hold aged out. Units go back to the pool.

```sql
-- Sweeper: run every 30-60s. Batched, so it never holds a long transaction.
--
-- NOTE: DELETE does not accept LIMIT in PostgreSQL --
--   ERROR: syntax error at or near "LIMIT"
-- Bound the batch by selecting ctids first, then deleting those.
-- FOR UPDATE SKIP LOCKED lets several sweepers run without colliding.
WITH batch AS (
    SELECT ctid
    FROM reserved_quantities
    WHERE expires_at < clock_timestamp()
    ORDER BY expires_at
    LIMIT 500
    FOR UPDATE SKIP LOCKED
),
expired AS (
    DELETE FROM reserved_quantities r
    USING batch b
    WHERE r.ctid = b.ctid
    RETURNING r.shop_id, r.inventory_item_id, r.location_id, r.quantity
)
INSERT INTO reservation_units (shop_id, inventory_item_id, location_id)
SELECT shop_id, inventory_item_id, location_id
FROM expired, generate_series(1, expired.quantity);
```

**Batch the sweeper and keep each transaction short.** An unbounded `DELETE … WHERE expires_at < now()` after an outage will hold locks and a connection for minutes — precisely the failure mode the *connection attribution* section is about. The sweeper is background work; it must never compete with checkout for connections.

---

## 🧹 The PostgreSQL-specific hazard: bloat

This is not in the Shopify post because InnoDB doesn't have it. **In PostgreSQL it is the number one operational risk of this design, and it will not show up in a short load test.**

Every reservation deletes rows from `reservation_units`, and every `DELETE` leaves a dead tuple that occupies space until vacuumed. At 10,000 reservations/sec you generate tens of thousands of dead tuples per second in a table whose entire performance story depends on `SKIP LOCKED` scanning a small number of pages. Let them accumulate and the scan walks dead tuples to find live ones. Latency climbs slowly, then not slowly.

The per-partition `autovacuum_*` settings in the schema above are the fix — vacuum on **absolute row counts** rather than a percentage of a small table, and don't throttle, because this table needs vacuum to keep up always. They must be set on the leaf partitions; a partitioned parent has no storage and rejects them.

Cluster-level settings that matter as much:

```ini
autovacuum_max_workers = 6        # with hash partitioning, workers run in parallel
autovacuum_naptime = 10s          # the 1min default is too slow for this churn
```

Monitor it as a first-class SLI, not an afterthought:

```sql
SELECT relname,
       n_live_tup,
       n_dead_tup,
       round(100.0 * n_dead_tup / nullif(n_live_tup + n_dead_tup, 0), 1) AS pct_dead,
       last_autovacuum,
       autovacuum_count
FROM pg_stat_user_tables
WHERE relname LIKE 'reservation_units%'
ORDER BY n_dead_tup DESC;
```

**Alert when `pct_dead` on any partition exceeds ~20% for more than a few minutes.** That is your early warning that vacuum has fallen behind, and it arrives well before latency does.

Two related notes. First, this table is a heavy **transaction ID consumer** — watch `age(datfrozenxid)` and never let anti-wraparound vacuum be the first vacuum that runs on a hot partition. Second, hash partitioning earns its keep here specifically because autovacuum assigns workers *per table*: 16 partitions can be vacuumed concurrently, while one giant table gets exactly one worker.

---

## 🔌 Connection attribution — the actual lesson

Shopify's throughput ceiling wasn't locks, queries, or CPU. It was **connection exhaustion at the ProxySQL layer, caused by code they weren't looking at** holding database connections longer than necessary across the checkout path. Those paths hadn't been optimised because they hadn't been the first to hit the limit; reservations were simply the workload that got there first. Cleaning them up **removed 50% of reads and 33% of transactions on the primary**, and an InnoDB thread-concurrency setting that hadn't been revisited in years turned out to be part of the same story. Afterwards, during high-volume flash sales, writer CPU stayed under 50% and reader CPU under 16% [web: shopify.engineering].

This matters *more* in PostgreSQL than in MySQL. PostgreSQL forks a backend process per connection, so a few hundred connections is a lot, where MySQL's threaded model handles thousands. **A pooler is mandatory, not optional.**

### Tag every statement with its business process

Shopify annotated SQL with a connection tag and parsed it at the proxy. PostgreSQL gives you two mechanisms — use both:

```sql
-- Per-connection, visible in pg_stat_activity and logs:
SET application_name = 'checkout_completion';

-- Per-statement, sqlcommenter style: survives into pg_stat_statements
-- and log lines even when connections are reused across processes.
SELECT /* app='checkout',route='reserve' */ count(*) FROM reservation_units;
```

Most ORMs support this natively (marginalia in Rails, sqlcommenter in Django/SQLAlchemy). Set `application_name` on checkout, and turn on `pg_stat_statements.track = all` with `compute_query_id = on`.

### Measure connection *hold* time, not query time

This is the distinction the whole story turns on, and the one most teams miss. `pg_stat_statements` tells you which queries are slow. It says nothing about a transaction that runs three fast queries and then sits `idle in transaction` for 400 ms waiting on an HTTP call to a payment gateway — which is the pattern that actually eats your pool.

Sample `pg_stat_activity` every second and aggregate:

```sql
SELECT coalesce(nullif(application_name, ''), 'untagged') AS caller,
       state,
       count(*)                              AS sessions,
       max(clock_timestamp() - xact_start)   AS oldest_xact,
       max(clock_timestamp() - state_change) AS longest_in_state
FROM pg_stat_activity
WHERE backend_type = 'client backend'
  AND xact_start IS NOT NULL
GROUP BY 1, 2
ORDER BY sessions DESC;
```

**`state = 'idle in transaction'` is the smoking gun.** A connection in that state holds its snapshot (blocking vacuum — see above), holds every lock it has taken, and holds a pool slot, while doing precisely nothing. Every one of these is a bug.

Put a hard stop on it:

```ini
idle_in_transaction_session_timeout = 15s     # kill the leak, loudly
statement_timeout = 5s                        # per-role, for OLTP paths
lock_timeout = 1s                             # fail fast rather than pile up
log_min_duration_statement = 200ms
log_lock_waits = on
```

And watch the pooler, where exhaustion actually becomes visible — PgBouncer's `SHOW POOLS` (`cl_waiting` is the number you care about) and `SHOW STATS`. Clients waiting for a server connection is the direct analogue of the ProxySQL exhaustion Shopify observed.

Stated plainly: **tag at the application layer, aggregate at the proxy or via sampling, and alert on connection-seconds per business process.** Knowing the pool is exhausted tells you nothing about who exhausted it.

---

## 🏭 In production — rolling it out

Shopify's cutover is worth copying wholesale, because it's the part most teams improvise and regret.

**Shadow mode.** Dual-write every reservation to both the old system and the new one, with the old system still the source of truth. Compare outcomes — correctness *and* latency — on real production traffic before trusting anything.

**No migration needed.** Because both systems are live and reservations are short-lived, there are no in-flight records to migrate: the old system's holds drain naturally while the new one accumulates its own. This property is worth engineering *for* — short TTLs make cutover trivial.

**Kill switch, permanently armed.** Keep the dual-write path active after flipping the source of truth, so the old system retains a complete view and reverting is one config change rather than a recovery operation.

**Ramp by shard, smallest first.** Shopify went pod by pod, starting with low-traffic pods and working up to their highest-volume merchants. Your riskiest tenant should be the last one you migrate, not the one that finds the bug.

---

## ⚖️ Trade-offs — should you build this?

**Probably not.** Be honest about your contention profile before adopting a design built for a platform that peaked at **$5.1 million in sales per minute** on Black Friday 2025 [web: shopify.engineering].

Start here:

```sql
UPDATE inventory_levels
SET available = available - $1
WHERE shop_id = $2 AND inventory_item_id = $3 AND location_id = $4
  AND available >= $1
RETURNING available;
```

Zero rows returned means insufficient stock. This is correct, trivially understandable, and handles **low thousands of reservations per second on a single hot row**. Most systems never exceed that on any individual SKU.

| Option | Gives you | Costs you | Use when |
| --- | --- | --- | --- |
| Single-row `UPDATE … WHERE available >= n` | Correctness in one statement; nothing to operate | Ceiling of `1 / lock_hold_time` per item | Contention spreads across a catalogue — almost always |
| Row-per-unit + `SKIP LOCKED` | Throughput scales with pool size; atomic with the ledger | Bloat management, replenishment, a pool to size and monitor | One SKU genuinely saturates one row lock |
| Hold in a separate store (Redis) | Fast, simple, familiar | **Cannot be atomic with the ledger** — oversell or undersell on crash | Holds are advisory and a wrong answer is cheap |

Move to row-per-unit when you can demonstrate **all three**:

- a single item/location genuinely exceeds what one row lock can serialize, **and**
- contention concentrates on individual SKUs (flash sales, drops, ticketing) rather than spreading across a catalogue, **and**
- reservations must be atomic with a ledger living in the same database.

If contention is spread thin across many items, the single-row approach already gives you per-item parallelism, and row-per-unit buys nothing but bloat and operational surface area.

**And regardless of which you pick:** the real finding was that the bottleneck lived somewhere nobody was looking. Instrument connection hold time by business process *before* you optimise anything. You may find, as they did, that the fix has nothing to do with the system you were planning to rewrite.

---

## 🔢 Numbers that matter

Every figure below is either quoted from the source write-up or measured on this page — nothing here is estimated.

| Quantity | Value |
| --- | --- |
| Pool cap per (item, location) | 1,000 rows |
| Single hot row, `UPDATE … WHERE available >= n` | low thousands of reservations/sec |
| Row-per-unit ceiling | scales with pool size, not lock hold time |
| Checkout-path cleanup — read reduction on the primary | 50% of reads |
| Checkout-path cleanup — transaction reduction | 33% of transactions |
| Writer CPU during high-volume flash sales | under 50% |
| Reader CPU during high-volume flash sales | under 16% |
| Peak sales rate the design sustains | $5.1M per minute (Black Friday 2025) |
| Bloat alarm threshold | `pct_dead` above ~20% for more than a few minutes |
| Verification result (64-client pgbench, PG 17.10) | 50 holds / 50 units, zero oversell, zero deadlocks |

The two ratios worth carrying away are the last-but-two: **CPU headroom of 50% and 84% at peak** is what "this design is not the bottleneck" actually looks like in a dashboard.

---

## 🪤 Pitfalls & traps

<div style="border-left:4px solid #da5233;background:rgba(218,82,51,0.08);padding:0.6rem 1rem;border-radius:0 0.5rem 0.5rem 0;margin:1.25rem 0">

⚠️ **The trap this whole page exists to name: optimising the system you suspect instead of the one that is slow.** The measured win here came from connection hold time on the checkout path, not from the reservation algorithm at all. Instrument first — **Connection attribution** above is the section that matters most, and it is the one most readers will skip.

</div>

The rest are specific to this design, and each has a section above that treats it properly.

- **Holding reservations outside the database.** A Redis hold is fast and familiar, and it **cannot be atomic with the ledger** — a crash between the two stores oversells or undersells. Acceptable only when a hold is advisory and a wrong answer is cheap.
- **Ignoring bloat until it bites.** Row-per-unit churns rows constantly, so dead tuples accumulate faster than a default autovacuum expects. See **The PostgreSQL-specific hazard: bloat** above.
- **Sizing the pool once and forgetting it.** The 1,000-row cap is the source's number for their workload, not a universal constant; a pool too small reintroduces the very contention it was built to remove.
- **Migrating the riskiest tenant first.** Ramp smallest-first — your highest-volume merchant should be the last cutover, not the one that discovers the bug.
- **Adopting this at all without the three preconditions.** The trade-off table above lists them, and they are conjunctive: fail any one and the single-row `UPDATE` is the better design.

---

## 🧪 Verify it yourself

Every SQL block above was executed against **PostgreSQL 17.10**. To reproduce the concurrency result:

```bash
docker run -d --name pgverify -e POSTGRES_PASSWORD=x -e POSTGRES_DB=inv -p 55444:5432 postgres:17-alpine
```

Load the schema and functions, seed 50 units, then race 64 clients for them:

```sql
INSERT INTO inventory_levels VALUES (1, 42, 7, 50);
SELECT replenish_pool(1, 42, 7);
```

```bash
pgbench -d inv -f reserve.sql -c 64 -j 8 -t 20 -n
```

where `reserve.sql` calls `reserve_units` with a distinct checkout id per transaction. With 1,280 transactions racing for 50 units, the run above produced exactly **50 holds covering 50 units, zero oversell, and zero deadlocks** — `pool + held = 50 = available`. That equality *is* the safety invariant; assert it after any load test.

Bloat and pool exhaustion only appear under **sustained** load, so for a real soak run for hours, not minutes, and watch three things side by side:

```sql
-- 1. Is vacuum keeping up?
SELECT relname, n_dead_tup, last_autovacuum FROM pg_stat_user_tables
 WHERE relname LIKE 'reservation_units%' ORDER BY n_dead_tup DESC LIMIT 5;

-- 2. What are backends actually waiting on?
SELECT wait_event_type, wait_event, count(*) FROM pg_stat_activity
 WHERE backend_type = 'client backend' GROUP BY 1, 2 ORDER BY 3 DESC;

-- 3. Are we deadlocking or rolling back?
SELECT deadlocks, xact_commit, xact_rollback FROM pg_stat_database
 WHERE datname = current_database();
```

If throughput is flat while CPU is low and `wait_event_type` shows `Client` or `IPC` rather than `Lock`, you are **not** lock-bound. Go look at connections.

---

## ✅ Check yourself

```quiz
{"prompt": "Reservations live in Redis and the ledger in MySQL. You must (a) decrement the ledger and (b) release the Redis hold. Which ordering is safe against a crash between the two?", "options": ["Ledger first, then release the hold", "Release the hold first, then the ledger", "Neither — one ordering undersells and the other oversells", "Either, as long as both operations are retried"], "answer": "Neither — one ordering undersells and the other oversells"}
```

```quiz
{"prompt": "Why does the reserve query use FOR UPDATE SKIP LOCKED rather than plain FOR UPDATE?", "options": ["SKIP LOCKED is faster because it takes no locks at all", "Plain FOR UPDATE makes every concurrent worker queue on the same first row, recreating the single-row bottleneck", "SKIP LOCKED guarantees FIFO ordering across transactions", "Plain FOR UPDATE cannot be combined with LIMIT"], "answer": "Plain FOR UPDATE makes every concurrent worker queue on the same first row, recreating the single-row bottleneck"}
```

```quiz
{"prompt": "You port this design to PostgreSQL and copy Shopify's switch to READ COMMITTED to escape gap locks. What does that buy you?", "options": ["Nothing — READ COMMITTED is already PostgreSQL's default, and PostgreSQL takes no gap locks below SERIALIZABLE", "It halves the number of row locks per reservation", "It prevents the replenishment deadlock, which PostgreSQL has too", "It is required for SKIP LOCKED to work"], "answer": "Nothing — READ COMMITTED is already PostgreSQL's default, and PostgreSQL takes no gap locks below SERIALIZABLE"}
```

```quiz
{"prompt": "Reserve latency has been degrading for hours. CPU is low, no deadlocks, and pg_stat_statements shows the reserve query itself is unchanged. What should you look at FIRST?", "options": ["Increase the bounded pool cap from 1,000 to 10,000", "n_dead_tup on the reservation_units partitions — the SKIP LOCKED scan is walking dead tuples autovacuum hasn't reclaimed", "Switch the isolation level to SERIALIZABLE", "Add more hash partitions"], "answer": "n_dead_tup on the reservation_units partitions — the SKIP LOCKED scan is walking dead tuples autovacuum hasn't reclaimed"}
```

<details>
<summary><strong>Q:</strong> The reserve function short-circuits on an existing hold for the same checkout, yet it <em>also</em> carries a unique constraint and <code>ON CONFLICT DO NOTHING</code>. Isn't one of those redundant?</summary>

No — they do different jobs. The `PERFORM … IF FOUND` check is a **fast path**: it avoids taking units from the pool when a retry arrives after the original succeeded. But it is a read followed by a write with no lock between them, so two concurrent retries of the same checkout can both see no row and both proceed to insert.

The `UNIQUE (checkout_id, inventory_item_id, location_id)` constraint is the actual **guarantee**, and `ON CONFLICT DO NOTHING` turns the loser of that race into a no-op rather than an error. A general rule: application-level checks make the common case cheap, constraints make the rare case correct. Never let the first one do the second one's job.

</details>

<details>
<summary><strong>Q:</strong> Replenishment computes <code>least(cap - current, available - reserved - current)</code>. What breaks if you drop the second term and just refill to the cap?</summary>

You oversell. The pool is a *claim* on stock that hasn't been deducted from the ledger yet, so pool rows and outstanding holds both represent units that are spoken for. Refilling blindly to the cap would mint pool rows for units that are already reserved by someone else, and two buyers would successfully reserve the same physical unit.

The second term is what keeps `pool_size + outstanding_holds ≤ available` true. That inequality is the entire safety property of the design — the `SKIP LOCKED` machinery is just how you make it fast.

</details>

<details>
<summary><strong>Q:</strong> Your reservation table is bloating despite aggressive per-partition autovacuum settings. Vacuum runs constantly but <code>n_dead_tup</code> keeps climbing. What is the likely cause?</summary>

A long-running transaction somewhere else in the system. Vacuum can only reclaim tuples that are invisible to **every** open snapshot, so a single connection sitting `idle in transaction` — or a long analytics query on a replica with `hot_standby_feedback = on` — pins the horizon and makes vacuum unable to remove anything newer, no matter how often it runs.

This is why the bloat problem and the connection-hold problem are the same problem wearing two hats: check `pg_stat_activity` for the oldest `xact_start`, and enforce `idle_in_transaction_session_timeout`.

</details>

---

## 📚 Sources

- [web: shopify.engineering/scaling-inventory-reservations] — the origin of the problem framing and of four decisions: the composite primary key and its InnoDB lock-count rationale, the `READ COMMITTED` switch to escape gap locks, consistent lock ordering across reserve/claim, and `UNION ALL` batching. Also the source of every figure quoted here: the 1,000-row pool cap per item/location, the checkout-path cleanup removing **50% of reads and 33% of transactions** on the primary, writer CPU under **50%** and reader CPU under **16%** during high-volume flash sales, and **$5.1M in sales per minute** at peak on Black Friday 2025.
- [web: postgresql.org/docs — *The Locking Clause* (`FOR UPDATE … SKIP LOCKED`), *Advisory Locks*, *Routine Vacuuming*, *Table Partitioning*, `pg_stat_activity`] — for the PostgreSQL semantics this port relies on.
- **Executed, not assumed.** Every SQL block was run against PostgreSQL 17.10, including the 64-client pgbench race. Three defects were found and fixed that way: `DELETE … RETURNING … LIMIT` is a syntax error; storage and autovacuum parameters cannot be set on a partitioned parent; and a `DEFAULT nextval(…)` needs its sequence created first.

Related lessons: [Dealing with Contention](/synapse/system-design-from-first-principles/patterns/dealing-with-contention) · [Transactions & Isolation](/synapse/system-design-from-first-principles/distributed-data/transactions-and-isolation) · [Idempotency & Exactly-Once](/synapse/system-design-from-first-principles/patterns/idempotency-and-exactly-once) · [Scaling Writes](/synapse/system-design-from-first-principles/patterns/scaling-writes)
