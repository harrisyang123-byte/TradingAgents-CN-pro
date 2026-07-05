# tasks.md — 市场舆情情报推演 Agent 实现任务

## 任务概览

| # | 任务 | 产出物 | 预估 |
|---|------|--------|------|
| 1 | 目录结构 + 数据落盘规范 | 空目录 + README | S |
| 2 | Data Agent 定义 | `data-agent.md` | M |
| 3 | Inference Agent 定义 | `inference-agent.md` | M |
| 4 | HTML 报告模板 | `report-template.html` | M |
| 5 | E2E 验证 | 首份报告产出 | M |

---

## Task 1: 目录结构 + 数据契约

**产出**：
- `scripts/sentiment-intel/` 目录
- `agents/sentiment-intel/` 目录
- `data/v4/sentiment-intel/.gitkeep`
- `data/v4/sentiment-intel/README.md`（schema 说明）

**验收**：目录结构符合 design.md 规格

---

## Task 2: Data Agent 定义

**产出**：`scripts/sentiment-intel/data-agent.md`
- 6 维取数 prompt
- tools: `web_search`, `web_fetch`, `Bash`（调 scrape-custom-x.py）
- 输出 schema：`intel-data.json`
- 降级链 + missing 诚实标注
- 跨维度并行取数策略

**验收**：agent 定义可被 Agent tool 直接调用

---

## Task 3: Inference Agent 定义

**产出**：`agents/sentiment-intel/inference-agent.md`
- 三层推演框架 prompt
- tools: `Read`（读 intel-data.json）、`Write`（写 HTML）
- 输出 schema：`intel-report.json` + `intel-report.html`
- 分叉检测逻辑、传导链推理、情景概率构造

**验收**：agent 定义可被 Agent tool 直接调用

---

## Task 4: HTML 报告模板

**产出**：`reports/sentiment-intel-template.html`
- 暗色主题 CSS
- 情绪温度条 + 关键数值卡片
- 板块热度雷达（纯 CSS Grid，无 JS 依赖）
- 时间线 / 分叉矩阵 / 传导链 / 情景概率 布局组件
- 自包含（无外部 CSS/JS）

**验收**：在浏览器中渲染正确，暗色主题

---

## Task 5: E2E 验证

**动作**：
1. 触发 `/sentiment-intel`
2. Data Agent 取数 → 检查 `intel-data.json` 6 维覆盖
3. Inference Agent 推演 → 检查 `intel-report.json` + `intel-report.html`
4. 浏览器打开 HTML，检查渲染

**验收**：全链路跑通，HTML 可读，JSON 字段完整
