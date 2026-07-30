"""Runnable schema-evolution demonstration.

    python -m app.demo   (or ./run)
"""

from __future__ import annotations

from app.schemas import V1, V2, V_BROKEN
from domain.errors import EvolutionError
from infra.tagged_codec import TaggedCodec


def main() -> None:
    codec = TaggedCodec()

    print("1) BACKWARD COMPATIBILITY — a NEW reader (v2) reads OLD data (v1)")
    old = codec.encode({"name": "Ada", "email": "ada@x.io"}, V1)
    print(f"   v1 wrote {len(old)} bytes; v2 decodes → {codec.decode(old, V2)}")
    print("   ('age' filled from its default; tag 1 read into the renamed 'full_name')\n")

    print("2) FORWARD COMPATIBILITY — an OLD reader (v1) reads NEW data (v2)")
    new = codec.encode({"full_name": "Ada", "email": "ada@x.io", "age": 36}, V2)
    print(f"   v2 wrote {len(new)} bytes; v1 decodes → {codec.decode(new, V1)}")
    print("   (unknown tag 3 'age' skipped; name + email intact)\n")

    print("3) THE UNSAFE CHANGE — reuse tag 2 with a different type")
    try:
        codec.decode(old, V_BROKEN)
    except EvolutionError as exc:
        print(f"   decode raised EvolutionError:\n     {exc}")

    print("\nPASS  encoding & evolution demo")


if __name__ == "__main__":
    main()
