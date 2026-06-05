## ADDED Requirements

### Requirement: 持仓录入时自动查询名称
系统 SHALL 在新增持仓时，若用户未传入 name 字段，按 instrument_type 自动查询名称并写入 `paper_positions.name`。

#### Scenario: fund 类型自动查名
- **GIVEN** 用户录入基金代码 270042，未传入 name
- **WHEN** add_position 执行
- **THEN** 系统调用 FundService.get_basic_info(270042) 获取基金简称，写入 paper_positions.name

#### Scenario: stock 类型自动查名
- **GIVEN** 用户录入股票 600519，未传入 name
- **WHEN** add_position 执行
- **THEN** 系统调用 AKShare stock_individual_info_em 获取"股票简称"，写入 paper_positions.name

#### Scenario: name 自动查询失败不阻断录入（Edge Case）
- **GIVEN** FundService/AKShare 查询超时或返回空
- **WHEN** add_position 执行
- **THEN** name 留空字符串，持仓正常保存，不抛异常

### Requirement: fund/etf 类型行业分类
系统 SHALL 对 fund/etf/other 类型跳过 AKShare 股票接口，直接用名称关键词匹配分类。

#### Scenario: 基金名命中关键词
- **GIVEN** 基金名称为"广发纳指100ETF联接（QDII）"
- **WHEN** classify_by_akshare 执行
- **THEN** 返回 "全球配置"（命中"纳指"+"QDII"关键词）

#### Scenario: 基金名无关键词时（Edge Case）
- **GIVEN** 基金名称为"华夏大盘精选"
- **WHEN** classify_by_akshare 执行
- **THEN** 返回 "未分类"，不阻塞录入

### Requirement: 历史持仓 name/industry 迁移
系统 SHALL 提供迁移脚本批量补填历史持仓的 name 和 industry 字段。

#### Scenario: 迁移脚本补填空 name
- **GIVEN** paper_positions 中存在 name 为空的持仓
- **WHEN** python scripts/migrate_position_industry.py 运行
- **THEN** 所有持仓的 name 被补填为非空值，industry 分类更新

#### Scenario: 迁移脚本 dry-run 不写库（Edge Case）
- **GIVEN** 执行 --dry-run 参数
- **WHEN** 迁移脚本运行
- **THEN** 预览补填结果，不实际写入 MongoDB

### Requirement: overview API 使用 paper_positions.industry
系统 SHALL 在 overview 降级路径中直接读取 paper_positions.industry 聚合行业，不调用运行时 LLM 分类。

#### Scenario: overview 降级路径行业数正常
- **GIVEN** 持仓已通过分类写入 industry 字段
- **WHEN** 调用 GET /api/portfolio/overview
- **THEN** 返回行业矩阵行数 ≤ 18（18-bucket），无个股名出现

#### Scenario: overview 返回 total_assets
- **GIVEN** 用户有持仓
- **WHEN** 调用 GET /api/portfolio/overview
- **THEN** 返回 total_assets 字段（来源于 portfolio_summary.total_assets）
