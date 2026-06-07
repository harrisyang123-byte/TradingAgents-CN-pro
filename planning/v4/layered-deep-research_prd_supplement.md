# 需求补充文档 — v4 角色补全（参考 TradingAgents 投研机构范式）

> 主文档：`planning/v4/layered-deep-research_prd.md`（FR-001~FR-009）
> 本文档：v4 **角色/部门能力补全**，新增 FR-010~FR-016，并修订主文档 FR-003 / FR-006 的部分 AC。
> 设计参照：[TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents)（arXiv:2412.20138）——模拟真实投研机构的多 Agent 分工。
> 范围档位：**C 档（最全）**——补齐专项分析师团队 + 交易执行 + 组合级风控委员会 + 配比层对立 + 组合合成终审 + 决策记忆回路。

---

## 0. 背景：为什么要补全（缺口诊断）

主文档定义了「七大类 → 行业 → 个股」三层部门 + 配比委员会的骨架；实现里已落地 14 个 v4 子 Agent。但对照**主文档自身的 AC（AC2.2「多空 + 专项视角分析师」、AC6.2「参考行业研究最佳实践配置角色」）**与你的 MECE 铁律（**能力打满 + 对立辩论 + 职责单一**），存在系统性能力缺口：

| 层 | 主文档/铁律要求 | 现有 14 agent 实况 | 缺口 |
|----|----------------|-------------------|------|
| 大类 `asset:*` | 多空 + 专项分析师 + 总监，3 轮 | bull/bear + macro/flow/policy + director（6） | ✅ 已打满（基准范式）|
| 行业 `industry:*` | 多空 + **专项视角**（AC6.2）+ 总监，多轮 | bull/bear + director（3） | ❌ **无专项分析师团队**，深度低于大类层 |
| 个股 `stock:*` | 独立研究部门，多空 + 总监 | bull/bear + director，且**仅 1 轮辩论** | ❌ **无专项分析师 + 辩论缩水成 1 轮** |
| 配比 `alloc:*` ×3 | 总监拍板 | 单总监（无对立）| ⚠ **无对立挑战角色**（与「对立辩论」铁律不符）|
| 组合级风控 | —（主文档未列）| 无 | ❌ **全 v4 无事前风控委员会**（v3 曾有，重构后丢失）|
| 组合级合成/终审 | —（主文档未列）| 无 | ❌ **无约束链合成校验 + 终审批准**（v3 曾有）|
| 学习回路 | —（主文档未列）| 无 | ❌ **无决策记忆/反思**，每次从零开始 |

**结论**：现有 14 agent 能跑通骨架，但行业/个股层「能力不打满」、配比层「无对立」、组合层「无风控+无终审+无记忆」。本补充按 TradingAgents 的成熟分工补齐。

---

## 1. TradingAgents 范式映射（设计锚点）

TradingAgents 把交易决策拆成五个协作团队，本补充逐一映射到 v4 的单元化分层：

| TradingAgents 角色/团队 | 职责 | 映射到 v4 | 落点 FR |
|------------------------|------|-----------|---------|
| **Analyst Team**（Fundamentals / Sentiment / News / Technical）| 4 个专项视角喂给辩论 | 行业层专项分析师团队 + 个股层专项分析师团队 | FR-010 / FR-011 |
| **Researcher Team**（Bull vs Bear + Research Manager）| 结构化多空辩论 + 经理拍板 | v4 已有（多空 + 总监）；**配比层补对立** | FR-014 |
| **Trader Agent** | 把研究转成可执行交易（择时 + 仓位） | 个股→配比之间的「交易执行/择时」角色 | FR-012 |
| **Risk Management Team**（Risky / Neutral / Safe + Risk Judge）| 三档风险偏好辩论 + 风控裁判 | 新单元 `risk:portfolio` 组合级风控委员会 | FR-013 |
| **Portfolio Manager**（终审 approve/reject）| 汇总并最终批准/打回 | 新单元 `synth:portfolio` 合成 + 终审 | FR-015 |
| **Memory / Reflection**（实现收益反思注入 PM）| 决策记忆与学习回路 | 单元决策日志 + 反思注入 | FR-016 |

> 改造原则：**借范式、不照抄**。TradingAgents 是「单标的、单次决策」；v4 是「分层单元化、独立缓存、约束硬传递」。专项分析师按 v4 各层语境改造（行业层关注景气/产业链，个股层关注财务/估值/技术/舆情），风控/合成作为**独立单元**接入新鲜度状态机（FR-004/FR-005）。

---

## 2. 新增功能需求（FR-010 ~ FR-016）

### FR-010: 行业研究部门专项分析师团队（落实主文档 AC6.2）
- **类型**: 功能需求
- **优先级**: P0
- **描述**: When 用户触发某行业深度分析时, the system shall 在多空 3 轮辩论之前/之中，由一支**行业专项分析师团队**从多个独立专业视角对该行业出具尽调意见，作为多空双方与行业总监的共同输入，使行业层达到与大类层对称的分析深度。
- **专项分析师角色（参考 TradingAgents Analyst Team，按行业研究改造，4 个）**:

  | 角色 | v4 agent | 视角 |
  |------|----------|------|
  | 景气/基本面分析师 | `v4-industry-analyst-prosperity` | 需求/订单/产能利用/价格趋势/盈利景气 |
  | 估值分析师 | `v4-industry-analyst-valuation` | 行业估值分位、相对历史/海外、性价比 |
  | 产业链/竞争格局分析师 | `v4-industry-analyst-chain` | 上下游、集中度、国产替代/出海、壁垒 |
  | 资金/交易面分析师 | `v4-industry-analyst-capital` | 北向/ETF 申赎/拥挤度/轮动/技术位 |

- **验收标准**:
  - [ ] AC10.1: WHEN 触发 `industry:<name>` THE SYSTEM SHALL 先运行 4 个专项分析师各出具一份结构化视角意见（景气/估值/产业链/资金），落盘为独立中间产物。
  - [ ] AC10.2: THE SYSTEM SHALL 将专项分析师意见作为多空双方与行业总监的共同输入；多空辩论须可引用专项结论作为论据。
  - [ ] AC10.3: THE SYSTEM SHALL 保持**固定 3 轮**多空辩论后由行业总监拍板（不变更主文档 AC6.2 的辩论轮次，仅补齐「专项视角」角色）。
  - [ ] AC10.4: IF 某专项数据缺失 THEN 该分析师须诚实降级（结论 neutral + 标注缺失），不得编造；缺失维度计入 `data_quality`。
- **修订主文档**: FR-006 AC6.2 中「参考行业研究最佳实践配置角色」**明确为**：多头研究员 + 空头研究员 + 上述 4 位专项分析师 + 行业总监。

### FR-011: 个股研究部门专项分析师团队 + 3 轮辩论（落实主文档 AC6.4）
- **类型**: 功能需求
- **优先级**: P0
- **描述**: When 用户触发某个股分析时, the system shall 由一支**个股专项分析师团队**从财务/估值/技术/舆情四个独立视角尽调，并将个股多空辩论由 1 轮提升为**固定 3 轮**，使个股层（最终下单标的所在层）达到与上层一致的分析强度。
- **专项分析师角色（直接对标 TradingAgents Analyst Team 四专项，4 个）**:

  | 角色 | v4 agent | 对标 TradingAgents | 视角 |
  |------|----------|--------------------|------|
  | 基本面/财务分析师 | `v4-stock-analyst-fundamental` | Fundamentals Analyst | 营收/利润/ROE/现金流/订单/产能 |
  | 估值分析师 | `v4-stock-analyst-valuation` | （Fundamentals 派生）| PE/PB/PS 分位、DCF、相对同业、目标价区间 |
  | 技术/交易面分析师 | `v4-stock-analyst-technical` | Technical Analyst | 趋势/均线/MACD/RSI/量价/关键位 |
  | 舆情/催化分析师 | `v4-stock-analyst-sentiment` | Sentiment + News Analyst | 公告/新闻/研报/解禁减持/事件催化 |

- **验收标准**:
  - [ ] AC11.1: WHEN 触发 `stock:<code>` THE SYSTEM SHALL 先运行 4 个专项分析师各出具结构化意见（财务/估值/技术/舆情），落盘为独立中间产物。
  - [ ] AC11.2: THE SYSTEM SHALL 将个股多空辩论轮次由现状 1 轮改为**固定 3 轮**（与 `DEBATE_ROUNDS` 一致），每轮记录论点与反驳。
  - [ ] AC11.3: THE SYSTEM SHALL 由个股总监综合 4 专项 + 3 轮多空，拍板评级/目标价/买入区间，并显式说明采信/压低了哪一方。
  - [ ] AC11.4: THE SYSTEM SHALL 使个股结论不逆所属行业 verdict 大方向（行业 avoid 时个股看多须给极强、接地的理由）。
- **修订主文档**: FR-006 AC6.4「独立的行业内研究部门……每只个股独立运行一次分析」**明确为**：4 位专项分析师 + 多空 3 轮 + 个股总监；个股辩论轮次与大类/行业层对齐为 3 轮。

### FR-012: 交易执行/择时角色（参考 TradingAgents Trader Agent）
- **类型**: 功能需求
- **优先级**: P1
- **描述**: When 个股评级与行业内权重就绪时, the system shall 由一个「交易执行/择时」角色把研究结论转成**可执行的建仓方案**：在买入区间基础上给出分批节奏、择时触发条件与单次仓位幅度（timing + magnitude），而非只给一个静态目标权重。
- **角色**: `v4-stock-trader`（交易执行员）。
- **验收标准**:
  - [ ] AC12.1: WHEN `alloc:industry:<name>` 产出个股目标权重 THE SYSTEM SHALL 由交易执行员对每只 go 标的产出 `execution_plan`：买入区间、分批档位（如 3 档逐步建仓）、加仓/减仓触发条件、单次幅度上限。
  - [ ] AC12.2: THE SYSTEM SHALL 使建仓方案受上游约束（不超该个股在行业内的目标权重、买入区间取研究区间与估值分位的保守交集）。
  - [ ] AC12.3: IF 缺乏实时价格 THEN 择时条件以相对区间/分位表述并标注 estimated，不编造绝对价位。
  - [ ] AC12.4: THE SYSTEM SHALL 把 `execution_plan` 并入个股/行业内配比单元的产物（不单独建单元类型，避免单元爆炸），随单元缓存与新鲜度联动。

### FR-013: 组合级风险管理委员会（新单元 `risk:portfolio`，参考 TradingAgents Risk Management Team）
- **类型**: 功能需求
- **优先级**: P0
- **描述**: When 资产配比/行业配比/行业内配比就绪、用户触发组合风控时, the system shall 以一个独立的**组合级风险管理委员会**单元，对整份待执行组合做事前硬风控校验 + 三档风险偏好辩论 + 风控总监拍板，输出风险评估与硬约束违规清单。
- **角色（对标 Risky / Neutral / Safe + Risk Judge，4 个）**:

  | 角色 | v4 agent | 对标 TradingAgents |
  |------|----------|--------------------|
  | 激进风险分析师 | `v4-risk-aggressive` | Risky/Aggressive Debator |
  | 中性风险分析师 | `v4-risk-neutral` | Neutral Debator |
  | 保守风险分析师 | `v4-risk-conservative` | Safe/Conservative Debator |
  | 风控总监（含硬规则引擎结果裁决）| `v4-risk-director` | Risk Judge |

- **新增单元类型**: `risk:portfolio`（unit_type=`risk`）。
- **验收标准**:
  - [ ] AC13.1: THE SYSTEM SHALL 在三档辩论之前执行**事前硬风控规则**（非 LLM 可计算项）：单标的权重上限、单行业合计上限（≤行业 target）、总仓位上限（≤权益额度+各类目标）、现金底线，产出 `hard_violations[]`。
  - [ ] AC13.2: THE SYSTEM SHALL 运行激进/中性/保守三档风险分析师对组合集中度、回撤、流动性、尾部风险做**固定 3 轮**辩论。
  - [ ] AC13.3: WHEN 辩论结束 THE SYSTEM SHALL 由风控总监综合硬规则 + 三档意见，输出 `RiskAssessment`：最大回撤估计、集中度风险、黑天鹅触发条件（建议性）、硬违规清单（拦截性）。
  - [ ] AC13.4: THE SYSTEM SHALL 区分**硬约束（违规须拦截/打回）**与**软建议（风控总监意见）**，二者职责分开、分别标注（延续 v3「风控规则硬、Risk Director 软」的设计）。
  - [ ] AC13.5: 上游 = `alloc:portfolio` + `alloc:equity_industries` + 各 `alloc:industry:*`；THE SYSTEM SHALL 记录其快照指纹，上游变更时本单元置黄（FR-005）。
  - [ ] AC13.6: IF 存在 `hard_violations` THEN 在产物与前端显式高亮，并提示「建议打回对应配比单元重做」，但**不自动重跑**（遵循 FR-004 软提醒原则）。

### FR-014: 配比层对立挑战（给 `alloc:*` 三单元补反方，参考 Researcher 辩论范式）
- **类型**: 功能需求
- **优先级**: P1
- **描述**: When 任一配比单元（`alloc:portfolio` / `alloc:equity_industries` / `alloc:industry:<name>`）运行时, the system shall 在配置总监拍板之前，引入一个**配置挑战者**角色，从对立立场（激进集中 vs 保守分散）挑战拟定配比，暴露过度集中/过度激进/踏空风险，使配比层符合「对立辩论」铁律。
- **角色**: `v4-allocation-challenger`（配置挑战者，复用于三个 alloc 单元，按单元注入语境）。
- **验收标准**:
  - [ ] AC14.1: WHEN 触发任一 `alloc:*` 单元 THE SYSTEM SHALL 先由对应配置总监给出**初稿配比**，再由配置挑战者逐条挑战（集中度、与 verdict 一致性、是否踏空高景气、是否过度配置弱景气）。
  - [ ] AC14.2: THE SYSTEM SHALL 由配置总监回应挑战并产出**终稿配比**，在产物中保留 `challenge[]` 与采纳/驳回理由（可追溯）。
  - [ ] AC14.3: THE SYSTEM SHALL 保持各配比单元原有的 Σ约束校验（FR-003 AC3.2 / FR-006 AC6.3、AC6.5）不变，挑战环节不破坏硬约束。
- **修订主文档**: FR-003 / FR-006 AC6.3、AC6.5 的「总监拍板」**明确为**：总监初稿 → 挑战者挑战 → 总监终稿（一轮对立即可，不强制 3 轮，控成本）。

### FR-015: 组合合成与终审（新单元 `synth:portfolio`，参考 Portfolio Manager）
- **类型**: 功能需求
- **优先级**: P0
- **描述**: When 各层单元（七大类 + 配比 + 行业 + 个股 + 风控）就绪、用户触发组合合成时, the system shall 以一个独立的**组合合成单元**做约束链完整性校验、缺口识别与最终处方组装，并由**组合终审（Portfolio Manager）**批准或打回，输出一份可直接执行的组合调整方案。
- **角色（2 个）**:

  | 角色 | v4 agent | 对标 TradingAgents |
  |------|----------|--------------------|
  | 组合合成师 | `v4-portfolio-synthesizer` | （Trader/Risk Judge 汇总）延续 v3 portfolio-synthesizer |
  | 组合终审 | `v4-portfolio-manager` | Portfolio Manager（approve/reject）|

- **新增单元类型**: `synth:portfolio`（unit_type=`synth`）。
- **验收标准**:
  - [ ] AC15.1: THE SYSTEM SHALL 由合成师验证约束链完整性（宏观→大类配比→行业配比→行业内个股配比的 Σ与上限逐层成立），**只校验报警、不擅自修正数值**（延续 FR-005 AC5.5）。
  - [ ] AC15.2: THE SYSTEM SHALL 识别覆盖缺口（如某 go 行业无个股分析、equity_quota 未配满、某大类无 verdict），产出 `gaps[]` 与「建议补跑的单元指令」。
  - [ ] AC15.3: THE SYSTEM SHALL 汇总 `asset_allocation` + `industry_matrix` + 个股配比 + `execution_plan` + `RiskAssessment` 为一份结构化最终处方。
  - [ ] AC15.4: WHEN 合成完成 THE SYSTEM SHALL 由组合终审给出 `decision: approve | reject_with_reasons`：存在硬违规（FR-013）或关键缺口时打回并列出须修复项，否则批准。
  - [ ] AC15.5: 上游 = `alloc:portfolio` + `alloc:equity_industries` + 各 `alloc:industry:*` + `risk:portfolio` + 各 `industry:*`/`stock:*`；THE SYSTEM SHALL 记录全部上游指纹，任一上游变更则本单元置黄。
  - [ ] AC15.6: THE SYSTEM SHALL 使终审产物成为前端 Tab 1 顶部「最终处方 + 风控结论 + 终审状态」的数据源。

### FR-016: 决策记忆与反思回路（参考 TradingAgents Memory/Reflection，可选增强）
- **类型**: 功能需求
- **优先级**: P2
- **描述**: When 任一单元/组合决策落盘时, the system shall 追加一条决策日志；WHEN 同单元再次运行时, the system shall 注入该单元的历史决策（及可得时的实现收益反思）作为上下文，形成跨次学习闭环，而非每次从零判断。
- **验收标准**:
  - [ ] AC16.1: THE SYSTEM SHALL 为每个单元维护 append-only 决策日志（决策摘要 + 时间 + 依据指纹），落盘于 `data/v4/_memory/<unit_id>.md`（含敏感数据，遵循 .gitignore/私有仓约定）。
  - [ ] AC16.2: WHEN 重跑某单元 THE SYSTEM SHALL 把最近 N 条同单元历史决策注入相关 agent 提示（如总监/终审），供其参考一致性与历史误判。
  - [ ] AC16.3: IF 可获取持仓的实现收益 THEN THE SYSTEM SHALL 生成一段简短反思（哪类判断对/错）注入组合终审；获取不到则跳过，不阻断。
  - [ ] AC16.4: THE SYSTEM SHALL 使记忆为**可选增强**：缺失记忆文件时全链路照常运行，不报错。

---

## 3. 角色补全总清单（净增 agent）

| FR | 新增 v4 agent | 数量 | 所属单元 |
|----|--------------|------|----------|
| FR-010 | `v4-industry-analyst-prosperity` / `-valuation` / `-chain` / `-capital` | 4 | `industry:*` |
| FR-011 | `v4-stock-analyst-fundamental` / `-valuation` / `-technical` / `-sentiment` | 4 | `stock:*` |
| FR-012 | `v4-stock-trader` | 1 | `alloc:industry:*`（增强）|
| FR-013 | `v4-risk-aggressive` / `-neutral` / `-conservative` / `-director` | 4 | `risk:portfolio`（新）|
| FR-014 | `v4-allocation-challenger` | 1 | 三个 `alloc:*` |
| FR-015 | `v4-portfolio-synthesizer` / `v4-portfolio-manager` | 2 | `synth:portfolio`（新）|
| FR-016 | （无新 agent，机制 + 记忆文件） | 0 | 全单元 |
| **合计** | | **16** | 14 → **30 个 v4 agent** |

补全后各层角色对称性：

| 层 | 补全后角色配置 | 角色数 |
|----|---------------|--------|
| 大类 `asset:*` | 多空 + macro/flow/policy + 总监 | 6（不变）|
| 行业 `industry:*` | 多空 + 景气/估值/产业链/资金 4 专项 + 总监 | 7（+4）|
| 个股 `stock:*` | 多空 + 财务/估值/技术/舆情 4 专项 + 总监 | 7（+4）|
| 配比 `alloc:*` | 总监 + 挑战者 | 2（+1）|
| 风控 `risk:portfolio` | 激进/中性/保守 + 风控总监 | 4（新）|
| 合成 `synth:portfolio` | 合成师 + 终审 | 2（新）|

---

## 4. 单元类型与选择器变更（接入主文档 §5.2 / FR-004）

新增 2 个单元类型，并入新鲜度状态机（FR-004）与 stale 软提醒（FR-005）：

| 新单元选择器 | unit_type | 上游 | 产物落点 |
|--------------|-----------|------|----------|
| `risk:portfolio` | `risk` | `alloc:portfolio` + `alloc:equity_industries` + 各 `alloc:industry:*` | `data/v4/risk/portfolio.json` |
| `synth:portfolio` | `synth` | 上述 + `risk:portfolio` + 各 `industry:*`/`stock:*` | `data/v4/synth/portfolio.json` |

> `v4-stock-trader`、`v4-allocation-challenger` **不新建单元类型**——前者并入 `alloc:industry:*` 产物的 `execution_plan`，后者并入 `alloc:*` 产物的 `challenge[]`，避免单元数量爆炸（遵循「能力打满但不滥设单元」）。

---

## 5. 对实现的影响点（design 阶段细化，本文不写实现）

- **编排器 `scripts/workflow-v4-advisor.js`**：
  - `runIndustryDepartment` / `runStockDepartment` 增加专项分析师团队调用（4 个）；个股辩论 `rounds` 由写死 1 轮改为 `DEBATE_ROUNDS`（3）。
  - 新增 `runRiskPortfolio()` / `runPortfolioSynth()` 部门函数 + `parseSelector` 支持 `risk:` / `synth:` 前缀 + `main()` 路由分支。
  - `runAllocation*` 三处在总监后插入挑战者→终稿环节。
- **采集 `scripts/collect_v4.py`**：为 `risk:portfolio` / `synth:portfolio` 拼装上游单元产物输入包；为专项分析师补充行业估值分位、个股财务/技术指标等输入维度。
- **CLI `scripts/run_v4.sh`**：unit-selector 文档与校验增加 `risk:portfolio` / `synth:portfolio`。
- **存储 `app/services/v4/v4_unit_store.py`**：`unit_type` 枚举增加 `risk` / `synth`；TTL 表为新类型配档。
- **前端**：Tab 1 顶部增加「最终处方 + 风控结论 + 终审状态」区块（数据源 = `synth:portfolio`）；风控违规高亮。
- **记忆**：新增 `data/v4/_memory/`（.gitignore，私有仓）。
- **AGENTS.md / docs/wiki/v4-ai-proxy-run.md**：补全角色清单与新单元跑法。

---

## 6. 验收与回归（在主文档 NFR 之上补充）

- [ ] 行业/个股单元产物含 `analysts{}`（4 专项意见）且多空辩论为 3 轮（FR-010/011）。
- [ ] `risk:portfolio` 产物含 `hard_violations[]`（硬）与 `RiskAssessment`（软），二者分离（FR-013）。
- [ ] `alloc:*` 产物含 `challenge[]` 与终监采纳/驳回理由（FR-014）。
- [ ] `synth:portfolio` 产物含 `decision`、`gaps[]`、完整最终处方，且约束链校验只报警不改数（FR-015）。
- [ ] 新单元正确接入五色状态机与 stale 软提醒：改一个上游配比 → `risk:portfolio` 与 `synth:portfolio` 置黄（FR-005/FR-004）。
- [ ] 缺记忆文件时全链路照常运行（FR-016 AC16.4）。
- [ ] 本地运行与 AI 代跑对新单元产出同构 schema（延续 NFR-004）。

---

## 7. 分阶段交付建议（staged，承接主文档分段策略）

1. **阶段 S1（P0，对称补齐）**：FR-010 行业专项 + FR-011 个股专项 + 个股 3 轮 —— 不动单元结构，立即提升行业/个股层深度。
2. **阶段 S2（P0，组合级闭环）**：FR-013 风控委员会 + FR-015 合成终审（含 2 个新单元类型 + 前端区块）—— 补齐「事前风控 + 终审」这条 v3 丢失的能力。
3. **阶段 S3（P1，精修）**：FR-012 交易择时 + FR-014 配比对立 —— 让下单更可执行、配比更经得起挑战。
4. **阶段 S4（P2，学习）**：FR-016 记忆反思回路 —— 跨次学习闭环。

> 每阶段独立可用、可回归；任一单元失败只染红自己（延续 FR-004 AC4.4 / NFR-004 AC4.2）。
