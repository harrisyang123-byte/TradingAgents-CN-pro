# TradingAgents-CN — 多智能体 A股/港股 金融投研系统

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Vue 3](https://img.shields.io/badge/Vue-3.5%2B-4FC08D.svg)](https://vuejs.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.4%2B-1C3C3C.svg)](https://langchain-ai.github.io/langgraph/)

面向中国 A股/港股用户的 **多智能体投资投研系统**。基于 LangGraph 工作流编排 + Claude Code Workflow 子 Agent 辩论架构，从宏观行业配置到个股配仓、风控检查全覆盖。

---

## 概览

本系统的核心是一个**分层辩论式投资决策引擎**。投资决策从**宏观到微观**逐层展开，每层都有多角度辩论，最终输出可直接执行的组合调整方案。

```
宏观 → 行业 → 公司 → 组合 → 配仓 → 风控 → 合成
```

---

## 架构

### 核心流程

```
【常态化后台】
├── 数据层（实时）：市场情绪/PE分位/持仓
├── 景气打分引擎：5类信号自动扫描18大行业
└── Tier1 研究库：行业判Go后自动触发公司研究，7天缓存

【主流程】
Step 0: 宏观裁判 → risk-on/off + 总仓位上限
Step 1: 行业研究员×N（并行）→ go_nogo + 景气强度
Step 2: 公司层 — 候选标的筛选 + 横向比较
Step 3: 组合层 — 现有持仓诊断
Step 4: 行业PM×N（并行）→ 激进行保守辩论 → per-stock 配仓
Step 5: 风控规则引擎 → 事前硬拦截（非LLM）
Step 6: Risk Director → 悲观vs乐观压力测试
Step 7: Portfolio Synthesizer → 约束验证 + 缺口处理 + 最终处方
```

### 决策层职责

| 角色 | 职责 | 实现方式 |
|------|------|---------|
| **行业研究员** ×N | B+C 数据注入, 研究员↔反向者辩论, 输出 go_nogo+景气强度 | LangGraph + LLM |
| **跨行业裁判** | 在 total_weight_limit 内做资源分配, 输出各行业 final_weight | LangGraph + LLM |
| **行业PM** ×N | 激进PM↔保守PM, 在配额内配仓, 输出 target_weight+买入区间 | Workflow 子Agent |
| **风控引擎** | 四项硬约束(单股/行业/总仓位/现金), 非LLM | Python 规则引擎 |
| **Risk Director** | 悲观↔乐观辩论, 整体组合压力测试 | Workflow 子Agent |
| **Portfolio Synthesizer** | 验证约束链, 处理缺口, 汇总 industry_matrix | Workflow 子Agent |
| **宏观裁判** | 宏观信号判断, 输出 total_weight_limit | LangGraph + LLM |

### 数据流：约束传递链

```
宏观裁判 → total_weight_limit, cash_floor
  ↓ 硬约束
跨行业裁判 → 在限额内分配 final_weight（加总 = total_weight_limit）
  ↓ 硬约束
行业PM → 在配额内分配 target_weight（加总 ≤ final_weight）
  ↓ 硬约束
风控规则引擎 → 检查违规，打回或通过
  ↓
Risk Director → 压力测试（建议性，不强制）
  ↓
Portfolio Synthesizer → 验证约束链 + 输出最终处方
```

---

## 技术栈

| 组件 | 技术 |
|------|------|
| **后端框架** | FastAPI + Uvicorn |
| **前端** | Vue 3 + Vite + Element Plus |
| **数据库** | MongoDB + Redis |
| **工作流编排** | LangGraph (时序) + Workflow `agent()` (子Agent驱动) |
| **AI Agent** | 子Agent：`.md` 定义 + 结构化 JSON Schema |
| **数据源** | AKShare, Tushare, BaoStock |
| **市场** | A股、港股、美股 |

---

## Agent 类型与调用模式

本系统有两种 Agent 调用模式，按场景选择：

**模式1: LangGraph 节点**（时序依赖强，确定性流程）
- 用于：宏观裁判、行业研究员、L2 Scout 等有严格上下游顺序的步骤
- 实现：`tradingagents/graph/advisor_graph.py` 定义节点 + 边
- 数据通过 `AdvisorState` 传递

**模式2: Workflow 子 Agent**（独立判断，可并行）
- 用于：行业PM辩论、风险双角色辩论、Portfolio Synthesizer
- 实现：`agents/advisor/{name}.md` 定义 prompt + schema → `scripts/workflow-*.js` 编排
- 数据通过 JSON 文件在步骤间传递

---

## 项目结构

```
├── app/                        # FastAPI 后端
│   ├── routers/                # API 路由
│   │   ├── paper.py            # 持仓/概览 API
│   │   ├── portfolio_analysis.py  # 组合分析两阶段 API
│   │   └── watchlist.py        # 行业关注列表 API
│   └── services/               # 业务服务
│       ├── industry_vitality.py    # 景气打分引擎
│       ├── industry_scan_pool.py   # 行业扫描池
│       ├── industry_classifier.py  # 行业分类（AKShare+关键词）
│       ├── stock_research_cache.py # Tier1 研究库
│       └── market_signals.py       # 市场温度计
├── agents/                     # Agent 定义（子Agent模式）
│   ├── advisor/v3-pm-aggressive.md    # 激进PM
│   ├── advisor/v3-pm-conservative.md  # 保守PM
│   ├── advisor/v3-pm-judge.md         # PM裁判
│   ├── advisor/v3-risk-pessimist.md   # 悲观风控
│   ├── advisor/v3-risk-optimist.md    # 乐观风控
│   ├── advisor/v3-risk-judge.md       # 风控裁判
│   └── advisor/v3-portfolio-synthesizer.md # 组合合成器
├── tradingagents/              # 核心框架
│   ├── graph/advisor_graph.py  # 组合顾问 LangGraph
│   └── agents/advisors/        # Agent 逻辑
├── scripts/                    # 工作流脚本
│   ├── workflow-v3-pm-debate.js    # 行业PM辩论
│   └── workflow-v3-synthesizer.js  # 风控+合成
├── frontend/                   # Vue 3 前端
└── openspec/                   # 变更记录与规格
```

---

## 关键特性

### 行业层
- **景气打分**：5类信号（资金流向/北向/PE分位/PMI-PPI/政策文件）加权打分，自动识别值得研究的行业
- **并行研究员**：每行业独立分析，B+C三层数据（LLM知识+AKShare硬数据+新闻研报），研究员↔反向者辩论
- **7天缓存**：行业结论缓存复用，手动强制刷新

### 配仓层
- **并行PM辩论**：每个行业独立 spawn 激进PM↔保守PM，三维度辩论（集中度/配额使用率/建仓时机）
- **买入区间双重验证**：Tier1估值区间 ∩ PE历史分位区间，取保守值
- **分批建仓计划**：支持立即/分批/条件触发三种策略

### 风控
- **事前硬拦截**：规则引擎（非LLM）检查四项约束，违规打回PM重做
- **双角色压力测试**：悲观↔乐观辩论，输出最坏情景回撤
- **缺口自动侦察**：配额有但PM未填满的差额 > 3% 触发补充研究

### 前端
- 行业覆盖矩阵：景气强度/配额缺口/入池来源可视化
- 处方详情：买入区间/建仓策略/分批计划/Tier1评级/PE分位

---

## 开发

```bash
# 启动后端
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 启动前端
cd frontend && npm run dev

# 运行组合分析
# 通过前端 "持仓分析" 页面触发，或调用 API
curl -X POST /api/portfolio/advice

# 运行 PM 辩论（子Agent模式）
claude -p "Run workflow with args {dataDir: '/path/to/data'}"

# 运行风控+合成
claude -p "Run workflow with args {dataDir: '/path/to/data'}"
```

更多命令请查看 [CLAUDE.md](./CLAUDE.md)。

---

## 前置知识

本系统的架构决策和实现细节记录在以下知识库文档中：

- [行业层重构](docs/wiki/industry-layer-rebuild.md) — 并行行业研究员+景气打分+7天缓存+Tier1自动触发
- [决策层重构](docs/wiki/decision-layer-rebuild.md) — 并行行业PM+子Agent风控+Risk Director双角色+Portfolio Synthesizer
- [组合顾问引擎](docs/wiki/portfolio-advisor-engine.md) — 辩论架构与结构化处方

---

## License

Apache 2.0
