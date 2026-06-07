# 技术设计 — v4：分层独立深度投研系统

> 本设计基于 `requirements.md`（9 条 FR + 5 条 NFR），将 v3「一次全量单链路」重构为「分层、单元化、独立触发、增量缓存、约束链一致性」的常驻深度投研体系。
> 设计铁律延续 v3：**所有 LLM 决策走 `.md` 子 Agent + Workflow 编排（claude -p 驱动），Python 不直接 `llm.invoke()`**；运行态存 MongoDB，git 传输用单元粒度 JSON。
> 项目大类：existing / web-fullstack（FastAPI + Vue3 + MongoDB）。技术栈沿用，未新增框架。

---

## 一、核心设计抽象：分析单元（Analysis Unit）

v4 的一切围绕「**分析单元**」展开——它是触发、缓存、落盘、状态、约束链的最小原子。这是把 v3「单链路阶段（stage）」升维成「可独立调度的单元（unit）」的关键。

### 1.1 单元类型与稳定 ID

| 单元类型 | unit_id 格式 | 部门 | 下钻 | 对应 FR |
|----------|-------------|------|------|---------|
| 大类分析 | `asset:<class>` | 大类研究部门 | 7 个固定 class | FR-002/FR-007 |
| 资产配比 | `alloc:portfolio` | 资产配置委员会 | 单例 | FR-003 |
| 行业深辩 | `industry:<name>` | 行业研究部门 | 仅权益 | FR-006 |
| 行业间配比 | `alloc:equity_industries` | 行业配置团队 | 单例（权益内） | FR-006 |
| 个股分析 | `stock:<code>` | 行业内研究部门 | 仅权益 | FR-006 |
| 行业内配比 | `alloc:industry:<name>` | 行业内研究部门 | 每 Go 行业一个 | FR-006 |
| 非权益方案 | `plan:<class>` | 大类研究部门（复用） | 6 个非权益 class | FR-007 |

> 七大类 `class` 枚举（固定）：`equity`(权益) / `fixed_income`(固定收益) / `cash`(现金及等价物) / `commodity`(大宗商品) / `precious_metal`(贵金属) / `real_estate`(房地产) / `alternative`(另类投资)。

### 1.2 统一单元信封（落盘 schema 的外壳，FR-009 同构核心）

每个单元一个稳定路径 JSON，**外壳统一、payload 按单元类型差异化**——这是「本地运行 / AI 代跑产物同构」「幂等 upsert」「快照指纹」三件事的共同地基：

```jsonc
{
  "unit_id": "industry:AI算力",        // 稳定唯一键（upsert 主键）
  "unit_type": "industry",
  "schema_version": "v4.0",
  "version": 7,                          // 每次重跑 +1（下游引用此号判 stale）
  "fingerprint": "sha256:...",           // 本单元输入内容指纹（复用 stage_cache 算法）
  "upstream": [                          // 本单元依据的上游版本（FR-005 链路追溯）
    {"unit_id": "alloc:portfolio", "version": 3, "fingerprint": "sha256:..."},
    {"unit_id": "asset:equity",    "version": 5, "fingerprint": "sha256:..."}
  ],
  "status": "green",                     // gray|blue|green|yellow|red（运行态计算，落盘记最近值）
  "ttl_days": 7,
  "generated_at": "2026-06-06T16:40:00Z",
  "run_mode": "ai_proxy",                // local | ai_proxy（仅元信息，前端解析不区分）
  "error": null,
  "payload": { /* 按 unit_type 不同，见 §4 各部门产物 schema */ }
}
```

---

## 二、需求追溯（每条 AC → 设计）

### FR-001 七大类体系与穿透归类
| AC | 设计方案 |
|----|----------|
| AC1.1 | `v4_classifier.py` 扩展现有 `industry_classifier.py`/`exposure_service.py` 的穿透逻辑，输出 7 大类归类；无法归类入 `class=unclassified` 桶并在 overview 标「待人工归类」，不丢弃 |
| AC1.2 | 单元 payload 内 `tradable` 标的列表 vs `holding_only` 敞口分离；持有型（实物房产/实物贵金属/各国现金）只记 `exposure_amount`，不产 candidates |
| AC1.3 | 七大类配置表 `ASSET_CLASSES`（含 `max_drill_depth` 字段）内置于 `app/services/v4/asset_classes.py` 与前端常量；前端据此决定 Tab2 渲染「行业+个股」还是「持有结构方案」 |
| AC1.4 | 归类入口同时支持 Mongo 持仓与 `--portfolio-file` JSON（复用 `collect_data.py` 文件输入模式），AI 代跑走文件路径 |

### FR-002 大类逐类深度分析部门（3 轮辩论 + 总监）
| AC | 设计方案 |
|----|----------|
| AC2.1 | 大类研究部门 agent 输入拼装多维数据包：宏观（复用 `data_macro.json`/`market_signals.py`）、基本面/估值、舆情资金面、政策地缘；缺数据源时降级为「LLM 知识 + 可得行情」并 evidence 标 `missing` |
| AC2.2 | 对立角色 `v4-asset-bull.md`（多头研究员）vs `v4-asset-bear.md`（空头研究员）+ 专项 `v4-asset-analyst-macro/flow/policy`；编排器固定循环 **3 轮**，每轮 append 到 `debate_rounds[]` |
| AC2.3 | `v4-asset-director.md`（大类部门总监）读 3 轮辩论 → 输出 `verdict`：形势研判/方向(看多/看空/中性)/主要风险/建议趋势 |
| AC2.4 | 每大类落 `data/v4/assets/<class>.json` 独立单元，独立 version/generated_at/status，互不覆盖（单元化天然隔离） |
| AC2.5 | 零持仓大类仍可触发（CLI `分析<大类>`）；`tradable` 候选可空，分析聚焦「是否值得择机配置」 |

### FR-003 资产配比决策与约束下传
| AC | 设计方案 |
|----|----------|
| AC3.1 | `alloc:portfolio` 单元读 7 个 `asset:*` 单元最新 verdict；缺失/stale 的类在 payload `input_warnings[]` 标注，前端展示「先补跑或带风险继续」 |
| AC3.2 | `v4-allocation-director.md`（配置委员会总监）输出 `assets[]`：current_weight→target_weight + action + reasoning，**校验 Σtarget=100** |
| AC3.3 | target_weight 允许 0；payload 区分 `actively_zeroed:true`（主动归零 + reasoning）与缺失；Σ 校验仍含归零类（贡献 0） |
| AC3.4 | payload `equity_quota` = 权益 target_weight，写入 `alloc:portfolio`，下游 `alloc:equity_industries` 引用为权重上限；`equity_quota==0` 时编排器跳过权益深链并在 overview 标「本期不配置权益」 |
| AC3.5 | `alloc:portfolio` 信封 `upstream[]` 记 7 个 `asset:*` 的 version+fingerprint，供下游一致性校验 |

### FR-004 触发机制与新鲜度状态机
| AC | 设计方案 |
|----|----------|
| AC4.1 | 主入口 CLI 对话：AI 解析自然语言 → `scripts/run_v4.sh <verb> <unit-selector>`；等价脚本子命令供本地直接调用（见 §5.2） |
| AC4.2 | 上游更新 → `v4_state.py` 级联置黄（软提醒，不自动跑）；可选 `run_v4.sh scan` 扫过期单元仅置黄 |
| AC4.3 | TTL 分档配置于 `asset_classes.py`/编排 CACHE：大类配置 TTL、行业 TTL、个股 TTL 各一档，可改 |
| AC4.4 | 单元选择器只跑命中单元；状态各自独立（单元化隔离，FR-009 覆盖式不动他单元） |
| AC4.5 | 每单元信封落盘 status/generated_at/ttl_days/upstream/产物路径；`_units.json` 索引汇总 |
| AC4.6 | overview/详情接口为每单元返回 `cli_hint`（自然语言 + 等价脚本命令），前端展示但不提供「点即跑 LLM」按钮 |
| AC4.7 | 运行锁：`data/v4/_locks/<unit_id>.lock`（含 pid+ts）；重复触发去重/排队，blue 态拒绝并发重入 |

### FR-005 约束链一致性与 stale 软提醒
| AC | 设计方案 |
|----|----------|
| AC5.1 | 下游信封 `upstream[]` 记上游 version+fingerprint（人读提示如「基于 alloc v3、asset:equity v5」） |
| AC5.2 | 上游 version 递增后，`v4_state.py` 计算下游 status=yellow，overview 返回 `stale_reason`（如「行业配比基于 3 天前资产配置，建议刷新」） |
| AC5.3 | 状态机只置黄、绝不自动重跑、不阻断读取 stale 产物（软提醒语义） |
| AC5.4 | 刷新下游时重新绑定当前最新上游 version/fingerprint，status 回 green |
| AC5.5 | 约束传递（equity_quota 等）校验：下游引用的上游 version < 上游当前 version → 仅报警不修正数值 |

### FR-006 权益深链（深辩→行业配比→个股→行业内配比）
| AC | 设计方案 |
|----|----------|
| AC6.1 | `app/services/v4/industry_candidates.py` 内置候选行业清单（风口 + 长期主题）；CLI 对话由 AI 询问/推荐「先分析哪些行业」，用户自选或采纳 |
| AC6.2 | `industry:<name>` 单元先跑：`v4-industry-bull/bear` 多轮辩论 + `v4-industry-director` 定方向（景气/空间/风险/配置建议）——**早于配比** |
| AC6.3 | `alloc:equity_industries` 单元后跑：`v4-industry-allocator` 读各 `industry:*` verdict，Σ行业权重 ≤ equity_quota；缺/stale 行业在 payload 标注 |
| AC6.4 | `stock:<code>` 单元：`v4-stock-bull/bear + v4-stock-director`，每只个股**独立单元独立缓存**，产评级/目标价 |
| AC6.5 | `alloc:industry:<name>` 单元：在该行业目标权重内对选定个股配比，产目标权重 + 买入区间 |
| AC6.6 | 链路：`industry:*` 变 → `alloc:equity_industries` 黄；`alloc:equity_industries` 变 → `alloc:industry:*` 黄（upstream 指纹驱动，§3） |

### FR-007 非权益六类差异化方案
| AC | 设计方案 |
|----|----------|
| AC7.1 | `plan:<class>` 复用大类研究部门范式（bull/bear/director），director prompt 按 class 注入「方案产出模板」 |
| AC7.2 | cash：payload `holding_structure[]`（活期/货基/短债/逆回购建议分布 + 理由），持有型不荐个券 |
| AC7.3 | fixed_income：payload `duration_view` + `instrument_mix[]`（国债/信用债/可转债/债基 + 久期取向），结合利率 |
| AC7.4 | commodity/precious_metal：payload `instrument_mix[]`（实物/ETF/相关股），可交易工具 tradable 下钻、持有型记敞口 |
| AC7.5 | real_estate：REITs 工具下钻 tradable；实物房产 holding_only 记敞口 + 宏观持有建议 |
| AC7.6 | alternative：payload `instrument_mix[]` + 显著 `risk_flags[]`（高波动/合规） |
| AC7.7 | `plan:*` 同样走 §3 指纹/状态机（upstream = `asset:<class>` 自身分析 + macro） |

### FR-008 三层 Tab 前端
| AC | 设计方案 |
|----|----------|
| AC8.1 | Tab1 资产配置：7 张**卡片**（状态色 + 摘要 + current→target），复用/扩展 `Overview.vue` |
| AC8.2 | Tab2 大类详情（动态）：权益→行业**表格**（配比/状态/指标）；非权益→方案卡片/小表 |
| AC8.3 | Tab3 行业/个股（动态）：行业深辩报告 + 个股**表格**（评级/目标价/目标权重/状态） |
| AC8.4 | 各单元卡片/表格行展示状态色 + stale 软提醒文案 + `cli_hint`，无「点即跑 LLM」按钮 |
| AC8.5 | 缺数据显示空态 + CLI 触发引导，不报错/空白 |

### FR-009 双跑同构落盘解析
| AC | 设计方案 |
|----|----------|
| AC9.1 | 入口①本地（连 Mongo）②AI 代跑（`--portfolio-file`，不依赖用户 Mongo）；均经统一编排器 |
| AC9.2 | 两模式产同一信封 schema（§1.2），`run_mode` 仅元信息，前端解析一致 |
| AC9.3 | git 载体 = `data/v4/**/*.json` 单元文件（diff 友好可 review），非 dump/二进制 |
| AC9.4 | 重跑覆盖式更新单个单元文件 + version+1，不触碰他单元 |
| AC9.5 | `scripts/import_v4.py` 幂等 upsert（按 `unit_id` 主键）入 Mongo `v4_units`；前端三层 Tab 正确展示，与本地一致 |
| AC9.6 | `data/` 已在 .gitignore；含持仓/处方的单元文件遵循私有仓库约定（沿用 v3 隐私约束） |

### 非功能需求
| AC | 设计方案 |
|----|----------|
| NFR1.1/1.2 | 单元独立深跑落盘；读取接口走 Mongo 缓存产物秒级响应、不触发 LLM |
| NFR2.1/2.2 | 信封 upstream + version 全程可追溯；约束链校验仅软提醒不静默不修正 |
| NFR3.1/3.2 | 五色状态统一语言；失败/降级显式提示，延续 `run_report` 理念（v4 产 `run_report_v4`） |
| NFR4.1/4.2 | 同构 schema 双跑对齐；覆盖式落盘不破坏未重跑单元 |
| NFR5.1/5.2 | 敏感数据遵循 .gitignore/私有仓库；不硬编码密钥 |

---

## 三、现有实现分析（旧项目必须）

| 功能 | 文件 | 状态 | v4 处理 |
|------|------|------|---------|
| 阶段缓存 + 输入指纹 | `scripts/stage_cache.py` | ✅ 可直接复用 | 指纹算法（sha256 输入文件）正是 FR-005 所需，v4 单元指纹/upstream 比对复用其 `_fingerprint` |
| 编排器范式 | `scripts/workflow-v3-advisor.js` | 🔁 参考重写 | 新建 `workflow-v4-advisor.js`，从「线性 7 stage」改为「单元选择器 + 部门子流程」；`agent()`/`Bash()`/缓存门范式保留 |
| 数据采集 | `scripts/collect_data.py` | 🔁 扩展 | 复用文件输入模式 + 景气榜；新增非权益大类数据包拼装 |
| 落库 | `scripts/ingest_advice.py` | 🔁 参考 | 新建 `scripts/import_v4.py` 按 unit_id upsert `v4_units`（v3 ingest 保留不动） |
| 静态快照 | `scripts/build_snapshot.py` | 🔁 扩展 | 新增 v4 单元 → `frontend/public/snapshot/v4/*.json` 同构组装 |
| 运行报告 | `scripts/run_report.py` | 🔁 参考 | v4 单元级 run_report（停在哪/降级与否） |
| 两阶段 runner | `app/services/v3_advisor_runner.py` | ⛔ 不复用在线触发 | v4 触发走 CLI/本地，不经 Web；保留 v3 兼容 |
| 组合分析 API | `app/routers/portfolio_analysis.py` | ⛔ 保留 v3 | v4 新建只读 + 导入路由 `app/routers/portfolio_v4.py` |
| 概览 API | `app/routers/paper.py` | 🔁 参考 | v4 overview 读 `v4_units` 组装三层结构 |
| 穿透归类 | `app/services/industry_classifier.py`/`exposure_service.py` | 🔁 复用 | 扩展为 7 大类穿透 `v4_classifier.py` |
| 景气打分 | `app/services/industry_vitality.py` | ✅ 复用 | 权益行业候选推荐沿用 |
| 个股研究缓存 | `app/services/stock_research_cache.py` | 🔁 参考 | 个股单元缓存语义参考，迁到单元信封 |
| 前端总览 | `frontend/src/views/Portfolio/Overview.vue` | 🔁 重构 | 扩为三层 Tab（现已有 asset/industry/drawer 雏形） |
| v3 子 Agent ×17 | `agents/advisor/v3-*.md` | 🔁 参考 | v4 新建 `agents/advisor/v4-*.md` 部门角色；v3 保留 |
| 历史结论 | Mongo `portfolio_advice` | 🟰 并存 | v4 用独立 `v4_units` 集合，不迁移不删除 v3 |

> **v3/v4 关系决策**：并存。v4 写独立集合与独立文件目录、独立编排器与路由，v3 链路完全不动，可灰度切换、可回退。

---

## 四、架构设计

### 4.1 整体分层与单元流（Mermaid）

```mermaid
flowchart TD
    subgraph CLI["触发层（CLI 对话为主，FR-004）"]
        U["用户自然语言<br/>『分析权益大类』『深辩AI行业』"]
        AI["AI 解析 → run_v4.sh verb unit-selector"]
        U --> AI
    end

    AI --> ORCH["workflow-v4-advisor.js<br/>单元调度 + 缓存门 + 部门子流程"]

    subgraph DEPT["分析部门（claude -p 驱动 v4-*.md 子 Agent）"]
        D1["大类研究部门<br/>bull/bear/analysts ×3轮 + director<br/>FR-002/FR-007"]
        D2["资产配置委员会<br/>allocation-director<br/>FR-003"]
        D3["行业研究部门<br/>bull/bear + director<br/>FR-006 AC6.2"]
        D4["行业配置团队<br/>industry-allocator<br/>FR-006 AC6.3"]
        D5["行业内研究部门<br/>stock bull/bear/director + 行业内配比<br/>FR-006 AC6.4/6.5"]
    end

    ORCH --> D1 --> D2
    D2 -->|equity_quota>0| D3 --> D4 --> D5
    D2 -.->|非权益 plan:class| D1

    subgraph STORE["单元落盘（FR-009）"]
        FS["data/v4/**/*.json<br/>单元信封 + _units.json 索引<br/>git 传输载体"]
    end
    D1 & D2 & D3 & D4 & D5 --> FS

    FS -->|stage_cache 指纹 + upstream 比对| STATE["v4_state 状态机<br/>gray/blue/green/yellow/red<br/>FR-005 软提醒"]

    subgraph IMPORT["本地拉取后导入（FR-009 AC9.5）"]
        GIT["git pull"] --> IMP["import_v4.py<br/>按 unit_id 幂等 upsert"]
    end
    FS --> GIT
    IMP --> MONGO[("MongoDB v4_units")]

    subgraph WEB["读取层（前端只读，FR-008）"]
        API["portfolio_v4 路由<br/>overview/asset/industry/状态"]
        FE["Overview.vue 三层 Tab<br/>卡片+表格+状态色+cli_hint"]
        API --> FE
        SNAP["静态快照 fetch 降级"] --> FE
    end
    MONGO --> API
    FS --> SNAP
```

### 4.2 状态机（FR-004/FR-005）

```mermaid
stateDiagram-v2
    [*] --> gray: 单元从未运行
    gray --> blue: CLI 触发，获锁
    blue --> green: 成功落盘，绑定上游指纹
    blue --> red: 运行失败
    green --> yellow: TTL 过期 或 上游 version 递增（软提醒）
    yellow --> blue: 用户 CLI 刷新
    red --> blue: CLI 重试
    yellow --> green: 仅当用户刷新（系统不自动转）
    note right of yellow
        只提醒不自动跑(AC5.3)
        旧结论仍可读
    end note
```

### 4.3 约束链与快照指纹（FR-005 核心机制）

- 复用 `stage_cache.py::_fingerprint`：对单元输入文件集做 sha256。
- 单元落盘时：`version+1`，并把当前所有上游单元的 `{unit_id, version, fingerprint}` 写入本单元 `upstream[]`。
- 状态计算（`v4_state.py`，纯函数，不调 LLM）：
  1. 文件不存在 → gray；有锁且无产物 → blue；`error!=null` → red。
  2. 自身 `now - generated_at > ttl_days` → yellow。
  3. 任一 `upstream[i].version < 该上游当前 version`（或 fingerprint 不匹配）→ yellow + `stale_reason`。
  4. 否则 green。
- **不强制刷新**：状态只读计算，绝不触发重跑（AC5.3）。约束数值（equity_quota 等）发现来自过时上游 → 仅报警（AC5.5）。

---

## 五、详细设计

### 5.1 落盘文件结构（git 传输载体）

```
data/v4/                              # 已在 .gitignore（含敏感财务，私有仓库共享）
├── _units.json                       # 单元状态索引（id→version/status/ttl/upstream/path）
├── _locks/<unit_id>.lock             # 运行锁（去重/排队，AC4.7）
├── inputs/                           # collect 产物（持仓穿透 / 宏观 / 景气榜）
│   ├── portfolio_classified.json     # 7 大类穿透归类（FR-001）
│   ├── data_macro.json  data_vitality.json
├── assets/<class>.json               # 大类分析单元 ×7（FR-002）
├── plans/<class>.json                # 非权益方案单元 ×6（FR-007）
├── allocation/
│   ├── portfolio.json                # 七大类配比 + equity_quota（FR-003）
│   ├── equity_industries.json        # 行业间配比（FR-006 AC6.3）
│   └── industry_<name>.json          # 行业内个股配比（FR-006 AC6.5）
├── industries/<name>.json            # 行业深辩单元（FR-006 AC6.2）
├── stocks/<code>.json                # 个股分析单元（FR-006 AC6.4）
├── run_report_v4.json / .md          # 单元级运行报告（NFR3.2）
└── _snapshot/v4/*.json               # 前端静态快照（同构降级）
```

### 5.2 CLI 触发命令设计（FR-004）

| 自然语言（AI 解析） | 脚本命令 | 单元 |
|--------------------|----------|------|
| 分析<大类> | `run_v4.sh analyze asset:<class>` | 大类分析/非权益方案 |
| 跑资产配比 | `run_v4.sh analyze alloc:portfolio` | 配比 |
| 深辩<行业> | `run_v4.sh analyze industry:<name>` | 行业深辩 |
| 跑行业配比 | `run_v4.sh analyze alloc:equity_industries` | 行业间配比 |
| 分析个股<代码> | `run_v4.sh analyze stock:<code>` | 个股 |
| 跑<行业>内配比 | `run_v4.sh analyze alloc:industry:<name>` | 行业内配比 |
| 刷新<单元> | `run_v4.sh refresh <unit-selector>` | 强制失效重跑 |
| 看状态 / 哪些该刷新 | `run_v4.sh status` / `scan` | 状态机扫描（仅置黄） |

- AI 代跑：`run_v4.sh analyze <selector> --portfolio-file holdings.json`（不连用户 Mongo）。
- 锁机制：获锁失败（blue 态）→ 提示「该单元正在运行」并退出（AC4.7）。

### 5.3 部门 Agent 角色清单（新建 `agents/advisor/v4-*.md`）

| Agent 文件 | 角色 | 部门 | 输出 |
|-----------|------|------|------|
| `v4-data-desk.md` | **数据采集台（唯一带 web 工具）** | **通用能力层（各层共用）** | 两档取数 → `inputs/data_macro.json` + `inputs/<单元>.json`（每项 evidence verified+URL） |
| `v4-asset-bull.md` | 多头研究员 | 大类研究 | 看多论点 + evidence |
| `v4-asset-bear.md` | 空头研究员 | 大类研究 | 看空/风险论点 + evidence |
| `v4-asset-analyst-macro.md` | 宏观视角分析师 | 大类研究 | 利率/通胀/周期 |
| `v4-asset-analyst-flow.md` | 资金/舆情视角分析师 | 大类研究 | 资金面/情绪 |
| `v4-asset-analyst-policy.md` | 政策/地缘视角分析师 | 大类研究 | 政策/地缘 |
| `v4-asset-director.md` | 大类部门总监 | 大类研究 | verdict：形势/方向/风险/趋势（含非权益方案模板） |
| `v4-allocation-director.md` | 资产配置委员会总监 | 配置委员会 | 7 大类 current→target + equity_quota |
| `v4-industry-bull.md` | 行业多头研究员 | 行业研究 | 景气/空间看多 |
| `v4-industry-bear.md` | 行业空头研究员 | 行业研究 | 景气拐点/风险 |
| `v4-industry-director.md` | 行业部门总监 | 行业研究 | 行业方向研判 |
| `v4-industry-allocator.md` | 行业配置总监 | 行业配置 | 行业间权重（≤equity_quota） |
| `v4-stock-bull.md` | 个股多头 | 行业内研究 | 标的看多 + 目标价 |
| `v4-stock-bear.md` | 个股空头 | 行业内研究 | 标的风险 |
| `v4-stock-director.md` | 行业内研究总监 | 行业内研究 | 个股评级/目标价 + 行业内配比 |

> 辩论轮次：大类/行业固定 3 轮（AC2.2），编排器循环 append `debate_rounds[]`，总监最后拍板。角色 prompt 沿用 v3 GROUNDING 凭据契约（evidence + verified/estimated/missing）。
>
> **取数/辩论分离（§5.8 优化）**：上表 14 个辩论/分析角色全部 `tools: [Read]`，**只消费 `v4-data-desk` 产出的输入包、绝不自己联网取数**；唯一带 `web_search`/`web_fetch` 的 Agent 是 `v4-data-desk`。这解决了原设计「14 个 Agent 各自重复解读宏观、且只有 Read 工具却被要求联网」的矛盾。详见 §5.8。

### 5.4 关键 payload schema（按单元类型，FR-009 同构）

**asset:<class>（大类分析，FR-002）**
```jsonc
"payload": {
  "asset_class": "equity",
  "debate_rounds": [{"round":1,"bull":"...","bear":"...","analysts":{...}}],
  "verdict": {"stance":"bullish|bearish|neutral","situation":"...","direction":"...","risks":["..."],"trend":"..."},
  "tradable": [{"name":"...","code":"...","note":"..."}],
  "holding_only_exposure": 0,
  "evidence": [{"claim":"...","source":"...","status":"verified"}]
}
```

**alloc:portfolio（资产配比，FR-003）**
```jsonc
"payload": {
  "assets": [{"asset_class":"equity","current_weight":39,"target_weight":55,"action":"add","actively_zeroed":false,"reasoning":"..."}],
  "equity_quota": 55,
  "input_warnings": [{"asset_class":"commodity","issue":"stale|missing"}],
  "sum_check": 100
}
```

**industry:<name> / alloc:equity_industries / stock:<code> / alloc:industry:<name>**：分别含 `verdict`（行业方向）、`allocations[{industry,target_weight}]`（Σ≤equity_quota）、`rating/target_price/entry_range`、`stock_weights[{code,target_weight,entry_price_range}]`。

**plan:<class>（非权益方案，FR-007）**：`verdict` + 按类的 `holding_structure[]`(cash) / `duration_view`+`instrument_mix[]`(fixed_income) / `instrument_mix[]`+`risk_flags[]`(commodity/precious_metal/alternative/real_estate)。

### 5.5 后端 API 设计（只读 + 导入，FR-004 触发链路分离）

| 端点 | 方法 | 描述 | 响应要点 |
|------|------|------|----------|
| `/api/portfolio/v4/overview` | GET | Tab1 七大类 + 配比 | 7 卡（状态/摘要/current→target）+ equity_quota |
| `/api/portfolio/v4/asset/{class}` | GET | Tab2 大类详情 | 权益→行业列表；非权益→方案 payload + 状态 |
| `/api/portfolio/v4/industry/{name}` | GET | Tab3 行业详情 | 深辩报告 + 个股列表 + 行业内配比 |
| `/api/portfolio/v4/units/status` | GET | 全单元状态机 | 各单元 status/ttl/stale_reason/cli_hint |
| `/api/portfolio/v4/import` | POST | 导入单元产物（可选，亦可脚本直写） | 调 import_v4 幂等 upsert |

> 所有读取接口响应均带单元 `status/version/generated_at/upstream/stale_reason/cli_hint`。**无任何「触发 LLM」写接口**（重计算只在 CLI/本地，技术约束）。鉴权复用 `get_current_user`。

### 5.6 数据库设计（MongoDB）

| 集合 | 主键 | 说明 |
|------|------|------|
| `v4_units` | `(user_id, unit_id)` 唯一索引 | 单元信封 upsert 落地（AC9.5）；含 status/version/upstream/payload |
| `v4_run_log` | `run_id` | 单元运行记录（触发时间/模式/结果/耗时，NFR3） |

> 导入幂等：`import_v4.py` 按 `(user_id, unit_id)` upsert，`$set` 整个信封，重复导入不产脏数据（AC9.5）。索引 `db.v4_units.create_index([("user_id",1),("unit_id",1)], unique=True)`。

### 5.7 前端三层 Tab（FR-008，扩展 Overview.vue）

```
Overview.vue（顶部 el-tabs）
├── Tab1 资产配置   AssetAllocationTab.vue   7×AssetCard（卡片，状态色+摘要+current→target+cli_hint）
├── Tab2 大类详情   AssetDetailTab.vue       权益→IndustryTable.vue（表格）；非权益→PlanCard.vue
└── Tab3 行业个股   IndustryDetailTab.vue    深辩报告 + StockTable.vue（表格：评级/目标价/权重/状态）
```
- 卡片 vs 表格：7 大类（少）卡片；行业/个股列表（多、需对比）表格（AC8.1-8.3）。
- 公共组件 `UnitStatusBadge.vue`（五色 + stale 文案 + `cli_hint` tooltip，AC8.4）；`EmptyUnitState.vue`（空态 + CLI 引导，AC8.5）。
- 数据源统一封装 `useV4Units.ts`：`VITE_STATIC_SNAPSHOT=1` 时 fetch `snapshot/v4/*.json`，否则走 API（FR-009 双来源同构解析）。

### 5.8 通用能力层与数据采集台 `v4-data-desk`（★架构优化，取数/辩论分离）

> 本节是 `docs/wiki/v4-architecture.md`（规范架构图）落到详细设计的实现规格。把原本散在 14 个辩论 Agent prompt 里的「自行联网补齐」抽成**一个共享的数据采集 Agent**，借鉴 [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) 的 Analyst-toolkit / Researcher-debate 分层。

#### 5.8.1 为什么要这一层（解决的矛盾）

| 旧设计问题 | 本节方案 |
|-----------|---------|
| 14 个辩论 Agent 各自解读宏观，N 个单元重复取同一份 LPR/CPI/北向，且各单元读数可能对不齐 → 破坏约束链一致性 | 公共指标 **run 级取一次、全单元同源共读**，一致性由「同源同指纹」构造保证 |
| 辩论 Agent `tools:[Read]` 却被 prompt 要求「联网补齐」——空头支票，做不到 | 联网集中到唯一带 `web_search`/`web_fetch` 的 `v4-data-desk`；辩论 Agent 维持 Read-only |
| akshare/Mongo 在 Pod 缺失即静默降级标 missing/编造 | data-desk 联网兜底，取到标 `verified`+URL；取不到才 `missing` 并显式提示，**严禁编造** |

#### 5.8.2 两档取数（消除重复 + 保证一致）

| 档 | 取什么 | 时机 | 产物 | 谁消费 |
|----|--------|------|------|--------|
| **档 A 全局公共指标**（薄薄一层、十来个数） | LPR、7天逆回购、CPI、PMI、北向资金、人民币汇率、原油、金价、10Y 国债收益率 | **run 起手取一次**（`data_macro.json` 在 TTL 内则跳过，复用同源） | `inputs/data_macro.json` | 全部 7 大类 + 所有行业 + 所有个股**共读同一份** |
| **档 B 单元级深取**（重活在此、按需多次） | 权益→行业景气/估值；固收→收益率曲线/信用利差；大宗→库存/期货升贴水；个股→财报/资金流 | **触发该单元时**、单元内可多次取 | `inputs/<单元>.json` 的 `desk_*` 字段 | 仅该单元的部门 |

- 心智模型：data-desk 是「**按单元调用的取数角色**」——深研到哪个单元就为它深取一轮，**不是**开跑前抓完全宇宙数据的批处理。
- 档 A 的「run 级一次」在 CLI 单元粒度运行下落为：**`data_macro.json` 带 `fetched_at`+`ttl_hours`（默认当个交易日内有效）；data-desk 启动先检查其新鲜度，新鲜则复用、过期才重取**——这样跨多次 `run_v4.sh analyze <unit>` 调用也能同源共读。

#### 5.8.3 `data_macro.json` 升级后 schema（档 A 产物）

```jsonc
{
  "source": "v4-data-desk",                 // 旧 needs_fetch/market_signals 之外的新来源
  "data_availability": "available",          // available | partial | unavailable
  "fetched_at": "2026-06-07T09:00:00Z",
  "ttl_hours": 12,
  "indicators": {
    "lpr_1y": {"value": 3.1, "unit": "%", "as_of": "2026-05-20",
               "status": "verified", "source_url": "http://www.pbc.gov.cn/..."},
    "cpi_yoy": {"value": 0.3, "unit": "%", "as_of": "2026-04", "status": "verified", "source_url": "..."},
    "northbound_net": {"value": null, "status": "missing", "note": "未取到当日北向净流入"}
    // … pmi / reverse_repo_7d / usdcny / brent / gold / cn10y
  },
  "evidence": [{"claim":"1年期LPR 3.1%","source_url":"...","status":"verified"}]
}
```

每个指标自带 `status`（verified/estimated/missing）+ `source_url`，下游辩论 Agent 引用时直接继承凭据，无需自己核实。

#### 5.8.4 编排器接入点（`workflow-v4-advisor.js`）

在 `main()` 跑具体部门**之前**插入一个 `ensureDataDesk(sel)` 阶段：

```
main(sel)
  ├─ ensureDataDesk(sel)                       // ★新增
  │    ├─ 档A：data_macro.json 不存在/过期 → agent('v4-data-desk', {tier:'global'}) → 写 inputs/data_macro.json
  │    └─ 档B：按 sel.type 取该单元深数据 → agent('v4-data-desk', {tier:'unit', selector}) → 写 inputs/<单元>.json 的 desk_* 字段
  └─ runAssetDepartment / runIndustryDepartment / runStockDepartment / runAllocation*  // 不变，只 Read 输入包
```

- `ensureDataDesk` 是编排器内唯一调用带 web 工具 Agent 的地方；其余 `agent()` 调用全是 Read-only 辩论角色，**一行不改**。
- `alloc:*` 单元只读上游落盘单元、不需要档 B 深取，仅确保档 A `data_macro.json` 新鲜。

#### 5.8.5 `collect_v4.py` 职责退化

collect_v4 从「取数 + 拼包」**退化为「持仓穿透归类 + 拼输入包骨架」**：

- **保留**：`classify_holdings` 七大类穿透归类、按单元类型拼 `asset_/plan_/industry_/stock_` 包的**骨架结构**（字段占位）。
- **移除/降级**：`build_macro_snapshot()` 的 best-effort 联网与 `score_all_industries`/个股基本面的 best-effort 抓取——这些**改由 data-desk 在 stage2 联网取**。collect 阶段只写 `data_macro.json` 的占位（`source:"pending_data_desk"`），或在 data-desk 接入前保持 `needs_fetch` 兼容。
- 好处：stage1 变成纯 Python、零网络依赖、永远成功；所有联网取数收敛到 stage2 的 data-desk（有 web 工具、有凭据契约）。

> 兼容策略：data-desk 落地前，编排器若检测不到 `v4-data-desk.md` 或运行环境无 web 工具，回落到「collect_v4 best-effort + needs_fetch 占位」旧路径——**不阻断**，仅在 run_report 标注「宏观未联网核实」。

#### 5.8.6 `v4-data-desk.md` Agent 契约要点

- frontmatter：`tools: [Read, web_search, web_fetch]`（**唯一开 web 的 v4 Agent**）。
- 入参：`tier`（global|unit）、`selector`、`data_dir`。
- 铁律：① 只取数、不做投资研判（研判是辩论部门的职责）；② 每个数字必须 `verified`+`source_url` 或显式 `missing`，**严禁编造/套用示例**；③ 优先官方源（PBoC/统计局/交易所/Wind 公开页），取不到再标 missing；④ 输出严格 JSON，写回 data_dir 由编排器 Bash 落盘。

---


### 5.9 大类辩论展示 + 结果闭环反思 + 反骑墙措辞（★借鉴 TradingAgents）

本节固化三块增强：**A 大类详情展示多轮辩论（纯展示管线，零 LLM 重跑）**、**B 结果闭环反思（director 跨轮自省，Layer 1）**、**C prompt 反骑墙 + 源冲突接地**。三者均叠加在 §5.8 之上，不改单元信封 schema 外壳、不改状态机/约束链/v3。

#### 5.9.1 A — 大类详情展示多轮辩论（展示缺口，非数据缺口）

**根因**：`asset:<class>` 信封 `payload` 早已存了完整的 `debate_rounds`（多空 3 轮）与 `analysts`（macro/flow/policy 三专项），但 `build_asset_detail`（`v4_query.py`）只吐 `verdict/tradable/industries/plan`，把辩论与专项分析丢弃；前端 `AssetDetailTab.vue` 也无渲染区。行业层 `build_industry_detail` 与 `IndustryDetailTab.vue` 已有现成的辩论折叠块（`idt-debate`），照搬即可。**这是展示管线缺口，不需要任何 LLM 重跑。**

改动点（4 处，全展示/管线）：

| # | 文件 | 改动 |
|---|------|------|
| 1 | `app/services/v4/v4_query.py` `build_asset_detail` | 响应加 `debate_rounds`（取 `payload.debate_rounds`，默认 `[]`）与 `analysts`（取 `payload.analysts`，默认 `{}`）。**所有大类通用**——非权益大类同样有多空辩论，一并展示 |
| 2 | `frontend/src/api/portfolioV4.ts` | `AssetDetail` 接口加 `debate_rounds: DebateRound[]` 与 `analysts?: Record<string, any>`（`DebateRound` 类型已存在，复用） |
| 3 | `frontend/src/views/Portfolio/v4/AssetDetailTab.vue` | 在 verdict 头与行业/方案区之间插「大类深辩历程（N 轮）」折叠块——照搬 `IndustryDetailTab.vue` 的 `idt-debate`/`extractText(side)` 多空对栏；可选追加「宏观/资金/政策三视角」小卡 |
| 4 | `scripts/build_snapshot_v4.py` | 无需改逻辑（复用 `build_asset_detail`），仅**重新生成快照**让静态快照也带辩论。**不重跑分析** |

因 `build_asset_detail` 被 `portfolio_v4` 路由与 `build_snapshot_v4` 共用，改这一个函数 → API 与静态快照同时生效（NFR4.1 同构）。

#### 5.9.2 B — 结果闭环反思（Layer 1：跨版本自我反思注入）

借鉴 TradingAgents 的洞察：**记忆的价值在「结果接地的反思」，而非单纯版本 diff**。完整对齐需「收益回填」基础设施，故分 3 层增量，本设计**只落 Layer 1**（轻量、无需收益 feed）：

- **时序巧合可复用**：`write_unit` 是「先归档旧版、再写新版」，而 director 跑在 write **之前**——所以 director 运行时，落盘的 `data/v4/assets/<class>.json` **仍是上一版**。director 直接 `Read` 它即可拿到自己上次的 verdict，**无需新建历史文件**。
- **director prompt 加「记忆/反思」节**：开辩前读上一版 verdict（若存在）+ 本轮 data-desk 新数据，在输出新增 `reflection` 字段：

```json
"reflection": {
  "prev_stance": "上次结论（无历史则 null）",
  "prev_date": "上次 generated_at",
  "what_changed": "数据/判断哪里变了",
  "why_changed": "为什么改判（引用本轮新数据/事件）",
  "self_check": "上次判断现在回看对不对（无历史则 'first_run'）"
}
```

- **schema/接口/前端**：`asset:<class>` payload 的 `verdict` 旁挂 `reflection`（可选）；`portfolioV4.ts` `AssetVerdict` 旁加 `reflection?` 类型；`AssetDetailTab.vue` verdict 区下方加「较上次 / 自检」小条（无历史则不显示）。
- **价值**：直接服务「看结论差异、调模型」，复用现成 archive + data-desk，零新基建。首跑 `reflection.self_check="first_run"`，重跑后才出真实自省。

**Layer 2/3（本设计不实现，仅登记演进方向）**：Layer 2 给每大类绑基准（权益=沪深300/固收=中债…），data-desk 每轮快照基准点位入信封，重跑算「上次→这次基准涨跌%」让反思引用真实结果（接近 TA alpha 接地）；Layer 3 个股级 alpha 跟踪，工程量大，暂不排期。

#### 5.9.3 C — 反骑墙 + 源冲突接地（prompt 措辞）

借鉴 TradingAgents 两条招牌措辞，改 director 与 data-desk/分析师 prompt：

1. **反骑墙（director）**：现铁律 2「数据盲区→stance 趋向 neutral / trend 趋向 hold / confidence low」反而**诱导骑墙**。改为 TA 式果断条款——「**只有多空证据真正势均力敌才给 neutral/hold；否则必须站队，明确说明采信哪方、压低哪方**」。数据盲区表达为「**降低 confidence + 缩小建议幅度**」，而非默认中性。
2. **源冲突接地（data-desk + 三专项分析师）**：加「**多源冲突时标记分歧（列出各源值 + 采用值 + 采用理由），不私自调和出一个数**」——把手工抓 cn10y `2.7% vs 1.71%` 冲突的经验固化成规则。这与 §5.8 data-desk 凭据契约一致、是其细化。

#### 5.9.4 实施顺序与验证

```
A（展示管线，纯前端/查询，改完即可前端验证看到辩论）
  → B-Layer1 + C（改 director/data-desk prompt + schema + 前端反思条；需重跑一次 asset:<class> 才出 reflection）
```

- A 验证：`build_asset_detail` 加字段后 `py_compile` 绿；重生成快照；前端点大类卡 → 大类详情页见多空 3 轮对栏。
- B/C 验证：director prompt 加 `reflection` 节后，部署机（claude 鉴权）重跑 `asset:equity`，确认 v2 verdict 带 reflection 引用 v1 结论；`AssetDetailTab` 显示「较上次」条。沙箱仅静态验证（`py_compile` / `node --check` / Vue 由 `vue-tsc` 或构建）。

#### 5.9.5 适用范围（全局通用能力 + 分阶段落地）

**定性**：B（结果闭环反思）与 C（反骑墙 + 源冲突接地）**本质是全局通用能力**，与 §5.8 的 `v4-data-desk` 同属「通用能力层」——它们不是大类层专属机制，而是对 v4 全部研判型角色普适。**但本期落地范围收窄到大类层**（`v4-asset-director` + data-desk），先验证闭环与效果，其余层下一阶段低成本铺开。

v4 有 4 个「总监/裁判」型角色，都满足同一模式（有结论 + 会重跑覆盖 + 已被 archive 归档）：

| Agent | 层 | 结论字段 | B 反思天然适用 | C 反骑墙天然适用 |
|-------|----|---------|:---:|:---:|
| `v4-asset-director` | 大类 | `verdict.stance` | ✅ | ✅ |
| `v4-industry-director` | 行业 | `verdict.stance/go_nogo` | ✅ | ✅ |
| `v4-stock-director` | 个股 | `rating/目标价` | ✅ | ✅ |
| `v4-allocation-director` | 配比 | `weights` | ✅ | （配比裁判无 stance，仅适用反思） |

**为什么说反思「地基已全局通用」**：`archive_v4.py` 的归档不分层级（`baseline` 一次性归档全部单元、`write_unit` 覆盖前留底对所有单元生效、`_conclusion()` 已兼容 stance/direction/weight/rating/vitality_level/go_nogo 全部结论字段），且「write 前落盘仍是旧版」的时序巧合对 4 个 director 同样成立。因此让行业/个股总监也读上一版、出 `reflection`，**不需要任何新基建，只是把同一段 prompt 节复制到另外 3 个 director**。C 的源冲突接地同理——任何读数角色（不止大类三专项分析师，含行业/个股层分析师）都普适。

**分阶段**：

| 阶段 | B 反思 | C 反骑墙 / 源冲突 | 说明 |
|------|--------|------------------|------|
| **本期**（随大类 equity 主线） | `v4-asset-director` | `v4-asset-director` + `v4-data-desk` + 大类三专项分析师 | 即本节 5.9.1~5.9.4 范围，先跑通验证 |
| **下一阶段**（低成本铺开） | `v4-industry-director` / `v4-stock-director` / `v4-allocation-director` | 行业/个股 director + 各层读数分析师 | prompt 措辞几乎一致、地基全通用，仅复制 reflection 节 + 反骑墙条款；reflection JSON schema 保持同构，避免各层各搞一套不一致格式 |

> 约束：下一阶段铺开时**沿用本期定稿的 `reflection` 字段结构与反骑墙措辞**，不得在行业/个股层另立格式。本说明仅定性与排期，不改动本期实现范围与其余 spec。

---

## 六、分阶段落地建议（staged，对齐 requirements 边界声明）

| 阶段 | 范围 | 交付可用点 |
|------|------|-----------|
| S1 资产层 | FR-001 穿透归类 + FR-002 大类研究部门 + 单元信封/落盘/状态机骨架（FR-004/005 机制） | 能 CLI 逐类深析、落盘、看状态 |
| S2 配比机制 | FR-003 资产配比 + equity_quota 约束下传 + Tab1 卡片 | 七大类配比可视 |
| S3 权益深链 | FR-006 行业深辩→配比→个股→行业内配比 + Tab2/3 表格 | 权益三层贯通 |
| S4 非权益 | FR-007 六类差异化方案 + Tab2 方案视图 | 全类覆盖 |
| S5 双跑/导入 | FR-009 import_v4 + 快照 + AI 代跑文件总线 + run_report_v4 | 本地/代跑一致 |

每阶段单元化天然独立可回归，不破坏 v3。

---

## 七、文件结构（新增/改动）

```
agents/advisor/
├── v4-data-desk.md                  # ★通用能力层：数据采集台（唯一带 web 工具，§5.8，新增）
└── v4-*.md                          # 14 个部门角色（§5.3，Read-only，新增）
scripts/
├── workflow-v4-advisor.js           # v4 单元调度编排器；main() 前插 ensureDataDesk 阶段（§5.8.4，新增/改动）
├── run_v4.sh                        # CLI 入口：analyze/refresh/status/scan（新增）
├── collect_v4.py                    # 退化为「持仓归类 + 拼包骨架」，联网取数交 data-desk（§5.8.5，新增/改动）
├── import_v4.py                     # 幂等 upsert 入 v4_units（新增）
├── build_snapshot_v4.py             # v4 同构静态快照（新增）
├── run_report_v4.py                 # 单元级运行报告（新增）
├── archive_v4.py                    # 单元历史归档 + 跨轮结论 diff（§5.9.2 反思地基，新增）
└── stage_cache.py                   # 复用（指纹算法）
app/
├── routers/portfolio_v4.py          # v4 只读 + 导入路由（新增）
└── services/v4/
    ├── asset_classes.py             # 7 大类常量 + TTL + 下钻深度（新增）
    ├── v4_classifier.py             # 7 大类穿透归类（扩展现有，新增）
    ├── v4_query.py                  # 三层 Tab 组装；build_asset_detail 加 debate_rounds/analysts（§5.9.1，改动）
    ├── v4_state.py                  # 状态机纯函数 + upstream 比对（新增）
    ├── v4_unit_store.py             # 单元读写/索引/锁 + 覆盖前自动留底 archive（新增）
    └── industry_candidates.py       # 内置候选行业（新增）
frontend/src/views/Portfolio/
├── Overview.vue                     # 重构为三层 Tab（改动）
└── v4/                              # AssetAllocationTab/AssetDetailTab/IndustryDetailTab
    ├── AssetCard.vue  IndustryTable.vue  StockTable.vue  PlanCard.vue
    ├── AssetDetailTab.vue           # 加大类深辩折叠块 + 「较上次」反思条（§5.9.1/5.9.2，改动）
    ├── UnitStatusBadge.vue  EmptyUnitState.vue
    └── useV4Units.ts
```

---

## 八、设计风险与权衡

| 风险 | 缓解 |
|------|------|
| 单元数量膨胀（7大类+N行业+M个股）调度复杂 | 单元化天然解耦，编排器只跑被选单元；`_units.json` 索引 + 锁防并发 |
| 非权益数据源缺失（大宗/另类） | `v4-data-desk` 联网兜底（§5.8）：取到标 verified+URL，**取不到才** evidence 标 missing 并显式提示，不静默降级、不编造 |
| 约束链跨单元一致性 | upstream 指纹 + version 比对，stale 软提醒；不自动改数值（AC5.5） |
| v3/v4 并存维护成本 | 独立集合/目录/路由/编排器，互不干扰，可灰度可回退 |
| CLI 自然语言解析歧义 | 提供等价显式脚本命令兜底（§5.2），AI 解析失败回落脚本 |
| 辩论数据已存却前端不可见（§5.9.1） | build_asset_detail 补吐 debate_rounds/analysts，前端照搬行业层折叠块；纯展示、零 LLM 重跑、API/快照同构 |
| 反思无收益接地易流于主观（§5.9.2 Layer 1） | Layer 1 仅做「跨版本自省」（引用上一版 verdict + 本轮新数据），明确登记 Layer 2 基准收益回填为后续演进；首跑标 first_run 不强造反思 |
| 反骑墙措辞矫枉过正（被迫站队）（§5.9.3） | 仅在「证据势均力敌」才允许 neutral；数据盲区表达为降 confidence + 缩幅度，而非强行站队造假 |
