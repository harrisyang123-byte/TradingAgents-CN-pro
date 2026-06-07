## Why

逐单元跑通 v4 后，对照 [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) 真实 prompt 暴露三处缺口：

1. **大类辩论在前端不可见（展示缺口，非数据缺口）**：`asset:<class>` 信封 `payload` 早已存了完整的 `debate_rounds`（多空 3 轮）与 `analysts`（macro/flow/policy），但 `build_asset_detail` 只吐 `verdict/tradable/industries/plan`，把辩论丢弃；`AssetDetailTab.vue` 也无渲染区。用户在大类详情页看不到任何辩论过程——而行业层（`build_industry_detail` + `IndustryDetailTab.vue`）早已有现成的辩论折叠块。
2. **无结果闭环记忆**：现有 `archive_v4.py` 只做到「存版本 + diff」，但**没有任何 Agent 消费历史**。重跑 `asset:equity` 时，director 不知道「上一版我判过什么、为什么」，无法自省与改判说明。这正是用户反复强调的「用结论差异调模型」落空处——TradingAgents 的招牌是 `get_past_context` 把反思注回决策者。
3. **prompt 鼓励骑墙 + 源冲突无规则**：director 铁律「数据盲区→stance neutral/trend hold/confidence low」反而**诱导中性骑墙**（本次 equity 实跑就是 `neutral/hold`）；data-desk/分析师缺「多源冲突时标记分歧而非私自调和」的规则（手工抓 cn10y `2.7% vs 1.71%` 就是典型）。

本 change 把三块固化为可治理变更：**A 大类详情展示多轮辩论（纯展示管线，零 LLM 重跑）**、**B 结果闭环反思（director 跨轮自省，Layer 1 轻量版）**、**C prompt 反骑墙 + 源冲突接地**。

> 现状：详细方案已固化于 `.kiro/specs/v4/design.md §5.9`。本 change 叠加在 `v4-layered-deep-research`（单元化地基）与 `v4-shared-data-desk`（取数/辩论分离）之上，不推翻其设计。

## What Changes

- **改动（A 展示）** `app/services/v4/v4_query.py` `build_asset_detail`：响应加 `debate_rounds`（取 `payload.debate_rounds`，默认 `[]`）与 `analysts`（默认 `{}`）。所有大类通用。因该函数被 `portfolio_v4` 路由与 `build_snapshot_v4` 共用，改一处 → API/快照同步生效。
- **改动（A 展示）** `frontend/src/api/portfolioV4.ts`：`AssetDetail` 接口加 `debate_rounds: DebateRound[]` 与 `analysts?`（`DebateRound` 类型已存在，复用）；`AssetVerdict` 加 `reflection?`。
- **改动（A 展示）** `frontend/src/views/Portfolio/v4/AssetDetailTab.vue`：插「大类深辩历程（N 轮）」折叠块（照搬 `IndustryDetailTab.vue` 的 `idt-debate`/`extractText`）；verdict 区下方加「较上次 / 自检」反思条。
- **改动（B 反思）** `agents/advisor/v4-asset-director.md`：加「记忆/反思」节——开辩前 `Read` 落盘的上一版 `asset:<class>.json`（write 前时序，仍是旧版），输出新增 `reflection{prev_stance,prev_date,what_changed,why_changed,self_check}`。首跑标 `first_run`。
- **改动（C 措辞）** `agents/advisor/v4-asset-director.md`：反骑墙——「仅证据势均力敌才给 neutral/hold，否则必须站队并说明采信/压低哪方；数据盲区降 confidence + 缩幅度而非默认中性」，替换原诱导骑墙的铁律 2。
- **改动（C 措辞）** `agents/advisor/v4-data-desk.md` + 三专项分析师：加「多源冲突标记分歧（列各源值 + 采用值 + 理由），不私自调和」。
- **重生成** v4 静态快照（`build_snapshot_v4.py` 逻辑不变，仅重跑让快照带辩论字段）。
- **不改动** 单元信封 schema 外壳、五色状态机、约束链指纹、v3 全链路；不实现 B 的 Layer 2/3（基准收益回填/个股 alpha，仅登记演进方向）。

## Capabilities

### New Capabilities

- `v4-result-reflection`: 结果闭环反思（Layer 1）—— director 开辩前读上一版 verdict + 本轮新数据，输出 `reflection` 字段（变了什么/为什么改判/上次对不对），前端展示「较上次」条。复用「write 前落盘仍是旧版」的时序巧合，零新基建。

### Modified Capabilities

- `v4-three-tab-overview`: Tab2 大类详情**新增多轮辩论展示**——`build_asset_detail` 补吐 `debate_rounds`/`analysts`，前端照搬行业层折叠块渲染多空 3 轮对栏 + 反思条。
- `v4-asset-research-dept`: director 研判范式修订——**反骑墙果断条款**（替换数据盲区默认中性）+ **源冲突标记分歧**（不私自调和），辩论质量对齐 TradingAgents。

## Impact

**代码（改动）**：
- `app/services/v4/v4_query.py`（`build_asset_detail` 加字段）
- `frontend/src/api/portfolioV4.ts`（`AssetDetail`/`AssetVerdict` 类型）
- `frontend/src/views/Portfolio/v4/AssetDetailTab.vue`（辩论折叠块 + 反思条）
- `agents/advisor/v4-asset-director.md`（reflection 节 + 反骑墙）
- `agents/advisor/v4-data-desk.md` + 三专项分析师 prompt（源冲突标记）

**文档（已更新）**：
- `.kiro/specs/v4/design.md §5.9`（A 展示管线 / B-Layer1 反思 / C 措辞）+ §七文件结构 + §八风险表

**数据**：`asset:<class>` payload 的 `verdict` 旁挂可选 `reflection`（向后兼容，旧信封无此字段不报错）；前端字段缺省即不渲染。不改信封外壳/Mongo 集合结构。

**不影响**：v4 单元信封 schema 外壳/状态机/约束链/v3 全链路；行业层与个股层展示。

**环境约束（验证）**：沙箱无 claude 鉴权/web 工具。A（展示）改动 `py_compile`（后端）+ `node`/构建（前端类型）静态验证，重生成快照即可前端验。B/C（prompt + reflection）需部署机重跑 `asset:equity` 才出 reflection（v2 引用 v1）；沙箱仅静态验证 prompt/schema 一致性。

<!-- Dialectical Analysis
## 方案对比

A 大类辩论展示
方案A1（本方案：build_asset_detail 补吐 + 前端照搬行业折叠块）
- 优点：数据现成（信封已有 debate_rounds/analysts），零 LLM 重跑；改一个共用函数 API/快照同步；前端复用行业层成熟组件
- 缺点：AssetDetailTab 需新增模板块（中等前端工作量）
方案A2（让前端直接读信封原始 JSON 自行解析）
- 缺点：破坏「前端只读 v4_query 同构契约」，快照/API 不一致风险 → 否

B 结果闭环反思
方案B-L1（本方案：复用 write 前时序，director Read 旧版落盘，输出 reflection）
- 优点：零新基建（不建历史文件、不改 write 时序）；轻量、立即可用；直击「调模型」
- 缺点：无收益接地，反思偏主观 → 缓解：明确登记 Layer 2 基准回填为演进；首跑 first_run 不强造
方案B-full（直接对齐 TA：收益回填 + alpha + Reflector）
- 缺点：需基准/持仓收益跟踪基础设施，工程量大、本轮过重 → 拆为 Layer 2/3 后续做
最可能失败点：
- director Read 不到旧版（首跑/路径变） → self_check="first_run"，reflection 各字段允许 null，不阻断
- 旧信封无 reflection 字段 → 前端可选渲染，缺省不显示；schema 向后兼容

C 反骑墙措辞
风险：矫枉过正逼 LLM 强行站队造假 → 缓解：仅「证据势均力敌」才允许 neutral；盲区表达为降 confidence + 缩幅度，保留诚实出口
-->
