"""RuleResolver — key → applicable rule (C4 code element).

Rules are matched by key prefix (tier/route) and cached locally, so the decision
path never blocks on the rule store. First matching prefix wins; otherwise the
default.
"""

from __future__ import annotations

from domain.model import Rule


class RuleResolver:
    def __init__(self, rules: list[tuple[str, Rule]], default: Rule) -> None:
        self._rules = rules
        self._default = default

    def resolve(self, key: str) -> Rule:
        for prefix, rule in self._rules:
            if key.startswith(prefix):
                return rule
        return self._default
