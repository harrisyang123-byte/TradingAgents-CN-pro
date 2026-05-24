# Design: Full Portfolio Coverage

## 1. 行业分类工具函数提取

### Module: `app/services/industry_classifier.py`（新增）

从 `paper.py:get_portfolio_overview()` 提取行业分类逻辑为独立函数：

```python
async def classify_holdings_industries(
    db, positions: list[dict]
) -> dict[str, list[str]]:
    """
    返回 {industry_name: [code, ...], ...}
    分类优先级：stock_basic_info.industry > 名称关键词推断 > "其他"
    """
```

同步修改 `paper.py` 调用此函数，保持概览页行为不变。

## 2. L1 接口改造

### Module: `app/routers/portfolio_analysis.py`

**PlanRequest 加 goal**：
```python
class PlanRequest(BaseModel):
    goal: str = ""  # 用户投资目标，空串 → AI 默认值博率最高
```

**L1 执行流程变更**：

```
_execute_l1():
  1. 调 classify_holdings_industries() → 持仓行业列表
  2. 计算各行业资金占比
  3. 构造 portfolio_industries = [{industry, weight, codes, ...}]
  4. advisor.propagate_l1_plan(portfolio_summary, portfolio_industries, user_goal, ...)
  5. 写入 industry_coverage（全量，status=completed，depth=light/deep）
```

**industry_coverage 写入**（替换旧的 planned 逻辑）：
```python
for ind in result["industries"]:
    await db["industry_coverage"].update_one(
        {"user_id": user_id, "industry_name": ind["industry"]},
        {"$set": {
            "status": "completed",
            "depth": ind.get("depth", "light"),
            "recommendation": ind.get("recommendation", ""),
            "confidence": ind.get("confidence", ""),
            "reasoning": ind.get("reasoning", ""),
            "lifecycle": ind.get("lifecycle", ""),
            "market": ind.get("market", "cn"),
            "analyzed_at": completed_at,
            "advice_id": task_id,
            "updated_at": completed_at,
        }},
        upsert=True,
    )
```

## 3. Agent Prompt 重写

### Module: `tradingagents/agents/advisors/market_strategist.py`

**核心变更**：从"扫描市场找机会"改为"基于持仓行业列表判断"。

新 system prompt 要点：
- 收到一份 `portfolio_industries`（含行业名、资金占比、涉及标的）
- 收到用户 `goal`（可能为空 → 默认值博率最高）
- 任务 1：对每个持仓行业做轻量评估（go/nogo + 一句话理由）
- 任务 2：自选 ≤5 个行业做深度辩论
- 任务 3：可推荐 ≤2 个用户未持有的机会行业
- 保留五阶段生命周期模型

**输出 JSON 新增 `depth` 字段**：
```json
[
  {"industry": "...", "depth": "light", "recommendation": "Go", "reasoning": "一句话"},
  {"industry": "...", "depth": "deep", "recommendation": "Go", "lifecycle": "稳步成长", "confidence": "高", "reasoning": "详细理由", "risk": "风险点"}
]
```

### Module: `tradingagents/agents/advisors/contrarian.py`

Prompt 调整：只对策略师标记为 `depth=deep` 的行业提出实质性质疑。

### Module: `tradingagents/agents/advisors/macro_judge.py`

Prompt 调整：对 `depth=light` 行业直接采信策略师判断；对 `depth=deep` 行业做完整裁决（审阅辩论记录 → Go/NoGo/观察 + 理由）。

## 4. AdvisorGraph 适配

### Module: `tradingagents/graph/advisor_graph.py`

`propagate_l1_plan()` 签名扩展：
```python
def propagate_l1_plan(
    self,
    portfolio_summary: Dict[str, Any],
    portfolio_industries: List[Dict[str, Any]],  # 新增
    user_goal: str = "",                          # 新增
    progress_callback: Optional[Callable] = None,
) -> Dict[str, Any]:
```

注入到初始状态：
```python
init_state["portfolio_industries"] = portfolio_industries
init_state["user_goal"] = user_goal
```

### Module: `tradingagents/agents/advisors/advisor_states.py`

`AdvisorState` TypedDict 加：
```python
portfolio_industries: List[Dict[str, Any]]
user_goal: str
```

## 5. 前端

### Module: `frontend/src/views/Portfolio/Analysis.vue`

**idle 状态加目标输入**：
```html
<el-input
  v-model="userGoal"
  type="textarea"
  :rows="2"
  placeholder="投资目标（选填），如：年化收益10%、最大化收益。不填则由 AI 以值博率最高为目标"
/>
```

**plan_ready 状态行业列表改造**：
- 持仓行业卡片：默认全选、不可取消（或可取消但有提示）
- AI 推荐行业卡片：可选，视觉区分（绿色边框/角标）
- 数据来源：`result.portfolio_industries`（持仓）+ `result.opportunity_industries`（AI 推荐）

### API 调用更新

`startL1Plan()` 加 `goal` 参数：
```typescript
portfolioApi.startL1Plan(goal: string)
// → POST /api/portfolio/analysis/plan { goal }
```

## 6. MongoDB

`industry_coverage` 集合：
- 加 `depth: "light" | "deep"` 字段
- 废弃 `status: "planned"`（不删除已有数据，新写入不再使用）
- 概览页 `coverage_status` 逻辑简化：有 doc 且 30 天内 = `covered`，否则 = `stale`

## 7. 验证

- L1 请求带 goal，后端正确注入 portfolio_industries
- Market Strategist 输出 JSON 所有持仓行业 + depth 字段
- industry_coverage 一次写入全量，无遗漏
- 前端 Analysis.vue：goal 输入 → 行业选择（区分持仓/AI推荐） → 执行 → 结果
