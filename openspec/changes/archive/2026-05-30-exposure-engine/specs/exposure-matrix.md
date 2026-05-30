# Exposure Engine — 验收规格

## Capability: 敞口矩阵计算

### Scenario: 纯股票组合
- Given 组合持有 3 只股票：A(40%), B(35%), C(25%)
- When 调用 `ExposureService.compute()`
- Then 返回矩阵中 A/B/C 的 total_weight = direct_weight
- And sector_concentration 包含各行业汇总
- And 无 stale_funds 警告

### Scenario: 纯基金组合（穿透）
- Given 组合持有 2 只基金：F1(60%) 重仓 A(40%), B(30%)；F2(40%) 重仓 A(35%), C(25%)
- When 计算敞口
- Then A 敞口 = 60% × 40% + 40% × 35% = 24% + 14% = 38%
- And top_overlaps 中 A 被标记为"被 F1, F2 双重持有"
- And 无直接持仓 stock_exposures

### Scenario: 混合组合（股票 + 基金）
- Given 组合持有：个股 A(20%) + 基金 F1(30%) 重仓 A(30%), B(25%)
- When 计算敞口
- Then A total = 20% + 30% × 30% = 29%
- And A source = "direct(20%) + F1(9%)"

### Scenario: 部分基金无持仓数据
- Given F2 为 QDII 基金，get_top_holdings 返回 []
- When 计算敞口
- Then F2 的 weight 计入 "未穿透" 分类
- And summary 标注 "X% 未穿透（QDII/货基等）"

### Scenario: 持仓数据过期
- Given F1 的 top_holdings 缓存日期距今 > 45 天
- When 计算敞口
- Then F1 加入 stale_funds 列表
- And summary 标注 "⚠ 数据过期: F1 (2026-03-15)"
- And 矩阵仍正常计算（不过期阻断）

### Scenario: 空组合
- Given 用户无持仓
- When 计算敞口
- Then 返回空矩阵 + summary = "无持仓数据"

## Capability: 集中度检测

### Scenario: 高度集中
- Given 敞口矩阵 top-3 占比 > 50% 或 HHI > 0.15
- When 生成 summary
- Then 包含 "⚠ 集中度偏高" 警告

### Scenario: 行业集中
- Given 单一行业占比 > 40%
- When 生成 sector_concentration
- Then 包含 "⚠ 行业集中: XX 行业占比 X%"

## Capability: AdvisorGraph 集成

### Scenario: 敞口上下文注入
- Given 敞口矩阵已计算
- When AdvisorGraph 启动
- Then 初始 messages 包含敞口矩阵摘要
- And 摘要包含 top-10 底层标的 + 行业分布 + 集中度警告

### Edge Case: 基金拆解后底层标的 > 100 只
- When 敞口矩阵 > 100 条
- Then context 只包含 top-20（按 weight 排序）
- And 完整矩阵通过 state 字段传递
