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
        "search_query_template": "{name_or_industry} 行业 市场规模 {fy_year} CAGR 复合增长率",
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
    # —— 价值创造组(6) — 判断"公司未来值多少钱"的必须输入(2026-06-14 用户拍板补全) ——
    "roic": {
        "label": "ROIC 投入资本回报率(%) 或 NOPAT+投入资本(可让 agent 算)",
        "search_query_template": "{name} {code} ROIC 投入资本回报率 NOPAT {fy_year}",
        "source_hints": ["stockanalysis.com ROIC", "wind 财务比率", "年报推算 NOPAT/(净债务+权益)"],
        "usage": "★最关键价值创造指标 — ROIC>WACC 才创造价值; ROE 被杠杆污染,ROIC 才干净",
    },
    "wacc_estimate": {
        "label": "WACC 加权平均资本成本(%)(无风险利率+beta+风险溢价估算,允许 estimated)",
        "search_query_template": "{name} {code} WACC 加权平均资本成本 beta",
        "source_hints": ["cn10y 无风险利率 + beta×股权风险溢价(5-6%) 估算", "卖方 DCF 报告 WACC 假设"],
        "usage": "ROIC 对比基准 / 正向 DCF 折现率 — 取不到精确值时按行业+beta 估算并标 estimated",
    },
    "tam_size": {
        "label": "所在赛道 TAM 绝对天花板(2030E 市场规模, 亿/万亿级)",
        "search_query_template": "{name_or_industry} 行业 市场规模 TAM 2030 天花板 测算",
        "source_hints": ["Gartner/IDC/Frost&Sullivan/灼识", "卖方行业深度报告 TAM 测算", "公司投资者交流市场空间"],
        "usage": "★成长上限 — 市场多大决定公司成长天花板; 配合渗透率判断还能涨多少",
    },
    "penetration_rate": {
        "label": "当前渗透率(%) + 行业阶段(导入/爆发/成熟/衰退)(允许 estimated)",
        "search_query_template": "{name_or_industry} 渗透率 行业阶段 {fy_year} 导入 爆发 成熟",
        "source_hints": ["卖方行业研报渗透率曲线", "行业协会数据"],
        "usage": "★成长弹性 — 渗透率 5-30% 高速成长期股价弹性最大; 取不到精确值时按阶段定性",
    },
    "capital_allocation_5y": {
        "label": "近 5 年资本配置去向(回购/分红/并购/capex 金额 + ROI 成败)",
        "search_query_template": "{name} {code} 回购 分红 并购 资本开支 历史 近5年",
        "source_hints": ["年报现金流量表筹资/投资活动", "回购分红公告历史", "并购案例复盘"],
        "usage": "★管理层水平(段永平/巴菲特核心) — 钱花得好不好是长期价值创造/毁灭的最大变量之一",
    },
    "fcf_latest": {
        "label": "最近年度自由现金流(亿元 = 经营现金流 - 资本开支)",
        "search_query_template": "{name} {code} 自由现金流 FCF 资本开支 {fy_year}",
        "source_hints": ["年报现金流量表(经营 - capex)", "stockanalysis FCF"],
        "usage": "★正向 DCF 内在价值锚的输入 — 预测未来 FCF 折现出内在价值,与反向 DCF 三角验证",
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
    """字段是否真有 verified 值(不是 None/空/unattainable/missing 占位字符串)"""
    if not isinstance(d, dict):
        return False
    v = d.get(key)
    if v is None or v == "" or v == [] or v == {}:
        return False
    if isinstance(v, dict) and not any(v.values()):
        return False
    # D0-8 unattainable/missing 占位字符串不算 verified(防止"装作已查")
    if isinstance(v, str):
        s = v.strip().lower()
        if s.startswith("unattainable") or s.startswith("missing") or s == "n/a":
            return False
    return True


def _is_unattainable(d: Dict, key: str, alias_paths: List[str]) -> bool:
    """字段是否标了 unattainable(诚实降级,与真 missing 区分)"""
    def _check(v):
        return isinstance(v, str) and v.strip().lower().startswith("unattainable")
    if _check(d.get(key)):
        return True
    for alias in alias_paths:
        v = _path_get(d, alias)
        if _check(v):
            return True
    return False


# 字段别名映射: 契约 key → 输入包里可能的实际路径(支持嵌套点号)
FIELD_ALIASES: Dict[str, List[str]] = {
    "roic": ["roic", "value_creation.roic", "financials.fy2025.roic", "fundamentals.data.roic"],
    "wacc_estimate": ["wacc_estimate", "value_creation.wacc", "valuation.wacc"],
    "tam_size": ["tam_size", "value_creation.tam_size", "industry_context.tam_size", "industry_context.market_size"],
    "penetration_rate": ["penetration_rate", "value_creation.penetration_rate", "industry_context.penetration_rate"],
    "capital_allocation_5y": ["capital_allocation_5y", "value_creation.capital_allocation", "business.capital_allocation"],
    "fcf_latest": ["fcf_latest", "value_creation.fcf", "financials.fy2025.fcf_yi", "fy2025.fcf"],
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
    name_or_industry = industry if industry else name  # 行业空时用公司名兜底
    peers_str = ""
    peers_v = stock_pack.get("peers") or (stock_pack.get("business", {}) or {}).get("peers")
    if isinstance(peers_v, list):
        peers_str = "/".join(peers_v[:3])

    fy_year = 2025  # TODO: 实时根据当前日期推算最新年报年份

    must_satisfied: List[str] = []
    must_missing: List[str] = []
    must_unattainable: List[str] = []  # D0-8 诚实降级:真取不到的(如公司未披露/付费数据)
    should_missing: List[str] = []
    should_unattainable: List[str] = []
    fetch_tasks: List[Dict[str, Any]] = []

    def _make_task(field_key: str, spec: Dict, priority: str) -> Dict[str, Any]:
        tmpl = spec.get("search_query_template", "")
        query = (tmpl
                 .replace("{name}", name)
                 .replace("{code}", code)
                 .replace("{fy_year}", str(fy_year))
                 .replace("{industry}", industry)
                 .replace("{name_or_industry}", name_or_industry)
                 .replace("{peers}", peers_str if peers_str else (name + " 同业")))
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
        aliases = FIELD_ALIASES.get(field_key, [])
        if _resolve_field(stock_pack, field_key):
            must_satisfied.append(field_key)
        elif _is_unattainable(stock_pack, field_key, aliases):
            must_unattainable.append(field_key)  # 诚实降级,不阻断,但 critic 必查降 confidence
        else:
            must_missing.append(field_key)
            fetch_tasks.append(_make_task(field_key, spec, "MUST"))

    # 检查 SHOULD
    for field_key, spec in SHOULD_FIELDS.items():
        aliases = FIELD_ALIASES.get(field_key, [])
        if _resolve_field(stock_pack, field_key):
            pass  # 有值
        elif _is_unattainable(stock_pack, field_key, aliases):
            should_unattainable.append(field_key)
        else:
            should_missing.append(field_key)
            fetch_tasks.append(_make_task(field_key, spec, "SHOULD"))

    # confidence 折扣:
    # - SHOULD 真缺 -0.02 / 项, 上限 -0.10
    # - unattainable(MUST/SHOULD) -0.03 / 项, 上限 -0.15(诚实降级也要扣)
    confidence_penalty = (
        min(0.10, len(should_missing) * 0.02)
        + min(0.15, (len(must_unattainable) + len(should_unattainable)) * 0.03)
    )

    # ok 判定: MUST 字段(verified + unattainable) ≥ 18 才允许跑
    # 但 unattainable 比例 > 30% 时 critic 应警告"数据基础不足"
    must_total_covered = len(must_satisfied) + len(must_unattainable)
    ok = must_total_covered == len(MUST_FIELDS)
    unattainable_ratio = len(must_unattainable) / max(1, len(MUST_FIELDS))
    n_must = len(MUST_FIELDS)
    n_should = len(SHOULD_FIELDS)
    summary = (f"契约检查 {('通过' if ok else '不通过')}: "
               f"MUST {len(must_satisfied)} verified + {len(must_unattainable)} unattainable / {n_must}, "
               f"SHOULD {n_should - len(should_missing) - len(should_unattainable)} verified / {n_should}, "
               f"confidence 折扣 {confidence_penalty:.2f}")
    if unattainable_ratio > 0.3:
        summary += f" ⚠️ MUST unattainable 比例 {unattainable_ratio:.0%} 偏高,数据基础不足,critic 应警告"

    return {
        "ok": ok,
        "must_satisfied": must_satisfied,
        "must_unattainable": must_unattainable,
        "must_missing": must_missing,
        "should_missing": should_missing,
        "should_unattainable": should_unattainable,
        "fetch_tasks": fetch_tasks,
        "confidence_penalty": confidence_penalty,
        "unattainable_ratio": unattainable_ratio,
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


# ════════════════════════════════════════════════════════════════
# 🚨 RULE-DATA-VERIFIED 强制校验(2026-06-14 用户血泪固化, 防通富$157B事故再现)
# ════════════════════════════════════════════════════════════════

EXPERT_VALUATION_REQUIRED_VERIFIED_FIELDS = [
    "future_tam",           # 必须含派生自行业层标记 + verified_sources
    "future_share",         # 必须基于子赛道可寻址 + 数据来源
    "target_price",         # 必须含 forward EPS + 可比PE推导链
]


def check_expert_valuation_verified(stock_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    🚨 RULE-DATA-VERIFIED 强制校验

    检查 stock 的 expert_valuation 字段是否符合 verified 数据红线:
    1. future_tam 必须含 'verified' 关键词或 derived_from_industry 标记
    2. future_share 必须含子赛道可寻址逻辑(不能用整个行业 TAM × 份额)
    3. target_price 必须含可比 PE 推导链(标可比公司 + 来源)
    4. data_status 必须明示 verified/estimated/missing

    返回:
        {
          "rule_violated": bool,
          "violations": [...],     # 违反列表
          "warnings": [...],       # 警告列表
          "block_write": bool,     # 是否应阻止落盘
        }

    用法:
        result = check_expert_valuation_verified(stock_payload)
        if result["block_write"]:
            print("🚨 RULE_DATA_VERIFIED 违规, 拒绝落盘")
            sys.exit(4)
    """
    violations = []
    warnings = []

    vc = stock_payload.get("value_creation", {}) or {}
    ev = vc.get("expert_valuation", {}) or {}

    # 1. future_tam 校验
    future_tam = ev.get("future_tam", "")
    if isinstance(future_tam, str):
        # 必须含派生标记或 verified 关键词
        has_derived = "derived_from" in str(ev) or "派生自行业层" in future_tam
        has_verified = "verified" in future_tam.lower() or "Yole" in future_tam or "IDC" in future_tam or "Gartner" in future_tam or "WSTS" in future_tam or "marketsandmarkets" in future_tam
        if future_tam and not (has_derived or has_verified):
            violations.append({
                "field": "future_tam",
                "issue": "缺 verified_source 或 派生自行业层 标记",
                "rule": "RULE-DATA-VERIFIED-1",
                "fix": "TAM 数字必须有 ≥3 独立来源标 URL, 或显式标'派生自行业层 industry:xxx'"
            })

    # 2. target_price 校验
    target_price = ev.get("target_price", "")
    if isinstance(target_price, str) and target_price:
        # 必须含可比 PE 推导链
        has_pe_chain = "PE" in target_price and ("EPS" in target_price or "倍" in target_price or "x" in target_price)
        has_comparable = any(c in target_price for c in ["对标", "可比", "vs ", "Lonza", "台积电", "Meta", "Coherent"])
        if not has_pe_chain:
            warnings.append({
                "field": "target_price",
                "issue": "缺 forward EPS × 目标 PE 推导链",
                "rule": "RULE-DATA-VERIFIED-3",
                "fix": "目标价应明示 'forward EPS ¥X × 合理 PE Yx = ¥Z'"
            })
        if not has_comparable and not warnings:  # 已有推导链但缺可比
            warnings.append({
                "field": "target_price",
                "issue": "缺可比公司锚定",
                "fix": "应标 vs Lonza 25x / 台积电 15x 等"
            })

    # 3. assumptions 校验
    assumptions = ev.get("assumptions", "")
    if isinstance(assumptions, str) and assumptions:
        if "证伪" not in assumptions and "若" not in assumptions:
            warnings.append({
                "field": "assumptions",
                "issue": "缺可证伪信号",
                "fix": "每个核心假设需配可证伪条件(如'若份额<X% 则下修')"
            })

    # 4. data_status 校验
    data_status = ev.get("data_status", "")
    if not data_status:
        violations.append({
            "field": "data_status",
            "issue": "未标注 data_status",
            "rule": "RULE-DATA-VERIFIED-4",
            "fix": "必须标 verified/estimated/missing/synthesized_by_main_agent"
        })

    rule_violated = len(violations) > 0
    block_write = rule_violated  # 有 violation 直接阻止落盘

    return {
        "rule_violated": rule_violated,
        "violations": violations,
        "warnings": warnings,
        "block_write": block_write,
        "summary": f"violations={len(violations)} warnings={len(warnings)}"
    }


def render_data_verified_report(check_result: Dict[str, Any]) -> str:
    """渲染校验报告为可读文本(用于 cli/critic 输出)"""
    lines = []
    if check_result["rule_violated"]:
        lines.append("🚨 RULE-DATA-VERIFIED 违规! 以下字段未通过 verified 校验:")
        for v in check_result["violations"]:
            lines.append(f"  ❌ {v['field']}: {v['issue']}")
            lines.append(f"     规则: {v.get('rule', 'general')}")
            lines.append(f"     修复: {v.get('fix', 'N/A')}")
    if check_result["warnings"]:
        lines.append("\n⚠️  警告(不阻止落盘但建议补充):")
        for w in check_result["warnings"]:
            lines.append(f"  • {w['field']}: {w['issue']}")
            lines.append(f"    建议: {w.get('fix', 'N/A')}")
    if not check_result["rule_violated"] and not check_result["warnings"]:
        lines.append("✅ RULE-DATA-VERIFIED 校验通过")
    return "\n".join(lines)
