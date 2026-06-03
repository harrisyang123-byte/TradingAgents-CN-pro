#!/usr/bin/env python3
"""组合顾问全链路分析 — Claude Code 编排 + 子 Agent

用法:
    python cli/claude_advisor.py --user-id 6a094caea814b57d3357fa0b

可选:
    --verbose    打印每步 Agent 输出摘要
    --skip-data  复用缓存的数据文件（debug 用）
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(name)s | %(message)s")
logger = logging.getLogger("claude-advisor")

DATA_DIR = Path("/tmp/claude_advisor")
DATA_DIR.mkdir(parents=True, exist_ok=True)


# ── LLM 工厂 ──────────────────────────────────────────────

def create_llm(_user_id: str):
    """创建 LLM 实例 — 从 .env 读取 API key，不依赖 DB 配置"""
    import os as _os
    from dotenv import load_dotenv
    from tradingagents.graph.trading_graph import create_llm_by_provider
    from tradingagents.llm_clients.provider_keys import normalize_provider_key

    # 加载 .env
    _env_path = _os.path.join(_os.path.dirname(__file__), "..", ".env")
    if _os.path.exists(_env_path):
        load_dotenv(_env_path, override=True)

    api_key = _os.getenv("DEEPSEEK_API_KEY") or ""
    provider = "deepseek"
    model = "deepseek-chat"

    if not api_key:
        api_key = _os.getenv("DASHSCOPE_API_KEY") or ""
        provider = "qwen"
        model = "qwen-turbo"

    return create_llm_by_provider(provider=provider, model=model, backend_url="",
                                   temperature=0.3, max_tokens=4000, timeout=120, api_key=api_key)


def run_agent(llm, system_prompt: str, input_data: str = "") -> str:
    """一次子 Agent 调用"""
    from langchain_core.messages import SystemMessage, HumanMessage

    messages = [SystemMessage(content=system_prompt)]
    if input_data:
        messages.append(HumanMessage(content=f"## 输入数据\n{input_data}"))

    response = llm.invoke(messages)
    return response.content if hasattr(response, "content") else str(response)


def extract_json(text: str) -> dict:
    """从 LLM 输出中提取 JSON"""
    import re
    # 优先 ```json ... ```
    m = re.search(r"```(?:json)\s*(\{[\s\S]*?\}|\[[\s\S]*?\])\s*```", text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # 裸 JSON
    m = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    return {}


# ── 数据收集 ──────────────────────────────────────────────

async def collect_all_data(user_id: str, skip_data: bool = False):
    """全量数据收集"""
    from cli.advisor.data_collector import collect_all
    if skip_data and (DATA_DIR / "portfolio.json").exists():
        logger.info("复用已有数据（--skip-data）")
        return
    await collect_all(user_id)


# ── 保存 ──────────────────────────────────────────────────

async def save_to_mongodb(
    user_id: str,
    cio_verdict: str,
    prescription: list,
    conflicts: list,
    elapsed: float,
):
    """保存最终结果到 MongoDB"""
    from app.core.database import init_database, get_mongo_db
    await init_database()
    db = get_mongo_db()
    advice_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    doc = {
        "advice_id": advice_id,
        "user_id": user_id,
        "status": "COMPLETED",
        "created_at": now,
        "completed_at": now,
        "cio_verdict": cio_verdict,
        "prescription": prescription,
        "conflicts": conflicts,
        "elapsed_seconds": round(elapsed, 2),
        "source": "claude-code-v3",
    }
    await db["portfolio_advice"].insert_one(doc)
    logger.info(f"已保存: advice_id={advice_id}, 处方 {len(prescription)} 条")
    return advice_id


# ── 主流程 ────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="组合顾问 Claued Code 版")
    parser.add_argument("--user-id", required=True, help="用户ID")
    parser.add_argument("--verbose", action="store_true", help="打印每步 Agent 输出")
    parser.add_argument("--skip-data", action="store_true", help="复用已缓存的数据")
    args = parser.parse_args()

    t0 = datetime.utcnow()

    # 1. 数据收集
    logger.info("=" * 50)
    logger.info("Phase 1: 数据收集")
    asyncio.run(collect_all_data(args.user_id, args.skip_data))

    pf = json.load(open(DATA_DIR / "portfolio.json"))
    tier1 = json.load(open(DATA_DIR / "tier1.json")) if (DATA_DIR / "tier1.json").exists() else []
    exposure = json.load(open(DATA_DIR / "exposure.json")) if (DATA_DIR / "exposure.json").exists() else {}
    market_temp = json.load(open(DATA_DIR / "market_temp.json")) if (DATA_DIR / "market_temp.json").exists() else {}

    logger.info(f"持仓: {len(pf.get('positions',[]))} 只")
    logger.info(f"Tier1: {len(tier1)} 份")
    logger.info(f"敞口穿透率: {exposure.get('penetration_ratio', 0)}%")

    # 2. 交叉验证
    logger.info("=" * 50)
    logger.info("Phase 2: 交叉验证")
    from cli.advisor.cross_validator import cross_validate_all
    conflicts = cross_validate_all(pf=pf, tier1=tier1, exposure=exposure, market_temp=market_temp)
    for c in conflicts:
        logger.info(f"  [{c['severity']}] {c['type']}: {c.get('detail','')[:100]}")

    # 3. LLM
    logger.info("=" * 50)
    logger.info("Phase 3: 子 Agent 链")
    llm = create_llm(args.user_id)

    from cli.advisor.prompts import (
        L1_STRATEGIST, L1_CONTRARIAN, L1_JUDGE,
        L2_SCOUT,
        L3_ANALYST, L3_STRATEGIST,
        L4_CIO, L4_RISK, L4_CIO_FINAL,
    )

    # 构造输入摘要
    pos_summary = json.dumps({
        "total_assets": pf.get("total_assets", 0),
        "cash_ratio": round(pf.get("available_cash", 0) / max(pf.get("total_assets", 1), 1) * 100, 1),
        "positions": [{"code": p["code"], "name": p.get("name", ""), "weight": round(p.get("weight", 0), 1),
                       "instrument_type": p.get("instrument_type", "stock"), "industry": p.get("industry", "")}
                      for p in pf.get("positions", [])],
    }, ensure_ascii=False, indent=2)

    tier1_summary = json.dumps([{
        "code": r["code"], "recommendation": r.get("recommendation", "")[:60],
        "instrument_type": r.get("instrument_type", "stock"),
    } for r in tier1[:15]], ensure_ascii=False)[:2000]

    # 3a. L1 策略师
    logger.info("L1 策略师...")
    l1_input = json.dumps({"portfolio": pos_summary, "market_temp": market_temp}, ensure_ascii=False)[:3000]
    l1_strategist = run_agent(llm, L1_STRATEGIST, l1_input)
    if args.verbose:
        print(f"\n=== L1 策略师 ===\n{l1_strategist[:1000]}\n")
    json.dump({"raw": l1_strategist}, open(DATA_DIR / "l1_strategist.json", "w"), ensure_ascii=False)

    # 3b. L1 反向者
    logger.info("L1 反向者...")
    l1_contrarian = run_agent(llm, L1_CONTRARIAN, l1_strategist[:3000])
    if args.verbose:
        print(f"\n=== L1 反向者 ===\n{l1_contrarian[:1000]}\n")
    json.dump({"raw": l1_contrarian}, open(DATA_DIR / "l1_contrarian.json", "w"), ensure_ascii=False)

    # 3c. L1 裁判
    logger.info("L1 裁判...")
    l1_judge_input = f"## 策略师\n{l1_strategist[:2000]}\n## 反向者\n{l1_contrarian[:2000]}"
    l1_judge = run_agent(llm, L1_JUDGE, l1_judge_input)
    if args.verbose:
        print(f"\n=== L1 裁判 ===\n{l1_judge[:1000]}\n")
    json.dump({"raw": l1_judge}, open(DATA_DIR / "l1_judge.json", "w"), ensure_ascii=False)

    # 3d. L2 Scout
    logger.info("L2 Scout...")
    l2_input = json.dumps({
        "l1_judge": l1_judge[:1500],
        "portfolio": pos_summary[:2000],
        "tier1": tier1_summary,
    }, ensure_ascii=False)[:3000]
    l2_scout = run_agent(llm, L2_SCOUT, l2_input)
    if args.verbose:
        print(f"\n=== L2 Scout ===\n{l2_scout[:1000]}\n")
    json.dump({"raw": l2_scout}, open(DATA_DIR / "l2_scout.json", "w"), ensure_ascii=False)

    # 3e. L3 分析师
    logger.info("L3 分析师...")
    l3_input = json.dumps({
        "l1_judge": l1_judge[:1000],
        "l2_scout": l2_scout[:1000],
        "portfolio": pos_summary[:2000],
        "tier1": tier1_summary,
    }, ensure_ascii=False)[:3000]
    l3_analyst = run_agent(llm, L3_ANALYST, l3_input)
    if args.verbose:
        print(f"\n=== L3 分析师 ===\n{l3_analyst[:800]}\n")
    json.dump({"raw": l3_analyst}, open(DATA_DIR / "l3_analyst.json", "w"), ensure_ascii=False)

    # 3f. L3 策略师
    logger.info("L3 策略师...")
    l3_strategist_input = json.dumps({
        "analyst": l3_analyst[:2000],
        "exposure": {k: v for k, v in exposure.items() if k in ("hhi", "penetration_ratio", "overlaps")},
        "positions": [{"code": p["code"], "weight": round(p.get("weight", 0), 1)} for p in pf.get("positions", [])[:20]],
    }, ensure_ascii=False)[:3000]
    l3_strategist = run_agent(llm, L3_STRATEGIST, l3_strategist_input)
    if args.verbose:
        print(f"\n=== L3 策略师 ===\n{l3_strategist[:800]}\n")
    json.dump({"raw": l3_strategist}, open(DATA_DIR / "l3_strategist.json", "w"), ensure_ascii=False)

    # 3g. L4 CIO 初稿
    logger.info("L4 CIO...")
    l4_input = json.dumps({
        "l1_judge": l1_judge[:1500],
        "l2_scout": l2_scout[:1500],
        "l3_analyst": l3_analyst[:1500],
        "l3_strategist": l3_strategist[:1500],
        "conflicts": conflicts[:5],
        "exposure": {k: v for k, v in exposure.items() if k in ("hhi", "penetration_ratio", "exposures")},
        "market_temp": market_temp,
    }, ensure_ascii=False)[:4000]
    l4_cio = run_agent(llm, L4_CIO, l4_input)
    if args.verbose:
        print(f"\n=== L4 CIO ===\n{l4_cio[:1000]}\n")
    json.dump({"raw": l4_cio}, open(DATA_DIR / "l4_cio.json", "w"), ensure_ascii=False)

    # 3h. L4 风险总监
    logger.info("L4 风险总监...")
    l4_risk = run_agent(llm, L4_RISK, l4_cio[:3000])
    if args.verbose:
        print(f"\n=== L4 风险总监 ===\n{l4_risk[:800]}\n")
    json.dump({"raw": l4_risk}, open(DATA_DIR / "l4_risk.json", "w"), ensure_ascii=False)

    # 3i. L4 CIO 终裁
    logger.info("L4 CIO 终裁...")
    l4_final_input = f"## CIO初稿\n{l4_cio[:3000]}\n## 风险总监\n{l4_risk[:2000]}"
    l4_final = run_agent(llm, L4_CIO_FINAL, l4_final_input)
    if args.verbose:
        print(f"\n=== L4 CIO终裁 ===\n{l4_final[:1000]}\n")
    json.dump({"raw": l4_final}, open(DATA_DIR / "l4_final.json", "w"), ensure_ascii=False)

    # 4. 提取处方 + 全覆盖后备
    logger.info("=" * 50)
    logger.info("Phase 4: 提取+保存")
    ciop = extract_json(l4_final)
    if isinstance(ciop, dict):
        for val in ciop.values():
            if isinstance(val, list) and len(val) > 0:
                ciop = val
                break
    if not isinstance(ciop, list):
        ciop = []

    # 全覆盖后备：CIO输出不足36条时，补全剩余为 hold
    all_positions = pf.get("positions", [])
    all_codes = {p["code"] for p in all_positions}
    covered_codes = set()
    for r in ciop:
        if r.get("code") in all_codes:
            covered_codes.add(r["code"])

    for p in all_positions:
        code = p["code"]
        if code not in covered_codes:
            ciop.append({
                "code": code,
                "name": p.get("name", "")[:20],
                "action": "hold",
                "current_weight": round(p.get("weight", 0), 1),
                "target_weight": round(p.get("weight", 0), 1),
                "reasoning": "CIO未指定，维持当前仓位",
                "priority": "optional",
            })
            covered_codes.add(code)

    prescription = ciop

    elapsed = (datetime.utcnow() - t0).total_seconds()

    # 5. 保存完整 CIO 裁决
    # 市场温度可用性标注
    temp_note = ""
    if market_temp.get("breadth_signal") in ("中性", None, "") or str(market_temp.get("north_net")) == "nan":
        temp_note = "\n\n⚠️ 市场温度数据不可用（AKShare连接超时），情绪修正已跳过，处方基于纯基本面判断。"

    cio_verdict = (
        f"# 组合顾问分析报告\n\n"
        f"## L1 行业方向\n{l1_judge[:2000]}\n\n"
        f"## L2 标的筛选\n{l2_scout[:1500]}\n\n"
        f"## L3 组合诊断\n{l3_strategist[:1000]}\n\n"
        f"## L4 处方正文\n{l4_final[:4000]}"
        f"{temp_note}"
    )

    aid = asyncio.run(save_to_mongodb(
        args.user_id, cio_verdict, prescription, conflicts, elapsed))

    # 6. 完成
    logger.info("=" * 50)
    logger.info(f"完成: {elapsed:.0f}s, advice_id={aid}")
    logger.info(f"处方: {len(prescription)} 条, 冲突: {len(conflicts)} 条")

    # 汇总
    actions = {}
    for r in prescription:
        a = r.get("action", "?")
        actions[a] = actions.get(a, 0) + 1
    for a, n in sorted(actions.items()):
        logger.info(f"  {a}: {n}")


if __name__ == "__main__":
    main()
