"""The experiments — drive two interleaved transactions to reproduce an anomaly,
then re-run with the guard that prevents it. Pure domain logic over the ports;
asyncio here is just concurrency control, not infrastructure.
"""

from __future__ import annotations

import asyncio

from domain.model import AnomalyResult, SerializationConflict
from domain.ports import Ledger


class LostUpdateExperiment:
    """Two clients each do read-modify-write on the same balance. Without a lock
    one update is silently lost; SELECT … FOR UPDATE serializes them."""

    ACCOUNT = "alice"
    START = 100

    def __init__(self, ledger: Ledger) -> None:
        self._ledger = ledger

    async def run_anomaly(self) -> AnomalyResult:
        await self._ledger.reset_balance(self.ACCOUNT, self.START)
        s1, s2 = self._ledger.session(), self._ledger.session()
        await s1.begin("READ COMMITTED")
        await s2.begin("READ COMMITTED")
        b1 = await s1.read_balance(self.ACCOUNT)   # 100
        b2 = await s2.read_balance(self.ACCOUNT)   # 100 (stale snapshot of the value)
        await s1.write_balance(self.ACCOUNT, b1 - 10)  # -> 90
        await s1.commit()
        await s2.write_balance(self.ACCOUNT, b2 - 20)  # -> 80, computed from stale 100
        await s2.commit()
        await s1.close()
        await s2.close()
        final = await self._ledger.read_balance(self.ACCOUNT)
        return AnomalyResult(
            "Lost update", "READ COMMITTED", final, self.START - 30, prevented=final == 70,
            note="both read 100 then wrote; s1's −10 is overwritten and lost",
        )

    async def run_fixed(self) -> AnomalyResult:
        await self._ledger.reset_balance(self.ACCOUNT, self.START)
        s1, s2 = self._ledger.session(), self._ledger.session()
        await s1.begin("READ COMMITTED")
        await s2.begin("READ COMMITTED")
        b1 = await s1.read_balance(self.ACCOUNT, lock=True)  # 100, row locked
        # s2's locking read must wait for s1 to release the lock.
        read2 = asyncio.create_task(s2.read_balance(self.ACCOUNT, lock=True))
        await asyncio.sleep(0.2)
        blocked = not read2.done()
        await s1.write_balance(self.ACCOUNT, b1 - 10)  # -> 90
        await s1.commit()                              # releases the lock
        b2 = await read2                               # unblocks, re-reads 90
        await s2.write_balance(self.ACCOUNT, b2 - 20)  # -> 70
        await s2.commit()
        await s1.close()
        await s2.close()
        final = await self._ledger.read_balance(self.ACCOUNT)
        blocked_note = "s2's read blocked until s1 committed" if blocked else "serialized"
        return AnomalyResult(
            "Lost update", "READ COMMITTED + FOR UPDATE", final, self.START - 30,
            prevented=final == 70, note=f"FOR UPDATE — {blocked_note}",
        )


class WriteSkewExperiment:
    """Two on-call doctors each check 'is anyone else on call?', see the other,
    and both go off. Snapshot isolation permits it (different rows); only
    SERIALIZABLE detects the read-write cycle and aborts one."""

    DOCTORS = {"alice": True, "bob": True}

    def __init__(self, ledger: Ledger) -> None:
        self._ledger = ledger

    async def run_anomaly(self) -> AnomalyResult:
        await self._ledger.reset_on_call(self.DOCTORS)
        s1, s2 = self._ledger.session(), self._ledger.session()
        await s1.begin("REPEATABLE READ")
        await s2.begin("REPEATABLE READ")
        if await s1.count_on_call() >= 2:
            await s1.set_on_call("alice", False)
        if await s2.count_on_call() >= 2:
            await s2.set_on_call("bob", False)
        await s1.commit()
        await s2.commit()
        await s1.close()
        await s2.close()
        final = await self._ledger.count_on_call()
        return AnomalyResult(
            "Write skew", "REPEATABLE READ", final, 1, prevented=final >= 1,
            note="both saw 2 on call, both went off; constraint (≥1) now violated",
        )

    async def run_fixed(self) -> AnomalyResult:
        await self._ledger.reset_on_call(self.DOCTORS)
        s1, s2 = self._ledger.session(), self._ledger.session()
        await s1.begin("SERIALIZABLE")
        await s2.begin("SERIALIZABLE")
        if await s1.count_on_call() >= 2:
            await s1.set_on_call("alice", False)
        if await s2.count_on_call() >= 2:
            await s2.set_on_call("bob", False)
        await s1.commit()
        conflicts = 0
        try:
            await s2.commit()
        except SerializationConflict:
            conflicts = 1
            await s2.rollback()
            await s2.begin("SERIALIZABLE")  # retry: re-read fresh state and re-decide
            if await s2.count_on_call() >= 2:
                await s2.set_on_call("bob", False)
            await s2.commit()
        await s1.close()
        await s2.close()
        final = await self._ledger.count_on_call()
        return AnomalyResult(
            "Write skew", "SERIALIZABLE (+retry)", final, 1, prevented=final >= 1,
            note=f"SSI aborted s2 (40001); retry re-read 1 on call and refused ({conflicts} conflict)",
        )
