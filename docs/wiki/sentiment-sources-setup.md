# 情绪数据源设置指南

## 概述

系统通过注册式框架 `tradingagents/agents/analysts/sources/` 接入多个中文情绪源。
默认启用 `["eastmoney", "wechat_mp"]`，通过配置 `sentiment_sources` 控制。

## 源列表

### eastmoney（东方财富）— ✅ 可用

- 文件: `sources/eastmoney.py`
- 方式: 通过 akshare 库获取 A 股新闻
- 限制: 仅支持 A 股（.SZ/.SS/.SH 后缀），港股自动跳过
- 依赖: `pip install akshare`（CN fork 已有）
- 启动: 零配置，开箱即用

### wechat_mp（微信公众号）— ⚠️ 需外部服务

- 文件: `sources/wechat_mp.py`
- 方式: 通过 we-mp-rss HTTP 服务搜索公众号文章
- 端点:
  - `GET /api/v1/articles/search?q={ticker}&limit=10`
  - `POST /api/v1/query` (回退) `{"query": "{ticker}", "limit": 10}`
- 配置: `wechat_mp_base_url`（默认 `http://localhost:8001`）
- 状态: **框架已集成，但 we-mp-rss 服务需自行搭建**
  - 该服务不在本仓库中
  - 需要部署一个能够抓取/检索微信公众号文章的 HTTP 服务
  - 接口协议见上，响应格式: `[{title, summary, url, pub_time}]` 或 `{articles: [...]}`

## 添加新源

1. 在 `sources/` 下新建文件
2. 实现 `BaseSentimentSource`，用 `@register("源名称")` 装饰
3. 在 `default_config.py` 的 `sentiment_sources` 默认列表追加名称

## 配置参考

```python
# default_config.py 相关字段
"sentiment_sources": ["eastmoney", "wechat_mp"],  # 启用哪些源
"wechat_mp_base_url": "http://localhost:8001",      # we-mp-rss 服务地址
```
