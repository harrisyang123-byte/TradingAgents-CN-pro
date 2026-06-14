# 价值创造维度补全设计 (value-creation-augment) — 质量优先版

> 用户纠正: **首要目标是最好的分析质量,而非不改变存量。用户思维第一。** 先定义"最好的个股分析",再想存量怎么升级到这个标准——不是想怎么少动存量、不是豁免旧版。

## 0. 第一性原理:什么是"判断一家公司未来值多少钱"的最好分析?

站在投资者(用户)角度,一份能帮我持久盈利的个股分析必须完整回答三件事:

```
A. 这家公司未来能值多少钱?  (价值创造 — 内在价值)
B. 市场现在/未来愿意给什么价? (价格形成)
C. 两者差距 = 我的机会在哪、买多少、何时认错  (交集决策)
```

### 完整骨架(融合用户框架 + v4 已有,缺的标 🆕)

**A. 价值创造(决定内在价值)**
- A1 行业空间: 🆕TAM 绝对天花板 + 🆕渗透率%与阶段 + 竞争格局(已有 five_forces) + 行业生命周期 → **决定成长上限**
- A2 商业模式 + 护城河: 🆕商业模式分类(现金流特征/重复客户/高周转vs高利润) + 护城河类型/深度/期限(已有 moat)
- A3 管理层: 🆕资本配置质量(再投资ROIC/并购成败/分红回购) + 🆕坦诚执行力(指引兑现率) → 巴菲特/段永平最看重
- A4 财务质量: 🆕ROIC vs WACC(创造还是毁灭价值,最关键) + 🆕收入质量(量/价/并购拆解) + 利润率趋势(已有) + 现金流质量(已有)

**B. 价格形成(决定买入价合理性)**
- B1 绝对估值: 🆕正向 DCF 内在价值锚
- B2 相对估值: 同业/历史 PE/PB/PS/PEG(已有 comparable_path)
- B3 反向推演: 当前价隐含什么预期(✅ v4 强项,反向 DCF)
- B4 市场面: 风格/利率/资金结构/流动性(部分有 forward_view,需贯穿)
- B5 催化剂与风险 + 退出纪律(已有 forward_view + sell_discipline)

**C. 交集决策**: 内在价值 vs 现价 → 安全边际档位 → 多派别合理价 → 反骑墙站队 + 仓位 + 买点 + 止损(✅ v4 强项)

> v4 当前: B3/C 是强项, B2/B5 充分; **A1/A3/A4/B1 是硬缺口** → 这正是补全目标。补全后才是"完整骨架"。

## 1. 架构归属(MECE,不新增 agent — 4 维是已有分析师职责的本职延伸)

| 维度 | 归属 | 理由 |
|---|---|---|
| A1 TAM/渗透率 | valuation 分析师产出(消费 industry chokepoint + data-desk 行业规模) | 成长空间是估值上限的输入,估值本职 |
| A3 管理层资本配置 | financial 分析师 + director 段永平视角硬性组成 | 资本配置是财务质量本职 |
| A4 ROIC vs WACC | financial 分析师 | 财务质量核心指标本职 |
| B1 正向 DCF | valuation 分析师(已有反向 DCF,加正向) | 估值本职 |

## 2. 数据契约:新字段进 MUST(做好分析的必须项),缺了就 exit=4 逼着补

**新建第 4 组 MUST「价值创造组」**(契约 18 → 24 MUST):
- `roic`(或 NOPAT+invested_capital 让 agent 算) — 价值创造核心
- `wacc_estimate`(无风险利率+beta+风险溢价估算,允许 estimated) — ROIC 对比基准
- `tam_size`(行业 2030 绝对天花板,亿/万亿级) — 成长上限
- `penetration_rate`(当前渗透率% + 阶段定性,允许 estimated) — 成长弹性判断
- `capital_allocation_5y`(近5年 回购/分红/并购/capex 去向 + ROI) — 管理层水平
- `fcf_latest`(自由现金流 = 经营现金流 - capex) — 正向 DCF 输入

**为什么进 MUST 不进 SHOULD**: 这 6 项是回答"公司值多少钱"的必须输入。缺了分析就是瞎的一半。exit=4 阻断 = 逼主 agent 联网补全,这是质量保障不是障碍。**取不到的标 unattainable(诚实降级机制已存在),不是用 SHOULD 蒙混**。

## 3. critic:统一加"价值创造四问"必查,不分级不豁免

新增 critic 必查(所有 stock 统一,不按 schema_version 豁免):
1. TAM 是否支撑当前成长假设?(成长股关键)
2. ROIC vs WACC 是创造还是毁灭价值?(配不配得上估值溢价)
3. 管理层资本配置加分还是减分?(影响 confidence + 长期持有意愿)
4. 正向 DCF 内在值 与 反向 DCF + 多派别合理价 是否三角验证一致?

**旧版没达标就是 NEEDS_CHANGES** — 这是诚实,不是问题。它就该被回补到新标准。豁免=自欺欺人。

## 4. director:新增 value_creation 块 + 价值创造四问铁律

schema 加 `value_creation` 块(A1-A4 结论)+ `dcf_intrinsic`(B1)。director 拍板前过"价值创造四问",结论与原 verdict 冲突时必须 reconcile(改 verdict 或说明为何忽略),reflection 记录"补 4 维后 what_changed"。

## 5. 前端:全部融入现有 ②③ 区块,不新增模块

| 新维度 | 落点 |
|---|---|
| A1 TAM/渗透率 | ② "🎯 投什么"旁加 "📈 成长空间" + ③ 估值推导步 |
| A3 管理层资本配置 | ② "🏰 凭什么"旁 + ③ 四维质量闸门·段永平视角 |
| A4 ROIC vs WACC | ② "💰 估值"行扩展 + ③ 财务步 |
| B1 正向 DCF | ③ 估值推导步内与反向 DCF 并列 |

全部在已有 valuation_basis/四维闸门/②核心区**扩展字段渲染**,不加 Tab/section/路由。

## 6. 存量 24 只升级路径(升级到新标准,不是打补丁豁免)

对每只已 ACCEPT 的 stock:
1. 主 agent 联网补 6 项价值创造数据(ROIC/WACC/TAM/渗透率/资本配置/FCF) → 重跑 collect 契约校验,缺 MUST 则 exit=4 直到补齐
2. spawn "价值创造分析"subagent(塞 director vN 完整 JSON + 新数据)产出 A1/A3/A4/B1
3. director 融入 + **重新估值**: 正向DCF内在值 vs 现价改不改 rating;ROIC<WACC 降不降级;TAM 调不调成长空间。真重估
4. spawn critic 按**新标准(含价值创造四问)**复核 → ACCEPT 才落盘
5. 落盘 vN+1

**不重跑已扎实的部分**(多空 R1-R3/3风险/五力论据保留),但**估值结论必须按完整骨架重新审视**。若发现原结论因缺 4 维而偏差,就改——这正是补全的价值。

## 7. 下游影响(质量优先下的诚实评估)

- 存量缺 MUST → exit=4 → 必须补全才能跑(这是质量保障,接受)
- critic 统一新标准 → 存量回补前若重过会 NEEDS_CHANGES(正确,它就该回补)
- 回补后 rating/target 若变 → 对应 alloc:industry/portfolio 置黄重跑(接受,因为结论更准了)
- 不为"省事"牺牲质量

## 8. 落地步骤

1. [ ] contract 加 6 个 MUST(价值创造组,18→24)
2. [ ] financial 分析师加 ROIC/WACC + 资本配置 + 收入质量
3. [ ] valuation 分析师加正向 DCF + TAM/渗透率
4. [ ] director schema 加 value_creation + dcf_intrinsic + 四问铁律
5. [ ] critic 加价值创造四问(统一,不豁免)
6. [ ] 前端 + build_stock_detail 融入现有区块
7. [ ] 24 只升级回补(补数据→分析→重估→critic→落盘)
8. [ ] 辩证终审(含价值创造一致性) + 快照 + commit
