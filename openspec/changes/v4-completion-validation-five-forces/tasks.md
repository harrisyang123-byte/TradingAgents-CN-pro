# Tasks — v4 Completion + Validation + Five Forces

> 严格按 B → C → D 顺序推进，每阶段完成后用户验收再进下一阶段

## 阶段 B：完整工程（先做，看整体效果）

### B1 个股下钻补全（14 个新增/升级）
- [ ] B1.1 联网取数 + 落盘：**新易盛 300502**（AI算力，1.6T 第二梯队）
- [ ] B1.2 联网取数 + 落盘：**天孚通信 300394**（AI算力，光器件）
- [ ] B1.3 联网取数 + 落盘：**北方华创 002371**（半导体设备龙头）
- [ ] B1.4 联网取数 + 落盘：**中微公司 688012**（半导体刻蚀设备）
- [ ] B1.5 联网取数 + 落盘：**华特气体 688268**（半导体材料-电子特气）
- [ ] B1.6 联网取数 + 落盘：**百济神州 06160**（创新药出海首选）
- [ ] B1.7 联网取数 + 落盘：**恒瑞医药 600276**（创新药本土龙头）
- [ ] B1.8 联网取数 + 落盘：**科伦博泰 06990**（创新药 ADC 出海标杆）
- [ ] B1.9 联网取数 + 落盘：**紫金矿业 601899**（铜+金双轮驱动）
- [ ] B1.10 联网取数 + 落盘：**北方稀土 600111**（稀土战略资产）
- [ ] B1.11 联网取数 + 落盘：**长江电力 600900**（大水电+红利底仓）
- [ ] B1.12 联网取数 + 落盘：**中国核电 601985**（核电核准加速）
- [ ] B1.13 联网取数 + 落盘：**腾讯 00700**（互联网+AI 应用入口）
- [ ] B1.14 联网取数 + 落盘：**阿里巴巴 09988**（云算力+AI 变现）
- [ ] B1.15 升级 **小米 01810** 到含 forward_view 完整版

### B2 alloc:industry:* 9 层升级
- [ ] B2.1 alloc:industry:人工智能算力 v2（基于 AI算力 v6 verdict + 中际旭创/新易盛/天孚通信 stock_weight）
- [ ] B2.2 alloc:industry:半导体 v2（中芯/北方华创/中微/华特气体）
- [ ] B2.3 alloc:industry:创新药 v2（百济/恒瑞/科伦博泰）
- [ ] B2.4 alloc:industry:有色资源 v2（紫金/北方稀土）
- [ ] B2.5 alloc:industry:电力公用事业 v2（长江电力/中国核电）
- [ ] B2.6 alloc:industry:互联网平台 v2（腾讯/阿里/小米）
- [ ] B2.7 alloc:industry:消费电子家电 v2（蓝思/立讯持仓内调整）
- [ ] B2.8 alloc:industry:新能源车 v2（观察仓位精简）
- [ ] B2.9 验证 sum_weight ≤ 行业 target_weight 一致性

### B3 关键 bug 修复
- [ ] B3.1 alloc:portfolio v3 verdict 顶层字段空 → 补 stance/situation/direction
- [ ] B3.2 AI算力 v6 verdict.stance="go" → 改为 "bullish"
- [ ] B3.3 asset:unclassified v1 → v2 升级 forward_view（按"待穿透"特性适配）
- [ ] B3.4 中际旭创 chokepoint_score 字段格式 → 与精细 schema 对齐

### B4 旧 v1 stock 升级 forward_view（10 个）
- [ ] B4.1 000063 中兴通讯 v2（通信设备/AI 算力外延）
- [ ] B4.2 002001 新和成 v2（化工/精细化学品）
- [ ] B4.3 002050 三花智控 v2（汽车热管理）
- [ ] B4.4 002415 海康威视 v2（安防+AI）
- [ ] B4.5 002517 恺英网络 v2（游戏）
- [ ] B4.6 09992 泡泡玛特 v2（潮玩）
- [ ] B4.7 603236 移远通信 v2（IoT 模组）
- [ ] B4.8 603663 三祥新材 v2（陶瓷/锆制品）
- [ ] B4.9 升级到 v2（注：300308 中际旭创/300433 蓝思/688981 中芯/01810 小米已升级或在 B1）

### B5 前端展示验证 + 优化
- [ ] B5.1 build_snapshot_v4 重生成全量静态快照
- [ ] B5.2 前端 dev 验证 AssetDetailTab 三层（verdict/forward_view/debate_rounds）展示完整
- [ ] B5.3 前端验证 IndustryDetailTab（chokepoint_map 精细版+forward_view+stocks 列表）
- [ ] B5.4 前端验证 StockDetailTab（如缺则记 backlog；当前可能没有此 Tab）
- [ ] B5.5 修复发现的展示 bug（数据存在但前端没显示）

### B6 文档/rerun-memory
- [ ] B6.1 rerun-memory.md 加 B 阶段所有变更日志
- [ ] B6.2 full-analysis-plan.md 13 步台账更新进度
- [ ] B6.3 backlog 加未来重跑提醒（如 collect_v4 重置坑保护、subagent 中文乱码 bug）

### B 阶段验收
- [ ] B 验收：用户 git pull + 前端三层 Tab 验证 + 推荐行业全部 ≥2 龙头股 → 拍板进入 C 阶段

---

## 阶段 C：回测验证机制（B 后做）

### C1 历史快照回放器
- [x] C1.1 设计 `scripts/v4_replay.py` —— 输入 unit_id + from_version + to_date，输出该时点判断 vs 实际行情对比
- [x] C1.2 数据源：股价用 AKShare 取历史，宏观用 FRED/AKShare，行业景气用 PE/ROE 历史
- [x] C1.3 输出格式：JSON + 简表 markdown（unit/version/judgment/actual/alpha/hit_or_miss）
- [x] C1.4 用中际旭创 v1→v6 跑通验证

### C2 判断准确率回填
- [x] C2.1 schema 加 `historical_alpha` 字段（每个 verdict 一个）
- [x] C2.2 v4_unit_cli write 时自动调用 v4_replay 回填上一版 alpha（若存在足够历史）
- [ ] C2.3 v4_query.build_*_detail 透传 historical_alpha 到前端

### C3 季度复盘报告
- [x] C3.1 `scripts/v4_quarterly_review.py` —— 扫所有 verdict 历史 → 按层（asset/industry/stock）汇总命中率/平均alpha/最大胜负/系统性偏差
- [x] C3.2 输出 `planning/v4/quarterly-review-YYYY-Qx.md`
- [x] C3.3 章节：本季度命中率/胜负 case 分析/系统性偏差识别/改进建议

### C4 critic 评审增强
- [x] C4.1 v4-investor-critic.md 加 historical_alpha 输入消费
- [x] C4.2 评审铁律加："如果上次判断错了，这次为什么会对？" 强制回答
- [x] C4.3 critic 输出 schema 加 `learning_from_history` 字段

### C 阶段验收
- [x] C 验收：用中际旭创+创新药跑回测 → 季度复盘报告产出 → 用户看效果 → 拍板进入 D 阶段

---

## 阶段 D0：决策链打通（信任感修复，CIO 投委会判定为「必做·最高优先」，插在 D 前）

> 用户反馈+CIO 体检: 系统看起来全但决策链断层(产业链→个股→买点→回测前端各自为政),不可信。这是雪中送炭,优先于五力。

### D0-1 估值推导链（解决"买点怎么来的,很草率"）
- [ ] D0-1.1 stock schema 加 `valuation_basis` 字段(显式: 目标价=forward EPS × 目标PE(对标谁) / 或 PB锚 / 或 DCF; 买点=目标价×安全边际)
- [ ] D0-1.2 给 17 个新架构 stock 补 valuation_basis 推导链(联网核实 EPS/PE/PB 锚)
- [ ] D0-1.3 v4-stock-director.md prompt 加"买点/目标价必须给推导链,禁止拍脑袋"铁律

### D0-2 产业链→个股连接（解决"不知道买什么"）
- [ ] D0-2.1 chokepoint_map 每个 top 环节加 `recommended_stock`(首选标的+卡位排序+是否已深析+unit_id链接)
- [ ] D0-2.2 行业 verdict 加 `investment_map`(瓶颈环节→推荐个股→为什么是它的明确推导链)
- [ ] D0-2.3 v4-industry-director.md prompt 加"chokepoint 必须落到可买个股+排序"铁律
- [ ] D0-2.4 给 6 个推荐行业补 investment_map

### D0-3 前端展示补全（解决"C 阶段看不到 + 个股无详情页"）
- [ ] D0-3.1 新建 StockDetailTab.vue(个股详情: 四维+forward_view+估值推导+止损+historical_alpha)
- [ ] D0-3.2 IndustryDetailTab chokepoint 地图加"推荐标的"列 + 点击跳个股
- [ ] D0-3.3 历史回测/historical_alpha 前端展示(StockDetailTab 内"判断准确率"区块)
- [ ] D0-3.4 v4_query.py build_stock_detail 新增(透传 stock 全字段给前端)
- [ ] D0-3.5 portfolio_v4.py 路由加 /stock/{code} + 前端路由跳转

### D0 验收
- [ ] D0 验收: 用户能从"产业链瓶颈地图"点击→看到推荐个股→点进个股详情→看到估值推导+买点依据+止损+历史准确率,全链条不断层

## 阶段 D：竞争五力补全 + A/B 测试（C 后做）

### D1 prompt 改造（先用旧版+新版双版本备用）
- [ ] D1.1 v4-industry-chokepoint.md 增强版（加波特五力 5 字段：entry_threat/substitute_threat/buyer_power/supplier_power/internal_rivalry）
- [ ] D1.2 v4-stock-analyst-competitive.md 增强版（消费行业五力 + 给个股具体打分）
- [ ] D1.3 schema 加可选字段 `five_forces`（嵌套 5 字段，向后兼容）

### D2 A/B 测试设计
- [ ] D2.1 选标的：半导体设备（北方华创）+ 创新药（百济神州）—— 两类商业模式差异大
- [ ] D2.2 跑两版：当前 chokepoint（无五力）vs 加五力 chokepoint
- [ ] D2.3 独立 critic 盲评：决策深度/风险识别/护城河可信度/可执行性/MECE 不重复 5 维度

### D3 据 A/B 结果决定
- [ ] D3.1 五力版 ≥ 旧版 +10 分 → 固化进 schema + 全行业重跑（约 4-5h 工作量）
- [ ] D3.2 提升 5-10 分 → 五力作为可选维度（行业层强制+个股层可选）
- [ ] D3.3 提升 < 5 分 → 不固化（避免过度复杂化），记 backlog

### D4 报告与归档
- [ ] D4.1 落盘 `planning/v4/five-forces-ab-test-report.md`
- [ ] D4.2 据决定更新 .kiro/specs/v4/design.md 与 chokepoint-framework.md

### D 阶段验收
- [ ] D 验收：A/B 报告产出 → 据数据决定是否固化 → 完成

---

## 全部完成后

- [ ] 总结报告：planning/v4/v4-completion-summary.md
- [ ] AGENTS.md 更新（如有架构层变更）
- [ ] OpenSpec change archive：移到 openspec/changes/archive/
