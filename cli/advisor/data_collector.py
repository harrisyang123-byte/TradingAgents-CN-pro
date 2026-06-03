"""数据收集模块 — 被 claude_advisor.py 主控调用"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger("claude-advisor")
DATA_DIR = Path("/tmp/claude_advisor")


async def ensure_db():
    from app.core.database import init_database
    await init_database()


async def collect_portfolio(user_id: str) -> Dict[str, Any]:
    """收集持仓数据"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    from app.services.portfolio_service import PortfolioService
    await ensure_db()
    svc = PortfolioService()
    s = await svc.get_portfolio_summary(user_id)
    json.dump(s, open(DATA_DIR / "portfolio.json", "w"), ensure_ascii=False, default=str)
    positions = s.get("positions", [])
    cash = s.get("available_cash", 0)
    total = s.get("total_assets", 1)
    logger.info(f"持仓: {len(positions)} 只, 总资产: ¥{total:.0f}, 现金: {cash:.0f} ({cash/total*100:.0f}%)")
    return {"position_count": len(positions), "total_assets": total, "cash_ratio": round(cash / max(total, 1) * 100, 1)}


async def collect_tier1(position_codes: List[str]) -> List[Dict]:
    """收集 Tier1 报告"""
    from app.core.database import get_mongo_db
    await ensure_db()
    db = get_mongo_db()
    reports = []

    for code in position_codes:
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

    json.dump(reports, open(DATA_DIR / "tier1.json", "w"), ensure_ascii=False)
    logger.info(f"Tier1: {len(reports)} 份")
    return reports


async def collect_exposure(user_id: str) -> Dict:
    """收集敞口矩阵"""
    from app.services.portfolio_service import PortfolioService
    from app.services.exposure_service import ExposureService
    await ensure_db()
    svc = PortfolioService()
    s = await svc.get_portfolio_summary(user_id)
    m = await ExposureService().compute(s)
    result = {
        "hhi": round(m.hhi or 0, 3) if m else 0,
        "penetration_ratio": round(m.penetration_ratio or 0, 1) if m else 0,
        "exposures": [{"code": e.code, "name": e.name, "direct": round(e.direct_weight, 1),
                       "fund": round(e.fund_derived_weight, 1), "total": round(e.total_weight, 1)}
                      for e in (m.stock_exposures if m else [])],
        "overlaps": [{"name": e.name, "total": round(e.total_weight, 1),
                      "sources": getattr(e, "fund_sources", [])}
                     for e in (m.top_overlaps if m else [])],
    }
    json.dump(result, open(DATA_DIR / "exposure.json", "w"), ensure_ascii=False, default=str)
    return result


async def collect_market_temp() -> Dict:
    """收集市场温度"""
    result = {
        "north_net": 0, "north_days": 0,
        "breadth_signal": "中性", "up_ratio": 50,
        "limit_up": 0, "limit_down": 0,
        "margin_balance": 0, "flow_signal": "中性",
    }
    try:
        from app.services.market_signals import fetch_market_breadth, fetch_north_flow, fetch_margin_data
        breadth, north, margin = await asyncio.gather(
            fetch_market_breadth(), fetch_north_flow(), fetch_margin_data(), return_exceptions=True)
        if isinstance(breadth, dict):
            result["breadth_signal"] = breadth.get("breadth_signal", "中性")
            result["up_ratio"] = breadth.get("up_ratio", 50)
            result["limit_up"] = breadth.get("limit_up", 0)
            result["limit_down"] = breadth.get("limit_down", 0)
        if isinstance(north, dict):
            result["north_net"] = north.get("north_net", 0)
            result["north_days"] = north.get("north_days", 0)
        if isinstance(margin, dict):
            result["margin_balance"] = margin.get("margin_balance", 0)
    except Exception as e:
        logger.warning(f"市场温度采集失败: {e}")

    net = result["north_net"]
    if net > 50: result["flow_signal"] = "大幅流入"
    elif net > 10: result["flow_signal"] = "流入"
    elif net > -10: result["flow_signal"] = "中性"
    elif net > -50: result["flow_signal"] = "流出"
    else: result["flow_signal"] = "大幅流出"

    json.dump(result, open(DATA_DIR / "market_temp.json", "w"), ensure_ascii=False)
    logger.info(f"市场温度: {result['breadth_signal']}, 北向: {result['north_net']}亿")
    return result


async def collect_all(user_id: str) -> None:
    """全量数据收集"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    await collect_portfolio(user_id)
    pf = json.load(open(DATA_DIR / "portfolio.json"))
    codes = [p["code"] for p in pf.get("positions", [])]
    await asyncio.gather(
        collect_tier1(codes),
        collect_exposure(user_id),
        collect_market_temp(),
        return_exceptions=True,
    )
    logger.info("数据收集完成")


async def load_portfolio() -> Dict:
    return json.load(open(DATA_DIR / "portfolio.json"))


async def load_tier1() -> List[Dict]:
    try:
        return json.load(open(DATA_DIR / "tier1.json"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []


async def load_exposure() -> Dict:
    try:
        return json.load(open(DATA_DIR / "exposure.json"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


async def load_market_temp() -> Dict:
    try:
        return json.load(open(DATA_DIR / "market_temp.json"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
