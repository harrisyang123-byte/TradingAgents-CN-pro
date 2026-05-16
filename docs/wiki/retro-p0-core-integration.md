# P0 核心集成 — W.W.L.D 复盘

> 复盘范围：单个变更 — P0 核心集成（结构化输出 + Checkpoint + 情绪预抓取）
> 日期：2026-05-16

## Well — 做得好

1. **增量合并策略正确**：选择在 CN fork 上增量追加原版能力，而非重构 Toolkit 架构，避免了大规模回归。review 和测试均未发现架构层面的问题。

2. **注册式情绪源设计**：`@register` 装饰器 + `BaseSentimentSource` ABC 的框架，源间解耦，后续新增源不需要改编排代码。eastmoney 和 wechat_mp 两个实现已验证了模式的可行性。

3. **降级路径完善**：
   - 结构化输出：LLM 不支持时自动回退到自由文本
   - 情绪预抓取：源超时/失败时静默跳过，不阻塞主线
   - checkpoint：默认关闭，不增加无 checkpoint 场景的负担
   - `_run_async()`：同时适配 sync（CLI）和 async（FastAPI）上下文

4. **review 发现了真实问题**：SqliteSaver context manager 误用 + asyncio.run() 跨上下文风险 — 两个都是不测试不会暴露的问题。

## Would — 可以改进

1. **启动太快，没先理解 ACE 结构** — 用户原话"太急了"、"好好理解下ace"。未充分理解 domain 目录结构、ACE 阶段划分就开始 coding。下次应按顺序：先读领域结构 → 确认理解 → 再动手。

2. **过早承诺** — 在规划阶段直接给出方案而不是先探索问题空间。用户指出后才回到 ace-planner 的正确流程。

3. **用户反馈为第三方数据源时缺少确认** — 在确定"以谁为基础"时，应该先让用户试用 CN fork 再决策，而不是替用户做判断。

4. **GBK 编码问题未提前识别** — Windows 中文环境的 GBK 编码导致 emoji 日志崩溃，需要 `PYTHONIOENCODING=utf-8` 绕行。这是 CN fork 在 Windows 开发环境中的已知摩擦点，早期未纳入测试 checklist。

## Learn — 学到了什么

1. **SqliteSaver 实例化陷阱**：`SqliteSaver.from_conn_string()` 返回的是 contextmanager 包装器，不是 saver 实例。`graph.compile(checkpointer=...)` 期望 `BaseCheckpointSaver` 实例。正确做法是 `sqlite3.connect()` → `SqliteSaver(conn)`。

2. **asyncio.run() 两难**：Python 3.10+ 中 `asyncio.run()` 在事件循环已运行时会抛出 `RuntimeError`。混合 sync/async 框架（LangGraph + FastAPI）下，正确的模式是新开线程 + 新事件循环执行协程。

3. **ACE 流程节奏**：planner 阶段需要充分探索 → 用户确认 → 再推进到 applier。跳过探索直接"出方案"适得其反。reviewer 不能只是形式主义 — 这次 review 真的发现了 bug。

4. **用户工程风格**（写入用户记忆）：
   - 严格遵循工作流，不喜欢被跳过
   - 偏好直接复用而非自研
   - 对模糊指令和过早结论会纠正
   - 重视测试验证

## Do — 以后怎么做

1. **任何新变更启动前**：先确认 ACE 各阶段的理解，特别是 domain 目录结构和各 skill 文件的位置
2. **规划阶段**：先探索问题空间，而非直接输出方案。用 ace-planner 的"Matt Pocock Grill 拷问细节"方式确保需求足够明确
3. **新增 Windows 测试 checklist**：
   - `PYTHONIOENCODING=utf-8` 前缀执行 Python 命令
   - 日志路径含中文/emoji 时的 GBK 兼容
4. **review 保持严格**：本次 review 发现了真实缺陷。后续所有变更至少应包含：
   - import 验证
   - sync/async 双上下文测试
   - config 字段边界检查
5. **知识沉淀时点**：不再等到 archiver 才写 wiki — 关键架构决策（如 `_run_async` 模式、@register 框架）应在设计阶段就记录到 docs/wiki/
