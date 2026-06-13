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
