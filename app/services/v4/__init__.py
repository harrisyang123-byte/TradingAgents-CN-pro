"""v4 分层独立深度投研系统 — 单元化常驻分析。

v4 把 v3「一次全量单链路」重构为「分析单元（Analysis Unit）」：
触发、缓存、落盘、状态、约束链的最小原子。v3 完全不动，v4 独立集合/目录/路由。

模块：
- asset_classes  七大类资产常量 + 下钻深度 + 分档 TTL
- v4_unit_store  单元信封读写 / 索引 / 运行锁（文件态，git 传输载体）
- v4_state       纯只读状态机（gray/blue/green/yellow/red）+ upstream 指纹比对
- v4_classifier  持仓七大类穿透归类
- industry_candidates  内置候选行业清单
"""

SCHEMA_VERSION = "v4.0"
