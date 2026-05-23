"""标的裁判 (L2 裁判)：读 L2 辩论记录，裁定最终推荐标的列表"""

from langchain_core.messages import HumanMessage


def create_stock_judge(llm):
    def stock_judge_node(state: dict) -> dict:
        stock_debate = state.get("stock_debate_state", {})
        debate_history = stock_debate.get("history", "")
        scout_assessment = state.get("scout_assessment", "")
        market_intel = state.get("market_intel", {})

        prompt = f"""你是标的裁判（Stock Judge），负责对 L2 标的筛选辩论做出最终裁定。

## 你的职责
1. 审阅侦察兵的标的推荐和反向意见者的质疑
2. 做出最终裁定：哪些标的进入推荐列表，哪些降级或淘汰
3. 确保每只推荐标的都通过了巴芒四层过滤器的实质审查

## 辩论记录

### 侦察兵（多方推荐）
{scout_assessment[:3000] if scout_assessment else '无评估'}

### 标的反向者（风险面挑战）
{stock_debate.get("scontrarian_response", "无评估")[:3000]}

### 辩论历史
{debate_history[:2000] if debate_history else '无辩论记录'}

### L1 行业方向参考
{market_intel.get("judge_verdict", "无")[:1500]}

## 裁定原则
- 四层过滤器全部通过 + 反向者质疑被有效回应 → 确认推荐
- 四层过滤通过但有未解决的风险疑虑 → 降级为观察
- 核心业务看不懂或没有护城河 → 淘汰
- 行业处于期望膨胀期 → 最多"观察"，不能推荐
- 不在 L1 Go 行业列表中的标的 → 特别标注原因

## 输出格式

### 最终推荐列表
对每只标的：
- 代码 + 名称 + 市场
- 裁定结果：推荐 / 观察 / 淘汰
- 推荐理由（综合多方和空方观点）
- 关键风险
- 建议操作：买入 / 观察等待更好价格 / 不操作
- 优先级：高 / 中 / 低

### 推荐理由总结
2-3句话总结为什么这些标的是当前最佳选择。

用中文回答。"""

        response = llm.invoke([HumanMessage(content=prompt)])
        verdict = response.content if hasattr(response, "content") else str(response)

        return {"stock_judge_verdict": verdict}

    return stock_judge_node
