# Tasks: portfolio-fund-name-fix

## Task 1: 持仓录入自动补 name + 修复 fund/etf 分类

**目标**：录入/更新持仓时自动查询并写入 name，fund/etf 类型正确分类（不走 AKShare 股票接口）。

- [ ] `AddPositionRequest` 加 `name: Optional[str] = None`
- [ ] `add_position` 新建分支：name 为空时按类型自动查询（fund→FundService，stock→AKShare）
- [ ] `paper_positions.insert_one` 加入 name 字段
- [ ] `update_position`：name 为空时补填
- [ ] `classify_by_akshare`：fund/etf 直接走 fallback（跳过 _is_a_share）
- [ ] `classify_by_akshare`：name 为空时先调 FundService.get_basic_info 获取 name
- [ ] 验证端到端

---

## Task 2: 升级历史持仓批量迁移脚本

**目标**：批量为历史持仓补填 name + industry，解决已有 37 只空持仓问题。

- [ ] 升级脚本：先查 name（fund→FundService，stock→portfolio_service）
- [ ] 再调 classify_by_akshare 分类
- [ ] 验证：37 只持仓全部有 name 和 industry

---

## Task 3: overview API 简化

**目标**：降级路径直接用 paper_positions.industry，不再用运行时 LLM 分类，行业数 ≤ 18。

- [ ] overview 降级路径：直接用 paper_positions.industry 聚合，不再调 classify_holdings_industries
- [ ] overview 返回值新增 total_assets
- [ ] 验证：行业矩阵行数 ≤ 18，无个股名出现
