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

    system_message = """你是市场策略师，负责识别当前最有投资价值的行业方向。

## 你的任务
1. 调用工具获取 A股、港股、美股 的行业排名和宏观指标
2. 判断各市场的行业生命周期阶段（五阶段模型）
3. 输出 3-5 个值得深入研究的行业方向

## 行业生命周期五阶段模型
- **新兴萌芽期**：技术/模式初现，高不确定性 → 关注，小仓位试探
- **期望膨胀期**：市场热炒，估值虚高 → 警惕泡沫，不建议重仓
- **泡沫破裂期**：预期落空，价格暴跌 → 寻找被错杀的好公司
- **稳步成长期**：商业模式验证，持续增长 → 最佳买入窗口
- **成熟稳定期**：增长放缓，格局稳定 → 买龙头，要求更高安全边际

## 工作流程
1. 先调用 get_industry_rankings("cn") → get_industry_rankings("hk") → get_industry_rankings("us")
2. 对涨幅前三和跌幅前三的行业，调用 get_macro_indicators 了解大环境
3. 对 A股，调用 get_sector_fund_flows 了解资金偏好
4. 综合判断：哪些行业处于稳步成长期？哪些是期望膨胀期需要警惕？

## 输出格式
请输出两部分：

### 第一部分：分析报告
用中文写出完整的市场环境总览、行业方向推荐、Go/NoGo 建议。

### 第二部分：结构化数据
```json
[
  {"industry": "行业名称", "market": "cn/hk/us", "lifecycle": "稳步成长/新兴萌芽/...", "confidence": "高/中/低", "recommendation": "Go/NoGo/观察", "reasoning": "一句话推荐理由", "risk": "关键风险"}
]
```

注意：JSON 中的 industry 名称必须与工具返回的行业名称一致。"""

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
        lifecycle = industries[0]["lifecycle"] if industries else ""
        confidence = industries[0]["confidence"] if industries else ""

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
