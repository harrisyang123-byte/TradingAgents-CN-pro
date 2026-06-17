---
name: v4-financial-analysis
description: >
  Use when running v4 stock 财务分析 agent. Mandatory for: v4-stock-analyst-financial.
  亦推荐用于: v4-stock-analyst-competitive(融合财务证据), v4-stock-analyst-valuation(财务质量是估值的根),
  v4-stock-bull/bear (引用财务分子做数据论证).
  Provides: ①财务 5 铁律(verified数字/分子模型/趋势序列/红旗对照/可证伪) ②杜邦 ROE/ROIC 拆解 SOP
  ③现金流质量 vs 净利润 SOP ④5 类红旗清单(乐视/康美/瑞幸同型) ⑤可比+趋势分析 SOP ⑥financial_analysis 输出契约。
  这是把"财务分析"从角色 prompt 沉淀为"会计师 SOP", 治"产品 mix 改善"等空话浅尝。
---

# v4 财务分析 SOP skill (financial analysis)

> **用途**: stock-analyst-financial 主用, competitive/valuation/bull/bear 引用财务分子时必读。
> **核心信念**: 财务分析是个股 verdict 的事实底座。空话"利润率改善/增速强劲"= 浅尝, 必须给分子模型 + verified 数字 + 红旗对照 + 可证伪信号。

## §1 财务分析 5 铁律 (内化自 critic 6.1 产品分子模型 + 6.5 数据使用追溯 + 通富同型治理)

### 铁律 1: verified 数字 + as_of 报告期 + 单位口径
- ❌ 浅: "公司增长强劲" / "净利率提升" / 凭训练记忆补数字
- ✅ 深: "营收 256 亿(+18.5% YoY, 2025年报, 来源 akshare.stock_financial_abstract(symbol='600519', as_of='20251231'))"
- 实操: 每个数字配 (a) 报告期 as_of (b) 单位 (¥亿/$B/%/x) (c) YoY/QoQ 标注 (d) verified_source

### 铁律 2: 产品分子模型 (替代 "mix 改善" 空话, critic 6.1)
- ❌ 浅: "高毛利产品占比提升" / "结构升级"
- ✅ 深: "产品 A 营收 X 亿(占比 Y%) × 毛利率 Z% = 净利贡献 N 亿; 产品 B 营收..."
- 实操: 任何"利润率改善/成长来源/mix 改善"声明必须能用产品分子拆出来, 加总到全公司净利

### 铁律 3: 3-5 年趋势序列 (不是单点数字)
- ❌ 浅: "ROE 22%" (单点不可证伪)
- ✅ 深: "ROE 5 年序列: 18%→20%→22%→24%→22% (2021-2025), 趋势上行但 2025 拐头, 主驱动是净利率(杜邦)"
- 实操: 关键比率(ROE/ROIC/毛利率/净利率/周转率)必给 ≥3 年序列, 标注趋势方向(上行/下行/拐点) + 主驱动因子(杜邦三因子哪个变了)

### 铁律 4: 红旗对照清单 (5 类同型)
- 任何高净利/高 ROE/高增速必须做"5 类红旗"对照(详见 §4), 任一红旗触发必标注
- 历史同型: 乐视(应收激增) / 康美(现金流 vs 净利背离) / 瑞幸(虚增收入) / 康得新(关联交易) / 暴风(商誉减值)

### 铁律 5: 可证伪信号 (达里奥极度求真, 对齐 critic 6.16②)
- ❌ 浅: "高增长可持续" (永远对永远不可证伪)
- ✅ 深: "若 2026Q3 单季净利率 < 18% 连续 2 季, 高增长假设失效"
- 实操: 每个核心结论(高增长/高 ROE/护城河强)配 ≥1 个绝对阈值反向信号

## §2 杜邦 ROE/ROIC 拆解 SOP (替代被杠杆污染的 ROE)

### 杜邦 ROE 三因子 (基础诊断)
```
ROE = 净利率 × 总资产周转率 × 权益乘数
    = (净利/营收) × (营收/总资产) × (总资产/权益)
```
**操作步骤**:
1. 取最近 5 年三因子序列(akshare.stock_financial_abstract)
2. 看哪个因子在变(高净利率主导=好生意 / 高周转主导=运营效率 / 高杠杆主导=危险信号)
3. 高杠杆驱动的 ROE 必标"被杠杆污染", 改用 ROIC 验证

### ROIC vs WACC (价值创造硬指标, critic 6.9 ②)
```
ROIC = NOPAT / 投入资本
     = 净利 × (1 - 税率) / (有息负债 + 股东权益 - 货币资金)
```
**WACC 估算 (本土 A 股 8-12% 区间)**:
- 蓝筹白马: WACC ≈ 8-9%
- 高成长 (科技/医药): WACC ≈ 10-12%
- 周期股: WACC ≈ 9-11% (周期顶部 +1pct, 周期底部 -1pct)

**判定**:
- ROIC > WACC + 5pct = 显著创造价值 (好生意)
- ROIC ≈ WACC ± 2pct = 持平 (普通生意)
- ROIC < WACC = 毁灭价值 (越增长越亏, 中芯/京东方式重资产陷阱)
- 周期底部 ROIC 暂低需说明是结构性还是周期性

**ROIC 计算稳健性检验** (用户 A/B 测试结论, 计算法 85 完胜估算法 35):
- 缺 NOPAT/有息负债等细科目时, 给 ROIC 区间不给伪精确点值
- 区间两端做"创造/毁灭价值"翻转检验 — 两端同向则结论稳健
- 标注口径不确定性(少数股东权益/合资厂/投资资产剔除与否影响 ROIC 几个 pct)
- ❌ 拍脑袋"ROIC=5.4%"无原始科目 = 浅尝 + RULE-DATA-VERIFIED 红线违规

## §3 现金流质量 vs 净利润 SOP (盈余质量诊断)

### 现金/净利比 (核心诊断)
```
盈余质量 = 经营现金流 (OCF) / 归母净利润
```
**判定**:
- 比率 ≥ 1.0 持续 3 年 = 真金白银, 盈余质量优 (茅台 ≈ 1.2)
- 比率 0.7-1.0 = 正常, 关注应收/存货变化
- 比率 < 0.7 持续 2 年 = 红旗, 必查应收激增/存货堆积/在建工程异常
- 比率 < 0 = 严重红旗, 利润是会计记账(乐视/康得新同型)

### 自由现金流 (FCF, 巴菲特股东盈余)
```
FCF = OCF - 维持性 capex
    ≈ OCF - 资本开支 (粗估; 精算需拆分维持 vs 扩张)
```
**用 FCF 而非净利的理由**: 净利可被会计调节(应收/存货/商誉/折旧), FCF 是真金白银流入。

**判定**:
- FCF 持续为正且 ≥ 净利的 70% = 优质生意 (茅台/海天)
- FCF 经常 < 0 但净利 > 0 = 重资产/烧钱扩张, 需查 ROIC 是否补偿
- FCF 与净利持续背离 = 警惕利润质量(康美/瑞幸同型)

### 应收 / 存货 / 在建工程 三个红旗指标
- **应收账款增速 > 营收增速 1.5 倍** 持续 2 年 = 收入质量恶化(乐视同型)
- **存货增速 > 营收增速 1.5 倍** 持续 2 年 = 销售放缓堆库存(三只松鼠同型)
- **在建工程 / 总资产 > 30%** = 重资产扩张, 必查未来 capex 是否能转产

## §4 5 类红旗清单 (反向锚, 对照 Part 2.7 死亡清单)

| 红旗类型 | 数字诊断 | 历史同型 |
|---|---|---|
| **应收激增 (收入质量)** | 应收/营收 > 30% 且增速 > 营收增速 1.5x | 乐视/康得新 |
| **现金流背离 (盈余质量)** | OCF/净利 < 0.7 持续 2 年 | 康美/瑞幸 |
| **商誉减值 (并购质量)** | 商誉/净资产 > 50% + 子公司业绩承诺到期 | 暴风/坚瑞沃能 |
| **关联交易 (公司治理)** | 关联交易占营收 > 20% | 康得新/獐子岛 |
| **大股东占款 (财务造假)** | 其他应收款 > 5% 总资产 + 大股东质押率 > 70% | 康美/獐子岛 |

**critic 6.16 ④对接**: 任一红旗触发必入 pre_mortem.fundamental_double_kill.trigger_indicators 数组 + historical_analog 引用对应案例。

## §5 可比公司 + 趋势分析 SOP

### 可比公司选择 3 原则 (critic 6.7 价值创造四问对接)
1. **同业务**: 主营产品/客户结构/技术路线相近 (≥3 家)
2. **同阶段**: 营收规模/增速段相近 (避免成熟期 vs 成长期混比)
3. **同地理**: A 股 vs 港股 vs 美股估值体系不同, 跨市场可比需调整

### 财务可比性检查
- 会计准则: A 股 CAS / 美股 GAAP / 港股 IFRS, 跨准则需调整
- 报告期: 财年同步(国内自然年 / 美股部分财年 9 月)
- 一次性损益: 剔除非经营性收益(如政府补贴/资产处置)算可比净利率

### 5 年趋势 + 同业相对位置
- 财务比率必给本股 5 年序列 + 同业 top3 当年值对比
- 标注本股位置 (top quartile / median / bottom)
- 看趋势是收敛/分化, 决定护城河在加深/收窄

## §6 financial_analysis 输出契约 (stock-analyst-financial 输出 JSON 必填)

```json
"financial_analysis": {
  "_doc": "★ iteration 5 落地, skill v4-financial-analysis §6 输出契约, verify_audit ⑪ 必查",
  "verified_period": "as_of 2025年报 (akshare.stock_financial_abstract(symbol='...', as_of='20251231'))",
  "dupont_5y": {
    "net_margin": [18.5, 20.1, 22.3, 24.5, 22.0],
    "asset_turnover": [0.85, 0.88, 0.90, 0.92, 0.90],
    "equity_multiplier": [1.15, 1.18, 1.20, 1.22, 1.20],
    "roe_5y": [18.2, 20.9, 24.1, 27.5, 23.7],
    "main_driver": "净利率主导(2021→2024 +6pct), 但 2025 拐头(净利率 -2.5pct)",
    "leverage_polluted": false
  },
  "roic_vs_wacc": {
    "roic_range": [22.0, 25.0],
    "wacc_estimate": 10.0,
    "verdict": "显著创造价值 (ROIC 区间 22-25% > WACC 10% +12-15pct)",
    "robustness_check": "区间两端均 > WACC, 创造价值结论稳健"
  },
  "cashflow_quality": {
    "ocf_to_net_income_5y": [1.10, 1.15, 1.20, 1.18, 1.05],
    "fcf_5y": [85, 95, 110, 120, 100],
    "verdict": "盈余质量优 (OCF/净利 5 年均 >1, 2025 略降至 1.05 关注)"
  },
  "product_molecule_model": {
    "products": [
      {"name": "高端系列", "revenue": 180, "revenue_pct": 70, "gross_margin_pct": 92, "net_contribution": 95},
      {"name": "中端系列", "revenue": 60, "revenue_pct": 24, "gross_margin_pct": 60, "net_contribution": 22}
    ],
    "growth_attribution": "70% 来自高端系列量增 + 30% 来自提价"
  },
  "red_flags_check": [
    {"type": "应收激增", "trigger": false, "data": "应收/营收 8.5%, 增速 +12% < 营收 +18.5%, 健康"},
    {"type": "现金流背离", "trigger": false, "data": "OCF/净利 5 年均 >1, 健康"},
    {"type": "商誉减值", "trigger": false, "data": "商誉/净资产 3%, 健康"},
    {"type": "关联交易", "trigger": false, "data": "关联交易占营收 5%, 健康"},
    {"type": "大股东占款", "trigger": false, "data": "其他应收款 0.8% 总资产, 健康"}
  ],
  "comparables": {
    "peers": ["公司B", "公司C", "公司D"],
    "current_position": "top_quartile (ROE 22% vs 同业中位 15%)",
    "trend": "5 年均 top_quartile, 护城河稳定"
  },
  "falsification_signals": [
    "若 2026Q3 单季净利率 < 18% 连续 2 季 → 高增长假设失效",
    "若应收/营收 > 15% (verified Q3 数据) → 收入质量预警, 启动红旗 1 监控"
  ]
}
```

## §7 反 Goodhart 输出契约 (协议 Part 7 #10)

- ❌ 形式 cite: "应用了杜邦拆解" 但 dupont_5y 数据全 null/数字数组长度 < 3
- ✅ 真 cite: dupont_5y 给完整 5 年序列 + main_driver narrative + leverage_polluted 布尔 + 引证 evidence_ref

verify_audit ⑪ 必查 (iteration 5 落地): financial_analysis 字段存在 + dupont_5y 数组长度 = 5 + roic_range 是数字区间 + cashflow_quality.ocf_to_net_income_5y 长度 = 5 + product_molecule_model.products 数组每项含 revenue/gross_margin_pct/net_contribution + red_flags_check 5 类齐 + falsification_signals 数组 ≥1。

<!-- USER_CORRECTION_START — 用户纠错沉淀, 禁日常编辑改写 -->
- 2026-06-14 用户血泪: ROIC A/B 测试结论 — 估算法 35 vs 计算法 85, 主 agent 估精确点值 = 拍脑袋。计算密集项 ROIC 必用 AKShare 细科目精算或给区间+稳健性检验, 严禁伪精确点值。
- 2026-06-14 用户拍板: 价值创造四问 — TAM/ROIC vs WACC/管理层资本配置/正向 DCF 三角验证 — 任一缺失 fatal_flaw NEEDS_CHANGES (critic 6.9).
- 2026-06-17 自进化循环 iteration 5 落地: 财务分析从角色 prompt 沉淀为会计师 SOP. 4 stock-analyst zero skill cite 同 iteration 3 辩手层同型, 单 skill 覆盖多 agent (规则 11). 5 层防御纵深第 4 次复用(规则 12).
<!-- USER_CORRECTION_END -->

---

## §8 与协议的关系

本 skill 是 critic 6.1(产品分子模型) + 6.5(数据使用追溯) + 6.9(价值创造四问) + 6.13(成长股估值) + 6.16(pre_mortem 红旗对接) 的财务分析层落地。每次 stock-analyst-financial 产出都应让 verify_audit ⑪ 看到 (a) 杜邦+ROIC 完整 (b) 现金流 5 年序列 (c) 产品分子模型 (d) 5 类红旗对照 (e) 可证伪信号 ≥1。**目标**: 财务分析从"利润率改善"空话变成"会计师专业 SOP"。
