# 一键组合顾问

**变更**: one-click-advisor
**复杂度**: 简单
**日期**: 2026-06-05

## 问题

每次跑组合顾问需要记 user_id 字符串、输完整命令，启动门槛高。

## 方案

三层降级：

1. `--user-id` 命令行参数（显式）
2. `.env` 中的 `ADVISOR_USER_ID`（配置一次）
3. MongoDB 自动探测：聚合 `paper_positions` 按持仓数排序，取最多的用户

`python` → `python3`（macOS Homebrew 默认无 python 命令）。

## 判断

多用户时自动探测的合理性：取持仓最多的用户 = 最活跃的用户，大概率是用户想要的。用户只有一个账户时更是无歧义。
