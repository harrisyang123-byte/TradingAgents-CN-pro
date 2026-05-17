## Why

情绪分析师已切换为 pre-fetch 模式（sentiment-analyst-redesign），但数据源不足：

1. **eastmoney 源名不副实** — 实际调的是 `akshare.stock_info_ths_zjlx`（同花顺资金流向），属于市场微观结构数据而非情绪数据
2. **wechat_mp** 需要外部 Docker 服务，不一定可用
3. 缺少对标 upstream StockTwits（散户多空比）和 Reddit（社区讨论）的中文替代源

akshare 提供了丰富的 A 股情绪数据接口：
- `stock_comment_em()` — 千股千评：综合得分、关注指数、机构参与度
- `stock_comment_detail_scrd_desire_em(symbol)` — 散户参与意愿时序
- `stock_comment_detail_zhpj_lspf_em(symbol)` — 综合评价历史评分

## What Changes

**新增**

- `tradingagents/agents/analysts/sources/eastmoney_comment.py` — 基于千股千评 + 参与意愿 + 历史评分的情绪数据源，注册为 `eastmoney_comment`。对标 upstream StockTwits 的角色（量化散户情绪）

**修改**

- `tradingagents/agents/analysts/sources/eastmoney.py` — 修正数据获取：从资金流向（`stock_info_ths_zjlx`）改为东方财富个股新闻（`stock_individual_info_em` 或保留现有接口但修正说明）

**不动**

- `sources/__init__.py` — auto-discover 已实现，新文件自动注册
- `sentiment_analyst.py` — 无需修改，自动加载新源
- `wechat_mp.py` — 保持不变
- `graph/` — 无需修改

## Impact

- 新增 1 个源文件，修改 1 个源文件
- A 股情绪分析从"资金流向占位符"升级为"千股千评 + 散户参与意愿 + 历史评分"
- 图结构、LLM 管线完全不受影响

**复杂度**: 简单
