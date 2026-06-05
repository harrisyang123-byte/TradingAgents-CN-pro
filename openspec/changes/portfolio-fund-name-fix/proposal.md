## Why

37只持仓全是基金，`paper_positions` 无 `name` 字段，`classify_by_akshare` 收到空 name 导致全部返回「未分类」，overview 行业矩阵出现 54 行混乱（个股名当行业名、重复行业、未分类37个）。

## What Changes

- **新增** `AddPositionRequest.name` 字段（可选），录入时自动查询并写入 `paper_positions.name`
- **修改** `classify_by_akshare`：fund/etf 类型跳过 AKShare 股票接口，先补 name 再 fallback 分类
- **修改** `update_position`：name 为空时补填
- **修改** `scripts/migrate_position_industry.py`：升级为先补 name 再分类的批量迁移脚本
- **修改** `overview` API：使用 `paper_positions.industry` 而非运行时 LLM 分类，简化降级路径

## Capabilities

### New Capabilities

- `auto-name-lookup`: 持仓录入时自动查询股票/基金名称写入 paper_positions.name

### Modified Capabilities

- `position-industry-classifier`: fund/etf 分类逻辑修复（跳过股票 AKShare 接口）

## Impact

- `app/routers/paper.py` — AddPositionRequest, add_position, update_position, get_portfolio_overview
- `app/services/industry_classifier.py` — classify_by_akshare
- `scripts/migrate_position_industry.py` — 升级批量补填逻辑
