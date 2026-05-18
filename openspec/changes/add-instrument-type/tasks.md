## 1. 添加持仓时支持 instrument_type（前端 → API → DB）

- [x] 1.1 前端 API 类型：`PortfolioPositionItem`、`PortfolioSummaryPosition`、`AddPositionPayload` 新增 `instrument_type: string`
- [x] 1.2 后端 `AddPositionRequest` 新增 `instrument_type: Optional[str]`；`add_position()` 路由存储到 MongoDB；**order-buy 买入建仓路径（L421-431）也写入 instrument_type**
- [x] 1.3 前端添加持仓弹窗：新增分类下拉选择器（stock/etf/fund/bond/other）+ `detectInstrumentType(code, market)` 自动识别函数
- [x] 1.4 前端持仓表格：新增 instrument_type 列，用不同颜色 Tag 展示分类

## 2. 编辑持仓 + GET 响应 + PortfolioService + 旧数据兼容

- [x] 2.1 后端 `UpdatePositionRequest` 新增 `instrument_type: Optional[str]`，`update_position()` 路由更新该字段
- [x] 2.2 前端编辑持仓弹窗：新增分类下拉选择器，预填当前值
- [x] 2.3 `GET /api/portfolio/positions` 响应（L263-274）返回 `instrument_type`
- [x] 2.4 `PortfolioService.get_portfolio_summary()` 返回 `instrument_type`（旧文档缺字段时返回 `"stock"`）；`get_portfolio_context()` 文本格式化中可选加入分类标识
- [x] 2.5 旧数据 UI 兼容：无 instrument_type 的持仓在表格中显示"未分类"标签，引导用户编辑补充
