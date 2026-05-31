#!/usr/bin/env python3
"""组合顾问 CLI — 对话调用入口

用法:
    python cli/run_advisor.py run --user-id <id>              # 完整 L1→L4 执行
    python cli/run_advisor.py run --user-id <id> --lite        # L3+L4 仅跑（复用缓存 L1/L2）
    python cli/run_advisor.py show --user-id <id>              # 显示最新处方
"""
import sys
import os
import asyncio
import argparse
import uuid
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── 公共依赖 ─────────────────────────────────────────────

async def _create_llm(user_id: str):
    """根据用户配置创建 LLM 实例"""
    from app.services.config_service import ConfigService
    from tradingagents.graph.trading_graph import create_llm_by_provider
    from tradingagents.llm_clients.provider_keys import normalize_provider_key

    config_service = ConfigService()
    llm_config = await config_service.get_analysis_config(user_id)
    provider = normalize_provider_key(
        llm_config.get("llm_provider", "qwen"))
    llm = create_llm_by_provider(
        provider=provider,
        model=llm_config.get(
            "deep_think_llm",
            llm_config.get("quick_think_llm", "qwen-plus")),
        backend_url=llm_config.get("backend_url", ""),
        temperature=0.7,
        max_tokens=4000,
        timeout=180,
        api_key=llm_config.get("deep_api_key")
        or llm_config.get("quick_api_key"),
    )
    return llm


# ── run 子命令 ──────────────────────────────────────────

async def cmd_run(user_id: str, lite: bool = False):
    """执行组合顾问分析"""
    from app.core.database import init_database, get_mongo_db
    from app.services.portfolio_service import PortfolioService
    from app.services.portfolio_advisor_service import (
        PortfolioAdvisorService)
    from tradingagents.graph.advisor_graph import AdvisorGraph

    t0 = time.time()
    mode = "lite" if lite else "full"
    print(f"组合顾问启动 | user={user_id} | mode={mode}")

    # 1. DB
    await init_database()
    db = get_mongo_db()

    # 2. 持仓数据
    portfolio_svc = PortfolioService()
    summary = await portfolio_svc.get_portfolio_summary(user_id)
    position_codes = [p["code"]
                      for p in summary.get("positions", [])]
    print(f"持仓: {len(position_codes)} 只")

    # 3. Tier1 报告
    advisor_svc = PortfolioAdvisorService()
    tier1_reports = await advisor_svc._prepare_tier1_reports(
        position_codes)
    print(f"Tier1 报告: {len(tier1_reports)} 份")

    # 4. LLM
    llm = await _create_llm(user_id)

    # 5. 构建图 & 执行
    graph_config = {}
    if lite:
        graph_config["market_debate_rounds"] = 1
        graph_config["stock_debate_rounds"] = 1
        graph_config["advisor_debate_rounds"] = 1

    advisor = AdvisorGraph(llm, config=graph_config)

    def progress(label):
        elapsed = time.time() - t0
        print(f"  [{elapsed:.0f}s] {label}", flush=True)

    result = advisor.propagate_advice(
        portfolio_summary=summary,
        tier1_reports=tier1_reports,
        exposure_context="",
        exposure_matrix=None,
        feedback_context="",
        progress_callback=progress,
    )

    # 6. 输出
    elapsed = time.time() - t0
    presc = result.get("prescription", [])
    print(f"\n{'=' * 60}")
    print(f"完成 | 耗时 {elapsed:.0f}s | 处方 {len(presc)} 条")
    print(f"{'=' * 60}")

    # 行业配置（从 CIO verdict 中提取表格部分）
    verdict = result.get("cio_verdict", "")
    table_start = verdict.find("## 行业配置方案")
    if table_start >= 0:
        table_end = verdict.find("```json", table_start)
        if table_end < 0:
            table_end = len(verdict)
        print("\n" + verdict[table_start:table_end])

    # 处方汇总
    print(f"\n--- 操作处方 ({len(presc)} 条) ---")
    for i, p in enumerate(presc):
        code = p.get("code", "?")
        name = p.get("name", "")
        action = p.get("action", "?")
        tw = p.get("target_weight", 0)
        itype = p.get("instrument_type", "stock")
        ib = p.get("industry_bucket", "")
        fr = p.get("fund_role", "")
        extras = []
        if ib:
            extras.append(f"bucket={ib}")
        if fr:
            extras.append(f"role={fr}")
        extra_str = f" | {', '.join(extras)}" if extras else ""
        print(
            f"  {i+1}. [{itype}] {code} {name} | "
            f"{action} | target={tw}%{extra_str}")

    # 7. 保存到 MongoDB
    advice_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    await db["portfolio_advice"].insert_one({
        "advice_id": advice_id,
        "user_id": user_id,
        "status": "COMPLETED",
        "created_at": now,
        "completed_at": now,
        "prescription": presc,
        "cio_verdict": result.get("cio_verdict", ""),
        "analyst_assessment": result.get("analyst_assessment", ""),
        "strategist_assessment": result.get("strategist_assessment", ""),
        "scout_assessment": result.get("scout_assessment", ""),
        "contrarian_assessment": result.get("contrarian_assessment", ""),
        "macro_judge_verdict": result.get("macro_judge_verdict", ""),
        "market_intel": result.get("market_intel", {}),
        "stock_candidates": result.get("stock_candidates", []),
        "stock_judge_verdict": result.get("stock_judge_verdict", ""),
        "risk_director_review": result.get("risk_director_review", ""),
        "elapsed_seconds": round(elapsed, 2),
        "market_debate_history": result.get("market_debate_history", ""),
        "stock_debate_history": result.get("stock_debate_history", ""),
        "debate_history": result.get("debate_history", ""),
        "price_context": result.get("price_context", {}),
        "risk_debate_final": result.get("risk_debate_final", {}),
        "audit_results": result.get("audit_results", []),
        "buy_signals": result.get("buy_signals", {}),
        "market_signals": result.get("market_signals", {}),
    })
    print(f"\n已保存 MongoDB: advice_id={advice_id}")


# ── show 子命令 ──────────────────────────────────────────

async def cmd_show(user_id: str):
    """查看最新处方"""
    from app.core.database import init_database, get_mongo_db

    await init_database()
    db = get_mongo_db()
    advice = await db["portfolio_advice"].find_one(
        {"user_id": user_id, "status": "COMPLETED"},
        sort=[("created_at", -1)],
    )
    if not advice:
        print("无已完成处方")
        return

    presc = advice.get("prescription", [])
    print(f"最新处方 | {advice.get('created_at', '')[:19]} | "
          f"{len(presc)} 条")
    for i, p in enumerate(presc):
        print(
            f"  {i+1}. [{p.get('instrument_type', '')}] "
            f"{p.get('code')} {p.get('name', '')} | "
            f"{p.get('action')} | {p.get('target_weight', 0)}%")
        ib = p.get("industry_bucket", "")
        fr = p.get("fund_role", "")
        if ib or fr:
            print(f"      bucket={ib} role={fr}")


# ── 入口 ────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="组合顾问 CLI")
    sub = parser.add_subparsers(dest="cmd")

    run_p = sub.add_parser("run")
    run_p.add_argument("--user-id", required=True)
    run_p.add_argument("--lite", action="store_true")

    show_p = sub.add_parser("show")
    show_p.add_argument("--user-id", required=True)

    args = parser.parse_args()

    if args.cmd == "run":
        asyncio.run(cmd_run(args.user_id, args.lite))
    elif args.cmd == "show":
        asyncio.run(cmd_show(args.user_id))
    else:
        parser.print_help()
