# POC: Encoding & schema evolution

A dependency-free, from-first-principles demonstration for the
`data-foundations/encoding-and-evolution` lesson. It implements a tiny
**tag/type/value binary codec** — the essence of Protobuf/Thrift — and uses it
to show why *numeric field tags* are what let a schema evolve without a
flag-day: writers and readers on different versions keep understanding each
other.

No Docker, no external formats, ~60 lines of codec.

| Piece | File | Role |
| --- | --- | --- |
| `Schema` / `Field` | [`domain/model.py`](domain/model.py) | ordered, tagged fields; a tag is the stable identity |
| `Codec` (port) | [`domain/ports.py`](domain/ports.py) | encode(record, schema) / decode(bytes, reader) |
| `TaggedCodec` | [`infra/tagged_codec.py`](infra/tagged_codec.py) | the Protobuf-style `[tag][type][value]` wire format |

## Run it

```bash
./run            # the three evolution scenarios
./run test       # mypy --strict + unit tests + demo
```

A [`uv`](https://docs.astral.sh/uv/) project (standard library only; `mypy` is
the one dev dependency).

## The three scenarios

1. **Backward compatibility** — a **new** reader (v2, which added an `age` field
   on a new tag) reads **old** data (v1). The missing `age` is filled from its
   default; a field renamed but kept on the same tag still reads correctly.
2. **Forward compatibility** — an **old** reader (v1) reads **new** data (v2).
   The unknown tag (`age`) is simply skipped; the fields it knows are intact.
3. **The unsafe change** — reusing an existing tag for a *different type* is the
   one move evolution can't survive; decoding raises `EvolutionError`. The rule
   that falls out: add fields on new tags, give them defaults, and **never reuse
   a tag**.

Real systems (Avro, Protobuf, Thrift) implement these same rules with more
machinery — writer/reader schema resolution, varint tags, default values — but
the mechanism is exactly this.
