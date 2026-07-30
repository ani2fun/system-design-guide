"""Domain errors for schema evolution."""


class EvolutionError(Exception):
    """An incompatible schema change — e.g. a tag reused with a different type."""
