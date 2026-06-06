# v3 组合总揽「全持有/目标0%/无指导」根因与修复计划

> 状态：待执行 ｜ 范围：解析层（落库契约）+ 分析层（覆盖广度）｜ 一次性改完依据
>
> 本文基于代码级核对（前端 `Overview.vue`、后端 `paper.py` overview、两个落库脚本、
> `run.sh`、synthesizer 定义、workflow-v3-advisor.js）。结论：**问题分属两层，解析层是
> 当前第一现场且正在掩盖分析层的真实结论；解析修好后会立刻暴露分析覆盖不足这一更本质的问题。**

---

## 1. 症状（来自截图）

行业配置矩阵里，几乎所有行业「操作」列显示**持有**、「目标%」列显示 **0%**、「市场 / 景气」列显示 **--**，
顶部「已覆盖」只有 2。**但**部分行存在自相矛盾：

| 行业 | 现持仓→目标（权重列） | 调仓金额 | 目标%列 | 操作列 |
|------|----------------------|----------|---------|--------|
| 黄金 | 3.0% → 8.0% | 6.0 万 | 0% | 持有 |
| QDII | 18.4% → 17.1% | 有金额 | 0% | 持有 |
| 新材料 | 6.4% → 4.6% | 有金额 | 0% | 持有 |

权重列与调仓金额明明显示了「3%→8% / 调 6 万」这样的有力结论，目标%列与操作列却显示「0% / 持有」。
**说明分析确实产出了真实结论，只是被展示层吞掉了。**

---

## 2. 为什么权重列对、目标%列和操作列错（前端契约）

`frontend/src/views/Portfolio/Overview.vue`：

- **调仓金额**：`actionAmount(row) = |target_weight - holdings_weight| × total_assets / 100`，
  只依赖权重，所以**只要 holdings/target 有值就正确**——这就是黄金能显示 6 万的原因。
- **目标%列**：完全由 `row.delta` 驱动（`delta>0` 绿 / `delta<0` 红 / `else` 显示 `0%`）。
  `delta` 为 `undefined` 时永远落到 `else` → **恒显示 0%**。
- **操作列 / 行高亮**：严格判 `row.go_nogo === 'GO'` / `=== 'NOGO'`，其余一律「持有」。
  收到小写 `"Go"` → 永远「持有」。
- **市场列 / 景气列**：分别读 `row.market` / `row.vitality_level`，缺字段则 `--`。

所以前端要的契约是：每行必须带 **`delta`（数字）、`go_nogo`（大写 GO/NOGO）、`market`、`vitality_level`**。

---

## 3. 解析层根因（已定位到铁证）

后端 `app/routers/paper.py::get_portfolio_overview` 的 v3 主路径，**原样透传** advice 里的矩阵行，
既不补 `delta` 也不把 `go_nogo` 转大写。读取优先级为：

```
synthesis_result.industry_matrix  →  latest_advice.industry_matrix  →  market_intel.industries
```

因此「矩阵行长什么样」完全取决于**落库脚本写了什么**。项目里有两个落库脚本：

### 🔴 `scripts/save_v3_to_mongodb.py`（旧，run.sh 当前实际调用）

synthesizer 实际输出（见 `agents/advisor/v3-portfolio-synthesizer.md`）：
`industry_matrix.json = {"matrix": [{actual_weight, final_weight, positions, go_nogo:"Go", ...}]}`。
旧脚本与该 schema 全面错位：

1. **`_as_list` 不认 `matrix` 键** —— 只认 `prescription/items/allocations/industries`，
   读 `{"matrix":[...]}` 直接返回 `[]`，矩阵几乎读空。
2. **字段名对不上** —— 读 `holdings_weight / target_weight / codes`，
   而 synthesizer 写的是 `actual_weight / final_weight / positions`。
   → `holdings_weight` 读成 0；`codes` 读成空（处方关联不上行业）；
   `target_weight` 只能靠 `industry_allocations.json` 的 `final_weight` fallback 侥幸活下来。
3. **`go_nogo` 不转大写** —— 原样写 `"Go"`，前端判 `=== 'GO'` 永远不成立 → 全显「持有」。
4. **没有 `delta`** —— 脚本不算，schema 也没有 → 前端目标%列恒为 `0%`。
5. **展示字段不写** —— `market / vitality_level / source / lifecycle / confidence` 全缺 → 市场、景气列恒 `--`。
6. **写错挂载点** —— 写进 `market_intel.industries`，且产物 `capital_plan.json` 完全不落库。

### 🟢 `scripts/ingest_advice.py`（新，正确，但 run.sh 没接上）

这个脚本**已经把上面 6 点全部修对了**：
`actual_weight→holdings_weight`、`final_weight→target_weight`、`positions→codes`、
`_map_go_nogo("Go")→"GO"`、计算 `delta = target - holdings`、写 `market/vitality_level/lifecycle/source`、
按真实 `total_assets` 重算 `capital_plan`，并写到**顶层 `industry_matrix`**（正是后端主路径优先读的字段）。

### ✅ 解析层根因一句话

**`run.sh` 调用的是旧的 `save_v3_to_mongodb.py`，而真正正确的 `ingest_advice.py` 从未被接入。**
调用点共 2 处：
- `scripts/run.sh` `run_save()` 函数，约 **L284**
- `scripts/run.sh` `all` 分支，约 **L353**

---

## 4. 分析层根因（解析修好后会暴露）

顶部「总行业数 14 / 已覆盖 2」：14 个行业里只有 **2 个**被判 Go 并深度覆盖，其余 12 个是
holdings 透传（`target ≈ 现持仓`，如科技 6.4→6.4、债券 13.2→13.2、宽基 10.7→10.7、医药 0.6→0.6）。

成因（设计使然，非 bug）：`scripts/workflow-v3-advisor.js` 只对
`go_nogo === 'Go' && final_weight > 0` 的行业 spawn PM 做深度配仓，非 Go 行业默认透传原仓、不给观点。
对「帮用户找到全行业盈利配比」这个目标，**覆盖广度和信念强度不足**。

---

## 5. 修复计划（按次序，一次性改完）

### 阶段 A — 解析层（必须先做，否则看不清分析到底有多差）

- [ ] **A1. run.sh 切换到正确的 ingester（核心修复）**
  把 `run.sh` 两处（L284 / L353）的
  `save_v3_to_mongodb.py --dir "$RUN_DIR"`
  改为 `ingest_advice.py --data-dir "$RUN_DIR" --user-id "$USER_ID"`。
  （`$USER_ID` 在 run.sh 上下文已存在。）
- [ ] **A2. 弃用旧脚本**：`save_v3_to_mongodb.py` 顶部加弃用注释，或直接删除，避免二次踩坑。
- [ ] **A3. 后端兜底（防御性，可选但推荐）**：在 `paper.py` overview v3 主路径，
  对每行补算 `delta = target_weight - holdings_weight`（缺失时）、`go_nogo` 统一 `.upper()`，
  使「即使将来又换了上游脚本」也不至于整屏 0%/持有。

### 阶段 B — 分析层（A 完成、前端能看到真实面目后再做）

- [ ] **B1. 扩大深度覆盖**：让 synthesizer / advisor 对**所有**扫描到的行业给出明确
  超配 / 标配 / 低配判断，而非非 Go 行业一律 holdings 透传。
- [ ] **B2. 强制信念表达**：每个行业必须产出 `vitality_level` 与 `delta` 方向，
  禁止「target=现仓 + 无理由」的空透传行。
- [ ] **B3. 覆盖计数口径对齐**：顶部「已覆盖」应反映真实深度覆盖数，避免误导。

---

## 6. 验证

1. **不连库验证字段契约**（最快）：
   ```bash
   python scripts/ingest_advice.py --data-dir <某次 run_dir> --user-id <id> --out-json /tmp/doc.json
   ```
   检查 `/tmp/doc.json` 的 `industry_matrix[*]` 是否都带 `delta`、`go_nogo` 为 `GO/NOGO/""`、
   `market`/`vitality_level` 有值。
2. **端到端**：跑一次 `run.sh all`，打开组合总揽页，确认：
   - Go 行业「操作」列显示「GO 加仓 / NOGO 减仓」，行有色边；
   - 目标%列显示真实 `+x% / -x%` 而非 0%；
   - 市场、景气列不再是 `--`；
   - 黄金这类行 3%→8% 与目标%、操作三者**一致**。
3. 阶段 B 完成后复看：深度覆盖行业数应 > 2，非 Go 行业也带明确判断。

---

## 7. 结论

- **表层（全持有 / 0% / 无指导）= 解析问题主导**，且严重到掩盖了真实分析结论（黄金 3→8 被显示成「持有」是铁证）。
  根因不是「4 处字段散修」，而是**run.sh 接错了落库脚本**——正确脚本 `ingest_advice.py` 已存在，改 2 行调用即可。
- **里层（修好解析后暴露）= 分析覆盖不足**：14 中仅深覆盖 2，多数行业默认透传无观点。
- **次序固定：先 A 后 B。** A 是一次性低风险改动；B 是迭代增强分析质量。
