---
name: v4-advisor
description: "v4 分层投研系统触发器：识别用户自然语言中的分析意图，映射为 run_v4.sh 命令并执行。当用户说「分析<大类/行业/个股>」「跑 v4」「刷新<单元>」「v4 状态」等时触发。"
tools: ["Read", "Bash", "Grep"]
---

# v4-advisor — 分层投研系统 AI 触发 Skill

## 职责

当用户在对话中表达 v4 分析意图时，将自然语言映射为 `scripts/run_v4.sh` 命令并在本地执行。

## 前置约定

- 持仓文件固定路径：`data/v4/_inputs/holdings.json`
- 脚本入口：`./scripts/run_v4.sh`
- user-id 默认使用环境变量 `V4_USER_ID`，未设则用 `000000000000000000000000`（24 位 hex）
- 产物目录：`data/v4/{assets,allocation,industries,stocks,plans}/`

## 意图识别 → 命令映射表

| 用户说（自然语言） | 映射 unit-selector | 执行命令 |
|---|---|---|
| `分析权益` / `跑权益大类` / `analyze equity` | `asset:equity` | `run_v4.sh analyze asset:equity` |
| `分析固收` / `分析债券` | `asset:fixed_income` | `run_v4.sh analyze asset:fixed_income` |
| `分析现金` | `asset:cash` | `run_v4.sh analyze asset:cash` |
| `分析大宗` / `分析商品` | `asset:commodity` | `run_v4.sh analyze asset:commodity` |
| `分析贵金属` / `分析黄金` | `asset:precious_metal` | `run_v4.sh analyze asset:precious_metal` |
| `分析房地产` / `分析 REIT` | `asset:real_estate` | `run_v4.sh analyze asset:real_estate` |
| `分析另类` / `分析虚拟币` / `分析比特币` | `asset:alternative` | `run_v4.sh analyze asset:alternative` |
| `跑资产配比` / `配比` / `资产配置` | `alloc:portfolio` | `run_v4.sh analyze alloc:portfolio` |
| `分析<行业名>行业` / `深辩<行业名>` | `industry:<行业名>` | `run_v4.sh analyze industry:<行业名>` |
| `行业配比` / `权益行业间配比` | `alloc:equity_industries` | `run_v4.sh analyze alloc:equity_industries` |
| `分析<代码>` / `分析<股票名>` | `stock:<代码>` | `run_v4.sh analyze stock:<代码>` |
| `行业内配比 <行业名>` | `alloc:industry:<行业名>` | `run_v4.sh analyze alloc:industry:<行业名>` |
| `非权益方案 <大类>` / `<大类>投资方案` | `plan:<class>` | `run_v4.sh analyze plan:<class>` |
| `刷新<任意单元>` / `refresh <unit>` | 同上，换命令 | `run_v4.sh refresh <unit-selector>` |
| `v4 状态` / `单元状态` / `看看哪些过期` | — | `run_v4.sh status --json` |
| `v4 扫描` / `扫描过期` | — | `run_v4.sh scan --json` |
| `跑全量 v4` / `v4 全量分析` / `全部分析` | 七大类+配比+非权益方案 | 见「全量分析序列」 |
| `导入 v4` / `import` | — | `python scripts/import_v4.py --user-id <id>` |
| `v4 报告` / `体检` | — | `python scripts/run_report_v4.py` |
| `v4 快照` | — | `python scripts/build_snapshot_v4.py` |
| `我的持仓是…` / `更新持仓` / `录入持仓` / `update holdings` | — | 解析内容 → 写入 `data/v4/_inputs/holdings.json`（见「持仓录入」） |
| `加一笔 XX` / `新买了 XX` / `增加持仓` | — | 追加到 holdings.json |
| `卖了 XX` / `清仓 XX` / `删掉 XX` | — | 从 holdings.json 移除 |
| `看看我的持仓` / `当前持仓` | — | 读取并展示 holdings.json |

### 七大类 class 名称映射

| 中文 | class 值 |
|------|----------|
| 权益 / 股票 | `equity` |
| 固收 / 债券 / 固定收益 | `fixed_income` |
| 现金 | `cash` |
| 大宗 / 商品 / 大宗商品 | `commodity` |
| 贵金属 / 黄金 / 白银 | `precious_metal` |
| 房地产 / REIT | `real_estate` |
| 另类 / 虚拟币 / 比特币 / 加密 | `alternative` |

## 持仓录入 / 更新意图

当用户说「我的持仓是…」「更新持仓」「帮我录入账户」「这是我最新的持仓」等（不是要求分析），执行以下流程：

### 识别触发词

| 用户说 | 动作 |
|--------|------|
| `我的持仓是…` / `帮我录入持仓` / `更新我的持仓` / `update holdings` | 写入/覆盖 holdings.json |
| `加一笔 XXX` / `新买了 XXX` / `增加持仓` | 追加到现有 holdings.json |
| `卖了 XXX` / `清仓 XXX` / `删掉 XXX` | 从 holdings.json 移除对应条目 |
| `看看我的持仓` / `当前持仓是什么` | 读取并展示 holdings.json |

### 执行步骤

1. **解析用户口述内容**为结构化持仓条目，每条需包含：
   - `name`（必填）— 名称，是归类主依据
   - `code`（尽量填）— 市场代码。A 股 6 位数字、港股 5 位、美股字母、基金/ETF 6 位。无代码的（现金/房产）留 `""`
   - `market_value` 或 `weight`（至少一个）— 市值或占比
   - `instrument_type`（尽量填）— `stock`/`etf`/`fund`/`bond`/`cash`/`other`

2. **信息不足时追问**（不猜测）：
   - 用户只说了名字没说金额 → 追问「市值大约多少？或占组合百分比？」
   - 代码不确定（如基金名不唯一）→ 列出候选让用户确认
   - 工具类型模糊 → 根据名称关键词推断，推断不了就问

3. **写入文件**：
   ```bash
   # 路径固定
   FILE=data/v4/_inputs/holdings.json
   ```
   - 全量录入 → 覆盖整个文件（保留 JSON 格式、不含 `_comment`）
   - 追加/删除 → 先读取现有文件 → 修改 positions 数组 → 写回
   - 写入后展示最终内容让用户确认

4. **写入后提示下一步**：
   ```
   ✅ 持仓已写入 data/v4/_inputs/holdings.json（共 N 笔）
   
   下一步可以：
   • 说「分析权益」开始跑权益大类深度分析
   • 说「跑全量 v4」一次跑完七大类 + 资产配比
   • 或 git push 到私有仓库让 AI 代跑
   ```

### 格式参考

```json
{
  "positions": [
    {"code": "600519", "name": "贵州茅台", "weight": 15, "market_value": 150000, "instrument_type": "stock"},
    {"code": "", "name": "活期存款", "weight": 7, "market_value": 70000, "instrument_type": "cash"}
  ]
}
```

### 约束

- 🚫 **不猜测代码** — 用户说「茅台」→ 代码填 `600519`（确定的才填，不确定就问）
- 🚫 **不丢弃条目** — 用户说了就必须写进去，即使你觉得奇怪也只是提醒、不删
- 🚫 **不自动触发分析** — 写完持仓只提示可选下一步，不自己开始跑分析
- ✅ **覆盖式写入安全** — 全量录入前告知用户「将覆盖现有持仓文件」并展示新内容，用户确认后写
- ✅ **隐私提醒** — 首次写入时提醒：「此文件含财务数据，请只在私有仓库使用」

---

## 分析触发流程

### Step 1: 确认前置条件

```bash
# 检查持仓文件
test -f data/v4/_inputs/holdings.json || { echo "⚠️ 未找到持仓文件 data/v4/_inputs/holdings.json"; echo "请先 cp data/v4/_inputs/holdings.example.json data/v4/_inputs/holdings.json 并编辑填入真实持仓"; exit 1; }

# 检查脚本可执行
test -x scripts/run_v4.sh || chmod +x scripts/run_v4.sh

# 确定 user-id
USER_ID="${V4_USER_ID:-000000000000000000000000}"
```

### Step 2: 解析意图并拼装命令

根据上方映射表，将用户自然语言解析为：
- **动作**：`analyze` / `refresh` / `status` / `scan`
- **单元选择器**：`asset:<class>` / `alloc:portfolio` / `industry:<name>` / `stock:<code>` / `plan:<class>` / `alloc:equity_industries` / `alloc:industry:<name>`

公共参数：
```bash
H=data/v4/_inputs/holdings.json
COMMON="--user-id $USER_ID --portfolio-file $H"
```

### Step 3: 执行

单个单元：
```bash
./scripts/run_v4.sh analyze <unit-selector> $COMMON
```

全量分析序列（用户说「跑全量」时按此顺序）：
```bash
H=data/v4/_inputs/holdings.json
# 1) 七大类逐个分析
for c in equity fixed_income cash commodity precious_metal real_estate alternative; do
  ./scripts/run_v4.sh analyze asset:$c --user-id $USER_ID --portfolio-file $H
done
# 2) 资产配比（下传 equity_quota）
./scripts/run_v4.sh analyze alloc:portfolio --user-id $USER_ID --portfolio-file $H
# 3) 非权益六类方案
for c in fixed_income cash commodity precious_metal real_estate alternative; do
  ./scripts/run_v4.sh analyze plan:$c --user-id $USER_ID --portfolio-file $H
done
# 4) 导入 + 体检
python scripts/import_v4.py --user-id $USER_ID
python scripts/run_report_v4.py
```

> 权益深链（行业/个股）需用户指定具体行业/标的，不在全量中自动跑（成本控制）。

### Step 4: 结果反馈

执行完成后向用户报告：
- 命中单元名 + 状态变化（灰→蓝→绿/红）
- 产物文件路径
- 若有 stale 下游，提示「以下单元建议刷新：...」
- 若失败，输出原因和重试指令

## 约束

- 🚫 **绝不在 Web 接口中触发 LLM 分析**——本 skill 只在本地 CLI 对话中执行。
- 🚫 **不强制连带重跑**——用户说「分析权益」只跑 `asset:equity`，不连带跑配比/行业。
- 🚫 **不猜测行业/个股**——用户未明确说哪个行业/标的时，列出可选项让用户选择。
- ✅ 用户说「刷新」时用 `refresh`（强制失效重跑）；说「分析」时用 `analyze`（有缓存则跳过）。
- ✅ 执行前确认持仓文件存在；不存在时引导用户创建。
- ✅ `--full` 仅在用户明确说「忽略缓存」「强制重跑」「--full」时才加。
