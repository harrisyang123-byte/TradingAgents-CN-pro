"""CIO 裁判：读三角色评估 + 辩论记录，芒格思维约束，输出结构化处方"""

from __future__ import annotations
import json
import re
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


def create_cio(llm):
    def cio_node(state: dict) -> dict:
        portfolio = state.get("portfolio_summary", {})
        positions = portfolio.get("positions", [])
        max_single = state.get("max_single_weight", 30.0)
        max_industry = state.get("max_industry_weight", 50.0)

        analyst = state.get("analyst_assessment", "")
        strategist = state.get("strategist_assessment", "")
        scout = state.get("scout_assessment", "")

        debate = state.get("advisor_debate_state", {})
        debate_history = debate.get("history", "")

        position_lines = []
        for pos in positions:
            position_lines.append(
                f"- {pos.get('code', '?')} ({pos.get('instrument_type', 'stock')}): "
                f"仓位 {pos.get('weight', 0):.1f}%, "
                f"市值 ¥{pos.get('market_value_cny', 0):,.2f}"
            )

        prompt = f"""你是组合顾问团队的首席投资官 (CIO)。你拥有最终决策权。

你需要综合三位顾问的评估和辩论记录，做出组合层面的操作建议。

## 三位顾问的评估

### 持仓分析师（关注个股安全边际）
{analyst[:2000] if analyst else '无评估'}

### 策略师（关注组合构建 + 逆向思维）
{strategist[:2000] if strategist else '无评估'}

### 侦察兵（关注组合缺口 + 新标的发现）
{scout[:2000] if scout else '无评估'}

## 辩论记录
{debate_history[:3000] if debate_history else '无辩论记录'}

## 当前持仓
{chr(10).join(position_lines) if position_lines else '无持仓'}

## 你的思维约束（必须遵守）

### 逆向验证（每条加仓/建仓建议必须回答）
对于每条"买入"或"加仓"建议，你必须回答：
- 如果这个判断是错的，最大亏损是多少？
- 在什么情况下这个判断会失败？

### 认知偏差检测
在做决策前，检查自己是否受到以下偏差影响：
- 禀赋效应：是否因为已持有就不愿卖出
- 近因偏差：是否过度重视最近的涨跌
- 锚定效应：是否被成本价锚定

### 定量红线（硬限制）
- 单只标的仓位不超过 {max_single}%
- 单一行业不超过 {max_industry}%
- 如果你的建议会突破红线，必须在理由中显式说明

## 输出格式

请输出两部分：

### 第一部分：总体判断
用 2-3 段话总结你的投资判断、关键分歧点、以及你如何权衡三位顾问的意见。

### 第二部分：操作处方
以 JSON 数组格式输出，用 ```json 包裹。每个元素包含：
- code: 股票代码
- action: buy / sell / hold / reduce / add / new_position 之一
- current_weight: 当前仓位占比（数字，无持仓填 0）
- target_weight: 建议目标仓位占比（数字）
- reasoning: 操作理由（1-2 句话）
- risk_note: 风险提示（如果判断错了会怎样）

示例：
```json
[
  {{"code": "600519", "action": "hold", "current_weight": 15.0, "target_weight": 15.0, "reasoning": "估值合理，持有观望", "risk_note": "白酒行业政策风险"}},
  {{"code": "300750", "action": "reduce", "current_weight": 25.0, "target_weight": 15.0, "reasoning": "仓位过重，突破单只30%红线风险", "risk_note": "减仓后若继续上涨损失收益"}}
]
```

请用中文回答。"""

        from langchain_core.messages import HumanMessage
        response = llm.invoke([HumanMessage(content=prompt)])
        verdict = response.content if hasattr(response, "content") else str(response)

        prescription = _parse_prescription(verdict)

        logger.info(f"[CIO] 裁决完成，{len(prescription)} 条处方，输出 {len(verdict)} 字符")
        return {
            "cio_verdict": verdict,
            "prescription": prescription,
        }

    return cio_node


def _parse_prescription(text: str) -> list:
    """从 CIO 输出中提取 JSON 处方"""
    match = re.search(r"```json\s*(\[.*?\])\s*```", text, re.DOTALL)
    if not match:
        match = re.search(r"\[[\s\S]*?\{[\s\S]*?\"code\"[\s\S]*?\}[\s\S]*?\]", text)
    if not match:
        return []
    try:
        items = json.loads(match.group(1) if match.lastindex else match.group(0))
        if not isinstance(items, list):
            return []
        valid = []
        for item in items:
            if isinstance(item, dict) and "code" in item:
                valid.append({
                    "code": str(item.get("code", "")),
                    "action": str(item.get("action", "hold")),
                    "current_weight": float(item.get("current_weight", 0)),
                    "target_weight": float(item.get("target_weight", 0)),
                    "reasoning": str(item.get("reasoning", "")),
                    "risk_note": str(item.get("risk_note", "")),
                })
        return valid
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"[CIO] 处方解析失败: {e}")
        return []
