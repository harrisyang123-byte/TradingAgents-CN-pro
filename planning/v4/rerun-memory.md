# v4 逐单元重跑 — 记忆文档

> 用途：对话式逐单元重跑 v4 分析的**断点续跑记忆**。每完成一步即追加到「进度日志」，防止 context 丢失后无法接续。
> 维护规则：每步完成 → 更新对应单元状态 + 追加进度日志一条 + 记下产出版本号。

## 0. 全局背景（不变量）

- **目标**：按用户「跑一个 → 讲一个 → 用户本地验一个 → 提交一个」的节奏，逐单元重跑 v4 单元，让每个单元带上 B（结果闭环反思 reflection）+ C（反骑墙/源冲突）的新效果。
- **运行模式**：模式 A —— 本会话 AI agent（我）直接驱动 v4 子 Agent，无 claude CLI。
  - **角色分工（2026-06-07 用户拍板，本节为权威约定）**：
    - **主 agent（我）只承担两件事**：① 需要**联网**的内容（宏观取数 / data-desk 角色）由我亲自用 `web_search`/`web_fetch` 获取核实，保证同源一致、不编造；② 编排与**最终拍板**（director：消费各方输出，产出 verdict + reflection + 反骑墙站队）。
    - **3 分析师（macro/flow/policy）+ 多空辩论（bull/bear 3轮）交给 subagent**：用 `ask-agent-v2` 之类通用 subagent，把对应 `agents/advisor/v4-*.md` 的角色 prompt + 我取回的宏观数据塞进它的 prompt 让它「扮演」该角色输出。
    - subagent 硬约束（遵循平台规约）：单次并发 ≤ 3、prompt 内写明「3 分钟内完成、只输出 ≤500 字摘要」、不嵌套、任一返回立即消费、失败则我主 agent 接管该角色自己跑。subagent **无 web 工具**，故凡需联网的一律我来取后喂给它。
  - 流程：`collect_v4.py` 建输入包（已跑）→ 我（主agent）读 `data/v4/inputs/asset_<class>.json` + 联网补宏观 → **spawn subagent 扮演 macro/flow/policy 三分析师 + 多空3轮**（我喂数据，它们出观点）→ 我（director）综合各 subagent 输出，产出 verdict（含 reflection + 反骑墙）→ `python3 scripts/v4_unit_cli.py write '<unit>' --payload <f> --run-mode ai_proxy` 落盘（自动归档旧版 + version+1）→ `build_snapshot_v4.py` 重生成静态快照。
- **用户ID（默认）**：`6a094caea814b57d3357fa0b`
- **持仓文件**：`data/v4/_inputs/holdings.json`（37 持仓，≈¥1.19M）
- **B/C 代码已实现并提交**：commit `db8547c`（前端 AssetDetailTab 辩论展示 + reflection 蓝条；director prompt 加 reflection/反骑墙；data-desk + 3分析师加源冲突规则）。
- **归档机制**：`write_unit` 覆盖前自动留底到 `data/v4/_archive/<unit>/v<N>_<日期>.json`；baseline（40 单元 v1）已建。`scripts/archive_v4.py` 有 baseline/list/snapshot/diff 子命令。

## 1. 重要注意事项 / 已知坑

- ⚠️ **`data/v4/inputs/` 是 gitignore 的 run 内中间产物**。`collect_v4.py` 每次跑会把 `data_macro.json` 重置成 `needs_fetch` 骨架——我之前写的结构化 22 指标宏观快照已被覆盖丢失。**每次重跑某单元前要先确认/补齐 `data_macro.json`**。
- ⚠️ **reflection 时序依赖**：director 跑在 `write_unit` 之前，此刻落盘的 `data/v4/assets/<class>.json` 还是上一版 → 我读它拿 prev verdict 做对比。写入后旧版进 `_archive`。
- ⚠️ **档 A 宏观数据冲突点**：v2 equity 用 **cn10y 2.7%**；后续核实纠正为 **1.71%**（2026-06-04 多源）。这是 reflection「why_changed」的核心素材。CPI 也有 +0.2%(1月) vs +1.2% 的口径差异，需重新核实。
- 当前真实日期 **2026-06-07**，超出训练数据 → 宏观必须联网取，禁止编造。

## 2. 单元状态表

| 单元 | baseline 版本 | 重跑后版本 | 状态 | 结论(stance/trend) |
|------|--------------|-----------|------|-------------------|
| asset:equity | v2 (neutral/hold, cn10y 2.7%) | **v3 (bullish/hold, cn10y 1.71%)** | ✅ 已重跑 | bullish / hold（看多方向、仓位克制）|
| asset:fixed_income | v1 | — | ⬜ 待跑 | — |
| asset:cash | v1 | — | ⬜ 待跑 | — |
| asset:commodity | v1 | — | ⬜ 待跑 | — |
| asset:precious_metal | v1 | — | ⬜ 待跑 | — |
| asset:real_estate | v1 | — | ⬜ 待跑 | — |
| asset:alternative | v1 | — | ⬜ 待跑 | — |
| alloc:portfolio | v1 | — | ⬜ 待跑 | — |
| 权益深链(行业/个股/配比) | v1 | — | ⬜ 待跑 | 用户点几个跑几个 |

## 3. 进度日志（每步追加）

- **2026-06-07 初始化**：建记忆文档。确认重跑机制（模式A）、当前 equity 为 v2(neutral/hold)、data_macro.json 已被重置为骨架需补。下一步：扮演 data-desk 联网补宏观 → 跑 asset:equity 重辩论（带 reflection + 反骑墙）。
- **2026-06-07 角色分工拍板**：用户确认模式 A 下分工——主 agent（我）只做「联网取数（data-desk）+ director 最终拍板」；macro/flow/policy 三分析师 + 多空3轮辩论用 subagent（通用角色塞角色 prompt）跑。subagent 无 web 工具→联网内容一律我取后喂给它；并发≤3、≤500字摘要、失败则我接管。已写入「运行模式」节为权威约定。
- **2026-06-07 asset:equity 重跑完成 → v3**：
  - **取数(我)**：data_macro.json 重写 22 指标，15 verified/7 missing。关键纠正 **cn10y 2.7%→1.71%**（多源核实，旧 v2 误用过时缓存）。
  - **三分析师(subagent ask-agent-v2 并行)**：macro=favorable（复苏/利率顺风）、policy=favorable（国内宽松>地缘逆风）、flow=unfavorable（两融流入但 AI/QDII 约13.6%拥挤）。**2:1 偏多**。
  - **多空3轮(subagent 串行交锋)**：bull 终态 hold（让步3点风险）、bear=reduce。bear 第1轮逐条挑战犀利（低利率=弱复苏、两融=拥挤顶、PMI下行、外围系统性收紧）。⚠️ subagent 工具只回传终端 stage 输出，bull 开场需 director 据已核实数据合成。
  - **director(我) verdict**：**stance neutral→bullish（反骑墙改判）**，trend 仍 hold 但定性改为「看多方向、仓位克制」（权益已 44.24%偏高+短期外围 risk-off），强制结构调整（压 QDII 至10%内、降拥挤AI、增红利/宽基/内需），5-6月社融为验证点，confidence medium。
  - **reflection**：prev=neutral@09:11；what/why_changed=利率锚纠正(2.7%→1.71%)使折现率支撑更强+2:1偏多→改判看多；self_check=上版 neutral 纠正利率锚后显过保守近骑墙，本应站队。
  - **落盘**：v3 写入，v2 自动归档 `_archive/assets/equity/v2_2026-06-07.json`(19KB)。快照重生成 17 文件，asset_equity.json 带 stance=bullish + reflection + 3 辩论轮。**未提交**，等用户本地验证。
  - **下一步**：用户本地 `git pull` + `VITE_STATIC_SNAPSHOT=1` 验前端（权益卡→大类详情看 reflection 蓝条 + 3 轮辩论 + bullish）→ 认可后提交 → 再跑下一单元（fixed_income 等）。
