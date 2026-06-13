"""stock_data_contract.py — 个股数据契约 + 缺口检测 + 取数任务生成（D0-8 用户'缺数据接着查'指令落地）

设计目标:
- 把 missing 字段从"借口"变成"agent 必须执行的取数 task"
- 跑 valuation 前, collect_v4 自动调本模块检查输入包契约
- MUST 字段缺 → exit=4 阻断, 输出具体取数指引(去哪儿查/查啥/怎么用)
- SHOULD 字段缺 → 降 confidence + 警告但不阻断

字段分类:
- 财务硬数据 8 (营收/净利/毛利/净利/ROE/经营现金流/股价/市值)
- 业务结构 6 (主营/分部营收/地区/Top客户/同业/行业空间)
- 估值锚 4 (PE-TTM/PE历史中枢/同业PE/卖方一致EPS)
合计 18 个 MUST 字段, 加上 10 个 SHOULD 字段(应收/存货周转/D/E/股本/股东变动/沽空/北上/分析师目标价等)。
"""

from typing import Dict, List, Any, Optional


# ============================================================================
# MUST 字段(18) — 缺一个 collect 阶段就 exit=4 不让 agent 跑分析
# ============================================================================
MUST_FIELDS: Dict[str, Dict[str, Any]] = {
    # —— 财务硬数据(8) ——
    "fy_latest_revenue": {
        "label": "最近年度营业收入(亿元)",
        "search_query_template": "{name} {code} {fy_year}年 营业收入 营收 年报",
        "source_hints": ["公司年报/季报", "aastocks.com 公告快讯", "stockanalysis.com", "雪球年报"],
        "usage": "DCF 现金流模型基础 / SOTP 分母 / 同业可比估值 PS",
        "validation": "must_be_number_with_unit",
    },
    "fy_latest_net_profit": {
        "label": "最近年度归母净利润(亿元)",
        "search_query_template": "{name} {code} {fy_year}年 归母净利润 净利",
        "source_hints": ["公司年报", "aastocks 公告"],
        "usage": "PE 估值分子 / EPS 推算",
        "validation": "must_be_number",
    },
    "fy_latest_gross_margin": {
        "label": "最近年度综合毛利率(%)",
        "search_query_template": "{name} {code} {fy_year}年 毛利率 综合毛利率",
        "source_hints": ["公司年报", "stockanalysis.com 财务比率"],
        "usage": "盈利质量判断 / mix shift 分析 / 同业对比",
    },
    "fy_latest_net_margin": {
        "label": "最近年度归母净利率(%)",
        "search_query_template": "{name} {code} 净利率 归母净利率 {fy_year}",
        "source_hints": ["公司年报", "推算 = 净利/营收"],
        "usage": "盈利能力 / 反向DCF 稳态净利率假设",
    },
    "fy_latest_roe": {
        "label": "最近年度ROE(摊薄/加权,%)",
        "search_query_template": "{name} {code} ROE 净资产收益率 {fy_year}",
        "source_hints": ["公司年报", "Reuters/Bloomberg 财务比率"],
        "usage": "资本效率 / DuPont 拆解 / 价值创造判断",
    },
    "fy_latest_operating_cashflow": {
        "label": "最近年度经营性现金流(亿元)",
        "search_query_template": "{name} {code} {fy_year}年 经营活动现金流 经营性现金流",
        "source_hints": ["公司年报现金流量表", "stockanalysis cashflow"],
        "usage": "盈余质量(经营现金流/净利 比) / FCF 推算",
    },
    "current_price": {
        "label": "当前股价(本地币种)",
        "search_query_template": "{name} {code} 股价 当前价 收盘价",
        "source_hints": ["Google Finance", "yahoo finance", "aastocks 实时报价"],
        "usage": "估值基准 / target_price 上下行空间计算",
    },
    "market_cap": {
        "label": "总市值(亿,本地币种)",
        "search_query_template": "{name} {code} 总市值 市值",
        "source_hints": ["Google Finance", "tradingview", "wind 推算 = 股价×总股本"],
        "usage": "反向DCF 隐含假设推算 / SOTP 分母",
    },
    # —— 业务结构(6) ——
    "main_business_description": {
        "label": "主营业务一句话描述",
        "search_query_template": "{name} {code} 主营业务 主要产品",
        "source_hints": ["公司官网", "招股书", "年报第二节"],
        "usage": "投资者快速理解 / 行业归类",
    },
    "revenue_breakdown_segments": {
        "label": "分产品/分部营收占比(占比合计 ≈ 100%)",
        "search_query_template": "{name} {code} 分产品 分部 营收占比 {fy_year}年报",
        "source_hints": ["公司年报第二节业务回顾", "投资者交流纪要", "卖方深度报告"],
        "usage": "SOTP 分部估值核心 / mix shift 分析",
        "validation": "list_with_pct_sum_100",
    },
    "geo_breakdown": {
        "label": "分地区营收占比(国内/海外, 海外细分)",
        "search_query_template": "{name} {code} 分地区 海外 国内 营收占比 {fy_year}",
        "source_hints": ["公司年报地区分部数据", "卖方研报"],
        "usage": "全球化进度 / 地缘风险评估 / 货币敞口",
    },
    "top_customers": {
        "label": "前 5 大客户占比 + 是否单一大客户",
        "search_query_template": "{name} {code} 前五大客户 客户集中度 {fy_year}",
        "source_hints": ["公司年报第十节关联交易/客户披露", "招股书"],
        "usage": "买方议价力 / 单客户依赖风险 / 五力之买方",
    },
    "peers": {
        "label": "可比公司清单(至少 3 家, 同行业同规模)",
        "search_query_template": "{name} {code} 同业 可比公司 主要竞争对手",
        "source_hints": ["卖方深度报告 同业对比页", "wind 行业分类"],
        "usage": "可比估值 / 五力之同业竞争烈度",
    },
    "industry_size_cagr": {
        "label": "所在行业市场规模 + 未来 3-5 年 CAGR",
        "search_query_template": "{industry} 市场规模 {fy_year} CAGR 复合增长率",
        "source_hints": ["Yole/Gartner/Frost & Sullivan/IDC", "卖方行业深度报告"],
        "usage": "天花板判断 / 长期增长可持续性",
    },
    # —— 估值锚(4) ——
    "pe_ttm": {
        "label": "PE-TTM(滚动市盈率)",
        "search_query_template": "{name} {code} PE TTM 市盈率",
        "source_hints": ["stockanalysis.com", "Reuters", "Wind"],
        "usage": "估值水平基线 / 反向DCF 隐含假设输入",
    },
    "pe_history_band": {
        "label": "PE 历史中枢 + 当前分位(过去 3-5 年)",
        "search_query_template": "{name} {code} PE 历史 估值分位 {fy_year}",
        "source_hints": ["wind PE 河流图", "卖方研报历史估值带"],
        "usage": "判断估值偏热/偏冷 / 均值回归概率",
    },
    "peer_pe_comparison": {
        "label": "同业 PE 对比表(至少 3 家)",
        "search_query_template": "{peers} PE 对比 估值",
        "source_hints": ["wind 同业对比", "卖方行业研报"],
        "usage": "相对估值 / 折溢价合理性判断",
    },
    "consensus_eps_2y": {
        "label": "卖方一致预期 EPS(未来 2 年)",
        "search_query_template": "{name} {code} 卖方一致预期 EPS 2026 2027",
        "source_hints": ["choice/wind 一致预期", "Bloomberg consensus", "stockanalysis forward"],
        "usage": "forward PE 推算 / 预期差判断基准",
    },
}


# ============================================================================
# SHOULD 字段(10) — 缺降 confidence 不阻断
# ============================================================================
SHOULD_FIELDS: Dict[str, Dict[str, Any]] = {
    "q_latest_revenue": {"label": "最近季度营收", "search_query_template": "{name} {code} 季度报告 营业收入"},
    "q_latest_net_profit": {"label": "最近季度归母净利", "search_query_template": "{name} {code} 季报 净利润"},
    "ar_turnover_days": {"label": "应收账款周转天数", "search_query_template": "{name} {code} 应收账款周转 {fy_year}"},
    "inventory_turnover_days": {"label": "存货周转天数", "search_query_template": "{name} {code} 存货周转 {fy_year}"},
    "debt_to_equity": {"label": "资产负债率/D-E", "search_query_template": "{name} {code} 资产负债率 杠杆"},
    "share_count": {"label": "总股本/流通股本", "search_query_template": "{name} {code} 总股本 流通股"},
    "shareholders_recent_changes": {"label": "近 6 月重大股东变动(增持/减持/质押)", "search_query_template": "{name} {code} 股东减持 增持 公告 2026"},
    "short_interest_or_margin": {"label": "沽空比例(港股) / 融资余额(A股)", "search_query_template": "{name} {code} 沽空 融资余额"},
    "northbound_flow": {"label": "北上资金近 30 日净流入(A股)", "search_query_template": "{name} {code} 北上资金 沪股通 深股通"},
    "analyst_target_price": {"label": "卖方目标价共识 / 评级分布", "search_query_template": "{name} {code} 大行 目标价 评级 2026"},
}


# ============================================================================
# 工具函数
# ============================================================================
def _has_value(d: Dict, key: str) -> bool:
    """字段是否真有值(不是 None/空字符串/empty dict/empty list)"""
    if not isinstance(d, dict):
        return False
    v = d.get(key)
    if v is None or v == "" or v == [] or v == {}:
        return False
    if isinstance(v, dict) and not any(v.values()):
        return False
    return True


# 字段别名映射: 契约 key → 输入包里可能的实际路径(支持嵌套点号)
FIELD_ALIASES: Dict[str, List[str]] = {
    "fy_latest_revenue": [
        "financials.fy2025.revenue_yi", "financials.fy2024.revenue_yi",
        "fundamentals.data.revenue", "fy2025.revenue_yi", "fy_latest_revenue",
        "fy2025.revenue", "revenue_2025",
    ],
    "fy_latest_net_profit": [
        "financials.fy2025.net_yi", "financials.fy2025.net_profit_yi",
        "fundamentals.data.net_profit", "fy2025.net_yi", "fy_latest_net_profit",
        "fy2025.net_profit_attributable_yi",
    ],
    "fy_latest_gross_margin": [
        "financials.fy2025.gross_margin", "financials.fy2025.gross_margin_pct",
        "fundamentals.data.gross_margin", "fy2025.gross_margin",
        "fy_latest_gross_margin",
    ],
    "fy_latest_net_margin": [
        "financials.fy2025.net_margin", "financials.fy2025.net_margin_pct",
        "fy2025.net_margin", "fy_latest_net_margin",
    ],
    "fy_latest_roe": [
        "financials.fy2025.roe", "fundamentals.data.roe",
        "reuters_2024_metrics.roe_ttm", "fy_latest_roe",
    ],
    "fy_latest_operating_cashflow": [
        "financials.fy2025.operating_cashflow_yi", "fy2025.operating_cashflow",
        "fy_latest_operating_cashflow",
    ],
    "current_price": [
        "price.current", "price", "fundamentals.data.price",
        "current_price",
    ],
    "market_cap": [
        "market_cap_yi.value", "market_cap_yi", "market_cap",
        "fundamentals.data.market_cap",
    ],
    "main_business_description": [
        "business.core", "business.model", "business.main_business",
        "business.core_segments", "main_business_description",
    ],
    "revenue_breakdown_segments": [
        "product_subdivision", "business.segments", "ip_breakdown",
        "revenue_breakdown_segments", "business.revenue_breakdown",
    ],
    "geo_breakdown": [
        "geo_breakdown", "business.geo_breakdown",
        "q1_2026_operating", "geographic_breakdown",
    ],
    "top_customers": [
        "business.amd_revenue_share_estimated", "business.top_customers",
        "top_customers", "customer_concentration",
    ],
    "peers": [
        "business.peers", "peers", "industry_context.peers",
    ],
    "industry_size_cagr": [
        "industry_context.industry_size", "industry_size_cagr",
        "industry_context.market_size", "industry_size",
    ],
    "pe_ttm": [
        "valuation.pe_ttm_estimated.value", "valuation.pe_ttm_estimated",
        "valuation.pe_ttm", "fundamentals.data.pe_ttm", "pe_ttm",
    ],
    "pe_history_band": [
        "valuation.pe_history_band", "valuation.pe_band",
        "pe_history_band", "valuation.pe_percentile",
    ],
    "peer_pe_comparison": [
        "valuation.peers_pe", "peer_pe_comparison",
        "business.peers_pe", "valuation.peer_pe",
    ],
    "consensus_eps_2y": [
        "consensus_eps_2y", "ratings.consensus_eps_2026",
        "sell_side_data.consensus_eps_2026",
    ],
    # SHOULD 字段别名
    "q_latest_revenue": ["financials.q1_2026.revenue_yi", "q1_2026.revenue_yi", "q_latest_revenue"],
    "q_latest_net_profit": ["financials.q1_2026.net_yi", "q1_2026.net_yi", "q_latest_net_profit"],
    "ar_turnover_days": ["financials.ar_turnover_days", "ar_turnover_days"],
    "inventory_turnover_days": ["financials.inventory_turnover_days", "inventory_turnover_days"],
    "debt_to_equity": ["reuters_2024_metrics.total_debt_to_equity", "financials.debt_to_equity", "debt_to_equity"],
    "share_count": ["shares_out_yi.value", "shares_out_yi", "share_count"],
    "shareholders_recent_changes": ["shareholders", "shareholders_recent_changes"],
    "short_interest_or_margin": ["sell_side_ratings_2026.short_interest", "short_interest_or_margin"],
    "northbound_flow": ["northbound_flow", "capital_flow.northbound_30d_net"],
    "analyst_target_price": ["sell_side_ratings_2026.consensus", "analyst_target_price", "ratings.morningstar"],
}


def _path_get(d: Dict, path: str) -> Any:
    """支持嵌套点号路径取值"""
    parts = path.split(".")
    cur = d
    for p in parts:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(p)
        if cur is None or cur == "" or cur == [] or cur == {}:
            return None
    return cur


def _resolve_field(stock_pack: Dict, field_key: str) -> bool:
    """检查 stock 输入包是否含某字段值, 兼容多种存放位置 + 别名映射"""
    # 直接顶层
    if _has_value(stock_pack, field_key):
        return True
    # 别名路径
    for alias_path in FIELD_ALIASES.get(field_key, []):
        if _path_get(stock_pack, alias_path) not in (None, "", [], {}):
            return True
    # 兼容嵌套位置(legacy)
    for nested_key in ["fundamentals", "financials", "business", "valuation", "macro_context"]:
        nested = stock_pack.get(nested_key)
        if isinstance(nested, dict):
            if _has_value(nested, field_key):
                return True
            data = nested.get("data") if "data" in nested else None
            if isinstance(data, dict) and _has_value(data, field_key):
                return True
    return False


def check_data_contract(stock_pack: Dict[str, Any]) -> Dict[str, Any]:
    """检查 stock 输入包是否满足契约。

    Returns:
        {
            "ok": bool,                    # 是否满足 MUST(允许跑 agent)
            "must_satisfied": [...],       # 已满足的 MUST 字段
            "must_missing": [...],         # 缺失的 MUST 字段(关键!)
            "should_missing": [...],       # 缺失的 SHOULD 字段(降 confidence)
            "fetch_tasks": [               # 待取数任务清单(主 agent 直接消费)
                {
                    "field": "fy_latest_revenue",
                    "label": "最近年度营业收入",
                    "search_query": "通富微电 002156 2025年 营业收入",
                    "source_hints": ["公司年报", ...],
                    "usage": "DCF...",
                    "priority": "MUST" | "SHOULD"
                }, ...
            ],
            "confidence_penalty": float,   # SHOULD 缺失带来的 confidence 折扣
            "summary": str                 # 一句话总结
        }
    """
    code = stock_pack.get("code", "?")
    name = stock_pack.get("name", "")
    industry = stock_pack.get("industry", "")
    peers_str = ""
    peers_v = stock_pack.get("peers") or (stock_pack.get("business", {}) or {}).get("peers")
    if isinstance(peers_v, list):
        peers_str = "/".join(peers_v[:3])

    fy_year = 2025  # TODO: 实时根据当前日期推算最新年报年份

    must_satisfied: List[str] = []
    must_missing: List[str] = []
    should_missing: List[str] = []
    fetch_tasks: List[Dict[str, Any]] = []

    def _make_task(field_key: str, spec: Dict, priority: str) -> Dict[str, Any]:
        tmpl = spec.get("search_query_template", "")
        query = (tmpl
                 .replace("{name}", name)
                 .replace("{code}", code)
                 .replace("{fy_year}", str(fy_year))
                 .replace("{industry}", industry)
                 .replace("{peers}", peers_str))
        return {
            "field": field_key,
            "label": spec["label"],
            "search_query": query,
            "source_hints": spec.get("source_hints", []),
            "usage": spec.get("usage", ""),
            "priority": priority,
        }

    # 检查 MUST
    for field_key, spec in MUST_FIELDS.items():
        if _resolve_field(stock_pack, field_key):
            must_satisfied.append(field_key)
        else:
            must_missing.append(field_key)
            fetch_tasks.append(_make_task(field_key, spec, "MUST"))

    # 检查 SHOULD
    for field_key, spec in SHOULD_FIELDS.items():
        if not _resolve_field(stock_pack, field_key):
            should_missing.append(field_key)
            fetch_tasks.append(_make_task(field_key, spec, "SHOULD"))

    # confidence 折扣: SHOULD 每缺 1 个扣 0.02, 上限 0.20
    confidence_penalty = min(0.20, len(should_missing) * 0.02)

    ok = len(must_missing) == 0
    n_must = len(MUST_FIELDS)
    n_should = len(SHOULD_FIELDS)
    summary = (f"契约检查 {('通过' if ok else '不通过')}: "
               f"MUST {len(must_satisfied)}/{n_must} verified, "
               f"SHOULD {n_should - len(should_missing)}/{n_should} verified, "
               f"confidence 折扣 {confidence_penalty:.2f}")

    return {
        "ok": ok,
        "must_satisfied": must_satisfied,
        "must_missing": must_missing,
        "should_missing": should_missing,
        "fetch_tasks": fetch_tasks,
        "confidence_penalty": confidence_penalty,
        "summary": summary,
    }


def render_fetch_instructions(check_result: Dict[str, Any]) -> str:
    """把契约检查结果渲染成主 agent 可直接执行的取数指令文本。"""
    tasks = check_result.get("fetch_tasks", [])
    if not tasks:
        return "✅ 数据契约已满足, 无需补取数."
    must_tasks = [t for t in tasks if t["priority"] == "MUST"]
    should_tasks = [t for t in tasks if t["priority"] == "SHOULD"]
    lines = []
    if must_tasks:
        lines.append(f"❌ 缺关键 MUST 字段 {len(must_tasks)} 个 (collect 阶段需 exit=4 阻断,主 agent 必须用 web_search 补齐):")
        for t in must_tasks:
            lines.append(f"  • {t['field']} ({t['label']})")
            lines.append(f"    → 查询: {t['search_query']}")
            lines.append(f"    → 来源: {' / '.join(t['source_hints'])}")
            lines.append(f"    → 用途: {t['usage']}")
    if should_tasks:
        lines.append(f"\n⚠️ 缺 SHOULD 字段 {len(should_tasks)} 个 (降 confidence 不阻断, 但建议补):")
        for t in should_tasks:
            lines.append(f"  • {t['field']} → {t['search_query']}")
    return "\n".join(lines)
