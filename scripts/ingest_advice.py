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


# 入池来源白名单：前端按此渲染来源小标签（holding/watchlist/vitality）。
# LLM 有时会把「分析链路描述」（如 "L1研究员+跨行业裁判+风险总监"）写进 source，
# 直接透传会让前端把整串文字当标签渲染。非白名单值一律归一为 holding。
_VALID_SOURCES = {"holding", "watchlist", "vitality"}


def _sanitize_source(v: Any) -> str:
    s = str(v or "").strip().lower()
    return s if s in _VALID_SOURCES else "holding"


def _vitality_from_score(score: Any) -> str:
    """景气总分(0-100) → 定性等级（与前端 CSS 类 v-* 一致）。"""
    try:
        s = float(score)
    except (TypeError, ValueError):
        return ""
    if s >= 70:
        return "强烈看好"
    if s >= 55:
        return "看好"
    if s >= 40:
        return "中性"
    return "看空"


def _build_alloc_lookup(data_dir: Path) -> Dict[str, Dict[str, Any]]:
    """从 industry_allocations.json（跨行业裁判输出）建行业名→字段 的查找表。

    跨行业裁判被强制对每个行业输出 vitality_level/stance/market/go_nogo，
    而 Synthesizer 产 industry_matrix.json 时 LLM 常丢这些字段。用此表回填。
    """
    alloc = _load(data_dir / "industry_allocations.json", []) or []
    rows = alloc if isinstance(alloc, list) else alloc.get("allocations", [])
    lookup: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        if isinstance(r, dict) and r.get("industry"):
            lookup[str(r["industry"]).strip()] = r
    return lookup


def _build_vitality_lookup(data_dir: Path) -> Dict[str, str]:
    """从 data_vitality.json（景气打分引擎产出，可选）建行业→等级 查找表。"""
    vit = _load(data_dir / "data_vitality.json", []) or []
    rows = vit if isinstance(vit, list) else vit.get("scores", vit.get("industries", []))
    lookup: Dict[str, str] = {}
    for r in rows:
        if not isinstance(r, dict):
            continue
        name = str(r.get("industry", "")).strip()
        if not name:
            continue
        level = r.get("vitality_level") or _vitality_from_score(r.get("total_score"))
        if level:
            lookup[name] = level
    return lookup


def _text(v: Any) -> str:
    """把 agent JSON 片段渲染成可读文本（dict/list → 缩进 JSON，标量 → str）。"""
    if v is None or v == "" or v == [] or v == {}:
        return ""
    if isinstance(v, str):
        return v.strip()
    try:
        return json.dumps(v, ensure_ascii=False, indent=2)
    except Exception:
        return str(v)


def _assemble_debates(data_dir: Path) -> Dict[str, str]:
    """从 workflow 各阶段产物组装三段辩论历程文本，供前端「分析师辩论历程」三个 tab。

    market（L1 市场研判）: 宏观裁判 + 各行业研究员/反向者 + 跨行业裁判
    stock （L3 个股辩论）: Scout 候选 + 组合诊断/反向者 + 各行业 PM 激进/保守/裁判
    final （综合裁决）   : 风控悲观/乐观/裁判 + Synthesizer summary
    """
    macro = _load(data_dir / "macro_verdict.json", {}) or {}
    researchers = _load(data_dir / "all_researchers.json", []) or []
    allocations = _load(data_dir / "industry_allocations.json", []) or []
    scout = _load(data_dir / "step4_scout.json", {}) or {}
    diag = _load(data_dir / "portfolio_diagnosis.json", {}) or {}
    diag_contra = _load(data_dir / "portfolio_contrarian.json", {}) or {}
    pm_results = _load(data_dir / "pm_results.json", []) or []
    pessimist = _load(data_dir / "pessimist_risk.json", {}) or {}
    optimist = _load(data_dir / "optimist_risk.json", {}) or {}
    risk_verdict = _load(data_dir / "risk_assessment.json", {}) or {}

    # ── 市场研判 L1 ──
    market_parts: List[str] = []
    if macro:
        market_parts.append("【宏观裁判】\n" + _text(macro))
    for item in researchers:
        if not isinstance(item, dict):
            continue
        ind = item.get("industry", "")
        r = _text(item.get("researcher"))
        c = _text(item.get("contrarian"))
        seg = [f"——— {ind} ———"]
        if r:
            seg.append("【研究员】\n" + r)
        if c:
            seg.append("【反向者】\n" + c)
        if len(seg) > 1:
            market_parts.append("\n".join(seg))
    alloc_rows = allocations if isinstance(allocations, list) else allocations.get("allocations", [])
    if alloc_rows:
        market_parts.append("【跨行业配置裁判】\n" + _text(alloc_rows))

    # ── 个股辩论 L3 ──
    stock_parts: List[str] = []
    cands = scout.get("candidates", scout) if isinstance(scout, dict) else scout
    if cands:
        stock_parts.append("【Scout 候选标的】\n" + _text(cands))
    if diag:
        stock_parts.append("【组合层持仓诊断】\n" + _text(diag))
    if diag_contra:
        stock_parts.append("【组合反向者】\n" + _text(diag_contra))
    for pr in pm_results:
        if not isinstance(pr, dict):
            continue
        ind = pr.get("industry", "")
        body = _text(pr.get("result", pr))
        if body:
            stock_parts.append(f"——— {ind} PM 裁判 ———\n" + body)

    # ── 综合裁决 ──
    final_parts: List[str] = []
    if pessimist:
        final_parts.append("【悲观风险总监】\n" + _text(pessimist))
    if optimist:
        final_parts.append("【乐观风险分析师】\n" + _text(optimist))
    if risk_verdict:
        final_parts.append("【风控裁判 RiskAssessment】\n" + _text(risk_verdict))

    return {
        "market_debate_history": "\n\n".join(p for p in market_parts if p).strip(),
        "stock_debate_history": "\n\n".join(p for p in stock_parts if p).strip(),
        "debate_history": "\n\n".join(p for p in final_parts if p).strip(),
    }


# ── 核心映射 ─────────────────────────────────────────────────

def build_doc(data_dir: Path, user_id: str) -> Dict[str, Any]:
    matrix_in = _load(data_dir / "industry_matrix.json", {}) or {}
    presc_in = _load(data_dir / "final_prescription.json", {}) or {}
    capital_in = _load(data_dir / "capital_plan.json", {}) or {}
    portfolio = _load(data_dir / "data_portfolio.json", {}) or {}

    # 回填源：跨行业裁判分配表（vitality/stance/market/go_nogo 的权威来源）
    # + 景气打分引擎产出（可选）。Synthesizer 的 matrix 行常丢这些字段，用它们补。
    alloc_lookup = _build_alloc_lookup(data_dir)
    vitality_lookup = _build_vitality_lookup(data_dir)

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
        industry = row.get("industry", "未分类")
        alloc = alloc_lookup.get(str(industry).strip(), {})
        holdings_w = float(row.get("actual_weight", row.get("holdings_weight", 0)) or 0)
        target_w = float(row.get("final_weight", row.get("target_weight", 0)) or 0)
        # go_nogo：matrix 缺失时回退到分配表
        go = _map_go_nogo(row.get("go_nogo") if row.get("go_nogo") not in (None, "") else alloc.get("go_nogo"))
        # vitality_level：matrix → 分配表 → 景气引擎，三级回退
        vitality = (
            row.get("vitality_level")
            or alloc.get("vitality_level")
            or vitality_lookup.get(str(industry).strip(), "")
        )
        # stance / market 同理回退
        stance = row.get("stance") or alloc.get("stance", "")
        market = row.get("market") or alloc.get("market") or "cn"
        sum_target += target_w
        matrix_out.append({
            "industry": industry,
            "source": _sanitize_source(row.get("source")),
            "market": market,
            "go_nogo": go,
            "stance": stance,
            # NOGO 行业是被深度研究后判定「不配置」，属于"已覆盖"；
            # 只有未被分析的行业（go 为空）才是 "never"。
            "coverage_status": "covered" if go in ("GO", "NOGO") else "never",
            "vitality_level": vitality,
            "lifecycle": row.get("lifecycle", ""),
            "holdings_weight": round(holdings_w, 2),
            "target_weight": round(target_w, 2),
            "delta": round(target_w - holdings_w, 2),
            "gap": round(float(row.get("gap", 0) or 0), 2),
            "scout_triggered": bool(row.get("scout_triggered", False)),
            "codes": row.get("positions", row.get("codes", [])) or [],
            "reasoning": row.get("reasoning", "") or alloc.get("reasoning", ""),
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

    # —— 5. 辩论历程（从各阶段产物组装三段文本，供前端三个 tab）——
    debates = _assemble_debates(data_dir)

    # —— 6. selected_industries（前端历史卡显示「N 个行业」，非现金行业名）——
    selected_industries = [r["industry"] for r in matrix_out if r["industry"] != CASH_INDUSTRY]

    # —— 7. data_score（数据质量）：优先 matrix 自带，否则按覆盖率估算 ——
    data_score = matrix_in.get("data_score", 0) if isinstance(matrix_in, dict) else 0
    if not data_score and selected_industries:
        covered = sum(1 for r in matrix_out
                      if r["industry"] != CASH_INDUSTRY and r["go_nogo"] in ("GO", "NOGO"))
        data_score = round(covered / len(selected_industries), 2)

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
        "selected_industries": selected_industries,
        "total_assets_snapshot": _round_money(total_assets),
        "data_score": data_score,
        # 三段辩论历程（前端「分析师辩论历程」market/stock/final tab）
        "market_debate_history": debates["market_debate_history"],
        "stock_debate_history": debates["stock_debate_history"],
        "debate_history": debates["debate_history"],
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
