"""v4 持仓聚合器 — 直接 + 间接(基金穿透) 持仓 → 行业暴露 (D0-6 / 2026-06-13)

输入: classify_holdings 输出 (含 fund_passthrough)
输出:
  {
    "industries": {
      "半导体": {
        "direct_yi": 12.5,        ← 直接持股的总市值(万元)
        "indirect_yi": 8.3,        ← 间接(基金穿透)总市值(万元)
        "total_yi": 20.8,
        "direct_holdings": [{"code", "name", "market_value"}, ...],
        "contributing_funds": [    ← 哪些基金贡献了这个行业的间接持仓
          {
            "code": "012629",
            "name": "广发国证半导体芯片ETF联接A",
            "market_value": 10000,
            "industry_weight_pct": 80.0,    ← 该基金中半导体占比
            "indirect_yi": 8000,             ← 间接贡献金额 = market_value × industry_weight_pct
            "data_status": "verified"
          }
        ]
      },
      ...
    },
    "stocks_held_by_funds": {       ← 通过基金间接持有的股票(给个股页"也被X个基金持有"用)
      "AAPL": [{"code":"270042","name":"广发纳指100","weight":8.5,"indirect_value":1737}, ...],
      ...
    },
    "summary": {
      "total_market_value": float,
      "direct_market_value": float,
      "indirect_market_value": float,
      "industries_count": int,
      "funds_with_passthrough": int,
      "funds_without_passthrough": int
    }
  }

使用:
  from app.services.v4.v4_aggregator import aggregate_holdings
  result = aggregate_holdings(classified)  # classify_holdings 输出
"""

from __future__ import annotations
from typing import Any, Dict, List
from collections import defaultdict


def aggregate_holdings(classified: Dict[str, Any]) -> Dict[str, Any]:
    """聚合直接 + 间接 持仓到行业层

    Args:
        classified: classify_holdings() 输出, 期望含 by_class.<class>.holdings 列表
                    每个 holding 含 fund_passthrough 字段 (若为基金且 holdings.json 已填)

    Returns:
        聚合后字典(详见 module docstring)
    """
    industries: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {
            "direct_yi": 0.0,
            "indirect_yi": 0.0,
            "total_yi": 0.0,
            "direct_holdings": [],
            "contributing_funds": [],
        }
    )

    # 通过基金间接持有的股票: code -> [{基金 code/name/weight/indirect_value}]
    stocks_held_by_funds: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    direct_mv = 0.0
    indirect_mv = 0.0
    funds_with = 0
    funds_without = 0

    # 遍历所有大类持仓
    by_class = classified.get("by_class", {}) or {}
    for klass, group in by_class.items():
        holdings = group.get("holdings", []) or []
        for h in holdings:
            code = h.get("code", "")
            name = h.get("name", "")
            mv = float(h.get("market_value", 0) or 0)
            itype = h.get("instrument_type", "")
            fp = h.get("fund_passthrough")

            # 1. 股票/直接持股
            if itype == "stock":
                direct_mv += mv
                # 注意: 个股的"行业"需要从 stock unit 反查(industry 字段),
                # 但这里 classifier 没有那个信息 — 暂留 "未分类直接持仓" 占位,
                # 行业页用 industry_weight_pct 单独算(查 stock unit 的 industry 即可)
                # 此处只统计直接持股 mv 总和供 summary 用
                continue

            # 2. 基金: 检查 fund_passthrough
            if itype in ("fund", "etf"):
                if not fp:
                    funds_without += 1
                    continue
                funds_with += 1
                indirect_mv += mv

                # 2.1 行业暴露: industry_exposure {半导体: 12, 新能源: 8, ...}
                ind_exp = fp.get("industry_exposure") or {}
                for industry, weight_pct in ind_exp.items():
                    if not industry or weight_pct is None:
                        continue
                    weight = float(weight_pct)
                    contribution = mv * weight / 100.0
                    industries[industry]["indirect_yi"] += contribution
                    industries[industry]["contributing_funds"].append({
                        "code": code,
                        "name": name,
                        "market_value": mv,
                        "industry_weight_pct": weight,
                        "indirect_yi": contribution,
                        "data_status": fp.get("_data_status", "estimated"),
                    })

                # 2.2 重仓股穿透: top_holdings [{code, name, weight, industry}, ...]
                top = fp.get("top_holdings") or []
                for s in top:
                    s_code = s.get("code", "")
                    s_name = s.get("name", "")
                    s_weight = float(s.get("weight", 0) or 0)
                    s_indirect_value = mv * s_weight / 100.0
                    if s_code:
                        stocks_held_by_funds[s_code].append({
                            "fund_code": code,
                            "fund_name": name,
                            "weight_in_fund": s_weight,
                            "indirect_value": s_indirect_value,
                            "stock_name": s_name,
                        })

    # 计算 total_yi 和直接持股(stock 通过 industry 字段单独聚合 - 暂留接口)
    for industry, data in industries.items():
        data["total_yi"] = round(data["direct_yi"] + data["indirect_yi"], 2)
        data["indirect_yi"] = round(data["indirect_yi"], 2)
        data["direct_yi"] = round(data["direct_yi"], 2)

    # 排序行业(按 total_yi 降序)
    sorted_industries = dict(
        sorted(industries.items(), key=lambda x: -x[1]["total_yi"])
    )

    return {
        "industries": sorted_industries,
        "stocks_held_by_funds": dict(stocks_held_by_funds),
        "summary": {
            "total_market_value": round(direct_mv + indirect_mv, 2),
            "direct_market_value": round(direct_mv, 2),
            "indirect_market_value": round(indirect_mv, 2),
            "industries_count": len(sorted_industries),
            "funds_with_passthrough": funds_with,
            "funds_without_passthrough": funds_without,
            "passthrough_coverage_pct": (
                round(funds_with / (funds_with + funds_without) * 100, 1)
                if (funds_with + funds_without) > 0 else 0.0
            ),
        },
    }


def aggregate_to_industry_with_direct_stocks(
    classified: Dict[str, Any],
    stock_industries: Dict[str, str],
) -> Dict[str, Any]:
    """带直接持股行业回填的版本.

    Args:
        classified: classify_holdings 输出
        stock_industries: 直接持股 code → industry 映射(从 stocks 单元反查)

    Returns:
        聚合后字典, industries.<name>.direct_yi 含直接持股贡献

    D0-6 升级(2026-06-13): 用基金 top_holdings 重仓股的 v4 industry 反推 indirect_yi
    解决基金 industry_exposure 用 GICS 体系(信息技术/通信服务) vs v4 用自己体系(半导体/AI算力) 的映射问题
    """
    # 先用 top_holdings 反推 (优先于 industry_exposure)
    base_with_top: Dict[str, Dict[str, Any]] = {}

    by_class = classified.get("by_class", {}) or {}
    funds_with = 0
    funds_without = 0
    direct_mv = 0.0
    indirect_mv = 0.0
    stocks_held_by_funds: Dict[str, List[Dict[str, Any]]] = {}

    for klass, group in by_class.items():
        for h in group.get("holdings", []) or []:
            itype = h.get("instrument_type", "")
            mv = float(h.get("market_value", 0) or 0)
            fp = h.get("fund_passthrough")
            code = h.get("code", "")
            name = h.get("name", "")

            # 直接持股
            if itype == "stock":
                direct_mv += mv
                industry = stock_industries.get(code, "未分类")
                if industry not in base_with_top:
                    base_with_top[industry] = _empty_industry()
                base_with_top[industry]["direct_yi"] += mv
                base_with_top[industry]["direct_holdings"].append({
                    "code": code, "name": name, "market_value": mv,
                })
                continue

            # 基金: 优先 top_holdings 反推 v4 industry
            if itype in ("fund", "etf"):
                if not fp:
                    funds_without += 1
                    continue
                funds_with += 1
                indirect_mv += mv

                # 用 top_holdings 反推 (核心)
                top = fp.get("top_holdings") or []
                top_total_weight = 0.0
                top_v4_industry_contributions: Dict[str, float] = {}
                for s in top:
                    s_code = s.get("code", "")
                    s_name = s.get("name", "")
                    s_weight = float(s.get("weight", 0) or 0)
                    if s_weight <= 0:
                        continue
                    top_total_weight += s_weight
                    s_indirect_value = mv * s_weight / 100.0

                    # stocks_held_by_funds 累积
                    if s_code:
                        if s_code not in stocks_held_by_funds:
                            stocks_held_by_funds[s_code] = []
                        stocks_held_by_funds[s_code].append({
                            "fund_code": code,
                            "fund_name": name,
                            "weight_in_fund": s_weight,
                            "indirect_value": s_indirect_value,
                            "stock_name": s_name,
                        })

                    # 优先用 stock_industries 映射 v4 行业;否则用 top_holdings 自带的 industry 字段(GICS)
                    v4_industry = stock_industries.get(s_code) or s.get("industry") or "未分类"
                    top_v4_industry_contributions[v4_industry] = (
                        top_v4_industry_contributions.get(v4_industry, 0.0) + s_indirect_value
                    )

                # 把 top_holdings 反推的 contribution 加到行业
                for v4_ind, contrib in top_v4_industry_contributions.items():
                    if v4_ind not in base_with_top:
                        base_with_top[v4_ind] = _empty_industry()
                    base_with_top[v4_ind]["indirect_yi"] += contrib
                    # 同基金不同股票贡献到同行业要合并
                    existing = next((cf for cf in base_with_top[v4_ind]["contributing_funds"]
                                     if cf["code"] == code), None)
                    if existing:
                        existing["indirect_yi"] += contrib
                    else:
                        base_with_top[v4_ind]["contributing_funds"].append({
                            "code": code, "name": name,
                            "market_value": mv,
                            "industry_weight_pct": (contrib / mv * 100) if mv > 0 else 0,
                            "indirect_yi": contrib,
                            "data_status": fp.get("_data_status", "estimated"),
                            "via": "top_holdings_v4_industry_lookup",
                        })

                # 处理 top_holdings 之外的 (1 - top_total_weight)% 资产
                # 用 industry_exposure (GICS) 处理 — 但聚到"未分类(GICS派生)"或省略
                if top_total_weight < 100 and fp.get("industry_exposure"):
                    remaining_pct = (100 - top_total_weight) / 100.0
                    remaining_value = mv * remaining_pct
                    # 这部分用 industry_exposure 占比分配 (按其内部权重比例)
                    ie = fp.get("industry_exposure", {})
                    ie_total = sum(ie.values()) or 1
                    for gics_ind, w in ie.items():
                        # 标"GICS-原名"区分,不与 v4 行业混淆
                        ind_label = f"GICS·{gics_ind}"
                        contrib = remaining_value * (w / ie_total)
                        if contrib < 1:
                            continue
                        if ind_label not in base_with_top:
                            base_with_top[ind_label] = _empty_industry()
                        base_with_top[ind_label]["indirect_yi"] += contrib
                        # 不重复加 contributing_funds (已通过 top_holdings 加过)

    # 计算 total
    for ind, data in base_with_top.items():
        data["total_yi"] = round(data["direct_yi"] + data["indirect_yi"], 2)
        data["indirect_yi"] = round(data["indirect_yi"], 2)
        data["direct_yi"] = round(data["direct_yi"], 2)

    # 排序
    sorted_inds = dict(sorted(base_with_top.items(), key=lambda x: -x[1]["total_yi"]))

    return {
        "industries": sorted_inds,
        "stocks_held_by_funds": stocks_held_by_funds,
        "summary": {
            "total_market_value": round(direct_mv + indirect_mv, 2),
            "direct_market_value": round(direct_mv, 2),
            "indirect_market_value": round(indirect_mv, 2),
            "industries_count": len(sorted_inds),
            "funds_with_passthrough": funds_with,
            "funds_without_passthrough": funds_without,
            "passthrough_coverage_pct": (
                round(funds_with / (funds_with + funds_without) * 100, 1)
                if (funds_with + funds_without) > 0 else 0.0
            ),
            "method": "top_holdings_v4_industry_lookup_first_then_gics_fallback",
        },
    }


def _empty_industry() -> Dict[str, Any]:
    return {
        "direct_yi": 0.0,
        "indirect_yi": 0.0,
        "total_yi": 0.0,
        "direct_holdings": [],
        "contributing_funds": [],
    }


# ============================================================================
# Level 2 (D0-6 / 2026-06-13): 风格因子聚合 + 重叠分析
# ============================================================================

def aggregate_style_factors(classified: Dict[str, Any]) -> Dict[str, Any]:
    """风格因子聚合 — 按基金 _fund_passthrough.style 字段

    输出: {
        "size": {"大盘": ¥X, "中盘": ¥Y, "小盘": ¥Z},
        "growth_value": {"成长": ¥A, "价值": ¥B, "平衡": ¥C},
        "region": {"A股": ¥D, "美国": ¥E, "全球": ¥F},
        "fund_type": {"股票型": ¥G, "ETF联接": ¥H, "QDII": ¥I, ...},
        "raw_funds": [{"code","name","mv","style","fund_type","region"}, ...]
    }
    """
    size_dist: Dict[str, float] = {}
    gv_dist: Dict[str, float] = {}
    region_dist: Dict[str, float] = {}
    type_dist: Dict[str, float] = {}
    raw: List[Dict[str, Any]] = []

    by_class = classified.get("by_class", {}) or {}
    for klass, group in by_class.items():
        for h in group.get("holdings", []) or []:
            fp = h.get("fund_passthrough")
            if not fp:
                continue
            mv = float(h.get("market_value", 0) or 0)
            code = h.get("code", "")
            name = h.get("name", "")

            # size + growth_value
            style = fp.get("style") or {}
            size = style.get("size", "未知")
            gv = style.get("growth_value", "未知")
            size_dist[size] = size_dist.get(size, 0) + mv
            gv_dist[gv] = gv_dist.get(gv, 0) + mv

            # fund_type
            ft = fp.get("fund_type", "未知")
            type_dist[ft] = type_dist.get(ft, 0) + mv

            # region
            region_exp = fp.get("region_exposure") or {}
            if region_exp:
                for r, pct in region_exp.items():
                    region_dist[r] = region_dist.get(r, 0) + mv * float(pct) / 100
            else:
                # 无 region_exposure 视为 A股
                region_dist["A股"] = region_dist.get("A股", 0) + mv

            raw.append({
                "code": code,
                "name": name,
                "market_value": mv,
                "size": size,
                "growth_value": gv,
                "fund_type": ft,
                "region": ",".join(region_exp.keys()) if region_exp else "A股",
            })

    # 按 mv 降序排
    def sort_dist(d):
        return dict(sorted(d.items(), key=lambda x: -x[1]))

    return {
        "size": sort_dist(size_dist),
        "growth_value": sort_dist(gv_dist),
        "region": sort_dist(region_dist),
        "fund_type": sort_dist(type_dist),
        "raw_funds": raw,
        "total_fund_mv": round(sum(h["market_value"] for h in raw), 2),
    }


def detect_overlap(classified: Dict[str, Any]) -> Dict[str, Any]:
    """重叠分析 — 识别同主题多 ETF 的重复暴露 + 同股票被多基金重仓

    输出: {
        "theme_overlaps": [        ← 同主题重复(沪深300+中证500+A500 都是大盘)
            {"theme": "大盘宽基(沪深300/中证A500)", "funds": [...], "total_mv": ¥X}
        ],
        "stock_overlaps": [        ← 同股票被多基金重仓(宁德时代被 5 只基金持有)
            {"code", "name", "total_indirect_value", "fund_count", "funds": [...]}
        ],
        "summary": {
            "theme_overlap_funds_count": N,
            "stock_overlap_count": M,
            "indirect_concentration_top10": [...]
        }
    }
    """
    # 主题重叠规则 (基于 fund name 关键词)
    theme_keywords = {
        "大盘宽基": ["沪深300", "中证A500", "中证500", "中证100", "上证50", "上证100"],
        "创业板/科创板": ["创业板", "科创板", "科创50"],
        "纳指/QDII美股": ["纳斯达克", "纳指", "标普500", "美股"],
        "海外中国": ["海外中国", "中概", "互联网50", "恒生科技"],
        "AI/人工智能": ["人工智能", "AI", "算力", "芯片"],
        "新能源车/电池": ["新能源车", "新能源汽车", "电池", "动力电池"],
        "医疗医药": ["医疗", "医药", "生物科技"],
        "黄金": ["黄金", "上海金"],
        "红利": ["红利", "高分红", "股息"],
        "家电消费": ["家电", "消费", "白酒", "食品"],
        "国债/信用债": ["国债", "信用债", "国开债", "添利", "稳健", "增强回报"],
    }

    by_class = classified.get("by_class", {}) or {}
    fund_list = []
    for klass, group in by_class.items():
        for h in group.get("holdings", []) or []:
            if h.get("instrument_type") in ("fund", "etf"):
                fund_list.append({
                    "code": h.get("code", ""),
                    "name": h.get("name", ""),
                    "market_value": float(h.get("market_value", 0) or 0),
                    "fund_passthrough": h.get("fund_passthrough"),
                })

    theme_overlaps = []
    for theme, keywords in theme_keywords.items():
        matched = [f for f in fund_list
                   if any(kw in f["name"] for kw in keywords)]
        if len(matched) >= 2:  # 同主题 ≥2 只才算重叠
            total_mv = sum(f["market_value"] for f in matched)
            theme_overlaps.append({
                "theme": theme,
                "fund_count": len(matched),
                "total_mv": round(total_mv, 2),
                "funds": [{"code": f["code"], "name": f["name"], "mv": f["market_value"]} for f in matched],
                "advice": (
                    f"⚠️ 重复暴露: {len(matched)} 只 {theme} 主题基金合计 ¥{total_mv:.0f}, "
                    f"建议合并到 1-2 只代表性 ETF (低管理费/高规模) 降低费率"
                ),
            })

    theme_overlaps.sort(key=lambda x: -x["total_mv"])

    # 同股票被多基金重仓
    stock_overlaps_dict: Dict[str, Dict[str, Any]] = {}
    for f in fund_list:
        fp = f["fund_passthrough"]
        if not fp:
            continue
        for s in fp.get("top_holdings") or []:
            s_code = s.get("code", "")
            s_name = s.get("name", "")
            s_weight = float(s.get("weight", 0) or 0)
            indirect_value = f["market_value"] * s_weight / 100
            if not s_code:
                continue
            if s_code not in stock_overlaps_dict:
                stock_overlaps_dict[s_code] = {
                    "code": s_code,
                    "name": s_name,
                    "total_indirect_value": 0.0,
                    "fund_count": 0,
                    "funds": [],
                }
            stock_overlaps_dict[s_code]["total_indirect_value"] += indirect_value
            stock_overlaps_dict[s_code]["fund_count"] += 1
            stock_overlaps_dict[s_code]["funds"].append({
                "fund_code": f["code"],
                "fund_name": f["name"],
                "weight": s_weight,
                "indirect_value": round(indirect_value, 2),
            })

    # 只保留被 >=2 只基金持有 + 总间接 >=500 元的
    stock_overlaps = [v for v in stock_overlaps_dict.values()
                      if v["fund_count"] >= 2 and v["total_indirect_value"] >= 500]
    for so in stock_overlaps:
        so["total_indirect_value"] = round(so["total_indirect_value"], 2)
    stock_overlaps.sort(key=lambda x: -x["total_indirect_value"])

    # top10 间接持仓集中度
    indirect_top10 = [
        {"code": s["code"], "name": s["name"], "total_indirect_value": s["total_indirect_value"], "fund_count": s["fund_count"]}
        for s in stock_overlaps[:10]
    ]

    return {
        "theme_overlaps": theme_overlaps,
        "stock_overlaps": stock_overlaps[:30],  # 限制 30 条避免过长
        "summary": {
            "theme_overlap_count": len(theme_overlaps),
            "theme_overlap_total_mv": round(sum(t["total_mv"] for t in theme_overlaps), 2),
            "stock_overlap_count": len(stock_overlaps),
            "indirect_concentration_top10": indirect_top10,
        },
    }


def aggregate_full(classified: Dict[str, Any], stock_industries: Dict[str, str]) -> Dict[str, Any]:
    """Level 1 + Level 2 完整聚合(行业 + 风格 + 重叠)

    Returns:
        {
            "industries": {...},          # Level 1 行业聚合
            "stocks_held_by_funds": {...},
            "summary": {...},
            "style_factors": {...},        # Level 2 风格因子
            "overlap_analysis": {...},     # Level 2 重叠分析
        }
    """
    base = aggregate_to_industry_with_direct_stocks(classified, stock_industries)
    base["style_factors"] = aggregate_style_factors(classified)
    base["overlap_analysis"] = detect_overlap(classified)
    return base
