# 项目总结

## 概览
- **Feature**: v4 — 分层独立深度投研系统（七大类资产 → 行业 → 个股的单元化常驻分析）
- **完成时间**: 2026-06-07
- **状态**: ⚠️ 部分完成（6 个任务中 Task 0 / Task 1 完整交付，Task 2 仅后端落地，Task 3/4/5 未开始）
- **执行模式**: staged（按 design 五阶段落地，v3 完全不动，独立集合 `v4_units` / 独立目录 `data/v4/` / 独立路由）

## 任务完成情况

| 任务 | 范围 | 实现状态 | 说明 |
|------|------|----------|------|
| **Task 0** 单元化基础骨架 | 信封 schema / 七大类常量 / 落盘 / 索引 / 运行锁 / 纯只读状态机 / CLI 骨架 / DB 初始化 | ✅ 完整 | 17 项单测全部 PASS（`scripts/test/test_v4_unit_store.py`） |
| **Task 1** S1 资产层 | 七大类穿透归类 + 6 个大类研究部门 Agent + collect_v4 + 编排器 asset 路径 | ✅ 完整 | 归类/采集/编排骨架齐备 |
| **Task 2** S2 配比机制 | 配比总监 Agent + 状态机收口 + 只读路由 + **前端 Tab1** | ⚠️ 部分 | 后端齐（agent/router/query/state）；**前端 Vue 组件未落地** |
| **Task 3** S3 权益深链 | 行业深辩→配比→个股→行业内配比 + Tab2/3 | ⬜ 未开始 | 无 `industry_candidates.py` / `v4-industry-*` / `v4-stock-*` / 前端 |
| **Task 4** S4 非权益六类 | 现金/固收/大宗/贵金属/房地产/另类差异化方案 | ⬜ 未开始 | 无 `plan:<class>` 路径 / 方案模板 / PlanCard |
| **Task 5** S5 双跑/导入/快照/报告 | import_v4 / build_snapshot_v4 / run_report_v4 | ⬜ 未开始 | 仅路由内 `/import` 端点骨架存在，三个脚本均缺失 |

> tasks.md 进度表把 Task 2 标为 ⬜，但实际后端已落地（`v4_query.py` / `portfolio_v4.py` / `v4-allocation-director.md`）。实测状态以本报告为准。

## 需求完成情况（按实现，非按设计覆盖）

| 需求 | 实现状态 |
|------|----------|
| FR-001 七大类穿透归类 + 下钻深度表 | ✅ |
| FR-002 大类研究部门（3 轮辩论 + 总监拍板） | ✅ |
| FR-003 资产配比 + 主动归零 + equity_quota 下传 | ⚠️ 后端逻辑在 agent/编排器，前端未呈现 |
| FR-004 CLI 触发 + 五色状态机 | ✅（CLI 骨架 + 纯只读状态机已验证） |
| FR-005 上游快照指纹 + stale 软提醒 | ✅（`v4_state.compute_status` 已测 yellow/约束链报警） |
| FR-006 权益深链（行业深辩→配比→个股→行业内配比） | ⬜ 未实现 |
| FR-007 非权益六类差异化方案 | ⬜ 未实现 |
| FR-008 三层 Tab 前端 | ⬜ 前端无任何 v4 组件 |
| FR-009 双跑同构落盘 + 导入 | ⚠️ `/import` 路由骨架在，导入/快照/报告脚本缺失 |

**需求完成率（按 AC 实现口径）：约 50%**（51 条 AC 中，Task 0+1 覆盖的 ~26 条已实现，Task 2 后端 AC 部分实现，前端及 Task 3/4/5 的 AC 未实现）。

> 注意：tasks.md 的「需求覆盖矩阵 51 条 100% ✅」是**设计阶段的覆盖声明**，非实现完成度，二者不应混淆。

## 代码质量
- **新增文件**: 22 个（Python 10 + JS 1 + Agent .md 7 + 脚本/测试 4）
  - `app/services/v4/`: `asset_classes.py` / `v4_unit_store.py` / `v4_state.py` / `v4_classifier.py` / `v4_query.py` / `__init__.py`
  - `app/routers/portfolio_v4.py`（已注册到 `main.py:737-738`）
  - `scripts/`: `collect_v4.py` / `workflow-v4-advisor.js` / `run_v4.sh` / `v4_unit_cli.py` / `init_v4_db.py` / `v4_status.py` / `v4_query.py`
  - `agents/advisor/v4-asset-*.md`（6 个研究部门）+ `v4-allocation-director.md`
- **修改文件**: 1 个（`app/main.py` 注册路由）
- **编译状态**: ✅ 全部通过（`py_compile` 全绿 + `node --check workflow-v4-advisor.js` 通过）
- **测试状态**: ✅ Task 0 单测 17/17 PASS

**亮点：**
- 状态机 `v4_state.py` 严格遵守「只读、只报警、绝不触发重跑/改数值」铁律（FR-005 / AC5.5），`compute_status` / `check_constraint_chain` 为纯函数，可测性好。
- 落盘采用「临时文件 + rename」原子写（`v4_unit_store.write_unit`），覆盖单元不污染其它单元，满足 NFR4.2 / AC9.4。
- 运行锁含 pid 存活检测 + 陈旧锁超时抢占（`acquire_lock`），防并发重入（AC4.7），实现稳健。
- 指纹算法复用 v3 `stage_cache._fingerprint`（带本地兜底），口径统一，符合「不重造轮子」原则。
- 路由层无任何触发 LLM 的写接口，触发链路分离（AC4.6）落实到位。

**待改进（具体到文件）：**
- `app/services/v4/v4_query.py:24` `load_user_units` 中 `except Exception: pass` 静默吞掉 Mongo 异常，建议至少 `logger.warning`，否则线上 Mongo 故障会无声降级到文件回退，难定位。
- `app/services/v4/v4_state.py:fingerprint` 用宽泛 `except Exception` 兜底，建议收窄为 `ImportError`，避免掩盖 stage_cache 内部真实错误。
- `app/routers/portfolio_v4.py:v4_import` 直接把外部 `payload` 整包 `$set` 入库，未校验 `schema_version` / `unit_type` 合法性，建议导入前用 `parse_unit_id` 校验 `unit_id` 格式，拒绝非法单元，防脏数据入库。

## 🔒 安全检查
| 检查项 | 状态 | 说明 |
|--------|------|------|
| 硬编码密钥/凭据 | ✅ | v4 全部文件未发现硬编码 API key / 密码 / token（NFR5.2 通过） |
| 命令注入 / 危险调用 | ✅ | 无 `os.system` / `eval` / `shell=True`；文件名经 `_safe_name` 正则过滤路径分隔与控制字符 |
| 路径遍历 | ✅ | `path_for` 经 `_safe_name(re.sub(r"[/\\\x00-\x1f]","_"))` 处理，unit_id 拼路径前已消毒 |
| 敏感数据落盘约定 | ✅ | `.gitignore` 已含 `data/` 与 `data/**/*.json`，持仓/处方不会误入版本库（AC9.6 / NFR5.1） |
| 接口鉴权 | ✅ | `portfolio_v4.py` 所有端点经 `Depends(get_current_user)`，含 `/import` 写接口 |
| 导入端点输入校验 | ⚠️ | `/import` 未校验信封 schema/unit_id 合法性即 upsert（见上「待改进」） |

**⚠️ 发现的设计张力（需在 Task 5 解决）：**
- **FR-009 AC9.3 与 .gitignore 冲突**：设计声明「git 传输载体 = `data/v4/` 下单元粒度 JSON」，但 `.gitignore` 已整体忽略 `data/`（含 `data/**/*.json`）。这意味着「AI 代跑产物经 git 传回本地」的链路**当前无法成立**——代跑生成的单元 JSON 在 data/v4 内会被 git 忽略。可选解法：(a) 走已保留追踪的 `frontend/public/snapshot/v4/`（`build_snapshot_v4.py` 的目标，但该路径含财务数据须私有仓）；(b) 为 v4 单元另设非忽略目录 + 强制 `git add -f`。**建议在 Task 5 实现前先定夺，否则双跑闭环跑不通。**

## 测试结果
- **Task 0 单元测试**：17/17 PASS（状态机五色、写读往返、版本递增、单元隔离、运行锁、路径映射、索引）。
- **端到端 / 集成测试**：`/workspace/.kiro/tests/v4/` 目录为空，**未产出 test-report.md，端到端测试阶段未执行**。
- 由于 Task 2 前端、Task 3/4/5 整体未实现，三层 Tab 的前端展示、双跑一致性、幂等导入均**无法进行端到端验证**。
- 建议：在 Task 2 前端落地后补充 API 契约测试（`/overview` / `/units/status` / `/asset/{class}`），并在 Task 5 完成后做「同份 holdings 本地跑 vs 代跑产物 schema 比对」与「重复 import 幂等」验证。

## 建议
1. **优先补齐 Task 2 前端**（`AssetAllocationTab.vue` / `AssetCard.vue` / `UnitStatusBadge.vue` / `EmptyUnitState.vue` + `useV4Units.ts`）：后端 `/overview` 已就绪，前端缺位导致 FR-008/AC8.1/8.4/8.5 完全不可见，是当前最大「看不见」缺口。
2. **在动工 Task 5 前先解决 .gitignore vs git 传输载体的冲突**（见安全检查），否则「你来跑、我本地拉取展示」这一核心诉求无法闭环。
3. **收紧三处异常处理与导入校验**（`v4_query.py:24`、`v4_state.py:fingerprint`、`portfolio_v4.py:v4_import`），避免线上无声降级与脏数据入库。
4. **同步 tasks.md 进度表**：Task 2 后端已实现却仍标 ⬜，建议拆为「Task 2a 后端 ✅ / Task 2b 前端 ⬜」，让进度反映真实状态。
5. **补 v4 集成测试骨架**：当前仅有 Task 0 store 层单测，建议为 `v4_classifier` 归类、`v4_state` 边界、路由契约各补一组测试。

## 结论
v4 的**地基质量很高**：单元化信封 + 纯只读状态机 + 原子落盘 + 运行锁这套核心抽象设计清晰、实现稳健、有单测背书，且严格复用 v3 既有资产、对 v3 零侵入。但**整体仅完成约 40%~50%**——Task 0/1 完整、Task 2 仅后端、Task 3/4/5 未动，前端三层 Tab 完全缺位，双跑闭环存在未解决的 .gitignore 设计冲突。当前产物**尚不可端到端使用**，距离「持续深度分析的投研公司」目标还需完成剩余 3.5 个阶段。建议按「Task 2 前端 → 解决 git 传输冲突 → Task 3 权益深链 → Task 4 非权益 → Task 5 双跑」顺序推进。

---

## 📊 结构化评估数据

> ⚠️ 以下 JSON 数据块供自我优化系统解析，请勿修改格式

```json
{
  "review_version": "1.0",
  "timestamp": "2026-06-07T00:48:00Z",
  "scores": {
    "requirements_completion": 0.48,
    "code_quality": 0.88,
    "test_coverage": 0.30,
    "security_check": 0.92,
    "overall": 0.62
  },
  "issues": [
    {
      "type": "completeness",
      "severity": "high",
      "description": "Task 3/4/5 完全未实现，Task 2 前端缺位，三层 Tab 前端无任何 v4 组件，FR-006/007/008 未落地，产物不可端到端使用",
      "suggestion": "优先补齐 Task 2 前端，再依序推进 Task 3/4/5"
    },
    {
      "type": "security",
      "severity": "high",
      "description": "FR-009 AC9.3 设计的 git 传输载体 data/v4/*.json 被 .gitignore 整体忽略（data/ 规则），AI 代跑产物无法经 git 回传本地，双跑闭环不成立",
      "suggestion": "Task 5 实现前定夺：走 frontend/public/snapshot/v4/（私有仓）或为 v4 单元另设非忽略目录 + git add -f"
    },
    {
      "type": "security",
      "severity": "medium",
      "description": "portfolio_v4.py 的 /import 端点未校验信封 schema/unit_id 合法性即整包 $set upsert，存在脏数据入库风险",
      "suggestion": "导入前用 parse_unit_id 校验 unit_id 格式与 schema_version，拒绝非法单元"
    },
    {
      "type": "code_quality",
      "severity": "low",
      "description": "v4_query.py:24 与 v4_state.py:fingerprint 使用宽泛 except Exception 静默吞异常，线上 Mongo/导入故障会无声降级难定位",
      "suggestion": "收窄异常类型并补 logger.warning"
    },
    {
      "type": "process",
      "severity": "low",
      "description": "tasks.md 进度表 Task 2 标 ⬜ 但后端已实现，进度与实际不符",
      "suggestion": "Task 2 拆为后端(✅)/前端(⬜)两条，进度反映真实状态"
    }
  ],
  "agent_feedback": {
    "requirements_agent": "优点：把用户三轮口语化方向准确固化为 9 条 FR + 51 条 AC，七大类机构级框架专业，约束链/状态机/双跑三大机制定义清晰。问题：单 Feature 9 条 FR 范围偏大，已自觉声明 staged 但仍埋下一次难完成的隐患。建议：超 8 条 FR 时主动建议拆 v4.1/v4.2 多 Feature。",
    "design_agent": "优点：没另起炉灶，精准复用 v3 stage_cache/build_snapshot/agent 范式，'分析单元'抽象一举落地独立触发+软提醒+git传输+状态机四诉求，3 张 Mermaid + 文件结构 + 五阶段落地完整。问题：FR-009 git 传输载体(data/v4)与既有 .gitignore(data/ 整体忽略)冲突未在设计中识别，是落地阻塞点。建议：设计阶段应核对 .gitignore 等既有约束与新增产物路径的兼容性。",
    "tasks_agent": "优点：6 任务依赖顺序清晰，Task 0 硬前置识别正确，需求覆盖矩阵详尽。问题：未对'后端可独立于前端交付'做更细粒度拆分，导致 Task 2 实际部分完成时进度表无法准确表达。建议：跨端任务拆为后端/前端子任务。",
    "development_agent": "优点：Task 0/1 实现质量高——原子写、运行锁、纯只读状态机均稳健且有 17 项单测背书，复用 v3 指纹算法，对 v3 零侵入，全部文件编译通过无硬编码密钥。问题：实际只完成约 2.5/6 任务即中断，前端完全未动；三处宽泛异常处理；/import 缺输入校验。建议：跨端阶段优先打通'后端+最小前端'垂直切片，让每阶段真正可见可用。",
    "testing_agent": "未执行：tests/v4 目录为空，无 test-report.md。因前端与 Task 3/4/5 未实现，端到端测试无法开展。仅开发自带的 Task 0 store 单测通过。建议后续在前端落地后补 API 契约测试与双跑一致性测试。"
  },
  "improvement_suggestions": [
    "需求阶段：FR 超 8 条应主动建议拆多个 Feature 分批交付，避免单 spec 一次难完成",
    "设计阶段：新增产物落盘路径必须与既有 .gitignore/构建约束交叉核对，提前暴露 data/ 被忽略这类阻塞",
    "任务阶段：Web 全栈跨端任务拆分为后端/前端子任务，使 staged 进度可精确反映部分完成",
    "开发阶段：分阶段交付优先'后端+最小前端'垂直切片而非先堆后端，保证每阶段端到端可见",
    "测试阶段：即使整体未完成，也应对已交付单元(Task 0/1)补集成测试并产出 test-report.md 占位"
  ]
}
```

---

## 执行信息

- **工作流ID**: 338736176191848448
- **总耗时**: 541分50秒
- **执行模式**: 阶段确认
- **项目类型**: 旧项目
- **完成时间**: 2026-06-07 00:51:48


## 🔒 依赖安全扫描 (SCA)

✅ 未发现已知漏洞
