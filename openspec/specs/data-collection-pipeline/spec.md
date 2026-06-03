# data-collection-pipeline Specification

## Purpose
TBD - created by archiving change claude-code-agent-advisor. Update Purpose after archive.
## Requirements
### Requirement: 数据收集产出完整的数据文件集
`collect_data.py` SHALL 产出至少 6 个 JSON 文件到 `data/advisor_runs/{run_id}/`: `data_portfolio.json`(持仓+账户)、`data_tier1.json`(Tier1报告)、`data_pe.json`(PE分位)、`data_exposure.json`(敞口矩阵)、`data_macro.json`(宏观指标+行业排名+资金流向)、`data_market_temp.json`(市场温度)。

#### Scenario: 正常采集全部数据
- **WHEN** 用户执行 `./run.sh collect --user-id abc123`
- **THEN** `collect_data.py` 调用 PortfolioService、compute_pe_context、ExposureService、get_macro_indicators、get_industry_rankings、get_sector_fund_flows,全部成功后写入 6 个 JSON 文件

#### Scenario: 基金穿透数据部分失败
- **WHEN** AKShare SSL 超时导致 `get_fund_holdings` 部分基金查询失败
- **THEN** `collect_data.py` 记录 warning 日志,在 `data_portfolio.json` 中标注 `fund_data_partial: true`,继续产出其余文件

#### Scenario: 用户持仓为空
- **WHEN** PortfolioService 返回 positions = []
- **THEN** `collect_data.py` 退出并输出 "当前用户无持仓数据，无法进行分析",不创建数据目录

### Requirement: PE 分位数据缺失时使用回退策略
当某只标的 PE 分位数据不可用时,系统 SHALL 在 `data_pe.json` 中标注 `null`,不回退到 MA20(由 Agent 在推理时自行决策)。

#### Scenario: 美股标的 PE 不可用
- **WHEN** `compute_pe_context` 对美股标的抛异常(timezone bug)
- **THEN** 该标的在 `data_pe.json` 中 PE 相关字段为 `null`,ci_verbose 标注"数据不可用"

### Requirement: 数据文件格式标准化
所有数据文件 SHALL 包含 `collected_at`(ISO8601时间戳)和 `status`(success/partial/error)顶级字段。

#### Scenario: 数据文件包含元信息
- **WHEN** 数据收集完成
- **THEN** 每个 data_*.json 文件包含 `"collected_at": "2026-06-03T14:00:00+08:00"` 和 `"status": "success"`

#### Scenario: 部分数据失败时标注状态
- **WHEN** 宏观数据采集成功但基金穿透失败
- **THEN** `data_portfolio.json` 的 status 为 `"partial"`,含 `"warnings": ["fund holdings data incomplete"]`

### Requirement: 市场温度数据采集
`collect_data.py` SHALL 采集市场温度指标:北向资金净流入/流出、市场涨跌比、涨停/跌停数、融资融券余额变化、个股千股千评评分,写入 `data_market_temp.json`。

#### Scenario: 市场温度数据正常采集
- **WHEN** AKShare 市场数据接口可用
- **THEN** `data_market_temp.json` 包含 `north_flow`(5日净流向)、`market_breadth`(涨跌比)、`limit_ratio`(涨跌停数)、`margin_change`(融资余额周变化)

#### Scenario: 市场温度数据源部分不可用
- **WHEN** 千股千评接口超时但其他接口正常
- **THEN** `data_market_temp.json` 包含所有字段,不可用的标为空对象,status = "partial"

