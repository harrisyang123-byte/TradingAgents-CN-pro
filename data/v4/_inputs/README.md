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
