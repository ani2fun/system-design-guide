-- News feed POC. Post ids are a monotonic BIGSERIAL, so id order ≈ time order —
-- which lets the timeline cache use the id itself as the sort score.

CREATE TABLE IF NOT EXISTS posts (
    id         BIGSERIAL PRIMARY KEY,
    author_id  BIGINT NOT NULL,
    content    TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS posts_author_id_idx ON posts (author_id, id DESC);

CREATE TABLE IF NOT EXISTS follows (
    follower_id BIGINT NOT NULL,
    followee_id BIGINT NOT NULL,
    PRIMARY KEY (follower_id, followee_id)
);
CREATE INDEX IF NOT EXISTS follows_followee_idx ON follows (followee_id);
