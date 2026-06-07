# Tasks: v4 大类辩论展示 + 结果闭环反思 + 反骑墙措辞

> 变更：`v4-debate-display-and-reflection`
> 执行模式：staged（叠加在 `v4-layered-deep-research` + `v4-shared-data-desk` 之上；不改单元信封外壳/状态机/约束链/v3）
> 权威设计：`.kiro/specs/v4/design.md §5.9`。借鉴：TauricResearch/TradingAgents。
> 进度：详细设计已落地；A/B/C 代码与 prompt 改动逐步实施，prompt/reflection 运行时行为需部署机端到端验证。

---

## Task 1 — 文档与方案定稿 ✅

- [x] `.kiro/specs/v4/design.md §5.9`：新增详细设计（A 展示管线 4 处改动表 / B-Layer1 reflection 字段 + 时序巧合 / C 反骑墙 + 源冲突）
- [x] `.kiro/specs/v4/design.md §七`：文件结构加 `archive_v4.py`、`v4_query.py`、`AssetDetailTab.vue` 改动注
- [x] `.kiro/specs/v4/design.md §八`：风险表加 3 条（辩论可见 / 反思主观 / 反骑墙矫枉）

**capability**：v4-result-reflection（设计）, v4-three-tab-overview（展示修订）, v4-asset-research-dept（措辞修订）

---

## Task 2 — A 大类辩论展示（后端查询补吐） ⬜

- [ ] `app/services/v4/v4_query.py` `build_asset_detail`：响应加 `debate_rounds`（`payload.debate_rounds`，默认 `[]`）+ `analysts`（`payload.analysts`，默认 `{}`）
- [ ] 确认 `portfolio_v4` 路由与 `build_snapshot_v4` 共用此函数 → API/快照同步生效（NFR4.1）
- [ ] 重生成快照：`python scripts/build_snapshot_v4.py`（逻辑不变，仅让快照带新字段）

**capability**：v4-three-tab-overview
**验证**：`python3 -m py_compile app/services/v4/v4_query.py`；`build_asset_detail` 对 `asset:equity` 返回含 3 轮 debate_rounds；快照 `snapshot/v4/asset_equity.json` 带 debate_rounds。

---

## Task 3 — A 大类辩论展示（前端类型 + 折叠块） ⬜

- [ ] `frontend/src/api/portfolioV4.ts`：`AssetDetail` 加 `debate_rounds: DebateRound[]` + `analysts?: Record<string, any>`；`AssetVerdict` 加 `reflection?`
- [ ] `frontend/src/views/Portfolio/v4/AssetDetailTab.vue`：插「大类深辩历程（N 轮）」`el-collapse` 折叠块（照搬 `IndustryDetailTab.vue` 的 `idt-debate` 多空对栏 + `extractText(side)`）
- [ ] （可选）追加「宏观/资金/政策三视角」小卡渲染 `analysts`

**capability**：v4-three-tab-overview
**验证**：前端 `npm run build`（或 `vue-tsc`）类型通过；`VITE_STATIC_SNAPSHOT=1` 下点权益卡 → 大类详情见多空 3 轮对栏。

---

## Task 4 — B 结果闭环反思（director prompt + schema） ⬜

- [ ] `agents/advisor/v4-asset-director.md`：加「记忆/反思」节——开辩前 `Read` 落盘的 `data/v4/assets/{asset_class}.json`（write 前时序，仍是上一版）取上次 verdict
- [ ] verdict 输出 schema 加 `reflection{prev_stance,prev_date,what_changed,why_changed,self_check}`；无历史时 `self_check:"first_run"`、各字段允许 null
- [ ] `AssetDetailTab.vue`：verdict 区下方加「较上次 / 自检」反思条（`detail.verdict.reflection` 存在且非 first_run 才显示）

**capability**：v4-result-reflection
**验证**：`node --check`（无 JS 改）/ prompt frontmatter 合法；部署机重跑 `asset:equity` → v2 verdict 带 reflection 引用 v1 stance；前端显示「较上次」条。

---

## Task 5 — C 反骑墙 + 源冲突接地（prompt 措辞） ⬜

- [ ] `agents/advisor/v4-asset-director.md`：替换铁律 2「数据盲区→neutral/hold」为「仅证据势均力敌才 neutral/hold；否则必须站队 + 说明采信/压低哪方；盲区降 confidence + 缩幅度」
- [ ] `agents/advisor/v4-data-desk.md` + bull/bear/三专项分析师：加「多源冲突标记分歧（列各源值 + 采用值 + 理由），不私自调和」
- [ ]（可选）bull/bear 加「第 2 轮起必须点名回应对方上一轮具体论点」

**capability**：v4-asset-research-dept
**验证**：prompt 文本一致性复核（与 design §5.9.3 / §5.8 凭据契约不冲突）；部署机重跑确认 equity 不再无脑 neutral、源冲突在 evidence 标记。

---

## Task 6 — 验证与一致性 ⬜

- [ ] `py_compile app/services/v4/v4_query.py`；前端 `npm run build` 类型通过；`node --check scripts/build_snapshot_v4.py`
- [ ] 部署机（claude 鉴权）端到端：重跑 `asset:equity` → reflection（v2 引用 v1）+ 不无脑骑墙 + 源冲突标记
- [ ] 文档与代码一致性复核（design §5.9 ↔ build_asset_detail 字段 ↔ director reflection schema ↔ 前端渲染）

**capability**：v4-result-reflection, v4-three-tab-overview, v4-asset-research-dept

---

## 执行顺序

```
Task 1 ✅（文档）→ Task 2 ⬜（后端补吐）→ Task 3 ⬜（前端折叠块）
  → Task 4 ⬜（reflection）→ Task 5 ⬜（反骑墙/源冲突）→ Task 6 ⬜（验证）
```

A（Task 2/3）改完即可前端验证看到辩论；B/C（Task 4/5）需重跑一次 asset:<class> 才出 reflection、走「跑一个→讲一个→验一个→提交一个」节奏。

## 验证策略（沙箱约束）

沙箱无 claude 鉴权 / web 工具。A 展示改动用 `py_compile`（后端）+ 前端构建/类型（`vue-tsc`）静态验证，重生成快照即可前端看辩论；B/C 的 reflection 与反骑墙运行时行为由部署机重跑承担，沙箱仅静态验证 prompt/schema 一致性。
