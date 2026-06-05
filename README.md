# TradingAgents-CN — 多智能体 A股/港股 金融投研系统

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Vue 3](https://img.shields.io/badge/Vue-3.5%2B-4FC08D.svg)](https://vuejs.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.4%2B-1C3C3C.svg)](https://langchain-ai.github.io/langgraph/)
[![Claude Code](https://img.shields.io/badge/Claude_Code-Workflow-orange.svg)](https://claude.ai/code)

面向中国 A股/港股 用户的**多智能体分层辩论式投资系统**。以用户持久盈利为目标，从宏观行业配置到个股配仓、事前风控全覆盖，所有 LLM 决策环节都有对立角色辩论。

---

## 目标

> **让用户持久盈利，而不是跑赢基准。**

系统以绝对收益为目标而非基准超额收益。景气度高+估值合理=配置，景气度低/高估=不配或减配，不和指数挂钩。

---

## 核心架构

投资决策从**宏观到微观**分 7 层展开，每层都有多视角辩论，约束从上到下硬传递。

```
【常态化后台，独立运行】
┌────────────────────────────────────────────────────────┐
│ 数据层      市场情绪 / 北向资金 / PE分位 / 宏观指标       │
│ 景气打分    5类信号自动扫描全量18大行业，每日更新         │
│ Tier1库     行业判Go后自动触发主要公司深度研究，7天缓存   │
└────────────────────────────────────────────────────────┘

【每次组合分析主流程】
Step 0  宏观裁判
        输入：PMI/利率/北向/涨跌比
        输出：risk-on/off + total_weight_limit + cash_floor
           ↓ 硬约束

Step 1  行业研究员 ×N（并行）
        每行业独立：LLM知识 + AKShare硬数据 + 新闻研报
        研究员首发 → 反向者挑战 → 行业内辩论（2轮）
        → 跨行业裁判：在 total_weight_limit 内做资源分配
        输出：go_nogo + vitality_level + final_weight
        缓存：7天有效期，手动可强制刷新
           ↓ 同时触发 Tier1 研究库异步更新

Step 2  公司层（Tier1 驱动）
        Scout 在 Go 行业找候选标的
        读取 Tier1 研究库报告做横向比较
        输出：每行业候选排序 + 评级 + 目标价

Step 3  组合层（与 Step 2 并行）
        持仓分析师 + 策略师 + Scout_L3 并行诊断
        → 组合反向者挑战
        输出：建议减仓/清仓标的 + 敞口风险

Step 4  行业PM ×N（并行，子 Agent 模式）
        每个 Go 行业独立 spawn 激进PM vs 保守PM
        激进：重仓高评级，配额用满，偏 immediate
        保守：分散配置，保留缓冲，偏 batch/conditional
        裁判：综合两者，买入区间取 Tier1 ∩ PE分位保守值
        输出：target_weight + entry_price_range + batch_plan
           ↓ 行业配额约束

Step 5  风控规则引擎（非LLM，事前硬拦截）
        ① 单股 ≤ max_single_weight
        ② 行业合计 ≤ final_weight
        ③ 总仓位 ≤ total_weight_limit
        ④ 现金 ≥ cash_floor
        违规 → 打回对应行业PM重做（最多2次），第3次自动截断

Step 6  Risk Director（子 Agent 模式）
        悲观风险总监 vs 乐观风险分析师（2轮）
        → 风控裁判
        输出：max_drawdown_20pct + 黑天鹅触发条件（建议性）

Step 7  Portfolio Synthesizer（子 Agent 模式）
        验证约束链完整性（不修正，只报警）
        识别行业缺口（gap > 3% 触发补充侦察）
        汇总 industry_matrix + 最终处方
        输出：可直接执行的组合调整方案
```

---

## Agent 列表（12个 v3 子 Agent）

| 层 | Agent 文件 | 职责 |
|----|-----------|------|
| 宏观 | `v3-macro-judge.md` | 宏观信号 → total_weight_limit |
| 行业 | `v3-industry-researcher.md` | B+C三层数据 → 首次判断 |
| 行业 | `v3-industry-contrarian.md` | 挑战研究员，暴露盲点 |
| 跨行业 | `v3-cross-industry-judge.md` | 在限额内分配 final_weight |
| PM | `v3-pm-aggressive.md` | 激进PM：配额用满，重仓高评级 |
| PM | `v3-pm-conservative.md` | 保守PM：保留缓冲，偏分批 |
| PM | `v3-pm-judge.md` | PM裁判：综合两者，取保守买入区间 |
| 风控 | `v3-risk-pessimist.md` | 找最坏情景，挑战集中风险 |
| 风控 | `v3-risk-optimist.md` | 反驳过度保守，指出踏空风险 |
| 风控 | `v3-risk-judge.md` | 综合两者，输出 RiskAssessment |
| 合成 | `v3-portfolio-synthesizer.md` | 验证约束链 + 缺口处理 + 汇总 |

编排脚本（3个 Workflow）：

| Workflow | 覆盖步骤 |
|---------|---------|
| `workflow-v3-industry-layer.js` | Step 0-1：宏观 + 行业研究员并行 + 跨行业裁判 |
| `workflow-v3-pm-debate.js` | Step 4：行业PM并行辩论 |
| `workflow-v3-synthesizer.js` | Step 5-7：风控规则 + Risk Director + Portfolio Synthesizer |

---

## 决策设计原则

**景气度 × 安全边际双因子**：景气度高但估值极端时调节权重，不直接否决（避免错过 AI 等成长赛道）。

**约束从宏观层硬传递**：宏观 → 行业 → PM，每层输出满足上游约束，Portfolio Synthesizer 验证链路完整性。

**辩论驱动质量**：每层都有对立角色，避免单一视角的确认偏误。风控是硬约束，Risk Director 是建议，两者职责分开。

**子 Agent 而非 `llm.invoke()`**：所有 LLM 决策逻辑都通过 `.md` 文件定义 + Workflow `agent()` 调用，不在 Python 中直接调 LLM——实践证明质量更好。

---

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端 | FastAPI 0.115+ + Uvicorn |
| 前端 | Vue 3.5+ + Vite + Element Plus |
| 数据库 | MongoDB + Redis |
| LangGraph | 时序确定性流程（Step 0-3） |
| Workflow 子 Agent | 并行判断性流程（Step 1/4/5-7） |
| 数据源 | AKShare / Tushare / BaoStock |
| 市场覆盖 | A股 / 港股 / 美股 |
| 行业体系 | 18大投资主题（消费/科技/金融/医药等） |

---

## 项目结构

```
tradingagents-cn/
├── agents/advisor/          # 12个 v3 子 Agent .md 定义
├── scripts/
│   ├── workflow-v3-*.js     # 3个 Workflow 编排脚本
│   └── migrate_position_industry.py  # 历史持仓行业补填
├── app/
│   ├── routers/
│   │   ├── paper.py             # 持仓/概览 API
│   │   ├── portfolio_analysis.py  # 组合分析 API
│   │   └── watchlist.py         # 行业关注列表 API
│   └── services/
│       ├── industry_vitality.py    # 景气打分引擎（5类信号）
│       ├── industry_scan_pool.py   # 行业扫描池（持仓+watchlist+景气）
│       ├── industry_classifier.py  # 持仓录入时前置行业分类
│       ├── stock_research_cache.py # Tier1 研究库（7天缓存）
│       └── market_signals.py       # 市场温度计
├── tradingagents/
│   ├── graph/advisor_graph.py  # L0-L3 LangGraph 主图
│   └── agents/advisors/
│       ├── advisor_states.py   # AdvisorState（含v3约束传递字段）
│       └── risk_rules.py       # 事前风控规则引擎（纯Python）
├── frontend/                   # Vue 3 前端
│   └── src/views/Portfolio/
│       └── Overview.vue        # 行业矩阵（含v3新列）
├── docs/wiki/                  # 架构知识库
└── openspec/                   # 变更记录（全部归档）
```

---

## 快速启动

**前置条件**：MongoDB、Redis 已启动。

### 一键分析

```bash
# 1. 配置 .env（只需一次）
echo "ADVISOR_USER_ID=<你的用户ID>" >> .env

# 2. 打开项目，对 Claude Code 说一个字：分析
```

### 手动启动

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000   # 后端
cd frontend && npm run dev                                   # 前端
```

### Workflow 快捷指令

| 对话中说 | 执行 |
|----------|------|
| `分析` | 全链路 L1-L4 组合顾问 |
| `跑行业层` | v3 行业研究员并行 + 反向者 |
| `跑辩论` | v3 PM 辩论 |
| `跑合成` | v3 风控 + 合成器 |

---

## API 说明

| 接口 | 说明 |
|------|------|
| `GET /api/portfolio/overview` | 行业覆盖矩阵（v3有则读 advice.industry_matrix，否则降级拼接） |
| `POST /api/portfolio/positions` | 新增持仓（自动分类行业） |
| `GET /api/watchlist` | 行业关注列表 |
| `POST /api/watchlist` | 添加关注行业 |
| `DELETE /api/watchlist/{industry}` | 删除关注行业 |
| `POST /api/portfolio/analysis/industry/{name}/refresh` | 强制刷新某行业缓存 |

完整 API 文档：`http://localhost:8000/docs`

---

## 知识库

| 文档 | 内容 |
|------|------|
| [行业层重构](docs/wiki/industry-layer-rebuild.md) | 景气打分/并行研究员/7天缓存/Tier1触发 |
| [决策层重构](docs/wiki/decision-layer-rebuild.md) | 并行PM/约束传递链/风控引擎/Portfolio Synthesizer |
| [组合顾问引擎](docs/wiki/portfolio-advisor-engine.md) | LangGraph辩论架构/结构化处方 |
| [认证与部署](docs/wiki/auth-bootstrap.md) | 初始 admin 创建/首次部署 |

---

## 风险提示

本系统仅用于辅助投资研究，不构成投资建议。AI 判断存在不确定性，投资有风险，决策需谨慎。

---

## License

Apache 2.0
