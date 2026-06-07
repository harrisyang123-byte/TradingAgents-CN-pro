# v4 大类辩论展示 + 结果闭环反思 + 反骑墙措辞 — 技术方案（OpenSpec change 摘要）

> 本文件是 OpenSpec change 内的精炼设计摘要。**完整权威设计**见 `.kiro/specs/v4/design.md §5.9`。
> 设计铁律延续 v3/v4：LLM 决策走 `.md` 子 Agent + Workflow 编排，Python 不直接 `llm.invoke()`；存储/锁/指纹走 `v4_unit_cli.py`。技术栈未新增框架。
> 借鉴来源：[TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) 的 Analyst/Researcher 分层、`get_past_context` 反思注入、数据接地与果断评级措辞。

## A — 大类详情展示多轮辩论（展示管线，零 LLM 重跑）

**根因**：数据已在信封（`payload.debate_rounds` 3 轮 + `payload.analysts`），但 `build_asset_detail` 没吐、前端没渲染。行业层早有现成实现可照搬。

```
asset:<class>.json (payload.debate_rounds / analysts)  ← 数据已存在
   └─ build_asset_detail 补吐 → AssetDetail.debate_rounds/analysts
        └─ AssetDetailTab.vue 折叠块（照搬 IndustryDetailTab 的 idt-debate）
   ↑ 同一函数被 portfolio_v4 路由 + build_snapshot_v4 共用 → API/快照同步
```

4 处改动：`v4_query.build_asset_detail`（加字段）/ `portfolioV4.ts`（接口）/ `AssetDetailTab.vue`（折叠块）/ 重生成快照（逻辑不变）。

## B — 结果闭环反思（Layer 1：跨版本自我反思）

**核心洞察（借鉴 TA）**：记忆价值在「结果接地的反思」，非单纯版本 diff。本设计只落 Layer 1（轻量、无需收益 feed）。

**时序巧合**：`write_unit` = 先归档旧版、再写新版，而 director 跑在 write **之前** → director 运行时落盘的 `assets/<class>.json` 仍是上一版，直接 `Read` 即得上次 verdict，**无需新建历史文件**。

director 输出新增字段：

```json
"reflection": {
  "prev_stance": "上次结论（无历史 null）",
  "prev_date": "上次 generated_at",
  "what_changed": "数据/判断哪里变了",
  "why_changed": "为什么改判（引用本轮新数据）",
  "self_check": "上次判断回看对不对（首跑 'first_run'）"
}
```

`verdict` 旁挂 `reflection`（可选，向后兼容）；`portfolioV4.ts` `AssetVerdict` 加 `reflection?`；`AssetDetailTab.vue` 加「较上次/自检」条（无历史不显示）。

**Layer 2/3 不实现，仅登记**：L2 绑基准（权益=沪深300…）+ data-desk 快照基准点位 → 反思引用真实涨跌%（接近 TA alpha）；L3 个股级 alpha 跟踪。

## C — 反骑墙 + 源冲突接地（prompt 措辞）

1. **反骑墙（director）**：替换铁律「数据盲区→neutral/hold」为「仅证据势均力敌才给 neutral/hold；否则必须站队并说明采信/压低哪方；盲区表达为降 confidence + 缩幅度」。
2. **源冲突接地（data-desk + 三专项分析师）**：「多源冲突时标记分歧（列各源值 + 采用值 + 理由），不私自调和出一个数」——固化 cn10y 2.7%→1.71% 经验，是 §5.8 凭据契约的细化。

## 实施顺序

```
A（展示，改完即可前端验证看到辩论）
  → B-Layer1 + C（改 director/data-desk prompt + schema + 前端反思条；需重跑 asset:<class> 才出 reflection）
```

## 兼容与回落

- 叠加在 `v4-layered-deep-research` + `v4-shared-data-desk` 之上，不改单元信封外壳/状态机/约束链/v3。
- 旧信封无 `reflection`/`debate_rounds` → 前端可选渲染缺省不显示；后端默认 `[]`/`{}`，不报错。
- director Read 不到旧版（首跑） → `self_check:"first_run"`，reflection 字段允许 null，不阻断。

## 关键风险与权衡

- 反思无收益接地偏主观 → Layer 1 仅跨版本自省 + 登记 Layer 2；首跑 first_run 不强造。
- 反骑墙矫枉过正逼造假 → 仅势均力敌才允许中性 + 保留「降 confidence」诚实出口。
- 展示与数据耦合 → 坚持只经 `build_asset_detail` 同构契约，不让前端直读原始信封。
