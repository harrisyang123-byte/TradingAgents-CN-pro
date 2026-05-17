## 1. 新增千股千评情绪源

- [x] 1.1 新增 `tradingagents/agents/analysts/sources/eastmoney_comment.py` — 实现 `EastMoneyCommentSource`，通过 akshare 获取：千股千评综合得分 + 散户参与意愿 + 历史评分。`@register("eastmoney_comment")`

## 2. 修正现有 eastmoney 源

- [x] 2.1 修改 `tradingagents/agents/analysts/sources/eastmoney.py` — 从已废弃的 `stock_info_ths_zjlx`（资金流向）改为 `stock_hot_keyword_em`（个股热搜概念）

## 3. 配置更新

- [x] 3.1 更新 `tradingagents/default_config.py` — `sentiment_sources` 默认值增加 `eastmoney_comment`

## 4. 验证

- [x] 4.1 确认新源可正常 import 并注册到 REGISTRY（eastmoney + eastmoney_comment + wechat_mp）
- [x] 4.2 确认新源 fetch 返回真实数据（600519.SH: eastmoney 8 items, eastmoney_comment 3 items）
