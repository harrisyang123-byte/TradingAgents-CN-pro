#!/usr/bin/env python3
"""build_snapshot_v4.py — v4 单元 → 前端静态快照（FR-009 / NFR4.1）

把 data/v4 单元落盘组装成与 API **完全同构**的静态 JSON，输出到
frontend/public/snapshot/v4/，供前端在 VITE_STATIC_SNAPSHOT=1 时直接 fetch
（无后端 / 无 Mongo 也能看，与走 API 展示一致）。

文件名与 frontend/src/api/portfolioV4.ts loadSnapshot 对齐：
  overview.json            ← build_overview
  units_status.json        ← build_units_status
  asset_<class>.json   ×7  ← build_asset_detail
  industry_<name>.json ×N  ← build_industry_detail（按已落盘 industry 单元）

复用 app/services/v4/v4_query 的同一批纯函数，确保 API/快照零分叉（NFR4.1）。

用法:
  python scripts/build_snapshot_v4.py
  python scripts/build_snapshot_v4.py --out frontend/public/snapshot/v4
"""

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from app.services.v4 import asset_classes as ac  # noqa: E402
from app.services.v4 import v4_query, v4_unit_store as store  # noqa: E402


def _load_units_from_files() -> dict:
    """从 data/v4 落盘读取全部单元 → {unit_id: envelope}（不连 Mongo）。"""
    store.rebuild_index()
    units = {}
    for u in store.list_units():
        env = store.read_unit(u["unit_id"])
        if env and env.get("unit_id"):
            units[env["unit_id"]] = env
    return units


def _write(out_dir: Path, name: str, data) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / name
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


def main() -> int:
    ap = argparse.ArgumentParser(description="v4 静态快照生成")
    ap.add_argument("--out", default="frontend/public/snapshot/v4", help="输出目录")
    args = ap.parse_args()

    out_dir = _REPO / args.out if not Path(args.out).is_absolute() else Path(args.out)
    units = _load_units_from_files()
    if not units:
        print("（data/v4 无单元产物；先 analyze 后再生成快照）")
        # 仍产出空 overview，保证前端不报错
    n = 0

    # overview.json（含 has_data / asset_classes，与路由一致）
    overview = v4_query.build_overview(units)
    overview["has_data"] = bool(units)
    overview["asset_classes"] = ac.ASSET_CLASSES
    _write(out_dir, "overview.json", overview)
    n += 1

    # units_status.json（与 /units/status 一致）
    _write(out_dir, "units_status.json",
           {"units": v4_query.build_units_status(units), "has_data": bool(units)})
    n += 1

    # asset_<class>.json ×7（与 /asset/{class} 一致）
    for cfg in ac.ASSET_CLASSES:
        klass = cfg["key"]
        _write(out_dir, f"asset_{klass}.json", v4_query.build_asset_detail(units, klass))
        n += 1

    # asset_unclassified.json：若存在 unclassified 单元（投顾组合等待穿透敞口），
    # 也生成详情快照，避免前端点击该卡片下钻时 404（与 build_overview 追加卡片对齐）。
    if units.get("asset:unclassified"):
        _write(out_dir, "asset_unclassified.json", v4_query.build_asset_detail(units, "unclassified"))
        n += 1

    # industry_<name>.json（按已落盘 industry 单元，文件名 = 原始行业名，与前端 encodeURIComponent 对齐）
    for uid in units:
        if uid.startswith("industry:"):
            name = uid.split(":", 1)[1]
            _write(out_dir, f"industry_{name}.json", v4_query.build_industry_detail(units, name))
            n += 1

    print(f"✅ v4 静态快照生成完成：{n} 个文件 → {out_dir}")
    print("   前端设 VITE_STATIC_SNAPSHOT=1 即直接 fetch 这些快照（与走 API 同构）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
