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


# ════════════════════════════════════════════════════════════════════
# 文件输入模式（B 档「文件总线」）——叠加式，不影响下方 Mongo 全量路径
#
# Pod 内没有 MongoDB，但持仓/watchlist/Tier1 这三类输入本来就在本地 Mongo。
# 文件模式下用本地导出的 JSON 替代这 3 处 Mongo 读取（export_inputs.py 产出），
# 其余联网采集环节（PE / 宏观 / 市场水温 / 景气打分）两模式完全共用、零改动。
# ════════════════════════════════════════════════════════════════════

def _read_json_file(path: Path, default):
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"    警告: 无法解析 {path.name}: {e}")
        return default


def load_portfolio_from_file(portfolio_file: Path) -> dict:
    """读取本地导出的 holdings.json，归一成与 get_portfolio_summary 同构的 summary。

    接受两种形态：
      ① 完整 summary dict: {available_cash, total_assets, positions:[...]}（推荐，export_inputs 产出）
      ② 裸 positions 列表: [...]（此时 total_assets/available_cash 需在文件里另带，缺则置 0）
    每条 position 至少含 code/name/weight；scan pool 还会用到 industry 字段。
    """
    raw = _read_json_file(portfolio_file, None)
    if raw is None:
        raise FileNotFoundError(f"持仓文件不存在或无法解析: {portfolio_file}")
    if isinstance(raw, list):
        summary = {"positions": raw, "available_cash": 0, "total_assets": 0}
    elif isinstance(raw, dict):
        summary = dict(raw)
        summary.setdefault("positions", [])
        summary.setdefault("available_cash", 0)
        summary.setdefault("total_assets", 0)
    else:
        raise ValueError(f"持仓文件格式不支持（应为 dict 或 list）: {portfolio_file}")
    return summary


def build_scan_pool_from_inputs(positions, watchlist_industries, vitality_scores,
                                all_industries: bool = False):
    """文件版扫描池：复刻 industry_scan_pool.build_scan_pool 的去重/来源标注逻辑，
    但来源换成 持仓 positions[].industry + watchlist 文件 + 景气打分（不碰 Mongo）。

    industry_coverage 缓存检查在文件模式下不可用（无 Mongo），一律 cached=False。
    返回与 build_scan_pool 同类型的 IndustryScanPool，下游 to_industry_list/to_dict 一致。
    """
    from app.services.industry_scan_pool import (
        IndustryScanItem, IndustryScanPool, CURRENCY_BUCKETS)

    scan_set = {}
    # 1. 持仓行业（必选）
    for p in positions:
        ind = (p.get("industry") or "").strip()
        if ind and ind not in ("未分类",) and ind not in scan_set:
            scan_set[ind] = IndustryScanItem(industry=ind, source="holding")
    # 2. watchlist（必选）
    for ind in watchlist_industries:
        ind = (ind or "").strip()
        if ind and ind not in scan_set:
            scan_set[ind] = IndustryScanItem(industry=ind, source="watchlist")
    # 3. 景气打分（默认 top3；all_industries 时纳入全部可投资行业，均无估值闸）
    candidates = list(vitality_scores) if all_industries else [
        s for s in vitality_scores if getattr(s, "top3_flag", False)]
    for score in candidates:
        if score.industry in CURRENCY_BUCKETS:
            continue
        if score.industry not in scan_set:
            scan_set[score.industry] = IndustryScanItem(
                industry=score.industry, source="vitality",
                vitality_score=score.total_score)
    return IndustryScanPool(industries=list(scan_set.values()))


async def collect_all(user_id: str, out_dir: Path, all_industries: bool = False,
                      allow_partial: bool = False,
                      portfolio_file: Path = None,
                      watchlist_file: Path = None,
                      tier1_file: Path = None) -> bool:
    """全量数据收集

    all_industries: 为 True 时，行业扫描池纳入全部可投资行业（全量深辩），
        否则只取 持仓 + watchlist + 景气top3（默认增量范围）。
    allow_partial: 默认 False = 严格模式。关键市场数据（宏观指标 / 市场水温 / 北向资金）
        缺任一即中止采集并返回 False，下游 LLM 分析根本不会启动——
        贯彻「拿不到数据就不分析，绝不在数据盲区出处方」。
        置 True 仅供接力/调试时绕过硬闸（缺数据时会改为告警放行）。
    portfolio_file: 给定即进入「文件输入模式」（B 档文件总线）——持仓/Tier1/扫描池
        三处 Mongo 读取改用本地导出的 JSON，跳过 init_database()。其余联网采集
        （PE/宏观/水温/景气）与 Mongo 模式完全一致。不给则走原 Mongo 全量路径。
    watchlist_file / tier1_file: 文件模式下的可选输入（缺省 → 空），仅文件模式生效。
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    warnings = []
    file_mode = portfolio_file is not None
    if file_mode:
        print(f"  ▶ 文件输入模式（脱离 MongoDB）：持仓={portfolio_file}")

    # —— 1. 持仓数据 ——
    print("  [1/7] 收集持仓数据...")
    try:
        if file_mode:
            # 文件模式：读本地导出的 holdings.json，不连 Mongo
            summary = load_portfolio_from_file(portfolio_file)
            positions = summary.get("positions", [])
        else:
            from app.core.database import init_database
            from app.services.portfolio_service import PortfolioService
            await init_database()
            svc = PortfolioService()
            summary = await svc.get_portfolio_summary(user_id)
            positions = summary.get("positions", [])

        if not positions:
            print("  错误: 当前用户无持仓数据，无法进行分析")
            return False

        # 整理持仓数据（两模式产物结构一致，下游 ingest/build_snapshot 无感知）
        portfolio_data = {
            "collected_at": datetime.now(timezone.utc).isoformat() + "Z",
            "status": "success",
            "user_id": user_id,
            "input_mode": "file" if file_mode else "mongo",
            "available_cash": summary.get("available_cash", 0),
            "total_assets": summary.get("total_assets", 0),
            "position_count": len(positions),
            "positions": positions,
        }
        with open(out_dir / "data_portfolio.json", "w") as f:
            json.dump(portfolio_data, f, ensure_ascii=False, default=str)
        cash = summary.get("available_cash", 0)
        total = summary.get("total_assets", 1) or 1
        print(f"    {len(positions)} 只持仓, 总资产 ¥{total:.0f}, 现金 ¥{cash:.0f} ({cash/total*100:.0f}%)")
    except Exception as e:
        print(f"  错误: {e}")
        return False

    # —— 2. Tier1 报告 ——
    print("  [2/7] 收集 Tier1 报告...")
    if file_mode:
        # 文件模式：读本地导出的 tier1_reports.json（可空）
        reports = _read_json_file(tier1_file, []) if tier1_file else []
        if not isinstance(reports, list):
            reports = []
        with open(out_dir / "data_tier1.json", "w") as f:
            json.dump(reports, f, ensure_ascii=False, default=str)
        print(f"    {len(reports)} 份 Tier1 报告（文件输入）")
    else:
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
    if file_mode:
        # 文件模式：基金穿透需 Mongo 基金持仓库，Pod 无法做 → 降级为「仅直接个股敞口」。
        # 敞口是次要信号（仅告警级），降级不阻断分析；如实标注 penetration unavailable。
        try:
            stocks = [p for p in positions if p.get("instrument_type", "stock") == "stock"]
            total_w = sum(float(p.get("weight", 0) or 0) for p in positions) or 1.0
            norm = 100.0 / total_w
            exps = sorted(
                ({"code": p.get("code", ""), "name": p.get("name", p.get("code", "")),
                  "direct": round(float(p.get("weight", 0) or 0) * norm, 1),
                  "fund": 0.0, "total": round(float(p.get("weight", 0) or 0) * norm, 1)}
                 for p in stocks if p.get("code")),
                key=lambda x: x["total"], reverse=True)
            hhi = round(sum((e["total"]) ** 2 for e in exps) / 10000, 3)
            exposure = {
                "hhi": hhi, "penetration_ratio": 0.0,
                "exposures": exps, "overlaps": [],
                "note": "file_mode: 仅直接个股敞口，基金穿透需 Mongo 不可用",
            }
            with open(out_dir / "data_exposure.json", "w") as f:
                json.dump(exposure, f, ensure_ascii=False, default=str)
            print(f"    HHI: {exposure['hhi']}（文件模式·仅直接持仓，基金穿透跳过）")
        except Exception as e:
            print(f"  警告: 敞口数据（文件模式）计算失败: {e}")
            warnings.append("Exposure file-mode partial")
            with open(out_dir / "data_exposure.json", "w") as f:
                json.dump({"hhi": 0, "status": "unavailable"}, f)
    else:
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
    # status 初值 pending —— 取到才置 success，绝不预设 success 让缺失蒙混过关
    macro_data = {"status": "pending", "collected_at": datetime.now(timezone.utc).isoformat() + "Z"}
    try:
        from tradingagents.agents.advisors.market_tools import (
            get_macro_indicators, get_industry_rankings, get_sector_fund_flows)
        indicators = get_macro_indicators.func() or {}
        macro_data["indicators"] = indicators
        macro_data["industry_rankings"] = get_industry_rankings.func() or []
        macro_data["sector_fund_flows"] = get_sector_fund_flows.func() or []
        # 关键宏观指标（PMI/利率等）没取到 → partial，下游须按数据盲区降级
        macro_data["status"] = "success" if indicators else "partial"
        if not indicators:
            warnings.append("Macro indicators empty (PMI/利率等未取到)")
        print(f"    宏观指标: {len(indicators)} 项, "
              f"行业排名: {len(macro_data.get('industry_rankings', []))} 行业, "
              f"资金流向: {len(macro_data.get('sector_fund_flows', []))} 行业")
    except Exception as e:
        print(f"  警告: 宏观数据收集失败: {e}")
        macro_data["status"] = "unavailable"
        macro_data.setdefault("indicators", {})
        warnings.append("Macro data unavailable")

    with open(out_dir / "data_macro.json", "w") as f:
        json.dump(macro_data, f, ensure_ascii=False, default=str)

    # —— 6. 市场温度 ——
    print("  [6/7] 收集市场温度数据...")

    def _src_ok(res):
        """判断 fetch_* 是否真取到数据。
        fetch_* 失败/空时会返回带 source='error:...' 或 '...empty' 的 dict，
        并把 north_net/margin_balance 等字段填成 0 —— 这是「假中性」的根源。
        只有 source 既非 error 也非 empty，才算真实读到。"""
        if not isinstance(res, dict):
            return False
        src = str(res.get("source", ""))
        return bool(src) and not src.startswith("error") and not src.endswith("empty")

    market_temp = {
        "collected_at": datetime.now(timezone.utc).isoformat() + "Z",
        "status": "pending",
        # 默认一律 null —— 未取到就是未取到，绝不用 0 / 中性 / up_ratio=50 伪装成真实读数，
        # 否则下游宏观裁判/战略师会把「数据盲区」误读成「中性行情」从而放心加仓。
        "north_net": None, "north_days": None, "north_direction": None,
        "breadth_signal": None, "up_ratio": None,
        "limit_up": None, "limit_down": None,
        "margin_balance": None, "margin_change_pct": None,
        "flow_signal": None,
        "data_availability": {"breadth": "unavailable", "north": "unavailable", "margin": "unavailable"},
    }
    try:
        from app.services.market_signals import fetch_market_breadth, fetch_north_flow, fetch_margin_data
        breadth, north, margin = await asyncio.gather(
            fetch_market_breadth(), fetch_north_flow(), fetch_margin_data(), return_exceptions=True)
        if _src_ok(breadth):
            market_temp["breadth_signal"] = breadth.get("breadth_signal")
            market_temp["up_ratio"] = breadth.get("up_ratio")
            market_temp["limit_up"] = breadth.get("limit_up")
            market_temp["limit_down"] = breadth.get("limit_down")
            market_temp["data_availability"]["breadth"] = "ok"
        if _src_ok(north):
            # 修正 key 错配：fetch_north_flow 返回 north_net/north_days（不是 net_flow/consecutive_days）
            nn = north.get("north_net")
            market_temp["north_net"] = nn
            market_temp["north_days"] = north.get("north_days")
            if isinstance(nn, (int, float)):
                market_temp["north_direction"] = "净流入" if nn > 0 else ("净流出" if nn < 0 else "中性")
                market_temp["flow_signal"] = (
                    "大幅流入" if nn > 50 else "流入" if nn > 10 else
                    "中性" if nn > -10 else "流出" if nn > -50 else "大幅流出")
            market_temp["data_availability"]["north"] = "ok"
        if _src_ok(margin):
            # 修正 key 错配：fetch_margin_data 返回 margin_balance（不是 balance）
            market_temp["margin_balance"] = margin.get("margin_balance")
            market_temp["data_availability"]["margin"] = "ok"
        ok_n = sum(1 for v in market_temp["data_availability"].values() if v == "ok")
        market_temp["status"] = "success" if ok_n == 3 else ("partial" if ok_n else "unavailable")
        if ok_n < 3:
            missing = [k for k, v in market_temp["data_availability"].items() if v != "ok"]
            warnings.append(f"Market temperature degraded: {','.join(missing)} unavailable ({ok_n}/3)")
        print(f"    水温: {market_temp['breadth_signal'] or '数据不可用'}, "
              f"北向: {market_temp['north_direction'] or '数据不可用'}, "
              f"可用源: {ok_n}/3")
    except Exception as e:
        print(f"  警告: 市场温度数据收集失败: {e}")
        market_temp["status"] = "unavailable"
        warnings.append("Market temperature unavailable")

    with open(out_dir / "data_market_temp.json", "w") as f:
        json.dump(market_temp, f, ensure_ascii=False, default=str)

    # —— 数据硬闸：关键市场气候数据「必须拿到」，否则中止本次分析 ——
    # 用户铁律：拿不到数据就不许继续分析，绝不在数据盲区出处方。
    # 关键源（缺任一即中止）——它们是宏观裁判/战略师判定 risk-on/off
    # 与 total_weight_limit / cash_floor 的硬输入，缺失=决策层在盲区里拍脑袋加仓：
    #   ① 宏观指标(PMI/利率等)  ② 市场水温(涨跌广度)  ③ 北向资金
    # 次要源（融资/Tier1/PE/敞口/景气）缺失仍只告警，不阻断——避免单个二级慢信号
    # 偶发抓不到就瘫痪整条链。确需在缺数据下调试可加 --allow-partial-data 绕过本闸。
    critical_missing = []
    if macro_data.get("status") != "success" or not macro_data.get("indicators"):
        critical_missing.append("宏观指标(PMI/利率等)")
    if market_temp["data_availability"].get("breadth") != "ok":
        critical_missing.append("市场水温(涨跌广度)")
    if market_temp["data_availability"].get("north") != "ok":
        critical_missing.append("北向资金")

    if critical_missing:
        if allow_partial:
            print(f"\n  ⚠ 关键数据缺失，但 --allow-partial-data 已开启，强行继续: "
                  f"{', '.join(critical_missing)}")
            warnings.append(f"CRITICAL data missing but bypassed: {', '.join(critical_missing)}")
        else:
            print("\n  ❌ 关键市场数据未取到，按「数据盲区不出处方」铁律中止本次分析：")
            for m in critical_missing:
                print(f"       - {m}（未取到）")
            print("     这些是宏观/大类层判定 risk-on/off 与仓位上限、现金下限的硬输入，")
            print("     缺失即无法可靠决策 —— 中止，不进入 Agent 分析阶段。")
            print("     处置：检查网络 / AKShare 可用性后重跑 collect；")
            print("     确需在缺数据下调试，可加 --allow-partial-data 绕过本闸（仅调试用）。")
            return False

    # —— 7. 行业扫描池 + 全量景气榜 ——
    # 全量18行业景气打分（廉价雷达，喂前端矩阵）只跑一次，
    # 复用给扫描池构建（深辩范围=持仓+watchlist+景气top3，无估值闸）
    print("  [7/7] 全量景气打分 + 行业扫描池...")
    try:
        from dataclasses import asdict
        from app.services.industry_vitality import score_all_industries

        # 景气打分纯联网（不碰 Mongo），两模式共用
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
        if file_mode:
            # 文件模式：持仓行业取 positions[].industry，watchlist 取文件，不碰 Mongo
            wl_raw = _read_json_file(watchlist_file, []) if watchlist_file else []
            watchlist_industries = []
            for w in (wl_raw if isinstance(wl_raw, list) else []):
                # 兼容 ["半导体", ...] 或 [{"industry": "半导体"}, ...]
                watchlist_industries.append(w if isinstance(w, str) else w.get("industry", ""))
            pool = build_scan_pool_from_inputs(
                positions, watchlist_industries, vitality_scores,
                all_industries=all_industries)
        else:
            from app.core.database import get_mongo_db
            from app.services.industry_scan_pool import build_scan_pool
            db = get_mongo_db()
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
    parser.add_argument(
        "--allow-partial-data", action="store_true",
        help="绕过关键数据硬闸：默认关键市场数据(宏观/水温/北向)缺任一即中止；"
             "加此开关仅在缺数据时改为告警放行（接力/调试用，慎用）",
    )
    # —— 文件输入模式（B 档文件总线）：叠加式，不给则走原 Mongo 全量路径 ——
    parser.add_argument(
        "--portfolio-file", default=None,
        help="持仓 JSON 文件（holdings.json）。给定即进入文件输入模式，"
             "脱离 MongoDB（持仓/Tier1/扫描池改读文件，PE/宏观/水温/景气仍联网）",
    )
    parser.add_argument(
        "--watchlist-file", default=None,
        help="关注行业 JSON 文件（watchlist.json，可选）。仅文件模式生效",
    )
    parser.add_argument(
        "--tier1-file", default=None,
        help="个股深度分析导出 JSON（tier1_reports.json，可选）。仅文件模式生效",
    )
    args = parser.parse_args()

    file_mode = bool(args.portfolio_file)

    # user_id 校验：Mongo 模式必须 24 位 hex（用于查库）；
    # 文件模式 user_id 仅作文档元信息标签，放宽校验（允许 file-bus 等占位）
    if not file_mode:
        if not (len(args.user_id) == 24 and all(c in "0123456789abcdef" for c in args.user_id.lower())):
            print(f"错误: Invalid user_id format: must be 24-character hex string")
            sys.exit(1)

    out_dir = Path(args.out_dir)
    success = asyncio.run(collect_all(
        args.user_id, out_dir,
        all_industries=(args.industries == "all"),
        allow_partial=args.allow_partial_data,
        portfolio_file=Path(args.portfolio_file) if args.portfolio_file else None,
        watchlist_file=Path(args.watchlist_file) if args.watchlist_file else None,
        tier1_file=Path(args.tier1_file) if args.tier1_file else None,
    ))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
