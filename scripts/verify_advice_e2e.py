#!/usr/bin/env python3
"""verify_advice_e2e.py — v3 组合顾问端到端「可复跑」验证夹具脚本

把 2026-06-06 那次端到端真跑沉淀成一个**确定性、可重复执行**的回归脚本，
覆盖两件真跑才暴露的事：

  A) cash_floor 中止 bug 回归
     —— 证明「不注入现金项」会被风控规则引擎判 cash_floor 违规（编排在 Synthesizer 前中止），
        而 workflow-v3-advisor.js::runSynth 的「注入合成现金项」修复能让违规归零。
     依赖：tradingagents/agents/advisors/risk_rules.py（importlib 直载，绕开包 __init__，
           不拖 langgraph 等重依赖）。

  B) ingest 落库字段契约回归
     —— 真跑 scripts/ingest_advice.py --out-json，断言落地文档满足前端 Overview.vue /
        后端 paper.py overview 期望的字段契约（delta 数字 / go_nogo 大写 / holdings/target /
        codes↔prescription 关联 / industry_bucket 分组）。

夹具目录默认 .adv_e2e/（与本脚本同仓留存的真跑产物）。这些 JSON 是确定性的，
不联网、不连 MongoDB，因此任何人 clone 下来都能一键复跑回归。

用法：
    python scripts/verify_advice_e2e.py                  # 用默认 .adv_e2e/ 夹具
    python scripts/verify_advice_e2e.py --data-dir <dir> # 指定其它产物目录

退出码：全部断言通过 = 0；任一失败 = 1。
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = REPO_ROOT / ".adv_e2e"
RISK_RULES_PATH = REPO_ROOT / "tradingagents" / "agents" / "advisors" / "risk_rules.py"
INGEST_PATH = REPO_ROOT / "scripts" / "ingest_advice.py"

# 与 workflow-v3-advisor.js 默认约束保持一致（maxSingle 默认 30）。
DEFAULT_MAX_SINGLE = 30.0


# ── 小工具 ──────────────────────────────────────────────────

class Checks:
    """累计 PASS/FAIL，最后统一汇报。"""

    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0

    def ok(self, cond: bool, msg: str) -> bool:
        mark = "PASS" if cond else "FAIL"
        print(f"  [{mark}] {msg}")
        if cond:
            self.passed += 1
        else:
            self.failed += 1
        return cond


def _load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_risk_rules():
    """importlib 直载 risk_rules.py（绕开 tradingagents 包 __init__ 的重依赖）。"""
    spec = importlib.util.spec_from_file_location("risk_rules_standalone", RISK_RULES_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 risk_rules: {RISK_RULES_PATH}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _compute_cash_weight(allocations: Any, cash_floor: float) -> float:
    """复刻 runSynth 修复逻辑：现金 = 100 - 非现金行业 final_weight 之和；
    若分配表已有「现金」行则直接取其 final_weight。"""
    rows = allocations if isinstance(allocations, list) else (allocations or {}).get("allocations", [])
    invested = sum(
        float(r.get("final_weight", 0) or 0)
        for r in rows
        if str(r.get("industry", "")) != "现金"
    )
    cash_row = next((r for r in rows if str(r.get("industry", "")) == "现金"), None)
    if cash_row and cash_row.get("final_weight") is not None:
        return float(cash_row["final_weight"])
    if rows:
        return round(100.0 - invested, 1)
    return float(cash_floor)


def _extract_pm_results(pm_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """复刻 runSynth：pm_results 每项取其 result（无则取本身）。"""
    out = []
    for pr in pm_results:
        if isinstance(pr, dict):
            out.append(pr.get("result", pr))
    return out


# ── 验证 A：cash_floor 中止 bug 回归 ─────────────────────────

def verify_cash_floor_regression(data_dir: Path, checks: Checks) -> None:
    print("\n[A] cash_floor 中止 bug 回归（风控规则引擎）")

    rr = _load_risk_rules()
    macro = _load_json(data_dir / "macro_verdict.json", {}) or {}
    pm_results_raw = _load_json(data_dir / "pm_results.json", []) or []
    allocations = _load_json(data_dir / "industry_allocations.json", []) or []

    total_limit = float(macro.get("total_weight_limit") or 100)
    cash_floor = float(macro.get("cash_floor") or 0)
    max_single = float(macro.get("max_single_weight") or DEFAULT_MAX_SINGLE)

    checks.ok(cash_floor > 0,
              f"宏观裁判给了 cash_floor>0（={cash_floor}%），这是触发 bug 的前提")

    # PM 阶段原始产出（只含 Go 行业，无「现金」项）。
    pm_only = [r for r in _extract_pm_results(pm_results_raw) if str(r.get("industry", "")) != "现金"]
    checks.ok(len(pm_only) > 0 and all(r.get("industry") != "现金" for r in pm_only),
              f"PM 阶段产出只含 Go 行业、无现金项（{len(pm_only)} 个行业）")

    # ① 复现 bug：不注入现金 → 必报 cash_floor 违规。
    v_buggy = rr.check_pm_positions(list(pm_only), total_limit, cash_floor, max_single)
    cash_viol = [v for v in v_buggy if v.get("rule") == "cash_floor"]
    checks.ok(len(cash_viol) >= 1,
              f"复现 bug：未注入现金项时报 cash_floor 违规（{len(cash_viol)} 条）"
              f" → runSynth 会返回 violations_found 中止编排")

    # ② 应用修复：注入合成现金项 → cash_floor 违规消失。
    cash_weight = _compute_cash_weight(allocations, cash_floor)
    checks.ok(cash_weight >= cash_floor,
              f"注入现金权重 {cash_weight}% ≥ cash_floor {cash_floor}%")

    fixed = list(pm_only) + [{
        "industry": "现金",
        "final_weight": cash_weight,
        "positions": [{"code": "CASH", "target_weight": cash_weight}],
    }]
    v_fixed = rr.check_pm_positions(fixed, total_limit, cash_floor, max_single)
    cash_viol_fixed = [v for v in v_fixed if v.get("rule") == "cash_floor"]
    checks.ok(len(cash_viol_fixed) == 0,
              f"修复后 cash_floor 违规归零（总违规 {len(v_fixed)} 条）→ 流水线可达 Synthesizer")


# ── 验证 B：ingest 落库字段契约回归 ─────────────────────────

def verify_ingest_contract(data_dir: Path, checks: Checks) -> None:
    print("\n[B] ingest 落库字段契约回归（ingest_advice.py --out-json）")

    if not INGEST_PATH.exists():
        checks.ok(False, f"找不到 ingest 脚本：{INGEST_PATH}")
        return

    with tempfile.TemporaryDirectory() as tmp:
        out_path = Path(tmp) / "ingested_doc.json"
        proc = subprocess.run(
            [sys.executable, str(INGEST_PATH),
             "--data-dir", str(data_dir),
             "--user-id", "0" * 24,
             "--out-json", str(out_path)],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        ran_ok = proc.returncode == 0 and out_path.exists()
        if not checks.ok(ran_ok, "ingest_advice.py --out-json 正常退出并产出文档"):
            print(f"      stderr: {proc.stderr.strip()[:500]}")
            return
        doc = _load_json(out_path, {}) or {}

    matrix = doc.get("industry_matrix") or (doc.get("synthesis_result") or {}).get("industry_matrix") or []
    prescription = doc.get("prescription") or []
    checks.ok(isinstance(matrix, list) and len(matrix) > 0,
              f"industry_matrix 非空（{len(matrix)} 行）")
    checks.ok(isinstance(prescription, list) and len(prescription) > 0,
              f"prescription 非空（{len(prescription)} 条）")

    # 前端 Overview.vue 契约：每行 delta 为数字、go_nogo 合法、holdings/target 存在。
    bad_delta = [m.get("industry") for m in matrix if not isinstance(m.get("delta"), (int, float))]
    checks.ok(len(bad_delta) == 0,
              f"每行 delta 都是数字（前端目标%列依赖；缺失项={bad_delta}）")

    # go_nogo 合法值 = {GO, NOGO, ''}：原 bug 是小写 "Go" 永不匹配前端 ==='GO' → 全显「持有」。
    # 中性(标配)行业与现金项 go_nogo 留空是设计内行为（前端对空值正确显示「持有」）。
    invalid_go = [(m.get("industry"), m.get("go_nogo")) for m in matrix
                  if str(m.get("go_nogo", "")) not in ("GO", "NOGO", "")]
    checks.ok(len(invalid_go) == 0,
              f"go_nogo 无非法值（不得出现小写 Go/NoGo；异常项={invalid_go}）")
    has_uppercase = any(m.get("go_nogo") in ("GO", "NOGO") for m in matrix)
    checks.ok(has_uppercase,
              "至少有行业带大写 GO/NOGO（证明操作列不再全『持有』）")

    missing_w = [m.get("industry") for m in matrix
                 if m.get("holdings_weight") is None or m.get("target_weight") is None]
    checks.ok(len(missing_w) == 0,
              f"每行都有 holdings_weight + target_weight（调仓金额依赖；缺失项={missing_w}）")

    # delta 与 target-holdings 自洽。
    inconsistent = [
        m.get("industry") for m in matrix
        if isinstance(m.get("delta"), (int, float))
        and abs(float(m["delta"]) - (float(m.get("target_weight", 0)) - float(m.get("holdings_weight", 0)))) > 0.15
    ]
    checks.ok(len(inconsistent) == 0,
              f"delta == target_weight - holdings_weight（自洽性；异常项={inconsistent}）")

    # codes↔prescription 关联：存量动作(add/reduce/hold/sell)的 code 必须能 join 到矩阵行业；
    # 新建仓(new_position/new/buy)按定义不在现持仓 → 允许不在矩阵 codes 中。
    matrix_codes = {str(c) for m in matrix for c in (m.get("codes") or [])}
    EXISTING_ACTIONS = {"add", "reduce", "hold", "sell"}
    existing_codes = [str(p.get("code")) for p in prescription
                      if p.get("code") and str(p.get("action", "")).lower() in EXISTING_ACTIONS]
    orphan = [c for c in existing_codes if c not in matrix_codes]
    checks.ok(len(existing_codes) > 0 and len(orphan) == 0,
              f"存量动作 {len(existing_codes)} 条 code 全部能 join 到矩阵行业（孤儿={orphan}）")

    # 至少有非「持有」动作，证明「敢给指导」（与坏状态截图相反）。
    actions = {str(p.get("action", "")).lower() for p in prescription}
    actionable = actions & {"add", "reduce", "buy", "sell", "new_position", "new"}
    checks.ok(len(actionable) > 0,
              f"处方含可执行动作（非全『持有』）：{sorted(actionable)}")


# ── 主流程 ──────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="v3 组合顾问端到端可复跑验证夹具")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR),
                        help="workflow 产物夹具目录（默认 .adv_e2e/）")
    args = parser.parse_args()

    data_dir = Path(args.data_dir).resolve()
    print(f"验证夹具目录: {data_dir}")
    if not data_dir.exists():
        print(f"[ERROR] 夹具目录不存在: {data_dir}")
        return 1

    required = ["macro_verdict.json", "pm_results.json", "industry_allocations.json",
                "industry_matrix.json", "final_prescription.json"]
    missing = [f for f in required if not (data_dir / f).exists()]
    if missing:
        print(f"[ERROR] 夹具缺少必需文件: {missing}")
        return 1

    checks = Checks()
    verify_cash_floor_regression(data_dir, checks)
    verify_ingest_contract(data_dir, checks)

    print(f"\n汇总: {checks.passed} PASS / {checks.failed} FAIL")
    if checks.failed == 0:
        print("✅ 全部验证通过——cash_floor 修复有效 + ingest 字段契约对齐。")
        return 0
    print("❌ 存在失败断言，见上。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
