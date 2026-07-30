"""ManifestDiffer — which chunks changed since the last version (C4 code element).

Given the new local hash list and the previously-committed remote list, returns
the local hashes that aren't in the remote — the only chunks a delta sync needs
to consider. (Global dedup then trims further: some 'changed' chunks may already
exist on the server from another file.)
"""

from __future__ import annotations


class ManifestDiffer:
    def diff(self, local: list[str], remote: list[str]) -> list[str]:
        remote_set = set(remote)
        seen: set[str] = set()
        changed: list[str] = []
        for h in local:
            if h not in remote_set and h not in seen:
                changed.append(h)
                seen.add(h)
        return changed
