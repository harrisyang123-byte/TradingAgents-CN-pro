# v4 基金穿透分析 Level 1 — 取数+穿透+行业聚合+前端展示

**状态**：approved by user 2026-06-13
**前置**：`v4-tradingagents-parity`（已合并）

---

## Why

用户持仓 36 项中 26 项是基金/ETF，权益类基金市值（¥47 万）是股票市值（¥24 万）的 1.93 倍。当前 v4 系统只能按 `instrument_type=fund` 归到大类，**不穿透到底层股票/行业**——整个组合分析瞎眼一半：
- 行业页只看到 9 个直接持股的行业，看不到 17 权益基金间接贡献的行业
- 重复持仓不可见（沪深300 ETF + 中证500 + 中证 A500 都是大盘暴露）
- 配比建议无法给"加配 X 行业 → 应该买什么基金"
- 基金内部风格/规模/行业分布完全黑盒

这违反 §1 终极目标 "全面" 要求："基金须穿透到底层股票/行业/风格（不穿透 = 整个组合分析瞎眼一半）"。

---

## What Changes

### Level 1 必做（本 change 范围）

1. **基金穿透取数** (`scripts/v4_fund_source.py` 新建)
   - AKShare `fund_portfolio_hold_em` 取前 10 重仓股
   - `fund_individual_basic_info_em` 取基金基本信息（类型/规模/费率）
   - `fund_portfolio_industry_em` 取行业分布
   - 缓存到 `data/v4/_funds/<code>.json`

2. **classifier 升级** (`app/services/v4/v4_classifier.py`)
   - 输出加 `fund_holdings: [{code, name, weight}]`
   - 输出加 `fund_industry_exposure: {半导体: 12%, 新能源: 8%}`
   - 仍保持 `instrument_type` 大类归类不变（向后兼容）

3. **行业聚合** (`app/services/v4/v4_aggregator.py` 新建)
   - 直接持仓 + 基金穿透 = 总行业暴露
   - 输出 `data/v4/inputs/portfolio_aggregated.json`
   - 字段：`{industry: {direct_yi, indirect_yi, total_yi, contributing_funds: [...]}}`

4. **后端透传**
   - `app/services/v4/v4_query.py` build_industry_detail 加 `indirect_holdings` 字段
   - `app/routers/portfolio_v4.py` 透传聚合数据

5. **前端展示**
   - `IndustryDetailTab.vue` 个股表加"间接持仓 ¥X (来自 N 只基金)"列
   - 持仓总览页加"基金穿透汇总"卡片
   - TS 类型加 `IndirectHolding` interface

### Level 2 / Level 3（不在本 change 范围）

- 风格因子拆解（大盘/小盘/价值/成长/红利）
- 重叠分析（同主题多 ETF）
- 基金费率/业绩/经理风格漂移评分

---

## Impact

### 新增文件
- `scripts/v4_fund_source.py`（基金取数 + AKShare 接口封装）
- `app/services/v4/v4_aggregator.py`（直接 + 间接持仓聚合）
- `data/v4/_funds/<code>.json`（基金穿透缓存）
- `data/v4/inputs/portfolio_aggregated.json`（聚合输出）

### 修改文件
- `app/services/v4/v4_classifier.py`（输出加 fund_holdings + fund_industry_exposure）
- `app/services/v4/v4_query.py`（透传 indirect_holdings）
- `app/routers/portfolio_v4.py`（API 加聚合）
- `frontend/src/api/portfolioV4.ts`（加 IndirectHolding 类型）
- `frontend/src/views/Portfolio/v4/IndustryDetailTab.vue`（个股表加间接持仓列）
- `agents/advisor/v4-data-desk.md`（加基金取数协议）

### 沙箱限制
- AKShare 在沙箱无外网 → schema + classifier + aggregator + 前端 UI 全部完成
- 数据用 `data_status: "manual_required"` 标注
- 用户在生产环境 git pull 后跑 `python scripts/v4_fund_source.py` 取真数据

### 用户验证路径
- `git pull` → 看 IndustryDetailTab 多了"间接持仓"列
- 沙箱无外网时显示 estimated/missing；生产环境跑取数后显示 verified

---

## Tasks（执行清单）

详见 `tasks.md`

---

## 完成判定

- [ ] `v4_fund_source.py` schema + AKShare 取数函数 + 缓存机制
- [ ] `v4_classifier.py` 输出加 `fund_holdings` + `fund_industry_exposure`
- [ ] `v4_aggregator.py` 直接+间接聚合
- [ ] 后端 API 透传聚合数据
- [ ] 前端 IndustryDetailTab 加"间接持仓"列
- [ ] TS 类型 `IndirectHolding` 接口
- [ ] 26 只基金的 mock 穿透数据（沙箱用，标 estimated）
- [ ] 静态快照重生成 + TS 检查 + 提交
