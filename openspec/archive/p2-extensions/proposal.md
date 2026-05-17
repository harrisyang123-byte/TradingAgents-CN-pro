# 变更提案：P2 扩展能力 (#8-12)

**变更 ID**: p2-extensions
**优先级**: P2
**状态**: 待实现

## 范围

| # | 能力 | 工作量 | 策略 |
|---|------|--------|------|
| 8 | Alpha Vantage | 510 行 | 移植为可选数据源（US 股票技术指标） |
| 9 | Azure OpenAI | 52 行 | 移植 azure_client.py + 注册到 factory |
| 10 | 模型目录更新 | ~150 行差异 | 更新 model_catalog.py 到最新模型 |
| 11 | 测试基础设施 | conftest 46 行 | 仅移植 conftest fixtures，不清理 282 个脚本 |
| 12 | CLI token 统计 | 76 行 | 移植 StatsCallbackHandler |
