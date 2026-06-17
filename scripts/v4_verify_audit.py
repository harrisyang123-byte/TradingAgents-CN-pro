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

    # ⑧ debate_discipline (iteration 3 GATE attempt#1 fatal F3 修复, 协议 Part 7 #10 narrative cite 防 Goodhart 工程化)
    rounds = p.get("debate_rounds")
    if rounds:
        VALID_PARTIES = {
            "段永平-好生意", "费雪-scuttlebutt", "马克斯-紫苏叶", "马克斯-错杀龙头",
            "芒格-逆向", "达里奥-风险优先",
            "死亡清单-LTCM", "死亡清单-Archegos", "死亡清单-Woodford",
            "死亡清单-价值陷阱", "死亡清单-乐视康美", "死亡清单-抱团瓦解",
        }
        rounds_blob = json.dumps(rounds, ensure_ascii=False)

        def find_methodology_used(obj):
            """递归找所有 methodology_used 数组"""
            results = []
            if isinstance(obj, dict):
                if "methodology_used" in obj:
                    results.append(obj["methodology_used"])
                for v in obj.values():
                    results.extend(find_methodology_used(v))
            elif isinstance(obj, list):
                for item in obj:
                    results.extend(find_methodology_used(item))
            return results

        mu_arrays = find_methodology_used(rounds)
        if not mu_arrays:
            violations.append({
                "field": "debate_rounds.methodology_used",
                "value": "missing",
                "issue": "debate_rounds 存在但任一轮均未输出 methodology_used 数组 (skill v4-debate-discipline §4 + critic 6.6 ⑤ 强制)",
                "severity": "fatal",
            })
        else:
            # 至少一个数组要非空
            non_empty = [a for a in mu_arrays if isinstance(a, list) and len(a) > 0]
            if not non_empty:
                violations.append({
                    "field": "debate_rounds.methodology_used",
                    "value": f"all {len(mu_arrays)} arrays empty",
                    "issue": "methodology_used 全部为空数组 (Goodhart 退化, 同型于 attempt#1 critic 抓的 'cite 检测靠字段名不靠 narrative')",
                    "severity": "fatal",
                })
            else:
                for arr_idx, arr in enumerate(non_empty):
                    for entry_idx, entry in enumerate(arr):
                        if not isinstance(entry, dict):
                            continue
                        if entry.get("_doc"):
                            continue  # 跳过 schema 注释
                        # ② 三 key 必填
                        party = entry.get("派别") or entry.get("party")
                        narrative = entry.get("本轮如何用的") or entry.get("how_used")
                        ev_ref = entry.get("evidence_ref")
                        if not party:
                            violations.append({
                                "field": f"methodology_used[{arr_idx}.{entry_idx}].派别",
                                "value": str(entry)[:80],
                                "issue": "methodology_used 项缺 派别 字段",
                                "severity": "fatal",
                            })
                        if not narrative:
                            violations.append({
                                "field": f"methodology_used[{arr_idx}.{entry_idx}].本轮如何用的",
                                "value": party or "?",
                                "issue": "methodology_used 项缺 本轮如何用的 narrative",
                                "severity": "fatal",
                            })
                        if not ev_ref:
                            violations.append({
                                "field": f"methodology_used[{arr_idx}.{entry_idx}].evidence_ref",
                                "value": party or "?",
                                "issue": "methodology_used 项缺 evidence_ref (协议 Part 7 #11 verified 红线辩手层延伸: narrative 必须引证至少1个 evidence/input 索引)",
                                "severity": "fatal",
                            })
                        # ③ 派别 enum 白名单
                        if party and party not in VALID_PARTIES and "|" not in str(party):
                            # "|" 跳过(是 schema 模板未替换), 实际应是单一派别名
                            violations.append({
                                "field": f"methodology_used[{arr_idx}.{entry_idx}].派别",
                                "value": str(party)[:80],
                                "issue": f"派别 '{party}' 不在 skill v4-debate-discipline §2 enum 白名单",
                                "severity": "should",
                            })
                        # ④ narrative ≥ 30 字中文
                        if narrative and isinstance(narrative, str):
                            chinese_chars = re.findall(r"[\u4e00-\u9fff]", narrative)
                            if len(chinese_chars) < 30:
                                violations.append({
                                    "field": f"methodology_used[{arr_idx}.{entry_idx}].本轮如何用的",
                                    "value": narrative[:60],
                                    "issue": f"narrative 仅 {len(chinese_chars)} 中文字, < 30 字硬要求 (浅尝即止套话)",
                                    "severity": "should",
                                })
                        # ⑤ narrative substring 在 history blob 中
                        if narrative and isinstance(narrative, str) and party:
                            # 取 narrative 前 15 字符或派别 split('-')[1] 关键词在 rounds_blob 中找
                            party_kw = str(party).split("-")[-1] if "-" in str(party) else str(party)
                            narrative_head = narrative[:15] if len(narrative) >= 15 else narrative
                            if party_kw not in rounds_blob:
                                # 派别核心词在 history 也找不到 = 形式 cite
                                violations.append({
                                    "field": f"methodology_used[{arr_idx}.{entry_idx}].派别",
                                    "value": f"{party} -> {narrative_head}",
                                    "issue": f"派别核心关键词 '{party_kw}' 在 debate_rounds history 中找不到 (协议 Part 7 #10 narrative cite 防 Goodhart 形式 cite)",
                                    "severity": "fatal",
                                })

    # ⑨ acquisition_audit (iteration 4 落地, 数据采集层 SOP 审计, skill v4-data-acquisition §6 输出契约)
    acq = p.get("acquisition_audit")
    if acq is not None:  # 字段存在则严查; data-desk 单元产物或 stock 显式带 acquisition_audit 时触发
        if not isinstance(acq, dict):
            violations.append({
                "field": "acquisition_audit",
                "value": str(type(acq)),
                "issue": "acquisition_audit 应是 dict 不是其他类型",
                "severity": "fatal",
            })
        else:
            # ② 5 子键齐
            REQUIRED_KEYS = ["akshare_calls", "web_search_queries", "downgrade_chain", "missing_fields", "tam_3source_check"]
            for k in REQUIRED_KEYS:
                if k not in acq:
                    violations.append({
                        "field": f"acquisition_audit.{k}",
                        "value": "missing",
                        "issue": f"acquisition_audit 缺子键 '{k}' (skill v4-data-acquisition §6)",
                        "severity": "fatal",
                    })

            # ③ akshare_calls 反 Goodhart: 每项必含 ()参数, 不能纯字面占位
            ak_calls = acq.get("akshare_calls") or []
            if isinstance(ak_calls, list):
                for i, call in enumerate(ak_calls):
                    if not isinstance(call, str):
                        continue
                    # 跳过 _doc 注释类
                    if "_doc" in call.lower():
                        continue
                    # 必须含 () — 函数调用形式
                    if "(" not in call or ")" not in call:
                        violations.append({
                            "field": f"acquisition_audit.akshare_calls[{i}]",
                            "value": call[:80],
                            "issue": f"akshare_calls 项 '{call[:30]}...' 不含函数调用 ()参数 (Goodhart 占位字符串, skill §2/§7)",
                            "severity": "fatal",
                        })
                    # 禁止字面 "verified"/"akshare verified" 占位
                    if call.strip().lower() in ("verified", "akshare", "akshare verified", ""):
                        violations.append({
                            "field": f"acquisition_audit.akshare_calls[{i}]",
                            "value": call[:80],
                            "issue": "akshare_calls 项是字面占位字符串(verified/akshare), 协议 Part 7 #10 narrative cite 防 Goodhart 已禁",
                            "severity": "fatal",
                        })

            # ④ TAM 类字段若存在则 tam_3source_check 必 sources_count ≥ 3 + 多机构去重(P1)
            tam_check = acq.get("tam_3source_check")
            psd = p.get("product_subdivision_deep") or {}
            vc = p.get("value_creation") or {}
            has_tam = any(
                isinstance(d, dict) and any(k in d for k in ("future_tam", "tam_2030", "tam_penetration"))
                for d in (psd, vc)
            )
            if has_tam:
                if not isinstance(tam_check, dict):
                    violations.append({
                        "field": "acquisition_audit.tam_3source_check",
                        "value": str(tam_check),
                        "issue": "存在 TAM 字段但 tam_3source_check 缺失 (skill §1 铁律 2 + §4 多源交叉)",
                        "severity": "fatal",
                    })
                else:
                    n_sources = tam_check.get("sources_count", 0)
                    try:
                        n_sources = int(n_sources)
                    except (ValueError, TypeError):
                        n_sources = 0
                    if n_sources < 3:
                        violations.append({
                            "field": "acquisition_audit.tam_3source_check.sources_count",
                            "value": str(n_sources),
                            "issue": f"TAM 类多源交叉只有 {n_sources} 源, < 3 硬要求 (通富 $157B 同型隐患)",
                            "severity": "fatal",
                        })
                    # P1 多机构去重: sources 数组中机构名首词 distinct ≥3 (不允许 IDC 多份报告凑数)
                    sources = tam_check.get("sources") or []
                    if isinstance(sources, list) and len(sources) > 0:
                        # 取每条来源第一个空格前的机构名 (如 "IDC 2024Q3" -> "IDC")
                        institutions = {str(s).split()[0].strip().lower() for s in sources if str(s).strip()}
                        if len(institutions) < 3:
                            violations.append({
                                "field": "acquisition_audit.tam_3source_check.sources",
                                "value": f"distinct institutions={len(institutions)}",
                                "issue": f"TAM 多源去重后只 {len(institutions)} 个不同机构, < 3 硬要求 (引 3 份 IDC 报告凑数 = 多源造假)",
                                "severity": "fatal",
                            })
                    # P1 锁源优先级: web_search_queries 数组中 TAM 相关查询必 ≥2 项 tier ≤ 2
                    wsq = acq.get("web_search_queries") or []
                    if isinstance(wsq, list) and wsq:
                        tam_queries = [q for q in wsq if isinstance(q, dict) and q.get("query") and ("tam" in str(q.get("query", "")).lower() or "市场规模" in str(q.get("query", "")) or "TAM" in str(q.get("query", "")))]
                        if tam_queries:
                            tier_le2 = [q for q in tam_queries if q.get("tier") in (1, 2)]
                            if len(tier_le2) < 2:
                                violations.append({
                                    "field": "acquisition_audit.web_search_queries (TAM tier 优先级)",
                                    "value": f"TAM 查询 tier≤2 数 = {len(tier_le2)}",
                                    "issue": "TAM 类查询 ≥2 项必走 Tier 1/2 权威源 (skill §3 锁源优先级, 防全走 Tier 3 估算)",
                                    "severity": "should",
                                })

    # ⑩ evidence 元数据强制 (iteration 4 GATE attempt#1 fatal F3 修复, skill 铁律 4 工程化)
    # verified status 的 evidence 项必有 as_of 或 claim 中含年份标注
    ev = p.get("evidence")
    if isinstance(ev, list):
        import re as _re
        YEAR_RE = _re.compile(r"20\d{2}")
        for i, entry in enumerate(ev):
            if not isinstance(entry, dict):
                continue
            if entry.get("_doc"):
                continue
            if entry.get("status") != "verified":
                continue
            claim_str = str(entry.get("claim", ""))
            has_as_of = bool(entry.get("as_of"))
            has_year = bool(YEAR_RE.search(claim_str))
            if not has_as_of and not has_year:
                violations.append({
                    "field": f"evidence[{i}]",
                    "value": claim_str[:60],
                    "issue": "verified evidence 项缺 as_of 字段且 claim 中无年份 (skill §1 铁律 4: 数字必含 as_of/年份/单位/口径)",
                    "severity": "should",
                })

    # ⑪ financial_analysis (iteration 5 落地, skill v4-financial-analysis §6 输出契约)
    fa = p.get("financial_analysis")
    if fa is not None:  # 字段存在则严查; stock-analyst-financial 产物或 stock unit 透传时触发
        if not isinstance(fa, dict):
            violations.append({
                "field": "financial_analysis",
                "value": str(type(fa)),
                "issue": "financial_analysis 应是 dict",
                "severity": "fatal",
            })
        else:
            # ② dupont_5y 三因子数组长度 = 5
            dupont = fa.get("dupont_5y") or {}
            if isinstance(dupont, dict):
                for f in ("net_margin", "asset_turnover", "equity_multiplier", "roe_5y"):
                    arr = dupont.get(f)
                    if not isinstance(arr, list) or len(arr) < 3:
                        violations.append({
                            "field": f"financial_analysis.dupont_5y.{f}",
                            "value": f"len={len(arr) if isinstance(arr, list) else 'n/a'}",
                            "issue": f"dupont_5y.{f} 数组长度 < 3 (skill §2 杜邦三因子序列, ≥5 年最佳 ≥3 年最低)",
                            "severity": "fatal" if not arr else "should",
                        })
            else:
                violations.append({
                    "field": "financial_analysis.dupont_5y",
                    "value": "missing or wrong type",
                    "issue": "dupont_5y 缺失或非 dict (skill §2 杜邦拆解必填)",
                    "severity": "fatal",
                })
            # ③ roic_vs_wacc.roic_range
            rw = fa.get("roic_vs_wacc") or {}
            if isinstance(rw, dict):
                rr = rw.get("roic_range")
                if not isinstance(rr, list) or len(rr) != 2:
                    violations.append({
                        "field": "financial_analysis.roic_vs_wacc.roic_range",
                        "value": str(rr)[:60],
                        "issue": "roic_range 应是 [low, high] 数字区间长度=2 (skill §2 ROIC 区间稳健性, 防伪精确点值)",
                        "severity": "fatal",
                    })
                elif not all(isinstance(x, (int, float)) for x in rr):
                    # iter 5 GATE attempt#1 fatal 修复: 类型校验
                    violations.append({
                        "field": "financial_analysis.roic_vs_wacc.roic_range",
                        "value": str(rr)[:60],
                        "issue": "roic_range 两端必须是数字 (int/float), 字符串等非数字 = fatal (防 LLM 绕过区间检查)",
                        "severity": "fatal",
                    })
                # iter 5 GATE attempt#1 fatal 1 修复: enum 检查布尔 bug
                VALID_VERDICTS = {"创造价值", "显著创造价值", "持平", "毁灭价值"}
                v = rw.get("verdict")
                if v is None or v == "":
                    violations.append({
                        "field": "financial_analysis.roic_vs_wacc.verdict",
                        "value": str(v)[:60],
                        "issue": "roic_vs_wacc.verdict 必填 (4 选 1: 创造价值/显著创造价值/持平/毁灭价值)",
                        "severity": "fatal",
                    })
                elif v not in VALID_VERDICTS:
                    violations.append({
                        "field": "financial_analysis.roic_vs_wacc.verdict",
                        "value": str(v)[:60],
                        "issue": f"verdict '{v}' 不在合法 enum {VALID_VERDICTS} (防 LLM 写'部分创造''边际持平'等模糊词, 反 Goodhart)",
                        "severity": "fatal",
                    })
            else:
                violations.append({
                    "field": "financial_analysis.roic_vs_wacc",
                    "value": "missing",
                    "issue": "roic_vs_wacc 缺失 (critic 6.9 价值创造四问 ②)",
                    "severity": "fatal",
                })

            # iter 5 GATE attempt#1 fatal 2 修复: verified_period 必查 (skill §1 铁律 1)
            vp = fa.get("verified_period")
            if not vp:
                violations.append({
                    "field": "financial_analysis.verified_period",
                    "value": "missing",
                    "issue": "verified_period 缺失 (skill §1 铁律 1: verified 数字 + as_of 报告期)",
                    "severity": "fatal",
                })
            elif isinstance(vp, str):
                import re as _re2
                if not _re2.search(r"20\d{2}", vp):
                    violations.append({
                        "field": "financial_analysis.verified_period",
                        "value": vp[:60],
                        "issue": "verified_period 不含 4 位年份, 无法验证 as_of (skill §1 铁律 1)",
                        "severity": "should",
                    })
            # ④ cashflow_quality.ocf_to_net_income_5y
            cf = fa.get("cashflow_quality") or {}
            if isinstance(cf, dict):
                ocf = cf.get("ocf_to_net_income_5y")
                if not isinstance(ocf, list) or len(ocf) < 3:
                    violations.append({
                        "field": "financial_analysis.cashflow_quality.ocf_to_net_income_5y",
                        "value": f"len={len(ocf) if isinstance(ocf, list) else 'n/a'}",
                        "issue": "ocf_to_net_income_5y 数组长度 < 3 (skill §3 现金流质量序列)",
                        "severity": "fatal" if not ocf else "should",
                    })
            else:
                violations.append({
                    "field": "financial_analysis.cashflow_quality",
                    "value": "missing",
                    "issue": "cashflow_quality 缺失 (skill §3 现金流 vs 净利润 必查)",
                    "severity": "fatal",
                })
            # ⑤ product_molecule_model.products 数组每项含必填字段
            pm = fa.get("product_molecule_model") or {}
            if isinstance(pm, dict):
                products = pm.get("products") or []
                if not isinstance(products, list) or len(products) == 0:
                    violations.append({
                        "field": "financial_analysis.product_molecule_model.products",
                        "value": "empty",
                        "issue": "products 数组空 (skill §1 铁律 2 + critic 6.1 产品分子模型必填)",
                        "severity": "fatal",
                    })
                for i, prod in enumerate(products):
                    if not isinstance(prod, dict):
                        continue
                    for f in ("revenue", "gross_margin_pct", "net_contribution"):
                        if f not in prod:
                            violations.append({
                                "field": f"financial_analysis.product_molecule_model.products[{i}].{f}",
                                "value": "missing",
                                "issue": f"产品分子项缺 {f} 字段",
                                "severity": "fatal",
                            })
            # ⑥ red_flags_check 5 类齐
            rf = fa.get("red_flags_check") or []
            if isinstance(rf, list):
                REQUIRED_FLAGS = {"应收激增", "现金流背离", "商誉减值", "关联交易", "大股东占款"}
                seen_flags = {item.get("type") for item in rf if isinstance(item, dict)}
                missing_flags = REQUIRED_FLAGS - seen_flags
                if missing_flags:
                    violations.append({
                        "field": "financial_analysis.red_flags_check",
                        "value": f"missing {missing_flags}",
                        "issue": f"red_flags_check 缺 {len(missing_flags)} 类: {missing_flags} (skill §4 5 类红旗清单, 必齐对照)",
                        "severity": "should",
                    })
            # ⑦ falsification_signals ≥1
            fs = fa.get("falsification_signals") or []
            if not isinstance(fs, list) or len(fs) < 1:
                violations.append({
                    "field": "financial_analysis.falsification_signals",
                    "value": f"len={len(fs) if isinstance(fs, list) else 'n/a'}",
                    "issue": "falsification_signals 数组 < 1 (skill §1 铁律 5 + 达里奥极度求真)",
                    "severity": "should",
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
