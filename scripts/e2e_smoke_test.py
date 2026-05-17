#!/usr/bin/env python3
"""E2E smoke test: run a full analysis on 贵州茅台 (600519.SH).

Auto-selects provider: DeepSeek > Qwen (whichever key is valid).
Override with SMOKE_TEST_PROVIDER=deepseek|qwen.

Usage:
  .venv/bin/python3 scripts/e2e_smoke_test.py
"""

import os
import sys
import time

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph


def main():
    provider = os.environ.get("SMOKE_TEST_PROVIDER", "auto")
    if provider == "auto":
        if os.environ.get("DEEPSEEK_API_KEY"):
            provider = "deepseek"
        elif os.environ.get("DASHSCOPE_API_KEY") and os.environ.get("DASHSCOPE_API_KEY") != "your_dashscope_api_key_here":
            provider = "qwen"
        else:
            print("ERROR: No valid API key found. Set DEEPSEEK_API_KEY or DASHSCOPE_API_KEY.")
            sys.exit(1)

    config = DEFAULT_CONFIG.copy()
    if provider == "deepseek":
        config["llm_provider"] = "deepseek"
        config["deep_think_llm"] = "deepseek-chat"
        config["quick_think_llm"] = "deepseek-chat"
        config["backend_url"] = "https://api.deepseek.com"
    else:
        config["llm_provider"] = "qwen"
        config["deep_think_llm"] = "qwen-plus"
        config["quick_think_llm"] = "qwen-plus"
        config["backend_url"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    config["max_debate_rounds"] = 1
    config["max_risk_discuss_rounds"] = 1
    config["sentiment_sources"] = ["eastmoney", "eastmoney_comment", "xueqiu", "tonghuashun"]

    ticker = "600519.SH"
    trade_date = "2025-05-15"

    print(f"=== E2E Smoke Test ===")
    print(f"Ticker: {ticker}")
    print(f"Date: {trade_date}")
    print(f"Provider: {provider} / {config['deep_think_llm']}")
    print(f"Sentiment sources: {config['sentiment_sources']}")
    print()

    ta = TradingAgentsGraph(
        selected_analysts=["market", "social", "news", "fundamentals"],
        config=config,
        debug=True,
    )

    start_time = time.time()
    try:
        state, decision = ta.propagate(ticker, trade_date)
    except Exception as e:
        print(f"FAIL: propagate() raised {type(e).__name__}: {e}")
        sys.exit(1)

    elapsed = time.time() - start_time
    print(f"\n=== Results (elapsed: {elapsed:.1f}s) ===\n")

    checks = []

    for report_name in ["market_report", "sentiment_report", "news_report", "fundamentals_report"]:
        content = state.get(report_name, "")
        ok = bool(content and len(content) > 10)
        checks.append((report_name, ok, f"{len(content)} chars" if content else "EMPTY"))

    final = state.get("final_trade_decision", "")
    checks.append(("final_trade_decision", bool(final), f"{len(final)} chars" if final else "EMPTY"))

    action = decision.get("action", "N/A")
    checks.append(("decision.action", action != "N/A", action))

    for name, ok, detail in checks:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}: {detail}")

    all_passed = all(ok for _, ok, _ in checks)
    print(f"\n{'ALL CHECKS PASSED' if all_passed else 'SOME CHECKS FAILED'}")

    if decision:
        print(f"\n=== Decision ===")
        for k, v in decision.items():
            if isinstance(v, str) and len(v) > 200:
                v = v[:200] + "..."
            print(f"  {k}: {v}")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
