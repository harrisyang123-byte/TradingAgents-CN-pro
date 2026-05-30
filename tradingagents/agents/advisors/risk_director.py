"""风险总监 (L4 辩手)：审查 CIO 处方初稿，站在极端风险角度提出挑战"""

from langchain_core.messages import HumanMessage


def create_risk_director(llm):
    def risk_director_node(state: dict) -> dict:
        cio_draft = state.get("cio_verdict", "")
        prescription = state.get("prescription", [])
        portfolio = state.get("portfolio_summary", {})
        stock_candidates = state.get("stock_candidates", [])
        market_intel = state.get("market_intel", {})
        exposure_context = state.get("exposure_context", "")
        audit_results = state.get("audit_results", [])

        presc_lines = []
        for i, p in enumerate(prescription):
            presc_lines.append(
                f"{i + 1}. {p.get('code', '?')} — {p.get('action', '?')}: "
                f"当前{p.get('current_weight', 0):.1f}% → 目标{p.get('target_weight', 0):.1f}%"
            )

        # 从 audit_results 计算集中度摘要
        if isinstance(audit_results, list) and audit_results:
            total_w = portfolio.get("total_assets", 0)
            top3 = sorted(audit_results, key=lambda x: abs(x.get("weight", 0)), reverse=True)[:3]
            top3_str = ", ".join(
                f"{a.get('code','?')} {a.get('weight',0):.1f}%" for a in top3
            )
            concentration_summary = f"Top-3 持仓: {top3_str}"
        else:
            concentration_summary = "无持仓数据"

        prompt = f"""你是风险总监（Risk Director），职责是在 CIO 终裁前对处方进行独立的终端风险审查。

## 你的立场
- 你不对标的基本面做判断（那是 L1/L2 的职责）
- 你的职责是审查 CIO 处方的 **组合层面风险**：集中度、流动性、尾部风险、黑天鹅
- 你对每一句 CIO 的判断都要问一句"万一错了呢？"

## 审查维度

### 集中度风险
- 处方是否导致单只/单行业过度集中？
- 加仓后最极端情况下可能暴露多少？

### 流动性风险
- 建议买入的标的中，是否有流动性差的（小市值、低成交量）？
- 港股/美股标的是否考虑汇率风险？

### 尾部风险
- 处方中的 BUY/ADD 操作在什么情况下会同时亏损（相关性风险）？
- 最大的组合回撤可能是什么场景？

### 操作风险
- 处方中的 SELL/REDUCE 操作，卖出的理由是否充分？
- 卖出后如果标的继续上涨（判断错误），损失多大？

### 处方纪律
- 处方数量是否合理（20孔卡片）？
- 是否有"为了做点什么而做"的冗余操作？

### 敞口矩阵数据（基金穿透后真实暴露）
{exposure_context[:2000] if exposure_context else '无敞口数据'}

### 持仓集中度
{concentration_summary}

## 当前处方（CIO 初稿）
{chr(10).join(presc_lines) if presc_lines else '无处方'}

## CIO 判断原文
{cio_draft[:3000] if cio_draft else '无'}

## L2 候选标的参考
{chr(10).join([f"- {c.get('code', '?')}: {c.get('action', '?')}" for c in stock_candidates[:10]]) if stock_candidates else '无'}

## 输出格式
对处方中的每条操作：
- 风险审查意见：通过 / 有风险（具体要求修正）/ 否决（给出替代方案）
- 风险说明
- 修正建议

最后给出总体风险评级：低风险 / 中等风险 / 高风险，并说明组合最大回撤估计。

用中文回答。"""

        response = llm.invoke([HumanMessage(content=prompt)])
        review = response.content if hasattr(response, "content") else str(response)

        return {"risk_director_review": review}

    return risk_director_node
