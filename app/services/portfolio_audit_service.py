"""持仓体检服务：对现有持仓做确定性健康诊断，区分 存量体检 vs 增量探索"""

from typing import Dict, List, Any
from datetime import datetime, timezone

HEALTH_EMOJI_MAP = {"float": "🔴", "pare": "🟡", "ok": "🟢", "good": "⭐"}


def audit_position(pos: Dict[str, Any]) -> Dict[str, Any]:
    """对单只持仓做健康体检，返回确定性诊断数据"""
    pnl_pct = pos.get("pnl_pct", 0) or 0
    pnl_cny = pos.get("pnl_cny", 0) or 0
    weight = pos.get("weight", 0) or 0
    avg_cost = pos.get("avg_cost", 0) or 0
    last_price = pos.get("last_price", 0) or 0

    if pnl_pct <= -20:
        health = "float"
    elif pnl_pct < -5:
        health = "pare"
    elif pnl_pct < 10:
        health = "ok"
    else:
        health = "good"

    cost_ratio = round(pnl_pct / 100 * weight, 2)

    return {
        "code": pos.get("code", ""),
        "name": pos.get("name", ""),
        "instrument_type": pos.get("instrument_type", "stock"),
        "health": health,
        "pnl_pct": round(pnl_pct, 1),
        "pnl_cny": round(pnl_cny, 0),
        "avg_cost": avg_cost,
        "last_price": last_price,
        "weight": weight,
        "cost_ratio": cost_ratio,
        "buy_date": pos.get("buy_date", ""),
    }


def audit_positions(positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """对全部持仓做健康体检"""
    return [audit_position(p) for p in positions]


def format_audit_context(audit_results: List[Dict[str, Any]]) -> str:
    """将体检结果格式化为 CIO prompt 可用的上下文"""
    parts = ["## 📋 持仓体检报告\n"]
    parts.append("| 代码 | 名称 | 健康分 | 浮盈% | 浮盈¥ | 仓位% | 对组合贡献 |")
    parts.append("|------|------|--------|-------|-------|-------|-----------|")
    for a in audit_results:
        symbol = a["code"]
        name = a["name"]
        health_label = {"float": "🔴 套牢", "pare": "🟡 减仓", "ok": "🟢 正常", "good": "⭐ 盈利"}.get(a["health"], "?")
        cost_sign = "+" if a["cost_ratio"] >= 0 else ""
        parts.append(
            f"| {symbol} | {name} | {health_label} | {a['pnl_pct']:+.1f}% | "
            f"¥{a['pnl_cny']:,.0f} | {a['weight']:.1f}% | {cost_sign}{a['cost_ratio']:.2f}pp |"
        )
    return "\n".join(parts)


def format_position_summary_for_cio(positions: List[Dict[str, Any]], audit_map: Dict[str, Dict[str, Any]]) -> str:
    """为 CIO prompt 生成增强版持仓摘要（含成本/P&L/健康分）"""
    lines = []
    for pos in positions:
        code = pos.get("code", "?")
        name = pos.get("name", "?")
        instr = pos.get("instrument_type", "stock")
        weight = pos.get("weight", 0)
        mv = pos.get("market_value_cny", 0)

        aud = audit_map.get(code, {})
        avg_cost = aud.get("avg_cost", 0)
        last_price = aud.get("last_price", 0)
        pnl_pct = aud.get("pnl_pct", 0)
        pnl_cny = aud.get("pnl_cny", 0)
        health = aud.get("health", "ok")
        buy_date = aud.get("buy_date", "")

        health_emoji = HEALTH_EMOJI_MAP.get(health, "⚪")

        line = (
            f"- {code} {name} ({instr}): 仓位 {weight:.1f}%, 市值 ¥{mv:,.0f}\n"
            f"  成本 ¥{avg_cost} → 现价 ¥{last_price}, 浮{'+' if pnl_pct >= 0 else ''}{pnl_pct:.1f}% "
            f"(¥{pnl_cny:+,.0f})"
        )
        if buy_date:
            line += f", 买入 {buy_date}"
        line += f"\n  健康分: {health_emoji} {health}"
        lines.append(line)
    return "\n".join(lines)
