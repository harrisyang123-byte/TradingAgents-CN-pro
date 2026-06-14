# v4 AKShare 全量重跑 (行业/大类/配比/方案 + 基金改造)

## 背景

AKShare 外网恢复后(2026-06-14 实测可用),个股层已完成 27 只 verified ROIC 价值创造回补。用户拍板:除个股外,**行业/大类/配比/方案全部用 verified 数据重跑**;**基金方式从"穿透底层"改为"行业内标的/宽基底仓"二分**。

东财诊断结论:push2 实时行情端点(stock_individual_info_em/stock_zh_a_spot_em)连接被阻断(非限流);历史日线 `stock_zh_a_hist` + 财务接口(新浪源)均通 → 价格走 stock_zh_a_hist 取 verified 收盘价。

## 目标

让行业/大类/配比/方案层全部基于 AKShare verified 数据,产出"大类→行业→公司/基金"完整可执行建议;基金以用户视角"买公司 or 买基金"呈现。

## 范围

### 前置修复
- stock_source 价格取数从 push2 实时接口 → `stock_zh_a_hist`(verified 收盘价)

### 阶段 A — 基金方式改造
- 基金二分:① 主题/行业基金(重仓集中)→ 算作该行业内一个 instrument,与个股并列配比;② 宽基/多资产基金 → 大类配置层"被动底仓/全球敞口"
- 基金持仓靠 akshare `fund_portfolio_hold_em`/`fund_individual_basic_info_xq` 联网查 verified → 判定主题行业
- 改 v4_classifier / collect_v4 / 前端展示(行业内推荐含公司+基金)

### 阶段 B — 行业层重跑 ×8
- 用 verified 数据(行业内个股 ROIC 均值/景气/TAM/瓶颈)重跑,产出行业 go/nogo + 行业内推荐(公司+基金)+ 价值创造分层

### 阶段 C — 大类层重跑 ×8(7 大类 + unclassified)
- akshare verified 宏观+大类数据校验 + reflection 对比旧版

### 阶段 D — 配比重跑
- alloc:portfolio + alloc:equity_industries + alloc:industry ×8,整合 B/C + 基金新方式

### 阶段 E — plan:* ×6
- 固收/现金/贵金属/大宗/地产/另类,verified 数据 + forward_view + 四维质量闸门

### 阶段 F — 收尾优化(辩证终审 3 conditions)
- WACC 行业化(半导体 11-13%/制造 9%/消费 7-8%)
- 个股 stance 全面重审(verified ROIC)
- 辩证横向终审

## 数据源(AKShare verified)
- 价格: stock_zh_a_hist(收盘价) / 财务: stock_financial_abstract(ROIC/FCF/ROE) / 港股: stock_financial_hk_analysis_indicator_em / 基金持仓: fund_portfolio_hold_em / 宏观: macro_source(22指标)

## 铁律
- 严格全流程(critic 真复核不自评) / verified 优先不拍脑袋 / 价值创造维度(ROIC vs WACC)贯穿 / 基金归类靠 verified 持仓

## 现状(上一 change 已完成)
- 个股 27 只 verified ROIC(archive/v4-value-creation-augment)
- 价值创造基础设施(契约24MUST/director四问/critic6.9/前端)已就绪
