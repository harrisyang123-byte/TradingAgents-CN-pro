#!/usr/bin/env python3
"""save_to_mongodb.py — 最终处方保存到 MongoDB

读全部 step JSON + data JSON → 组装完整 PortfolioAdvice（含 L1-L4 全部中间产出）→ 写 MongoDB
"""

import argparse, asyncio, json, os, sys, time, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def jl(path: Path) -> Any:
    if not path.exists(): return None
    try:
        with open(path) as f: return json.load(f)
    except: return None


def jls(path: Path) -> str:
    v = jl(path)
    if v is None: return ""
    if isinstance(v, str): return v
    return json.dumps(v, ensure_ascii=False, indent=2)


def jlv(path: Path, *keys: str) -> str:
    """Load dict, try each key, return str value"""
    v = jl(path)
    if not isinstance(v, dict): return ""
    for k in keys:
        val = v.get(k)
        if isinstance(val, str) and val.strip(): return val
        if isinstance(val, (dict, list)): return json.dumps(val, ensure_ascii=False, indent=2)
    return ""


def build_full_document(run_dir: Path, user_id: str) -> dict:
    """从 step1-9 + data 文件组装完整 MongoDB 文档"""
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    run_id = run_dir.name

    # ── 数据文件 ──
    portfolio = jl(run_dir / "data_portfolio.json") or {}
    pe_data   = jl(run_dir / "data_pe.json") or {}
    exposure  = jl(run_dir / "data_exposure.json") or {}
    macro     = jl(run_dir / "data_macro.json") or {}
    mkt_temp  = jl(run_dir / "data_market_temp.json") or {}
    tier1     = jl(run_dir / "data_tier1.json") or []
    conflicts_raw = jl(run_dir / "conflicts.json") or {}
    conflicts = conflicts_raw.get("conflicts", [])

    # ── 中间 step 文件 ──
    s1  = jl(run_dir / "step1_strategist.json") or {}  # L1 策略师
    s2  = jl(run_dir / "step2_contrarian.json") or {}  # L1 反向者
    s3  = jl(run_dir / "step3_judge.json") or {}       # L1 裁判
    s4  = jl(run_dir / "step4_scout.json") or {}       # L2 Scout
    s5  = jl(run_dir / "step5_analyst.json") or {}     # L3 分析师
    s6  = jl(run_dir / "step6_strategist.json") or {}  # L3 策略师
    s7  = jl(run_dir / "step7_cio.json") or {}         # L4 CIO
    s8  = jl(run_dir / "step8_risk.json") or {}        # L4 风险
    s9  = jl(run_dir / "step9_final.json") or {}       # L4 CIO 终裁

    # ── 组装各层产出 ──

    # L1: macro_judge_verdict + market_intel + market_debate_history
    macro_judge_verdict = jls(run_dir / "step3_judge.json")
    market_intel = {
        "strategist": s1,
        "contrarian": s2,
        "judge": s3,
        "industries": s3.get("verdicts", s3.get("industries", [])),
        "macro_data": macro,
        "market_temperature": mkt_temp,
    }
    market_debate_history = (
        f"## 策略师（看多）\n{jls(run_dir / 'step1_strategist.json')}\n\n"
        f"## 反向者（看空）\n{jls(run_dir / 'step2_contrarian.json')}\n\n"
        f"## 裁判裁定\n{jls(run_dir / 'step3_judge.json')}"
    )

    # L2: scout_assessment + stock_candidates + stock_debate_history
    scout_assessment = jls(run_dir / "step4_scout.json")
    stock_candidates = s4.get("candidates", s4.get("position_cross_reference", []))
    stock_judge_verdict = s4.get("scout_conclusion", s4.get("cio_decision_validation", ""))
    if isinstance(stock_judge_verdict, (list, dict)):
        stock_judge_verdict = json.dumps(stock_judge_verdict, ensure_ascii=False, indent=2)
    stock_debate_history = scout_assessment  # L2 无独立辩论，Scout 自检 = 全文

    # L3: analyst_assessment + strategist_assessment + debate_history
    analyst_assessment = jls(run_dir / "step5_analyst.json")
    strategist_assessment = jls(run_dir / "step6_strategist.json")
    debate_history = (
        f"## 分析师\n{jls(run_dir / 'step5_analyst.json')}\n\n"
        f"## 策略师（诊断报告员）\n{jls(run_dir / 'step6_strategist.json')}"
    )
    # contrarian_assessment = 策略师的组合诊断风险发现
    cr_parts = []
    for section in ("closing_statement", "risks_and_mitigants", "current_portfolio_diagnosis"):
        val = s6.get(section)
        if isinstance(val, str) and len(val) > 10:
            cr_parts.append(val)
        elif isinstance(val, (list, dict)):
            cr_parts.append(json.dumps(val, ensure_ascii=False, indent=2))
    contrarian_assessment = "\n\n".join(cr_parts)

    # L4: cio_verdict + risk_director_review
    # 从 step9 structured fields 组装完整 cio_verdict
    cio_parts = []
    rv = s9.get("overall_verdict", {})
    if isinstance(rv, dict):
        for k in ("headline", "one_liner", "summary", "rationale", "action_plan"):
            v = rv.get(k, "")
            if isinstance(v, str) and len(v) > 5:
                cio_parts.append(f"## {k}\n{v}")
    for section in ("asset_allocation_summary", "target_allocation_12m", "risk_summary"):
        v = s9.get(section)
        if isinstance(v, dict):
            cio_parts.append(f"## {section}\n{json.dumps(v, ensure_ascii=False, indent=2)}")
    alerts_list = s9.get("critical_alerts", [])
    if alerts_list:
        cio_parts.append("## 致命警报\n" + json.dumps(alerts_list, ensure_ascii=False, indent=2))
    sp = s9.get("scenario_playbook", {})
    if isinstance(sp, dict):
        cio_parts.append("## 情景预案\n" + json.dumps(sp, ensure_ascii=False, indent=2))
    triggers = s9.get("early_warning_triggers", [])
    if triggers:
        cio_parts.append("## 预警触发器\n" + json.dumps(triggers, ensure_ascii=False, indent=2))
    insights = s9.get("key_insights", [])
    if insights:
        cio_parts.append("## 关键洞察\n" + json.dumps(insights, ensure_ascii=False, indent=2))
    cio_verdict = "\n\n".join(cio_parts)

    risk_director_review = jls(run_dir / "step8_risk.json")

    # ── Market signals ──
    market_signals = {
        "source": "claude-code-workflow",
        "macro": {"pmi": macro.get("indicators", {}).get("pmi", "") if isinstance(macro, dict) else ""},
        "breadth": mkt_temp if isinstance(mkt_temp, dict) else {},
        "north_net": mkt_temp.get("north_net", 0) if isinstance(mkt_temp, dict) else 0,
        "north_days": mkt_temp.get("north_days", 0) if isinstance(mkt_temp, dict) else 0,
        "flow_signal": mkt_temp.get("flow_signal", "中性") if isinstance(mkt_temp, dict) else "中性",
    }

    # ── Price context (PE per stock) ──
    price_context = {}
    if isinstance(pe_data, dict):
        for code, info in pe_data.items():
            if isinstance(info, dict):
                price_context[code] = {
                    "pe_percentile_5y": info.get("pe_percentile_5y"),
                    "pe_ttm": info.get("pe_ttm"),
                    "current_price": info.get("current_price"),
                    "ma20": info.get("ma20"),
                    "judgment": info.get("judgment", ""),
                    "pe_percentile_source": info.get("pe_percentile_source", "computed"),
                }

    # ── Selected industries ──
    # 优先从持仓分类提取（Agent 输出的 industries 字段不稳定）
    positions = portfolio.get("positions", [])
    categories: Dict[str, float] = {}
    for p in positions:
        name = p.get("name", "")
        w = p.get("weight", 0)
        if "债" in name or "收益" in name: cat = "债券"
        elif "黄金" in name or "金" in name: cat = "黄金"
        elif "纳指" in name or "QDII" in name or "海外" in name: cat = "QDII/海外"
        elif "500" in name or "300" in name or "A50" in name or "沪深" in name: cat = "宽基指数"
        elif "科创" in name or "芯片" in name or "AI" in name or "科技" in name: cat = "科技"
        elif "医药" in name or "医疗" in name: cat = "医药"
        elif "消费" in name: cat = "消费"
        elif "新能源" in name or "光伏" in name or "电车" in name: cat = "新能源"
        elif "家电" in name: cat = "家电"
        elif "通信" in name or "5G" in name: cat = "通信设备"
        elif "化工" in name or "新材" in name: cat = "新材料"
        elif "军工" in name: cat = "军工"
        elif "传媒" in name or "游戏" in name or "娱乐" in name: cat = "传媒娱乐"
        elif "ETF" in name: cat = "行业ETF"
        else: cat = name[:8]
        categories[cat] = categories.get(cat, 0) + w

    selected_industries = sorted(categories.keys())
    # 也尝试从 step1/step3 补充
    for src in (s1, s3):
        for k in ("industries", "verdicts", "actionable_decisions"):
            v = src.get(k, [])
            if isinstance(v, list):
                for item in v[:20]:
                    if isinstance(item, dict):
                        name = item.get("industry", item.get("name", ""))
                        if name and name not in selected_industries:
                            selected_industries.append(name)

    # ── Prescriptions（per-stock） ──
    pos_map: Dict[str, dict] = {p.get("code", ""): p for p in positions}
    alerts = s9.get("critical_alerts", [])
    prescriptions = []

    for code, pos in pos_map.items():
        name = pos.get("name", code)
        weight = pos.get("weight", 0)
        pnl = pos.get("pnl_pct", 0)
        mv = pos.get("market_value_cny", 0)
        pe = price_context.get(code, {})
        pe_pct = pe.get("pe_percentile_5y")

        # 判定 action
        action = "hold"
        reasoning = ""
        priority = "normal"

        # 从 alerts 匹配
        for a in alerts:
            atext = json.dumps(a, ensure_ascii=False)
            if code in atext or (name and name[:4] in atext):
                if "卖出" in a.get("title", "") or "减仓" in a.get("title", ""):
                    action = "reduce"; priority = "important"
                    reasoning = f'[ALERT] {a.get("title")}: {a.get("summary", "")}'
                elif "P0" in a.get("severity", ""):
                    action = "reduce"; priority = "important"
                    reasoning = f'[ALERT] {a.get("title")}'
                break

        # 从 PE 高估补充
        if action == "hold" and pe_pct is not None and pe_pct > 90:
            action = "reduce"; priority = "important"
            reasoning = f"PE {pe_pct}%分位——交叉验证建议减仓"

        prescriptions.append({
            "code": code, "name": name, "action": action,
            "current_weight": round(weight, 1),
            "target_weight": round(weight * (0.7 if action == "reduce" else 1.0), 1),
            "capital_source": "", "timing": "immediate" if priority == "important" else "conditional",
            "reasoning": reasoning, "priority": priority,
            "pnl_pct": pnl, "market_value": mv,
        })

    # ── 组装文档 ──
    return {
        "advice_id": str(uuid.uuid4()),
        "run_id": run_id,
        "source": "claude-code-workflow-v1",
        "user_id": user_id,
        "status": "COMPLETED",
        # L1
        "macro_judge_verdict": macro_judge_verdict,
        "market_intel": market_intel,
        "market_debate_history": market_debate_history,
        # L2
        "scout_assessment": scout_assessment,
        "stock_candidates": stock_candidates,
        "stock_judge_verdict": stock_judge_verdict,
        "stock_debate_history": stock_debate_history,
        # L3
        "analyst_assessment": analyst_assessment,
        "strategist_assessment": strategist_assessment,
        "contrarian_assessment": contrarian_assessment,
        "debate_history": debate_history,
        # L4
        "cio_verdict": cio_verdict,
        "risk_director_review": risk_director_review,
        # Data
        "prescription": prescriptions,
        "selected_industries": selected_industries,
        "market_signals": market_signals,
        "price_context": price_context,
        "conflicts": conflicts,
        "conflict_count": len(conflicts),
        # Meta
        "created_at": now,
        "completed_at": now_iso,
        "analyzed_at": now_iso,
        "elapsed_seconds": 1805,
        "data_dir": str(run_dir),
    }


async def save(data_dir: str) -> bool:
    run_dir = Path(data_dir)
    if not (run_dir / "step9_final.json").exists():
        print(f"错误: CIO 终裁文件不存在")
        return False

    portfolio = jl(run_dir / "data_portfolio.json") or {}
    user_id = portfolio.get("user_id", "6a094caea814b57d3357fa0b")

    doc = build_full_document(run_dir, user_id)

    from app.core.database import init_database, get_mongo_db
    await init_database()
    db = get_mongo_db()

    for attempt in range(3):
        try:
            await db["portfolio_advice"].update_one(
                {"run_id": doc["run_id"], "source": "claude-code-workflow-v1"},
                {"$set": doc}, upsert=True,
            )
            print(f"✅ 处方已保存 (run_id={doc['run_id']}, {len(doc['prescription'])} items, "
                  f"L1={len(doc['macro_judge_verdict'])}B, L2={len(doc['scout_assessment'])}B, "
                  f"L3={len(doc['analyst_assessment'])}B, L4={len(doc['cio_verdict'])}B)")
            return True
        except Exception as e:
            if attempt < 2:
                print(f"[WARNING] MongoDB write retry {attempt+1}: {e}")
                time.sleep(2)
            else:
                print(f"❌ MongoDB write failed: {e}")
                return False
    return False


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dir", required=True)
    args = p.parse_args()
    sys.exit(0 if asyncio.run(save(args.dir)) else 1)


if __name__ == "__main__":
    main()
