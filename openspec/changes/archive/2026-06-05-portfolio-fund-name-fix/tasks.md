# Tasks: portfolio-fund-name-fix

## Task 1: 持仓录入自动补 name + 修复 fund/etf 分类

- [x] `AddPositionRequest` 加 `name: Optional[str] = None`
- [x] `add_position` 新建分支：name 为空时按类型自动查询（fund→FundService，stock→AKShare）
- [x] `paper_positions.insert_one` 加入 name 字段
- [x] `update_position`：name 为空时补填
- [x] `classify_by_akshare`：fund/etf 直接走 fallback（跳过 _is_a_share）
- [x] `classify_by_akshare`：name 为空时先调 FundService.get_basic_info 获取 name
- [x] 验证端到端

## Task 2: 升级历史持仓批量迁移脚本

- [x] 升级脚本：先查 name（fund→FundService，stock→AKShare `stock_individual_info_em`）
- [x] 再调 classify_by_akshare 分类
- [x] 验证：37 只持仓全部有 name 和 industry（通过 unit test + dry-run）

## Task 3: overview API 简化

- [x] overview 降级路径：直接用 paper_positions.industry 聚合，不再调 classify_holdings_industries
- [x] overview 返回值新增 total_assets
- [x] 验证：行业矩阵行数 ≤ 18，无个股名出现
