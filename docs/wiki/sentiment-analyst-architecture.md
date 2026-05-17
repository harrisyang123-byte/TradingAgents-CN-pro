# 情绪分析师架构

> 从 tool-calling 重构为 pre-fetch 模式，解决 A 股/港股情绪数据空转问题。

## 设计动机

旧架构存在两套互不连通的系统：
1. **pre-fetch 框架** — 有真实中文数据源但输出 `sentiment_context` 无人读取
2. **tool-calling 分析师** — 在图中运行但 `get_stock_sentiment_unified` 对 CN/HK 返回占位符

LLM 被 prompt 要求分析社交媒体情绪，但唯一的工具返回占位符 → 被迫编造数据。TG upstream 已验证此问题并切换到 pre-fetch 模式。

## 当前架构

```
Source Registry (eastmoney / wechat_mp / ...)
    ↓ async fetch (per source, 10s timeout)
_fetch_all() → SentimentReport
    ↓
_format_source_blocks() → XML 分隔文本块
    ↓
_build_system_message() → 中文分析指令 + 数据块
    ↓
prompt | llm （单次调用，无 bind_tools）
    ↓
sentiment_report: str → AgentState
```

## 数据源 Registry

| 源 | 文件 | 机制 | 数据内容 | 覆盖 |
|----|------|------|----------|------|
| eastmoney | `sources/eastmoney.py` | akshare `stock_hot_keyword_em` | 个股热搜概念和热度 | A 股 |
| eastmoney_comment | `sources/eastmoney_comment.py` | akshare 千股千评系列 | 综合得分、散户参与意愿、历史评分 | A 股 |
| wechat_mp | `sources/wechat_mp.py` | we-mp-rss Docker HTTP | 微信公众号文章 | 全市场 |

新增数据源只需在 `sources/` 目录下创建文件，实现 `BaseSentimentSource` 并加 `@register("name")` 装饰器。`__init__.py` 的 auto-discover 会自动导入。

## 图接线

```
Social Analyst → Msg Clear Social → (下一个分析师或 Bull Researcher)
```

直通边，无 ToolNode 循环。其他三个分析师（market/news/fundamentals）保持 tool-calling 模式不变。

## 与 upstream 的对比

| 维度 | TG upstream | TG-CN |
|------|------------|-------|
| 数据源 | Yahoo Finance + StockTwits + Reddit | eastmoney + wechat_mp |
| 注入格式 | XML 标签分隔 | XML 标签分隔（相同） |
| LLM 调用 | 单次，无 tool-calling | 单次，无 tool-calling（相同） |
| prompt 语言 | 英文 | 中文 |
| 异步处理 | 直接 sync 调用 | `_run_async` 兼容 FastAPI event loop |
