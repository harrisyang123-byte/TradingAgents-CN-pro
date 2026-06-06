#!/usr/bin/env python3
"""ingest_advice.py — 把 v3 workflow 产出落库为前端可读的 portfolio_advice

读取 workflow 产出的三个 JSON：
    industry_matrix.json, final_prescription.json, capital_plan.json(可选)
按「前端/后端 overview 接口期望的字段名」做映射 + 金额计算，
写入一条 status=COMPLETED 的 portfolio_advice 文档。

用法（落 MongoDB，本机真实环境）:
    python scripts/ingest_advice.py --data-dir <dir> --user-id <24hex>

用法（不连库，导出文档 JSON，用于验证字段契约）:
    python scripts/ingest_advice.py --data-dir <dir> --user-id <id> --out-json <path>

字段映射（v3 synthesizer schema → overview 契约）:
    actual_weight        -> holdings_weight
    final_weight         -> target_weight
    "Go"/"NoGo"          -> "GO"/"NOGO"   (前端严格大写判定)
    positions            -> codes          (后端用 codes 关联 prescription)
    industry             -> industry_bucket(前端按此分组处方)
    build_strategy       -> timing         (immediate/batch/conditional)
    entry_price_range    -> suggested_price("low-high" 字符串)
"""

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# 现金行业标识：与风控引擎共用同一常量，消除「现金」字面量在多处各写各的耦合。
# 兜底：最小依赖环境（仅跑 --out-json 字段契约校验、未装 toml 等）下导入失败时回退到字面量，
# 该字面量必须与 tradingagents.agents.advisors.risk_rules.CASH_INDUSTRY 保持一致。
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tradingagents.agents.advisors.risk_rules import CASH_INDUSTRY
except Exception:
    CASH_INDUSTRY = "现金"


# ── 工具 ────────────────────────────────────────────────────

def _load(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  警告: 无法解析 {path.name}: {e}")
        return default


def _round_money(n: float) -> int:
    """四舍五入到百元"""
    return int(round(n / 100.0) * 100)


def _map_go_nogo(v: Any) -> str:
    """Go/NoGo/观察 → GO/NOGO/'' （前端严格大写判定）"""
    s = str(v or "").strip().lower()
    if s in ("go", "强烈看好", "看好"):
        return "GO"
    if s in ("nogo", "no-go", "no go"):
        return "NOGO"
    return ""


def _suggested_price(epr: Any) -> str:
    """entry_price_range{low,high} | [low,high] → 'low-high' 字符串"""
    if isinstance(epr, dict):
        lo, hi = epr.get("low"), epr.get("high")
        if lo is not None and hi is not None:
            return f"{lo}-{hi}"
        if lo is not None:
            return str(lo)
    if isinstance(epr, (list, tuple)) and len(epr) >= 2:
        return f"{epr[0]}-{epr[1]}"
    if epr:
        return str(epr)
    return ""


def _action_from_delta(current: float, target: float) -> str:
    if target <= 0 and current > 0:
        return "sell"
    if current <= 0 and target > 0:
        return "new_position"
    if target > current:
        return "add"
    if target < current:
        return "reduce"
    return "hold"


# ── 核心映射 ─────────────────────────────────────────────────

def build_doc(data_dir: Path, user_id: str) -> Dict[str, Any]:
    matrix_in = _load(data_dir / "industry_matrix.json", {}) or {}
    presc_in = _load(data_dir / "final_prescription.json", {}) or {}
    capital_in = _load(data_dir / "capital_plan.json", {}) or {}
    portfolio = _load(data_dir / "data_portfolio.json", {}) or {}

    # —— 总资产口径：优先真实持仓数据，其次 capital_plan ——
    total_assets = (
        portfolio.get("total_assets")
        or capital_in.get("total_assets")
        or 0
    )
    total_assets = float(total_assets or 0)
    available_cash = float(portfolio.get("available_cash", 0) or 0)

    raw_matrix: List[Dict[str, Any]] = matrix_in.get("matrix", []) if isinstance(matrix_in, dict) else (matrix_in or [])
    raw_presc: List[Dict[str, Any]] = presc_in.get("prescription", []) if isinstance(presc_in, dict) else (presc_in or [])
    summary = presc_in.get("summary", {}) if isinstance(presc_in, dict) else {}

    # —— 1. industry_matrix 映射 ——
    matrix_out: List[Dict[str, Any]] = []
    sum_target = 0.0
    for row in raw_matrix:
        holdings_w = float(row.get("actual_weight", row.get("holdings_weight", 0)) or 0)
        target_w = float(row.get("final_weight", row.get("target_weight", 0)) or 0)
        go = _map_go_nogo(row.get("go_nogo"))
        sum_target += target_w
        matrix_out.append({
            "industry": row.get("industry", "未分类"),
            "source": row.get("source", "holding"),
            "market": row.get("market", "cn"),
            "go_nogo": go,
            "stance": row.get("stance", ""),
            # NOGO 行业是被深度研究后判定「不配置」，属于"已覆盖"；
            # 只有未被分析的行业（go 为空）才是 "never"。
            "coverage_status": "covered" if go in ("GO", "NOGO") else "never",
            "vitality_level": row.get("vitality_level", ""),
            "lifecycle": row.get("lifecycle", ""),
            "holdings_weight": round(holdings_w, 2),
            "target_weight": round(target_w, 2),
            "delta": round(target_w - holdings_w, 2),
            "gap": round(float(row.get("gap", 0) or 0), 2),
            "scout_triggered": bool(row.get("scout_triggered", False)),
            "codes": row.get("positions", row.get("codes", [])) or [],
            "reasoning": row.get("reasoning", ""),
        })

    # —— 2. prescription 映射 ——
    presc_out: List[Dict[str, Any]] = []
    for rx in raw_presc:
        current_w = float(rx.get("current_weight", 0) or 0)
        target_w = float(rx.get("target_weight", 0) or 0)
        action = rx.get("action") or _action_from_delta(current_w, target_w)
        item: Dict[str, Any] = {
            "code": rx.get("code", ""),
            "name": rx.get("name", rx.get("code", "")),
            "industry_bucket": rx.get("industry", rx.get("industry_bucket", "其他")),
            "action": action,
            "current_weight": round(current_w, 2),
            "target_weight": round(target_w, 2),
            "timing": rx.get("build_strategy", rx.get("timing", "")),
            "suggested_price": _suggested_price(rx.get("entry_price_range", rx.get("suggested_price"))),
            "entry_price_range": rx.get("entry_price_range"),
            "batch_plan": rx.get("batch_plan", []),
            "reasoning": rx.get("reasoning", ""),
            "risk_note": rx.get("risk_note", ""),
            "amount": _round_money((target_w - current_w) / 100.0 * total_assets),
        }
        pe_pct = rx.get("pe_percentile", rx.get("pe_percentile_5y"))
        if pe_pct is not None:
            item["pe_data"] = {"pe_percentile_5y": float(pe_pct)}
        presc_out.append(item)

    # —— 3. 现金行（前端 filteredMatrix 排除，但资金总览卡需要）——
    cash_target_w = float(capital_in.get("cash_weight", max(0.0, 100.0 - sum_target)))
    cash_holdings_w = round(available_cash / total_assets * 100, 2) if total_assets else 0.0
    matrix_out.append({
        "industry": CASH_INDUSTRY,
        "source": "holding",
        "market": "",
        "go_nogo": "",
        "coverage_status": "covered",
        "vitality_level": "",
        "holdings_weight": cash_holdings_w,
        "target_weight": round(cash_target_w, 2),
        "delta": round(cash_target_w - cash_holdings_w, 2),
        "gap": 0,
        "scout_triggered": False,
        "codes": [],
        "reasoning": "现金缓冲",
    })

    # —— 4. capital_plan（金额口径以真实 total_assets 为准重算）——
    allocations: List[Dict[str, Any]] = []
    invested_amount = 0
    for row in matrix_out:
        if row["industry"] == CASH_INDUSTRY:
            continue
        cur_amt = _round_money(row["holdings_weight"] / 100.0 * total_assets)
        tgt_amt = _round_money(row["target_weight"] / 100.0 * total_assets)
        invested_amount += tgt_amt
        allocations.append({
            "industry": row["industry"],
            "go_nogo": row["go_nogo"],
            "current_weight": row["holdings_weight"],
            "target_weight": row["target_weight"],
            "current_amount": cur_amt,
            "target_amount": tgt_amt,
            "delta_amount": tgt_amt - cur_amt,
            "action": _action_from_delta(row["holdings_weight"], row["target_weight"]),
        })
    cash_amount = _round_money(total_assets) - invested_amount
    capital_plan = {
        "total_assets": _round_money(total_assets),
        "invested_weight": round(sum_target, 2),
        "invested_amount": invested_amount,
        "cash_weight": round(cash_target_w, 2),
        "cash_amount": cash_amount,
        "cash_floor": capital_in.get("cash_floor", 0),
        "allocations": sorted(allocations, key=lambda a: a["target_amount"], reverse=True),
    }

    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "advice_id": str(uuid.uuid4()),
        "user_id": user_id,
        "status": "COMPLETED",
        "source": "v3-workflow",
        "created_at": now,
        "completed_at": now,
        "elapsed_seconds": 0,
        "cio_verdict": "v3 子 Agent 流水线（Step0-7）",
        "industry_matrix": matrix_out,
        "prescription": presc_out,
        "capital_plan": capital_plan,
        "total_assets_snapshot": _round_money(total_assets),
        "data_score": matrix_in.get("data_score", 0) if isinstance(matrix_in, dict) else 0,
        "constraint_chain_valid": (
            matrix_in.get("constraint_chain_valid", True) if isinstance(matrix_in, dict) else True
        ),
        "violations": matrix_in.get("violations", []) if isinstance(matrix_in, dict) else [],
        "summary": summary,
    }
    return doc


# ── 落库 ────────────────────────────────────────────────────

async def _write_mongo(doc: Dict[str, Any]) -> str:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from app.core.database import init_database, get_mongo_db
    await init_database()
    db = get_mongo_db()
    await db["portfolio_advice"].insert_one(dict(doc))
    return doc["advice_id"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest v3 workflow output into portfolio_advice")
    parser.add_argument("--data-dir", required=True, help="workflow 产出目录")
    parser.add_argument("--user-id", required=True, help="用户 ID")
    parser.add_argument("--out-json", default=None,
                        help="给定则把文档写入该 JSON 文件（不连 MongoDB），用于验证字段契约")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"错误: data-dir 不存在: {data_dir}")
        sys.exit(1)

    doc = build_doc(data_dir, args.user_id)

    n_matrix = len([r for r in doc["industry_matrix"] if r["industry"] != CASH_INDUSTRY])
    n_buy = len([p for p in doc["prescription"] if p["action"] in ("buy", "add", "new_position")])
    n_sell = len([p for p in doc["prescription"] if p["action"] in ("sell", "reduce")])
    cp = doc["capital_plan"]
    print(f"  映射完成: {n_matrix} 行业, {len(doc['prescription'])} 条处方 "
          f"(买入 {n_buy} / 卖出 {n_sell})")
    print(f"  资金: 总资产 ¥{cp['total_assets']:,} → 投资 ¥{cp['invested_amount']:,}"
          f"({cp['invested_weight']}%) + 现金 ¥{cp['cash_amount']:,}({cp['cash_weight']}%)")

    if args.out_json:
        with open(args.out_json, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
        print(f"  ✓ 文档已写入 {args.out_json}（未连库）advice_id={doc['advice_id']}")
        return

    import asyncio
    advice_id = asyncio.run(_write_mongo(doc))
    print(f"  ✓ 已落库 portfolio_advice advice_id={advice_id} status=COMPLETED")


if __name__ == "__main__":
    main()
