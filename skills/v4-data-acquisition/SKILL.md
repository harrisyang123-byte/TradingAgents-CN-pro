---
name: v4-data-acquisition
description: >
  Use when running v4-data-desk agent (唯一联网取数 agent). Mandatory for: v4-data-desk.
  Provides: ①取数 5 铁律(verified URL/多源交叉/失败降级/年份单位口径/不编造)
  ②AKShare 函数白名单(财务/行情/个股信息) ③web_search 源优先级(权威/二手/不算来源)
  ④失败降级链(权威→次级→estimated→绝不编造) ⑤RULE-DATA-VERIFIED 红线对接(verify_audit URL_RE 命中)。
  这是把数据采集从"prompt 描述"沉淀为"工程师 SOP"的核心 skill, 治通富 $157B 事故根因。
---

# v4 数据采集 SOP skill (data acquisition)

> **用途**: v4-data-desk 唯一联网取数 agent 的方法论锚。所有下游(分析师/director/critic)的事实底座。
> **核心信念**: 数据采集是源头, 源头不实=全链浅尝。verify_audit ⑥-⑧ 能拦空字段, 但拦不住"选错源/源不权威/年份错位/单位混乱", 这些必须靠 SOP 治。

## §1 取数 5 铁律 (内化自 RULE-DATA-VERIFIED 红线 + 通富 $157B 事故沉淀)

每个数字字段必须做到 5 件事, 缺一即 verify_audit fatal_flaw:

### 铁律 1: verified URL 命中 (verify_audit URL_RE 兼容)
- ❌ 浅: source="verified" / "akshare" / "据某券商研报" / "训练记忆"
- ✅ 深: source="https://data.eastmoney.com/..." / "akshare.stock_financial_abstract(symbol='002001')" / "Yole 2024年报《先进封装市场展望》" / "工信部 2024 公告 第N号"
- 实操: source 必须命中 v4_verify_audit.py URL_RE: https?:// 或 akshare.func() 调用 或 数据源具体函数名 或 财报年份(如"2024年报"/"2024Q3报") 或 权威机构名(IDC/Gartner/Yole/marketsandmarkets/工信部)

### 铁律 2: 多源交叉 (TAM 类硬要求 ≥3 独立源)
- ❌ 浅: 只引一篇 IDC 报告就给 TAM
- ✅ 深: TAM 类必查 ≥3 独立来源 (IDC/Gartner/marketsandmarkets/Yole/工信部 任 3), 差异 >30% 标分歧不调和
- 实操: TAM/市场份额/CAGR/渗透率四类必 ≥3 源, 财务比率(ROIC/ROE/FCF)单源 AKShare 也算 verified 但需标 as_of 日期

### 铁律 3: 失败降级链 (不编造)
- ❌ 浅: 取不到数据 → 主 agent 凭训练记忆补 (通富 $157B 事故根因)
- ✅ 深: 权威源失败 → 次级公开页 → estimated(标"基于行业常识"+置信度) → missing(诚实标) → **永不编造**
- 实操: 输出 evidence.status 字段必填 verified|estimated|missing, status=verified 必有 source URL 命中铁律 1

### 铁律 4: 年份/单位/口径校验
- ❌ 浅: "TAM $157B" — 年份不明/单位混乱(美元/人民币)/口径不清(整体行业 vs 子赛道)
- ✅ 深: "TAM 2030E $80B (Yole 2024Q3 先进封装报告, 含 CoWoS+SoIC, 不含传统封装)" — 年份明确 + 单位明确 + 口径明确
- 实操: 数字字段必含 as_of(数据快照日期) + unit(美元$B/人民币¥亿/%) + scope(覆盖范围), 这三项任缺即 NEEDS_CHANGES

### 铁律 5: 不编造 (RULE-DATA-VERIFIED 永久红线)
- ❌ 浅: data-desk 也是 LLM, 不直接联网时凭训练记忆补
- ✅ 深: web_search/web_fetch/AKShare 三件工具任一失败 → 标 missing, 不补编
- 实操: 训练数据有截止日期(<2024 末), 任何 2025+ 数据若无 web 源 = 必 missing, 不允许"基于训练记忆推断"

## §2 AKShare 函数白名单 (财务比率/行情/个股信息一手源)

### 财务比率类 (stock:* 单元必用)
| 字段 | AKShare 函数 | 返回口径 | 注意 |
|---|---|---|---|
| 营收/净利/毛利率/净利率/ROE/ROA | `stock_financial_abstract(symbol)` | 三表关键科目, 季度/年度 | 必标 as_of 报告期(如 20251231 = 2025 年报) |
| 资产负债 (有息负债/货币资金/应收周转) | `stock_financial_report_sina(stock, symbol)` | 完整三表 | 大科目用 abstract, 细科目用 report |
| 股价/PE/PB/市值/换手率/涨跌幅 | `stock_zh_a_daily(symbol, period='daily')` | 日频 OHLCV+指标 | 用 adjust='qfq' 后复权 |
| 个股基本信息 (上市日/总股本/行业) | `stock_individual_info_em(symbol)` | 静态信息 | 行业归类用 SW 申万 |
| PE/PB 历史分位 | `stock_a_lg_indicator(symbol)` | 5/10/20 年分位 | 用于 critic 6.13 ① 高成长股 PE 分位检查 |
| 资金流向 | `stock_individual_fund_flow(stock)` | 主力/散户净流入 | 辅助 sentiment 分析 |
| 北向持仓 (受限) | 2024-08 起停止日频 | 不再纳入档 A 必取 | 用 stock_zh_a_daily.margin_balance 替代 |

### 行情指数类 (asset:* 大类层用)
| 字段 | AKShare 函数 | 注意 |
|---|---|---|
| 上证/深证/创业板指数 | `stock_zh_index_daily(symbol)` | sh000001/sz399001/sz399006 |
| 美股标普/纳指 | `stock_us_daily(symbol)` | symbol 用美股代码如 'aapl' |
| VIX 恐慌指数 | `index_vix_us` | 风险情绪锚 |
| 大宗商品 (原油/黄金/铜) | `futures_main_sina` 或权威源 web_fetch | 期货主力合约 |

### 宏观指标类 (档 A 全局)
| 字段 | AKShare 函数 | 注意 |
|---|---|---|
| LPR/逆回购 | `macro_china_lpr` / `repo_rate_hist` | 央行官方 |
| CPI/PPI/PMI | `macro_china_cpi` / `ppi` / `pmi_yearly` | 国家统计局 |
| M2/社融 | `macro_china_money_supply` / `tsf_*` | 央行 |
| 美国宏观 (美10Y/Fed funds) | `macro_bank_usa_*` 或 FRED web_fetch | 跨市场 |

### AKShare 失败时的降级
- akshare.func() 调用失败 → 用 web_search "{实体名} {字段}" → web_fetch 官方源 → estimated → missing
- akshare 函数名变更/字段不存在 → 必告诉用户(不静默降级), 不允许 try/except 跳过

## §3 web_search 源优先级

### Tier 1 — 权威源 (verified, 命中 URL_RE)
- 官方源: 央行/国家统计局/工信部/SEC/FRED/上交所深交所/财政部
- 行业研究权威: IDC / Gartner / marketsandmarkets / Yole Développement / Counterpoint / TrendForce
- 公司公告: 巨潮资讯/SEC EDGAR/港交所披露易/公司年报季报 PDF

### Tier 2 — 主流财经页 (verified, 命中 URL_RE)
- 东方财富 (data.eastmoney.com) / 新浪财经 / 英为财情 / Investing.com
- 路透/彭博公开页 (bloomberg.com 公开内容, 非订阅区)

### Tier 3 — 二手/估算 (估算用, 不算 verified)
- 卖方研报二手转引 (中信/海通/华泰等) — 标 estimated, 不算 verified
- 维基百科 — 仅作背景, 不算 verified
- 行业咨询新闻稿 — 看具体是否引用 Tier 1/2 源

### 不算来源 (绝不计入 verified)
- 雪球/股吧/微博/贴吧 个人发言
- "据传"/"业内人士透露"/"一位知情人士"
- "训练记忆推断"/"模型常识"
- 仅含字面 "verified"/"akshare" 而无具体函数/URL 的占位字符串 (verify_audit URL_RE 已防自我 Goodhart)

## §4 失败降级链 (取数失败时的责任路径)

```
数字字段需求
  ↓
① AKShare 优先 (财务/行情/宏观, ≥1 函数调用)
  ↓ 失败/字段不存在
② web_search Tier 1 权威源 (≥1 命中)
  ↓ 失败
③ web_search Tier 2 主流财经页 (≥1 命中)
  ↓ 失败
④ web_search Tier 3 估算 (标 estimated + 区间不给点值 + 稳健性检验)
  ↓ 失败
⑤ 标 missing (诚实)
  ↓ 永不
⑥ 编造 / 训练记忆补 — 触发 RULE-DATA-VERIFIED 永久红线 fatal_flaw
```

**TAM/市场份额/CAGR/渗透率四类硬要求**: ≥3 独立 Tier 1/2 源交叉, 不允许停在 ① 单源。

## §5 RULE-DATA-VERIFIED 红线对接 (verify_audit 命中)

每个 evidence 字段输出必须做到 verify_audit URL_RE 兼容:
```json
{
  "claim": "中兴通讯 2025 营收 +10.4% 归母 -33.3% / 2026Q1 -46.58%",
  "source": "akshare.stock_financial_abstract(symbol='000063', as_of='20251231')",
  "status": "verified"
}
```
- ✅ 命中 URL_RE: `akshare\.[a-z_]+\(`
- ❌ 浅尝: source="verified" (URL_RE 已剔除此 Goodhart 字面量)

```json
{
  "claim": "全球 AI 算力 TAM 2030E $350B",
  "source": "IDC 2024Q3《全球 AI 基础设施市场预测》+ Gartner 2024H2《Magic Quadrant》+ marketsandmarkets 2024年报",
  "status": "verified"
}
```
- ✅ TAM 类必 ≥3 独立源, source 字段列全
- 命中 URL_RE: 含权威机构名 IDC/Gartner/marketsandmarkets

## §6 acquisition_audit 输出契约 (data-desk 输出 JSON 必填字段)

为让 verify_audit 机器审计取数纪律, data-desk 输出 JSON 末尾必填:
```json
"acquisition_audit": {
  "akshare_calls": ["stock_financial_abstract(...)", "stock_zh_a_daily(...)"],  // 实际调用的函数名+参数
  "web_search_queries": [{"query": "中兴通讯 2025 财报", "tier": 1, "hit_url": "..."}],  // 实际搜索+命中
  "downgrade_chain": [],  // 失败降级路径(空=直接命中, 否则记录降级到第几步)
  "missing_fields": [],   // 取不到的字段(诚实标)
  "tam_3source_check": {"field": "future_tam", "sources_count": 3, "sources": [...]},  // TAM 类多源检查
  "_doc": "iteration 4 落地, verify_audit ⑨ 必查"
}
```

## §7 反 Goodhart 输出契约 (协议 Part 7 #10)

- ❌ 形式 cite: acquisition_audit.akshare_calls=["akshare verified"] (字面 "verified" 占位)
- ✅ 真 cite: acquisition_audit.akshare_calls=["stock_financial_abstract(symbol='002001', period='annual', as_of='20251231')"] (函数+参数+日期)

verify_audit ⑨ 必查 (iteration 4 落地): acquisition_audit 字段存在 + akshare_calls 数组每项含函数名()参数 + tam_3source_check 对所有 TAM 字段非空。

<!-- USER_CORRECTION_START — 用户纠错沉淀, 禁日常编辑改写, 只有循环 CONSOLIDATE 经 GATE 能更新 -->
- 2026-06-14 用户血泪: 通富先进封装 $157B 事故 — data-desk 无 SOP 时主 agent 凭训练记忆补 TAM 数字, 实际 Yole verified $80B 虚高 96%, 下游 future_share/forward EPS/target_price 全错。本 skill §1 铁律 5 + §4 失败降级链直接治此根因。
- 2026-06-17 自进化循环 iteration 4 落地: v4-data-desk 是 35 agent 唯一联网取数 agent, 但 206 行 prompt 散乱无 SOP. 本 skill 沉淀 AKShare 函数白名单 + web_search 源优先级 + 失败降级链, 配 acquisition_audit 字段输出契约 + verify_audit ⑨ 机器审计, 形成数据采集层的 5 层防御纵深(认知层 prompt + skill 层 SOP + schema 层 acquisition_audit 字段 + 代码层 verify_audit ⑨ + 监控层 mine scan_data_acquisition).
<!-- USER_CORRECTION_END -->

---

## §8 与协议的关系

本 skill 是 `planning/v4/self-evolving-optimization-loop.md` Part 7 #11 (新数字字段必同步打 verified 红线) + #13 (verify_audit 落盘必跑) 的数据采集层落地。每次 data-desk 取数都应让 verify_audit ⑨ 看到: (a) acquisition_audit 字段非空 (b) AKShare 函数+参数完整 (c) TAM 类 ≥3 源交叉 (d) 失败降级链可追溯 (e) 永不编造。**目标**: 让数据采集从"agent 自觉"变成"工程师 SOP", 治通富 $157B 同型隐患。
