"""Tier 2 组合顾问引擎 E2E 测试

测试完整流程: 持仓数据 → 三角色分析 → 辩论 → CIO 裁决 → 结构化处方

用法:
    cd domains/tradingagents-cn
    .venv/bin/python3 tests/test_advisor_e2e.py
"""

from dotenv import load_dotenv; load_dotenv()
import json, os, sys, time
from datetime import datetime

# ── Test Data ──────────────────────────────────────────────

def build_test_portfolio():
    """构造一个真实的 A 股模拟持仓: 4 只股票，总资产 ~25 万"""
    return {
        "total_invested": 240_000.00,
        "available_cash": 35_000.00,
        "total_assets": 255_000.00,
        "total_market_value_cny": 220_000.00,
        "total_pnl": 15_000.00,
        "total_pnl_pct": 6.25,
        "positions": [
            {
                "code": "600519", "market": "CN", "currency": "CNY",
                "quantity": 100, "avg_cost": 1680.00, "last_price": 1725.00,
                "exchange_rate": 1.0, "market_value_cny": 172_500.00,
                "pnl_cny": 4_500.00, "pnl_pct": 2.68,
                "weight": 67.65, "buy_date": "2026-03-15",
                "notes": "白酒龙头，长期持有",
            },
            {
                "code": "000858", "market": "CN", "currency": "CNY",
                "quantity": 200, "avg_cost": 155.00, "last_price": 138.00,
                "exchange_rate": 1.0, "market_value_cny": 27_600.00,
                "pnl_cny": -3_400.00, "pnl_pct": -10.97,
                "weight": 10.82, "buy_date": "2026-04-20",
                "notes": "白酒二号，近期回调明显",
            },
            {
                "code": "300750", "market": "CN", "currency": "CNY",
                "quantity": 50, "avg_cost": 210.00, "last_price": 245.00,
                "exchange_rate": 1.0, "market_value_cny": 12_250.00,
                "pnl_cny": 1_750.00, "pnl_pct": 16.67,
                "weight": 4.80, "buy_date": "2026-02-10",
                "notes": "新能源电池龙头",
            },
            {
                "code": "601318", "market": "CN", "currency": "CNY",
                "quantity": 150, "avg_cost": 48.00, "last_price": 50.50,
                "exchange_rate": 1.0, "market_value_cny": 7_575.00,
                "pnl_cny": 375.00, "pnl_pct": 5.21,
                "weight": 2.97, "buy_date": "2026-05-01",
                "notes": "保险龙头，刚建仓",
            },
        ],
    }


def build_tier1_reports():
    """Tier 1 分析报告: 针对 3 只持仓股票的深度分析结果"""
    return [
        {
            "stock_code": "600519", "stock_symbol": "600519",
            "rating": "Buy",
            "summary": (
                "贵州茅台2026Q1营收同比增长12%，净利润增长15%，毛利率维持在92%以上。"
                "批价稳定在2700-2800元区间，渠道库存健康。直销占比提升至48%，"
                "i茅台平台贡献增量。估值方面，当前PE 28x处于近5年中位数下方。"
                "建议维持仓位，目标价2000元。"
            ),
            "created_at": "2026-05-12T10:00:00Z",
        },
        {
            "stock_code": "000858", "stock_symbol": "000858",
            "rating": "Hold",
            "summary": (
                "五粮液2026Q1营收增速放缓至5%，净利润增长3%，低于市场预期。"
                "普五批价回落至950元附近，渠道库存偏高，经销商打款意愿下降。"
                "公司推进渠道改革，但短期效果有限。当前PE 18x，估值合理但缺乏催化剂。"
                "建议观望，等待批价企稳信号。"
            ),
            "created_at": "2026-05-10T10:00:00Z",
        },
        {
            "stock_code": "300750", "stock_symbol": "300750",
            "rating": "Buy",
            "summary": (
                "宁德时代2026Q1出货量同比增长25%，全球市占率维持37%。"
                "神行电池二代量产，能量密度突破200Wh/kg，成本下降15%。"
                "储能业务收入增长40%，成为第二增长曲线。当前PE 22x，"
                "对应PEG < 0.8，建议增持，目标价300元。"
            ),
            "created_at": "2026-05-15T10:00:00Z",
        },
        {
            "stock_code": "601318", "stock_symbol": "601318",
            "rating": "Hold",
            "summary": (
                "中国平安2026Q1 NBV同比增长8%，代理人规模企稳回升。"
                "财险综合成本率97.2%，优于同业。但利率下行环境下，"
                "利差损压力犹存。当前PEV 0.7x处于历史低位，"
                "分红率5.5%有吸引力。建议持有，关注利率走势。"
            ),
            "created_at": "2026-05-08T10:00:00Z",
        },
    ]


def build_non_held_reports():
    """非持仓标的的 Tier 1 报告（侦察兵用来发现新机会）"""
    return [
        {
            "stock_code": "002415", "stock_symbol": "002415",
            "rating": "Buy",
            "summary": (
                "海康威视AI转型加速，观澜大模型落地多个行业场景。"
                "海外收入占比提升至38%，EBG业务增长30%。"
                "当前PE 25x，低于AI安防同业，建议买入。"
            ),
            "created_at": "2026-05-14T10:00:00Z",
        },
        {
            "stock_code": "688981", "stock_symbol": "688981",
            "rating": "Buy",
            "summary": (
                "中芯国际14nm良率提升至95%，N+2工艺试产成功。"
                "国产替代加速，28nm以上成熟制程产能利用率100%。"
                "当前PB 2.1x，低于全球晶圆代工平均PB 3.5x。"
            ),
            "created_at": "2026-05-13T10:00:00Z",
        },
        {
            "stock_code": "600036", "stock_symbol": "600036",
            "rating": "Hold",
            "summary": (
                "招商银行零售AUM突破14万亿，私行客户增长12%。"
                "但NIM收窄至2.05%，不良率微升至1.02%。"
                "建议等待NIM企稳后再考虑配置。"
            ),
            "created_at": "2026-05-11T10:00:00Z",
        },
    ]


# ── Main Test ──────────────────────────────────────────────

def test_advisor_engine():
    """运行 Tier 2 引擎完整流程"""

    print("=" * 60)
    print("Tier 2 组合顾问引擎 E2E 测试")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. 创建 LLM
    print("\n[1/5] 创建 LLM 实例...")
    from tradingagents.llm_clients.provider_keys import normalize_provider_key
    from tradingagents.graph.trading_graph import create_llm_by_provider

    provider = normalize_provider_key("deepseek")
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    print(f"  provider={provider}, model={model}")

    llm = create_llm_by_provider(
        provider=provider,
        model=model,
        backend_url=os.getenv("DEEPSEEK_BASE_URL", ""),
        temperature=0.7,
        max_tokens=4000,
        timeout=180,
    )
    print("  ✓ LLM 创建成功")

    # 2. 准备测试数据
    print("\n[2/5] 准备测试数据...")
    portfolio = build_test_portfolio()
    tier1_reports = build_tier1_reports()
    non_held_reports = build_non_held_reports()

    print(f"  持仓: {len(portfolio['positions'])} 只")
    for p in portfolio["positions"]:
        print(f"    {p['code']}  weight={p['weight']:.1f}%  pnl={p['pnl_pct']:+.2f}%")
    print(f"  Tier1 报告: {len(tier1_reports)} 份")
    print(f"  非持仓报告: {len(non_held_reports)} 份")

    # 3. 创建 AdvisorGraph
    print("\n[3/5] 创建 AdvisorGraph...")
    from tradingagents.graph.advisor_graph import AdvisorGraph

    config = {
        "max_single_weight": 30.0,
        "max_industry_weight": 50.0,
        "advisor_debate_rounds": 2,
        "report_staleness_days": 7,
    }
    advisor = AdvisorGraph(llm, config=config)
    print("  ✓ AdvisorGraph 创建成功（LangGraph 编译完成）")

    # 4. 运行分析
    print("\n[4/5] 运行 Tier 2 引擎（预计 2-5 分钟）...")
    print("  流程: Analyst → Strategist → Scout → 辩论x2 → CIO")

    progress_steps = []

    def on_progress(label: str):
        progress_steps.append(label)
        elapsed = time.time() - start_time
        print(f"  [{elapsed:5.0f}s] {label}")

    start_time = time.time()
    try:
        result = advisor.propagate_advice(
            portfolio_summary=portfolio,
            tier1_reports=tier1_reports,
            non_held_reports=non_held_reports,
            progress_callback=on_progress,
        )
        total_elapsed = time.time() - start_time
    except Exception as e:
        print(f"\n  ✗ 引擎执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 5. 验证输出
    print(f"\n[5/5] 验证输出 (总耗时 {total_elapsed:.0f}s)...")

    all_pass = True

    # 5a. 处方结构
    prescription = result.get("prescription", [])
    print(f"\n  ── 处方 ({len(prescription)} 条) ──")
    if len(prescription) > 0:
        for item in prescription:
            print(f"    [{item.get('action', '?')}] {item.get('code', '?')} "
                  f"weight {item.get('current_weight', 0):.1f}% → {item.get('target_weight', 0):.1f}%")
            print(f"       理由: {item.get('reasoning', 'N/A')[:120]}")
            if item.get("risk_note"):
                print(f"       风险: {item.get('risk_note', '')[:120]}")
    else:
        print("    ⚠ 处方为空！")
        all_pass = False

    # 5b. CIO 裁决
    cio = result.get("cio_verdict", "")
    print(f"\n  ── CIO 裁决 ({len(cio)} 字符) ──")
    print(f"    {cio[:500]}")
    if len(cio) < 100:
        print("    ⚠ CIO 裁决过短！")
        all_pass = False

    # 5c. 三角色评估
    analyst = result.get("analyst_assessment", "")
    strategist = result.get("strategist_assessment", "")
    scout = result.get("scout_assessment", "")

    for role, content in [("分析师", analyst), ("策略师", strategist), ("侦察兵", scout)]:
        status = "✓" if len(content) > 50 else "⚠"
        print(f"\n  ── {role}评估 {status} ({len(content)} 字符) ──")
        print(f"    {content[:300]}")

    # 5d. 辩论历史
    debate = result.get("debate_history", "")
    print(f"\n  ── 辩论记录 ({len(debate)} 字符) ──")
    if len(debate) > 100:
        print(f"    {debate[:400]}...")
    else:
        print(f"    ⚠ 辩论记录过短！")
        all_pass = False

    # 5e. 结构检查
    print(f"\n  ── 结构检查 ──")
    checks = [
        ("prescription 为 list", isinstance(prescription, list) and len(prescription) > 0),
        ("cio_verdict 非空", len(cio) > 100),
        ("analyst_assessment 非空", len(analyst) > 50),
        ("strategist_assessment 非空", len(strategist) > 50),
        ("scout_assessment 非空", len(scout) > 50),
        ("debate_history 非空", len(debate) > 100),
        ("elapsed_seconds > 0", result.get("elapsed_seconds", 0) > 0),
        ("处方 action 合法", all(
            item.get("action") in ["buy", "sell", "hold", "reduce", "add", "new_position"]
            for item in prescription
        )),
    ]
    for label, ok in checks:
        mark = "✓" if ok else "✗ FAIL"
        if not ok:
            all_pass = False
        print(f"    {mark}  {label}")

    # Summary
    print(f"\n{'=' * 60}")
    if all_pass:
        print("✓ 所有检查通过")
    else:
        print("✗ 存在失败项，请检查上方输出")
    print(f"总耗时: {total_elapsed:.0f}s | 步骤数: {len(progress_steps)}")
    print(f"Token 消耗: 请查看 MongoDB token_usage 表")
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    return all_pass


if __name__ == "__main__":
    success = test_advisor_engine()
    sys.exit(0 if success else 1)
