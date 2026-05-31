"""侦察兵 (L2 辩手)：全市场扫描 + 6维度评分筛选优秀公司

重写：从"巴芒四层过滤器"模糊 prompt 升级为结构化 6 维度评分体系，
修复回退模式无上下文问题。
"""

import json
import re
import logging
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from .market_tools import L2_TOOLS

logger = logging.getLogger("webapi")


def _sanitize_messages(msgs: list) -> list:
    """确保消息历史中每个 tool_calls 都有对应的 ToolMessage 响应"""
    if not msgs:
        return msgs
    cleaned = []
    pending_tool_ids = set()
    for m in msgs:
        if isinstance(m, AIMessage) and hasattr(m, "tool_calls") and m.tool_calls:
            for tc in m.tool_calls:
                pending_tool_ids.add(tc.get("id", ""))
        elif isinstance(m, ToolMessage):
            tid = getattr(m, "tool_call_id", "")
            pending_tool_ids.discard(tid)
        cleaned.append(m)

    if pending_tool_ids:
        logger.warning(
            f"[Scout] 检测到 {len(pending_tool_ids)} 个未响应的 tool_calls，清理消息历史"
        )
        safe = []
        for m in msgs:
            if isinstance(m, AIMessage) and hasattr(m, "tool_calls") and m.tool_calls:
                if any(tc.get("id", "") in pending_tool_ids for tc in m.tool_calls):
                    break
            safe.append(m)
        if safe:
            return safe
        for m in reversed(msgs):
            if isinstance(m, HumanMessage):
                return [m]
        return [HumanMessage(content="Continue")]

    return cleaned


def _parse_candidates(text: str) -> list:
    """从 LLM 输出中提取结构化候选标的列表"""
    # Strategy 1: ```json[...]``` code block
    match = re.search(r"```json\s*(\[.*?\])\s*```", text, re.DOTALL)
    if match:
        try:
            items = json.loads(match.group(1))
            if isinstance(items, list) and len(items) > 0:
                return items
        except (json.JSONDecodeError, ValueError):
            pass

    # Strategy 2: bare JSON array
    for m in re.finditer(r"\[[\s\S]*?\{[\s\S]*?\"code\"[\s\S]*?\}[\s\S]*?\]", text):
        try:
            items = json.loads(m.group(0))
            if isinstance(items, list) and len(items) > 0 and all(isinstance(i, dict) and "code" in i for i in items):
                return items
        except (json.JSONDecodeError, ValueError):
            continue

    # Strategy 3: markdown entries
    entries = []
    entry_pattern = re.compile(
        r'(?:^|\n)\s*(?:[-*]|\d+[.、])\s*'
        r'(?:\*\*)?(\d{5,6}\.(?:SH|SZ|HK|US|[A-Z]+)|[A-Z]{1,5})\s*'
        r'(?:\(([^)]+)\))?[：:\s]+',
        re.IGNORECASE
    )
    for m in entry_pattern.finditer(text):
        code = m.group(1)
        name = m.group(2) or ""
        entries.append({
            "code": code, "name": name,
            "market": "cn" if any(s in code for s in (".SH", ".SZ")) else ("hk" if ".HK" in code else "us"),
            "action": "observe", "reasoning": "", "risk": "",
            "score_business_model": 0, "score_moat": 0, "score_management": 0,
            "score_financials": 0, "valuation": "", "top_risks": [],
        })
    return entries


SCOUT_SYSTEM_PROMPT = """你是侦察兵（Scout），负责在全市场（A股+港股+美股）扫描和筛选真正的优秀公司。

## 核心方法论：优秀公司 6 维度评分

对每只候选标的，必须按以下 6 个维度逐一打分：

### 1. 生意模式（1-10分）
- 这家公司靠什么赚钱？一句话能讲清楚吗？
- 客户是谁？供应商是谁？产业链位置？
- 生意是否可持续？过去 5 年营收是否稳定增长？
- ≤3分：看不懂的生意 → 直接淘汰

### 2. 护城河（1-10分）
- 定价权：能否提价而不丢失客户？
- 品牌壁垒 / 技术壁垒 / 规模效应 / 网络效应 / 监管壁垒
- ≤4分：无护城河 → 观察列表

### 3. 管理层（1-5分）
- 长期 ROE 是否 >12%？
- 资本配置能力（再投资 vs 回购 vs 分红）
- 诚信记录（是否有损害股东利益的历史？）
- ≤2分：管理层有问题 → 淘汰

### 4. 财务健康（1-10分）
- 负债率、自由现金流、经营现金流 vs 净利润
- 应收账款/存货是否异常增长？
- ROE 来源（真实盈利能力 vs 高杠杆）

### 5. 估值合理性
- PE 分位 vs 历史区间
- 与同行业对比
- 判定：低估 / 合理 / 偏贵

### 6. 风险因素
- 列出 Top 3 关键风险（行业风险、监管风险、竞争风险、技术替代风险）

## 综合推荐等级
- 强烈推荐（≥35分）：生意好 + 护城河深 + 管理优秀 + 财务健康 + 估值合理
- 推荐（≥28分）：多数维度优秀，有 1-2 个瑕疵
- 观察（≥20分）：有亮点但风险显著，需要等待更好时机
- 不推荐（<20分）：有致命缺陷

## 工作流程
1. 读取 L1 的 market_intel → Go 行业列表
2. 对每个 Go 行业，调用 get_industry_constituents 获取成分股
3. 对市值前 10-15 只，调用 get_company_profile + get_financial_summary + get_stock_quotes
4. 调用 get_global_leaders(industry, market) 获取该行业全球优质对标公司
5. 用 6 维度逐只评分，输出完整评分表

## 输出格式

### 第一部分：行业扫描摘要
每个 Go 行业：成分股数量、代表性标的、行业趋势判断

### 第二部分：标的评分表
| 代码 | 名称 | 生意 | 护城河 | 管理 | 财务 | 估值 | 总分 | 推荐 |
每只推荐标的附评分理由。

### 第三部分：结构化数据
```json
[
  {
    "code": "标的代码", "name": "标的名称", "market": "cn/hk/us",
    "action": "buy/observe/eliminate",
    "score_business_model": 8, "score_moat": 7, "score_management": 4,
    "score_financials": 7, "valuation": "合理/低估/偏贵",
    "total_score": 26, "recommendation": "推荐/观察/不推荐",
    "top_risks": ["风险1", "风险2", "风险3"],
    "reasoning": "推荐理由一句话",
    "priority": "high/medium/low"
  }
]
```

注意：
- 不要只推荐大盘股（如腾讯/茅台）— 中小市值优质公司同样重要
- 多个行业要覆盖，不要只关注一个行业
- 港股代码格式为 5 位数字（如 00700），美股为字母（如 AAPL）
- code 格式与工具返回一致（A股 600519.SH，港股 00700.HK，美股 AAPL）"""


def create_scout(llm):
    tools = L2_TOOLS

    prompt = ChatPromptTemplate.from_messages([
        ("system", "{system_message}"),
        MessagesPlaceholder(variable_name="messages"),
    ])
    prompt = prompt.partial(system_message=SCOUT_SYSTEM_PROMPT)

    chain = prompt | llm.bind_tools(tools)
    fallback_chain = prompt | llm

    def scout_node(state: dict) -> dict:
        # 注入选定行业
        selected = state.get("selected_industries", [])
        msg_list = list(state["messages"])
        if selected:
            industry_hint = (
                f"\n\n⚠️ 本次分析限定以下行业：{', '.join(selected)}。"
                f"请仅扫描这些行业内的标的，不要扫描其他行业。"
            )
            last_msg = msg_list[-1] if msg_list else None
            if last_msg and hasattr(last_msg, "content") and isinstance(last_msg.content, str):
                if "限定以下行业" not in last_msg.content:
                    msg_list[-1] = HumanMessage(content=last_msg.content + industry_hint)

        msgs = _sanitize_messages(msg_list)

        try:
            result = chain.invoke(msgs)
        except Exception as e:
            err_msg = str(e)
            if "tool_calls" in err_msg or "insufficient tool messages" in err_msg:
                logger.warning(
                    f"[Scout] tool_calls 异常，降级为无工具模式: {err_msg[:150]}"
                )
                # 降级：保留已获取的数据作为上下文
                fallback_msgs = list(msgs)
                fallback_msgs.append(HumanMessage(
                    content="工具调用出现问题。请基于你的知识库和此前已获取的所有数据，"
                            "直接给出标的筛选报告。必须包含完整的分析文本和JSON结构化数据块，"
                            "不要调用任何工具函数。"
                ))
                result = fallback_chain.invoke(fallback_msgs)
            else:
                raise

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
