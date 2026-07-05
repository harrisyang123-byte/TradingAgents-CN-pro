# sentiment-intel 数据目录

## 结构

```
data/v4/sentiment-intel/
  {YYYY-MM-DD}/
    intel-data.json      # Data Agent 取数产物
    intel-report.json    # Inference Agent 推演产物
    intel-report.html    # 可视化报告
```

## intel-data.json Schema

由 Data Agent 产出。顶层 6 维度 + data_availability + acquisition_audit：

- `as_of`: ISO8601 数据时间戳
- `data_availability`: {维名: "available"|"partial"|"unavailable"}
- `market_temp`: 全市场涨跌比/涨停数/跌停数/成交额vs5日均量
- `sector_heat`: 行业涨跌TOP10/资金净流入TOP10
- `concept_themes`: 热门概念/涨停板行业分布/连板高度
- `kol_feed`: X KOL 最新推文(方向共识/分歧/催化事件)
- `a_share_popularity`: 雪球最热讨论/东财人气榜
- `cross_market`: 美股/大宗/VIX/汇率
- `acquisition_audit`: 取数审计(fetch_tasks/downgrade/missing)

## intel-report.json Schema

由 Inference Agent 产出：

- `as_of`: 报告时间戳
- `sentiment_index`: 综合情绪温度 0-100
- `dominant_narrative`: 今日主导叙事
- `heat_map`: [{theme, score, trend, signal}]
- `signal_list`: [{direction, content, source, strength}]
- `divergence_matrix`: [{theme, global_signal, cn_signal, type, inference}]
- `transmission_chain`: [{chain_name, steps[{num, title, desc}]}]
- `catalyst_calendar`: [{date, event, impact}]
- `scenarios`: [{name, probability, body, trigger}]
- `implications`: [{title, body}]
- `data_quality`: 各维可用性评估

## 数据可用性标记

每个取数维度必标：
- `available`: 成功取到 ≥80% 字段
- `partial`: 成功取到 30-80%
- `unavailable`: <30% 或完全失败

诚实地降级，不编造。
