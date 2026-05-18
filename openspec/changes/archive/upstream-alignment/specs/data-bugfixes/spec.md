## ADDED Requirements

### Requirement: A股代码正确路由
纯数字 A股代码（如 `000063`）SHALL 被路由到 A股数据链（AKShare），不走美股数据链。

#### Scenario: 6位纯数字代码识别为A股
- **WHEN** 用户输入 `000063` 或 `600519`
- **THEN** `identify_stock_market()` 返回 A股标识，数据请求走 AKShare

#### Scenario: 带后缀的A股代码
- **WHEN** 用户输入 `000063.SZ` 或 `600519.SH`
- **THEN** 同样路由到 A股数据链

### Requirement: 新闻数据 NoneType 防护
新闻获取函数 SHALL 在 `news_df` 为 None 时安全处理，不抛出 AttributeError。

#### Scenario: AKShare 返回 None
- **WHEN** `stock_news_em()` 返回 None（网络错误）
- **THEN** 函数返回空结果或 fallback，不崩溃

### Requirement: A股分析不调用外国数据源
A股分析 SHALL NOT 调用 FinnHub、Google News、OpenAI 全球新闻等非中国数据源。

#### Scenario: A股新闻只用中国源
- **WHEN** 分析 A股（如 `000063.SZ`）的新闻
- **THEN** 仅调用东方财富、AKShare 等中国数据源，跳过 FinnHub/Google News/OpenAI

### Requirement: AKShare 连接重试
AKShare 数据请求 SHALL 包含合理的重试机制（指数退避），处理 `RemoteDisconnected` 错误。

#### Scenario: 首次连接断开
- **WHEN** AKShare 请求遇到 `RemoteDisconnected`
- **THEN** 最多重试 3 次，指数退避（2s/4s/8s），全部失败后返回空结果而非抛异常
