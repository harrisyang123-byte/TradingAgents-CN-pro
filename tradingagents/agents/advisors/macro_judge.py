"""宏观裁判 (L1 裁判)：读 L1 辩论记录，裁决 Go/NoGo + 行业方向最终建议"""

from langchain_core.messages import HumanMessage


def create_macro_judge(llm):
    def macro_judge_node(state: dict) -> dict:
        market_intel = state.get("market_intel", {})
        debate = state.get("market_debate_state", {})
        debate_history = debate.get("history", "")
        strategist_raw = market_intel.get("strategist_raw", "")
        contrarian_raw = debate.get("contrarian_response", "")

        prompt = f"""你是宏观裁判（Macro Judge），负责对 L1 行业方向辩论做出最终裁决。

## 你的职责
1. 审阅市场策略师的行业推荐和反向意见者的质疑
2. 做出最终裁定：哪些行业方向值得进入（Go），哪些应回避（NoGo）
3. 为每个 Go 的行业标注生命周期阶段和置信度

## 辩论记录

### 市场策略师（多方）
{strategist_raw[:3000] if strategist_raw else '无评估'}

### 反向意见者（风险面）
{contrarian_raw[:3000] if contrarian_raw else '无评估'}

### 辩论历史
{debate_history[:2000] if debate_history else '无辩论记录'}

## 裁决原则
- 策略师的推荐 + 反向意见者的质疑都有道理时 → 降级（Go 但降低置信度）
- 策略师的推荐有数据支撑、反向意见者的质疑无力 → 确认 Go
- 反向意见者的质疑有实质性风险、策略师未回应 → NoGo
- 行业处于期望膨胀期 → 最多给"观察"评级，不能给 Go

## 输出格式

### 最终裁定

对每个行业给出：
- 行业名称 + 市场
- 裁定结果：Go / NoGo / 观察
- 生命周期阶段：新兴萌芽 / 期望膨胀 / 泡沫破裂 / 稳步成长 / 成熟稳定
- 置信度：高 / 中 / 低
- 裁定理由（2-3句话，说明如何权衡双方意见）
- 关键风险提示

### Go 行业优先级排序
按推荐优先顺序排列 Go 的行业，供 L2 标的筛选使用。

用中文回答。"""

        response = llm.invoke([HumanMessage(content=prompt)])
        verdict = response.content if hasattr(response, "content") else str(response)

        return {
            "macro_judge_verdict": verdict,
            "market_intel": {
                **market_intel,
                "judge_verdict": verdict,
            },
        }

    return macro_judge_node
