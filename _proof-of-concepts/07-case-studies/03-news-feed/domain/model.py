"""Domain model — entities and events (no I/O, no framework)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Post:
    id: int
    author_id: int
    content: str


@dataclass(frozen=True, slots=True)
class PostEvent:
    """A fan-out event pulled off the queue (carries the delivery id for ack)."""

    msg_id: str
    post_id: int
    author_id: int
