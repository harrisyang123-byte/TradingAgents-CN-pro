#!/usr/bin/env python3
"""
v4_verify_audit.py — RULE-DATA-VERIFIED 红线自动审计器

协议: planning/v4/self-evolving-optimization-loop.md (iteration 2 active_hole)
配套铁律: AGENTS.md §0bis + RULE-DATA-VERIFIED 永久红线

检查产物 data/v4/stocks/*.json 中所有数字字段是否配 verified_source URL。
正确范例: payload.value_creation_verified.source = "akshare stock_financial_abstract (verified)"
违规模式: target_price=¥45 但 evidence=[] 或 verified_sources 字段缺失

扫描以下数字字段路径 (路径 -> 是否需要 source):
  - target_price / price_at_judgment             (必须 verified)
  - valuation_basis.consensus_target              (必须 verified)
  - valuation_basis.scenarios.{bull,base,bear}.fair_price_range
  - forward_view_6dim.path_scenarios[].implied_target_price
  - pre_mortem.*.downside_price                   (iteration 1 新字段, 必须 verified_anchor)
  - pre_mortem.*.trigger_observed_values[].verified_source
  - pre_mortem.*.verified_anchor.verified_source_count >= 1
  - product_subdivision_deep.future_tam / future_share / forward_eps
  - value_creation.tam_penetration                (必须含 verified TAM 数据源)

输出:
  data/v4/_loop/verify_audit.json    全量审计
  data/v4/_loop/verify_audit.md      人读违规清单
  exit code 0 = 0 violations / 4 = 有违规 (对齐 collect_v4 风格)

用法: python3 scripts/v4_verify_audit.py
       python3 scripts/v4_verify_audit.py --strict   # exit=4 if any violation
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
STOCKS_DIR = ROOT / "data" / "v4" / "stocks"
LOOP_DIR = ROOT / "data" / "v4" / "_loop"
AUDIT_JSON = LOOP_DIR / "verify_audit.json"
AUDIT_MD = LOOP_DIR / "verify_audit.md"

URL_RE = re.compile(
    r"https?://"                                        # 任何 http(s) URL
    r"|akshare\.[a-z_]+\("                              # akshare 具体函数调用
    r"|stock_financial_abstract|stock_zh_a_hist|stock_zh_a_daily|stock_individual_info_em"
    r"|tonghuashun|wind|bloomberg|yole|idc|gartner|工信部|marketsandmarkets"
    r"|\d{4}\s*年(?:[1-4]季|半年|年)?报"                # 财报年份格式: 2024年报/2024年Q3报/2024半年报
    r"|公告\s*\d{4}|\d{4}\s*公告"                        # 公告年份
    r"|新浪财经|东方财富|证监会"
    , re.I)
# 注: 故意不收录 'verified' 字面量(避免自我 Goodhart, source='verified' 不算来源)
# 也不收录纯 'akshare' (必须 akshare.func() 调用形式才算)
NUMBER_RE = re.compile(r"\d+\.?\d*\s*(?:亿|万|%|x|倍|元|¥|\$|B|M)")


def has_source_signal(value: Any) -> bool:
    """检查值是否含 verified_source 信号 (URL/具体数据源函数/财报年份-机构)"""
    if value is None:
        return False
    s = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    return bool(URL_RE.search(s))


def value_has_number(value: Any) -> bool:
    if value is None:
        return False
    s = str(value) if not isinstance(value, (dict, list)) else json.dumps(value, ensure_ascii=False)
    return bool(NUMBER_RE.search(s))


def audit_payload(payload: dict) -> list[dict]:
    """对 payload dict 跑全量审计, 返回 violation 列表

    可被 scripts/v4_unit_cli.py import 后在 stock:* 写盘咽喉强制调用:
        from v4_verify_audit import audit_payload
        violations = audit_payload(payload)
        if any(v['severity'] == 'fatal' for v in violations): exit=4

    协议铁律 Part 7 #13: director write_unit 落盘前必跑(2026-06-17 iteration 2)
    """
    violations: list[dict] = []
    p = payload or {}

    # ① target_price / price_at_judgment 顶层
    if p.get("target_price") is not None:
        ev = p.get("evidence", []) or []
        ev_blob = json.dumps(ev, ensure_ascii=False) if ev else ""
        if not has_source_signal(ev_blob):
            violations.append({
                "field": "target_price",
                "value": p.get("target_price"),
                "issue": "target_price 数字存在但 evidence 数组无对应 verified_source URL/数据源",
                "severity": "fatal",
            })

    # ② evidence 数组本身是否空 (director schema 要求填) 且 entry 三态
    ev = p.get("evidence")
    verdict_blob = json.dumps(p.get("verdict", {}), ensure_ascii=False)
    if not ev or (isinstance(ev, list) and len(ev) == 0):
        if value_has_number(verdict_blob):
            violations.append({
                "field": "evidence",
                "value": "[] empty",
                "issue": "evidence 空但 verdict 含数字; director schema 要求 evidence min 5 项",
                "severity": "fatal",
            })
    elif isinstance(ev, list):
        # 三态实测: 每条必须含 claim+source+status, 缺 source = fatal, 缺 status = should
        for i, entry in enumerate(ev):
            if not isinstance(entry, dict):
                continue
            if entry.get("_doc"):
                continue  # _doc 是 schema 注释行, 跳过
            if not entry.get("source"):
                violations.append({
                    "field": f"evidence[{i}].source",
                    "value": entry.get("claim", "?")[:50] if isinstance(entry.get("claim"), str) else "?",
                    "issue": "evidence 条目缺 source 字段 (director schema 强制 claim+source+status 三态)",
                    "severity": "fatal",
                })
            if not entry.get("status"):
                violations.append({
                    "field": f"evidence[{i}].status",
                    "value": entry.get("claim", "?")[:50] if isinstance(entry.get("claim"), str) else "?",
                    "issue": "evidence 条目缺 status 字段 (verified|estimated|missing 三选一)",
                    "severity": "should",
                })

    # ③ valuation_basis 数字字段
    vb = p.get("valuation_basis", {})
    if isinstance(vb, dict):
        ct = vb.get("consensus_target")
        if ct and value_has_number(ct) and not has_source_signal(ct):
            violations.append({
                "field": "valuation_basis.consensus_target",
                "value": str(ct)[:80],
                "issue": "consensus_target 含数字但无 verified_source(应标卖方报告/共识)",
                "severity": "should",
            })

    # ④ forward_view_6dim.path_scenarios[].implied_target_price
    fv = p.get("forward_view_6dim", {})
    if isinstance(fv, dict):
        for ps in fv.get("path_scenarios", []) or []:
            if isinstance(ps, dict):
                itp = ps.get("implied_target_price")
                if itp not in (None, 0, "0"):
                    name = ps.get("name", "?")
                    trigger = ps.get("trigger", "") or ""
                    if not has_source_signal(trigger) and not has_source_signal(ps):
                        violations.append({
                            "field": f"forward_view_6dim.path_scenarios[{name}].implied_target_price",
                            "value": str(itp),
                            "issue": "情景 implied_target_price 含数字但 trigger 无 verified_source(应锚定财报/卖方/历史可比)",
                            "severity": "should",
                        })

    # ⑤ pre_mortem (iteration 1 新字段) 必须有 verified_anchor
    pm = p.get("pre_mortem")
    if isinstance(pm, dict):
        for scene in ("fundamental_double_kill", "valuation_kill", "policy_or_blackswan_kill"):
            obj = pm.get(scene)
            if not isinstance(obj, dict):
                continue
            va = obj.get("verified_anchor")
            if not isinstance(va, dict) or not va.get("verified_source_count"):
                if obj.get("downside_price") and value_has_number(obj.get("downside_price")):
                    violations.append({
                        "field": f"pre_mortem.{scene}.verified_anchor",
                        "value": "missing or count=0",
                        "issue": "pre_mortem 场景含 downside_price 数字但 verified_anchor 未填 (RULE-DATA-VERIFIED + iteration 1 critic 6.16 ⑥)",
                        "severity": "fatal",
                    })

    # ⑥ value_creation
    vc = p.get("value_creation", {})
    if isinstance(vc, dict):
        tam = vc.get("tam_penetration")
        if tam and value_has_number(tam) and not has_source_signal(tam):
            violations.append({
                "field": "value_creation.tam_penetration",
                "value": str(tam)[:80],
                "issue": "TAM 数字未配 verified_source (通富 $157B 事故同型)",
                "severity": "fatal",
            })

    # ⑦ product_subdivision_deep
    psd = p.get("product_subdivision_deep")
    if isinstance(psd, dict):
        for k in ("future_tam", "future_share", "forward_eps", "forward_revenue"):
            v = psd.get(k)
            if v and value_has_number(v) and not has_source_signal(v):
                violations.append({
                    "field": f"product_subdivision_deep.{k}",
                    "value": str(v)[:80],
                    "issue": f"{k} 含数字但无 verified_source",
                    "severity": "fatal",
                })

    return violations


def audit_one_stock(d: dict) -> list[dict]:
    """文件级审计入口, 调用 audit_payload 对 d.payload 跑全量审计"""
    return audit_payload(d.get("payload", {}))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="exit=4 if any violation found")
    parser.add_argument("--single", help="审计单个 stock JSON 文件路径, 用于 v4_unit_cli.py 写盘前调用")
    args = parser.parse_args()

    LOOP_DIR.mkdir(parents=True, exist_ok=True)

    # 单文件模式 (v4_unit_cli.py 写盘咽喉调用)
    if args.single:
        try:
            d = json.loads(Path(args.single).read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[verify_audit] failed to read {args.single}: {e}", file=sys.stderr)
            return 1
        violations = audit_one_stock(d)
        fatal_count = sum(1 for v in violations if v.get("severity") == "fatal")
        print(json.dumps({
            "single_file": args.single,
            "total_violations": len(violations),
            "fatal_count": fatal_count,
            "violations": violations,
        }, ensure_ascii=False, indent=2))
        if args.strict and fatal_count > 0:
            return 4
        return 0

    if not STOCKS_DIR.exists():
        print(f"[verify_audit] no stocks dir: {STOCKS_DIR}", file=sys.stderr)
        return 0

    files = sorted(STOCKS_DIR.glob("*.json"))
    all_violations: dict[str, list[dict]] = {}
    severity_count = {"fatal": 0, "should": 0}
    stocks_clean = 0
    stocks_with_fatal = 0

    for f in files:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[verify_audit] skip {f}: {e}", file=sys.stderr)
            continue
        violations = audit_one_stock(d)
        if violations:
            all_violations[f.stem] = violations
            for v in violations:
                severity_count[v["severity"]] = severity_count.get(v["severity"], 0) + 1
            if any(v["severity"] == "fatal" for v in violations):
                stocks_with_fatal += 1
        else:
            stocks_clean += 1

    n = len(files)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total_stocks": n,
        "stocks_clean": stocks_clean,
        "stocks_with_fatal": stocks_with_fatal,
        "stocks_with_any_violation": len(all_violations),
        "compliance_pct": round(stocks_clean / max(n, 1) * 100, 1),
        "severity_count": severity_count,
        "violations": all_violations,
    }
    AUDIT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# RULE-DATA-VERIFIED 红线自动审计报告",
        f"\n生成: {report['generated_at']}",
        f"扫描: {n} 只 stock",
        f"- 完全合规: **{stocks_clean}** ({report['compliance_pct']}%)",
        f"- 含 fatal 违规: **{stocks_with_fatal}**",
        f"- 含任意违规: **{len(all_violations)}**",
        f"- fatal 违规计数: {severity_count.get('fatal', 0)}",
        f"- should 违规计数: {severity_count.get('should', 0)}",
        "",
        "## 违规明细 (top 15)",
    ]
    for stem, vios in list(all_violations.items())[:15]:
        md_lines.append(f"\n### {stem} ({len(vios)} 项)")
        for v in vios:
            md_lines.append(f"- [{v['severity']}] `{v['field']}`: {v['issue']}")
            if v.get("value"):
                md_lines.append(f"  - value: `{v['value']}`")
    AUDIT_MD.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"[verify_audit] stocks={n} clean={stocks_clean} fatal_stocks={stocks_with_fatal} compliance={report['compliance_pct']}%")
    print(f"[verify_audit] fatal={severity_count.get('fatal',0)} should={severity_count.get('should',0)}")
    print(f"[verify_audit] report: {AUDIT_MD.relative_to(ROOT)}")

    if args.strict and (severity_count.get("fatal", 0) > 0 or stocks_with_fatal > 0):
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
