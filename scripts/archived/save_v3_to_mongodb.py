#!/usr/bin/env python3
"""save_v3_to_mongodb.py — 【已弃用 DEPRECATED，请勿使用】

⚠️ 弃用原因（2026-06-06）：
本脚本与 v3 synthesizer 实际产出的 schema 全面错位，是「组合总揽全显示
持有 / 目标 0% / 市场景气 --」的解析层根因：
  1. _as_list 不认 industry_matrix.json 的 `matrix` 键 → 矩阵读空
  2. 读 holdings_weight/target_weight/codes，而 synthesizer 写的是
     actual_weight/final_weight/positions → 现持仓恒为 0、处方关联不上
  3. go_nogo 不转大写（写 "Go"），前端严格判 === 'GO' → 全显「持有」
  4. 不计算 delta → 前端目标%列恒为 0%
  5. 不写 market/vitality_level/lifecycle/source → 市场、景气列恒 '--'
  6. 写错挂载点（market_intel.industries），capital_plan.json 不落库

✅ 正确替代：scripts/ingest_advice.py
   它把以上 6 点全部修对，并写到后端主路径优先读的顶层 `industry_matrix`。
   run.sh 已切换为调用 ingest_advice.py。

本文件仅作历史留存，不再被 run.sh 调用，请勿在新流程中引用。

---
原 docstring：
v3 编排器产物 → MongoDB

读 v3 编排器的固定 schema 产物：
    final_prescription.json   逐持仓处方数组
    industry_matrix.json      行业矩阵数组
    （可选）risk_assessment.json / macro_verdict.json / industry_allocations.json

写出与前端兼容的 portfolio_advice + industry_coverage（沿用 save_to_mongodb.py 的文档形状）。

用法: python scripts/save_v3_to_mongodb.py --dir <data_dir>

注：旧的 save_to_mongodb.py 绑定 step1-9 结构，保留作旧路径回退；本文件专供 v3。
"""

import argparse
import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _jls(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _as_list(v: Any) -> List[dict]:
    if isinstance(v, list):
        return [x for x in v if isinstance(x, dict)]
    if isinstance(v, dict):
        for key in ("prescription", "prescriptions", "items", "allocations", "industries"):
            if isinstance(v.get(key), list):
                return [x for x in v[key] if isinstance(x, dict)]
    return []


def _num(v: Any, dflt: float = 0.0) -> float:
    try:
        return round(float(v), 1)
    except (TypeError, ValueError):
        return dflt


async def save(data_dir: str) -> bool:
    run_dir = Path(data_dir)

    presc_raw = _jls(run_dir / "final_prescription.json")
    if presc_raw is None:
        print("错误: 缺少 final_prescription.json（v3 合成阶段未产出）")
        return False

    prescriptions_in = _as_list(presc_raw)
    if not prescriptions_in:
        print("错误: final_prescription.json 为空或格式不符")
        return False

    matrix_in = _as_list(_jls(run_dir / "industry_matrix.json"))
    portfolio = _jls(run_dir / "data_portfolio.json") or {}
    risk = _jls(run_dir / "risk_assessment.json") or {}
    macro = _jls(run_dir / "macro_verdict.json") or {}
    allocations = _as_list(_jls(run_dir / "industry_allocations.json"))

    run_id = run_dir.name
    user_id = portfolio.get("user_id", "") or "6a094caea814b57d3357fa0b"

    # ── 规整处方 ──
    pos_map = {p.get("code", ""): p for p in portfolio.get("positions", [])}
    prescriptions: List[dict] = []
    for rx in prescriptions_in:
        code = str(rx.get("code", ""))
        pos = pos_map.get(code, {})
        cur_w = _num(rx.get("current_weight", pos.get("weight", 0)))
        prescriptions.append({
            "code": code,
            "name": rx.get("name", pos.get("name", code)),
            "action": rx.get("action", "hold"),
            "current_weight": cur_w,
            "target_weight": _num(rx.get("target_weight", cur_w)),
            "capital_source": rx.get("capital_source", ""),
            "timing": rx.get("timing", "conditional"),
            "suggested_price": rx.get("suggested_price", ""),
            "reasoning": str(rx.get("reasoning", ""))[:500],
            "priority": rx.get("priority", "normal"),
            "pnl_pct": _num(pos.get("pnl_pct", 0)),
            "market_value": pos.get("market_value_cny", 0),
        })

    # ── 规整行业矩阵 ──
    alloc_map = {a.get("industry", ""): a for a in allocations}
    industries: List[dict] = []
    for m in matrix_in:
        name = m.get("industry", "")
        alloc = alloc_map.get(name, {})
        industries.append({
            "industry": name,
            "holdings_weight": _num(m.get("holdings_weight", 0)),
            "target_weight": _num(m.get("target_weight", alloc.get("final_weight", 0))),
            "position_count": m.get("position_count", len(m.get("codes", []))),
            "codes": m.get("codes", []),
            "names": m.get("names", []),
            "go_nogo": m.get("go_nogo", alloc.get("go_nogo", "Watch")),
            "depth": m.get("depth", "deep"),
            "reasoning": m.get("reasoning", alloc.get("reasoning", "")),
        })

    now = datetime.now(timezone.utc)
    doc = {
        "advice_id": str(uuid.uuid4()),
        "run_id": run_id,
        "source": "claude-code-workflow-v3",
        "user_id": user_id,
        "status": "COMPLETED",
        "macro_judge_verdict": json.dumps(macro, ensure_ascii=False, indent=2) if macro else "",
        "market_intel": {"industries": industries},
        "risk_director_review": json.dumps(risk, ensure_ascii=False, indent=2) if risk else "",
        "prescription": prescriptions,
        "selected_industries": [i["industry"] for i in industries],
        "created_at": now,
        "completed_at": now.isoformat(),
        "analyzed_at": now.isoformat(),
        "elapsed_seconds": 0,
        "data_dir": str(run_dir),
    }

    from app.core.database import init_database, get_mongo_db
    await init_database()
    db = get_mongo_db()

    for attempt in range(3):
        try:
            await db["portfolio_advice"].update_one(
                {"run_id": run_id, "source": "claude-code-workflow-v3"},
                {"$set": doc}, upsert=True,
            )
            cov = 0
            for ind in industries:
                await db["industry_coverage"].update_one(
                    {"user_id": user_id, "industry_name": ind["industry"]},
                    {"$set": {
                        "industry_name": ind["industry"],
                        "user_id": user_id,
                        "market": "cn",
                        "go_nogo": ind["go_nogo"],
                        "lifecycle": "",
                        "depth": ind["depth"],
                        "reasoning": ind["reasoning"],
                        "confidence": "",
                        "holdings_weight": ind["holdings_weight"],
                        "target_weight": ind["target_weight"],
                        "position_codes": ind["codes"],
                        "position_names": ind["names"],
                        "position_count": ind["position_count"],
                        "analyzed_at": now.isoformat(),
                        "advice_id": doc["advice_id"],
                        "status": "completed",
                    }},
                    upsert=True,
                )
                cov += 1

            actions: dict = {}
            for p in prescriptions:
                actions[p["action"]] = actions.get(p["action"], 0) + 1
            print(f"✅ v3 处方已保存 (run_id={run_id})")
            print(f"   处方: {len(prescriptions)} 条 · 操作分布 {actions}")
            print(f"   行业覆盖: {cov} 个行业已同步")
            return True
        except Exception as e:
            if attempt < 2:
                print(f"[WARNING] MongoDB write retry {attempt + 1}: {e}")
                time.sleep(2)
            else:
                print(f"❌ MongoDB write failed: {e}")
                return False
    return False


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dir", required=True)
    a = p.parse_args()
    sys.exit(0 if asyncio.run(save(a.dir)) else 1)


if __name__ == "__main__":
    main()
