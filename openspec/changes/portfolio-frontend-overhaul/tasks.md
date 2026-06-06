# Tasks: Portfolio Frontend Overhaul

> 变更：`portfolio-frontend-overhaul`
> 前置条件：服务运行中，MongoDB 可访问

---

## Task 1 — 后端 `/overview` 主路径补注处方和 positions_detail

**文件**: `app/routers/paper.py`

**改动**：在 `get_portfolio_overview` 的 `market_intel.industries` 主路径分支（第 612-629 行），补充：

1. 从 `latest_advice.prescription[]` 建立 `code → rx_item` 映射
2. 遍历 `matrix_list`，按 `row.codes` 交叉匹配处方，注入 `row["positions_detail"]`
3. response 补充 `total_assets`（来自 `pf_summary`）

**验收**：
- [x] `GET /api/paper/overview` 返回的 `matrix[].positions_detail` 非空（当有最近 advice 时）
- [x] `total_assets` 字段出现在 response 顶层

---

## Task 2 — 行业矩阵 GoGo/NoGo Badge + reasoning 折叠行

**文件**: `frontend/src/views/Portfolio/Overview.vue`

**改动**：

1. 「操作」列的 GoGo/NoGo 文字改为带背景色的 Badge（`go_nogo === 'GO'` → 绿底白字；`NOGO` → 红底白字；其他 → 灰色"持有"）
2. 每行增加一个隐藏的 `<tr class="reasoning-row">`，内容是 `row.reasoning`；行点击时切换展开/折叠（独立于 Drawer）
3. reasoning 行展开时高亮整行背景，折叠时不占空间
4. Drawer 宽度从 `420px` 改为 `520px`

**验收**：
- [x] 行业表格每行点击出现/隐藏推理文字
- [x] GoGo 显示绿色 Badge，NOGO 显示红色 Badge
- [x] Drawer 宽度 520px

---

## Task 3 — Drawer 处方明细修复 + PE 分位标签

**文件**: `frontend/src/views/Portfolio/Overview.vue`

**依赖**: Task 1（`positions_detail` 有数据）

**改动**：

1. `industryPositions` computed 直接读 `selectedIndustry.value.positions_detail`
2. 处方卡片布局调整，每条显示：
   - 行 1：名称 + 代码 + 操作 Badge + 盈亏%（红绿色）
   - 行 2：当前%→目标% | 调仓金额（取 `total_assets * delta_weight / 100` 取整到百）| 时机 Badge
   - 行 3：reasoning 文字（最多 3 行，超出省略号）
3. 若 `pos.pe_data` 存在，行 1 右侧追加 PE 分位 Badge（`pe_percentile_5y > 80` 红色；`< 30` 绿色；否则灰色）

**验收**：
- [x] Drawer 展示处方明细，不再空白
- [x] 每条处方有盈亏%、调仓金额、时机
- [x] pe_data 存在时显示 PE 分位

---

## Task 4 — 辩论历程折叠卡片

**文件**: `frontend/src/views/Portfolio/Overview.vue`

**改动**：

1. 在「历史分析记录」卡片之前，新增「分析师辩论历程」卡片
2. 数据来源：`latestAdvice` ref（从 `/api/paper/advice/:id` 或 adviceHistory 第一条）
3. Tab 页签：
   - **市场研判（L1）** → `market_debate_history`
   - **个股辩论（L3）** → `stock_debate_history`
   - **综合裁决** → `debate_history`
4. 内容用 `<pre>` 渲染（保留 Markdown 格式），字体 13px，最大高度 400px，可滚动
5. 卡片默认 `collapsed = true`，点击 header 展开

**验收**：
- [x] 三个 Tab 均有内容（当有最近 advice 时）
- [x] 默认折叠，不撑开页面
- [x] 内容可滚动

---

## Task 5 — 历史记录增强

**文件**: `frontend/src/views/Portfolio/Overview.vue`

**改动**：

1. 历史记录摘要行：增加「{{ row.selected_industries?.length || 0 }} 个行业」和「总资产 {{ formatMoney(row.total_assets_snapshot) }}」
2. 点击历史记录：填充 `latestAdvice` ref（包含 debate_history），让 Task 4 的辩论区块自动切换到该次分析
3. 当前选中记录高亮（`border-left: 3px solid #409eff`）

**验收**：
- [x] 历史记录卡片显示行业数
- [x] 点击历史记录后，辩论区块内容切换到该次分析
- [x] 选中记录高亮

---

## 执行顺序

```
Task 1 → Task 2 → Task 3 → Task 4 → Task 5
```

Task 3 依赖 Task 1，其余任务独立。
