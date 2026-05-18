## 1. 基础配置

- [x] 1.1 `default_config.py` — 追加 checkpoint_enabled、output_language、sentiment_sources、wechat_mp_base_url 字段及默认值
- [x] 1.2 `graph/setup.py` — 读取新增配置字段，准备传入 graph 构建函数

## 2. 结构化输出基础设施

- [x] 2.1 `agents/schemas.py` — 定义 ResearchPlan、TraderProposal、PortfolioDecision、SingleDecision Pydantic 模型
- [x] 2.2 `agents/utils/structured.py` — 实现 bind_structured() 和 invoke_structured_or_freetext() 辅助函数
- [x] 2.3 `agents/utils/rating.py` — 实现 parse_rating() 5 档评级确定性解析器

## 3. Checkpoint 断点恢复

- [x] 3.1 `graph/checkpointer.py` — 实现 SqliteSaver 封装，支持按 ticker 的 thread_id 管理
- [x] 3.2 `graph/setup.py` — 按 checkpoint_enabled 条件注入 checkpointer 到 graph.compile()

## 4. 情绪预抓取框架

- [x] 4.1 `analysts/sources/__init__.py` — 实现 BaseSentimentSource 抽象基类、注册表、get_enabled_sources() 工厂函数
- [x] 4.2 `analysts/sentiment_analyst.py` — 实现预抓取编排逻辑：遍历启用的 source → 聚合 SentimentReport → 格式化文本报告
- [x] 4.3 `agents/utils/agent_states.py` — 在 AgentState 中追加 sentiment_context: str 字段（如有需要）

## 5. 情绪数据源

- [x] 5.1 `analysts/sources/eastmoney.py` — 实现 EastMoneySource，基于 akshare 获取 A 股新闻热度，港股 ticker 静默跳过
- [x] 5.2 `analysts/sources/wechat_mp.py` — 实现 WeChatMPSource，通过 httpx 请求 we-mp-rss 服务获取公众号文章

## 6. Graph 管线集成

- [x] 6.1 `graph/setup.py` — 在 research_manager 节点前注入 sentiment_prefetch 节点
- [x] 6.2 可选：按 LLM 能力按条件启用结构化输出绑定（has_structured_output 判断 → bind_structured / 自由文本二选一）

## 7. 验证

- [x] 7.1 import 验证 — 所有 9 个新增文件 import 通过
- [x] 7.2 CLI 冒烟 — `python -m cli.main --help` 正常输出 command 列表
- [x] 7.3 Web 前端 — Docker 文件未修改，VITE_API_BASE_URL 修复已在之前验证
- [x] 7.4 checkpoint 验证 — SqliteSaver 编译 graph + invoke 测试通过
