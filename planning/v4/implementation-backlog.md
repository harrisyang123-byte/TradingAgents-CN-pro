# v4 实施待办清单（Implementation Backlog）— 应改造未改造台账

> 用途：把"已设计/已验证、但还没落到代码/prompt/schema"的事项集中登记，防止设计与落地脱节。
> 维护：每完成一项打勾 + 注明 commit；新设计产生的待办随手追加。
> 创建：2026-06-10（用户要求"所有应改造未改造记录 plan"）。

## 图例
- [ ] 未做　[~] 部分做　[x] 已完成
- 优先级：P0 阻塞后续 / P1 重要 / P2 增强

---

## A. data-desk 数据能力补齐（最优先——所有数据都该走 data-desk）

- [x] **P0 A股个股数据模块**（commit 见下）：新建 `app/services/v4/stock_source.py`(对齐 macro_source 降级风格,AKShare 取 股价/市值/PE-TTM/PB/PE分位/财务/近1年涨幅) + collect_v4._build_stock_pack 集成(AKShare优先→Mongo兜底→降级)。✅降级行为验证通过(无akshare不崩/非A股识别);✅akshare本体可装(1.18.64),估值接口已对齐新版(stock_value_em);⚠️沙箱无外网访问akshare数据源(ConnectionError),实测取数待生产环境(有外网)验证。
- [ ] **P0 运行环境装 akshare**：当前环境 import 失败，宏观/个股取数模块都跑不了(只能临时装实测)。需在部署环境固化 akshare 依赖。
- [ ] **P1 PE/PB 历史分位**：服务预期差锚2"定价充分度"。AKShare `stock_a_indicator_lg` 可取。
- [ ] **P2 机构覆盖度数据**：服务预期差锚2(覆盖少=未发现)。AKShare 覆盖弱，可能需研报数代理或标 missing。
- [ ] **P1 web_only 宏观的稳定源**：reverse_repo_7d / tsf_yoy / usdcny / dxy / fed_funds / 标普纳指 / vix / 油金铜 仍靠主agent手工联网，每次重跑要补。考虑 FRED API / 稳定接口。

## B. Chokepoint + 预期差 选股理论落地（设计已验证，prompt/schema 未固化）

- [ ] **P1 新建 `agents/advisor/v4-industry-chokepoint.md`**：产业链瓶颈分析师角色(四维判定+逆向工程+替代路径)。已 A/B 验证专职角色胜出。
- [ ] **P1 瓶颈专项调研员机制**：主agent对 top1-2 瓶颈派 subagent 深挖，固化到编排流程(chokepoint-framework §3)。
- [ ] **P1 个股层3分析师**(财务/竞争/估值)：v4 个股层现在直接 bull/bear 无分析师底座(结构不对称)。已实测分队胜出且纠正乐观偏差。需新建角色 prompt。
- [ ] **P1 预期差三锚落到个股 prompt**：隐含增速缺口/定价充分度/催化。理论已定稿 stock-selection-theory.md，未落到角色 prompt。
- [ ] **P1 改 `v4-stock-bear.md`**：加替代路径专项攻击。
- [ ] **P2 改 `v4-stock-bull.md`**：加瓶颈溢价逻辑。
- [ ] **P2 改 `v4-industry-bear.md`**：加替代路径挑战。
- [ ] **P1 个股 Scout 加 Chokepoint 6维评分**：注意 v4 当前无独立 scout.md，需确认 Scout 落点。
- [ ] **P1 payload schema 正式定义** `chokepoint_map` / `top_chokepoints` / `expectation_gap` / `discovery_level` 字段：当前是模式A手动塞进 payload，未进 schema 文档。

## C. 数据可信铁律固化（这次中际旭创"420"教训）

- [~] **P0 数据铁律已写入** stock-selection-theory.md §6(价格/财务必须 data-desk 核实，分析 subagent 禁编数字)。**未固化到各 subagent 的 prompt**——应在每个分析角色 prompt 里硬性写明"不得自行产出价格/PE/市值数字"。
- [ ] **P1 director 落盘前数字核对清单**：编排流程加一步"verdict 内每个价格/PE/目标价是否来自 data-desk 核实值"。

## D. reflection / 反骑墙 推广（设计说全局通用，仅大类层落地）

- [~] **P1 行业层 director reflection/反骑墙**：本轮手动加了(industry v3)，未固化到 v4-industry-director.md prompt。
- [~] **P1 配比层 reflection**：alloc:portfolio 手动加了 reflection，未固化到 v4-allocation-director.md。
- [ ] **P2 个股层 director reflection**：未落地。

## E. 前端展示

- [x] **chokepoint_map 行业详情 UI**（commit a618a03）。
- [x] **unclassified 大类卡片 + 详情**（commit 2c165be / ce09318）。
- [ ] **P2 个股层预期差/Chokepoint评分展示**：个股详情页展示三锚+评分。
- [ ] **P2 reflection 蓝条**在行业/个股层确认渲染（大类层已有）。
- [ ] **P2 overview unclassified target** 已修；复查其它非标准 stance 兜底是否齐全。

## F. 模式A临时产物正式化

- [ ] **P1 industry payload 的 chokepoint_map** 当前透传靠 build_industry_detail 手加，schema 未正式纳入 design.md。
- [ ] **P2 alloc:portfolio 的 reflection** 字段未进 alloc schema。

---

## 已完成里程碑（备查）
- Wave1 七大类研究单元全部重跑(asset:* v2-v4) + unclassified 占位
- Wave2 alloc:portfolio 资产配比(equity_quota=44%)
- Chokepoint 框架设计 + 两轮实测(融合vs专职 / 单兵vs分队) + 混合分队架构定稿
- 个股层"单兵vs分队"实测(中际旭创) → 个股3分析师方向确立
- 选股理论从"估值分位"重构为"预期差驱动" + A/B 验证
- Wave3 首跑 industry:人工智能算力(chokepoint_map 5环节) + 前端可视
