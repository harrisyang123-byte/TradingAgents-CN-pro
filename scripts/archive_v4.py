#!/usr/bin/env python3
"""archive_v4.py — v4 单元历史归档与跨轮结论对比

为什么要它：单元信封是覆盖式写入（重跑 version+1 原地覆盖），旧结论只剩 git 历史、
前端不可见。本工具把"按单元留版本"显式化，让用户能对比"equity 这次 vs 上次怎么变、
为什么变"，据此调整模型。

归档落点：data/v4/_archive/<unit路径目录>/<stem>/v<version>_<日期>.json（随 git 传输）。
覆盖前的自动留底由 v4_unit_store.write_unit(archive=True) 完成；本 CLI 负责：
  - baseline  把当前全部已落盘单元快照为基准版本（首轮用一次）
  - snapshot  手动归档某单元当前版本
  - list      列出某单元的全部历史版本
  - diff      并排对比某单元两版结论（stance/direction/配比/评级等），高亮变化

用法：
  python scripts/archive_v4.py baseline
  python scripts/archive_v4.py list asset:equity
  python scripts/archive_v4.py snapshot asset:equity
  python scripts/archive_v4.py diff asset:equity                 # 最近归档版 vs 当前实时
  python scripts/archive_v4.py diff asset:equity --from v1 --to v2
"""

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from app.services.v4 import v4_unit_store as store  # noqa: E402


# ── 结论摘要抽取（跨单元类型通用） ─────────────────────────────────────
def _conclusion(env):
    """从信封 payload 抽取"可对比的结论字段"，兼容研究/配比/个股单元。"""
    p = env.get("payload", {}) or {}
    out = {}
    v = p.get("verdict")
    if isinstance(v, dict):  # 研究/方案单元
        for k in ("stance", "direction", "trend_advice", "confidence"):
            if v.get(k) is not None:
                out[k] = v.get(k)
    # 配比单元 / 个股单元的关键结论字段
    for k in ("current_weight", "equity_quota", "target_allocation", "allocations",
              "industry_weights", "stock_weights", "weights", "rating", "target_price",
              "vitality_level", "go_nogo", "direction"):
        if k in p and p[k] is not None:
            out.setdefault(k, p[k])
    return out


def _meta(env):
    return {
        "version": env.get("version"),
        "status": env.get("status"),
        "generated_at": env.get("generated_at"),
        "run_mode": env.get("run_mode"),
    }


def _fmt(val):
    if isinstance(val, (dict, list)):
        return json.dumps(val, ensure_ascii=False)
    return str(val)


# ── 版本加载 ───────────────────────────────────────────────────────────
def _load_ref(unit_id, ref):
    """ref: 'current'/'live' → 当前实时；'vN'/'N' → 归档版本号；否则当文件名。"""
    if ref in (None, "current", "live", "now"):
        env = store.read_unit(unit_id)
        return env, "current(live)"
    archives = store.list_archive(unit_id)
    norm = ref[1:] if ref.startswith("v") else ref
    # 匹配 v<N>_ 前缀，多个取最后（同版本同日多跑）
    matches = [p for p in archives if p.name.startswith(f"v{norm}_")]
    if matches:
        f = matches[-1]
        return json.loads(f.read_text(encoding="utf-8")), f.name
    # 直接当文件名
    for p in archives:
        if p.name == ref:
            return json.loads(p.read_text(encoding="utf-8")), p.name
    return None, ref


# ── 子命令 ─────────────────────────────────────────────────────────────
def cmd_baseline(_args):
    idx = store.load_index().get("units", {})
    if not idx:
        print("索引为空，无单元可快照。")
        return 0
    n = 0
    for uid in sorted(idx):
        env = store.read_unit(uid)
        if env is None:
            continue
        dest = store.archive_existing(uid, env)
        if dest:
            n += 1
            print(f"  ✓ {uid:<32} → {dest.relative_to(store.data_root())}")
    print(f"\nbaseline 完成：{n} 个单元已快照到 _archive/")
    return 0


def cmd_snapshot(args):
    dest = store.archive_existing(args.unit_id)
    if dest is None:
        print(f"单元 {args.unit_id} 当前无落盘文件，跳过。")
        return 1
    print(f"✓ {args.unit_id} → {dest.relative_to(store.data_root())}")
    return 0


def cmd_list(args):
    archives = store.list_archive(args.unit_id)
    if not archives:
        print(f"单元 {args.unit_id} 暂无归档历史。")
        return 0
    print(f"{args.unit_id} 历史版本（{len(archives)} 个）：")
    for p in archives:
        try:
            env = json.loads(p.read_text(encoding="utf-8"))
            m = _meta(env)
            print(f"  {p.name:<24} v{m['version']} {m['status']} {m['generated_at']} ({m['run_mode']})")
        except (OSError, ValueError):
            print(f"  {p.name}  (读取失败)")
    return 0


def cmd_diff(args):
    # 默认：最近归档版（from）vs 当前实时（to）
    if args.from_ref is None:
        archives = store.list_archive(args.unit_id)
        if not archives:
            print(f"单元 {args.unit_id} 无归档历史，无法对比。先 baseline 或重跑一次产生历史。")
            return 1
        args.from_ref = archives[-1].name
    to_ref = args.to_ref or "current"

    env_a, label_a = _load_ref(args.unit_id, args.from_ref)
    env_b, label_b = _load_ref(args.unit_id, to_ref)
    if env_a is None or env_b is None:
        print(f"加载失败：from={label_a}({'OK' if env_a else '缺'}) to={label_b}({'OK' if env_b else '缺'})")
        return 1

    ma, mb = _meta(env_a), _meta(env_b)
    ca, cb = _conclusion(env_a), _conclusion(env_b)

    print(f"\n=== {args.unit_id} 结论对比 ===")
    print(f"  [A] {label_a}: v{ma['version']} {ma['status']} {ma['generated_at']}")
    print(f"  [B] {label_b}: v{mb['version']} {mb['status']} {mb['generated_at']}")
    print("-" * 64)

    keys = sorted(set(ca) | set(cb))
    if not keys:
        print("  （两版均无可对比的结论字段）")
        return 0
    changed = 0
    for k in keys:
        va, vb = ca.get(k), cb.get(k)
        mark = "  " if va == vb else "▶ "
        if va != vb:
            changed += 1
        print(f"{mark}{k}:")
        print(f"     A: {_fmt(va)}")
        print(f"     B: {_fmt(vb)}")
    print("-" * 64)
    print(f"  共 {len(keys)} 个结论字段，其中 {changed} 个发生变化（▶ 标记）。")
    return 0


def main():
    ap = argparse.ArgumentParser(description="v4 单元历史归档与跨轮结论对比")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("baseline", help="把当前全部单元快照为基准版本")

    s_snap = sub.add_parser("snapshot", help="手动归档某单元当前版本")
    s_snap.add_argument("unit_id")

    s_list = sub.add_parser("list", help="列出某单元的全部历史版本")
    s_list.add_argument("unit_id")

    s_diff = sub.add_parser("diff", help="并排对比某单元两版结论")
    s_diff.add_argument("unit_id")
    s_diff.add_argument("--from", dest="from_ref", default=None, help="基准版本：vN / 文件名（默认最近归档版）")
    s_diff.add_argument("--to", dest="to_ref", default=None, help="对比版本：vN / current（默认当前实时）")

    args = ap.parse_args()
    return {
        "baseline": cmd_baseline,
        "snapshot": cmd_snapshot,
        "list": cmd_list,
        "diff": cmd_diff,
    }[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
