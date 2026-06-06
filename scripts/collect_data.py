#!/usr/bin/env python3
"""collect_data.py — 数据收集适配器

用法:
    python scripts/collect_data.py --user-id <id> --out-dir <path>

输出 JSON 文件到指定目录:
    data_portfolio.json, data_tier1.json, data_pe.json,
    data_exposure.json, data_macro.json, data_market_temp.json,
    data_vitality.json (全量18行业景气榜),
    industry_list.json (深辩范围: 持仓+watchlist+景气top3),
    data_scan_pool.json (扫描池来源标注)
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


async def collect_all(user_id: str, out_dir: Path, all_industries: bool = False) -> bool:
    """全量数据收集

    all_industries: 为 True 时，行业扫描池纳入全部可投资行业（全量深辩），
        否则只取 持仓 + watchlist + 景气top3（默认增量范围）。
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    warnings = []

    # —— 1. 持仓数据 ——
    print("  [1/7] 收集持仓数据...")
    try:
        from app.core.database import init_database
        from app.services.portfolio_service import PortfolioService
        await init_database()
        svc = PortfolioService()
        summary = await svc.get_portfolio_summary(user_id)
        positions = summary.get("positions", [])

        if not positions:
            print("  错误: 当前用户无持仓数据，无法进行分析")
            return False

        # 整理持仓数据
        portfolio_data = {
            "collected_at": datetime.now(timezone.utc).isoformat() + "Z",
            "status": "success",
            "user_id": user_id,
            "available_cash": summary.get("available_cash", 0),
            "total_assets": summary.get("total_assets", 0),
            "position_count": len(positions),
            "positions": positions,
        }
        with open(out_dir / "data_portfolio.json", "w") as f:
            json.dump(portfolio_data, f, ensure_ascii=False, default=str)
        cash = summary.get("available_cash", 0)
        total = summary.get("total_assets", 1)
        print(f"    {len(positions)} 只持仓, 总资产 ¥{total:.0f}, 现金 ¥{cash:.0f} ({cash/total*100:.0f}%)")
    except Exception as e:
        print(f"  错误: {e}")
        return False

    # —— 2. Tier1 报告 ——
    print("  [2/7] 收集 Tier1 报告...")
    try:
        from app.core.database import get_mongo_db
        db = get_mongo_db()
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

        with open(out_dir / "data_tier1.json", "w") as f:
            json.dump(reports, f, ensure_ascii=False, default=str)
        print(f"    {len(reports)} 份 Tier1 报告")
    except Exception as e:
        print(f"  警告: Tier1 数据收集失败: {e}")
        warnings.append("Tier1 data partial")
        with open(out_dir / "data_tier1.json", "w") as f:
            json.dump([], f)

    # —— 3. PE 分位数据 ——
    print("  [3/7] 收集 PE 分位数据...")
    pe_data = {}
    try:
        from cli.advisor.data_collector import collect_pe
        position_codes = [p.get("code", p.get("stock_code", "")) for p in positions if p.get("code") or p.get("stock_code")]
        pe_result = await collect_pe(position_codes)
        pe_data = pe_result if isinstance(pe_result, dict) else {}
        with open(out_dir / "data_pe.json", "w") as f:
            json.dump(pe_data, f, ensure_ascii=False, default=str)
        available = sum(1 for v in pe_data.values() if isinstance(v, dict) and v.get("pe_percentile_5y") is not None)
        print(f"    {available}/{len(pe_data)} 只 PE 数据可用")
    except Exception as e:
        print(f"  警告: PE 数据收集失败: {e}")
        warnings.append("PE data partial")
        with open(out_dir / "data_pe.json", "w") as f:
            json.dump({}, f)

    # —— 4. 敞口矩阵 ——
    print("  [4/7] 收集敞口数据...")
    try:
        from app.services.portfolio_service import PortfolioService
        from app.services.exposure_service import ExposureService
        svc2 = PortfolioService()
        s = await svc2.get_portfolio_summary(user_id)
        m = await ExposureService().compute(s)
        exposure = {
            "hhi": round(m.hhi or 0, 3) if m else 0,
            "penetration_ratio": round(m.penetration_ratio or 0, 1) if m else 0,
            "exposures": [{"code": e.code, "name": e.name, "direct": round(e.direct_weight, 1),
                           "fund": round(e.fund_derived_weight, 1), "total": round(e.total_weight, 1)}
                          for e in (m.stock_exposures if m else [])],
            "overlaps": [{"code": e.name, "name": e.name, "overlap_weight": round(e.total_weight, 1),
                          "sources": getattr(e, "fund_sources", [])}
                         for e in (m.top_overlaps if m else [])],
        }
        with open(out_dir / "data_exposure.json", "w") as f:
            json.dump(exposure, f, ensure_ascii=False, default=str)
        print(f"    HHI: {exposure['hhi']}, 穿透率: {exposure['penetration_ratio']}%")
    except Exception as e:
        print(f"  警告: 敞口数据收集失败: {e}")
        warnings.append("Exposure data partial")
        with open(out_dir / "data_exposure.json", "w") as f:
            json.dump({"hhi": 0, "status": "unavailable"}, f)

    # —— 5. 宏观指标 ——
    print("  [5/7] 收集宏观指标 + 行业排名 + 资金流向...")
    macro_data = {"status": "partial", "collected_at": datetime.now(timezone.utc).isoformat() + "Z"}
    try:
        from tradingagents.agents.advisors.market_tools import (
            get_macro_indicators, get_industry_rankings, get_sector_fund_flows)
        macro_data["indicators"] = get_macro_indicators.func() or {}
        macro_data["industry_rankings"] = get_industry_rankings.func() or []
        macro_data["sector_fund_flows"] = get_sector_fund_flows.func() or []
        print(f"    宏观指标: {len(macro_data.get('indicators', {}))} 项, "
              f"行业排名: {len(macro_data.get('industry_rankings', []))} 行业, "
              f"资金流向: {len(macro_data.get('sector_fund_flows', []))} 行业")
    except Exception as e:
        print(f"  警告: 宏观数据收集失败: {e}")
        warnings.append("Macro data partial")

    with open(out_dir / "data_macro.json", "w") as f:
        json.dump(macro_data, f, ensure_ascii=False, default=str)

    # —— 6. 市场温度 ——
    print("  [6/7] 收集市场温度数据...")
    market_temp = {
        "collected_at": datetime.now(timezone.utc).isoformat() + "Z",
        "status": "success",
        "north_net": 0, "north_days": 0,
        "breadth_signal": "中性", "up_ratio": 50,
        "limit_up": 0, "limit_down": 0,
        "margin_balance": 0, "margin_change_pct": 0,
        "flow_signal": "中性",
    }
    try:
        from app.services.market_signals import fetch_market_breadth, fetch_north_flow, fetch_margin_data
        breadth, north, margin = await asyncio.gather(
            fetch_market_breadth(), fetch_north_flow(), fetch_margin_data(), return_exceptions=True)
        if isinstance(breadth, dict):
            market_temp["breadth_signal"] = breadth.get("breadth_signal", "中性")
            market_temp["up_ratio"] = breadth.get("up_ratio", 50)
            market_temp["limit_up"] = breadth.get("limit_up", 0)
            market_temp["limit_down"] = breadth.get("limit_down", 0)
        if isinstance(north, dict):
            market_temp["north_net"] = north.get("net_flow", 0)
            market_temp["north_days"] = north.get("consecutive_days", 0)
            market_temp["north_direction"] = north.get("direction", "中性")
        if isinstance(margin, dict):
            market_temp["margin_balance"] = margin.get("balance", 0)
            market_temp["margin_change_pct"] = margin.get("weekly_change_pct", 0)
        print(f"    水温: {market_temp['breadth_signal']}, 北向: {market_temp.get('north_direction', 'N/A')}, "
              f"融资变化: {market_temp['margin_change_pct']}%")
    except Exception as e:
        print(f"  警告: 市场温度数据收集失败: {e}")
        market_temp["status"] = "partial"
        warnings.append("Market temperature partial")

    with open(out_dir / "data_market_temp.json", "w") as f:
        json.dump(market_temp, f, ensure_ascii=False, default=str)

    # —— 7. 行业扫描池 + 全量景气榜 ——
    # 全量18行业景气打分（廉价雷达，喂前端矩阵）只跑一次，
    # 复用给扫描池构建（深辩范围=持仓+watchlist+景气top3，无估值闸）
    print("  [7/7] 全量景气打分 + 行业扫描池...")
    try:
        from dataclasses import asdict
        from app.core.database import get_mongo_db
        from app.services.industry_vitality import score_all_industries
        from app.services.industry_scan_pool import build_scan_pool

        db = get_mongo_db()
        vitality_scores = await score_all_industries()

        # A 档：全量18行业景气榜 → 前端雷达视图
        vitality_data = {
            "collected_at": datetime.now(timezone.utc).isoformat() + "Z",
            "status": "success",
            "top3": [s.industry for s in vitality_scores if s.top3_flag],
            "scores": [asdict(s) for s in vitality_scores],
        }
        with open(out_dir / "data_vitality.json", "w") as f:
            json.dump(vitality_data, f, ensure_ascii=False, default=str)

        # B 档：扫描池（复用已算好的景气分，避免二次扫描）→ 深辩范围
        pool = await build_scan_pool(db, user_id, vitality_scores=vitality_scores,
                                     all_industries=all_industries)
        industry_list = pool.to_industry_list()

        if industry_list:
            with open(out_dir / "industry_list.json", "w") as f:
                json.dump(industry_list, f, ensure_ascii=False, default=str)
            with open(out_dir / "data_scan_pool.json", "w") as f:
                json.dump(pool.to_dict(), f, ensure_ascii=False, default=str)
            srcs = pool.to_source_map()
            holding_n = sum(1 for v in srcs.values() if v == "holding")
            watch_n = sum(1 for v in srcs.values() if v == "watchlist")
            vit_n = sum(1 for v in srcs.values() if v == "vitality")
            print(f"    景气榜 top3: {vitality_data['top3']}")
            scope_tag = "全量行业深辩" if all_industries else "增量深辩"
            print(f"    深辩范围({scope_tag}) {len(industry_list)} 个行业 "
                  f"(持仓{holding_n} + watchlist{watch_n} + 景气{vit_n})")
        else:
            # 扫描池为空（无持仓行业分类/无watchlist/景气全失败）：
            # 不写 industry_list.json，让编排器命中内置兜底，避免空列表导致行业层空跑
            print("    警告: 扫描池为空，行业层将使用编排器内置兜底列表")
            warnings.append("Scan pool empty")
    except Exception as e:
        print(f"  警告: 行业扫描池/景气榜构建失败: {e}")
        warnings.append("Scan pool partial")

    # 写入警告
    if warnings:
        print(f"\n  ⚠ 数据收集完成但有 {len(warnings)} 个警告: {', '.join(warnings)}")

    return True


def main():
    parser = argparse.ArgumentParser(description="Collect advisor data")
    parser.add_argument("--user-id", required=True, help="User ID (24-char hex)")
    parser.add_argument("--out-dir", required=True, help="Output directory")
    parser.add_argument(
        "--industries", choices=["scope", "all"], default="scope",
        help="深辩范围：scope=持仓+watchlist+景气top3（默认），all=全量可投资行业",
    )
    args = parser.parse_args()

    if not (len(args.user_id) == 24 and all(c in "0123456789abcdef" for c in args.user_id.lower())):
        print(f"错误: Invalid user_id format: must be 24-character hex string")
        sys.exit(1)

    out_dir = Path(args.out_dir)
    success = asyncio.run(collect_all(args.user_id, out_dir, all_industries=(args.industries == "all")))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
