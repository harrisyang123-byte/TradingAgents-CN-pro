# 一键组合顾问 — 验收规格

## Scenario: 无参数直接运行

**Given** MongoDB 中有用户 A（3 个持仓）和用户 B（1 个持仓）
**When** 运行 `python3 cli/claude_advisor.py`
**Then** 自动选择用户 A，日志输出 `用户: <A的id>`

## Scenario: 通过 --user-id 指定

**Given** 任意状态
**When** 运行 `python3 cli/claude_advisor.py --user-id xxx`
**Then** 使用 xxx，不触发自动探测

## Scenario: 通过 .env 指定

**Given** .env 中配置 `ADVISOR_USER_ID=yyy`
**When** 运行 `python3 cli/claude_advisor.py`
**Then** 使用 yyy，不触发自动探测

## Scenario: 无用户可探测

**Given** MongoDB 中无任何持仓记录，且未配置 --user-id 或 .env
**When** 运行 `python3 cli/claude_advisor.py`
**Then** 退出并输出错误提示

## Edge Case: 多用户持仓数相同

**Given** 用户 A 和 B 各有 3 个持仓
**When** 自动探测
**Then** 返回聚合结果中的第一条（确定性取决于 MongoDB 内部顺序）
