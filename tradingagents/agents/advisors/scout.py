"""侦察兵 (L2 辩手)：用工具扫描全市场标的，巴芒四层过滤器筛选好公司

重写：从纯 prompt agent 升级为 tool-agent，支持 A股+港股+美股 全市场扫描。
"""

import json
import re
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from .market_tools import L2_TOOLS


def _parse_candidates(text: str) -> list:
    """从 LLM 输出中提取结构化候选标的列表，支持多种格式"""
    # Strategy 1: ```json[...]``` code block
    match = re.search(r"```json\s*(\[.*?\])\s*```", text, re.DOTALL)
    if match:
        try:
            items = json.loads(match.group(1))
            if isinstance(items, list) and len(items) > 0:
                return items
        except (json.JSONDecodeError, ValueError):
            pass

    # Strategy 2: bare JSON array anywhere in text
    for m in re.finditer(r"\[[\s\S]*?\{[\s\S]*?\"code\"[\s\S]*?\}[\s\S]*?\]", text):
        try:
            items = json.loads(m.group(0))
            if isinstance(items, list) and len(items) > 0 and all(isinstance(i, dict) and "code" in i for i in items):
                return items
        except (json.JSONDecodeError, ValueError):
            continue

    # Strategy 3: extract individual entries from markdown-style report
    entries = []
    entry_pattern = re.compile(
        r'(?:^|\n)\s*(?:[-*]|\d+[.、])\s*'
        r'(?:\*\*)?(\d{5,6}\.(?:SH|SZ|HK|US|[A-Z]+)|[A-Z]{1,5})\s*'
        r'(?:\(([^)]+)\))?[：:\s]+'
        r'(buy|observe|eliminate|sell|hold|add|reduce)[\s,，]+',
        re.IGNORECASE
    )
    for m in entry_pattern.finditer(text):
        code = m.group(1)
        name = m.group(2) or ""
        action = m.group(3).lower()
        entries.append({
            "code": code,
            "name": name,
            "market": "cn" if any(s in code for s in (".SH", ".SZ")) else ("hk" if ".HK" in code else "us"),
            "action": action,
            "filter_result": "",
            "reasoning": "",
            "risk": "",
        })

    return entries


def create_scout(llm):
    tools = L2_TOOLS

    system_message = """你是侦察兵（Scout），负责在全市场（A股+港股+美股）扫描和筛选优质标的。

## 你的核心筛选框架：巴芒四层过滤器

对每只候选标的，必须依次通过四层过滤：

### 第一层：看懂生意
- 这家公司靠什么赚钱？用一句话能讲清楚吗？
- 它的客户是谁？供应商是谁？在产业链中处于什么位置？
- AI 时代能力圈不再是瓶颈——你能看懂绝大多数行业的生意逻辑
- → 讲不清楚生意逻辑的公司，直接淘汰

### 第二层：护城河
- 定价权：能否提价而不丢失客户？
- 品牌壁垒：消费者是否愿意为品牌溢价买单？
- 技术壁垒：技术领先性、专利保护
- 规模效应：边际成本随规模递减
- 网络效应：越多用户→产品越好
- 监管壁垒：牌照或许可证限制竞争
- → 没有护城河的公司，只能给"观察"评级

### 第三层：管理层
- ROE：长期 ROE 是否稳定 > 12%？
- 资本配置：是否明智地再投资或回购？
- 诚信记录：是否有损害股东利益的历史？
- → 管理层有疑问的公司，降级处理

### 第四层：价格合理
- PE/PB 在历史区间的位置
- 行业生命周期阶段校准（期望膨胀期 → 自动降级）
- 市场情绪：当前是恐惧还是贪婪？
- 安全边际：当前价格是否提供了足够的安全边际？
- → "用合理的价格买好公司"，不是"用任何价格买好公司"

## 工作流程
1. 读取 L1 的 market_intel 中的 Go 行业列表
2. 对每个 Go 行业，调用 get_industry_constituents 获取成分股
3. 对市值前 10-15 的成分股，调用 get_company_profile 和 get_financial_summary
4. 调用 get_stock_quotes 获取当前价格和走势
5. 对基金方向，调用 get_fund_rankings 获取 top 基金
6. 用四层过滤器逐只筛选

## 输出格式

### 第一部分：分析报告
用中文写出完整的标的筛选报告，包括推荐标的（通过四层过滤）、观察列表（部分通过，有疑虑）、淘汰列表（未通过核心过滤）。

### 第二部分：结构化数据
```json
[
  {"code": "标的代码", "name": "标的名称", "market": "cn/hk/us", "action": "buy/observe/eliminate", "filter_result": "通过四层/通过三层/未通过", "reasoning": "一句话推荐理由", "risk": "关键风险", "priority": "high/medium/low"}
]
```

注意：code 必须与工具返回的代码格式一致（如 A股 600519.SH，港股 00700.HK，美股 AAPL）。"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", "{system_message}"),
        MessagesPlaceholder(variable_name="messages"),
    ])
    prompt = prompt.partial(system_message=system_message)

    chain = prompt | llm.bind_tools(tools)

    def scout_node(state: dict) -> dict:
        result = chain.invoke(state["messages"])
        report = ""
        if not hasattr(result, "tool_calls") or not result.tool_calls:
            report = result.content if hasattr(result, "content") else str(result)

        candidates = _parse_candidates(report) if report else []

        return {
            "messages": [result],
            "scout_assessment": report,
            "stock_candidates": candidates,
        }

    return scout_node
