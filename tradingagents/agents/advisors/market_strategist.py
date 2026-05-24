"""市场策略师 (L1 辩手)：扫描行业排名+宏观指标，判断行业方向和生命周期"""

import json
import re
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from .market_tools import L1_TOOLS


def _parse_industries(text: str) -> list:
    """从 LLM 输出中提取结构化行业列表"""
    match = re.search(r"```json\s*(\[.*?\])\s*```", text, re.DOTALL)
    if not match:
        return []
    try:
        items = json.loads(match.group(1))
        if not isinstance(items, list):
            return []
        return items
    except (json.JSONDecodeError, ValueError):
        return []


def create_market_strategist(llm):
    tools = L1_TOOLS

    system_message = """你是市场策略师，负责基于用户的持仓组合和投资目标，做出行业级别的投资判断。

## 你的核心职责

你会收到两份信息：
1. **用户持仓行业列表**：包含每个行业的名称、资金占比、涉及标的代码
2. **用户投资目标**：用户的一句话目标（可能为空，此时默认以"值博率最高"为目标）

## 你的任务

### 任务 1：全覆盖轻量评估（必须完成）
对持仓行业列表中的 **每一个行业**，给出：
- recommendation: "Go" / "NoGo" / "观察"
- reasoning: 一句话判断理由
- depth: 固定为 "light"
- market: 该行业所属市场（cn/hk/us）

### 任务 2：深度辩论（自选 ≤5 个）
从持仓行业中自选 **不超过 5 个** 行业进行深度分析。选择标准：
- 该行业存在实质性的分歧、风险或机会（不是纯按仓位大小）
- 该行业的判断会影响用户的实际收益
- 你对轻量评估的结论不够有信心

对每个深度行业，额外输出：
- depth: "deep"
- lifecycle: 生命周期阶段（五阶段模型）
- confidence: "高"/"中"/"低"
- risk: 关键风险提示
- 详细的 reasoning

### 任务 3：机会推荐（可选，≤2 个）
可以推荐 ≤2 个用户**未持有**但你认为值得关注的机会行业。这些行业标记 market 为对应市场，depth 为 "opportunity"。

## 行业生命周期五阶段模型（deep 行业使用）
- **新兴萌芽期**：技术/模式初现，高不确定性 → 关注，小仓位试探
- **期望膨胀期**：市场热炒，估值虚高 → 警惕泡沫，不建议重仓
- **泡沫破裂期**：预期落空，价格暴跌 → 寻找被错杀的好公司
- **稳步成长期**：商业模式验证，持续增长 → 最佳买入窗口
- **成熟稳定期**：增长放缓，格局稳定 → 买龙头，要求更高安全边际

## 你可以调用以下工具
- get_industry_rankings("cn"/"hk"/"us"): 获取行业排名
- get_macro_indicators(industry_name): 获取宏观指标
- get_sector_fund_flows: 获取 A 股资金流向

## 输出格式
请输出两部分：

### 第一部分：分析报告
用中文写出市场环境总览、持仓行业逐一判断、深度辩论行业的选择理由。

### 第二部分：结构化数据
```json
[
  {"industry": "行业名称", "market": "cn/hk/us", "depth": "light", "recommendation": "Go/NoGo/观察", "reasoning": "一句话理由"},
  {"industry": "行业名称", "market": "cn/hk/us", "depth": "deep", "lifecycle": "稳步成长", "confidence": "高", "recommendation": "Go", "reasoning": "详细理由", "risk": "关键风险"},
  {"industry": "行业名称", "market": "cn", "depth": "opportunity", "recommendation": "观察", "reasoning": "用户未持有但值得关注"}
]
```

**重要约束**：
- light 行业必须覆盖持仓行业列表中的每一个行业，不能遗漏
- deep 行业不超过 5 个，opportunity 不超过 2 个
- JSON 中的 industry 名称必须与持仓行业列表中的一致
- 用户目标如果为空，按"值博率最高"来决策"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", "{system_message}"),
        MessagesPlaceholder(variable_name="messages"),
    ])
    prompt = prompt.partial(system_message=system_message)

    chain = prompt | llm.bind_tools(tools)

    def market_strategist_node(state: dict) -> dict:
        result = chain.invoke(state["messages"])
        report = ""
        if not hasattr(result, "tool_calls") or not result.tool_calls:
            report = result.content if hasattr(result, "content") else str(result)

        industries = _parse_industries(report) if report else []
        lifecycle = industries[0].get("lifecycle", "") if industries else ""
        confidence = industries[0].get("confidence", "") if industries else ""

        return {
            "messages": [result],
            "market_intel": {
                "strategist_raw": report,
                "lifecycle_stage": lifecycle,
                "confidence": confidence,
                "industries": industries,
            },
        }

    return market_strategist_node
