---
version: "3.0.0"
requirement: "Claude Code 组合顾问引擎 — Python 编排 + 子 Agent 混合架构"
status: draft
created: "2026-06-03"
updated: "2026-06-03"
modules: ["cli/claude_advisor.py", "app/services"]
entities: ["PortfolioAdvice", "AdviceItem"]
author: "AI + yangyanyu"
oais_version: "1.1.0"
---

# Claude Code 组合顾问引擎 v3 — Python 编排 + 子 Agent 混合架构

## O — Objective（业务目标）

### P（现状）

当前 LangGraph 四层 Agent 管线有三大问题：

**问题1: 内容品质不足，用户不敢相信结论**
```
专业投资公司产出                          Tid 顾问现产出
─────────────────────────────────────────────────────────────
L1: 宏观定量+行业轮动+超配/标配/低配       → Go/NoGo 标签（20行业仅1个Go）
L2: ROE/营收增速/DCF+小盘+价格区间         → 6 维 LLM 评分（19只候选全是大蓝筹）
L3: 回测/相关性/因子暴露/波动率             → 无（策略师报"行业全部为未知"）
L4: 资金分配方案(有来源有去向+优先级+时间线) → 持仓操作清单（13条new_position无视Tier1建议卖的6只）
```

用户反馈：
- "只推荐腾讯" → L2 只有大蓝筹
- "现金持有32万怎么处理也不说" → 没资金分配概念
- "分析极奇怪，感觉不像合作" → 层间数据断裂
- "不敢用" → 最致命

**问题2: Agent 间数据断链**

msg_clear → 每层 Agent 上下文断裂：
- L1→L2: Scout 没收到 L1 的 Go 行业 → 自己全市场扫
- L3 策略师: 看不到分析师评估 → 报"行业全部为未知"
- Tier1 查询: 11 份报告只匹配到 9 份（中兴通讯 3 份互相矛盾但不被任何 Agent 发现）

**问题3: 迭代验证成本高**

改 6 个文件才能修一个断链，每次跑 22 分钟验证。

### A（动作）

**不改 LangGraph 原代码（留 fix 分支保留）**。在新分支 `feature/claude-code-advisor` 上构建 Python 编排 + 9 个子 Agent 混合架构。每个子 Agent 一次独立 LLM 调用，通过 JSON 文件传递完整上下文。

每层产出对标专业投资公司：
- L1: 宏观定量 + 超配/标配/低配 + 量化指标
- L2: 财务数据驱动 + 建仓价格区间 + 不限于大蓝筹
- L3: 组合健康度诊断（集中度 + 一致性风险 + 共性担忧）
- L4: 资金分配方案（有来源有去向 + 优先级 + 时间线）
+ 交叉验证规则引擎做 LangGraph 做不到的矛盾检测

### M（指标）

| 指标 | 当前 | 目标 |
|------|------|------|
| 单次分析时间 | ~22min | ≤ 5min |
| 处方覆盖持仓 | 36/36 | 100% |
| L1 Go 行业数 | 1/20 | ≥ 5（含超配/标配区分） |
| L1 每行业理由 | ~60字 | ≥ 200字 |
| 候选标的非大盘比例 | 0/19 | ≥ 30% |
| Tier1 矛盾检出 | 0 | ≥ 1 |
| CIO 敞口诊断 | 无 | 始终包含 |
| 前端展示 | 加载失败 | 正常展示 |
| 交叉验证检出 | 0 | ≥ 1（中兴通讯矛盾） |

---

## A — Architecture（架构设计）

### A.1 模块总览

```
cli/claude_advisor.py（Python 主控 — 流程编排）
  │
  ├── 数据收集层（Python 工具调用，~30s）
  │   ├── PortfolioService.get_portfolio_summary()
  │   ├── analysis_reports → Tier1 报告
  │   ├── compute_pe_context() per stock
  │   ├── ExposureService.compute()
  │   ├── get_macro_indicators（PMI/CPI/利率）
  │   ├── get_sector_fund_flows（行业资金流向）
  │   └── get_industry_rankings（行业排名）
  │
  ├── 子 Agent 层（9 个独立 LLM 调用，通过 JSON 文件通信）
  │
  │   L1:  ┌── Agent 1: 市场策略师 ──┐
  │        │                         ├──→ Agent 3: 宏观裁判 → step3
  │        └── Agent 2: 反向者 ─────┘
  │   L2:  ┌── Agent 4: Scout (含6维评分+反向自检) ──→ step4
  │   L3:  ┌── Agent 5: 分析师 ──┐
  │        │                     ├──→ step6
  │        └── Agent 6: 策略师 ──┘（诊断报告员，不输出操作建议）
  │   L4:  Agent 7: CIO → step7
  │        Agent 8: 风险总监 → step8
  │        Agent 9: CIO 终裁 → step9（最终）
  │
  ├── 交叉验证层（Python 规则引擎，非 LLM，~5ms）
  │   ├── Tier1 矛盾检测（同标的买入 vs 卖出）
  │   ├── PE 分位 vs 建议方向一致性
  │   ├── 敞口重叠识别
  │   └── L2 候选大盘占比
  │
  └── 保存层
      └── MongoDB portfolio_advice（source='claude-code-v3'）
```

### A.2 实体定义

复用现有实体（不做 schema 变更）：
- `PortfolioAdvice`（不变）
- `AdviceItem`（不变，已含 timing/suggested_price/priority 等）
- `BuySignal`（不变）
- `MarketSignalSnapshot`（不变）

仅 `cli/claude_advisor.py` 的 `cio_verdict` 文本中增加结构化段落。

### A.3 子 Agent 通信：JSON 文件总线

```
/tmp/claude_advisor/
├── data_portfolio.json    # 持仓 + 账户
├── data_tier1.json        # Tier1 报告
├── data_pe.json           # PE 分位
├── data_exposure.json     # 敞口矩阵
├── data_macro.json        # 宏观指标（PMI/CPI/利率/行业排名/资金流向）
├── step1_strategist.json  # L1 策略师
├── step2_contrarian.json  # L1 反向者
├── step3_judge.json       # L1 裁判
├── step4_scout.json       # L2 Scout
├── step5_analyst.json     # L3 分析师
├── step6_strategist.json  # L3 策略师（诊断报告）
├── step7_cio.json         # L4 CIO 初稿
├── step8_risk.json        # L4 风险总监
├── step9_final.json       # L4 CIO 终裁
└── conflicts.json         # 交叉验证结果（注入 CIO）
```

每个子 Agent 读前面几步的全部 JSON → 推理 → 写自己的 JSON。

### A.4 辩论结构

```
L1 辩论（3 Agent）:
  Agent 1(策略师): 有宏观数据+持仓 → 行业判断
  Agent 2(反向者): 有策略师输出 → 质疑
  Agent 3(裁判): 有策略师+反向者 → 最终裁定

L2 标的筛选（1 Agent + 交叉验证）:
  Agent 4(Scout): 有L1裁定+持仓+Tier1 → 6维评分+反向自检+候选池
  【无独立辩论——反方向题合并到Scout的自检环节，裁判评分合并到6维评分体系】
  交叉验证层: 通过规则引擎检查Scout输出的矛盾

L3 辩论（2 Agent）:
  Agent 5(分析师): 有L1裁定+L2+Tier1+PE → 安全边际
  Agent 6(策略师): 有分析师输出+集中度+敞口 → 诊断报告

L4 辩论（3 Agent）:
  Agent 7(CIO): 有全部→初稿
  Agent 8(风险): 有初稿→风险审查
  Agent 9(CIO终裁): 有初稿+风险→最终
```

### A.5 L2 辩论合并的设计理由

原 LangGraph L2: Scout → StockContrarian → StockJudge + 2 轮辩论。在 claude_advisor 中合并为 1 个 Scout + 交叉验证。理由：

| 原职责 | 归属 | 说明 |
|--------|------|------|
| Scout 6 维评分 | Scout prompt 本身 | 评分标准已在 prompt 中定义，SCout 输出时就带评分 |
| Contrarian 挑战 | Scout 反向自检 | Scout prompt 中要求"列出每只候选的 Top-3 风险"和"反向视角自查" |
| Judge 裁定 | 6 维总分映射 | 总分 >=35 强烈推荐 / >=28 推荐 / >=20 观察 / <20 不推荐，已在 Scout 输出中 |
| 辩论循环 | 不需要 | Scout 的数据查询是确定性的（调工具拿数据），不是可辩论的观点 |

不会引起质量下降的原因：
- Scout 有工具调用能力（`get_industry_constituents`、`get_company_profile`、`get_financial_summary`、`get_stock_quotes`、`get_fund_rankings`）——给足数据让 LLM 打分，不是凭空猜
- 反向者的独立 PK 被交叉验证层的规则引擎替代——规则引擎不做"你觉得呢"，它做确定性的矛盾检测（"Tier1 说买入但 PE 99% 分位"）
- 如果未来需要更精细的辩论，可以在交叉验证层加一个"L2 争议检测"Agent——这不是当下的瓶颈
  Agent 8(风险): 有初稿→风险审查
  Agent 9(CIO终裁): 有初稿+风险→最终
```

和 LangGraph 关键区别：

```
LangGraph:         Analyst → msg_clear → Strategist(msg="Continue")
                   策略师不知道分析师说了什么！

claude_advisor.py: Analyst → step5_analyst.json → Strategist 读 step5.json
                   策略师完整看到分析师的每只持仓评估
```

---

## A.5 每层产出规范

### L1 产出

**策略师输出**（Agent 1）：
```json
{
  "industries": [
    {
      "industry": "通信设备",
      "recommendation": "Go",
      "direction": "超配",
      "lifecycle": "稳步成长",
      "data": {
        "pe_median": 18.5,
        "roe_median": 12.3,
        "revenue_growth": "15% YoY",
        "fund_flow": "行业流入 Top 5"
      },
      "key_drivers": ["5.5G 商用", "政企数字化"],
      "key_risks": ["地缘制裁"],
      "reasoning": "当前PE中位数18.5x处于历史中低位，行业营收增速15%..."
    }
  ]
}
```

**裁判输出**（Agent 3）：
- 最终的超配/标配/低配/零配方向
- 5-8 个方向，每个 ≥ 200 字理由
- 明确标注数据来源（引用了哪个工具的哪条数据）

### L2 产出

**Scout 输出**（Agent 4）：
```json
{
  "candidates": [
    {
      "code": "000063",
      "name": "中兴通讯",
      "from_l1_industry": "通信设备",
      "score_business_model": 8,
      "score_moat": 7,
      "score_management": 4,
      "score_financials": 8,
      "financial_data": {
        "roe": 14.2,
        "revenue_growth": "8.7%",
        "fcf_positive": true,
        "debt_ratio": 55.3
      },
      "valuation": "合理",
      "price_range": "¥35-42",
      "catalyst": "5.5G商用订单增加",
      "target_position": "5%"
    }
  ]
}
```

关键要求：
- 财务数据必须引用具体数值，不能只凭 LLM 估
- 30%+ 候选来自中小市值
- 每只候选附带 price_range + catalyst + target_position

### L3 产出

**分析师输出**（Agent 5）：
- 每只持仓的安全边际评估（包含 Tier1 引用 + PE 引用）
- 对 Tier1 的矛盾说明（如有）

**策略师输出**（Agent 6）：
- 组合健康度诊断，不输出操作建议
- 集中度检测（当前 HHI + 超标预警）
- 分析师建议的一致性风险（"5 只加仓全在科技"）
- 基金穿透后隐形暴露汇总
- 共性的数据质量担忧

### L4 产出

**CIO 终裁输出**（Agent 9）：
```json
{
  "cio_verdict": "第一部分：敞口诊断...\n第二部分：行业配置方案\n第三部分：资金分配说明\n第四部分：操作处方",
  "prescription": [
    {
      "code": "000063",
      "action": "add",
      "current_weight": 2.1,
      "target_weight": 5.0,
      "timing": "conditional",
      "suggested_price": "¥35-38",
      "reasoning": "L1 Go通信设备，Tier1目标价42（注意Tier1矛盾）",
      "priority": "important"
    }
  ]
}
```

资金分配 = 每条处方标注 capital_source（来源现金 / 来源卖出某标的）。

---

## A.6 交叉验证层

Python 规则引擎，非 LLM：

```python
conflicts = []

# 1. Tier1 矛盾检测
for code in tier1_codes:
    recs = [r for r in tier1 if r['code'] == code]
    if any('买入' in r for r in recs) and any('卖出' in r for r in recs):
        conflicts.append({"code": code, "type": "tier1_conflict", "severity": "high"})

# 2. PE 高估 vs 建议买
for code, pe in pe_data.items():
    if pe.get('pe_percentile_5y', 0) > 85:
        conflicts.append({"code": code, "type": "pe_overvalued", "severity": "medium"})

# 3. 敞口重叠
for o in exposure.get('overlaps', []):
    conflicts.append({"code": o['code'], "type": "overlap", "severity": "low"})
```

冲突报告注入 CIO prompt → CIO 在处方中必须处理。

---

## A.7 数据收集

L1 子 Agent 调用前，先收集：

| 数据 | 来源 | 耗时 |
|------|------|------|
| 持仓 | PortfolioService | ~10s |
| Tier1 | analysis_reports | ~1s |
| PE 分位 | compute_pe_context | ~10s/只 |
| 敞口矩阵 | ExposureService | ~5s |
| 宏观指标 | get_macro_indicators | ~2s |
| 行业排名 | get_industry_rankings | ~2s |
| 资金流向 | get_sector_fund_flows | ~2s |

---

## I — Interface（交互层）

### CLI 入口

```bash
# 完整分析
python cli/claude_advisor.py --user-id 6a094caea814b57d3357fa0b

# --verbose = 每步打印子 Agent 输出
# --skip-data = 复用已缓存的数据文件（debug 用）
```

### 前端（零改动）

写 MongoDB 后，前端 `/portfolio/overview` 直接从 `portfolio_advice` 读取展示。前端通过 `source='claude-code-v3'` 区分。

### 和 LangGraph 的共存

| 维度 | LangGraph（fix 分支） | claude_advisor.py（新分支） |
|------|----------------------|---------------------------|
| 触发 | 前端按钮→后端API | CLI python cli/claude_advisor.py |
| 数据源 | 同上 | 同上 |
| 输出 | MongoDB | MongoDB（同一 collection）|
| 前端区分 | source='langgraph' | source='claude-code-v3' |
| Agent 数 | 12+6 辩论循环 | 9 |
| 上下文完整 | ❌ msg_clear 断裂 | ✅ JSON 文件总线 |
| 交叉验证 | ❌ 无 | ✅ 规则引擎 |
| 单次耗时 | ~22min | 预估 ~5min |

---

## S — Scenarios（场景）

### Normal: 完整分析

- 用户运行 CLI
- 数据收集 ~30s → 9 个子 Agent ~3min → 交叉验证 ~5ms → 保存 ~1s
- 总计 ~4min
- MongoDB 写入成功，前端可展示

### Error: 数据收集失败

- AKShare SSL 超时（基金穿透失败）
- → 跳过基金穿透，记录警告，继续流程
- CIO 备注"基金穿透数据不完整"

### Error: PE 管道不可用

- 美股 timezone bug 导致 PE 失败
- → 该标的使用 MA20 回退，cross_validator 标注数据质量低

### Conflict: Tier1 矛盾

- 中兴通讯 3 份报告方向矛盾
- → cross_validator 检出 → CIO 在处方中标注"Tier1矛盾，建议重新分析"

### Conflict: 分析师 vs 策略师不一致

- 分析师推荐 5 只加仓全在科技
- 策略师诊断"科技集中度已达危险线"
- → CIO 终裁必须明确取舍

---

## 未解决的问题（v4）

- 组合回测/相关性矩阵/因子暴露（需要更多数据基建）
- 基金穿透数据实时化（AKShare SSL 问题待修）
- 美股 PE 数据（timezone bug 待修）
- 交叉验证规则扩展为 LLM 辅助（当前是硬编码规则）
