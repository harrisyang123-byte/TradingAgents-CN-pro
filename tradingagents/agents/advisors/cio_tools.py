"""CIO 工具 — 分页读持仓、查 L1/L2、派员工搜索行业、查 ETF、验证权重"""

from langchain_core.tools import tool
import json


def _extract_codes(raw_result, market: str) -> list:
    """从 get_industry_constituents 返回的文本中提取股票代码列表"""
    import re
    text = str(raw_result)
    if market == "cn":
        codes = re.findall(r'\b(\d{6})\b', text)
    elif market == "hk":
        codes = re.findall(r'\b(\d{4,5})\b', text)
    else:
        codes = re.findall(r'\b([A-Z]{2,5})\b', text)
    return list(dict.fromkeys(codes))


def create_cio_tools(state_provider):
    """创建 CIO 工具列表。

    Args:
        state_provider: callable, 返回当前 state dict
    """

    @tool
    def get_position_batch(batch_num: int) -> str:
        """分页读取持仓。batch_num 从 1 开始，每批 10 只。
        返回 JSON: {positions: [...], total: N, batch_num: X, has_more: bool}"""
        state = state_provider()
        positions = state.get("portfolio_summary", {}).get("positions", [])
        audit_list = state.get("audit_results", [])
        audit_map = {}
        if isinstance(audit_list, list):
            for a in audit_list:
                audit_map[a.get("code", "")] = a

        start = (batch_num - 1) * 10
        batch = positions[start:start + 10]
        items = []
        for p in batch:
            code = p.get("code", "?")
            aud = audit_map.get(code, {})
            items.append({
                "code": code,
                "name": p.get("name", ""),
                "instrument_type": p.get("instrument_type", "stock"),
                "weight": round(p.get("weight", 0), 2),
                "market_value_cny": round(p.get("market_value_cny", 0), 0),
                "avg_cost": aud.get("avg_cost", 0),
                "last_price": aud.get("last_price", 0),
                "pnl_pct": round(aud.get("pnl_pct", 0), 1),
                "pnl_cny": round(aud.get("pnl_cny", 0), 0),
                "health": aud.get("health", "ok"),
                "buy_date": aud.get("buy_date", ""),
                "industry": p.get("industry", "未知"),
            })
        return json.dumps({
            "positions": items, "total": len(positions),
            "batch_num": batch_num, "has_more": start + 10 < len(positions),
        }, ensure_ascii=False, indent=2)

    @tool
    def get_l1_verdict(industry: str) -> str:
        """读取某个行业的 L1 宏观裁判结果（Go/NoGo/观察 + 生命周期阶段）。
        返回: {industry, go_nogo, lifecycle, confidence, reasoning}"""
        state = state_provider()
        mi = state.get("market_intel", {})
        industries = mi.get("industries", []) if isinstance(mi, dict) else []
        for ind in industries:
            if isinstance(ind, dict) and ind.get("industry") == industry:
                return json.dumps(ind, ensure_ascii=False, indent=2)
        judge = mi.get("judge_verdict", "") if isinstance(mi, dict) else ""
        msg = {"industry": industry, "go_nogo": "未知",
               "note": "L1 未覆盖此行业", "judge_context": judge[:500]}
        return json.dumps(msg, ensure_ascii=False, indent=2)

    @tool
    def get_l2_candidates() -> str:
        """读取 L2 Scout 产出的候选标的列表（已通过巴菲特四层过滤器）。
        返回 JSON: {candidates: [{code, name, market, action, reasoning, rating}]}"""
        state = state_provider()
        candidates = state.get("stock_candidates", [])
        items = []
        for c in candidates[:20]:
            items.append({
                "code": c.get("code", ""),
                "name": c.get("name", ""),
                "market": c.get("market", ""),
                "action": c.get("action", ""),
                "reasoning": str(c.get("reasoning", ""))[:200],
                "rating": c.get("rating", "未评级"),
            })
        return json.dumps({"candidates": items, "total": len(candidates)},
                          ensure_ascii=False, indent=2)

    @tool
    def dispatch_scout(industry: str, market: str = "cn") -> str:
        """CIO 派员工定向搜索某行业的优质标的。
        内部调用: 获取成分股 → 公司概况 → 财务摘要 → 行情数据。
        返回该行业 Top 10 标的列表，含 PE/ROE/营收增速/市值。"""
        from tradingagents.agents.advisors.market_tools import (
            get_industry_constituents, get_company_profile,
            get_financial_summary, get_stock_quotes,
        )

        constituents_raw = get_industry_constituents.invoke(
            {"industry": industry, "market": market})
        codes = _extract_codes(constituents_raw, market)
        if not codes:
            return json.dumps(
                {"error": f"未找到 {industry} 的成分股", "market": market},
                ensure_ascii=False)

        results = []
        for code in codes[:10]:
            profile = get_company_profile.invoke(
                {"code": code, "market": market})
            financials = get_financial_summary.invoke(
                {"code": code, "market": market})
            quotes = get_stock_quotes.invoke(
                {"code": code, "market": market})
            results.append({
                "code": code,
                "profile": str(profile)[:300],
                "financials": str(financials)[:300],
                "quotes": str(quotes)[:200],
            })
        return json.dumps(
            {"industry": industry, "market": market, "stocks": results},
            ensure_ascii=False, indent=2)

    @tool
    def search_industry_etf(industry: str, market: str = "cn") -> str:
        """搜索某行业的 ETF/指数基金（行业暴露工具）。
        返回: {etfs: [{code, name, type, fee_rate, aum}]}"""
        from tradingagents.agents.advisors.market_tools import (
            get_fund_rankings,
        )
        result = get_fund_rankings.invoke(
            {"fund_type": "股票型", "market": market})
        etf_text = str(result)
        lines = etf_text.split("\n")
        matched = [l for l in lines if industry[:2] in l or industry in l]
        return json.dumps(
            {"industry": industry, "market": market, "etfs": matched[:10]},
            ensure_ascii=False, indent=2)

    @tool
    def validate_allocation(allocation_json: str) -> str:
        """检查行业目标仓位是否满足约束。
        输入: JSON数组 [{industry, target_weight, ...}]
        返回: {valid, total_weight, cash_ratio, violations}"""
        try:
            items = json.loads(allocation_json)
        except json.JSONDecodeError:
            return json.dumps({"valid": False, "error": "JSON 解析失败"})
        if not isinstance(items, list):
            return json.dumps({"valid": False, "error": "需要 JSON 数组"})

        state = state_provider()
        max_industry = state.get("max_industry_weight", 50.0)
        total = sum(it.get("target_weight", 0) for it in items)
        violations = []
        for it in items:
            tw = it.get("target_weight", 0)
            if tw > max_industry:
                violations.append({
                    "industry": it.get("industry"),
                    "issue": f"单行业 {tw}% > 上限 {max_industry}%",
                })
        cash = round(100 - total, 1)
        if cash < 5:
            violations.append({
                "industry": "现金",
                "issue": f"现金仅 {cash}%，建议 >= 5%",
            })
        return json.dumps({
            "valid": len(violations) == 0 and total <= 100,
            "total_weight": round(total, 1),
            "cash_ratio": cash,
            "max_industry_limit": max_industry,
            "violations": violations,
        }, ensure_ascii=False, indent=2)

    @tool
    def get_buy_signal(code: str) -> str:
        """读取某只标的的预计算买入信号（由 Buy Signal Engine 计算，非 LLM 编造）。
        返回: {code, name, signal, total_score, valuation_score, sentiment_score,
               fund_flow_score, confidence, price_range, timing, lights}"""
        state = state_provider()
        buy_signals = state.get("buy_signals", {})
        sig = buy_signals.get(code, {})
        if sig:
            return json.dumps(sig, ensure_ascii=False, indent=2)
        return json.dumps(
            {"code": code, "signal": "无信号", "note": "该标的不在 Buy Signal Engine 覆盖范围内"},
            ensure_ascii=False)

    return [
        get_position_batch, get_l1_verdict, get_l2_candidates,
        dispatch_scout, search_industry_etf, validate_allocation,
        get_buy_signal,
    ]
