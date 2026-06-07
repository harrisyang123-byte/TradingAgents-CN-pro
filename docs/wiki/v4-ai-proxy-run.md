# v4 本会话 Agent 直跑全量分析（AI 代跑落地步骤）

> 面向「把持仓交给 AI，AI 直接跑完整分析 → 存档到 `data/v4/` → 用户本地 `git pull` 后前端解析」这条路径的**可执行步骤**。
> 纠正三个常见误区，给出 agent 不依赖 `claude` CLI、不依赖本地 MongoDB、不降级数据的完整跑法。

## 0. 三个误区的纠正（先读这个）

| 误区 | 纠正 |
|------|------|
| ❌「第 2 阶段必须 `claude /login` 鉴权后才能跑」 | ✅ **`claude -p` 只是其中一种驱动方式**。`run_v4.sh` 把第 2 阶段 shell 出 `claude -p` 只是为「无人值守的本地命令行」准备的。**当前正在跟你对话的这个 AI agent 本身就是执行体**——它可以直接读输入包、按 `agents/advisor/v4-*.md` 的角色定义做部门辩论推理、再用 `v4_unit_cli.py write` 落盘。**不需要另起一个 `claude` 子进程，也不需要 CLI 鉴权。** 需要更高并行度时，agent 可用 subagent（≤3 并发）分担不同单元/角色。 |
| ❌「前端展示必须连本地 MongoDB」 | ✅ **MongoDB 不是必需**。分析结论的运行态载体是 `data/v4/**/*.json` 单元信封文件。前端有两条读法：**(A) 静态快照**——`build_snapshot_v4.py` 生成 `frontend/public/snapshot/v4/*.json`，前端设 `VITE_STATIC_SNAPSHOT=1` 直接 fetch，**完全不连后端/Mongo**；(B) 在线 API——`import_v4.py` 幂等导入 Mongo 后走 `/api/portfolio/v4/*`。**AI 代跑只需产出 JSON 存档；用户本地拉取后用 (A) 即可看，Mongo 是可选增强。** |
| ❌「数据源（AKShare/行情/宏观）取不到就降级标 missing/estimated」 | ✅ **不允许静默降级**。运行环境缺 AKShare 等依赖时，agent **必须用 `web_search` / `web_fetch` 联网补齐**关键数据（宏观指标、估值分位、价格、政策），并在 `evidence` 里标 `status:"verified"` + 注明来源 URL。**只有联网也确实取不到时**才允许标 `estimated`（注明推算依据）或 `missing`（注明已尝试的来源）。降级是最后手段，不是默认。 |

---

## 1. 数据流与产物落点

```
持仓 holdings.json
   │
   ▼  [阶段1] 纯 Python 采集（collect_v4.py）—— 脱 LLM、脱 Mongo
data/v4/inputs/{portfolio_classified, asset_<class>, plan_<class>,
                industry_<name>, stock_<code>, data_macro}.json   ← 单元输入包
   │
   ▼  [阶段2] 本会话 agent 直跑部门辩论（读输入包 + 角色定义 + 联网补数）
data/v4/{assets,plans,allocation,industries,stocks}/<unit>.json   ← 单元信封（存档）
data/v4/_units.json                                               ← 索引
   │
   ▼  git push（私有仓）→ 用户 git pull
前端解析：build_snapshot_v4.py → frontend/public/snapshot/v4/*.json（VITE_STATIC_SNAPSHOT=1，无需 Mongo）
          或 import_v4.py → Mongo → /api/portfolio/v4/*（可选）
```

单元信封 schema（`app/services/v4/v4_unit_store.py::new_envelope`）：

```json
{
  "unit_id": "asset:cash", "unit_type": "asset", "schema_version": 1,
  "version": 1, "fingerprint": "<输入包指纹>",
  "upstream": [{"unit_id": "...", "version": 1, "fingerprint": "..."}],
  "status": "green", "ttl_days": 7,
  "generated_at": "2026-06-07T..Z", "run_mode": "ai_proxy", "error": null,
  "payload": { /* 各单元类型 schema，见 workflow-v4-advisor.js */ }
}
```

---

## 2. 本会话 agent 直跑——单个单元的 4 步

以 `asset:cash`（现金大类）为例。其它单元同理，只是 payload 形状与上游不同（见 §4）。

### Step 1 — 采集输入包（纯 Python，不需要 LLM/claude/Mongo）

```bash
H=data/v4/_inputs/holdings.json
python scripts/collect_v4.py --selector asset:cash --user-id <id> --verb analyze --portfolio-file $H
# 产出 data/v4/inputs/asset_cash.json + portfolio_classified.json + data_macro.json
```

> ⚠️ 若 `data_macro.json` 的 `source=="degraded"`（环境缺 AKShare），**进入 Step 2 时必须联网补数**，不要直接拿降级值当结论。

### Step 2 — agent 直跑部门辩论（按角色定义推理 + 联网补数）

agent（本会话 / 或 spawn 的 subagent）按 `agents/advisor/v4-*.md` 定义的角色，对该单元执行：

1. **读输入包**：`data/v4/inputs/asset_cash.json`、`data_macro.json`、`portfolio_classified.json`。
2. **联网补齐缺失数据**（核心纠正点）：凡输入包里 `data_availability=="unavailable"` 或关键指标为空的，用 `web_search`/`web_fetch` 取当前值——例如：
   - 宏观：最新 LPR/逆回购利率、CPI/PMI、央行操作；
   - 现金类：货币基金 7 日年化、国债逆回购利率；
   - 权益/行业：指数 PE 分位、北向资金、行业景气新闻；
   - 个股：最新价、估值、近期公告。
   每个取到的数字写进 `evidence`：`{"claim":"7天逆回购利率1.4%","source":"http://...(央行)","status":"verified"}`。
3. **做 3 轮多空辩论 + 3 位专项分析师 + 总监拍板**（固定 3 轮，AC2.2）。可 inline 推理，或用 subagent 分担角色（≤3 并发，每个 prompt 要求 3 分钟内 ≤500 字摘要）。
4. **组装 payload**（schema 见 §4）。

> 铁律：每个量化结论必须来自真实读到/联网取到的数据；取不到才置 null 并在 reasoning 注明，**严禁编造，也不得套用 prompt 里的示例数字**。

### Step 3 — 写单元信封（覆盖式落盘，version+1）

把 Step 2 的 payload 写到临时文件，再经 CLI 落盘（自动更新 `_units.json` 索引、计算指纹、加版本号）：

```bash
# payload 已写到 /tmp/cash_payload.json
FP=$(python scripts/v4_unit_cli.py fingerprint data/v4/inputs/asset_cash.json data/v4/inputs/data_macro.json)
python scripts/v4_unit_cli.py lock 'asset:cash'
python scripts/v4_unit_cli.py write 'asset:cash' \
    --payload /tmp/cash_payload.json --fingerprint "$FP" \
    --run-mode ai_proxy --status green
python scripts/v4_unit_cli.py unlock 'asset:cash'
```

- 上游单元（如 `alloc:portfolio` 依赖 7 个 `asset:*`）用 `--upstream 'asset:equity,asset:fixed_income,...'`，CLI 会自动取各上游当前 version+fingerprint 组装 `upstream[]`（AC3.5）。
- 运行失败时 `--status red --error '<原因>'`，不污染其它单元。

### Step 4 — 校验本单元

```bash
python scripts/run_report_v4.py            # 逐单元体检：跑没跑/产物空不空/停在哪
```

---

## 3. 跑全量分析（按约束链自上而下）

```bash
H=data/v4/_inputs/holdings.json
ID=<user-id>            # 24 位 hex；AI 代跑可用占位 000000000000000000000000

# ① 七大类（含零持仓大类；每类一个 asset:<class> 单元）
for c in equity fixed_income cash commodity precious_metal real_estate alternative; do
  python scripts/collect_v4.py --selector asset:$c --user-id $ID --verb analyze --portfolio-file $H
  #  → agent 直跑该类部门辩论(§2 Step2) → v4_unit_cli.py write 'asset:'$c
done

# ② 七大类资产配比（上游=7 个 asset:*，下传 equity_quota）
python scripts/collect_v4.py --selector alloc:portfolio --user-id $ID --verb analyze --portfolio-file $H
#  → agent 直跑配置委员会 → write 'alloc:portfolio' --upstream 'asset:equity,asset:fixed_income,asset:cash,asset:commodity,asset:precious_metal,asset:real_estate,asset:alternative'

# ③ 权益深链（仅当 equity_quota>0；行业/个股由用户/推荐选定）
#    industry:<行业> → alloc:equity_industries → stock:<代码> → alloc:industry:<行业>
python scripts/collect_v4.py --selector industry:半导体 --user-id $ID --verb analyze --portfolio-file $H
#  → agent 直跑行业部门 → write 'industry:半导体' --upstream 'alloc:portfolio,asset:equity'
# ...（行业间配比、个股、行业内配比依次类推，上游见 §4）

# ④ 非权益六类差异化方案（plan:<class>）
for c in fixed_income cash commodity precious_metal real_estate alternative; do
  python scripts/collect_v4.py --selector plan:$c --user-id $ID --verb analyze --portfolio-file $H
  #  → agent 直跑 → write 'plan:'$c
done

# ⑤ 存档体检 + 生成前端静态快照（无需 Mongo）
python scripts/run_report_v4.py
python scripts/build_snapshot_v4.py        # → frontend/public/snapshot/v4/*.json

# ⑥ 提交单元产物（私有仓），用户 git pull 后即可前端解析
#    git add data/v4/  frontend/public/snapshot/v4/  &&  git commit  &&  git push
```

> 用户本地拉取后：设 `VITE_STATIC_SNAPSHOT=1` 起前端直接看（路径 A，无需后端）；或 `python scripts/import_v4.py --user-id <id>` 导入 Mongo 走在线 API（路径 B，可选）。

---

## 4. 各单元 payload schema（agent 直跑时按此组装）

权威定义在 `scripts/workflow-v4-advisor.js`；下表为速查。

| unit_id | 上游 `--upstream` | payload 关键字段 |
|---------|-------------------|------------------|
| `asset:<class>` | （无） | `asset_class, label, debate_rounds[], analysts{macro,flow,policy}, verdict{stance,situation,direction,risks,trend,confidence}, data_quality, tradable[], holding_only_exposure, current_weight, evidence[]` |
| `plan:<class>` | （无） | 同 asset + `plan{...}`：cash→`holding_structure`；fixed_income→`duration_view+instrument_mix`；commodity/precious_metal→`instrument_mix+risk_flags`；real_estate→`instrument_mix(REITs下钻/实物记敞口)+holding_only_note`；alternative→`instrument_mix+risk_flags`（类内结构占比 Σ≈100） |
| `alloc:portfolio` | 7 个 `asset:*` | `assets[{asset_class,current_weight,target_weight,action,actively_zeroed,reasoning}], equity_quota, sum_check(Σ=100), input_warnings[], summary, evidence[]` |
| `industry:<name>` | `alloc:portfolio,asset:equity` | `industry, debate_rounds[], verdict{stance,situation,direction,vitality_level,risks,allocation_advice,confidence}, data_quality, evidence[]` |
| `alloc:equity_industries` | `alloc:portfolio` + 各 `industry:*` | `equity_quota, allocations[{industry,target_weight,reasoning}], sum_weight(≤quota), cash_buffer_in_equity, input_warnings[], summary, evidence[]` |
| `stock:<code>` | `industry:<所属行业>` | `code, name, industry, rating, target_price, entry_price_range, thesis, risks[], debate_rounds[], confidence, evidence[]` |
| `alloc:industry:<name>` | `alloc:equity_industries` + 本行业各 `stock:*` | `industry, industry_target_weight, stock_weights[{code,target_weight,entry_price_range,reasoning}], sum_weight(≤行业上限), input_warnings[], evidence[]` |

---

## 5. 与 `run_v4.sh` 两种驱动方式的关系

| 驱动方式 | 谁跑第 2 阶段 | 何时用 |
|----------|---------------|--------|
| **本会话 agent 直跑（本文）** | 当前对话中的 AI（可 spawn subagent） | 把持仓交给 AI 代跑、要联网补数、不想配 claude CLI 时——**默认推荐** |
| `claude -p` 子进程 | 本地 `run_v4.sh` 自动起的 claude 子进程 | 本地已装并鉴权 claude CLI、想无人值守一条命令跑完时 |

两条路产出**同构信封**（FR-009 / NFR4.1），前端解析无差别。`run_v4.sh` 在无 `claude` 时退出码 2 并打印手动命令——此时改用本文的 agent 直跑即可，**不是阻塞**。

---

## 6. 相关文件

- 入口脚本：`scripts/run_v4.sh`（`claude -p` 驱动版）
- 采集：`scripts/collect_v4.py`（阶段 1，纯 Python）
- 编排器/角色 prompt 与 payload 权威：`scripts/workflow-v4-advisor.js`
- 单元读写 CLI：`scripts/v4_unit_cli.py`（lock/unlock/write/fingerprint/upstream）
- 存储/信封/锁：`app/services/v4/v4_unit_store.py`
- 角色定义：`agents/advisor/v4-*.md`（`.claude/agents/advisor/` 同源）
- 触发 Skill：`.claude/skills/v4-advisor/SKILL.md`
- 体检/快照/导入：`scripts/{run_report_v4,build_snapshot_v4,import_v4}.py`
- 持仓输入约定：`data/v4/_inputs/README.md`
