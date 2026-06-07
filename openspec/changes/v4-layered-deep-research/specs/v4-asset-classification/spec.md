# v4-asset-classification Specification

## Purpose
定义固定的七大类资产框架，并对用户持仓（含基金穿透）做归类，标注每类「可下钻深度」与「可交易标的 vs 持有型敞口」，作为 v4 三层深研的归类地基。对应 FR-001。

## Requirements

### Requirement: 七大类资产体系定义
系统 SHALL 内置固定的七大类资产框架（`equity` 权益 / `fixed_income` 固定收益 / `cash` 现金及等价物 / `commodity` 大宗商品 / `precious_metal` 贵金属 / `real_estate` 房地产 / `alternative` 另类投资），每类记录其「最深下钻层级」，供前端决定详情页渲染「行业+个股」还是「持有结构方案」。

#### Scenario: 大类配置含下钻深度
- **GIVEN** v4 资产体系已初始化
- **WHEN** 读取大类配置表
- **THEN** 返回 7 个固定大类，权益 `max_drill_depth=3`（大类→行业→个股），非权益为 2（大类→品种/工具或持有结构）

### Requirement: 持仓穿透归类
系统 SHALL 将每一笔持仓（含基金按底层资产穿透）归入七大类之一；无法归类的标记为「待人工归类」（`class=unclassified`）而非静默丢弃。

#### Scenario: 基金按底层资产穿透归类
- **GIVEN** 用户持有一只股票型基金
- **WHEN** 运行穿透归类
- **THEN** 该基金按底层资产归入 `equity`，不被当作独立不可识别条目丢弃

#### Scenario: 无法识别的持仓不丢弃
- **GIVEN** 某持仓代码无法匹配任一大类
- **WHEN** 运行穿透归类
- **THEN** 该持仓归入 `unclassified` 桶并在 overview 标「待人工归类」，归类总额不丢失

### Requirement: 区分可交易标的与持有型敞口
系统 SHALL 区分每类的「可交易标的」（ETF/REITs/债基/金条 ETF，支持下钻到品种/标的）与「持有型敞口」（实物房产、实物贵金属、各国现金，仅作为配置桶记录敞口，不推荐具体标的）。

#### Scenario: 持有型敞口只记金额
- **GIVEN** 用户持有实物房产
- **WHEN** 归类至 `real_estate`
- **THEN** 该笔记入 `holding_only_exposure`，不产生 candidates/可交易标的列表

### Requirement: AI 代跑持仓文件归类
当用户本地持仓为空、仅由 AI 代跑给定持仓文件时，系统 SHALL 按传入的持仓文件做同样的穿透归类。

#### Scenario: 文件输入模式归类
- **GIVEN** 运行 `run_v4.sh ... --portfolio-file holdings.json` 且未连接用户 MongoDB
- **WHEN** 触发归类
- **THEN** 系统读取该 JSON 做七大类穿透归类，结果与本地运行同构
