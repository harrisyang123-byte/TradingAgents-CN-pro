# Design: 持仓组合规划

## Data Model

### `industry_coverage` 集合

```json
{
  "_id": ObjectId,
  "user_id": "string",
  "industry_name": "食品饮料",
  "market": "cn",
  "lifecycle": "成熟稳定期",
  "go_nogo": "NoGo",
  "confidence": "高",
  "reasoning": "消费降级压力持续，白酒渠道库存高企",
  "priority": 3,
  "analyzed_at": "2026-05-24T10:30:00Z",
  "advice_id": "uuid",
  "status": "completed",
  "created_at": "2026-05-24T10:30:00Z"
}
```

索引: `{user_id: 1, industry_name: 1}`, `{user_id: 1, status: 1}`, `{analyzed_at: -1}`

### `analysis_reports` 扩展

新增 `report_type` 字段：
- `"single"` — 单股/基金分析（存量默认值）
- `"portfolio"` — 组合建议（stock_symbol=`portfolio_{advice_id}`）

## API Design

### 组合分析 API

```
POST /api/portfolio/analysis/plan
  → 触发 L1 市场扫描
  ← {task_id, status: "running"}

GET /api/sse/portfolio/{task_id}
  → SSE 流式推送
  ← event: progress, data: {node, stage, text}

POST /api/portfolio/analysis/execute
  body: {task_id, selected_industries: [...]}
  ← {task_id, status: "running"}

GET /api/portfolio/analysis/{task_id}/status
  ← {status, progress, steps, result?}
```

### 总揽 API

```
GET /api/portfolio/overview
  ← {industries: IndustryRow[], history: AdviceSummary[]}

IndustryRow = {
  industry_name, current_weight, holdings[],
  last_analysis_at, lifecycle, go_nogo, coverage_status,
  recommended_weight, weight_delta, prescribed_action, key_risk,
  linked_reports[]
}
```

### 报告 API 扩展

```
GET /api/reports/list?report_type=portfolio
  ← 已有结构 + type 动态化
```

## Two-Phase Graph

```
Phase 1: propagate_l1_plan()
  market_strategist → contrarian → debate → macro_judge
  → 返回 {industries, market_intel, macro_judge_verdict}

Phase 2: propagate_advice(selected_industries=[...])
  scout(stock_candidates filtered by industries) → ... → CIO_Final
  → 完整四层分析
```

每个节点完成时调用 `progress_callback(node_label, output_text)` → publish Redis。
