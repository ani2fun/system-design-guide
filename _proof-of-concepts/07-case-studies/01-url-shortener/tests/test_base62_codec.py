"""Pure unit tests for Base62Codec — no I/O, runnable with plain python.

    python3 tests/test_base62_codec.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from domain.base62_codec import Base62Codec  # noqa: E402


def test_roundtrip():
    for n in [0, 1, 61, 62, 63, 1000, 999_999, 1_000_000, 3_521_614_606_207]:
        assert Base62Codec.decode(Base62Codec.encode(n)) == n, n


def test_monotonic_lengths():
    # Codes stay short: a 7-char base62 code covers > 3.5 trillion ids.
    assert len(Base62Codec.encode(1_000_000)) == 4
    assert len(Base62Codec.encode(62**7 - 1)) == 7


def test_zero_and_base():
    assert Base62Codec.encode(0) == "0"
    assert Base62Codec.encode(62) == "10"


def test_invalid_char():
    try:
        Base62Codec.decode("abc!")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError on invalid char")


def test_negative_rejected():
    try:
        Base62Codec.encode(-1)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError on negative id")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"PASS  {len(fns)} base62 unit tests")
