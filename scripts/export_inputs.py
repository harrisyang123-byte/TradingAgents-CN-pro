#!/usr/bin/env python3
"""export_inputs.py — 本地导出文件总线输入（B 档）

在你的本地机器上运行（需 MongoDB），把组合分析所需的三类输入导出成 JSON，
供 collect_data.py 的「文件输入模式」（--portfolio-file ...）消费。这样 Pod 端
不连你的 Mongo 也能采数分析。导出物与 collect 文件模式的契约严格对称：

    holdings.json        持仓（含 industry，scan pool 依赖）+ 现金/总资产  → --portfolio-file
    watchlist.json       关注行业列表                                    → --watchlist-file
    tier1_reports.json   持仓个股的深度分析摘要（可空）                   → --tier1-file

用法（本地，连 Mongo）:
    python scripts/export_inputs.py --user-id <24hex> [--out-dir data/_inputs]

只读你自己的持仓库，不改任何数据。导出的 holdings.json 含敏感财务信息，
默认写到 data/_inputs/（已在 .gitignore 保护），别推公开库。
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


async def export_all(user_id: str, out_dir: Path) -> bool:
    out_dir.mkdir(parents=True, exist_ok=True)

    from app.core.database import init_database, get_mongo_db
    from app.services.portfolio_service import PortfolioService
    await init_database()
    db = get_mongo_db()

    # —— 1. 持仓 holdings.json ——
    print("  [1/3] 导出持仓...")
    svc = PortfolioService()
    summary = await svc.get_portfolio_summary(user_id)
    positions = summary.get("positions", [])
    if not positions:
        print("  错误: 当前用户无持仓，无法导出")
        return False

    # get_portfolio_summary 的 position_details 可能不带 industry（scan pool 依赖它）；
    # 从 paper_positions 补 code→industry，保证文件模式扫描池能正确分组。
    pos_docs = await db["paper_positions"].find({"user_id": user_id}).to_list(None)
    code_to_industry = {
        d.get("code", ""): d.get("industry", "")
        for d in pos_docs if d.get("code")
    }
    for p in positions:
        if not p.get("industry"):
            p["industry"] = code_to_industry.get(p.get("code", ""), "")

    holdings = {
        "exported_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": "export_inputs",
        "user_id": user_id,
        "available_cash": summary.get("available_cash", 0),
        "total_assets": summary.get("total_assets", 0),
        "position_count": len(positions),
        "positions": positions,
    }
    _dump(out_dir / "holdings.json", holdings)
    print(f"    {len(positions)} 只持仓 → holdings.json")

    # —— 2. watchlist.json ——
    print("  [2/3] 导出关注行业...")
    wl_docs = await db["watchlist"].find({"user_id": user_id}).to_list(None)
    watchlist = [d["industry"] for d in wl_docs if d.get("industry")]
    _dump(out_dir / "watchlist.json", watchlist)
    print(f"    {len(watchlist)} 个关注行业 → watchlist.json")

    # —— 3. tier1_reports.json（持仓个股深度分析摘要，可空）——
    # 查询与 collect_data.py Mongo 模式完全一致，保证两路 Tier1 数据同构。
    print("  [3/3] 导出 Tier1 报告...")
    position_codes = [p.get("code", p.get("stock_code", "")) for p in positions]
    reports = []
    for code in position_codes:
        if not code:
            continue
        doc = await db["analysis_reports"].find_one(
            {"$and": [
                {"$or": [{"stock_symbol": code}, {"stock_code": code}]},
                {"stock_symbol": {"$ne": "?"}},
                {"status": "completed"},
            ]},
            sort=[("created_at", -1)],
        )
        if not doc:
            doc = await db["analysis_results"].find_one(
                {"$or": [{"stock_code": code}, {"stock_symbol": code}]},
                sort=[("created_at", -1)],
            )
        if doc:
            reports.append({
                "code": doc.get("stock_symbol") or doc.get("stock_code", code),
                "name": doc.get("stock_name", ""),
                "instrument_type": doc.get("instrument_type", "stock"),
                "recommendation": str(doc.get("recommendation", "") or doc.get("rating", ""))[:200],
                "summary": str(doc.get("summary", "") or doc.get("final_decision", ""))[:500],
                "risk_level": doc.get("risk_level", ""),
                "confidence": doc.get("confidence_score", 0),
                "created_at": str(doc.get("created_at", ""))[:19],
            })
    _dump(out_dir / "tier1_reports.json", reports)
    print(f"    {len(reports)} 份 Tier1 报告 → tier1_reports.json")

    print(f"\n  ✅ 已导出到 {out_dir}/")
    print(f"     传到 Pod 后用: python scripts/collect_data.py \\")
    print(f"       --user-id {user_id} --out-dir <run_dir> \\")
    print(f"       --portfolio-file {out_dir}/holdings.json \\")
    print(f"       --watchlist-file {out_dir}/watchlist.json \\")
    print(f"       --tier1-file {out_dir}/tier1_reports.json")
    return True


def _dump(path: Path, obj) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, default=str)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export file-bus inputs from local MongoDB")
    parser.add_argument("--user-id", required=True, help="User ID (24-char hex)")
    parser.add_argument("--out-dir", default="data/_inputs",
                        help="导出目录（默认 data/_inputs，已在 .gitignore 保护）")
    args = parser.parse_args()

    if not (len(args.user_id) == 24 and all(c in "0123456789abcdef" for c in args.user_id.lower())):
        print("错误: Invalid user_id format: must be 24-character hex string")
        sys.exit(1)

    ok = asyncio.run(export_all(args.user_id, Path(args.out_dir)))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
