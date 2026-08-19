-- URL shortener — system of record + id range allocator.
-- The unique PRIMARY KEY on links.code is the hard guarantee against double-issue.

CREATE TABLE IF NOT EXISTS links (
    code       TEXT PRIMARY KEY,
    long_url   TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One row, mutated by atomic fetch-and-add. This is the whole "distributed
-- counter" — disjoint ranges leased from a single row, no per-write hot counter.
CREATE TABLE IF NOT EXISTS id_range_allocator (
    name       TEXT PRIMARY KEY,
    next_value BIGINT NOT NULL
);
