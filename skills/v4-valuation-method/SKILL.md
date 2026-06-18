---
name: v4-valuation-method
description: >
  Use when running v4 估值分析 agent. Mandatory for: v4-stock-analyst-valuation,
  v4-stock-valuation-engineer (估值工程师), v4-stock-valuation-auditor (推导链审计).
  Provides: ①估值 5 铁律 (诚实区间/三派合理价/PEG 五陷阱/历史可比/可证伪)
  ②预期差三锚 SOP (隐含增速缺口/定价充分度/催化) ③DCF 反向工程 SOP ④PEG 五大陷阱
  (后视镜增速/低基数/周期伪装/质量不分/久期) ⑤多派别合理价 (价值/GARP/成长/逆向)
  ⑥安全边际档位 (蓝筹 25-30% / 高增长 30-35% / 周期 40-50% / 困境 60%+)
  ⑦valuation_method 输出契约。这是把"PE 50x 合理"空话沉淀为"反向 DCF + 三派合理价 + 历史可比 SOP"。
---

# v4 估值方法 SOP skill (valuation method)

> **用途**: 估值分析师 + valuation-engineer + valuation-auditor 三 agent 主用。
> **核心信念**: "PE 50x 合理"是结论不是分析。真分析必须给反向 DCF 隐含增速 + 多派别合理价 + 历史可比 + PEG 五陷阱排查 + 安全边际档位。

## §1 估值 5 铁律 (内化自 critic 6.7 估值底层四问 + 6.13 成长股估值 + planning/v4/stock-selection-theory.md)

### 铁律 1: 价值是诚实区间 + 估算误差%
- ❌ 浅: "目标价 ¥45" (假装精确单点)
- ✅ 深: "DCF 内在价值区间 ¥35-55 (±20% 误差) — WACC 8-12%/g 永续 2-4%/营收 5y CAGR 15-20% 三敏感性"
- 实操: 任何 target_price 必给 [low, high] 区间 + estimation_error_pct + 三敏感性变量(WACC/g/CAGR)

### 铁律 2: 多派别合理价 (≥3 派)
- ❌ 浅: 给 1 个 base case 目标价
- ✅ 深: 价值派 ¥27 (内在 ×0.6 安全边际) / GARP 派 ¥36 (PEG ≤1) / 成长派 ¥50 (信号触发后任意价) / 逆向派 ¥22 (深度套牢承接)
- 实操: 必给 ≥3 派各自合理买点 + each派的逻辑 (用户风格不同)

### 铁律 3: PEG 五陷阱排查 (用户血泪反例, critic 6.10)
每给 PEG 数字必排查 5 陷阱, 任一命中标"PEG 不可用":
- ① 后视镜增速: 用 forward 常态增速, 非 TTM 峰值
- ② 低基数幻觉: 寒冬→恢复年份 +102% 增速虚高, 必对比正常年份 5y CAGR
- ③ 周期伪装成长: 周期股景气高点低 PEG = 卖出信号 (紫金 61.5% 增速实为内生 8-12%), 周期股禁用 PEG 改 PB+产能周期
- ④ 增速质量不分: 营收增速 ≠ 利润增速 (工业富联增收不增利毛利 3-5%), 必拆量/价/利润率
- ⑤ 增速久期: PEG 隐含永续, 高增速实仅 2-3 年, 必做久期折算

### 铁律 4: 安全边际档位 (用户 D0-8 反馈)
| 档位 | 标的类型 | 安全边际 |
|---|---|---|
| 1 | 蓝筹白马 (茅台/海天) | 25-30% |
| 2 | 高增长 (中际/恒瑞/恺英) | 30-35% |
| 3 | 周期+大客户+高杠杆 (中芯/京东方) | 40-50% |
| 4 | 困境反转 | 60%+ |

- ❌ 浅: 安全边际 -10% 给周期股 (随手填) = critic fatal_flaw
- ✅ 深: "本股归档位 3 (周期+大客户), 安全边际 45%, 价值派买点 = DCF 内在 ¥45 × 0.55 = ¥25"

### 铁律 5: 可证伪 + 历史可比路径
- ❌ 浅: "PE 35x 合理" 凭感觉
- ✅ 深: "可比公司 X 从增速 30%→15% 时 PE 从 50x→25x 用 18 月; 本股增速预测 30%→20%, 概率 60%, 对应 PE 35x→28x 时间窗 12-18 月"
- 实操: 每个 PE 中枢锚 ≥1 个历史可比 re-rating 路径 (critic 6.3)

## §2 预期差三锚 SOP (核心选股理论, planning/v4/stock-selection-theory.md)

### 锚 1: 隐含增速缺口
- 反向 DCF: 当前价格隐含的永续 g% = (P×WACC - FCF) / P 反推
- 与可验证增速对比: 行业 CAGR / 卖方一致 forward 5y / 公司指引
- **预期差 > 0**: 可验证增速 > 隐含, 还能涨
- **预期差 = 0 / < 0**: 已 price-in / 已透支

### 锚 2: 定价充分度 (市场已 price-in 什么)
- 列出市场共识 (≥3 卖方研报关键词高频项)
- 标注哪些**未** price-in (我方独立判断)
- 例: 中际旭创 ¥88 时市场 price-in '光模块周期顶', 未 price-in '800G 渗透+1.6T 储备 + 客户 A 卡位独家' → 11 倍

### 锚 3: 催化剂时间窗
- 每锚配 ≥1 个 12 月内可观测催化 (财报/订单/产能/政策)
- 量化阈值: "Q3 出货量 > X 万 = 兑现"

**预期差三锚必齐, 缺任一 → critic NEEDS_CHANGES** (planning/v4/stock-selection-theory.md A/B 测试已证, 涨幅/PE 分位错锚导致中际旭创错过 11 倍)

## §3 DCF 反向工程 SOP (隐含增速 vs 可验证增速)

### 公式
```
P = Σ FCF_t / (1+WACC)^t + 终值 / (1+WACC)^N
终值 = FCF_N × (1+g) / (WACC - g)
```

### 反向: 给 P, 求 implied g
- 假设 5 年明确期 + 永续: P = FCF₁ × [1 - ((1+g)/(1+WACC))^5] / (WACC-g) + 终值PV
- 解出 implied g (隐含永续增速)

### 三敏感性 (WACC ± 1pct / g ± 1pct / 5y CAGR ± 5pct)
- 给 27 单元格矩阵 (3×3×3) 不是单点
- 区间两端做"创造价值/毁灭"翻转检验

### 与可验证 g 对比
- 隐含 g 5% vs 行业 CAGR 15% = 显著低估 (创造预期差)
- 隐含 g 25% vs 行业 CAGR 10% = 已透支

## §4 PEG 五大陷阱排查表 (critic 6.10 必查)

| 陷阱 | 症状 | 排查 SOP | 历史反例 |
|---|---|---|---|
| ① 后视镜增速 | 用 TTM 峰值算 PEG | 改 forward 常态 5y CAGR | 半导体景气顶 |
| ② 低基数幻觉 | 寒冬→恢复年 +100%+ | 对比正常年 5y CAGR | 创新药 CXO 102% |
| ③ 周期伪装 | 周期股景气顶低 PEG | 周期股改 PB+产能周期 | 紫金 61.5% (内生 8-12%) |
| ④ 质量不分 | 营收增速当利润增速 | 拆量/价/利润率 3 因子 | 工业富联毛利 3-5% |
| ⑤ 久期 | 永续假设高增速 | 久期折算 (高增 2-3 年 + 常态) | 多数高成长股 |

**结论必答**: (a) 增速能持续几年? (b) 增速来源是什么(量/价/并购)? (c) 是否周期伪装?

## §5 多派别合理价 (≥3 派, 用户风格匹配)

### 价值派 (巴菲特/段永平)
- 锚: 内在价值 × (1 - 安全边际%)
- 适用: 蓝筹白马, 长期持有 10 年
- 例: 茅台 DCF 内在 ¥1500 × 0.7 = 价值派买点 ¥1050

### GARP 派 (Lynch)
- 锚: PEG ≤ 1 + 信号触发后任意价
- 适用: 高增长, 持有 3-5 年
- 例: forward PE 35x / forward CAGR 35% = PEG 1, 信号触发买

### 成长派 (Marks 二阶思维)
- 锚: 基本面拐点信号触发即买
- 适用: 紫苏叶/错杀龙头/拐点
- 例: 中际旭创 ¥88 拐点信号: 客户 A 独家 + 800G 渗透加速

### 逆向派 (Templeton/邓普顿)
- 锚: 深度套牢承接 (PB < 0.7 或 PE 历史分位 < 5%)
- 适用: 困境反转 / 价值陷阱辨别
- 例: 平安银行 PB 0.5 + 信用风险释放后承接

**critic 必查**: 任一 verdict 必含 ≥3 派合理价 + each 派逻辑

## §6 valuation_method 输出契约

```json
"valuation_method": {
  "_doc": "★ iter 7 落地, skill v4-valuation-method §6, verify_audit ⑬ 必查",
  "verified_period": "as_of 2025年报",
  "expectation_gap_3anchor": {
    "implied_growth": {"value_pct": 5, "vs_verifiable_pct": 15, "gap": "正", "method": "反向 DCF"},
    "pricing_completeness": {"market_priced_in": ["共识1", "共识2"], "we_see_unpriced": ["独立判断1"]},
    "catalysts": [{"event": "Q3 财报", "window_months": 3, "threshold": "出货量 > 50 万", "verified": "卖方一致 +18%"}]
  },
  "dcf_reverse": {
    "implied_g_pct": 5.0,
    "verifiable_g_pct": 15.0,
    "wacc_range": [8, 12],
    "g_perpetual_range": [2, 4],
    "cagr_5y_range": [15, 20],
    "sensitivity_3x3": [["¥35", "¥40", "¥45"], ["¥40", "¥45", "¥50"], ["¥45", "¥50", "¥55"]],
    "robustness_verdict": "区间 ¥35-55 创造价值结论稳健"
  },
  "peg_traps_check": [
    {"trap": "后视镜增速", "trigger": false, "data": "用 forward 5y CAGR 18% 非 TTM 峰值 35%"},
    {"trap": "低基数幻觉", "trigger": false, "data": "..."},
    {"trap": "周期伪装", "trigger": false, "data": "成长股非周期"},
    {"trap": "质量不分", "trigger": false, "data": "营收 18% / 利润 22% / 毛利率稳"},
    {"trap": "久期", "trigger": true, "data": "高增速仅 3 年, 永续 g 仅 3%"}
  ],
  "safety_margin_tier": {
    "tier": 2,
    "tier_label": "高增长",
    "safety_margin_pct": 32,
    "rationale": "ROIC > 15% + 双重护城河, 适用 30-35% 档"
  },
  "fair_price_4school": {
    "value_school": {"price": 35, "logic": "DCF 内在 ¥50 × 0.7 安全边际"},
    "garp_school": {"price": 40, "logic": "forward PE 25x / CAGR 25% PEG 1"},
    "growth_school": {"price": 45, "logic": "拐点信号触发任意价"},
    "contrarian_school": {"price": 28, "logic": "PB 0.8 极端套牢承接"}
  },
  "historical_comparable": {
    "comparable_company": "X 公司",
    "comparable_path": "增速从 30% 降至 15% 时 PE 从 50x 降至 25x 用 18 月",
    "applied_to_self": "本股增速预测 30%→20% 概率 60%, 对应 PE 35x→28x 时间窗 12-18 月"
  },
  "falsification_signals": [
    "若 forward CAGR 跌破 12% (verified Q3) → 估值锚降至 PE 25x → target 重算"
  ]
}
```

## §7 反 Goodhart 输出契约 (协议 Part 7 #10)

- ❌ 形式 cite: "应用了 PEG 五陷阱" 但 peg_traps_check 数组空 / 5 类不齐
- ✅ 真 cite: peg_traps_check 5 类齐 + 每条 trigger 布尔 + data narrative

verify_audit ⑬ 必查 (iter 7 落地):
- valuation_method 字段存在
- expectation_gap_3anchor 三锚齐 (implied_growth/pricing_completeness/catalysts)
- dcf_reverse.sensitivity_3x3 是 3×3 二维数组
- peg_traps_check 数组长度 = 5, 5 陷阱 type 齐
- safety_margin_tier.tier ∈ {1,2,3,4} enum
- fair_price_4school 4 派齐
- historical_comparable.comparable_path 非空
- falsification_signals ≥1

<!-- USER_CORRECTION_START -->
- 2026-06-14 用户血泪 PEG 五陷阱: 紫金 61.5% 增速 = 周期顶非成长; 工业富联营收增 ≠ 利润增; 创新药 CXO 102% 低基数. 凡 PEG 数字必排查 5 陷阱, 任一命中标 PEG 不可用.
- 2026-06-14 用户拍板安全边际档位: 蓝筹 25-30% / 高增长 30-35% / 周期 40-50% / 困境 60%+. 随手填 -10% 给周期股 = fatal_flaw.
- 2026-06-17 iter 7 落地: 估值方法从 prompt 描述沉淀为反向 DCF + 多派别合理价 + 历史可比 SOP. 3 agent (valuation/auditor/engineer) 单 skill 覆盖, 5 层范式第 6 次复用.
<!-- USER_CORRECTION_END -->

---

## §8 与协议关系
本 skill 是 critic 6.7(估值四问)+6.10(PEG 五陷阱)+6.13(成长股估值)+planning/v4/stock-selection-theory.md(预期差三锚) 的估值层落地。每次估值产出让 verify_audit ⑬ 看到 (a) 三锚齐 (b) DCF 反向工程含三敏感性 (c) PEG 五陷阱排查 (d) 安全边际档位 (e) 多派别合理价 (f) 历史可比 (g) 可证伪信号。**目标**: 估值从"PE 35x 合理"空话变成"反向 DCF + 多派别 + 历史可比 + PEG 五陷阱排查"专业 SOP。
