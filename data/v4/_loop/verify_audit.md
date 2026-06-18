# RULE-DATA-VERIFIED 红线自动审计报告

生成: 2026-06-18T00:31:26+00:00
扫描: 49 只 stock
- 完全合规: **8** (16.3%)
- 含 fatal 违规: **41**
- 含任意违规: **41**
- fatal 违规计数: 72
- should 违规计数: 54

## 违规明细 (top 15)

### 000063 (2 项)
- [fatal] `evidence`: evidence 空但 verdict 含数字; director schema 要求 evidence min 5 项
  - value: `[] empty`
- [fatal] `debate_rounds.methodology_used`: debate_rounds 存在但任一轮均未输出 methodology_used 数组 (skill v4-debate-discipline §4 + critic 6.6 ⑤ 强制)
  - value: `missing`

### 002001 (3 项)
- [fatal] `evidence`: evidence 空但 verdict 含数字; director schema 要求 evidence min 5 项
  - value: `[] empty`
- [should] `valuation_basis.consensus_target`: consensus_target 含数字但无 verified_source(应标卖方报告/共识)
  - value: `卖方均值 ¥28-30 (+25-35% upside)`
- [fatal] `debate_rounds.methodology_used`: debate_rounds 存在但任一轮均未输出 methodology_used 数组 (skill v4-debate-discipline §4 + critic 6.6 ⑤ 强制)
  - value: `missing`

### 002050 (2 项)
- [fatal] `evidence`: evidence 空但 verdict 含数字; director schema 要求 evidence min 5 项
  - value: `[] empty`
- [fatal] `debate_rounds.methodology_used`: debate_rounds 存在但任一轮均未输出 methodology_used 数组 (skill v4-debate-discipline §4 + critic 6.6 ⑤ 强制)
  - value: `missing`

### 002156 (4 项)
- [fatal] `debate_rounds.methodology_used`: debate_rounds 存在但任一轮均未输出 methodology_used 数组 (skill v4-debate-discipline §4 + critic 6.6 ⑤ 强制)
  - value: `missing`
- [should] `evidence[2]`: verified evidence 项缺 as_of 字段且 claim 中无年份 (skill §1 铁律 4: 数字必含 as_of/年份/单位/口径)
  - value: `扣非占归母仅 51.7%,含 1.59亿非经常性损益(占48%)`
- [should] `evidence[4]`: verified evidence 项缺 as_of 字段且 claim 中无年份 (skill §1 铁律 4: 数字必含 as_of/年份/单位/口径)
  - value: `Morningstar premium 48%`
- [should] `evidence[8]`: verified evidence 项缺 as_of 字段且 claim 中无年份 (skill §1 铁律 4: 数字必含 as_of/年份/单位/口径)
  - value: `CPI+1.2%/PPI+3.9%(连3月上行)`

### 002326 (1 项)
- [fatal] `target_price`: target_price 数字存在但 evidence 数组无对应 verified_source URL/数据源
  - value: `26`

### 002371 (17 项)
- [fatal] `debate_rounds.methodology_used`: debate_rounds 存在但任一轮均未输出 methodology_used 数组 (skill v4-debate-discipline §4 + critic 6.6 ⑤ 强制)
  - value: `missing`
- [should] `evidence[1]`: verified evidence 项缺 as_of 字段且 claim 中无年份 (skill §1 铁律 4: 数字必含 as_of/年份/单位/口径)
  - value: `PE-TTM 64x`
- [should] `evidence[3]`: verified evidence 项缺 as_of 字段且 claim 中无年份 (skill §1 铁律 4: 数字必含 as_of/年份/单位/口径)
  - value: `PB 5.2x`
- [should] `evidence[4]`: verified evidence 项缺 as_of 字段且 claim 中无年份 (skill §1 铁律 4: 数字必含 as_of/年份/单位/口径)
  - value: `市值 4211 亿`
- [should] `evidence[15]`: verified evidence 项缺 as_of 字段且 claim 中无年份 (skill §1 铁律 4: 数字必含 as_of/年份/单位/口径)
  - value: `CR5 ≈ 85% (含长鑫/合肥晶合)`
- [should] `evidence[16]`: verified evidence 项缺 as_of 字段且 claim 中无年份 (skill §1 铁律 4: 数字必含 as_of/年份/单位/口径)
  - value: `客户性质: 国央企晶圆厂(战略采购+受政策约束但谈判强势)`
- [should] `evidence[20]`: verified evidence 项缺 as_of 字段且 claim 中无年份 (skill §1 铁律 4: 数字必含 as_of/年份/单位/口径)
  - value: `Top3 关键投入: 射频电源/精密阀门 MFC/真空泵`
- [should] `evidence[21]`: verified evidence 项缺 as_of 字段且 claim 中无年份 (skill §1 铁律 4: 数字必含 as_of/年份/单位/口径)
  - value: `射频电源最大供应商: MKS/AE 全球占 70%+ (受美管制威胁)`
- [should] `evidence[28]`: verified evidence 项缺 as_of 字段且 claim 中无年份 (skill §1 铁律 4: 数字必含 as_of/年份/单位/口径)
  - value: `前 3 大国产竞品: 中微(刻蚀)/拓荆(CVD)/盛美上海(清洗)`
- [should] `evidence[30]`: verified evidence 项缺 as_of 字段且 claim 中无年份 (skill §1 铁律 4: 数字必含 as_of/年份/单位/口径)
  - value: `累计专利数 4000+ 件 (覆盖等离子/真空/热场/清洗)`
- [should] `evidence[31]`: verified evidence 项缺 as_of 字段且 claim 中无年份 (skill §1 铁律 4: 数字必含 as_of/年份/单位/口径)
  - value: `客户验证周期 18-36 月 (单台百万-千万级,认证失败客户停线损失数亿)`
- [should] `evidence[32]`: verified evidence 项缺 as_of 字段且 claim 中无年份 (skill §1 铁律 4: 数字必含 as_of/年份/单位/口径)
  - value: `替代技术: AMAT/LAM/TEL (受管制阻断增量)/国内细分竞品(互补>替代)/晶圆厂自研(<3%)`
- [should] `evidence[33]`: verified evidence 项缺 as_of 字段且 claim 中无年份 (skill §1 铁律 4: 数字必含 as_of/年份/单位/口径)
  - value: `切换成本: 工艺 recipe 重新验证 6-18 月+良率风险 (高度不可逆物理驱动)`
- [should] `evidence[36]`: verified evidence 项缺 as_of 字段且 claim 中无年份 (skill §1 铁律 4: 数字必含 as_of/年份/单位/口径)
  - value: `盛美上海(688082) 营收增速 +35%/+30% 高于北方华创`
- [should] `evidence[37]`: verified evidence 项缺 as_of 字段且 claim 中无年份 (skill §1 铁律 4: 数字必含 as_of/年份/单位/口径)
  - value: `华海清科(688120) CMP 龙头 PE-TTM 50x`
- [should] `evidence[49]`: verified evidence 项缺 as_of 字段且 claim 中无年份 (skill §1 铁律 4: 数字必含 as_of/年份/单位/口径)
  - value: `覆盖刻蚀/PVD/CVD/CMP 4 大平台 + 炉管 = 唯一多平台 integrator`
- [should] `evidence[50]`: verified evidence 项缺 as_of 字段且 claim 中无年份 (skill §1 铁律 4: 数字必含 as_of/年份/单位/口径)
  - value: `前 5 大客户营收占 70% (中芯/华虹/长存/长鑫/合肥晶合)`

### 002415 (2 项)
- [fatal] `evidence`: evidence 空但 verdict 含数字; director schema 要求 evidence min 5 项
  - value: `[] empty`
- [fatal] `debate_rounds.methodology_used`: debate_rounds 存在但任一轮均未输出 methodology_used 数组 (skill v4-debate-discipline §4 + critic 6.6 ⑤ 强制)
  - value: `missing`

### 002517 (2 项)
- [fatal] `evidence`: evidence 空但 verdict 含数字; director schema 要求 evidence min 5 项
  - value: `[] empty`
- [fatal] `debate_rounds.methodology_used`: debate_rounds 存在但任一轮均未输出 methodology_used 数组 (skill v4-debate-discipline §4 + critic 6.6 ⑤ 强制)
  - value: `missing`

### 00700 (3 项)
- [fatal] `evidence`: evidence 空但 verdict 含数字; director schema 要求 evidence min 5 项
  - value: `[] empty`
- [should] `valuation_basis.consensus_target`: consensus_target 含数字但无 verified_source(应标卖方报告/共识)
  - value: `HK$711 (+52.53% Strong Buy 46 分析师)`
- [fatal] `debate_rounds.methodology_used`: debate_rounds 存在但任一轮均未输出 methodology_used 数组 (skill v4-debate-discipline §4 + critic 6.6 ⑤ 强制)
  - value: `missing`

### 01024 (1 项)
- [fatal] `target_price`: target_price 数字存在但 evidence 数组无对应 verified_source URL/数据源
  - value: `75`

### 01211 (1 项)
- [fatal] `target_price`: target_price 数字存在但 evidence 数组无对应 verified_source URL/数据源
  - value: `115`

### 01810 (2 项)
- [fatal] `evidence`: evidence 空但 verdict 含数字; director schema 要求 evidence min 5 项
  - value: `[] empty`
- [fatal] `debate_rounds.methodology_used`: debate_rounds 存在但任一轮均未输出 methodology_used 数组 (skill v4-debate-discipline §4 + critic 6.6 ⑤ 强制)
  - value: `missing`

### 06160 (4 项)
- [fatal] `target_price`: target_price 数字存在但 evidence 数组无对应 verified_source URL/数据源
  - value: `460`
- [fatal] `debate_rounds.methodology_used`: debate_rounds 存在但任一轮均未输出 methodology_used 数组 (skill v4-debate-discipline §4 + critic 6.6 ⑤ 强制)
  - value: `missing`
- [should] `evidence[1]`: verified evidence 项缺 as_of 字段且 claim 中无年份 (skill §1 铁律 4: 数字必含 as_of/年份/单位/口径)
  - value: `美元口径Q1净利2.27亿+178倍 vs 上年130万美元`
- [should] `evidence[2]`: verified evidence 项缺 as_of 字段且 claim 中无年份 (skill §1 铁律 4: 数字必含 as_of/年份/单位/口径)
  - value: `上调全年收入指引;瑞银目标价465美元/花旗453美元`

### 06990 (5 项)
- [fatal] `target_price`: target_price 数字存在但 evidence 数组无对应 verified_source URL/数据源
  - value: `520`
- [fatal] `debate_rounds.methodology_used`: debate_rounds 存在但任一轮均未输出 methodology_used 数组 (skill v4-debate-discipline §4 + critic 6.6 ⑤ 强制)
  - value: `missing`
- [should] `evidence[1]`: verified evidence 项缺 as_of 字段且 claim 中无年份 (skill §1 铁律 4: 数字必含 as_of/年份/单位/口径)
  - value: `招银国际目标价507.11港元 野村目标价544.42港元`
- [should] `evidence[3]`: verified evidence 项缺 as_of 字段且 claim 中无年份 (skill §1 铁律 4: 数字必含 as_of/年份/单位/口径)
  - value: `收到宜联生物医药逾6亿人民币和解款`
- [should] `evidence[4]`: verified evidence 项缺 as_of 字段且 claim 中无年份 (skill §1 铁律 4: 数字必含 as_of/年份/单位/口径)
  - value: `H股全流通备案获批`

### 09988 (3 项)
- [fatal] `evidence`: evidence 空但 verdict 含数字; director schema 要求 evidence min 5 项
  - value: `[] empty`
- [should] `valuation_basis.consensus_target`: consensus_target 含数字但无 verified_source(应标卖方报告/共识)
  - value: `HK$170-200 (大行均值, +30-50%)`
- [fatal] `debate_rounds.methodology_used`: debate_rounds 存在但任一轮均未输出 methodology_used 数组 (skill v4-debate-discipline §4 + critic 6.6 ⑤ 强制)
  - value: `missing`
