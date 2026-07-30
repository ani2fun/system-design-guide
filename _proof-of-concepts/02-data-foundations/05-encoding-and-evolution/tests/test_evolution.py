"""Unit tests for schema evolution.

    python tests/test_evolution.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.schemas import V1, V2, V_BROKEN  # noqa: E402
from domain.errors import EvolutionError  # noqa: E402
from infra.tagged_codec import TaggedCodec  # noqa: E402

CODEC = TaggedCodec()


def test_roundtrip_same_schema() -> None:
    data = CODEC.encode({"name": "Ada", "email": "ada@x.io"}, V1)
    assert CODEC.decode(data, V1) == {"name": "Ada", "email": "ada@x.io"}


def test_backward_new_reader_old_data() -> None:
    old = CODEC.encode({"name": "Ada", "email": "ada@x.io"}, V1)
    got = CODEC.decode(old, V2)
    assert got["full_name"] == "Ada"     # tag 1, renamed
    assert got["email"] == "ada@x.io"
    assert got["age"] == 0               # missing → default


def test_forward_old_reader_new_data() -> None:
    new = CODEC.encode({"full_name": "Ada", "email": "ada@x.io", "age": 36}, V2)
    got = CODEC.decode(new, V1)
    assert got == {"name": "Ada", "email": "ada@x.io"}   # age (tag 3) skipped


def test_reusing_a_tag_with_new_type_raises() -> None:
    old = CODEC.encode({"name": "Ada", "email": "ada@x.io"}, V1)
    try:
        CODEC.decode(old, V_BROKEN)
    except EvolutionError:
        return
    raise AssertionError("expected EvolutionError on a reused tag with a new type")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"PASS  {len(fns)} evolution tests")
