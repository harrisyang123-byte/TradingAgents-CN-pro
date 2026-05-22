# TradingAgents-CN

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![Version](https://img.shields.io/badge/Version-v1.0.1-green.svg)](./VERSION)
[![Original](https://img.shields.io/badge/基于-TauricResearch/TradingAgents-orange.svg)](https://github.com/TauricResearch/TradingAgents)

面向中文用户的多智能体 A股/港股/美股 金融分析系统，基于 [TradingAgents](https://github.com/TauricResearch/TradingAgents) 构建。

- 📦 **本项目**：https://github.com/harrisyang123-byte/TradingAgents-CN-pro
- 🔗 **原项目**：https://github.com/TauricResearch/TradingAgents

---

## 功能特性

- **多智能体分析**：多角色 LLM 协作（市场分析师、基本面分析师、情绪分析师、风险管理师），辩论式决策
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
tradingagents/   # 核心多智能体框架（Agent / Graph / LLM 管线）
app/             # FastAPI 后端
frontend/        # Vue 3 前端
cli/             # 命令行工具
docs/            # 文档
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
