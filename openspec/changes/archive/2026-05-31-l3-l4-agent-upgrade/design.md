# L3/L4 Agent 升级 — 技术方案

## 架构总览

```
L1: market_strategist(Agent+ToolNode) ←→ contrarian(Agent+ToolNode) → macro_judge(纯LLM裁判)
L2: scout(Agent+ToolNode) ←→ stock_contrarian(Agent+ToolNode) → stock_judge(纯LLM裁判)
L3: Analyst(Agent+ToolNode) → msg_clear → Strategist(Agent+ToolNode) → msg_clear → Scout_L3(纯LLM) → debate → enrich_price_data
L4: CIO(Agent+ToolNode) → msg_clear → Risk_Director(Agent+ToolNode) → msg_clear → debate → CIO_Final(Agent+ToolNode) → END
```

## Agent 模式（复用 L1/L2 已验证模式）

### 工具型 Agent 节点

```python
prompt = ChatPromptTemplate.from_messages([
    ("system", "{system_message}"),
    MessagesPlaceholder(variable_name="messages"),
])
chain = prompt.partial(system_message=...) | llm.bind_tools(TOOLS)

def agent_node(state: dict) -> dict:
    msgs = state.get("messages", [])
    result = chain.invoke(msgs)
    return {"messages": [result], ...}
```

### ToolNode + 计数器

```python
tools_node = _make_tool_executor(tools, counter_key)  # 内置 max_calls=3 强制总结
router = _make_tool_router(counter_key, next_node, agent_node)  # 条件路由
```

### msg_clear 节点

```python
_msg_clear_node(state) -> {"messages": [RemoveMessage(...), HumanMessage("Continue")]}
```

## L3 变更

### Analyst → 工具型 Agent

**工具** (analyst_tools.py):
1. `read_tier1_report(code)` — 读取单只标的的 Tier1 深度分析报告
2. `get_position_audit(code)` — 读取持仓体检数据（成本、现价、盈亏、健康分）

系统 prompt 指导分析师逐只调用工具，对每只输出安全边际评估。

### Strategist → 工具型 Agent

**工具** (strategist_tools.py):
1. `compute_sector_concentration()` — 计算行业集中度，标注是否突破 50% 红线
2. `compute_top_holdings_risk(n)` — 计算前 N 大持仓合计权重，估算最大回撤影响
3. `compute_cash_drag()` — 计算现金拖累和机会成本

### Scout_L3（纯 prompt，不变）

维持现有纯 prompt 调用，读 L2 stock_candidates + 组合缺口。

## L4 变更

### CIO → 工具型 Agent

**工具** (cio_tools.py):
1. `get_position_batch(batch_num)` — 分页读持仓，每批 10 只。先调 batch=1 看总数，再逐批读完
2. `get_l1_verdict(industry)` — 查某行业 L1 评级（Go/NoGo/观察 + 生命周期阶段）
3. `get_l2_candidates()` — 读 L2 Scout 筛出的候选标的池
4. `dispatch_scout(industry, market)` — 派员工去搜索该行业 Top 标的（链式调用 L2 已有数据函数）
5. `search_industry_etf(industry, market)` — 搜索某行业的 ETF/指数基金
6. `validate_allocation(json)` — 验证行业权重方案是否合规

**6 阶段决策流程**:
- Phase 1: 数据收集（逐批读持仓 + L1/L2 数据）
- Phase 2: 行业配置方案（按 L1 评级定级）
- Phase 3: 约束验证
- Phase 4: 标的级决策
- Phase 5: 资金配对
- Phase 6: 输出（行业配置表 + JSON 处方）

### Risk Director → 工具型 Agent

**工具** (risk_tools.py):
1. `get_prescription_draft()` — 读取 CIO 初稿处方
2. `check_stress_scenario(scenario)` — 获取场景压力测试结果

## 图结构变更

### L3 新结构

```
msg_clear_final_l2 → Analyst --[tool_loop]--> msg_clear_l3a
  → Strategist --[tool_loop]--> msg_clear_l3b
  → Scout_L3 → debate_analyst → debate_strategist → debate_scout_l3 → debate_advisor_ctr
  --[轮次够了?]--> enrich_price_data
```

### L4 新结构

```
enrich_price_data → CIO --[tool_loop]--> msg_clear_l4a
  → Risk_Director --[tool_loop]--> msg_clear_l4b
  → debate → CIO_Final --[tool_loop]--> END
```

## State 新增字段

```python
# advisor_states.py 新增
cio_tool_call_count: int
analyst_tool_call_count: int
strategist_tool_call_count: int
risk_tool_call_count: int
```

## dispatch_scout 实现细节

CIO 派员工搜索某行业时，内部链式调用 L2 已有工具:

```
get_industry_constituents(industry, market)     # 获取成分股列表
→ get_company_profile(code, market)             # 逐只获取公司概况
→ get_financial_summary(code, market)           # 逐只获取财务摘要
→ get_stock_quotes(code, market)                # 获取行情数据
```

返回该行业 Top 10 标的列表（含 PE/ROE/营收增速/市值）。

## CLI 入口

```bash
# 完整 L1→L4 执行
python cli/run_advisor.py run --user-id 6a094adc2c14a0b1cc6201ff

# Lite 模式（复用缓存 L1/L2，仅跑 L3+L4）
python cli/run_advisor.py run --user-id 6a094adc2c14a0b1cc6201ff --lite

# 展示最新处方
python cli/run_advisor.py show --user-id 6a094adc2c14a0b1cc6201ff
```
