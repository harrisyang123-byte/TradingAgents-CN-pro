#!/usr/bin/env python3
"""build_snapshot.py — 把一次 v3 运行产物组装成「前端静态快照」

文件总线（B 档）的成品环节：读 data/advisor_runs/<ts>/ 里的产物，
组装出两个与后端 API 响应体 **完全同构** 的 JSON，让前端在
VITE_STATIC_SNAPSHOT=1 时直接 fetch 静态文件、不连后端/Mongo 也能看：

    overview.json       = GET /api/portfolio/overview 的 data 载荷
                          （复刻 app/routers/paper.py 的 v3 矩阵组装路径）
    advice_latest.json  = GET /api/portfolio/advice/latest 的 data 载荷
                          （= ingest_advice.build_doc 的产物，本就是 advice 文档）
    meta.json           = 生成时间 / run ts / 数据质量 / 是否会触发前端降级

纯 stdlib，不连网络 / 不连 Mongo / 不调 LLM —— 复用 ingest_advice.build_doc
（其本身亦为纯 stdlib，仅 _write_mongo 才惰性 import app 模块）。

用法:
    python scripts/build_snapshot.py --data-dir data/advisor_runs/<ts> [--user-id <id>]
    # 默认同时写入  <data-dir>/_snapshot/  与  frontend/public/snapshot/
    python scripts/build_snapshot.py --data-dir <dir> --no-frontend   # 只写 _snapshot/

约束：纯叠加产物，不改任何既有 Mongo / API 链路。前端不设 VITE_STATIC_SNAPSHOT
时行为与现在完全一致（照常走 API 读 Mongo）。
"""

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 复用 ingest 的 build_doc（纯 stdlib）+ 现金行业常量
from scripts.ingest_advice import build_doc, CASH_INDUSTRY  # noqa: E402


def _load(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  警告: 无法解析 {path.name}: {e}")
        return default


def build_overview_payload(advice: Dict[str, Any], data_dir: Path) -> Dict[str, Any]:
    """复刻 paper.py get_portfolio_overview 的 v3 矩阵组装路径。

    后端 v3 路径只依赖 advice 文档 + 持仓总资产，可纯文件复刻，无需 Mongo。
    字段、防御兜底、覆盖计数口径与后端保持一致，保证前端契约不漂移。
    """
    portfolio = _load(data_dir / "data_portfolio.json", {}) or {}
    total_assets = portfolio.get("total_assets", 0) or 0

    matrix: List[Dict[str, Any]] = list(advice.get("industry_matrix", []) or [])
    prescriptions: List[Dict[str, Any]] = advice.get("prescription", []) or []
    code_to_rx: Dict[str, Dict[str, Any]] = {
        rx["code"]: rx for rx in prescriptions if rx.get("code")
    }

    for row in matrix:
        codes = row.get("codes", []) or []
        row["positions_detail"] = [code_to_rx[c] for c in codes if c in code_to_rx]

        # 防御兜底（与后端 A3 一致）：
        # ① go_nogo 统一大写（前端严格判 === 'GO' / 'NOGO'）
        row["go_nogo"] = str(row.get("go_nogo", "") or "").strip().upper()
        # ② source 净化：非白名单一律归 holding
        if str(row.get("source", "")).strip().lower() not in ("holding", "watchlist", "vitality"):
            row["source"] = "holding"
        # ③ delta 缺失按 目标 - 现持仓 补算
        if row.get("delta") is None:
            try:
                row["delta"] = round(
                    float(row.get("target_weight", 0) or 0)
                    - float(row.get("holdings_weight", 0) or 0),
                    2,
                )
            except (TypeError, ValueError):
                row["delta"] = 0.0

    total = len(matrix)
    # 覆盖计数口径与后端 B3 一致
    covered = sum(
        1 for r in matrix
        if r.get("coverage_status") == "covered" or r.get("go_nogo") in ("GO", "NOGO")
    )
    stale = sum(1 for r in matrix if r.get("coverage_status") == "stale")
    never = sum(1 for r in matrix if r.get("coverage_status") == "never")

    return {
        "matrix": matrix,
        "total_industries": total,
        "covered_count": covered,
        "stale_count": stale,
        "never_count": never,
        "latest_advice_at": advice.get("created_at", ""),
        "data_score": advice.get("data_score", 0),
        "total_assets": round(total_assets, 0) if total_assets else 0,
        "asset_allocation": advice.get("asset_allocation"),
    }


def build_meta(advice: Dict[str, Any], overview: Dict[str, Any],
               data_dir: Path) -> Dict[str, Any]:
    """生成快照元信息，并诚实标注前端是否会降级（矩阵为空 = 必降级）。"""
    real_rows = [r for r in overview["matrix"] if r.get("industry") != CASH_INDUSTRY]
    will_degrade = len(real_rows) == 0
    new_positions = [
        p for p in advice.get("prescription", [])
        if p.get("action") in ("buy", "add", "new_position")
    ]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "run_dir": str(data_dir.name),
        "advice_id": advice.get("advice_id", ""),
        "advice_created_at": advice.get("created_at", ""),
        "data_score": advice.get("data_score", 0),
        "total_industries": overview["total_industries"],
        "covered_count": overview["covered_count"],
        "prescription_count": len(advice.get("prescription", [])),
        "new_position_count": len(new_positions),
        # 诚实标注：矩阵为空时前端会降级成「拿持仓拼凑」，只显示历史股
        "frontend_will_degrade": will_degrade,
        "degrade_reason": (
            "industry_matrix 为空 —— synth 可能 fail-closed 吞了矩阵，"
            "前端将降级为持仓拼凑视图（仅历史股，无新推荐）"
            if will_degrade else ""
        ),
    }


def write_snapshot(data_dir: Path, user_id: str, write_frontend: bool = True) -> Dict[str, Any]:
    advice = build_doc(data_dir, user_id)
    overview = build_overview_payload(advice, data_dir)
    meta = build_meta(advice, overview, data_dir)

    # 1. 写入 run 目录下的 _snapshot/（可回溯）
    snap_dir = data_dir / "_snapshot"
    snap_dir.mkdir(parents=True, exist_ok=True)
    _dump(snap_dir / "advice_latest.json", advice)
    _dump(snap_dir / "overview.json", overview)
    _dump(snap_dir / "meta.json", meta)
    print(f"  ✓ 快照已写入 {snap_dir}")

    # 2. 同步到前端可静态加载目录（Vite 把 public/ 映射到根路径 /）
    if write_frontend:
        fe_dir = PROJECT_ROOT / "frontend" / "public" / "snapshot"
        fe_dir.mkdir(parents=True, exist_ok=True)
        for name in ("advice_latest.json", "overview.json", "meta.json"):
            shutil.copyfile(snap_dir / name, fe_dir / name)
        print(f"  ✓ 已同步到前端静态目录 {fe_dir}")
        print(f"     本地: cd frontend && VITE_STATIC_SNAPSHOT=1 npm run dev")

    # 控制台体检摘要
    print(f"  矩阵 {meta['total_industries']} 行业（覆盖 {meta['covered_count']}）, "
          f"处方 {meta['prescription_count']} 条（新建仓 {meta['new_position_count']}）")
    if meta["frontend_will_degrade"]:
        print(f"  ⚠ {meta['degrade_reason']}")
    return meta


def _dump(path: Path, obj: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, default=str)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build static frontend snapshot from a v3 run dir")
    parser.add_argument("--data-dir", required=True, help="v3 运行产物目录 data/advisor_runs/<ts>")
    parser.add_argument("--user-id", default="file-bus", help="用户 ID（仅写入文档元信息，默认 file-bus）")
    parser.add_argument("--no-frontend", action="store_true",
                        help="只写 <data-dir>/_snapshot/，不同步到 frontend/public/snapshot/")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"错误: data-dir 不存在: {data_dir}")
        sys.exit(1)

    write_snapshot(data_dir, args.user_id, write_frontend=not args.no_frontend)


if __name__ == "__main__":
    main()
