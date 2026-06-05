# industry-vitality-scorer Specification

## Purpose
TBD - created by archiving change industry-layer-rebuild. Update Purpose after archive.
## Requirements
### Requirement: 5类信号加权打分全行业排序
系统 SHALL 对全量18大行业按5类信号（资金流向/北向资金/PE分位/PMI-PPI/政策文件）加权打分，输出行业景气排行榜。

#### Scenario: 正常打分输出前3名
- **GIVEN** AKShare 接口可用，官网爬虫可访问
- **WHEN** 景气打分引擎运行
- **THEN** 系统输出18大行业的景气分数排序，取前3名作为自动补充候选

#### Scenario: 部分数据源不可用时降级
- **GIVEN** PMI/PPI 接口超时
- **WHEN** 景气打分引擎运行
- **THEN** 系统跳过不可用信号，用剩余可用信号打分，结果标注数据完整度，不中断流程

#### Scenario: 政策文件官网爬虫被拦截（Edge Case）
- **GIVEN** 国务院/发改委官网返回 403 或超时
- **WHEN** 景气打分引擎获取政策信号
- **THEN** 系统降级为 AKShare 新闻接口，记录降级日志，打分继续执行，不抛出异常

### Requirement: 景气分数结构化输出
系统 SHALL 为每个行业输出结构化景气评分，包含总分、各维度分项、数据来源标注。

#### Scenario: 评分结构完整
- **WHEN** 打分完成
- **THEN** 每个行业的评分包含 total_score（0-100）、signal_breakdown（各维度得分）、data_completeness（0-1，可用信号比例）、top3_flag（是否进入前3）

