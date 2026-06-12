## Why

v4 投研系统经过多轮能力升级（chokepoint 框架/预期差选股/forward_view 11维前瞻/四维质量闸门），架构层已基本成型。但**距离"用户可信赖、持久盈利的专家团队"目标仍有三大缺口**：

1. **完整性缺口（B阶段）**：核心闭环未跑完——推荐行业的代表个股仅 3/12 完成新架构（中际旭创/中芯国际/蓝思科技），9 个 alloc:industry:* 配比层仍 v1 baseline，10 个旧 v1 stock 没 forward_view，alloc:portfolio v3 verdict 字段空、unclassified/AI算力 stance 等遗留 bug。**"半截投研"无法支撑实际决策**。
2. **学习能力缺口（C阶段）**：reflection 字段已有但**从未真正回测过历史判断的准确率**——系统对自己的过往判断不负责，无法识别"哪些判断对了/哪些错了/为什么"。这是"持久盈利"的关键缺口（用户在拿真钱试错）。
3. **决策完备性缺口（D阶段）**：当前 chokepoint 仅看"供应链卡位"（不可替代/供给集中/产能刚性/价值卡位/替代路径/发现度6维），但**真正的护城河分析需要波特五力**（潜在进入者威胁/替代品威胁/买方议价力/供方议价力/同业内部竞争）补全。需要 A/B 测试验证"加五力 vs 不加"的实际效果再固化。

本 change 按 **B → C → D** 三阶段递进，每阶段完成后可独立验收效果，**先看 B 整体效果，再看 C 改进，再 A/B 测试 D 补全**。

## What Changes

### 阶段 B：完整工程（必做，先看整体效果）

**B1 个股下钻补全**（推荐行业每 2-3 龙头）：
- AI算力：补 新易盛300502 / 天孚通信300394
- 半导体：补 北方华创002371 / 中微公司688012 / 华特气体688268
- 创新药：新跑 百济神州06160 / 恒瑞医药600276 / 科伦博泰06990
- 有色资源：新跑 紫金矿业601899 / 北方稀土600111
- 电力公用事业：新跑 长江电力600900 / 中国核电601985
- 互联网平台：新跑 腾讯00700 / 阿里09988 / 小米01810升级
- 共 13 个新增 + 1 个升级 = 14 个个股

**B2 alloc:industry:* 9 层升级**：消费推荐行业 verdict + 个股完成度，给 stock_weights 配比方案（每行业内分股票占该行业目标权重）。

**B3 关键 bug 修复**：
- alloc:portfolio v3 verdict 顶层字段空 → 补 stance/situation/direction
- AI算力 v6 verdict.stance="go"（应为 bullish/bearish/neutral）→ 修
- asset:unclassified v1 没 forward_view → 升级
- 中际旭创 chokepoint_score 字段格式不一致 → 统一
- collect_v4 重置 data_macro.json 坑 → 加保护(本期记 backlog 不实施)

**B4 旧 v1 stock 升级**（10 个旧股补 forward_view）：000063 中兴/002001 新和成/002050 三花/002415 海康/002517 恺英/09992 泡泡玛特/603236 移远/603663 三祥（小米/中际旭创已升级）。

**B5 前端展示验证 + 优化**：build_snapshot_v4 → 静态快照重生成 → 前端 AssetDetailTab/IndustryDetailTab/StockDetailTab 三层验证（forward_view 折叠面板/chokepoint_map 表格/止损纪律/三情景）。

**B6 文档/rerun-memory 更新**：把 B 阶段所有变更记入 `planning/v4/rerun-memory.md` + 更新 `full-analysis-plan.md` 13 步台账。

### 阶段 C：回测验证机制（学习能力补全，B 后做）

**C1 历史快照回放器**：`scripts/v4_replay.py` —— 给定 `--unit <id>` + `--from-version vN` + `--to-date YYYY-MM-DD`，回放 verdict 在该日期点的判断 vs 实际行情（股价/指数/汇率走势）。
**C2 判断准确率打分**：每条 verdict 增加 `historical_alpha` 字段（vs 基准/绝对收益/胜率/最大回撤），由 C1 在每次新版本写入时自动回填上一版的实际表现。
**C3 季度复盘报告**：`scripts/v4_quarterly_review.py` 输出 markdown 报告（这一季度对了什么/错了什么/系统性偏差/改进建议），落 `planning/v4/quarterly-review-YYYY-Qx.md`。
**C4 critic 评审增强**：将 historical_alpha 纳入 v4-investor-critic 评审输入——"如果上次判断错了，这次为什么会对？" 形成真正的结果闭环。

### 阶段 D：竞争五力补全 + A/B 测试（决策完备性，C 后做）

**D1 新建分析维度**：在 `chokepoint_map` 每环节加波特五力 5 字段：
- `entry_threat`（潜在进入者威胁，影响利润分割）
- `substitute_threat`（替代品威胁，扩展替代路径分析）
- `buyer_power`（买方议价力，已有客户集中度的扩展）
- `supplier_power`（供方议价力，影响成本结构）
- `internal_rivalry`（同业内部竞争烈度）

**D2 prompt 改造**：`v4-industry-chokepoint.md` + `v4-stock-analyst-competitive.md` 加五力分析任务。

**D3 A/B 测试验证**：取 1-2 个标的（半导体设备/创新药龙头），独立 critic 盲评"原 chokepoint vs 加五力后"两版产出，按"决策深度/识别风险/护城河可信度"5 维度打分。

**D4 据测试结果决定**：
- 五力提升≥10 分 → 固化进 schema
- 提升<10 分 → 五力作为可选维度，不强制要求
- 提升<5 分 → 不固化（避免过度复杂化）

## Capabilities

### New Capabilities

- **v4-stock-coverage-completion**：推荐行业 6 + 观察行业 2 共 8 个行业各≥2 龙头股的完整 v4 新架构覆盖（含 chokepoint_score/四维/forward_view/止损纪律）。
- **v4-intra-industry-allocation**：9 个 alloc:industry:* 行业内股票配比方案（每个行业内的 stock_weight 总和≤行业 target_weight）。
- **v4-historical-validation**：历史回测+判断准确率回填+季度复盘的完整闭环，让 reflection 从"定性自省"升级为"量化验证"。
- **v4-five-forces-augmentation**（待 A/B 验证）：波特五力补充 chokepoint，全面看护城河。

### Modified Capabilities

- **v4-investor-critic**（C阶段）：评审输入加 `historical_alpha` → 据过往准确率拷问当前判断。
- **v4-data-grounding**（B阶段）：bug 修复后强化数据一致性。
- **v4-frontend-display**（B阶段）：三层 Tab 全部展示新 schema（forward_view/chokepoint 精细版/五力可选）。

## Impact

### B 阶段（完整工程）
- 角色 prompt：无新建 / 无改造（沿用现有）
- 数据：14 个 stock 新增/升级 + 9 个 alloc:industry 升级 + 修 4 个 bug + 10 个旧 stock 补 forward_view
- 文档：rerun-memory + full-analysis-plan 更新
- **预计工作量**：~12-14h（含联网取数、payload 合成、落盘、提交）
- **验收标准**：用户 git pull + 前端验证三层 Tab 数据完整 + 推荐行业全部有 ≥2 龙头股 verdict

### C 阶段（回测验证）
- 新建脚本：v4_replay.py + v4_quarterly_review.py
- schema：每个 verdict 加 historical_alpha 字段（向后兼容）
- 角色：v4-investor-critic.md 加 historical_alpha 消费
- **预计工作量**：~8-10h
- **验收标准**：能跑回测对中际旭创 v3→v6 准确率打分；季度复盘 markdown 自动生成

### D 阶段（五力补全 + A/B）
- prompt：v4-industry-chokepoint + v4-stock-analyst-competitive 加五力任务
- A/B 测试：1-2 个标的双版本盲评 + 决策报告
- **预计工作量**：~3-5h（A/B 测试为主，固化看结果）
- **验收标准**：A/B 报告产出 + 据数据决定是否固化

### 总体
- **总工作量**：~25-30h（B/C/D 三阶段累计）
- **不影响**：单元信封/状态机/v3 链路/已落盘 stable 数据（新字段向后兼容，alpha 回填仅追加不删改）
- **风险**：subagent 不稳定时主 agent 接管；数据时效性（联网取数 + estimated 标注）

## Order

**严格按 B → C → D 推进**：
1. B 阶段完成后，用户先看整体效果（前端验证），拍板后进入 C
2. C 阶段完成后，用户看回测改进效果，拍板后进入 D
3. D 阶段 A/B 测试结果用数据决定是否固化

**禁止跳跃**：不能 B 没做完就上 C；C 没验证就上 D。
