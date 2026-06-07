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

## 执行流程

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
