# design.md — 市场舆情情报推演 Agent 技术方案

## 架构概览

```
用户触发 "/sentiment-intel"
       │
       ▼
  ┌─────────────────────┐
  │  Data Agent          │  ← 联网取数，6 维并行
  │  (scripts/sentiment- │
  │   intel/data-agent)  │
  └────────┬────────────┘
           │ intel-data.json
           ▼
  ┌─────────────────────┐
  │  Inference Agent     │  ← 分叉检测 + 传导链 + 情景推演
  │  (agents/sentiment-  │
  │   intel/inference)   │
  └────────┬────────────┘
           │ intel-report.json + intel-report.html
           ▼
      用户浏览器打开 HTML
```

## 目录结构

```
scripts/sentiment-intel/
  data-agent.md          # 取数 agent 定义 (含 tools + prompt)
  fetch-intel.py         # 取数脚本（可选，包装 market_tools + akshare 调用）

agents/sentiment-intel/
  inference-agent.md     # 推演 agent 定义 (Read-only + 报告生成)

data/v4/sentiment-intel/
  {YYYY-MM-DD}/
    intel-data.json      # 取数产物
    intel-report.json    # 推演产物
    intel-report.html    # 可视化报告

reports/
  sentiment-intel-{YYYYMMDD}.html  # 用户可见的最终报告副本
```

## Data Agent — 6 维取数

### 输入
无（联网实时获取）

### 取数维度与来源

| # | 维度 | 具体数据 | 来源 |
|---|------|---------|------|
| 1 | 市场情绪温度 | 全市场上涨/下跌家数、涨停/跌停数、成交额 vs 5日均量 | `stock_zh_a_spot()` / 新浪行情 |
| 2 | 板块热度 | 行业涨跌幅 TOP10、资金净流入 TOP10 | `get_industry_rankings("cn")` + `get_sector_fund_flows("cn")` |
| 3 | 概念/题材 | 当日热门概念、涨停板行业分布、连板高度 | `stock_board_concept_name_ths()` + web_search |
| 4 | X KOL 舆情 | 最新推文（方向共识/分歧/催化事件/发现度温度） | `scrape-custom-x.py` → `custom-feed-x.json` |
| 5 | A 股人气 | 雪球最热讨论 TOP10、东财人气榜、千股千评热点 | `stock_hot_tweet_xq()` + `stock_hot_keyword_em()` + web_search |
| 6 | 跨市场锚点 | 美股前日收盘（纳指/费半/SOX）、大宗（原油/铜/金）、VIX、汇率 | `get_macro_indicators("us")` |

### 降级策略
- X feed 抓取失败 → 维度 4 标 missing，报告诚实标注
- akshare 函数不可用 → 按 WebFetch 降级链
- 单个维度缺失不阻断其余维度

### 输出：`intel-data.json`
```json
{
  "as_of": "2026-06-25T09:00:00+08",
  "data_availability": {
    "market_temp": "available",
    "sector_heat": "available",
    "concept_themes": "available",
    "kol_feed": "available",
    "a_share_popularity": "partial",
    "cross_market": "available"
  },
  "market_temp": { ... },
  "sector_heat": { ... },
  "concept_themes": { ... },
  "kol_feed": { ... },
  "a_share_popularity": { ... },
  "cross_market": { ... }
}
```

## Inference Agent — 推演引擎

### 输入
读取 `data/v4/sentiment-intel/{date}/intel-data.json`

### 三层推演框架

#### 层 1：现状 · 当日快照
- 市场情绪温度（0-100 合成指数）
- 今日主导叙事（1-2 句话）
- 板块热力地图（8-10 主题，升温/平温/降温）
- 多空信号汇总（按来源标注）

#### 层 2：近期 · 1-2 周催化日历
- X KOL 提到的具体事件窗口
- A 股题材轮动节奏预判
- 关键数据发布时间点

#### 层 3：未来 · 1 月方向判断
- 跨市场信号分叉检测（境内外同一产业链信号方向是否一致）
- 事件传导链推演（A → B → C 因果链）
- 情景概率（基准/乐观/悲观，各附概率 + 触发信号）
- 衍生推论（数据没直接说但可合理推断的结论）

### 输出

#### `intel-report.json`
结构化 JSON，字段包含：
- `sentiment_index`：综合情绪温度 0-100
- `dominant_narrative`：今日主导叙事
- `heat_map`：[{theme, score, trend, signal}]
- `signal_list`：[{direction, content, source, strength}]
- `divergence_matrix`：[{theme, global_signal, cn_signal, type, inference}]
- `transmission_chain`：[{chain_name, steps}]
- `catalyst_calendar`：[{date, event, impact}]
- `scenarios`：[{name, probability, body, trigger}]
- `implications`：[{title, body}]
- `data_quality`：各维数据可用性评估

#### `intel-report.html`
自包含 HTML 文件，暗色主题，包含：
- 情绪温度条
- 关键数值卡片
- 板块热度雷达
- 关键事件时间线
- 多空信号列表
- 传导链推演
- 全球 vs A 股分叉矩阵
- 情景概率
- 衍生推论
- 数据源质量评估

## 执行流程

```
1. 用户输入 "/sentiment-intel"（或自然语言"出个舆情推演报告"）
2. 主 agent 调用 Data Agent（联网取数 6 维并行）
3. Data Agent 输出 intel-data.json 落盘
4. 主 agent 调用 Inference Agent（Read intel-data.json）
5. Inference Agent 输出 intel-report.json + intel-report.html
6. 主 agent 用 open 命令打开 HTML
```

## 与 v4 的关系

- **互补非重叠**：v4 辩论体系输出投资决策（买什么/配多少），sentiment-intel 输出市场认知（市场在想什么/信号怎么传）
- **独立部署**：不被 v4 编排器调用，不消费 v4 行业分析包
- **共享基础设施**：复用 `market_tools`、`scrape-custom-x.py`、akshare 数据源
