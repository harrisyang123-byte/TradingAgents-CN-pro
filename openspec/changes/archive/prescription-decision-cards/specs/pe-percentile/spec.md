# Spec: PE Percentile Computation

## ADDED Requirements

### Requirement: A-Share Daily PE Percentile
The system SHALL compute PE(TTM) percentile for A-share stocks using BaoStock daily historical data with approximately 1200 data points over 5 years, providing precise percentile ranking of current PE against its 5-year history.

#### Scenario: 正常计算 A 股 PE 分位
- **GIVEN** 用户持有/候选 A 股标的 600519.SH
- **WHEN** `compute_pe_context("600519.SH", "cn")` 被调用
- **THEN** 返回 `pe_percentile_5y` 为 0-100 的浮点数，`pe_percentile_source: "daily"`，`pe_data_points >= 1000`，`pe_range_5y` 为 "min - max" 格式

#### Scenario: 数据源不可用降级
- **GIVEN** BaoStock 接口超时或返回空数据
- **WHEN** `compute_pe_context` 被调用
- **THEN** 返回 `pe_percentile_5y: null, pe_percentile_source: "data_unavailable"`，仍返回 `current_price` 和 `ma20`，`judgment` 基于 MA20 做定性判断

### Requirement: HK Stock Annual PE Range
The system SHALL compute PE range for HK stocks using AKShare annual EPS_TTM (9 data points typical) combined with daily price history, providing a coarser but still useful historical PE comparison.

#### Scenario: 正常计算港股 PE 分位
- **GIVEN** 用户持有/候选港股标的 00700.HK
- **WHEN** `compute_pe_context("00700.HK", "hk")` 被调用
- **THEN** 返回 `pe_percentile_5y` 基于年度数据点计算，`pe_percentile_source: "annual"`，`pe_data_points <= 10`

### Requirement: US Stock Annual PE Range
The system SHALL compute PE range for US stocks using yfinance annual Basic EPS (5 data points typical) combined with 5-year daily price history, providing a rough historical PE comparison.

#### Scenario: 正常计算美股 PE 分位
- **GIVEN** 用户持有/候选美股标的 AAPL
- **WHEN** `compute_pe_context("AAPL", "us")` 被调用
- **THEN** 返回 `pe_percentile_5y` 基于年度数据点计算，`pe_percentile_source: "annual"`，`pe_data_points <= 5`

### Requirement: Edge Case — 上市不足一年
The system MUST return null PE percentile with reason "insufficient_history" when a stock has been listed for less than one year, preventing misleading percentile calculations from inadequate data.

#### Scenario: 新股跳过 PE 分位
- **GIVEN** 标的上市场 < 1 年，历史数据不足
- **WHEN** `compute_pe_context` 被调用
- **THEN** 返回 `pe_percentile_5y: null, pe_percentile_source: "insufficient_history"`，`judgment` 标注"上市不足一年，无历史 PE 参考"

### Requirement: Edge Case — 亏损企业
The system MUST return null PE percentile with reason "negative_earnings" when a stock has negative trailing earnings, and SHALL fall back to PB percentile or qualitative judgment instead.

#### Scenario: PE 为负时降级
- **GIVEN** 标的当前 PE(TTM) 为负数（亏损）
- **WHEN** `compute_pe_context` 被调用
- **THEN** 返回 `pe_ttm: null, pe_percentile_5y: null, pe_percentile_source: "negative_earnings"`，`judgment` 标注"当前亏损"

### Requirement: Edge Case — 混合市场组合
The system MUST compute PE percentile independently for each stock in a multi-market portfolio without cross-market comparison, and SHALL label the data source granularity clearly for each market.

#### Scenario: 多市场标的分开计算
- **GIVEN** 组合同时持有 A 股(600519.SH)、港股(00700.HK)、美股(AAPL)
- **WHEN** `enrich_price_data_node` 遍历所有标的
- **THEN** 每只标的独立计算 PE 分位，不跨市场比较，不同 `pe_percentile_source` 在 CIO prompt 中明确标注
