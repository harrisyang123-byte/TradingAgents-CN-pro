---
name: v4-five-forces-method
description: >
  Use when running v4 五力分析 agent. Mandatory for: v4-stock-force-entry/substitute/buyer/supplier/rivalry (5 专项) + v4-stock-analyst-competitive (整合者).
  Provides: ①波特 5 力量化矩阵 (level 1-5 每级数字门槛) ②五力数据契约对接 (买方 CR1/CR3/CR5+毛利率序列, 供方进口依赖度+库存周转, 同业 HHI+产能利用率, 进入者 R&D 率+专利+认证周期, 替代者技术成熟度+渗透率)
  ③五力交叉编织 SOP (互相强化/互相抵消/最弱一环/趋势) ④护城河评级 (晨星 5 类来源 + 宽/中/窄 + 持续性) ⑤five_forces 输出契约。
  这是把"五力分析"从 prompt 描述沉淀为"波特原版量化矩阵", 治"有护城河"空话浅尝。
---

# v4 五力分析 SOP skill (five-forces method)

> **用途**: 5 force 专项 agent 主用 (entry/substitute/buyer/supplier/rivalry) + competitive 整合者必读。
> **核心信念**: 五力是行业利润分配机制。"有护城河"是结论不是分析, 真分析必须给每力量化 level + 数据分子 + 交叉编织 + 趋势。

## §1 五力分析 5 铁律 (内化自 critic 6.6 辩论深度 + 数据契约 6.8 + AGENTS.md §5 5 力深做铁律)

### 铁律 1: 量化 level (1-5) + 数字门槛
- ❌ 浅: "进入壁垒高" / "买方议价强" (定性级)
- ✅ 深: "进入壁垒 level 4 (high): 客户验证周期 18 月 + 累计专利 230 + 研发费用率 8.5%"
- 实操: 每力 level (1=极低, 2=低, 3=中, 4=高, 5=极高) 必含 ≥3 个数字门槛对应 (见 §2 各力数据契约)

### 铁律 2: 5 年趋势 + 同业相对位置
- ❌ 浅: "护城河强大" (永远对永远不可证伪)
- ✅ 深: "5 年趋势: level 3→3→4→4→5 (上行), 同业平均 level 3.5, 本股 top quartile"
- 实操: 每力给 5 年序列 + 同业 top 3 当前 level 对比

### 铁律 3: 数据契约对接 (硬要求, AGENTS.md §5)
每力必查 `app/services/v4/stock_source.py` COMPETITIVE_DATA_SCHEMA 字段:
- **买方力**: 客户集中度 CR1/CR3/CR5 + 客户性质 + 毛利率近 3 年序列 + 净利率近 3 年序列 + 应收账款周转天数
- **供方力**: 前 3 大关键投入 + 最大供应商占比 + 进口依赖度/管制清单状态 + 库存周转天数
- **同业**: 行业 CR3/CR5/HHI + 产能利用率 + 前 3 大竞品(含份额)
- **进入威胁**: 研发费用率 + 累计专利数 + 客户验证周期(月)
- **替代威胁**: 替代技术清单(成熟度+渗透率) + 客户切换成本(定性+量化, 如切换成本/年营收)

### 铁律 4: 交叉编织 (5 力 ≠ 5 段平铺, A/B 测试已证 5 段平铺扣分)
必须识别:
- **互相强化** (双重锁定): 如进入壁垒高 + 供方议价权强(国产替代) → 利润率与定价权双锁
- **互相抵消** (天花板): 如买方议价强 + 出口管制锁定客户 → 议价权有上限
- **最弱一环** (护城河上限): 5 力中最弱者决定整体上限
- **趋势方向**: 整体在加宽/收窄/稳定, 哪一力是关键推动

### 铁律 5: 可证伪信号 (达里奥, 对齐 critic 6.16②)
每个核心结论(护城河强/最弱一环/趋势)配 ≥1 个绝对阈值反向信号:
- "若买方力 level 升至 5 (具体: 客户 A 出货占比 > 50%), 我承认护城河收窄"
- "若 HHI 跌破 1500 (verified Q3), 我承认竞争格局恶化"

## §2 5 力量化矩阵 (level 1-5 数字门槛)

### Force 1: 潜在进入者威胁 (entry threat)
| level | 含义 | 数字门槛 (≥1 满足即可) |
|---|---|---|
| 1 极低 | 无人能进 | 客户验证 >36 月 / 累计专利 >500 / R&D 率 >12% / 监管牌照 + 资本壁垒 >50 亿 |
| 2 低 | 极少人能进 | 客户验证 18-36 月 / 专利 200-500 / R&D 率 8-12% |
| 3 中 | 部分能进 | 验证 6-18 月 / 专利 50-200 / R&D 率 4-8% |
| 4 高 | 多数能进 | 验证 < 6 月 / 专利 < 50 / R&D 率 < 4% |
| 5 极高 | 谁都能进 | 无壁垒, 同质化竞争 |

**对 bull 是利好**: level 1-2 (高壁垒锁定利润)
**对 bear 是利空**: level 4-5 (新进入者将摊薄利润)

### Force 2: 替代品威胁 (substitute threat)
| level | 含义 | 数字门槛 |
|---|---|---|
| 1 极低 | 无替代 | 替代技术尚未实验室验证 / 成熟度 <2 (TRL 1-2) |
| 2 低 | 远期替代 | TRL 3-5 / 渗透率 < 1% / 切换成本 > 年营收 50% |
| 3 中 | 中期替代 | TRL 6-7 / 渗透率 1-10% / 切换成本 20-50% |
| 4 高 | 近期替代 | TRL 8-9 / 渗透率 10-30% / 切换成本 < 20% |
| 5 极高 | 已被替代 | TRL 9 + 渗透率 > 30% (柯达数码同型) |

### Force 3: 买方议价力 (buyer power)
| level | 含义 | 数字门槛 |
|---|---|---|
| 1 极低 | 卖方主导 | CR1 < 5% (单客户占比) / 毛利率持续 > 60% / 应收周转 < 30 天 |
| 2 低 | 卖方略强 | CR1 5-10% / 毛利率 40-60% / 应收 30-60 天 |
| 3 中 | 平衡 | CR1 10-20% / 毛利率 25-40% / 应收 60-90 天 |
| 4 高 | 买方略强 | CR1 20-40% / 毛利率 15-25% / 应收 90-150 天 |
| 5 极高 | 买方主导 | CR1 > 40% / 毛利率 < 15% / 应收 > 150 天 (大客户砍单同型) |

### Force 4: 供方议价力 (supplier power)
| level | 含义 | 数字门槛 |
|---|---|---|
| 1 极低 | 多供应商竞争 | 最大供应商占比 < 10% / 进口依赖 < 10% / 库存周转 < 60 天 |
| 2 低 | 供应商略弱 | 最大占比 10-20% / 进口 10-25% / 库存 60-90 天 |
| 3 中 | 平衡 | 最大占比 20-40% / 进口 25-50% / 库存 90-120 天 |
| 4 高 | 供应商略强 | 最大占比 40-60% / 进口 50-80% / 库存 120-180 天 |
| 5 极高 | 供应商主导 | 最大占比 > 60% / 进口 > 80% / 列入管制清单 |

### Force 5: 同业竞争烈度 (internal rivalry)
| level | 含义 | 数字门槛 |
|---|---|---|
| 1 极低 | 寡头垄断 | HHI > 5000 / CR3 > 80% / 产能利用率 > 90% |
| 2 低 | 少数主导 | HHI 2500-5000 / CR3 60-80% / 产能利用率 80-90% |
| 3 中 | 适度竞争 | HHI 1500-2500 / CR3 40-60% / 产能利用率 70-80% |
| 4 高 | 激烈竞争 | HHI 1000-1500 / CR3 20-40% / 产能利用率 60-70% |
| 5 极高 | 完全竞争 | HHI < 1000 / CR3 < 20% / 产能利用率 < 60% (光伏/钢铁同型) |

## §3 五力交叉编织 SOP (5 段平铺扣分, A/B 测试已证)

### 3.1 互相强化矩阵 (利润放大)
| force_a | force_b | 强化机制 | 例 |
|---|---|---|---|
| 进入壁垒高 | 供方议价弱 | 双重锁定: 自己进入难 + 上游分散好谈 | 茅台 (酒厂资质 + 高粱供应分散) |
| 替代威胁低 | 买方议价弱 | 长期定价权: 无替代 + 客户分散 | 创新药专利期 |
| 同业寡头 | 进入壁垒高 | 寡头分赃: 内部默契 + 无新进入者 | 中国白酒 top3 |

### 3.2 互相抵消矩阵 (天花板)
| force_a | force_b | 抵消机制 | 例 |
|---|---|---|---|
| 买方议价强 | 出口管制锁客户 | 议价权有上限 (客户走不掉) | 半导体出口管制下的设备厂 |
| 进入壁垒高 | 替代威胁高 | 守得住但对手在外 (柯达 vs 数码) | 传统胶片 |
| 供方议价强 | 买方议价强 | 两头挤压利润 | 代工厂(富士康同型) |

### 3.3 最弱一环 (护城河上限)
- 5 力中 level 最低者决定护城河整体上限
- 例: 4/3/3/4/3 → 上限 = 同业竞争 (level 3 中等)
- **铁律**: weakest_link 必单点指出, 不可平摊

### 3.4 趋势方向 (5 年序列)
- 整体在加宽 (≥3 力 level 上行) / 收窄 (≥3 力下行) / 稳定 (混合)
- 关键推动力: 哪一力变化最大 (≥1 level 跳动)

## §4 护城河评级 (晨星 5 类来源 × 宽/中/窄 × 持续性)

### 5 类来源 (源自 Morningstar Wide Moat 研究, critic 6.13 同型对照)
1. **无形资产** (品牌/专利/牌照): 茅台/苹果/恒瑞专利
2. **转换成本** (用户切换贵): SAP/Salesforce/微信
3. **网络效应** (用户多→更值钱): 微信/抖音/Visa
4. **成本优势** (规模/资源/工艺): 沙特阿美/海螺水泥/比亚迪
5. **有效规模** (市场容下少数玩家): 美国铁路/中国白酒高端

### 评级
- **宽 (wide)**: ≥2 类来源 + ≥3 力 level ≥4 + 5 年稳定/上行 + 持续性 ≥10 年
- **中 (narrow)**: 1-2 类来源 + 2-3 力 level ≥4 + 持续性 5-10 年
- **窄 (none)**: 0-1 类来源 + 多力 level ≤3 + 持续性 < 5 年

### 持续性判定
- ≥10 年: 多重护城河 + 行业稳定 (酒/医药专利)
- 5-10 年: 单点护城河 + 技术周期内 (半导体设计)
- 1-3 年: 窗口期 (TWS/AIGC 早期)

## §5 five_forces 输出契约 (5 force + competitive 输出 JSON 必填)

### 5 force 专项输出 (entry/substitute/buyer/supplier/rivalry 各自)
```json
"force_analysis": {
  "_doc": "★ iter 6 落地, skill v4-five-forces-method §5 输出契约, verify_audit ⑫ 必查",
  "force_type": "entry|substitute|buyer|supplier|rivalry",
  "level": 4,
  "level_5y_trend": [3, 3, 4, 4, 4],
  "data_thresholds_hit": [
    {"metric": "客户验证周期", "value": "18 月", "level_threshold": "level 4 high (≥18 月)", "verified_source": "akshare 公告/年报"}
  ],
  "industry_avg_level": 3.5,
  "position_vs_peers": "top_quartile (top 25%)",
  "trend_direction": "stable|upward|downward",
  "key_driver": "推动趋势的核心因子(如'专利数从 100 增至 230')",
  "falsification_signal": "若客户验证周期跌破 12 月 → level 降为 3, 承认壁垒收窄"
}
```

### competitive 整合者输出 (5 力交叉编织)
```json
"five_forces_synthesis": {
  "_doc": "★ iter 6 落地, 整合 5 force 专项产出, 不可平铺",
  "five_levels": {"entry": 4, "substitute": 2, "buyer": 3, "supplier": 2, "rivalry": 3},
  "mutual_reinforcement": [
    {"force_a": "entry", "force_b": "supplier", "mechanism": "国产替代下供应链分散 + 自身高壁垒", "amplification": "利润率天花板 +5pct"}
  ],
  "mutual_offset": [
    {"force_a": "buyer", "force_b": "出口管制", "mechanism": "议价权 vs 客户锁定", "ceiling": "毛利率上限 35%"}
  ],
  "weakest_link": "buyer (level 3) — 客户 CR3 偏高, 决定护城河上限",
  "trend": "upward (3 力上行) — 关键推动: 专利累计 +130 件 (5 年)",
  "moat_rating": "wide|narrow|none",
  "moat_sources": ["intangible_assets", "switching_cost"],
  "moat_durability": "10年+ (双重护城河 + 行业稳定)",
  "falsification_signals": ["若 HHI 跌破 1500 → moat 降级 narrow", "若 CR1 > 40% → buyer level 升 5 → moat 收窄"]
}
```

## §6 反 Goodhart 输出契约

- ❌ 形式 cite: level=4 但 data_thresholds_hit 空数组 (level 凭感觉填)
- ✅ 真 cite: level=4 + 必有 ≥1 条 data_thresholds_hit 含 verified_source

verify_audit ⑫ 必查 (iter 6 落地):
- force_analysis.level ∈ {1,2,3,4,5} enum
- level_5y_trend 数组长度 ≥3
- data_thresholds_hit 数组 ≥1 + 每条含 metric/value/level_threshold/verified_source
- competitive.five_levels 5 个 force 都填
- mutual_reinforcement OR mutual_offset 至少有 1 项
- weakest_link narrative 非空
- moat_rating ∈ {wide, narrow, none} enum
- falsification_signals 数组 ≥1

<!-- USER_CORRECTION_START -->
- 2026-06-13 用户拍板: 5 力深做不增 agent 改 5 力专项+整合者模式 (A/B 测试 5 段平铺扣分, 整合者交叉编织加分). competitive agent 升级为整合者.
- 2026-06-17 iter 6 落地: 6 agent (5 force 专项 + 1 competitive 整合者) zero skill cite. 单 skill 覆盖 6 agent (规则 11 切片≠单 agent), 5 层防御纵深第 5 次复用 (规则 12). PRIMARY (5 force) + INTEGRATOR (competitive) 模式扩展 iter 5 PRIMARY/SECONDARY 范式.
<!-- USER_CORRECTION_END -->

---

## §7 与协议关系
本 skill 是 critic 6.6(辩论深度) + 6.8(数据契约) + 6.13(成长股估值含护城河) + AGENTS.md §5 5 力深做铁律 的五力分析层落地。每次 5 force 专项 + competitive 整合者产出都应让 verify_audit ⑫ 看到 level enum 锁 + 数据阈值 verified + 交叉编织非平铺 + 护城河评级 enum 锁 + 可证伪信号。**目标**: 五力分析从"有护城河"空话变成"波特原版量化矩阵 + 交叉编织"。
