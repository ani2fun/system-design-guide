"""Postgres adapters — persistence + read-model ports (infrastructure).

The only place asyncpg is imported.
"""

from __future__ import annotations

import asyncpg

from domain.model import Post
from domain.ports import FeedQueries, FollowGraph, PostRepository


class PostgresPostRepository(PostRepository):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def add(self, author_id: int, content: str) -> int:
        post_id: int = await self._pool.fetchval(
            "INSERT INTO posts (author_id, content) VALUES ($1, $2) RETURNING id",
            author_id,
            content,
        )
        return post_id

    async def hydrate(self, ids: list[int]) -> list[Post]:
        rows = await self._pool.fetch(
            "SELECT id, author_id, content FROM posts WHERE id = ANY($1::bigint[])", ids
        )
        return [Post(id=r["id"], author_id=r["author_id"], content=r["content"]) for r in rows]


class PostgresFollowGraph(FollowGraph):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def add_follow(self, follower_id: int, followee_id: int) -> None:
        await self._pool.execute(
            "INSERT INTO follows (follower_id, followee_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            follower_id,
            followee_id,
        )

    async def followers(self, author_id: int) -> list[int]:
        rows = await self._pool.fetch(
            "SELECT follower_id FROM follows WHERE followee_id = $1", author_id
        )
        return [r["follower_id"] for r in rows]

    async def follower_count(self, author_id: int) -> int:
        count: int = await self._pool.fetchval(
            "SELECT count(*) FROM follows WHERE followee_id = $1", author_id
        )
        return count


class PostgresFeedQueries(FeedQueries):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def celebrity_recent_post_ids(self, user_id: int, threshold: int, limit: int) -> list[int]:
        rows = await self._pool.fetch(
            "SELECT p.id FROM posts p "
            "WHERE p.author_id IN ("
            "  SELECT f.followee_id FROM follows f "
            "  WHERE f.follower_id = $1 "
            "    AND (SELECT count(*) FROM follows c WHERE c.followee_id = f.followee_id) >= $2"
            ") "
            "ORDER BY p.id DESC LIMIT $3",
            user_id,
            threshold,
            limit,
        )
        return [r["id"] for r in rows]

    async def celebrities(self, threshold: int) -> list[tuple[int, int]]:
        rows = await self._pool.fetch(
            "SELECT followee_id, count(*) AS followers FROM follows "
            "GROUP BY followee_id HAVING count(*) >= $1 ORDER BY followers DESC",
            threshold,
        )
        return [(r["followee_id"], r["followers"]) for r in rows]
