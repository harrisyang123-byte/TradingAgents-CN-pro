## Why

Chokepoint 瓶颈框架 + 预期差选股理论经多轮实测验证后，需从"模式A手动塞 payload"固化为**正式的角色 prompt + schema**，否则权益深链（行业层/个股层）每次跑都靠主agent临时拼，不可复现、易出错（中际旭创"420"事故即此）。本 change 把以下已验证设计落地：

1. **Chokepoint 瓶颈框架**（A/B 验证：专职瓶颈分析师 + top瓶颈派专项调研员的混合分队，胜过融合/单兵）——`chokepoint-framework.md`。
2. **预期差选股理论**（A/B 验证：方案B 预期差驱动胜方案A 估值分位，能解释中际旭创88→1000）——`stock-selection-theory.md`。
3. **个股层结构不对称修复**（审查发现：大类层有3分析师打底，个股层却直接 bull/bear 无底座）——`squad-vs-solo-audit.md`。
4. **数据铁律**（中际旭创"420"事故根因：subagent 无联网却编了价格、director 没核实就落盘）——分析 subagent 严禁自产价格/PE/市值数字。
5. **reflection/反骑墙推广**：设计本为全局通用，仅在大类层落地，本期推广到行业层/个股层 director。

## What Changes

**新建角色**：
- `agents/advisor/v4-industry-chokepoint.md`：产业链瓶颈分析师（四维判定 不可替代/供给集中/产能刚性/价值卡位 + 自下而上逆向工程 + 替代路径 substitution_risk + 发现度 discovery_level）。
- `agents/advisor/v4-stock-analyst-financial.md` / `..-competitive.md` / `..-valuation.md`：个股3分析师分队（修复结构不对称，与大类层 macro/flow/policy 范式对齐）。估值分析师承载预期差三锚。

**改造角色**：
- `v4-stock-bull.md`：加瓶颈溢价逻辑 + 消费3分析师底座。
- `v4-stock-bear.md`：加替代路径专项攻击 + 预期差赔率/定价充分度挑战。
- `v4-stock-director.md`：加预期差三锚综合（隐含增速缺口/定价充分度/催化）+ chokepoint_score + reflection + 反骑墙。
- `v4-industry-bear.md`：加替代路径挑战。
- `v4-industry-director.md`：加 chokepoint_map 整合 + reflection + 反骑墙。
- `v4-industry-bull.md`：轻改（景气+瓶颈衔接）。

**数据铁律（全部分析 subagent）**：统一加"严禁自行产出价格/PE/市值/目标价等数字，一律引用 data-desk（输入包）已核实值；无则标 missing，绝不编造"。

**schema**：`.kiro/specs/v4/design.md` 加 `chokepoint_map` / `top_chokepoints` / `expectation_gap` / `discovery_level` 字段定义（行业/个股 payload 可选字段，向后兼容）。

**不改动**：单元信封外壳/五色状态机/约束链/v3 全链路/data-desk 取数逻辑（个股数据 stock_source.py 已单独补齐）。

## Capabilities

### New Capabilities
- `v4-chokepoint-analysis`：产业链瓶颈逆向工程 + 四维判定 + 替代路径 + 发现度，混合分队（瓶颈分析师出骨架 + 主agent对top瓶颈派专项调研员深挖）。
- `v4-expectation-gap-stock`：预期差驱动选股（隐含增速缺口/定价充分度/催化三锚），替代"估值分位/涨幅"错误锚。
- `v4-stock-analyst-squad`：个股3分析师分队（财务/竞争/估值），修复个股层无分析师底座的结构不对称。

### Modified Capabilities
- `v4-result-reflection`：reflection/反骑墙从大类层推广到行业层 + 个股层 director。
- `v4-data-grounding`：数据铁律强化——分析 subagent 禁编价格数字，价格/财务唯一来源 = data-desk 核实值。

## Impact
- **角色 prompt**：新建4个（chokepoint + 3分析师），改造6个（stock bull/bear/director + industry bull/bear/director）。
- **schema**：design.md 加4个可选字段定义。
- **不影响**：信封外壳/状态机/约束链/v3/已落盘单元（新字段向后兼容）。
- **验证（沙箱）**：prompt 一致性 + py_compile（无新代码，stock_source 已单独验）；实际效果需部署机重跑权益深链（行业→个股）。
