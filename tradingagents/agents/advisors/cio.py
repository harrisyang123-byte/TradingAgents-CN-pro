"""CIO 首席投资官 (L4) — 工具型 Agent，多步迭代决策"""

from __future__ import annotations
import json
import re
import time
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")

CIO_SYSTEM_PROMPT = """你是组合顾问团队的首席投资官 (CIO)。你需要制定完整的行业配置方案和组合操作处方。

## 你的工具（按需调用，不要一次性全调）
1. `get_position_batch(batch_num)` — 分页读持仓，每批 10 只。先调 batch=1 看总数，再逐批读完
2. `get_l1_verdict(industry)` — 查某行业 L1 评级（Go/NoGo/观察）
3. `get_l2_candidates()` — 读 L2 Scout 筛出的候选标的池
4. `dispatch_scout(industry, market)` — 派员工去搜索行业 Top 标的（当 L2 未覆盖时使用）
5. `search_industry_etf(industry, market)` — 搜索某行业的 ETF/指数基金
6. `validate_allocation(json)` — 验证行业权重方案是否合规（Σ≤100%，单行业≤50%，现金≥5%）

## 决策流程（按顺序）

### Phase 1: 数据收集
- 调用 `get_position_batch(1)` 看第一批持仓和总数
- 如果 has_more=true，继续调用 batch=2,3,4... 直到读完
- 每批持仓中，对每个标的的 industry 字段，调用 `get_l1_verdict(industry)` 查行业评级
- 调用 `get_l2_candidates()` 获取 L2 候选池

### Phase 2: 行业配置方案
- 按行业分组所有持仓标的
- 基于 L1 评级定级：超配(Go)/标配(Go+Watch)/低配(Watch)/零配(NoGo)
- 超配行业组合内标的少 → 调用 `dispatch_scout(industry)` 搜索
- 需要 ETF 暴露 → 调用 `search_industry_etf(industry)` 找基金工具
- 给出每个行业的目标权重百分比（总和 ≤ 100%）

### Phase 3: 约束验证
- 调用 `validate_allocation(行业配置JSON)` 检查合规
- 有 violations → 修正后重新 validate

### Phase 4: 标的级决策
- 每只存量持仓判定：hold / add / reduce / sell
- 增量标的判定：new_position（标注资金来源）

### Phase 5: 资金配对
- Σ 买入 ≤ 可用现金 + Σ 卖出释放
- 每笔 new_position/add 标注 capital_source

### Phase 6: 输出
先输出行业配置表（Markdown 表格），再输出 JSON 处方。

## 硬性要求
- 存量必须全覆盖：每只现有持仓都要出现在处方 JSON 中
- Hold 也要列：action="hold" 必须写明维持理由
- NoGo 行业不留仓：L1 判 NoGo 的行业，目标权重必须为 0%
- 新标的要有来路：要么 L2 候选池，要么 dispatch_scout，不能凭空推荐
- 基金标注角色：fund_role = "行业暴露工具" | "主动alpha来源" | "现金管理工具"

## JSON 输出格式
```json
[
  {"code": "...", "name": "...", "instrument_type": "stock/fund/etf",
   "action": "buy/sell/hold/reduce/add/new_position",
   "current_weight": 0.0, "target_weight": 0.0,
   "split_type": "存量体检/增量探索",
   "industry_bucket": "行业名称", "fund_role": "",
   "priority": "urgent/important/optional", "timing": "immediate/conditional/scheduled",
   "l1_context": "...", "l2_context": "...",
   "reasoning": "...", "risk_note": "...", "capital_source": "..."},
  ...
]
```
"""


def create_cio(llm, tools=None, shared_state=None):
    """创建 CIO Agent（工具型，多步迭代）

    Args:
        llm: LLM 实例
        tools: 外部创建的工具列表（图层面创建并传入）
        shared_state: 共享状态引用字典，tools 和 agent 共用同一 state 引用
    """
    if shared_state is None:
        shared_state = {}

    if tools is None:
        from .cio_tools import create_cio_tools
        def _sp():
            return shared_state.get("state", {})
        tools = create_cio_tools(_sp)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "{system_message}"),
        MessagesPlaceholder(variable_name="messages"),
    ])
    prompt = prompt.partial(system_message=CIO_SYSTEM_PROMPT)
    chain = prompt | llm.bind_tools(tools)

    def sanitize_messages(messages: list) -> list:
        """清除孤立的 tool_calls（有 AIMessage.tool_calls 但无对应 ToolMessage）"""
        if not messages:
            return messages
        from langchain_core.messages import AIMessage, ToolMessage
        tool_result_ids = set()
        for m in messages:
            if isinstance(m, ToolMessage):
                tool_result_ids.add(m.tool_call_id)
        cleaned = []
        for m in messages:
            if isinstance(m, AIMessage) and hasattr(
                    m, "tool_calls") and m.tool_calls:
                orphaned = [
                    tc for tc in m.tool_calls
                    if tc.get("id") not in tool_result_ids
                ]
                if orphaned and not (
                        hasattr(m, "content") and m.content):
                    continue
            cleaned.append(m)
        return cleaned

    def cio_node(state: dict) -> dict:
        shared_state["state"] = state

        is_final = bool(state.get("risk_director_review", ""))
        prefix = "CIO_Final" if is_final else "CIO_Draft"

        portfolio = state.get("portfolio_summary", {})
        positions = portfolio.get("positions", [])
        available_cash = portfolio.get("available_cash", 0.0)
        total_assets = portfolio.get("total_assets", 0.0)

        msgs = list(state.get("messages", []))
        msgs = sanitize_messages(msgs)

        init_content = (
            f"请开始分析组合。当前持仓 {len(positions)} 只，"
            f"可用现金 ¥{available_cash:,.2f}，"
            f"总资产 ¥{total_assets:,.2f}。\n\n"
            f"请先调用 get_position_batch(1) 查看第一批持仓数据。"
        )

        if is_final:
            risk_review = state.get(
                "risk_director_review", "")[:4000]
            init_content += (
                f"\n\n## 风险总监审查意见\n\n{risk_review}\n\n"
                f"请基于风险总监的意见，修正你的处方并输出最终版本。"
            )

        msgs.append(HumanMessage(content=init_content))

        logger.info(f"[{prefix}] 开始, messages={len(msgs)}")
        start = time.time()
        result = chain.invoke(msgs)
        elapsed = time.time() - start

        report = ""
        has_tool_calls = (hasattr(result, "tool_calls") and
                          result.tool_calls)

        if has_tool_calls:
            logger.info(
                f"[{prefix}] 触发 {len(result.tool_calls)} 个 "
                f"工具调用, 耗时 {elapsed:.1f}s")
        else:
            report = (result.content if hasattr(result, "content")
                      else str(result))
            logger.info(
                f"[{prefix}] 完成, 输出 {len(report)} 字符, "
                f"耗时 {elapsed:.1f}s")

        prescription = _parse_prescription(report) if report else []

        messages_out = [result]
        if not has_tool_calls:
            return {
                "messages": messages_out,
                "prescription": prescription,
                "cio_verdict": report,
            }
        return {"messages": messages_out}

    return cio_node


def _parse_prescription(text: str) -> list:
    """从 CIO 输出中提取 JSON 处方"""
    match = re.search(
        r"```json\s*(\[.*?\])\s*```", text, re.DOTALL)
    if not match:
        match = re.search(
            r"\[[\s\S]*?\{[\s\S]*?\"code\"[\s\S]*?\}[\s\S]*?\]", text)
    if not match:
        return []
    try:
        items = json.loads(
            match.group(1) if match.lastindex else match.group(0))
        if not isinstance(items, list):
            return []
        valid = []
        for item in items:
            if isinstance(item, dict) and "code" in item:
                valid.append({
                    "code": str(item.get("code", "")),
                    "name": str(item.get("name", "")),
                    "instrument_type": str(
                        item.get("instrument_type", "stock")),
                    "action": str(item.get("action", "hold")),
                    "current_weight": float(
                        item.get("current_weight", 0)),
                    "target_weight": float(
                        item.get("target_weight", 0)),
                    "reasoning": str(item.get("reasoning", "")),
                    "risk_note": str(item.get("risk_note", "")),
                    "split_type": str(item.get("split_type", "")),
                    "avg_cost": str(item.get("avg_cost", "")),
                    "pnl_pct": str(item.get("pnl_pct", "")),
                    "cost_context": str(
                        item.get("cost_context", "")),
                    "timing": str(
                        item.get("timing", "immediate")),
                    "capital_source": str(
                        item.get("capital_source", "")),
                    "trigger_condition": str(
                        item.get("trigger_condition", "")),
                    "priority": str(
                        item.get("priority", "optional")),
                    "l1_context": str(item.get("l1_context", "")),
                    "l2_context": str(item.get("l2_context", "")),
                    "suggested_price": str(
                        item.get("suggested_price", "")),
                    "max_loss_pct": str(
                        item.get("max_loss_pct", "")),
                    "five_year_view": str(
                        item.get("five_year_view", "")),
                    "bias_check": str(
                        item.get("bias_check", "")),
                    "fund_role": str(item.get("fund_role", "")),
                    "industry_bucket": str(
                        item.get("industry_bucket", "")),
                })
        return valid
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"[CIO] 处方解析失败: {e}")
        return []
