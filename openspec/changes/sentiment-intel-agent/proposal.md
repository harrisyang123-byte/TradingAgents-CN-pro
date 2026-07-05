# sentiment-intel-agent — 市场舆情情报推演 Agent

## Why

v4 投研体系有完整的宏观分析（`v4-asset-analyst-macro`）、个股舆情（`v4-stock-analyst-sentiment`）、行业舆情（`v4-industry-sentiment`），但缺少一个**市场级、跨源融合、非结构化信号推演**的能力。三个缺口：

1. **能取数但不会讲故事**：`get_industry_rankings()` 能拿行业涨跌，`scrape-custom-x.py` 能抓 X feed，但没人把"韩股存储熔断 -12%"和"A 股 DRAM 链涨停 +8%"放在一起说"这两个市场在互搏，分叉终将收敛"。
2. **有辩论但没有情报产品**：v4 的 50+ agent 做的是投资决策（买什么/配多少），产出的都是 JSON 字段给 director 裁决。没有一个 agent 的职责是"让用户看清今天市场在发生什么、信号怎么传导"。
3. **用户需要独立的认知入口**：不做投资建议，只做"多路信号融合 → 分叉检测 → 传导链推演 → 情景概率"，帮用户建立自己的判断框架。

## What

一个独立于 v4 辩论体系的**市场舆情情报推演 agent**，按需触发。

**核心能力**：
- 三路数据（X KOL 舆情、东财/雪球 A 股人气、跨市场行情）一次取数
- 跨源分叉检测（境内外同一产业链信号方向是否一致）
- 事件传导链推演（MU 财报 → CoWoS 需求 → 封装涨停）
- 三层时间视野（当日快照 / 1-2 周催化日历 / 1 月方向判断）
- HTML 可视化报告 + JSON 结构化落盘

## Design Decisions (Grill 产出)

| 维度 | 决定 |
|------|------|
| 触发方式 | 按需 |
| 取数方式 | 联网获取，复用 `market_tools` + X scraper + akshare |
| 分析范围 | 纯市场级 |
| 分析深度 | 推演型（分叉/传导链/情景） |
| 时间视野 | 当日 + 1-2 周催化 + 1 月方向 |
| 输出格式 | JSON + HTML 双写 |
| 内部结构 | 流水线（取数 agent → 推演 agent） |
| 取数维度 | 6 维（情绪温度/板块热度/概念题材/KOL舆情/A股人气/跨市场锚点） |
| 部署位置 | `scripts/sentiment-intel/` + `agents/sentiment-intel/`，独立于 v4 |

## Non-Goals

- 不做个股分析、不出持仓建议
- 不接入 v4 辩论编排器
- 不消费 v4 行业分析 JSON（保持独立闭环）

<!-- Dialectical Analysis -->

### 方案对比

**方案 A（保守）— 复用 v4-data-desk + v4-industry-sentiment**：在现有 agent 上加"多源融合" prompt，不建新 agent。
- 优点：零新增文件，复用 acquisition_audit 审计链
- 缺点：v4 agent 设计目标是"输出 JSON 给 director 辩论"，推演型报告的思维模式与之冲突。硬塞会把两边都搞乱。
- **否决**：职责冲突，不可行。

**方案 B（创新）— 独立 agent + 独立目录**：新建 `agents/sentiment-intel/`，跟 v4 同级但不隶属。
- 优点：边界清晰，不污染 v4 辩论体系；可独立迭代；未来可加定时调度
- 缺点：新增 agent 定义文件 + 取数脚本 + 输出目录
- **采用**

### 风险对冲

- **最大风险**：X feed 抓取失败（API 限流/账号被封），导致 KOL 舆情腿缺失。预案：降级为"两路数据报告"，在报告中诚实标注缺失。
- **次级风险**：akshare 函数变更导致取数断裂。预案：取数 agent 输出 `data_availability` 字段，推演 agent 遇到 missing 降级处理。
