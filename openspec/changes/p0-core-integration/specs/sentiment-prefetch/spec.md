## ADDED Requirements

### Requirement: 情绪预抓取框架

系统 SHALL 在主线 agent 启动前，预抓取情绪数据并合成为情绪报告注入 agent state。

#### Scenario: 主线前执行预抓取
- **WHEN** 用户启动分析请求
- **THEN** sentiment_analyst 在 research_manager 前执行
- **AND** 聚合所有启用的情绪源数据
- **AND** 输出 SentimentReport 注入 agent state

#### Scenario: 所有情绪源不可用
- **WHEN** 所有注册的情绪源均返回错误
- **THEN** 返回空报告
- **AND** 主线 agent 继续执行，不受影响
- **AND** 记录警告日志

### Requirement: 注册式情绪源管理

情绪源 SHALL 通过注册表管理，新增源只需实现接口并注册。

#### Scenario: 注册新源
- **WHEN** 实现 BaseSentimentSource 子类并使用 @register 装饰器
- **THEN** 该源自动加入注册表
- **AND** 配置中启用后即可使用

#### Scenario: 按配置启用源
- **WHEN** sentiment_sources 配置为 ["eastmoney"]
- **THEN** 只拉取东方财富数据
- **AND** wechat_mp 不执行

### Requirement: 东方财富情绪源

eastmoney source SHALL 通过 akshare 获取 A 股个股的新闻和情绪数据。

#### Scenario: 拉取 A 股情绪数据
- **WHEN** eastmoney source 收到 ticker 列表
- **THEN** 对每个 A 股 ticker 调用 akshare 获取相关新闻和热度
- **AND** 汇总为 SentimentData

#### Scenario: 港股 ticker 跳过
- **WHEN** ticker 是港股（如 00700.HK）
- **THEN** eastmoney source 静默跳过该 ticker
- **AND** 不报错

#### Scenario: API 超时
- **WHEN** akshare 请求超过 5 秒
- **THEN** 超时退出，记录 warn 日志
- **AND** 不影响其他源

### Requirement: 微信公众号情绪源

wechat_mp source SHALL 通过 we-mp-rss Docker 服务拉取相关公众号文章。

#### Scenario: 拉取公众号文章
- **WHEN** wechat_mp source 收到 ticker 列表
- **THEN** 查询 we-mp-rss API 获取相关文章
- **AND** 提取文章标题、摘要、发布时间
- **AND** 汇总为 SentimentData

#### Scenario: we-mp-rss 服务不可达
- **WHEN** localhost:8001 无法连接
- **THEN** wechat_mp source 返回空数据
- **AND** 记录警告日志
- **AND** 不影响其他源

### Requirement: 情绪报告注入 agent state

预抓取结果 SHALL 以结构化格式注入 agent state，供后续 agent 消费。

#### Scenario: 情绪数据注入 state
- **WHEN** 所有源抓取完成
- **THEN** 汇总数据格式化为文本报告
- **AND** 写入 agent_state 的 sentiment_context 字段
- **AND** research_manager 和 analyst 可读取该字段
