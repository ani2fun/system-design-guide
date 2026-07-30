"""Domain errors for the booking critical section."""


class DomainError(Exception):
    """Base class for every error the domain raises."""


class SeatUnavailableError(DomainError):
    """The seat does not exist or is already sold."""
