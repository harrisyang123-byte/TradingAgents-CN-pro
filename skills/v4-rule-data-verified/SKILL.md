---
name: v4-rule-data-verified
description: >
  Use when any agent needs concrete numbers (TAM, market share, prices, financials, ROIC, growth rate).
  Mandatory for: ALL v4 agents that handle quantitative claims.
  Critical separation: main agent does data fetching (web_search/AKShare), subagents do reasoning.
  Provides: data sourcing rules + verified URL requirements + main vs subagent division of labor.
  Counter-examples: 通富 $157B fabrication, 2026-06-17 ai_tam $400B undervalue 50-100%.
---

# 数据 Verified 铁律(RULE-DATA-VERIFIED)

> **方法论真源**:`AGENTS.md §RULE-DATA-VERIFIED` + `planning/v4/project-master-prompt.md §7/§7-bis/§7-bis-x`
> **2026-06-14 用户血泪固化代码层强制**:`stock_data_contract.py::check_expert_valuation_verified()` write 钩子 exit=4 拦截
> **2026-06-17 v2 升级**:加"取数 vs 推理"分工明确,防 ai_tam_verified 事故

## 第一铁律:取数 vs 推理职责分离

**主 agent 取数,subagent 推理。** 任何 agent 处理具体数字时必须明确:

| 数据类型 | 谁取(必须) | 是否允许 subagent 凭训练记忆? |
|---|---|---|
| **价格 / PE / PB / 市值** | 主 agent AKShare(stock_zh_a_daily / stock_financial_abstract) | ❌ 禁,过时数据=错的 |
| **财务比率(ROE/ROIC/FCF/EPS)** | 主 agent AKShare(stock_financial_abstract) | ❌ 禁 |
| **TAM 当前 / 2030E** | 主 agent web_search ≥3 独立 URL(McKinsey/Gartner/Goldman/IDC/SEMI) | ❌ 禁,subagent 必凭旧数据 |
| **市场份额 / 龙头集中度** | 主 agent web_search verified(年报/Counterpoint/IDC) | ❌ 禁 |
| **CAGR / 渗透率** | 主 agent web_search verified | ❌ 禁 |
| **宏观 22 指标** | data-desk(macro_source.py AKShare 22 指标) | ❌ 禁 |
| **方法论推理(七把尺/五因子/估值方法)** | subagent 在 verified 数据基础上推理 | ✅ 允许(只要有 verified 数据输入) |
| **多空辩论 / stance 判断 / forward_view 6维** | subagent 综合判断 | ✅ 允许 |

## 致命反例库(必读,防同类再犯)

### 反例 1:通富微电 $157B 事故(2026-06-13)
- **错的做法**:主 agent 凭训练记忆为先进封装 TAM 写 $157B
- **真值**:Yole 2026 先进封装 TAM ~$46-79B
- **教训**:主 agent 也不能凭记忆,必须 web_search 验证

### 反例 2:ai_tam $400B 事故(2026-06-17)
- **错的做法**:spawn ask-agent-v2(无联网)做 future_market_analyst,subagent 输出"Goldman $400B / McKinsey $370-410B / Gartner $395B 三源一致"
- **真值**:web_search verified Goldman $527B / Mag7 $725B / Top9 CSP $830B / 全球 ~$1T,**subagent 低估 50-100%**
- **教训**:subagent 凭训练记忆 = 2023-2024 旧数据,即便给出"具体来源"也是编的(它没真访问那个 URL)
- **修正**:主 agent 必须自己 web_search,subagent 只能在拿到 verified 数据后做方法论推理

### 反例 3:hunter 估市值偏小事故(2026-06-15)
- **错的做法**:alpha-hunter spawn 时输出"国瓷材料市值~15亿"等具体数字
- **真值**:AKShare verified 国瓷 554亿(差 37 倍)、侨源 246亿(差 70 倍)、鹏辉 378亿(差 31 倍)
- **教训**:hunter 也是 subagent,无联网,凭训练记忆估市值系统性偏小
- **修正**:hunter 输出市值标 `inferred_待verified`,主 agent 用 AKShare 校正

## 必产字段(任何含数字的 agent 输出)

```json
{
  "data_status": "verified|estimated|inferred|missing",
  "data_source_url": "https://... + 发布日期 + 口径(如'hyperscaler capex' vs '全球AI总支出')",
  "_data_verification_status": "verified_by_main_agent_websearch|verified_by_AKShare|inferred_by_subagent_reasoning|凭脑补⚠️"
}
```

## 代码层硬拦截(已实施)

1. **`app/services/v4/stock_data_contract.py::check_expert_valuation_verified()`**:个股 expert_valuation 含 TAM/份额数字必须有 `verified_source URL` 或 `derived_from_industry`,缺则 `block_write=True`
2. **`scripts/v4_unit_cli.py` write 钩子**:check fail → exit=4 拦截不让落盘
3. **`v4-investor-critic` 6.11/6.11.x 必查**:每个数字的 `data_status` + 来源
4. **`v4-investor-critic` 6.14**(本次新增):必查 `_data_verification_status`,subagent 凭推理报具体 TAM 数字 → 直接 NEEDS_CHANGES

## 何时该新增 verified 数据源 vs 何时改 .md 推理

详见 `project-master-prompt.md §7-bis`:

**第一类(必须 verified 数据源)**:
- 财务比率 ROIC/ROE/FCF/EPS → AKShare
- 价格/PE/PB → AKShare
- **TAM 当前/2030E/CAGR/渗透率%** → web_search ≥3 独立来源标 URL+status
- 宏观 22 指标 → AKShare/官方源

**第二类(改 .md 推理即可)**:
- 多空辩论 / 风险辩论 / chokepoint 判定 / forward_view 6 维 / stance / 方向 / 仓位 → subagent 用 verified 数据辩论
- 渗透率阶段判定(在已知%基础上) / forward PEG 解读

## 反偷懒约束

- ❌ subagent 凭训练记忆报具体 TAM/份额数字
- ❌ 主 agent 自己也凭训练记忆(即便方便)
- ❌ 数据无 URL/无 status(无法验证真假)
- ✅ 主 agent **取数前必先 web_search/AKShare**
- ✅ subagent 收到 verified 数据后才能展开方法论推理
- ✅ 每个数字标 `data_status` + URL/source

## critic 必查清单

1. ✓ 每个 TAM/份额/渗透率/财务数字是否有 `data_source_url` 或 AKShare 来源
2. ✓ `_data_verification_status` 是否明示(verified/inferred 不能含糊)
3. ✓ subagent 是否在没有 verified 数据输入下"自己报数字"(必 NEEDS_CHANGES)
4. ✓ 多源 TAM 是否标分歧不调和(偏差>30% 禁调和)
5. ✓ 历史数据 vs 最新 verified 是否同步(防用 2023 旧数据下 2026 判断)
