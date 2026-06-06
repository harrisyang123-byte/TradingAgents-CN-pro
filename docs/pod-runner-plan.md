# 方案：把组合分析全链路搬进 Agent Pod（文件总线 + 静态前端）

> 目标：你本地**只管持仓输入**，我在 Pod 里跑分析、把结果按规范写成文件，你拉到本地、前端直接解析展示，效果和现在一致。
> 本文档是**提案**，等你拍板再动代码。我没有擅自改任何业务逻辑。

---

## 0. 一句话结论（先给态度）

你的方向**我认同**，而且我实测后发现比之前以为的更可行。但你那句「所有联网数据你都能跑」里，**混了两件本质不同的事**，必须拆开：

- **行情/市场数据采集**（北向、PE 分位、行业景气…）= 联网 + akshare → ✅ **我能跑**（待装包 + 实测接口）。
- **分析大脑**（17 个 v3 子 Agent）= `claude -p` LLM 推理 → ⚠️ **这不是"联网数据"，是烧你 Claude 额度的推理**。Pod 里 claude CLI 在（v2.1.161），但**是否已鉴权、跑一次烧多少你的额度，我不能擅自试**——这是整套方案唯一需要你点头的硬门槛。

所以方案落地与否，**不卡在网络，卡在"你是否同意我在 Pod 里用你的 Claude 额度跑分析"**。下面给三档模型，你选。

---

## 1. Pod 环境实测（这些是事实，不是假设）

| 能力 | 实测结果 | 对方案的影响 |
|---|---|---|
| outbound 联网 | ✅ 通（上一轮实测 eastmoney/AKShare 后端 HTTP 200） | 「我自己联网取行情」成立 |
| `claude` CLI | ✅ 存在 `/usr/local/bin/claude` v2.1.161 | 大脑**可能**能在 Pod 跑，但**鉴权/额度未验证** |
| `node` | ✅ v20.20.2 | 编排器 `workflow-v3-advisor.js` 能跑 |
| `python3` | ✅ 3.11.2 | OK |
| `.venv` | ❌ 不存在 | 要新建并装依赖 |
| `akshare` | ❌ 未安装 | 要 `pip install` + **逐个实测关键接口** |
| `pymongo` | ❌ 未安装 | 见下方「MongoDB 依赖比你想的深」 |
| MongoDB 实例 | ❌ Pod 里没有 | **这是你「持仓写文件」要解决的核心，但不止持仓** |

---

## 2. 关键发现：MongoDB 依赖比「只是持仓」深

你以为只要把**持仓**写成文件就行。但我读了 `scripts/collect_data.py`，它**有 5 处**直接读 MongoDB，不止持仓：

| 步骤 | 读 Mongo 的内容 | 文件化方案 |
|---|---|---|
| [1] 持仓数据 | `PortfolioService.get_portfolio_summary` | ✅ 用 `holdings.json` 替代（你本地导出） |
| [2] Tier1 报告 | `analysis_reports` / `analysis_results` 集合 | ⚠️ 用 `tier1_reports.json` 替代（你本地导出，可空） |
| [4] 敞口矩阵 | 依赖持仓 → `ExposureService` | ✅ 持仓有了就能算 |
| [7] 行业扫描池 | `get_mongo_db()` + watchlist | ⚠️ 用 `watchlist.json` 替代 + 扫描池逻辑改读文件 |
| —— | 现金/总资产也在持仓 summary 里 | ✅ 随 `holdings.json` 一起 |

**结论**：要让 collect 脱离 Mongo，得给 `collect_data.py` 加一个 **`--portfolio-file` 文件输入模式**——读 `holdings.json` / `watchlist.json` / `tier1_reports.json`（后两者可空），跳过所有 Mongo 调用。这是**中等改动**，但一次性投入，是整套方案的地基。

（备选：在 Pod 里起一个本地 MongoDB，把持仓 seed 进去，代码零改。但 Pod 无 docker，要 `pip install` + 跑 mongod，反而更重、更脏。**文件输入模式更干净，也正是你要的「文件总线」。**）

---

## 3. 前端怎么「拉下来直接解析展示」

现状：前端 `Overview.vue` → `portfolioApi.getPortfolioOverview()` → `GET /api/portfolio/overview` → **读 MongoDB `portfolio_advice` 集合**。辩论历程、资产配比、行业矩阵全走这个 API。

要做到「你拉下来、不连后端、前端直接显示」，加一个**静态快照加载模式**：

- 新增脚本 `scripts/build_snapshot.py`：把一次运行的产物（`industry_matrix.json` / `asset_allocation.json` / `final_prescription.json` / 辩论历程…）组装成**和 API 响应完全同构**的两个 JSON：
  - `overview.json`（= `GET /api/portfolio/overview` 的响应体，复用 `paper.py` 里那段矩阵组装 + `positions_detail` 注入 + 防御兜底逻辑，保证字段契约一致）
  - `advice_latest.json`（= `GET /api/portfolio/advice/latest` 的响应体）
- 前端 `paper.ts` 的 `getPortfolioOverview` / `getLatestAdvice` 加一个开关：当 `VITE_STATIC_SNAPSHOT=1` 时，直接 `fetch` 仓库里的 `frontend_snapshot/*.json`，**不走后端 API**。
- 你本地：`git pull` → `cd frontend && VITE_STATIC_SNAPSHOT=1 npm run dev` → 打开页面，效果和现在一模一样（含辩论历程的可读渲染、现金下钻、目标对账——这些上几轮已做在前端层）。

这样**你本地连 Mongo、连后端都不用起**，纯前端 + 仓库里的快照 JSON 就能看。

---

## 4. 文件管理规范（你要的「做好文件管理」）

```
data/advisor_runs/<ts>/              # 每次运行一个时间戳目录（既有约定）
├── _input/                          # 【新增】你本地提交的输入
│   ├── holdings.json                #   持仓（替代 Mongo，必填）
│   ├── watchlist.json               #   关注行业（可空 → [])
│   └── tier1_reports.json           #   个股深度分析导出（可空 → [])
├── data_portfolio.json              # collect 产物（既有）
├── data_macro.json / data_market_temp.json / data_pe.json …
├── data_vitality.json               # 全量18行业景气榜
├── industry_list.json               # 深辩范围
├── asset_allocation.json            # 大类裁判产物
├── industry_matrix.json             # synth 产物（前端矩阵来源）
├── final_prescription.json          # synth 产物（处方）
├── run_report.json / run_report.md  # 【已建】终态守卫报告：断在哪、为何空、前端会不会降级
└── _snapshot/                       # 【新增】供前端静态加载的成品
    ├── overview.json
    ├── advice_latest.json
    └── meta.json                    #   生成时间 / run ts / 数据质量评分 / 是否降级

frontend_snapshot/                   # 【新增】仓库根：指向"最新一次"快照（前端默认读这里）
├── overview.json
├── advice_latest.json
└── meta.json
```

规则：
- 每次运行产物全部沉淀在 `data/advisor_runs/<ts>/`，**不互相覆盖**，可回溯任意历史。
- `frontend_snapshot/` 只放**最新一次**的快照副本（`build_snapshot.py` 跑完自动覆盖），前端默认读这里。
- 持仓是敏感财务数据 → `holdings.json` / `_input/` 建议进 `.gitignore` 或只走私有分支，**别推公开库**（提案里我会同时给 `.gitignore` 规则）。

---

## 5. 三档模型（你选一个）

### 模型 A — 数据总线（我只当管道工，零额度风险，最稳）
- **你本地**跑 `run.sh all`（你有 Mongo + Claude 额度）→ 跑出 advice。
- 我建 `build_snapshot.py` + 前端静态加载模式。
- 你本地导出快照 → 提交 → 拉到任意机器纯前端看。
- **我不碰你额度、不跑大脑。** 缺点：分析还得你本地跑，没解决「我帮你跑」。

### 模型 B — 半搬（我跑采集 + 诊断，你跑大脑）⭐ 我倾向先走这档
- 我在 Pod 装 `.venv` + akshare；给 collect 加 `--portfolio-file` 文件输入模式。
- **我自己联网**采集真实市场数据（北向/PE/景气…）→ 产出 `data_*.json` + `run_report.md`，**我能亲眼验证数据层到底通不通、闸门有没有误杀**。
- `claude -p` 分析这步**仍由你本地跑**（规避额度问题）。
- 我建 `build_snapshot.py` + 前端静态加载。
- **价值**：彻底搞清「数据盲区」「只推历史股」到底断在采集还是分析——这正是你最近几轮的痛点根因。不烧你额度。

### 模型 C — 全搬（我全跑，真正"一个 Agent 全管"）
- 在 B 基础上，**我在 Pod 里直接跑 `claude -p` 17 个子 Agent 做完整分析**，产出快照，你拉下来即看。
- **唯一前提（硬门槛）**：① claude CLI 在 Pod 能鉴权；② **你明确同意我用你的 Claude 额度跑**（一次全链路 17 个 Agent + 多轮辩论，token 消耗不小）。
- 这才是你设想的终极形态。但额度和鉴权是你的资产，**我不点头不动**。

---

## 6. 必须诚实告诉你的三个风险（别被"能跑"冲昏头）

1. **跑通 ≠ 结果变好**。即使在 Pod 跑通全链路，也会**复现你最近痛批的那两个根因**：`synth` 风控异常就 fail-closed 吞掉 `industry_matrix`（→ 前端降级成"拿持仓拼凑"→ 永远只显示历史股）。我上一轮建的 `run_report.md` 能让它**暴露可见**，但**根治要做 Part B**（被风控拦下的处方仍写出、打 `blocked_by_risk: 不可执行` 标签，而非凭空消失）——这会动风控语义，要你单独点头。

2. **akshare「连得上 ≠ 接口都好用」**。北向资金、PE 分位是爬取型接口，可能区域限制/偶发失败。模型 B/C 第一步我会**只读实测这几个关键接口**（不装一堆包、不烧额度），通了再往下。

3. **claude 额度不可预估**。我不能替你估"一次跑多少钱"——这要看你的套餐和 token 计费。模型 C 前我会先用**一次最小的 claude 调用**探鉴权（征得你同意后），不直接跑全链路。

---

## 7. 我建议的推进顺序（每步都可独立验证、低风险优先）

1. **【共用地基，零风险】** 建 `scripts/build_snapshot.py` + 前端 `VITE_STATIC_SNAPSHOT` 静态加载模式 + `.gitignore` 持仓规则。→ A/B/C 三档都要用，先做不浪费。
2. **【模型 B 第一步，只读零额度】** Pod 装 `.venv`+akshare，**只实测**北向/PE/景气 3 个关键接口通不通。→ 决定数据层站不站得住。
3. **【给 collect 加 `--portfolio-file` 文件输入模式】** → 让采集脱离 Mongo。
4. **【你定】** 数据层通了之后，决定停在 B（你跑大脑）还是上 C（我跑大脑，需你同意烧额度）。
5. **【可选 Part B】** 改 synth 为 fail-open-labeled，根治"只显示历史股"。

---

## 8. 我需要你拍板的 3 件事

1. **选哪档模型？** A（我当管道工）/ B（我跑采集+诊断，你跑大脑，**我推荐先到这**）/ C（我全跑，含大脑）。
2. **若选 C：你同意我在 Pod 用你的 Claude 额度跑 `claude -p` 全链路吗？** 同意我才会动，且会先用一次最小调用探鉴权。
3. **要不要一并做 Part B**（让被风控拦下的处方带"禁止执行"标签露出来，根治"前端降级成只显示历史股"）？

你回我这三个，我就按第 7 节顺序开干。

---

## 9. 实施记录（B 档已落地 · 叠加式，新老两条路都跑通）

> 你已拍板 **B 档**，并要求「之前那套本地 Mongo 全量路径」与「新的文件输入路径」**都要跑通**。
> 下面是已落地的改动，全部**叠加式**——不给文件参数/不设环境开关时，行为与现在 **完全一致**。

### 9.1 改了哪些文件

| 文件 | 改动 | 对老路（Mongo 全量）的影响 |
|---|---|---|
| `scripts/build_snapshot.py` | **新增**。复用 `ingest_advice.build_doc`（纯 stdlib）产 `advice_latest.json` + `overview.json` + `meta.json`，写到 `<run>/_snapshot/` 与 `frontend/public/snapshot/` | 无（新文件） |
| `scripts/export_inputs.py` | **新增**。本地连 Mongo 导出 `holdings.json`/`watchlist.json`/`tier1_reports.json` | 无（新文件，只读 Mongo） |
| `scripts/collect_data.py` | 加 `--portfolio-file/--watchlist-file/--tier1-file` 文件输入模式 | **零影响**：不给 `--portfolio-file` 时走原 Mongo 分支（原逻辑原样移进 `else:`） |
| `frontend/src/api/paper.ts` | 加 `VITE_STATIC_SNAPSHOT` 静态加载 | **零影响**：不设该环境变量时照常走 API |
| `scripts/run.sh` | 透传文件参数 + `--snapshot` 步骤 | **零影响**：不传新参数时与原命令等价 |
| `.gitignore` | 保护 `data/_inputs/` 等敏感持仓输入 | 无 |

### 9.2 两条路怎么跑（都已验证语法/合成数据，端到端需你的真实环境）

**老路（本地 Mongo 全量，原样不变）：**
```bash
./scripts/run.sh all --user-id <24hex>        # collect(Mongo)→claude→ingest(Mongo)
```

**新路（文件总线，B 档）：**
```bash
# ① 本地（连 Mongo）导出输入
python scripts/export_inputs.py --user-id <24hex> --out-dir data/_inputs
# ② Pod/任意机（不连 Mongo）：采数（联网 akshare）+ 分析 + 出快照
./scripts/run.sh collect --portfolio-file data/_inputs/holdings.json \
    --watchlist-file data/_inputs/watchlist.json --tier1-file data/_inputs/tier1_reports.json
./scripts/run.sh analyze --data-dir data/advisor_runs/<ts> --snapshot
# ③ 本地 git pull 后纯前端查看（无需后端/Mongo）
cd frontend && VITE_STATIC_SNAPSHOT=1 npm run dev
```

### 9.3 文件契约（export_inputs 产出 ←→ collect 文件模式消费，对称）

- `holdings.json` = `{available_cash, total_assets, positions:[{code,name,weight,industry,instrument_type,...}]}`
  （`industry` 字段供文件版扫描池分组；export_inputs 会从 `paper_positions` 补齐）
- `watchlist.json` = `["半导体", ...]` 或 `[{"industry":"半导体"}, ...]`（两种都兼容）
- `tier1_reports.json` = 个股深度分析摘要 list（可空 `[]`）

### 9.4 文件模式与 Mongo 模式的差异（诚实标注）

- **基金穿透敞口**：文件模式无 Mongo 基金持仓库，降级为「仅直接个股敞口」（`data_exposure.json` 带 `note` 标注）。敞口是告警级次要信号，不阻断分析。
- **行业覆盖缓存**：文件模式无 `industry_coverage`，扫描池一律 `cached=False`（不影响深辩范围本身）。
- **数据硬闸照常生效**：宏观/水温/北向缺任一仍中止（文件模式不绕过「数据盲区不出处方」铁律）。
- **景气打分/PE/宏观/水温**：两模式**完全共用**联网采集，无差异。

### 9.5 仍未做（等你单独点头）

- **Part B（fail-open-labeled synth）**：被风控拦下的处方仍写出、打 `blocked_by_risk` 标签，而非凭空消失——根治「只显示历史股」。这会动风控语义，未做。
- **模型 C（在 Pod 跑 `claude -p` 大脑）**：B 档分析大脑仍由你本地跑，未烧你额度。
