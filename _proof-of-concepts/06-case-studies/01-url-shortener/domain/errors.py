"""Domain errors — raised by the domain, translated at the edges (HTTP / adapters).

Keeping these in the domain lets services signal failure without knowing about
HTTP status codes or the specific database driver.
"""


class DomainError(Exception):
    """Base class for every error the domain raises."""


class InvalidURLError(DomainError):
    """The submitted long URL is not a valid absolute http(s) URL."""


class DuplicateCodeError(DomainError):
    """The short code / custom alias is already taken."""
