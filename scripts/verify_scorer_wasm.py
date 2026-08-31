"""Inspect WASM exports and, if wasmtime is installed, run the structural gate."""

from __future__ import annotations

import hashlib
import pathlib
import struct
import sys

VALTYPE = {0x7F: "i32", 0x7E: "i64", 0x7D: "f32", 0x7C: "f64"}


def read_u32(buf: bytes, i: int) -> tuple[int, int]:
    n = shift = 0
    while True:
        b = buf[i]
        i += 1
        n |= (b & 0x7F) << shift
        if b & 0x80 == 0:
            return n, i
        shift += 7


def parse_exports(data: bytes) -> dict[str, tuple[str, str]]:
    assert data[:4] == b"\x00asm", "not wasm"
    i = 8
    types: list[tuple[list[str], list[str]]] = []
    functions: list[int] = []
    exports: dict[str, tuple[str, str]] = {}
    while i < len(data):
        sec_id = data[i]
        i += 1
        size, i = read_u32(data, i)
        body = data[i : i + size]
        i += size
        if sec_id == 1:
            count, j = read_u32(body, 0)
            for _ in range(count):
                assert body[j] == 0x60
                j += 1
                nparams, j = read_u32(body, j)
                params = [VALTYPE[body[j + k]] for k in range(nparams)]
                j += nparams
                nrets, j = read_u32(body, j)
                rets = [VALTYPE[body[j + k]] for k in range(nrets)]
                j += nrets
                types.append((params, rets))
        elif sec_id == 3:
            count, j = read_u32(body, 0)
            for _ in range(count):
                idx, j = read_u32(body, j)
                functions.append(idx)
        elif sec_id == 7:
            count, j = read_u32(body, 0)
            for _ in range(count):
                nlen, j = read_u32(body, j)
                name = body[j : j + nlen].decode("utf-8")
                j += nlen
                kind = body[j]
                j += 1
                idx, j = read_u32(body, j)
                if kind == 0:
                    params, rets = types[functions[idx]]
                    sig = f"({','.join(params)}) -> {','.join(rets) or 'void'}"
                    exports[name] = ("func", sig)
                else:
                    exports[name] = ("other", str(kind))
    return exports


def structural_gate(path: pathlib.Path) -> None:
    try:
        from wasmtime import Engine, Linker, Module, Store, MemoryType, Memory, Func, FuncType, ValType
    except Exception as e:
        print("wasmtime_not_installed", e)
        return

    engine = Engine()
    store = Store(engine)
    module = Module.from_file(engine, str(path))
    linker = Linker(engine)
    instance = linker.instantiate(store, module)
    exports = instance.exports(store)
    alloc = exports["alloc"]
    rank = exports["rank_answer"]
    memory = exports["memory"]

    def write(text: str) -> tuple[int, int]:
        raw = text.encode("utf-8")
        ptr = int(alloc(store, len(raw) if raw else 1))
        if raw:
            memory.write(store, raw, ptr)
        return ptr, len(raw)

    def score(q: str, gt: str, ma: str) -> float:
        qp, ql = write(q)
        gp, gl = write(gt)
        mp, ml = write(ma)
        return float(rank(store, qp, ql, gp, gl, mp, ml))

    empty = score("weather in Berlin", "sunny 20C", "")
    ans = "Berlin today: high 17C, overcast, no rain."
    other = "The stock market closed mixed after a volatile session."
    self_s = score("WEATHER_FORECAST for Berlin", ans, ans)
    cross = score("WEATHER_FORECAST for Berlin", ans, other)
    print(f"empty={empty:.4f} self={self_s:.4f} cross={cross:.4f}")
    if empty != 0.0:
        raise SystemExit(f"empty miner must be 0, got {empty}")
    if not (self_s > cross):
        raise SystemExit(f"self-match {self_s} did not beat cross-match {cross}")
    print("structural_gate_ok")


def main() -> None:
    path = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\DELL\Downloads\OnLookout\scorer\target\wasm32-unknown-unknown\release\onlookout_scorer.wasm")
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    print("file", path)
    print("bytes", len(data))
    print("sha256", digest)
    exports = parse_exports(data)
    for name, (kind, sig) in sorted(exports.items()):
        print(f"export {name} {kind} {sig}")
    expected = "(i32,i32,i32,i32,i32,i32) -> f32"
    if "rank_answer" not in exports:
        raise SystemExit("missing rank_answer")
    if exports["rank_answer"][1] != expected:
        raise SystemExit(f"rank_answer signature {exports['rank_answer'][1]} != {expected}")
    if "alloc" not in exports or "dealloc" not in exports:
        raise SystemExit("missing alloc/dealloc")
    print("abi_ok")
    structural_gate(path)


if __name__ == "__main__":
    main()
