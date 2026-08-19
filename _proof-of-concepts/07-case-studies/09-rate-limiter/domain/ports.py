"""Port — atomic script execution (Dependency Inversion).

The algorithm *logic* (Lua) is domain knowledge in AtomicCounter; only running a
script atomically is infrastructure. The domain never imports redis.
"""

from __future__ import annotations

import abc


class ScriptRunner(abc.ABC):
    @abc.abstractmethod
    async def eval(self, script: str, keys: list[str], args: list[str]) -> list[int]:
        """Run a Lua script atomically; return its integer array reply."""
