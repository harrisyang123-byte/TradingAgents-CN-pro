# v4-data-desk Specification

## Purpose
通用能力层的共享数据采集台 —— v4 中唯一被授权联网的 Agent，为各分析单元集中取数，实现「取数/辩论分离」：辩论部门只读输入包、不联网。两档取数消除重复并保证约束链一致性，凭据契约杜绝编造与静默降级。

## ADDED Requirements

### Requirement: 唯一联网取数 Agent（取数/辩论分离）
系统 SHALL 以 `agents/advisor/v4-data-desk.md` 作为 v4 中**唯一**配置 `web_search`/`web_fetch` 工具的 Agent；所有辩论/分析 Agent（`v4-asset-*`/`v4-industry-*`/`v4-stock-*`）维持 `tools: [Read]`，只消费 data-desk 产出的输入包、不自行联网。data-desk SHALL 只取数不做投资研判（不输出 stance/目标价/配比）。

#### Scenario: 辩论 Agent 不直接联网
- **GIVEN** 触发某单元分析，辩论部门需要宏观/行情数据
- **WHEN** 编排器运行
- **THEN** 数据由 `v4-data-desk` 联网取回并落盘，辩论 Agent 仅 `Read` 输入包，自身不发起任何网络请求

#### Scenario: data-desk 不越权研判
- **GIVEN** data-desk 完成取数
- **WHEN** 它输出结果
- **THEN** 输出仅含指标数值/来源/凭据，不含 stance/target_price/配比等研判结论

### Requirement: 两档取数（全局共读 + 单元深取）
系统 SHALL 把取数分两档：**档 A 全局公共指标**（LPR/逆回购/CPI/PMI/北向/汇率/原油/金价/10Y 国债等约十项）run 级取一次、全单元同源共读；**档 B 单元级深取**（行业景气/估值、收益率曲线/信用利差、个股财报/资金流等）在触发该单元时按需进行、单元内可多次。

#### Scenario: 档 A 全单元同源共读
- **GIVEN** 先后触发 `asset:equity` 与 `asset:fixed_income`
- **WHEN** 两次运行
- **THEN** 两个单元引用同一份 `inputs/data_macro.json` 的 LPR/CPI 等读数（同源同值），不各自重复解读

#### Scenario: 档 B 逐单元深取
- **GIVEN** 触发 `industry:AI算力`
- **WHEN** data-desk 以 tier=unit 运行
- **THEN** 取该行业的景气/估值/政策等深度数据写入 `inputs/industry_*.json` 的 `desk_*` 字段，不波及其它单元

### Requirement: 档 A 新鲜度短路复用
系统 SHALL 在 data-desk 档 A 启动时检查 `data_macro.json` 的 `fetched_at`+`ttl_hours`；若仍在有效期内则直接复用、不重复联网（实现跨 CLI 进程的「run 级取一次」同源共读）。

#### Scenario: 同交易日二次运行命中短路
- **GIVEN** `data_macro.json` 于当日已由 data-desk 取得且未超 `ttl_hours`
- **WHEN** 再次触发任一单元、ensureDataDesk 执行档 A
- **THEN** data-desk 返回 `action:"reused"`，不发起联网，下游复用同一份宏观

### Requirement: 凭据契约（verified/missing，禁编造）
系统 SHALL 要求每个取回的指标标注 `status`：`verified`（联网核实，必附 `source_url`+`as_of`）或 `missing`（取不到，`value:null`+note）；SHALL NOT 编造数值或套用提示中的示例数字。来源优先官方（PBoC/统计局/交易所/财政部），其次主流财经公开页。

#### Scenario: 取不到则标 missing 不编造
- **GIVEN** data-desk 无法从任何来源核实当日北向净流入
- **WHEN** 它输出 `indicators.northbound_net`
- **THEN** 该项 `value:null`、`status:"missing"`，绝不填入编造或示例数字

#### Scenario: 取到则附来源凭据
- **GIVEN** data-desk 从央行页核实 1 年期 LPR
- **WHEN** 它输出该指标
- **THEN** 含 `value`+`as_of`+`status:"verified"`+`source_url`，并追加到 `evidence[]`

### Requirement: 无网降级不阻断
系统 SHALL 在运行环境无 web 工具或联网全部失败时，输出 `data_availability:"unavailable"` + 全指标 missing，并由编排器在 run_report 标注「宏观未联网核实」；SHALL NOT 因取数失败而阻断后续辩论部门运行（降级而非崩溃）。

#### Scenario: 无 web 工具环境回落
- **GIVEN** 运行环境不具备 `web_search`/`web_fetch`
- **WHEN** ensureDataDesk 档 A 执行
- **THEN** data_macro 标 `unavailable`、run_report 提示「未联网核实」，辩论部门仍以降级数据继续运行并产出信封
