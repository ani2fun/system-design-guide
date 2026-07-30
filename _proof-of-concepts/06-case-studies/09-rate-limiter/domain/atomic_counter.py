"""AtomicCounter — the race-killer (C4 code element).

Each algorithm is one Lua script executed as a single atomic round-trip, so a
concurrent burst can never over-admit (read-then-write from the app would lose
updates). The scripts *are* the algorithms; the ScriptRunner port only executes
them. Every script returns [allowed, remaining, retry_after_ms].
"""

from __future__ import annotations

from domain.model import Decision
from domain.ports import ScriptRunner

_FIXED = """
local c = redis.call('INCR', KEYS[1])
if c == 1 then redis.call('PEXPIRE', KEYS[1], ARGV[2]) end
local limit = tonumber(ARGV[1])
if c <= limit then return {1, limit - c, 0} end
return {0, 0, redis.call('PTTL', KEYS[1])}
"""

_SLIDING = """
local now = tonumber(ARGV[2])
local window = tonumber(ARGV[3])
local limit = tonumber(ARGV[1])
redis.call('ZREMRANGEBYSCORE', KEYS[1], 0, now - window)
local count = redis.call('ZCARD', KEYS[1])
if count < limit then
  redis.call('ZADD', KEYS[1], now, tostring(now) .. ':' .. tostring(math.random()))
  redis.call('PEXPIRE', KEYS[1], window)
  return {1, limit - count - 1, 0}
end
return {0, 0, window}
"""

_BUCKET = """
local cap = tonumber(ARGV[1])
local refill = tonumber(ARGV[2])   -- tokens per ms
local now = tonumber(ARGV[3])
local d = redis.call('HMGET', KEYS[1], 'tokens', 'ts')
local tokens = tonumber(d[1])
local ts = tonumber(d[2])
if tokens == nil then tokens = cap; ts = now end
tokens = math.min(cap, tokens + (now - ts) * refill)
local allowed = 0
if tokens >= 1 then tokens = tokens - 1; allowed = 1 end
redis.call('HMSET', KEYS[1], 'tokens', tokens, 'ts', now)
redis.call('PEXPIRE', KEYS[1], math.ceil(cap / refill))
if allowed == 1 then return {1, math.floor(tokens), 0} end
return {0, 0, math.ceil((1 - tokens) / refill)}
"""


class AtomicCounter:
    def __init__(self, runner: ScriptRunner) -> None:
        self._runner = runner

    @staticmethod
    def _decide(reply: list[int]) -> Decision:
        return Decision(allowed=bool(reply[0]), remaining=int(reply[1]), retry_after_ms=int(reply[2]))

    async def fixed_window(self, key: str, limit: int, window_ms: int) -> Decision:
        return self._decide(await self._runner.eval(_FIXED, [key], [str(limit), str(window_ms)]))

    async def sliding_window(self, key: str, limit: int, window_ms: int, now_ms: int) -> Decision:
        reply = await self._runner.eval(_SLIDING, [key], [str(limit), str(now_ms), str(window_ms)])
        return self._decide(reply)

    async def token_bucket(self, key: str, capacity: int, refill_per_ms: float, now_ms: int) -> Decision:
        reply = await self._runner.eval(_BUCKET, [key], [str(capacity), str(refill_per_ms), str(now_ms)])
        return self._decide(reply)
