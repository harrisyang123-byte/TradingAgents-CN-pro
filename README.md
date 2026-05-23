# TradingAgents-CN

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![Version](https://img.shields.io/badge/Version-v1.0.1-green.svg)](./VERSION)
[![Original](https://img.shields.io/badge/基于-TauricResearch/TradingAgents-orange.svg)](https://github.com/TauricResearch/TradingAgents)

面向中文用户的多智能体 A股/港股/美股/基金 金融分析系统，基于 [TradingAgents](https://github.com/TauricResearch/TradingAgents) 构建。

- 📦 **本项目**：https://github.com/harrisyang123-byte/TradingAgents-CN-pro
- 🔗 **原项目**：https://github.com/TauricResearch/TradingAgents

---

## 系统架构：多智能体协作网络

系统由 **26 个 LangGraph Agent 节点**（19 种去重概念角色）组成，分布在三条独立流水线中，通过辩论式决策机制协作产出交易建议。

### 股票分析流水线（12 Agent）

```
输入股票代码
  │
  ├─ 阶段1 · 分析师团队（顺序执行，可选配）
  │   ├── 📈 市场分析师    → 行情数据 / 技术指标
  │   ├── 💬 社媒分析师    → 社交舆情 / 投资者心理
  │   ├── 📰 新闻分析师    → 新闻公告 / 内部交易
  │   └── 💰 基本面分析师  → 财报 / 资产负债 / 现金流
  │
  ├─ 阶段2 · 投资多空辩论
  │   ├── 🐂 多头研究员 ──┐
  │   ├── 🐻 空头研究员 ──┤ 交替辩论（默认 2 回合）
  │   └── 🔬 研究经理   ──┘ 综合裁决
  │
  ├─ 阶段3 · 交易计划
  │   └── 💼 交易员 → 输出投资计划
  │
  ├─ 阶段4 · 风控三方辩论
  │   ├── ⚡ 激进风控 ──┐
  │   ├── 🛡️ 保守风控 ──┤ 轮转辩论（默认 3 回合）
  │   ├── ⚖️ 中性风控 ──┤
  │   └── 👔 组合经理   ──┘ 最终裁决
  │
  └── 输出: action · target_price · confidence · risk_score
```

### 基金分析流水线（10 Agent）

```
输入基金代码
  │
  ├─ 阶段1 · 基金经理分析师团队
  │   ├── 🧑‍💼 基金经理分析师  → 履历 / 历史业绩 / 投资风格
  │   ├── 📦 持仓分析师      → 资产配置 / 重仓股 / 行业分布
  │   └── ⚠️ 风险分析师      → 回撤 / 波动率 / 尾部风险
  │
  ├─ 阶段2 · 基金投资多空辩论
  │   ├── 🐂 基金多头 ──┐
  │   ├── 🐻 基金空头 ──┤ 交替辩论
  │   └── 🔬 基金研究总监 ──┘ 综合裁决
  │
  ├─ 阶段3 · 基金风控辩论
  │   ├── ⚡ 基金激进风控 ──┐
  │   ├── 🛡️ 基金保守风控 ──┤ 三方轮转辩论
  │   ├── ⚖️ 基金中性风控 ──┤
  │   └── 🎯 基金组合经理   ──┘ 最终裁决
  │
  └── 输出
```

### 组合顾问引擎（4 Agent，Tier 2）

基于已有分析报告，对用户持仓组合做整体评估：

| Agent | 角色 | 职责 |
|---|---|---|
| 📊 持仓分析师 | Portfolio Analyst | 评估现有持仓质量 |
| 🎯 策略师 | Strategist | 战略性配置视角 |
| 🔭 侦察兵 | Scout | 扫描新机会和风险 |
| 👨‍⚖️ CIO | Chief Investment Officer | 最终裁决和处方建议 |

### 辩论机制

| | 投资多空辩论 | 风控辩论 |
|---|---|---|
| 参与方 | 多头 ↔ 空头（交替） | 激进 → 保守 → 中性（轮转） |
| 每轮回合 | 2（bull → bear） | 3（agg → con → neu） |
| 裁判 | 研究经理（深度 LLM） | 组合经理（深度 LLM） |
| 决策产出 | trader_investment_plan | final_trade_decision |

---

## 功能特性

- **多智能体分析**：26 个 Agent 节点，19 种角色，辩论式决策，覆盖股票 + 基金 + 组合
- **全资产支持**：A股、港股、美股、场外基金、ETF
- **持仓管理**：多资产类型持仓录入、汇率折算、组合顾问引擎
- **基金详情**：AKShare 穿透数据、净值历史、重仓股分析
- **多 LLM 支持**：OpenAI、DeepSeek、阿里百炼、Google Gemini、xAI Grok 等
- **数据源**：AKShare、Tushare、BaoStock、Finnhub
- **报告导出**：Markdown / Word / PDF

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.12 + FastAPI + Uvicorn |
| 前端 | Vue 3 + Element Plus + Vite |
| 数据库 | MongoDB + Redis |
| Agent 框架 | LangGraph + 自研 Agent 节点 |
| LLM | DeepSeek（默认） / OpenAI / 阿里百炼 / Gemini |
| 部署 | Docker Compose |

## 快速启动

```bash
# 1. 复制并填写配置
cp .env.example .env
# 编辑 .env，填入 LLM API Key

# 2. 一键启动（自动启动 MongoDB/Redis + 后端 + 前端）
bash start.sh

# 停止
bash stop.sh

# 查看状态
bash status.sh
```

访问 http://localhost:3000

## 配置

复制 `.env.example` 为 `.env`，至少配置一个 LLM 提供商：

```bash
# DeepSeek（推荐，性价比高）
DEEPSEEK_API_KEY=your_key

# 或 OpenAI
OPENAI_API_KEY=your_key
```

数据源（可选，不配置则使用 AKShare 免费数据）：
```bash
TUSHARE_TOKEN=your_token
FINNHUB_API_KEY=your_key
```

## 项目结构

```
tradingagents/        # 核心多智能体框架
  agents/             # 19 种 Agent 角色实现
  graph/              # 3 条 LangGraph 流水线（股票/基金/组合顾问）
app/                  # FastAPI 后端
frontend/             # Vue 3 前端
cli/                  # 命令行工具
docs/wiki/            # 领域知识库
```

## 版本历史

- **v1.0.1**：配置管理优化、AiHubMix 聚合厂家、持仓管理、基金详情页
- **v1.0.0-preview**：FastAPI + Vue 3 新架构
- **v0.1.x**：Streamlit 版本（已停止维护）

## 许可证

- `tradingagents/`、`cli/`、`docs/` 等：[Apache 2.0](./LICENSE)
- `app/`、`frontend/`：专有许可，个人学习免费，商业使用需授权（联系 hsliup@163.com）

## 致谢

感谢 [Tauric Research](https://github.com/TauricResearch) 团队的原始框架 [TradingAgents](https://github.com/TauricResearch/TradingAgents)。

---

⚠️ **风险提示**：本项目仅用于研究和学习，不构成投资建议。
