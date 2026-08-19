"""Domain errors."""


class DomainError(Exception):
    """Base class for payment-domain errors."""


class IllegalTransition(DomainError):
    """A payment-intent transition the state machine doesn't allow."""


class UnbalancedPostings(DomainError):
    """Double-entry postings that don't sum to zero."""
