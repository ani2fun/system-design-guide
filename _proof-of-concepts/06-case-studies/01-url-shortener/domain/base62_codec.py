"""Base62Codec — pure counter-id ↔ short-code conversion (C4 code element).

No I/O, no state, no ports: a pure domain value transform. `encode` and
`decode` are exact inverses for every non-negative integer.
"""

from __future__ import annotations

_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
_BASE = len(_ALPHABET)  # 62
_INDEX = {c: i for i, c in enumerate(_ALPHABET)}


class Base62Codec:
    @staticmethod
    def encode(n: int) -> str:
        if n < 0:
            raise ValueError("id must be non-negative")
        if n == 0:
            return _ALPHABET[0]
        out: list[str] = []
        while n:
            n, rem = divmod(n, _BASE)
            out.append(_ALPHABET[rem])
        return "".join(reversed(out))

    @staticmethod
    def decode(code: str) -> int:
        n = 0
        for ch in code:
            try:
                n = n * _BASE + _INDEX[ch]
            except KeyError:
                raise ValueError(f"invalid base62 character: {ch!r}") from None
        return n
