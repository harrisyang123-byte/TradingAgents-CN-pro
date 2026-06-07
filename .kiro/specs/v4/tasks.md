# 开发任务 — v4：分层独立深度投研系统

## 概览
- **Feature**: v4 分层独立深度投研系统（七大类资产 → 行业 → 个股的单元化常驻分析）
- **任务数**: 6（Task 0 基础骨架 + S1~S5 五个分段阶段）
- **项目大类**: existing / web-fullstack（FastAPI + Vue3 + MongoDB + claude -p 子 Agent 编排）
- **API 策略**: 在现有 `app/routers/` 扩展，v4 新建**只读 + 导入**路由 `portfolio_v4.py`；触发链路分离——重计算只在 CLI/本地由 claude 调起，Web 不承载在线 LLM 长任务
- **执行模式**: staged（按 design §六 五阶段落地，每阶段独立可用、可回归，v3 完全不动）
- **v3/v4 关系**: 并存。独立集合 `v4_units`、独立目录 `data/v4/`、独立编排器/路由，可灰度可回退

## 需求覆盖矩阵

| 验收标准 | 对应任务 | 覆盖状态 |
|----------|----------|----------|
| AC1.1 持仓穿透归类入七大类，无法归类标「待人工归类」不丢弃 | Task 1 | ✅ |
| AC1.2 区分「可交易标的」vs「持有型敞口」 | Task 1 | ✅ |
| AC1.3 每大类记录「最深下钻层级」配置表 | Task 0 | ✅ |
| AC1.4 持仓为空时按传入持仓文件做同样归类 | Task 1 | ✅ |
| AC2.1 单大类独立运行，多维输入（宏观/基本面/舆情资金/政策地缘） | Task 1 | ✅ |
| AC2.2 对立角色 + 固定 3 轮辩论，记录论点/反驳 | Task 1 | ✅ |
| AC2.3 总监拍板输出形势/方向/风险/趋势 | Task 1 | ✅ |
| AC2.4 每大类独立落盘、独立时间/新鲜度、互不覆盖 | Task 1 | ✅ |
| AC2.5 零持仓大类仍可触发分析 | Task 1 | ✅ |
| AC3.1 读 7 类最新结论；缺失/stale 显式标注并允许补跑或带风险继续 | Task 2 | ✅ |
| AC3.2 当前→目标配比，Σ=100%，每类方向+理由 | Task 2 | ✅ |
| AC3.3 允许某类目标配比 0%（主动归零，记理由），其余 Σ=100% | Task 2 | ✅ |
| AC3.4 权益额度下传为行业层上限；权益=0% 跳过深链并前端标注 | Task 2 | ✅ |
| AC3.5 配比报告记录各大类分析快照指纹 | Task 2 | ✅ |
| AC4.1 CLI 对话主入口 + 等价脚本命令 | Task 0 | ✅ |
| AC4.2 上游更新级联软提醒（仅置黄不自动跑）；可选 scan | Task 2 | ✅ |
| AC4.3 各层独立 TTL，可配置 | Task 0 | ✅ |
| AC4.4 仅跑命中单元，不连带重跑其它，单元状态独立 | Task 0 | ✅ |
| AC4.5 每单元落盘状态/时间/TTL/上游指纹/产物路径 | Task 0 | ✅ |
| AC4.6 前端每单元给「该如何在 CLI 触发」提示，无「点即跑 LLM」按钮 | Task 2 | ✅ |
| AC4.7 运行中单元重复触发去重/排队，不并发重入 | Task 0 | ✅ |
| AC5.1 下游产物记录依据的上游版本/指纹 | Task 0 | ✅ |
| AC5.2 上游新版本→引用旧版的下游置黄 + 可读提示 | Task 2 | ✅ |
| AC5.3 不自动重跑、不阻断使用 stale 结论（软提醒） | Task 0 | ✅ |
| AC5.4 主动刷新下游→重绑最新上游指纹→恢复绿 | Task 0 | ✅ |
| AC5.5 约束链校验发现过时上游约束仅报警不修正数值 | Task 2 | ✅ |
| AC6.1 内置候选行业 + CLI 对话询问/推荐先分析哪些 | Task 3 | ✅ |
| AC6.2 行业深辩单元先跑（多轮辩论定方向），早于配比 | Task 3 | ✅ |
| AC6.3 行业间配比 Σ≤equity_quota；缺/stale 行业标注 | Task 3 | ✅ |
| AC6.4 独立「行业内研究部门」对每只个股独立分析独立缓存 | Task 3 | ✅ |
| AC6.5 行业内资金配比，产目标权重 + 买入区间 | Task 3 | ✅ |
| AC6.6 行业层/个股层遵守独立触发 + 快照指纹/软提醒 | Task 3 | ✅ |
| AC7.1 每非权益大类专属分析部门（复用部门范式） | Task 4 | ✅ |
| AC7.2 现金：持有结构方案（活期/货基/短债/逆回购） | Task 4 | ✅ |
| AC7.3 固收：久期 + 品种结构建议 | Task 4 | ✅ |
| AC7.4 大宗/贵金属：品种/工具层方案，可交易下钻、持有型记敞口 | Task 4 | ✅ |
| AC7.5 房地产：REITs 下钻、实物房产仅记敞口+宏观建议 | Task 4 | ✅ |
| AC7.6 另类：品种方案 + 显著风险标注 | Task 4 | ✅ |
| AC7.7 非权益方案同样遵守独立触发 + 快照/软提醒 | Task 4 | ✅ |
| AC8.1 Tab1 卡片展示七大类（状态色/摘要/当前→目标） | Task 2 | ✅ |
| AC8.2 点大类进 Tab2：权益→行业表格；非权益→差异化方案 | Task 3 / Task 4 | ✅ |
| AC8.3 点行业进 Tab3：深辩报告 + 个股表格 + 行业内配比 | Task 3 | ✅ |
| AC8.4 单元展示状态色 + stale 软提醒文案 + CLI 指令提示 | Task 2 | ✅ |
| AC8.5 缺数据显示空态 + CLI 触发引导，不报错/空白 | Task 2 | ✅ |
| AC9.1 两入口：本地（连库）/ AI 代跑（仅持仓文件） | Task 5 | ✅ |
| AC9.2 两模式产出同构 schema，前端解析一致 | Task 0 | ✅ |
| AC9.3 git 载体 = 单元粒度结构化 JSON 文件 | Task 0 | ✅ |
| AC9.4 重跑覆盖式更新单个单元文件，不触碰其它单元 | Task 1 | ✅ |
| AC9.5 幂等导入（按 unit_id upsert 入 Mongo），前端正确展示 | Task 5 | ✅ |
| AC9.6 落盘敏感数据遵循 .gitignore / 私有仓库约定 | Task 0 | ✅ |
| NFR1.1 单元独立深跑落盘，不阻塞查看其它单元 | Task 0 | ✅ |
| NFR1.2 读取接口走缓存秒级响应，不触发实时 LLM | Task 2 | ✅ |
| NFR2.1 产物可追溯上游版本（指纹）与生成时间 | Task 0 | ✅ |
| NFR2.2 约束链过时可见软提醒，不静默不强制修正 | Task 2 | ✅ |
| NFR3.1 五色状态统一颜色语言前端一目了然 | Task 2 | ✅ |
| NFR3.2 失败/数据降级显式提示可定位（run_report_v4） | Task 5 | ✅ |
| NFR4.1 同份持仓本地/代跑产物 schema 一致 | Task 5 | ✅ |
| NFR4.2 覆盖式落盘不破坏未重跑单元产物/状态 | Task 0 | ✅ |
| NFR5.1 持仓/处方落盘遵循 .gitignore / 私有仓库 | Task 0 | ✅ |
| NFR5.2 不硬编码 API key / 凭据 | Task 0 | ✅ |

> 覆盖率：51 条 AC（46 条 FR-AC + 5 条 NFR 组）100% 覆盖，无遗漏。

## 现有实现利用（旧项目）

### 可直接复用（不改）
| 功能 | 现有文件 | v4 用法 |
|------|----------|---------|
| 输入指纹算法（sha256） | `scripts/stage_cache.py::_fingerprint` | 单元 fingerprint / upstream 比对直接复用 |
| 景气打分引擎 | `app/services/industry_vitality.py` | 权益候选行业推荐沿用 |
| 文件输入模式 | `scripts/collect_data.py`（`--portfolio-file`） | AI 代跑脱库采集复用 |

### 参考重写 / 扩展
| 功能 | 现有文件 | v4 处理 |
|------|----------|---------|
| 编排器范式 | `scripts/workflow-v3-advisor.js` | 新建 `workflow-v4-advisor.js`：线性 7 stage → 单元选择器 + 部门子流程 |
| 落库 | `scripts/ingest_advice.py` | 新建 `scripts/import_v4.py` 按 unit_id upsert（v3 保留） |
| 静态快照 | `scripts/build_snapshot.py` | 新增 `build_snapshot_v4.py` 同构组装 |
| 运行报告 | `scripts/run_report.py` | 新增 `run_report_v4.py` 单元级 |
| 穿透归类 | `industry_classifier.py` / `exposure_service.py` | 扩展为 7 大类 `v4_classifier.py` |
| 个股缓存 | `stock_research_cache.py` | 缓存语义迁到单元信封 |
| 前端总览 | `frontend/src/views/Portfolio/Overview.vue` | 重构为三层 Tab |
| 子 Agent 角色 | `agents/advisor/v3-*.md` | 新建 14 个 `agents/advisor/v4-*.md`（v3 保留） |

### 保留不动（v3 资产）
| 功能 | 现有文件 |
|------|----------|
| v3 在线触发 runner | `app/services/v3_advisor_runner.py` |
| v3 组合分析 API | `app/routers/portfolio_analysis.py` |
| v3 历史结论 | Mongo `portfolio_advice` 集合 |

---

## 任务列表

### Task 0: 单元化基础骨架（基础准备）✅
**关联需求**: AC1.3, AC4.1, AC4.3, AC4.4, AC4.5, AC4.7, AC5.1, AC5.3, AC5.4, AC9.2, AC9.3, AC9.6, NFR1.1, NFR2.1, NFR4.2, NFR5.1, NFR5.2
**目标**: 搭起 v4 的「分析单元」原子地基——统一信封 schema、七大类常量、落盘/索引/锁、纯只读状态机、CLI 入口骨架与 MongoDB 集合。这是后续所有阶段的公共底座（design §一/§4.2/§4.3/§5.1/§5.6）。
**依赖**: 无
**实施**:
1. 建 `app/services/v4/asset_classes.py`：七大类 `class` 枚举 + `max_drill_depth` + 分档 TTL（大类/行业/个股各一档，可配置）（AC1.3, AC4.3）。
2. 建 `app/services/v4/v4_unit_store.py`：单元信封读写（§1.2 schema：unit_id/version/fingerprint/upstream/status/ttl_days/generated_at/run_mode/payload）、`_units.json` 索引、覆盖式写入「只动本单元不触碰其它」（AC4.5, AC9.4 基础, NFR4.2）；`_locks/<unit_id>.lock`（含 pid+ts）去重/排队（AC4.7）。
3. 建 `app/services/v4/v4_state.py`：纯函数状态机（gray/blue/green/yellow/red），按 design §4.3 五步判定；复用 `stage_cache.py::_fingerprint` 做指纹/upstream version 比对；**只读计算，绝不触发重跑**（AC5.1, AC5.3, AC5.4, NFR2.1）。
4. 建 `scripts/run_v4.sh` 骨架：`analyze/refresh/status/scan` 子命令 + 单元选择器解析（仅跑命中单元）+ `--portfolio-file` 透传（AC4.1, AC4.4）。
5. 建 MongoDB `v4_units` 集合 + `(user_id, unit_id)` 唯一索引、`v4_run_log` 集合（design §5.6）。
6. 确认 `data/v4/` 目录结构（§5.1）已在 `.gitignore`；信封不硬编码任何凭据（AC9.6, NFR5.1, NFR5.2）。
**文件**: `app/services/v4/asset_classes.py`、`app/services/v4/v4_unit_store.py`、`app/services/v4/v4_state.py`、`scripts/run_v4.sh`、`.gitignore`（确认）、DB 初始化脚本
**验证**: 单测 `v4_state` 五状态判定（构造 gray/blue/green/yellow/red 各场景）；写入/读取一个 mock 信封，校验覆盖单元不影响其它单元；锁文件防并发重入；`run_v4.sh status` 能列出空单元索引。

### Task 1: S1 资产层 — 七大类穿透归类 + 大类研究部门（3 轮辩论）✅
**关联需求**: AC1.1, AC1.2, AC1.4, AC2.1, AC2.2, AC2.3, AC2.4, AC2.5, AC9.4
**目标**: 落地七大类穿透归类与「大类研究部门」深度分析单元——单大类独立运行、固定 3 轮对立辩论、总监拍板，逐类独立落盘（design FR-001/FR-002、§5.3、§5.4 `asset:<class>` payload）。
**依赖**: Task 0
**实施**:
1. 建 `app/services/v4/v4_classifier.py`：扩展 `industry_classifier.py`/`exposure_service.py`，输出七大类归类，无法归类入 `class=unclassified` 标「待人工归类」不丢弃（AC1.1）；payload 内分离 `tradable` 标的 与 `holding_only_exposure` 敞口（AC1.2）；同时支持 Mongo 持仓与 `--portfolio-file`（AC1.4）。
2. 建大类研究部门 6 个子 Agent：`v4-asset-bull.md`/`v4-asset-bear.md`/`v4-asset-analyst-macro.md`/`v4-asset-analyst-flow.md`/`v4-asset-analyst-policy.md`/`v4-asset-director.md`，沿用 v3 GROUNDING 凭据契约（evidence + verified/estimated/missing）（AC2.1, AC2.2）。
3. 建 `scripts/collect_v4.py`：拼装单大类多维输入包（宏观复用 `market_signals.py`/`data_macro.json`、基本面/估值、舆情资金、政策地缘），缺数据源降级「LLM 知识 + 可得行情」并标 missing（AC2.1）。
4. 建 `scripts/workflow-v4-advisor.js`（首版仅 `asset:<class>` 单元路径）：固定 3 轮辩论循环 append `debate_rounds[]` → director 输出 `verdict`（形势/方向/风险/趋势）（AC2.2, AC2.3）。
5. 落盘 `data/v4/assets/<class>.json` 独立单元，独立 version/generated_at/status，覆盖式更新只动本单元（AC2.4, AC9.4）；零持仓大类仍可 `analyze asset:<class>`（AC2.5）。
**文件**: `app/services/v4/v4_classifier.py`、`agents/advisor/v4-asset-*.md`（6 个）、`scripts/collect_v4.py`、`scripts/workflow-v4-advisor.js`
**验证**: 用样例持仓跑穿透归类，校验七大类 + unclassified 桶 + tradable/holding_only 分离；CLI `run_v4.sh analyze asset:equity` 跑通，产物含 3 轮 debate_rounds + verdict；对零持仓大类（如 alternative）触发能产报告；重跑某类不影响其它类文件。

### Task 2: S2 配比机制 — 资产配比决策 + 约束下传 + 状态机收口 + Tab1 ✅
**关联需求**: AC3.1, AC3.2, AC3.3, AC3.4, AC3.5, AC4.2, AC4.6, AC5.2, AC5.5, AC8.1, AC8.4, AC8.5, NFR1.2, NFR2.2, NFR3.1
**目标**: 落地资产配置委员会配比决策（Σ=100%、允许主动归零、equity_quota 下传）、上游变更级联软提醒的完整状态机闭环，以及前端 Tab1 七大类卡片 + 公共状态组件（design FR-003/FR-004/FR-005、§5.4 `alloc:portfolio`、§5.5 API、§5.7 前端）。
**依赖**: Task 0, Task 1
**实施**:
1. 建 `v4-allocation-director.md`（配置委员会总监）：读 7 个 `asset:*` 最新 verdict，输出 `assets[]`（current→target + action + reasoning），校验 Σtarget=100（AC3.2）；缺失/stale 类入 `input_warnings[]`（AC3.1）；支持 `target_weight=0` + `actively_zeroed:true` + 归零理由，Σ 仍含归零类（AC3.3）。
2. 编排器加 `alloc:portfolio` 单元：写 `equity_quota`=权益 target；`equity_quota==0` 跳过权益深链并标注（AC3.4）；信封 `upstream[]` 记 7 个 `asset:*` 的 version+fingerprint（AC3.5）。
3. 状态机收口（在 `v4_state.py` 基础上）：上游 version 递增→下游置黄 + `stale_reason` 可读文案（AC5.2）；`run_v4.sh scan` 扫过期/过时单元仅置黄不自动跑（AC4.2）；约束传递校验下游引用上游 version < 当前 → 仅报警不修正（AC5.5, NFR2.2）。
4. 建 v4 只读路由 `app/routers/portfolio_v4.py`：`GET /overview`（Tab1 七大类 + 配比 + equity_quota）、`GET /units/status`，响应带 status/version/generated_at/upstream/stale_reason/`cli_hint`，走 Mongo 缓存秒级响应不触发 LLM（AC4.6, NFR1.2）。
5. 前端：`AssetAllocationTab.vue` + `AssetCard.vue`（7 张卡片：状态色 + 摘要 + 当前→目标）（AC8.1, NFR3.1）；公共 `UnitStatusBadge.vue`（五色 + stale 文案 + cli_hint tooltip，无「点即跑 LLM」按钮）（AC8.4, AC4.6）；`EmptyUnitState.vue` 空态 + CLI 引导（AC8.5）。
**文件**: `agents/advisor/v4-allocation-director.md`、`scripts/workflow-v4-advisor.js`（扩展）、`app/services/v4/v4_state.py`（扩展）、`app/routers/portfolio_v4.py`、`frontend/src/views/Portfolio/v4/{AssetAllocationTab,AssetCard,UnitStatusBadge,EmptyUnitState}.vue`、`useV4Units.ts`
**验证**: `run_v4.sh analyze alloc:portfolio` 产配比，Σ=100% 校验；构造某类目标 0% 校验 actively_zeroed 合法；权益=0% 时前端标「本期不配置权益」；改某 `asset:*` 重跑使 version+1，`scan` 后配比单元置黄并显示 stale_reason；前端 Tab1 渲染 7 卡 + 五色 + 空态。

### Task 3: S3 权益深链 — 行业深辩 → 行业配比 → 个股 → 行业内配比 + Tab2/3 ✅
**关联需求**: AC6.1, AC6.2, AC6.3, AC6.4, AC6.5, AC6.6, AC8.2（权益）, AC8.3
**目标**: 贯通权益大类三层深链（正确顺序：先深辩定方向→行业间配比→独立行业内部门做个股→行业内资金配比），并落地 Tab2 权益行业表格与 Tab3 行业/个股表格（design FR-006、§5.3 行业/个股角色、§5.7）。
**依赖**: Task 2
**实施**:
1. 建 `app/services/v4/industry_candidates.py`：内置候选行业清单（风口 + 长期主题），复用 `industry_vitality.py` 景气推荐；CLI 对话由 AI 询问/推荐「先分析哪些行业」（AC6.1）。
2. 建行业研究部门角色 `v4-industry-bull/bear/director.md`；编排器加 `industry:<name>` 单元：多轮辩论 + director 定方向（景气/空间/风险/配置建议），**早于配比**（AC6.2）。
3. 建 `v4-industry-allocator.md` + `alloc:equity_industries` 单元：读各 `industry:*` verdict，Σ行业权重 ≤ equity_quota，缺/stale 行业标注（AC6.3）。
4. 建行业内研究部门角色 `v4-stock-bull/bear/director.md`；`stock:<code>` 单元每只个股独立分析独立缓存，产评级/目标价（AC6.4）；`alloc:industry:<name>` 单元在行业目标权重内配比，产目标权重 + 买入区间（AC6.5）。
5. upstream 链路：`industry:*` 变→`alloc:equity_industries` 黄；`alloc:equity_industries` 变→`alloc:industry:*` 黄（指纹驱动）（AC6.6）。
6. 前端：`AssetDetailTab.vue`（权益分支）+ `IndustryTable.vue`（行业表格：配比/状态/指标）（AC8.2 权益）；`IndustryDetailTab.vue` + `StockTable.vue`（深辩报告 + 个股表格：评级/目标价/目标权重/状态）（AC8.3）。
**文件**: `app/services/v4/industry_candidates.py`、`agents/advisor/v4-industry-*.md`（4 个）、`agents/advisor/v4-stock-*.md`（3 个）、`scripts/workflow-v4-advisor.js`（扩展）、`app/routers/portfolio_v4.py`（扩展 asset/industry 详情）、`frontend/src/views/Portfolio/v4/{AssetDetailTab,IndustryTable,IndustryDetailTab,StockTable}.vue`
**验证**: `run_v4.sh analyze industry:AI算力` 产深辩 + verdict；`analyze alloc:equity_industries` 校验 Σ≤equity_quota；`analyze stock:<code>` 独立缓存、重跑不影响他股；行业配比变更后行业内配比置黄；前端 Tab2 行业表格、Tab3 深辩+个股表格渲染正确。

### Task 4: S4 非权益六类 — 差异化投资方案 ✅
**关联需求**: AC7.1, AC7.2, AC7.3, AC7.4, AC7.5, AC7.6, AC7.7, AC8.2（非权益）
**目标**: 为固收/现金/大宗/贵金属/房地产/另类六大类落地与其本质匹配的差异化方案（复用大类研究部门范式，director 注入按类方案模板），并在 Tab2 渲染方案视图（design FR-007、§5.4 `plan:<class>` payload）。
**依赖**: Task 1（复用大类部门范式）, Task 2（Tab2 框架）
**实施**:
1. 编排器加 `plan:<class>` 单元路径：复用 `v4-asset-bull/bear/director.md`，director prompt 按 class 注入方案产出模板（AC7.1）；upstream = `asset:<class>` 自身分析 + macro（AC7.7）。
2. 各类方案 payload（design §5.4）：
   - 现金 → `holding_structure[]`（活期/货基/短债/逆回购建议分布 + 理由，持有型不荐个券）（AC7.2）；
   - 固收 → `duration_view` + `instrument_mix[]`（国债/信用债/可转债/债基 + 久期取向，结合利率）（AC7.3）；
   - 大宗/贵金属 → `instrument_mix[]`（实物/ETF/相关股），可交易 tradable 下钻、持有型记敞口（AC7.4）；
   - 房地产 → REITs tradable 下钻、实物房产 holding_only 记敞口 + 宏观持有建议（AC7.5）；
   - 另类 → `instrument_mix[]` + 显著 `risk_flags[]`（高波动/合规）（AC7.6）。
3. 前端 `PlanCard.vue`：Tab2 非权益分支渲染各类差异化方案（条目少用卡片/小表）（AC8.2 非权益）。
**文件**: `scripts/workflow-v4-advisor.js`（扩展 plan 路径）、`agents/advisor/v4-asset-director.md`（方案模板）、`app/routers/portfolio_v4.py`（plan 详情）、`frontend/src/views/Portfolio/v4/PlanCard.vue`
**验证**: 对 cash/fixed_income/commodity/precious_metal/real_estate/alternative 各 `run_v4.sh analyze plan:<class>` 跑通，校验各自 payload 字段（holding_structure / duration_view+instrument_mix / risk_flags 等）；前端 Tab2 进入非权益大类展示对应方案卡片；非权益单元遵守状态机软提醒。

### Task 5: S5 双跑 / 导入 / 快照 / 运行报告 — 本地与代跑一致 ✅
**关联需求**: AC9.1, AC9.5, NFR3.2, NFR4.1
**目标**: 打通「本地运行 / AI 代跑」两入口同构、git JSON → MongoDB 幂等导入、静态快照降级与单元级运行报告，确保本地拉取后前端三层 Tab 展示与本地运行一致（design FR-009、§5.5 import、§5.1 快照、NFR3.2）。
**依赖**: Task 0（信封 schema/落盘）, Task 2（前端解析层）；建议在 Task 3/4 单元齐备后做端到端一致性验证
**实施**:
1. 两入口统一编排：本地（连 Mongo）/ AI 代跑（`run_v4.sh analyze <selector> --portfolio-file holdings.json`，不依赖用户 Mongo），均经统一编排器产同构信封（AC9.1, NFR4.1）。
2. 建 `scripts/import_v4.py`：`git pull` 后按 `(user_id, unit_id)` 幂等 upsert `$set` 整个信封入 `v4_units`，重复导入不产脏数据（AC9.5）；可选 `POST /api/portfolio/v4/import` 路由触发或脚本直写。
3. 建 `scripts/build_snapshot_v4.py`：v4 单元 → `frontend/public/snapshot/v4/*.json` 同构组装；`useV4Units.ts` 在 `VITE_STATIC_SNAPSHOT=1` 时 fetch 快照、否则走 API，两来源解析一致（NFR4.1）。
4. 建 `scripts/run_report_v4.py`：单元级运行报告（停在哪/产物空不空/降级与否/前端是否降级），延续 v3「保证看得见」（NFR3.2）。
**文件**: `scripts/import_v4.py`、`scripts/build_snapshot_v4.py`、`scripts/run_report_v4.py`、`scripts/run_v4.sh`（代跑入口收口）、`app/routers/portfolio_v4.py`（import 路由）、`frontend/src/views/Portfolio/v4/useV4Units.ts`（快照来源）
**验证**: 用同一份 holdings.json 走本地 + 代跑两路径，比对产物信封 schema 一致；`import_v4.py` 重复导入两次校验幂等（无重复/脏数据）；`VITE_STATIC_SNAPSHOT=1` 下前端三层 Tab 与走 API 展示一致；`run_report_v4.py` 对一次运行/失败/降级目录均能产可读报告。

---

## 进度
| 任务 | 关联需求 | 状态 |
|------|----------|------|
| Task 0 单元化基础骨架 | AC1.3/4.1/4.3/4.4/4.5/4.7/5.1/5.3/5.4/9.2/9.3/9.6 + NFR1.1/2.1/4.2/5.1/5.2 | ✅ |
| Task 1 S1 资产层（归类+大类部门） | AC1.1/1.2/1.4/2.1~2.5/9.4 | ✅ |
| Task 2 S2 配比机制 + 状态机 + Tab1 | AC3.1~3.5/4.2/4.6/5.2/5.5/8.1/8.4/8.5 + NFR1.2/2.2/3.1 | ✅ |
| Task 3 S3 权益深链 + Tab2/3 | AC6.1~6.6/8.2(权益)/8.3 | ✅ |
| Task 4 S4 非权益六类方案 | AC7.1~7.7/8.2(非权益) | ✅ |
| Task 5 S5 双跑/导入/快照/报告 | AC9.1/9.5 + NFR3.2/4.1 | ✅ |

> 状态更新（2026-06-07）：S2-S5 全部已落地——后端（`portfolio_v4.py` 只读+导入路由 / `v4_query.py` / `v4_state.py` 收口 / `industry_candidates.py` / 编排器 `workflow-v4-advisor.js` 全单元路径）、Agent（`v4-allocation-director` + `v4-industry-*` + `v4-stock-*`）、前端三层 Tab（`V4Overview.vue` + `v4/` 下 11 个组件/composable）、脚本（`import_v4.py` / `build_snapshot_v4.py` / `run_report_v4.py`）均已创建并通过 `py_compile` + `node --check` + `bash -n`。审查报告点名的 3 处遗留（`v4_query` 静默吞异常、`v4_state.fingerprint` 宽泛 except、`/import` 缺 unit_id 校验）已修复。端到端真跑（claude -p 驱动子 Agent + Mongo）仍需具鉴权与数据库的部署环境验证。
