# v3 增量编排器落地计划

> 状态：进行中（方案 A 已拍板）
> 最近更新：2026-06-06

本文件固化讨论结论，防止上下文遗忘。落地范围 = **v3 三段增量编排器 + run.sh 切换**。ingest 与前端是后续阶段，本轮不做。

---

## 1. 背景与问题

最初设想是 "Step0→7 一条命令跑完"（宏观→并行行业研究→跨行业裁判→PM辩论→风控规则→Risk Director→Synthesizer）。
实际诉求是：**Agent 调用要能分阶段、增量执行，不要每次都把全部重跑一遍**——尤其是最贵的并行行业研究。

### 摸排到的真实现状（与早先表述有出入）

1. **真正入口是 `scripts/run.sh`**：`collect_data.py` → `workflow-advisor.js`（**旧 L1-L4 / 9-Agent**，step1~9）→ `save_to_mongodb.py`。
2. `run.sh` / `workflow-advisor.js` 里现有的 `--from / --only` 控制的是**旧的 9 个 step**，不是 v3 Step0-7。
3. **v3 Step0-7 的三个脚本没接进 run.sh**，目前各自单独 `claude -p "Run workflow"` 手动跑，靠 `dataDir` 文件交接。v3 此前**没有编排器、没有缓存跳过**。
4. 每个 workflow 在 `scripts/` 和 `.claude/workflows/` 各有一份副本（Workflow 工具从 `.claude/workflows/` 加载），改动两份都要同步。

### v3 三脚本的产物交接链

| 脚本 | 覆盖 | 关键产物 |
|---|---|---|
| `workflow-v3-industry-layer.js` | Step0-2 | `macro_verdict.json` / `researcher_*.json` / `contrarian_*.json` / `all_researchers.json` / `industry_allocations.json` |
| `workflow-v3-pm-debate.js` | Step4 | `candidates_*.json` / `aggressive_pm_*.json` / `conservative_pm_*.json` / `pm_results.json` |
| `workflow-v3-synthesizer.js` | Step5-7 | `risk_violations.json` / `pessimist_risk.json` / `optimist_risk.json` / `risk_assessment.json` / `industry_matrix.json` / `final_prescription.json` |

---

## 2. 核心设计：分阶段 + 缓存门

把 v3 拆成 **4 个缓存单元**，每个产物旁写一个 `<output>.meta.json`（时间戳 + TTL + 输入指纹）。

| 阶段 stage | 脚本 | 主产物 | TTL | 指纹输入 | 触发频率 |
|---|---|---|---|---|---|
| `macro` (Step0) | industry-layer | `macro_verdict.json` | 1 天 | `data_macro.json` + `data_market_temp.json` | 每天可刷 |
| `industry` (Step1-2) | industry-layer | `industry_allocations.json` | **7 天** | `macro_verdict.json` + `industry_list.json`（**不含持仓**） | 景气没变就别动（最贵） |
| `pm` (Step4) | pm-debate | `pm_results.json` | **不缓存** | `industry_allocations.json` + 持仓指纹 | 持仓/现金一变就重跑 |
| `synth` (Step5-7) | synthesizer | `final_prescription.json` | **不缓存** | `pm_results.json` + 持仓/现金指纹 | 同上 |

### 已认可的两点设计决策

1. **TTL**：行业研究/Tier1 = 7 天，宏观 = 1 天，PM 及之后不缓存。
2. **持仓自动失效**：持仓/现金变化时 `pm`→`synth` 自动失效重跑（指纹包含持仓快照）。

### 关键洞察（为什么分阶段值钱）

- `industry` 指纹**不含持仓** → 改现金/持仓时 7 天缓存命中、跳过，最贵的并行行业研究**完全不动**。
- 只重跑 `pm`→`synth`（便宜），**秒级到分钟级**出新配比。
- 反例：每次全量 = 改一次现金就把 N 个行业深度研究重跑，又慢又烧 token。

### 执行逻辑

- **默认增量**：逐阶段先验缓存（在 TTL 内 **且** 指纹未变）→ 命中即跳过。
- **下游强制重跑**：只要某阶段真跑了（未命中/被刷新），其**所有下游阶段强制重跑**（输入已变）。
- 阶段顺序：`macro` → `industry` → `pm` → `synth`。

---

## 3. CLI 设计

stage 取值：`macro | industry | pm | synth`。

| 参数 | 语义 |
|---|---|
| （默认） | 增量：跑缓存失效的阶段 + 其全部下游 |
| `--from <stage>` | 从该阶段强制重跑到结尾（断点续跑） |
| `--only <stage>` | 只跑该阶段（调试） |
| `--refresh <stage>` | 强制让该阶段失效并重跑 + 下游 |
| `--refresh industry:<行业名>` | 只刷某个行业的研究产物，再重跑 industry 裁判 + 下游 |
| `--full` | 忽略全部缓存，从头全跑 |

---

## 4. 改动清单（方案 A）

本轮只做编排器，不碰 ingest/前端。

1. **新建 `scripts/stage_cache.py`**：指纹（sha256 输入文件）/meta 读写、新鲜度判定。供编排器通过 `Bash` 调用，返回 `FRESH` / `STALE`。
2. **新建 `scripts/workflow-v3-advisor.js`**：三段增量编排器，按 stage 顺序调用三个 v3 子流程，每段前查缓存门，支持 `from/only/refresh/full`。
3. **同步 `.claude/workflows/workflow-v3-advisor.js`** 副本。
4. **改 `run.sh`**：
   - `VALID_STEPS` 词表换成 v3 四段 `macro/industry/pm/synth`；
   - 透传 `--refresh` / `--full`；
   - 入口（`all` / `analyze`）的 `claude -p` 指向 `workflow-v3-advisor.js`；
   - 保存环节读 `final_prescription.json`。
5. **校验 `save_to_mongodb.py` / `collect_data.py`** 与 v3 产物对齐，必要时适配。
6. **旧 9-Agent `workflow-advisor.js` 保留不动**（回退用），run.sh 默认不再走它。
7. 语法/字节码校验：`node --check`、`python -m py_compile`。

---

## 5. 后续阶段（本轮不做，备忘）

- **ingest**：把 v3 产物（`final_prescription.json` / `industry_matrix.json`）写入 MongoDB `portfolio_advice`，与前端读取对齐。
- **前端**：`Overview.vue` 行业矩阵读 `advice.industry_matrix`。
- **持仓快照指纹**：已纳入本轮（`pm`/`synth` 指纹含持仓），后续可扩展到自动检测触发重跑。
