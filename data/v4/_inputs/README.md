# v4 持仓输入约定（git 文件总线入口）

这是 **v4 双跑文件总线的「输入端」**。你在本地把持仓放进这里、`git push` 到**私有仓库**，
AI 代跑环境 `git pull` 后即可读取它跑全量分析；产物（单元 JSON）再经 git 回传到你本地展示。

```
本地: 编辑 data/v4/_inputs/holdings.json ──git push──▶ 私有仓
                                                          │ git pull
                                          AI 代跑: ./run_v4.sh analyze <unit> --portfolio-file data/v4/_inputs/holdings.json
                                                          │ 产出 data/v4/{assets,allocation,industries,stocks,plans}/*.json + _units.json
本地: git pull ◀──git push (AI 提交单元产物)──────────────┘
      python scripts/import_v4.py --user-id <id>   # 幂等导入 Mongo，前端三层 Tab 即与代跑一致
```

> ⚠️ **隐私铁律**：`holdings.json` 含真实财务数据，`data/v4/` 子树只在**私有仓库 / 私有分支**使用。
> 仓库其它位置的 `holdings.json`（如根目录、`data/_inputs/`）仍被 `.gitignore` 忽略，**只有 `data/v4/_inputs/holdings.json` 这一条路径被显式追踪**。

## 文件位置

| 文件 | 是否追踪 | 用途 |
|------|----------|------|
| `data/v4/_inputs/holdings.example.json` | ✅ 模板（不含真实数据） | 复制它当起点 |
| `data/v4/_inputs/holdings.json` | ✅ 你推送的真实持仓 | AI 代跑读取的输入 |

```bash
cp data/v4/_inputs/holdings.example.json data/v4/_inputs/holdings.json
# 编辑 holdings.json 填入真实持仓，然后
git add data/v4/_inputs/holdings.json && git commit -m "chore: update v4 holdings" && git push
```

## 格式

顶层是 `{"positions": [...]}`（也兼容直接传数组 `[...]`，或用 `holdings` 代替 `positions` 作为键名）。
每条持仓字段：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `code` | string | 否 | 市场代码（A股 `600519` / 港股 `00700` / 美股 `AAPL` / 基金/ETF/REIT 代码）。现金、实物房产等无市场代码的敞口留空 `""` |
| `name` | string | ✅ | 名称。**归类主依据**——名称里的关键词（如「黄金」「国债」「货币」「REIT」「比特币」）决定落到哪个大类 |
| `weight` | number | 否 | 占组合百分比（如 `15` 表示 15%）。可只填 `market_value`，由系统算占比 |
| `market_value` | number | 否 | 市值（本币）。`weight` 与 `market_value` 至少填一个 |
| `instrument_type` | string | 否 | 工具类型，名称未命中关键词时的兜底归类依据：`stock` / `etf` / `fund` / `bond` / `cash` / `other` |

### 七大类穿透归类（`instrument_type` 兜底规则）

名称关键词优先；未命中再按 `instrument_type` 兜底：

| `instrument_type` | 兜底归入 |
|-------------------|----------|
| `bond` | 固定收益 fixed_income |
| `cash` | 现金及等价物 cash |
| `stock` / `etf` | 权益 equity |
| `fund` | 权益 equity（股票型/混合；名称命中「货币/债/黄金/商品/REIT」则改归对应类） |
| `other` / 其它 | 先按名称关键词；仍无法判定 → `unclassified`（不丢弃，标「待人工归类」） |

七大类：`equity`(权益) / `fixed_income`(固定收益) / `cash`(现金及等价物) / `commodity`(大宗商品) / `precious_metal`(贵金属) / `real_estate`(房地产) / `alternative`(另类)。
零持仓的大类也能分析（判断是否值得择机配置），不会报错。

### 最小示例

```json
{
  "positions": [
    {"code": "600519", "name": "贵州茅台", "weight": 15, "market_value": 150000, "instrument_type": "stock"},
    {"code": "511990", "name": "华宝添益货币ETF", "weight": 12, "market_value": 120000, "instrument_type": "fund"},
    {"code": "", "name": "活期存款", "weight": 7, "market_value": 70000, "instrument_type": "cash"}
  ]
}
```

## 基金穿透字段 `_fund_passthrough`（2026-06-13 加，可选但**强烈推荐**）

> **为什么需要**：基金本质是股票/债券组合，不穿透到底层就无法算清楚行业暴露/重叠/风格。沙箱无外网取不到 AKShare 真数据，**用户本地填充是最可靠的来源**（从天天基金/雪球/招商证券/基金季报 PDF 任一渠道）。

**基金 / ETF 持仓 →加可选字段** `_fund_passthrough`：

```json
{
  "code": "270042",
  "name": "广发纳指100ETF联接（QDII）人民币A",
  "market_value": 20438,
  "instrument_type": "fund",
  "weight": 1.94,

  "_fund_passthrough": {
    "as_of": "2025-12-31",                ← 季报披露日 (3/31, 6/30, 9/30, 12/31 末)
    "fund_type": "ETF联接·QDII·权益",      ← 类型: 股票型/混合型/债券型/货币型/QDII/REIT/商品型/...
    "fund_company": "广发基金",
    "asset_size_yi": 28.5,                 ← 规模(亿元), 不知道留 null
    "management_fee_pct": 0.50,            ← 管理费率 % (年)
    "benchmark": "纳斯达克100指数",         ← 业绩比较基准
    "stock_position_pct": 95.0,            ← 股票仓位 % (相对净值, 季报披露)
    "bond_position_pct": 0,
    "cash_position_pct": 5.0,
    "top_holdings": [                      ← 前 10 重仓 (核心数据! 行业聚合靠这个)
      {"code": "AAPL", "name": "苹果", "market": "US", "weight": 8.5, "industry": "消费电子"},
      {"code": "MSFT", "name": "微软", "market": "US", "weight": 7.8, "industry": "软件"},
      ...
    ],
    "industry_exposure": {                 ← 行业暴露 % (核心! 行业页"间接持仓"靠这个)
      "信息技术": 50.0,
      "通信服务": 15.0,
      "可选消费": 14.0,
      ...
    },
    "region_exposure": {                   ← QDII 加这个 (中国/美国/全球) ; A 股基金可省
      "美国": 95.0
    },
    "style": {                             ← 风格 (Level 2 用; Level 1 占位)
      "size": "大盘",                       ← 大盘/中盘/小盘
      "growth_value": "成长"                 ← 成长/价值/平衡
    },
    "_data_source": "易方达官网 2025 年 4 季报 / 天天基金 / 雪球",
    "_data_status": "verified"             ← verified / estimated / partial
  }
}
```

### 字段说明（按 v4-data-desk.md 协议）

| 字段 | 必填 | 说明 |
|---|---|---|
| `as_of` | **必填** | 季报披露日，越新越好（A 股季报 4/8/10 月披露，QDII 时滞略大）|
| `fund_type` | **必填** | 用于 classifier 大类归属判断（QDII 归 equity_overseas，债基归 fixed_income，黄金 ETF 归 precious_metal） |
| `top_holdings` | **核心**（无则降级）| 前 10 重仓股，**行业聚合的主要数据源** |
| `industry_exposure` | **核心**（无则降级）| 行业暴露 %，**行业页"间接持仓"的数据源** |
| `region_exposure` | QDII 必填 | 海外/A 股/港股区域暴露，影响大类归类 |
| `style` | 可选 | Level 2 风格因子分析用 |
| `_data_source` | 推荐 | 数据来源（用于追溯 + 多源冲突标记） |
| `_data_status` | 推荐 | verified（季报确认）/ estimated（招商等第三方推算）/ partial（只填了部分） |

### 取数渠道（推荐优先级）

1. **基金公司官网季报 PDF**：最权威，但 PDF 解析麻烦
2. **天天基金 → 基金详情 → 重仓股/行业分布**：体验好，但数据时滞 1-2 季度
3. **雪球 → 基金详情**：含历史持仓变化曲线
4. **招商证券 / 各券商 App → 基金诊断报告**：含风格因子分析（Level 2）
5. **AKShare 程序化取数**（生产环境）：`python scripts/v4_fund_source.py 270042`，沙箱不可用

### 不填会怎样

- `_fund_passthrough` 缺失 → fund_source.py 写 `data_status: "manual_required"` 占位 → 行业页该基金"间接持仓 ¥0 (待填)" → **不影响其他基金/股票分析**
- 部分填（只填 top_holdings 不填 industry_exposure）→ aggregator 用 top_holdings 反推行业（精度低，标 estimated）

## 跑全量分析（拿到 holdings.json 之后）

按约束链自上而下依序触发单元（每次只跑命中单元，不连带重跑其它）：

```bash
H=data/v4/_inputs/holdings.json
# 1) 七大类（含零持仓大类）
for c in equity fixed_income cash commodity precious_metal real_estate alternative; do
  ./scripts/run_v4.sh analyze asset:$c --user-id <id> --portfolio-file $H
done
# 2) 七大类资产配比（下传 equity_quota）
./scripts/run_v4.sh analyze alloc:portfolio --user-id <id> --portfolio-file $H
# 3) 权益深链：行业深辩 → 行业间配比 → 个股 → 行业内配比
./scripts/run_v4.sh analyze industry:<行业名> --user-id <id> --portfolio-file $H
./scripts/run_v4.sh analyze alloc:equity_industries --user-id <id> --portfolio-file $H
./scripts/run_v4.sh analyze stock:<代码> --user-id <id> --portfolio-file $H
# 4) 非权益六类差异化方案
for c in fixed_income cash commodity precious_metal real_estate alternative; do
  ./scripts/run_v4.sh analyze plan:$c --user-id <id> --portfolio-file $H
done
# 5) 回传产物后本地导入 + 体检
python scripts/import_v4.py --user-id <id>
python scripts/run_report_v4.py            # 逐单元体检：跑没跑/产物空不空/停在哪
python scripts/build_snapshot_v4.py        # （可选）生成前端静态快照
```

`run_v4.sh` 第 2 阶段（Agent 推理）有两种驱动：**① 本会话 AI agent 直跑**（默认，无需 `claude` CLI，缺数据源联网补齐而非降级，产物存 `data/v4/` 单元 JSON，前端走静态快照、MongoDB 可选）；**② `claude -p` 子进程**（需 claude 鉴权）。无 claude 时第 1 阶段（采集输入包）仍完成、退出码 2 不是阻塞——改走方式 ①。完整步骤见 `docs/wiki/v4-ai-proxy-run.md`。


## 个股数据契约（D0-8 用户"缺数据接着查"指令落地，2026-06-13）

`collect_v4.py` 跑 `stock:<code>` 时会调 `app/services/v4/stock_data_contract.py` 自动校验 18 MUST 字段 + 10 SHOULD 字段，缺关键字段直接 **exit=4 阻断**，输出**精确的取数任务**让主 agent web_search 补齐。

### MUST 字段（18 个，缺一就阻断）

**财务硬数据 8**：最近年度营收 / 净利 / 毛利率 / 净利率 / ROE / 经营现金流 / 当前股价 / 总市值
**业务结构 6**：主营业务 / 分部营收占比 / 分地区营收占比 / 前 5 大客户占比 / 同业清单 / 行业规模 CAGR
**估值锚 4**：PE-TTM / PE 历史中枢分位 / 同业 PE 对比 / 卖方一致 EPS 未来 2 年

### SHOULD 字段（10 个，缺降 confidence 不阻断）

最近季度营收/净利、应收周转、存货周转、D/E、总股本、近期股东变动、沽空比例/融资余额、北上资金、卖方目标价

### 工作流

```
collect_v4.py stock:<code>
  ↓
1. 调 stock_source.py (AKShare 取硬数据)
  ↓
2. 调 stock_data_contract.check_data_contract(pack)
  ↓
3a. 契约通过 → 写 inputs/stock_<code>.json，exit 0，可进 spawn analysts
3b. 契约不通过 → 输出 fetch_tasks(每条含 search_query+source_hints+usage)
                 exit=4 阻断，主 agent 必须真去 web_search 补齐字段
                 → 回填到 inputs/stock_<code>.json
                 → 重跑 collect_v4 直至契约通过

最终 inputs/stock_<code>.json 含 data_contract_check + data_contract_instructions
让主 agent 透明看到取数审计
```

### 真取不到的字段处理

- 沙箱无外网 → 标 `unattainable: 沙箱限制` + 给替代假设区间（行业平均/同业代理）
- 公司未披露（如客户精确占比）→ 标 `unattainable: 公司未披露` + 引用行业研报估算
- 付费数据（Bloomberg consensus）→ 标 `unattainable: 数据收费` + 用免费源代理（stockanalysis）

critic 6.8 必查：装作"已查"实际数据没动 = fatal_flaw。
