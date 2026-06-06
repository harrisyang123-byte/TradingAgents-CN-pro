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

---

## 6. 端到端真跑发现（2026-06-06，真实数据 + 截图持仓夹具）

按 `Step0→synth` 顺序真跑了一遍（宏观/行情用 akshare 实时真数据，持仓按参考截图造 14 行业 / 60 万夹具），
落到真 `ingest_advice.py --out-json` 并逐字段比对前端 `Overview.vue` / 后端 `paper.py` overview 契约。
暴露并修复了一个**静态审查没发现、只有真跑才会触发的端到端阻断 bug**，另记录 akshare 接口漂移。
全部证据夹具留存于 `.adv_e2e/`，可用 `scripts/verify_advice_e2e.py` 复跑回归。

### 6.1 🔴 cash_floor 中止 bug（已修复）

**现象**：只要宏观裁判给了 `cash_floor > 0`（本轮=10%），`runSynth()` 在风控规则引擎处必报
`cash_floor` 违规 → 返回 `violations_found` → 整条编排在 Synthesizer 之前中止，**处方永远产不出来**。

**根因**（`tradingagents/agents/advisors/risk_rules.py::check_pm_positions` 规则4，第 91-106 行）：

```
cash_pm = next((p for p in pm_results if p.get("industry") == "现金"), None)
if cash_pm: ...校验现金权重 ≥ cash_floor...
elif cash_floor > 0:
    # 没有「现金」项 → 直接报违规「无现金行业配仓，但要求不低于 N%」
```

而 PM 阶段（`workflow-v3-pm-debate.js`）只把 **Go 行业**喂进风控引擎，**从不构造「现金」项** →
`cash_pm` 恒为 `None` → 只要 `cash_floor > 0` 必然命中 `elif` 分支报违规。这是规则引擎期望的
「现金项」与 PM 阶段实际产物之间的契约缺口，全量/增量编排都会触发。

**修复**（`scripts/workflow-v3-advisor.js::runSynth`，调风控前注入合成「现金」项）：
现金权重 = `100 − 跨行业裁判分配表(industry_allocations.json)里全部非现金行业 final_weight 之和`
（本轮 = 100 − 73.5 = 26.5%），若分配表已有「现金」行则直接取其 `final_weight`，兜底回退到 `cashFloor`。
注入后再调 `check_pm_positions`，违规归零，流水线跑到 Synthesizer 出完整处方。`node --check` 通过。

> ⚠️ 同步提醒：`.claude/workflows/workflow-v3-advisor.js` 副本需同步此修复（见 §4 改动清单第 3 项）。
> 更彻底的修法是让 PM 阶段或 synthesizer 显式落一个「现金」配仓项，本轮先在编排器侧注入兜住阻断。

### 6.2 ⚠️ akshare 接口漂移适配（沙箱 akshare 1.18.64 实测）

真查时装的 akshare **1.18.64** 与 `market_tools.py` 代码假设的列名/参数已漂移，对应函数会抛异常降级：

| 位置 | 调用 | 漂移点 | 现象 |
|---|---|---|---|
| `market_tools.py::_get_industry_rankings_cn`（~209-216 行） | `ak.stock_board_industry_name_ths()` 后 `df.nlargest(30, "涨跌幅")[[top_col,"涨跌幅","成交量"]]` | 新版该接口**不再返回「涨跌幅」「成交量」列** | `KeyError: '涨跌幅'` → 行业排名走 fallback |
| `market_tools.py::_get_sector_fund_flows_cn`（~219 行） | `ak.stock_sector_fund_flow_rank(indicator="今日", sector_type="行业资金流向")` | `sector_type` **取值已变**（"行业资金流向" 不再被接受） | `KeyError`/参数错误 → 资金流向走 fallback |

补充观察：东财（EM）系接口在沙箱内连接易被重置不稳定；同花顺（THS）行业名表、指数历史
（上证 8655 行真实历史）、sina 全市场快照（5524 只算涨跌家数=市场宽度）这三类是稳定可用的。

**建议适配**（非本轮编排器范围，记一笔待办）：
1. `_get_industry_rankings_cn`：改用东财行业接口（如 `stock_board_industry_name_em` + 实时行情）取真实涨跌幅，
   或对 THS 返回列做存在性判断（`"涨跌幅" in df.columns` 再排序），缺列则降级而非抛 `KeyError`。
2. `_get_sector_fund_flows_cn`：核对当前 akshare 版本 `stock_sector_fund_flow_rank` 的 `sector_type`
   合法取值并改用新值，同样加列/参数存在性保护。
3. 统一在 A股实现层对 akshare 列名/参数做防御式校验，避免一次接口漂移就让整段行业数据静默降级。

> 注：本机若锁的是旧版 akshare，上述函数可能仍正常；漂移仅在升级到 1.18.x 后暴露。建议在
> `requirements` 锁定 akshare 版本，或按上面做版本无关的防御式取列。

### 6.3 真跑结果对比（验证「敢不敢给指导」）

| 维度 | 截图坏状态 | 本轮真跑产出 |
|---|---|---|
| 目标% | 全 0% | 科技 13% / 黄金 8% / 债券 7% … |
| 操作 | 全「持有」 | add 8 / reduce 7 / new 1 |
| delta | 几乎全 0 | 科技 +6.6% / 黄金 +5% / QDII −5.4% / 债券 −6.2% |
| 资金 | 看不到 | 60万→投资44.1万(73.5%)+现金15.9万(26.5%) |

前端契约字段（`delta` 数字 / `go_nogo` 大写 GO/NOGO / `holdings_weight` / `target_weight` /
`vitality_level` / `market` / `codes→prescription.code` 关联 / `industry_bucket`）逐项断言通过。

> 边界诚实标注：本轮**未真写 MongoDB**（沙箱无 DB，走 `--out-json` 旁路验证字段契约，落库代码路径本身未跑）；
> 行情/宏观为真数据，持仓为按截图造的夹具。
