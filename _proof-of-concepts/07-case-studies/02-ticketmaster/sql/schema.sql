-- Ticketmaster POC — the orders store is the system of record; the seat row's
-- status is the contended resource, guarded by SELECT ... FOR UPDATE at confirm.

CREATE TABLE IF NOT EXISTS seats (
    seat_id  TEXT PRIMARY KEY,
    event_id TEXT NOT NULL,
    status   TEXT NOT NULL DEFAULT 'available',  -- 'available' | 'sold'
    sold_to  TEXT
);

CREATE TABLE IF NOT EXISTS orders (
    id         BIGSERIAL PRIMARY KEY,
    seat_id    TEXT NOT NULL REFERENCES seats(seat_id),
    holder     TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
