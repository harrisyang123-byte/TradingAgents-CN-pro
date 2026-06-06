#!/usr/bin/env python3
"""stage_cache.py — v3 增量编排器的阶段缓存门

每个阶段产物旁写一个 `<output>.meta.json`：
    { "stage", "ts", "ttl_days", "fingerprint", "inputs" }

新鲜度判定（FRESH 才能跳过）：
    1. 产物文件存在
    2. meta 存在且 fingerprint 与当前输入一致（输入内容变了即失效）
    3. ttl_days > 0 且 now - ts < ttl_days（ttl_days<=0 视为永不缓存）

用法:
    # 判定（输出 FRESH / STALE 到 stdout，退出码 0）
    python scripts/stage_cache.py check  --stage industry \
        --out <dir>/industry_allocations.json \
        --inputs "<dir>/macro_verdict.json,<dir>/industry_list.json" \
        --ttl-days 7

    # 盖戳（阶段跑完后写 meta）
    python scripts/stage_cache.py stamp  --stage industry \
        --out <dir>/industry_allocations.json \
        --inputs "<dir>/macro_verdict.json,<dir>/industry_list.json" \
        --ttl-days 7

    # 失效（删除 meta，可选 --drop-output 同时删产物）
    python scripts/stage_cache.py invalidate --out <dir>/industry_allocations.json
"""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import List


def _meta_path(out: str) -> Path:
    return Path(out + ".meta.json")


def _split_inputs(inputs: str) -> List[str]:
    if not inputs:
        return []
    return [s.strip() for s in inputs.split(",") if s.strip()]


def _fingerprint(inputs: List[str]) -> str:
    """对所有输入文件内容做 sha256，缺失文件以占位符计入（缺失也是一种状态）。"""
    h = hashlib.sha256()
    for path in inputs:
        p = Path(path)
        h.update(path.encode("utf-8"))
        h.update(b"\x00")
        if p.exists() and p.is_file():
            try:
                h.update(p.read_bytes())
            except OSError:
                h.update(b"<unreadable>")
        else:
            h.update(b"<missing>")
        h.update(b"\x01")
    return h.hexdigest()


def cmd_check(args) -> int:
    out = Path(args.out)
    meta = _meta_path(args.out)
    ttl_days = float(args.ttl_days)
    inputs = _split_inputs(args.inputs)

    # ttl<=0 → 永不缓存，永远 STALE
    if ttl_days <= 0:
        print("STALE")
        return 0

    if not out.exists():
        print("STALE")
        return 0
    if not meta.exists():
        print("STALE")
        return 0

    try:
        m = json.loads(meta.read_text())
    except (OSError, ValueError):
        print("STALE")
        return 0

    # 指纹比对
    if m.get("fingerprint") != _fingerprint(inputs):
        print("STALE")
        return 0

    # TTL 比对
    age_days = (time.time() - float(m.get("ts", 0))) / 86400.0
    if age_days >= ttl_days:
        print("STALE")
        return 0

    print("FRESH")
    return 0


def cmd_stamp(args) -> int:
    meta = _meta_path(args.out)
    inputs = _split_inputs(args.inputs)
    payload = {
        "stage": args.stage,
        "ts": time.time(),
        "ttl_days": float(args.ttl_days),
        "fingerprint": _fingerprint(inputs),
        "inputs": inputs,
        "stamped_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
    }
    meta.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"STAMPED {args.stage} -> {meta}")
    return 0


def cmd_invalidate(args) -> int:
    meta = _meta_path(args.out)
    if meta.exists():
        meta.unlink()
        print(f"INVALIDATED {meta}")
    else:
        print(f"NOMETA {meta}")
    if args.drop_output:
        out = Path(args.out)
        if out.exists():
            out.unlink()
            print(f"DROPPED {out}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="v3 阶段缓存门")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check")
    c.add_argument("--stage", required=True)
    c.add_argument("--out", required=True)
    c.add_argument("--inputs", default="")
    c.add_argument("--ttl-days", default="0")
    c.set_defaults(func=cmd_check)

    s = sub.add_parser("stamp")
    s.add_argument("--stage", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--inputs", default="")
    s.add_argument("--ttl-days", default="0")
    s.set_defaults(func=cmd_stamp)

    i = sub.add_parser("invalidate")
    i.add_argument("--stage", default="")
    i.add_argument("--out", required=True)
    i.add_argument("--inputs", default="")
    i.add_argument("--drop-output", action="store_true")
    i.set_defaults(func=cmd_invalidate)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
