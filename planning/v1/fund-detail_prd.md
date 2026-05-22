# FundDetail 页面 PRD (O.A.I.S)

## 1. Objective (目标)

### P.A.M 框架

| 维度 | 定义 | 度量方式 |
|------|------|----------|
| **Problem** | 当前持仓列表无法查看单只基金的详细持仓数据（重仓股、行业分布），用户缺乏穿透分析能力 | 用户在持仓列表点击基金代码 → 404 / 无响应 |
| **Action** | 开发基金详情页，提供基金基础概况 + 穿透数据（十大重仓股 + 行业分布） | 页面成功渲染真实数据，从持仓列表正确路由跳转 |
| **Measurement** | 页面加载成功率 ≥ 95%，AKShare 数据获取延迟 < 3s，用户从点击到看到详情 ≤ 2 次点击 | 前端日志 + 后端 API 响应时间监控 |

### 用户故事

> 作为一名组合持仓用户，我希望在持仓列表中点击基金的代码，能进入一个专门的详情页面，查看该基金的基本信息、前十大重仓股和行业分布，从而判断该基金是否值得继续持有。

---

## 2. Architecture (架构)

### 2.1 实体模型

```
FundDetail
  ├── code: string (基金代码)
  ├── name: string (基金名称)
  ├── type: string (基金类型)
  ├── scale: number (最新规模，亿元)
  ├── establishment_date: string (成立日期)
  ├── manager: string (基金经理)
  ├── top_holdings: TopHolding[]
  │   ├── stock_code: string
  │   ├── stock_name: string
  │   ├── ratio: number (占净值比例 %)
  │   └── change: number (较上期变化 %)
  └── sector_distribution: SectorItem[]
      ├── sector_name: string (行业名称)
      └── ratio: number (权重占比 %)
```

### 2.2 状态图

```
[初始态] → 加载中 → [理想态]
                  → [空态]    ← 基金无持仓数据 / 数据未披露
                  → [错误态]  ← AKShare 接口超时 / 基金代码无效 / 网络异常
```

### 2.3 路由设计

```
/portfolio/fund/:code → FundDetail 页面
```

从 `PaperTrading` 持仓列表的基金代码 (`instrument_type === 'fund'`) 点击跳转，携带 `code` 参数。

---

## 3. Interface (接口与页面绑定)

### 3.1 后端 API

| 端点 | 方法 | 参数 | 响应 |
|------|------|------|------|
| `/api/fund/basic-info?code={code}` | GET | code: string | `{ code, name, type, scale, establishment_date, manager }` |
| `/api/fund/top-holdings?code={code}` | GET | code: string | `{ code, holdings: [{ stock_code, stock_name, ratio, change }] }` |
| `/api/fund/sector-distribution?code={code}` | GET | code: string | `{ code, sectors: [{ sector_name, ratio }] }` |

### 3.2 页面 - 实体绑定

| 页面区域 | 数据实体 | API 端点 | 状态覆盖 |
|----------|----------|----------|----------|
| 基础概况卡片 | `basic-info` | `/api/fund/basic-info` | loading / 理想 / 错误 |
| 十大重仓股表格 | `top-holdings` | `/api/fund/top-holdings` | loading / 理想 / 空(无数据) / 错误 |
| 行业分布图表 | `sector-distribution` | `/api/fund/sector-distribution` | loading / 理想 / 空 / 错误 |

### 3.3 页面渲染示意

```
┌─────────────────────────────────────────┐
│  首页 / 我的持仓 / {基金名称}     ← 面包屑 │
├─────────────────────────────────────────┤
│  ┌ 基础概况卡片 ──────────────────────┐  │
│  │  基金名称: 易方达蓝筹精选          │  │
│  │  基金代码: 005827  类型: 混合型    │  │
│  │  最新规模: 420.50亿  成立日期: ... │  │
│  │  基金经理: 张坤                     │  │
│  └────────────────────────────────────┘  │
│  ┌ 十大重仓股 ────────────────────────┐  │
│  │  股票代码 │ 股票名称 │ 占净值比例(%) │  │
│  │  600519  │ 贵州茅台 │  9.85       │  │
│  │  ...     │          │             │  │
│  └────────────────────────────────────┘  │
│  ┌ 行业分布 ──────────────────────────┐  │
│  │  食品饮料 ████████████ 40.2%      │  │
│  │  银行     ██████      18.5%       │  │
│  │  医药     ████        12.3%       │  │
│  └────────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

---

## 4. Scenarios (场景与状态覆盖)

### 4.1 SECURE 框架

| 分类 | 场景 | 触发条件 | 预期行为 |
|------|------|----------|----------|
| **Standard** | 正常浏览 | 用户从持仓列表点击基金 | 页面加载并展示完整数据 |
| **Empty** | 基金无持仓数据 | 新成立基金/数据未披露 | 重仓股和行业分布显示"暂无数据" |
| **Error** | 接口超时 | AKShare 超过 10s 无响应 | 展示错误提示 + 重试按钮 |
| **Edge** | 无效基金代码 | 用户手动输入错误 code | 展示"基金不存在" + 返回持仓列表引导 |
| **Loading** | 数据加载中 | 首次进入页面 / 刷新 | 骨架屏加载态 |
| **Limit** | 限流/并发 | 短时间内多次请求 | 后端返回 429 → 前端展示"请求过于频繁" |

### 4.2 各场景 UI 规范

| 状态 | UI 表现 | 用户操作 |
|------|---------|----------|
| 加载态 | 基础概况卡片骨架屏 + 表格 3 行骨架 + 进度条骨架 | 等待 |
| 空态 | "暂无持仓数据" 或 "该基金数据尚未披露" 文本 | 返回持仓列表 |
| 错误态 | 错误信息 + 蓝色重试按钮 | 点击重试或返回 |
| 理想态 | 完整展示所有数据区域 | 浏览数据 |

---

## 5. 原型验证

原型由 ace-designer 生成，位于 `planning/v1/fund-detail_prototype.html`，包含 4 种状态视图：
- 理想态：完整数据展示
- 加载态：骨架屏
- 空态：暂无数据提示
- 错误态：错误信息 + 重试

验收标准：前端实现与原型图视觉一致。

---

## 6. 变更范围总结

| 层级 | 文件 | 变更类型 |
|------|------|----------|
| Backend | `app/services/fund_service.py` (新) | 新增 |
| Backend | `app/routers/fund.py` (新) | 新增 |
| Backend | `app/api/portfolio.py` (或类似路径) | 修改：新增 fund 路由注册 |
| Frontend | `frontend/src/api/fund.ts` (新) | 新增 |
| Frontend | `frontend/src/views/FundDetail/index.vue` (新) | 新增 |
| Frontend | `frontend/src/router/index.ts` | 修改：新增 fund 路由 |
| Frontend | `frontend/src/views/PaperTrading/index.vue` | 修改：基金代码跳转路径 |
