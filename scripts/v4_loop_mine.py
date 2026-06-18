#!/usr/bin/env python3
"""
v4_loop_mine.py — 自进化优化循环 DISCOVER 阶段的扫描器

协议: planning/v4/self-evolving-optimization-loop.md Part 7.1 铁律
"DISCOVER 必须真看产物，禁凭印象空想洞"

扫 4 类根因信号 (见对话纪要):
  1) 方法论缺失     — Part 2 标尺没被 cite 的频次
  2) prompt 没强制 — 字段填了但内容是套话/无量化/无证伪
  3) verified 漏洞 — 数字字段缺 verified_sources URL
  4) 主 agent 偷懒 — director 字段比下游 subagent 字段更浅

输出:
  data/v4/_loop/mine_report.json    - 全量统计
  data/v4/_loop/mine_report.md      - 人读摘要
  并把 top-3 候选洞写进 optimization_state.json 的 backlog (不重复)

用法: python3 scripts/v4_loop_mine.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
STOCKS_DIR = ROOT / "data" / "v4" / "stocks"
INDUSTRIES_DIR = ROOT / "data" / "v4" / "industries"
LOOP_DIR = ROOT / "data" / "v4" / "_loop"
STATE_FILE = LOOP_DIR / "optimization_state.json"
REPORT_JSON = LOOP_DIR / "mine_report.json"
REPORT_MD = LOOP_DIR / "mine_report.md"

# Part 2 标尺关键词 (用于检测 verdict/summary 中是否显式 cite)
RULER_KEYWORDS = {
    "巴菲特-能力圈": ["能力圈", "circle of competence", "看不懂"],
    "巴菲特-护城河量化": ["护城河量化", "wide moat", "narrow moat", "moat trend", "护城河趋势"],
    "巴菲特-安全边际": ["安全边际", "margin of safety", "内在价值"],
    "巴菲特-逆向思考": ["死亡清单", "invert", "怎么会亏", "怎么死", "反向自问", "亏光本金", "死亡路径", "pre-mortem narrative"],
    "巴菲特-FCF/股东盈余": ["owner earnings", "股东盈余", "维持性capex", "FCF剔除"],
    "段永平-商业模式": ["商业模式", "好生意", "复购", "定价权"],
    "段永平-stop-doing": ["stop doing", "不做清单", "不碰"],
    "段永平-管理层": ["资本配置", "管理层质量", "回购质量"],
    "马克斯-二阶思维": ["二阶思维", "预期差", "price-in", "已 price-in", "市场共识"],
    "马克斯-周期定位": ["周期定位", "S曲线", "渗透率阶段", "估值分位"],
    "马克斯-永久损失": ["永久损失", "permanent loss", "本金"],
    "马克斯-紫苏叶": ["紫苏叶", "无人知晓", "上溯产业链", "碎片演绎"],
    "达里奥-可证伪": ["可证伪", "看到X就证明", "反向信号", "证伪信号"],
    "达里奥-what-am-i-missing": ["What am I missing", "盲区清单", "反面证据"],
    "达里奥-真分散": ["真分散", "驱动因子", "相关性"],
    "费雪-scuttlebutt": ["闲聊法", "scuttlebutt", "客户名单", "产能地图"],
    "费雪-错杀龙头": ["错杀", "卡位龙头", "中际旭创"],
    # 新增 IPS / 死亡清单 / SOP
    "IPS-集中度上限": ["集中度上限", "单股≤", "top10≤"],
    "IPS-流动性": ["days-to-liquidate", "流动性约束", "ADV"],
    "IPS-卖出明文化": ["卖出条件", "sell trigger", "exit plan", "止损价"],
    "IPS-多PM委员会": ["双签", "多PM", "investment committee"],
    "死亡-LTCM相关性": ["相关性崩溃", "LTCM", "压力测试相关"],
    "死亡-Archegos集中": ["Archegos", "集中度+杠杆"],
    "死亡-Woodford流动性": ["Woodford", "流动性错配"],
    "死亡-现金流背离": ["OCF<净利", "现金流背离", "康美", "乐视"],
    "死亡-抱团": ["crowded trade", "拥挤度", "抱团"],
    "死亡-价值陷阱": ["价值陷阱", "value trap"],
    "SOP-晨星moat": ["晨星", "morningstar", "无形资产", "转换成本", "网络效应", "成本优势", "有效规模"],
    "SOP-催化时间表": ["催化剂时间", "catalyst calendar", "Q3 兑现", "时间窗"],
    "SOP-三情景估值": ["bull/base/bear", "三情景", "概率权重"],
    "SOP-下行情景": ["基本面双杀", "估值杀", "政策杀", "下行幅度"],
    "SOP-拥挤度": ["公募集中", "北向重叠", "卖空比例"],
    # 2026-06-17 iteration 3 落地: v4-debate-discipline skill cite 检测 (Part 7 #10 narrative 防 Goodhart)
    "辩论纪律-3铁律": ["点名反驳", "数据分子", "反向阈值", "可证伪信号"],
    "辩论纪律-bull派别": ["段永平好生意", "费雪 scuttlebutt", "scuttlebutt 闲聊", "紫苏叶切入", "错杀龙头切入"],
    "辩论纪律-bear派别": ["芒格逆向切入", "芒格 invert", "达里奥风险切入", "永久损失场景", "Archegos 同型", "Woodford 流动性", "LTCM 相关性"],
}

# 浅尝特征正则 (放之四海皆准的套话)
SHALLOW_PHRASES = [
    r"有(一定|较强|强大)?护城河",
    r"长期(看好|增长|向好)",
    r"宏观(风险|不确定)",
    r"政策(风险|不确定性)",
    r"行业前景(广阔|良好)",
    r"具备一定竞争优势",
    r"未来可期",
    r"有望(实现|达到|超过)",
]
SHALLOW_RE = re.compile("|".join(SHALLOW_PHRASES))

# verified 必填字段 (RULE-DATA-VERIFIED)
VERIFIED_REQUIRED = ["future_tam", "future_share", "forward_eps", "target_price", "tam_2030"]


def load_jsons(d: Path) -> list[tuple[Path, dict]]:
    if not d.exists():
        return []
    out = []
    for p in sorted(d.glob("*.json")):
        try:
            out.append((p, json.loads(p.read_text(encoding="utf-8"))))
        except Exception as e:
            print(f"[warn] skip {p}: {e}", file=sys.stderr)
    return out


def text_blob(obj: Any) -> str:
    """递归把 dict/list/str 拼成字符串，用于关键词扫描"""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, (int, float, bool, type(None))):
        return ""
    if isinstance(obj, dict):
        return " ".join(text_blob(v) for v in obj.values())
    if isinstance(obj, list):
        return " ".join(text_blob(v) for v in obj)
    return str(obj)


def scan_ruler_coverage(stocks: list[tuple[Path, dict]]) -> dict[str, int]:
    """根因 1: 标尺被 cite 频次"""
    cnt: Counter = Counter()
    for path, d in stocks:
        blob = text_blob(d.get("payload", {})).lower()
        for ruler, kws in RULER_KEYWORDS.items():
            if any(kw.lower() in blob for kw in kws):
                cnt[ruler] += 1
            else:
                cnt.setdefault(ruler, 0)
    return dict(cnt)


def scan_shallow_phrases(stocks: list[tuple[Path, dict]]) -> dict[str, list[str]]:
    """根因 2: 套话频次 — 哪些 stock 的 verdict.summary 命中了无量化套话"""
    hits: dict[str, list[str]] = defaultdict(list)
    for path, d in stocks:
        p = d.get("payload", {})
        verdict = p.get("verdict", {})
        if isinstance(verdict, dict):
            summary = verdict.get("summary", "") or ""
            for m in SHALLOW_RE.findall(summary):
                hits[path.stem].append(m if isinstance(m, str) else "|".join(m))
    return dict(hits)


def scan_verified_holes(stocks: list[tuple[Path, dict]]) -> dict[str, list[str]]:
    """根因 3: verified_sources 缺失 (RULE-DATA-VERIFIED 风险)"""
    hits: dict[str, list[str]] = defaultdict(list)
    for path, d in stocks:
        blob_text = json.dumps(d.get("payload", {}), ensure_ascii=False)
        for field in VERIFIED_REQUIRED:
            if field in blob_text and "verified_sources" not in blob_text:
                hits[path.stem].append(field)
    return dict(hits)


def scan_falsifiable_gap(stocks: list[tuple[Path, dict]]) -> dict[str, list[str]]:
    """根因 5: 缺卖出触发/反向信号 (达里奥-可证伪)"""
    missing: dict[str, list[str]] = defaultdict(list)
    for path, d in stocks:
        p = d.get("payload", {})
        ap = p.get("action_plan", {})
        if isinstance(ap, dict):
            has_sell = bool(ap.get("sell_trigger") or ap.get("exit_plan") or ap.get("trim_zones"))
            has_stop = bool(ap.get("stop_loss"))
            has_monitor = bool(ap.get("monitoring_signals"))
            if not has_sell:
                missing[path.stem].append("缺sell_trigger/exit_plan")
            if not has_stop:
                missing[path.stem].append("缺stop_loss")
            if not has_monitor:
                missing[path.stem].append("缺monitoring_signals")
    return dict(missing)


def scan_pre_mortem_field(stocks: list[tuple[Path, dict]]) -> dict:
    """active_hole 专项: pre_mortem 字段填实率 (skill §2.6 + critic 6.16)"""
    REQUIRED_SCENES = ["fundamental_double_kill", "valuation_kill", "policy_or_blackswan_kill"]
    RELATIVE_DEVIATION_RE = re.compile(r"(跌\s*\d+\s*%|下滑\s*\d+\s*%|低于历史|降\s*\d+\s*%|相对|偏离)")
    has_field = three_scenes_full = threshold_ok = sell_link_closed = analog_cited = 0
    verified_anchor_ok = absolute_threshold_only = 0
    detail: dict[str, dict] = {}
    for path, d in stocks:
        p = d.get("payload", {})
        pm = p.get("pre_mortem")
        if not isinstance(pm, dict) or not pm:
            detail[path.stem] = {"status": "missing"}
            continue
        has_field += 1
        scenes_present = [s for s in REQUIRED_SCENES if isinstance(pm.get(s), dict) and pm[s].get("scenario")]
        thr_per_scene, link_per_scene, analog_per_scene = [], [], []
        verified_per_scene, abs_threshold_per_scene = [], []
        for s in REQUIRED_SCENES:
            obj = pm.get(s) or {}
            if isinstance(obj, dict):
                tri = obj.get("trigger_indicators") or []
                thr_per_scene.append(len(tri) >= 3)
                link_per_scene.append(bool(obj.get("sell_trigger_link")))
                analog_per_scene.append(bool(obj.get("historical_analog")))
                # verified_anchor 检测
                va = obj.get("verified_anchor") or {}
                va_count = va.get("verified_source_count") if isinstance(va, dict) else None
                try:
                    va_n = int(str(va_count).strip("≥+ ")) if va_count else 0
                except (ValueError, TypeError):
                    va_n = 1 if va_count else 0
                has_va = isinstance(va, dict) and (va_n >= 1 or va.get("trigger_observed_values"))
                verified_per_scene.append(bool(has_va))
                # 绝对/相对阈值识别
                tri_blob = " ".join(str(t) for t in tri) if tri else ""
                has_relative = bool(RELATIVE_DEVIATION_RE.search(tri_blob))
                abs_threshold_per_scene.append(not has_relative and len(tri) >= 3)
        if len(scenes_present) == 3:
            three_scenes_full += 1
        if thr_per_scene and len(thr_per_scene) == 3 and all(thr_per_scene):
            threshold_ok += 1
        if link_per_scene and len(link_per_scene) == 3 and all(link_per_scene):
            sell_link_closed += 1
        if analog_per_scene and len(analog_per_scene) == 3 and all(analog_per_scene):
            analog_cited += 1
        if verified_per_scene and len(verified_per_scene) == 3 and all(verified_per_scene):
            verified_anchor_ok += 1
        if abs_threshold_per_scene and len(abs_threshold_per_scene) == 3 and all(abs_threshold_per_scene):
            absolute_threshold_only += 1
        detail[path.stem] = {
            "status": "ok" if (len(scenes_present) == 3 and thr_per_scene and all(thr_per_scene) and all(link_per_scene)) else "partial",
            "scenes_present": scenes_present,
        }
    n = max(len(stocks), 1)
    return {
        "total_stocks": len(stocks),
        "has_field_count": has_field,
        "has_field_pct": round(has_field / n * 100, 1),
        "three_scenes_full_count": three_scenes_full,
        "three_scenes_full_pct": round(three_scenes_full / n * 100, 1),
        "threshold_compliance_count": threshold_ok,
        "threshold_compliance_pct": round(threshold_ok / n * 100, 1),
        "sell_link_closed_count": sell_link_closed,
        "sell_link_closed_pct": round(sell_link_closed / n * 100, 1),
        "analog_cited_count": analog_cited,
        "analog_cited_pct": round(analog_cited / n * 100, 1),
        "verified_anchor_count": verified_anchor_ok,
        "verified_anchor_pct": round(verified_anchor_ok / n * 100, 1),
        "absolute_threshold_only_count": absolute_threshold_only,
        "absolute_threshold_only_pct": round(absolute_threshold_only / n * 100, 1),
        "detail_sample": dict(list(detail.items())[:5]),
    }


def scan_debate_discipline(stocks: list[tuple[Path, dict]]) -> dict:
    """active_hole iteration 3 专项: 辩手 skill 引用 + 产物 methodology_used 应用率
    (skill v4-debate-discipline + critic 6.6 升级)"""
    # ① agent 层 (静态): 扫 9 个 bull/bear/risk agent .md 是否含 skill cite + 必读 skill 段
    DEBATE_AGENTS = [
        "v4-asset-bull.md", "v4-asset-bear.md",
        "v4-industry-bull.md", "v4-industry-bear.md",
        "v4-stock-bull.md", "v4-stock-bear.md",
        "v4-stock-risk-aggressive.md", "v4-stock-risk-safe.md", "v4-stock-risk-neutral.md",
    ]
    agents_dir = ROOT / "agents" / "advisor"
    agent_skill_cite = 0
    agent_must_read = 0
    agent_details: dict[str, dict] = {}
    for fname in DEBATE_AGENTS:
        p = agents_dir / fname
        if not p.exists():
            agent_details[fname] = {"status": "missing"}
            continue
        text = p.read_text(encoding="utf-8")
        has_cite = "v4-debate-discipline" in text
        has_must_read = "## 必读 skill" in text
        if has_cite:
            agent_skill_cite += 1
        if has_must_read:
            agent_must_read += 1
        agent_details[fname] = {"skill_cite": has_cite, "must_read_section": has_must_read}
    n_agents = max(len(DEBATE_AGENTS), 1)

    # ② 产物层 (动态): 扫 stock debate_rounds 是否含 methodology_used + 派别切入 narrative
    PARTY_KEYWORDS = [
        "段永平好生意", "费雪 scuttlebutt", "scuttlebutt 闲聊", "紫苏叶切入", "错杀龙头切入",
        "芒格逆向切入", "芒格 invert", "达里奥风险切入", "永久损失场景",
        "Archegos 同型", "Woodford 流动性", "LTCM 相关性",
    ]
    debate_total = 0
    debate_methodology_used = 0
    debate_party_cite = 0
    for path, d in stocks:
        p = d.get("payload", {})
        rounds = p.get("debate_rounds")
        if not rounds:
            continue
        debate_total += 1
        rounds_blob = json.dumps(rounds, ensure_ascii=False)
        if "methodology_used" in rounds_blob:
            debate_methodology_used += 1
        if any(kw in rounds_blob for kw in PARTY_KEYWORDS):
            debate_party_cite += 1
    n_stocks_with_debate = max(debate_total, 1)

    return {
        "agent_count": len(DEBATE_AGENTS),
        "agent_skill_cite_count": agent_skill_cite,
        "agent_skill_cite_pct": round(agent_skill_cite / n_agents * 100, 1),
        "agent_must_read_count": agent_must_read,
        "agent_must_read_pct": round(agent_must_read / n_agents * 100, 1),
        "agent_details": agent_details,
        "stocks_with_debate_rounds": debate_total,
        "debate_methodology_used_count": debate_methodology_used,
        "debate_methodology_used_pct": round(debate_methodology_used / n_stocks_with_debate * 100, 1) if debate_total else 0.0,
        "debate_party_cite_count": debate_party_cite,
        "debate_party_cite_pct": round(debate_party_cite / n_stocks_with_debate * 100, 1) if debate_total else 0.0,
    }


def scan_data_acquisition(stocks: list[tuple[Path, dict]]) -> dict:
    """active_hole iteration 4 专项: 数据采集 SOP 静态+产物层应用率 (5 层防御纵深第 5 层 mine 监控)
    skill v4-data-acquisition + verify_audit ⑨"""
    # ① agent 层 (静态): 扫 v4-data-desk.md
    p_desk = ROOT / "agents" / "advisor" / "v4-data-desk.md"
    desk_skill_cite = desk_must_read = desk_schema_field = False
    if p_desk.exists():
        text = p_desk.read_text(encoding="utf-8")
        desk_skill_cite = "v4-data-acquisition" in text
        desk_must_read = "## 必读 skill" in text
        desk_schema_field = '"acquisition_audit"' in text  # schema 块内显式字段

    # ② 产物层 (动态): 扫 stock+industry JSON 是否含 acquisition_audit
    industries_dir = ROOT / "data" / "v4" / "industries"
    inputs_dir = ROOT / "data" / "v4" / "inputs"
    all_units: list[tuple[Path, dict]] = list(stocks)
    for d in (industries_dir, inputs_dir):
        if d.exists():
            for p in sorted(d.glob("*.json")):
                try:
                    all_units.append((p, json.loads(p.read_text(encoding="utf-8"))))
                except Exception:
                    pass

    n_total = len(all_units)
    n_with_field = n_5keys_full = n_no_placeholder = n_tam_pass = 0
    placeholder_hits: list[str] = []
    tier3_only_hits: list[str] = []

    for path, d in all_units:
        # acquisition_audit 可在 payload 或顶层 (data-desk 输出在顶层, stock unit envelope 在 payload)
        acq = (d.get("payload") or {}).get("acquisition_audit") or d.get("acquisition_audit")
        if not isinstance(acq, dict) or not acq:
            continue
        n_with_field += 1
        REQUIRED = ["akshare_calls", "web_search_queries", "downgrade_chain", "missing_fields", "tam_3source_check"]
        if all(k in acq for k in REQUIRED):
            n_5keys_full += 1
        # akshare_calls 反 Goodhart
        ak_calls = acq.get("akshare_calls") or []
        has_placeholder = False
        if isinstance(ak_calls, list):
            for call in ak_calls:
                if isinstance(call, str) and call.strip().lower() in ("verified", "akshare", "akshare verified"):
                    has_placeholder = True
                    placeholder_hits.append(path.stem)
                    break
                if isinstance(call, str) and "(" not in call and ")" not in call and "_doc" not in call.lower():
                    has_placeholder = True
                    placeholder_hits.append(path.stem)
                    break
        if not has_placeholder:
            n_no_placeholder += 1
        # tam_3source_check ≥3 + 多机构去重(P1 强化)
        tc = acq.get("tam_3source_check") or {}
        if isinstance(tc, dict):
            n_src = tc.get("sources_count", 0)
            try:
                n_src = int(n_src)
            except (ValueError, TypeError):
                n_src = 0
            sources = tc.get("sources") or []
            distinct_sources = len({str(s).split()[0] for s in sources}) if isinstance(sources, list) else 0
            # 没 TAM 字段时 sources_count 可为 0, 视为 pass
            field_name = str(tc.get("field", ""))
            if "n/a" in field_name.lower() or n_src == 0:
                n_tam_pass += 1
            elif n_src >= 3 and distinct_sources >= 3:
                n_tam_pass += 1
        # tier=3 only 检测
        wsq = acq.get("web_search_queries") or []
        if isinstance(wsq, list) and wsq:
            tiers = [q.get("tier") for q in wsq if isinstance(q, dict) and q.get("tier") is not None]
            if tiers and all(t == 3 for t in tiers):
                tier3_only_hits.append(path.stem)

    n = max(n_total, 1)
    n_field = max(n_with_field, 1)
    return {
        "agent_layer": {
            "data_desk_skill_cite": desk_skill_cite,
            "data_desk_must_read_section": desk_must_read,
            "data_desk_schema_field": desk_schema_field,  # F1 修复后应为 True
        },
        "total_units_scanned": n_total,
        "units_with_acquisition_audit": n_with_field,
        "units_with_acquisition_audit_pct": round(n_with_field / n * 100, 1),
        "five_keys_full_count": n_5keys_full,
        "five_keys_full_pct": round(n_5keys_full / n_field * 100, 1) if n_with_field else 0.0,
        "no_placeholder_count": n_no_placeholder,
        "no_placeholder_pct": round(n_no_placeholder / n_field * 100, 1) if n_with_field else 0.0,
        "tam_3source_pass_count": n_tam_pass,
        "tam_3source_pass_pct": round(n_tam_pass / n_field * 100, 1) if n_with_field else 0.0,
        "placeholder_hits_sample": placeholder_hits[:5],
        "tier3_only_hits_sample": tier3_only_hits[:5],
    }


def scan_financial_analysis(stocks: list[tuple[Path, dict]]) -> dict:
    """active_hole iteration 5 专项: financial-analysis 静态+产物层应用率 (5 层防御纵深第 5 层 mine 监控)
    skill v4-financial-analysis + verify_audit ⑪"""
    # ① agent 层: 扫 4 stock-analyst
    AGENTS = ["v4-stock-analyst-financial.md", "v4-stock-analyst-competitive.md", "v4-stock-analyst-valuation.md", "v4-stock-analyst-sentiment.md"]
    agents_dir = ROOT / "agents" / "advisor"
    agent_skill_cite = agent_must_read = 0
    for fname in AGENTS:
        p = agents_dir / fname
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        if "v4-financial-analysis" in text:
            agent_skill_cite += 1
        if "## 必读 skill" in text:
            agent_must_read += 1
    n_agents = max(len(AGENTS), 1)

    # ② 产物层: 扫 stocks 是否含 financial_analysis 字段
    n_with_field = n_dupont_full = n_roic_range = n_cashflow_full = n_products_full = n_red_flags_5 = n_falsify = 0
    for path, d in stocks:
        p = d.get("payload", {})
        fa = p.get("financial_analysis")
        if not isinstance(fa, dict) or not fa:
            continue
        n_with_field += 1
        # dupont_5y 三因子 ≥3
        dupont = fa.get("dupont_5y") or {}
        if isinstance(dupont, dict):
            if all(isinstance(dupont.get(k), list) and len(dupont.get(k, [])) >= 3 for k in ("net_margin", "asset_turnover", "equity_multiplier", "roe_5y")):
                n_dupont_full += 1
        # roic_range
        rw = fa.get("roic_vs_wacc") or {}
        if isinstance(rw, dict) and isinstance(rw.get("roic_range"), list) and len(rw.get("roic_range", [])) == 2:
            n_roic_range += 1
        # cashflow_quality 序列 ≥3
        cf = fa.get("cashflow_quality") or {}
        if isinstance(cf, dict) and isinstance(cf.get("ocf_to_net_income_5y"), list) and len(cf.get("ocf_to_net_income_5y", [])) >= 3:
            n_cashflow_full += 1
        # product_molecule_model.products 每项三字段
        pm = fa.get("product_molecule_model") or {}
        if isinstance(pm, dict):
            products = pm.get("products") or []
            if isinstance(products, list) and products and all(
                isinstance(prod, dict) and all(k in prod for k in ("revenue", "gross_margin_pct", "net_contribution"))
                for prod in products
            ):
                n_products_full += 1
        # red_flags 5 类
        rf = fa.get("red_flags_check") or []
        if isinstance(rf, list) and len({item.get("type") for item in rf if isinstance(item, dict)}) >= 5:
            n_red_flags_5 += 1
        # falsification_signals ≥1
        fs = fa.get("falsification_signals") or []
        if isinstance(fs, list) and len(fs) >= 1:
            n_falsify += 1
    n = max(len(stocks), 1)
    n_field = max(n_with_field, 1)
    return {
        "agent_count": len(AGENTS),
        "agent_skill_cite_count": agent_skill_cite,
        "agent_skill_cite_pct": round(agent_skill_cite / n_agents * 100, 1),
        "agent_must_read_count": agent_must_read,
        "agent_must_read_pct": round(agent_must_read / n_agents * 100, 1),
        "stocks_with_financial_analysis": n_with_field,
        "stocks_with_financial_analysis_pct": round(n_with_field / n * 100, 1),
        "dupont_full_pct": round(n_dupont_full / n_field * 100, 1) if n_with_field else 0.0,
        "roic_range_pct": round(n_roic_range / n_field * 100, 1) if n_with_field else 0.0,
        "cashflow_full_pct": round(n_cashflow_full / n_field * 100, 1) if n_with_field else 0.0,
        "products_full_pct": round(n_products_full / n_field * 100, 1) if n_with_field else 0.0,
        "red_flags_5_pct": round(n_red_flags_5 / n_field * 100, 1) if n_with_field else 0.0,
        "falsify_pct": round(n_falsify / n_field * 100, 1) if n_with_field else 0.0,
    }


def scan_five_forces(stocks: list[tuple[Path, dict]]) -> dict:
    """active_hole iter 6 专项: 五力分析静态+产物层 (5 层防御纵深第 5 层 mine 监控)
    skill v4-five-forces-method + verify_audit ⑫"""
    AGENTS = ["v4-stock-force-entry.md", "v4-stock-force-substitute.md", "v4-stock-force-buyer.md", "v4-stock-force-supplier.md", "v4-stock-force-rivalry.md", "v4-stock-analyst-competitive.md"]
    agents_dir = ROOT / "agents" / "advisor"
    agent_skill_cite = 0
    for fname in AGENTS:
        p = agents_dir / fname
        if not p.exists():
            continue
        if "v4-five-forces-method" in p.read_text(encoding="utf-8"):
            agent_skill_cite += 1

    # 产物层: 扫 stock five_forces 字段 (现有结构, 检查 moat_rating enum) + five_forces_synthesis
    n_with_ff = n_moat_enum_pass = n_synthesis_full = 0
    VALID_MOAT = {"wide", "narrow", "none", "中", "中上", "中下", "宽", "窄"}  # 兼容现有"中/中上/中下/宽/窄" 中文
    for path, d in stocks:
        p = d.get("payload", {})
        ff = p.get("five_forces")
        if isinstance(ff, dict) and ff:
            n_with_ff += 1
            mr = ff.get("moat_rating")
            if mr and (mr in VALID_MOAT or any(z in str(mr) for z in ["wide", "narrow", "none", "宽", "中", "窄"])):
                n_moat_enum_pass += 1
        ffs = p.get("five_forces_synthesis")
        if isinstance(ffs, dict) and ffs:
            five_levels = ffs.get("five_levels") or {}
            if isinstance(five_levels, dict) and len(five_levels) >= 5:
                n_synthesis_full += 1
    n = max(len(stocks), 1)
    n_ag = max(len(AGENTS), 1)
    return {
        "agent_count": len(AGENTS),
        "agent_skill_cite_count": agent_skill_cite,
        "agent_skill_cite_pct": round(agent_skill_cite / n_ag * 100, 1),
        "stocks_with_five_forces": n_with_ff,
        "stocks_with_five_forces_pct": round(n_with_ff / n * 100, 1),
        "moat_enum_pass_count": n_moat_enum_pass,
        "moat_enum_pass_pct": round(n_moat_enum_pass / n * 100, 1) if n_with_ff else 0.0,
        "stocks_with_synthesis": n_synthesis_full,
        "stocks_with_synthesis_pct": round(n_synthesis_full / n * 100, 1),
    }


def scan_director_vs_subagent_depth(stocks: list[tuple[Path, dict]]) -> dict[str, dict]:
    """根因 4: director verdict 字符长度 vs five_forces/forward_view 字符长度
    director 显著浅 = 主 agent 偷懒 (粗略代理指标)"""
    out: dict[str, dict] = {}
    for path, d in stocks:
        p = d.get("payload", {})
        verdict_len = len(text_blob(p.get("verdict", {})))
        ff_len = len(text_blob(p.get("five_forces", {})))
        fv_len = len(text_blob(p.get("forward_view_6dim", {})))
        downstream = max(ff_len, fv_len)
        if downstream > 0 and verdict_len < downstream * 0.4:
            out[path.stem] = {
                "verdict_len": verdict_len,
                "max_downstream_len": downstream,
                "ratio": round(verdict_len / max(downstream, 1), 2),
            }
    return out


def build_candidate_holes(report: dict) -> list[dict]:
    """根据扫描结果产出候选洞 (按伤害排序)"""
    holes: list[dict] = []

    # 标尺覆盖率 0 的标尺 = 候选洞
    coverage = report["ruler_coverage"]
    total = report["stock_count"]
    never_cited = sorted(
        [(r, c) for r, c in coverage.items() if c == 0],
        key=lambda x: x[0],
    )
    if never_cited:
        rulers = [r for r, _ in never_cited[:5]]
        holes.append({
            "id_prefix": "RULER",
            "title": f"标尺库 {len(never_cited)} 条从没被 cite (top: {', '.join(rulers[:3])}...)",
            "violated_practice": "Part 2 标尺库覆盖率",
            "evidence": [f"扫描 {total} 只 stock，{len(never_cited)} 条标尺零 cite"],
            "harm_to_profit": "嘴上有(skill 文档列了) / 流程无(产物零引用)，浅尝即止系统性",
            "shallow_score": 5,
            "priority": "must",
        })

    # 卖出触发缺失率
    fal = report["falsifiable_gap"]
    sell_missing = sum(1 for v in fal.values() if any("sell_trigger" in x for x in v))
    if sell_missing >= total * 0.5:
        holes.append({
            "id_prefix": "SELL",
            "title": f"{sell_missing}/{total} 只 stock 缺 sell_trigger/exit_plan",
            "violated_practice": "IPS-卖出明文化 + 达里奥-可证伪",
            "evidence": [f"扫描 {total} 只 stock，{sell_missing} 只 action_plan 没卖出条件"],
            "harm_to_profit": "用户买进去不知道何时卖，论点失效也没机制提醒",
            "shallow_score": 5,
            "priority": "must",
        })

    # verified 漏洞
    ver = report["verified_holes"]
    if ver:
        holes.append({
            "id_prefix": "VERIFIED",
            "title": f"{len(ver)} 只 stock 有 future_tam/target 等数字但缺 verified_sources",
            "violated_practice": "RULE-DATA-VERIFIED 永久红线",
            "evidence": [f"top: {list(ver.keys())[:3]}"],
            "harm_to_profit": "通富 $157B 事故同类风险 — 拍脑袋数字误导用户加仓",
            "shallow_score": 4,
            "priority": "must",
        })

    # 套话命中
    shal = report["shallow_phrases"]
    if shal:
        total_hits = sum(len(v) for v in shal.values())
        holes.append({
            "id_prefix": "SHALLOW",
            "title": f"{len(shal)}/{total} 只 stock verdict 命中无量化套话 (共 {total_hits} 处)",
            "violated_practice": "深度闸门 §1 浅尝特征 #2 套话填字段",
            "evidence": [f"sample: {list(shal.keys())[:3]}"],
            "harm_to_profit": "字段填满但放之四海皆准，换个股也成立 → 假深度",
            "shallow_score": 3,
            "priority": "should",
        })

    # director 偷懒
    lazy = report["director_lazy"]
    if lazy:
        holes.append({
            "id_prefix": "LAZY",
            "title": f"{len(lazy)} 只 stock director verdict 长度 <40% downstream",
            "violated_practice": "MECE 反偷懒铁律 + 段永平-把事做对",
            "evidence": [f"sample: {list(lazy.keys())[:3]}"],
            "harm_to_profit": "下游分析做了但 director 没整合，相当于白做",
            "shallow_score": 3,
            "priority": "should",
        })

    # 辩论纪律 cleanup (iteration 3 GATE attempt#1 fatal F2 修复落地)
    dd = report.get("debate_discipline", {}) or {}
    if dd.get("stocks_with_debate_rounds", 0) > 0 and dd.get("debate_methodology_used_pct", 0) < 50:
        n_with_debate = dd.get("stocks_with_debate_rounds", 0)
        n_used = dd.get("debate_methodology_used_count", 0)
        holes.append({
            "id_prefix": "DEBATE-CLEANUP",
            "title": f"{n_with_debate - n_used} 只含 debate_rounds 的旧 stock 缺 methodology_used (iteration 3 静态层 100% / 产物层 {dd.get('debate_methodology_used_pct', 0)}% 落差)",
            "violated_practice": "iteration 2 fatal#3 同型 (存量 cleanup 缺位) + 协议 Part 7 #10 narrative cite 防 Goodhart",
            "evidence": [f"含 debate_rounds: {n_with_debate}, methodology_used 应用率仅 {dd.get('debate_methodology_used_pct', 0)}%, 派别切入 {dd.get('debate_party_cite_pct', 0)}%"],
            "harm_to_profit": "新 stock 走 director→write→audit 自动堵, 旧 stock 永远 0% — 自进化循环被自动验证为伪进化(达里奥风险=永久损失信任)",
            "shallow_score": 4,
            "priority": "must",
        })

    # 数据采集 cleanup (iteration 4 P1 残留补 + iter 5 同型范式)
    da = report.get("data_acquisition", {}) or {}
    if da.get("total_units_scanned", 0) > 0 and da.get("units_with_acquisition_audit_pct", 0) < 50:
        holes.append({
            "id_prefix": "DATA-ACQ-CLEANUP",
            "title": f"{da.get('total_units_scanned', 0) - da.get('units_with_acquisition_audit', 0)} 个单元缺 acquisition_audit (iter 4 静态 100% / 产物 {da.get('units_with_acquisition_audit_pct', 0)}% 落差)",
            "violated_practice": "iter 2/3 cleanup 同型 + 协议 Part 7 #10",
            "evidence": [f"total {da.get('total_units_scanned', 0)} units, only {da.get('units_with_acquisition_audit', 0)} 含 acquisition_audit ({da.get('units_with_acquisition_audit_pct', 0)}%)"],
            "harm_to_profit": "data-desk 写盘 hook 已落 (verify_audit ⑨), 但旧产物无字段永远 0%, 通富 $157B 同型隐患存量",
            "shallow_score": 4,
            "priority": "must",
        })

    # 财务分析 cleanup (iter 5 落地, 配套范式)
    fa_d = report.get("financial_analysis", {}) or {}
    if fa_d.get("stocks_with_financial_analysis_pct", 0) < 50:
        holes.append({
            "id_prefix": "FINANCIAL-CLEANUP",
            "title": f"{49 - fa_d.get('stocks_with_financial_analysis', 0)} 只 stock 缺 financial_analysis (iter 5 静态 {fa_d.get('agent_skill_cite_pct', 0)}% / 产物 {fa_d.get('stocks_with_financial_analysis_pct', 0)}% 落差)",
            "violated_practice": "iter 2/3/4 cleanup 同型 + skill v4-financial-analysis §6 输出契约",
            "evidence": [f"49 stocks 中仅 {fa_d.get('stocks_with_financial_analysis', 0)} 含 financial_analysis ({fa_d.get('stocks_with_financial_analysis_pct', 0)}%)"],
            "harm_to_profit": "iter 5 schema+code+monitor 全齐, 但旧产物无 financial_analysis 字段永远 0% — '产品 mix 改善'空话浅尝复发",
            "shallow_score": 4,
            "priority": "must",
        })

    # 五力 cleanup (iter 6 落地, 配套范式)
    ff_d = report.get("five_forces", {}) or {}
    if ff_d.get("stocks_with_synthesis_pct", 0) < 50:
        holes.append({
            "id_prefix": "FIVE-FORCES-CLEANUP",
            "title": f"{49 - ff_d.get('stocks_with_synthesis', 0)} 只 stock 缺 five_forces_synthesis 5 力交叉编织 (iter 6 静态 {ff_d.get('agent_skill_cite_pct', 0)}% / 产物 synthesis {ff_d.get('stocks_with_synthesis_pct', 0)}% 落差)",
            "violated_practice": "iter 2-5 cleanup 同型 + skill v4-five-forces-method §5 输出契约",
            "evidence": [f"含 synthesis 仅 {ff_d.get('stocks_with_synthesis', 0)} ({ff_d.get('stocks_with_synthesis_pct', 0)}%); 含 five_forces 不含 synthesis = 5 段平铺扣分"],
            "harm_to_profit": "5 力专项已落地但 competitive 整合者交叉编织缺位, A/B 测试已证 5 段平铺扣分",
            "shallow_score": 4,
            "priority": "must",
        })

    return holes


def write_state_backlog(holes: list[dict]) -> int:
    """把候选洞 append 到 state.backlog，按 id_prefix (RULER/SELL/VERIFIED/LAZY 等) 去重 (iteration 2 修复)"""
    if not STATE_FILE.exists():
        return 0
    state = json.loads(STATE_FILE.read_text(encoding="utf-8"))

    def extract_prefix(hole_id: str) -> str:
        return hole_id.split("-")[0] if hole_id else ""

    existing_prefixes: set[str] = set()
    for h in state.get("backlog", []):
        existing_prefixes.add(extract_prefix(h.get("id", "")))
    for h in state.get("done", []):
        existing_prefixes.add(extract_prefix(h.get("id", "")))
    if state.get("active_hole"):
        existing_prefixes.add(extract_prefix(state["active_hole"].get("id", "")))

    appended = 0
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for i, h in enumerate(holes, 1):
        if h["id_prefix"] in existing_prefixes:
            continue
        hole_id = f"{h['id_prefix']}-{datetime.now().strftime('%Y%m%d')}-{i:02d}"
        state.setdefault("backlog", []).append({
            "id": hole_id,
            "title": h["title"],
            "violated_practice": h["violated_practice"],
            "shallow_score": h["shallow_score"],
            "harm_to_profit": h["harm_to_profit"],
            "priority": h["priority"],
            "discovered_at": now,
            "evidence": h["evidence"],
            "source": "v4_loop_mine.py",
        })
        appended += 1
        existing_prefixes.add(h["id_prefix"])

    state.setdefault("loop_meta", {})["last_mine"] = now
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return appended


def render_md(report: dict, holes: list[dict]) -> str:
    lines = [
        "# v4 自进化循环 — DISCOVER 扫描报告",
        f"\n生成时间: {report['generated_at']}",
        f"扫描 stock: **{report['stock_count']}** 只 / industry: **{report['industry_count']}** 个",
        "",
        "## 根因 1 — 标尺覆盖率",
    ]
    cov = sorted(report["ruler_coverage"].items(), key=lambda x: x[1])
    for r, c in cov:
        bar = "█" * min(c, 20)
        lines.append(f"- `{r}` — {c} / {report['stock_count']}  {bar}")
    lines.append("")
    lines.append("## 根因 2 — 浅尝套话命中")
    lines.append(f"命中 stock: **{len(report['shallow_phrases'])}** 只")
    for k, v in list(report["shallow_phrases"].items())[:10]:
        lines.append(f"- `{k}`: {v}")
    lines.append("")
    lines.append("## 根因 3 — verified_sources 漏洞")
    for k, v in list(report["verified_holes"].items())[:10]:
        lines.append(f"- `{k}`: {v}")
    lines.append("")
    lines.append("## 根因 4 — director 偷懒 (verdict <40% downstream)")
    for k, v in list(report["director_lazy"].items())[:10]:
        lines.append(f"- `{k}`: ratio={v['ratio']} verdict={v['verdict_len']} downstream={v['max_downstream_len']}")
    lines.append("")
    lines.append("## 根因 5 — 卖出触发/可证伪缺失")
    fal = report["falsifiable_gap"]
    sell_missing = sum(1 for v in fal.values() if any("sell_trigger" in x for x in v))
    stop_missing = sum(1 for v in fal.values() if any("stop_loss" in x for x in v))
    monitor_missing = sum(1 for v in fal.values() if any("monitoring_signals" in x for x in v))
    lines.append(f"- 缺 sell_trigger: {sell_missing} / {report['stock_count']}")
    lines.append(f"- 缺 stop_loss:    {stop_missing} / {report['stock_count']}")
    lines.append(f"- 缺 monitoring:   {monitor_missing} / {report['stock_count']}")
    lines.append("")
    pm = report.get("pre_mortem_field", {})
    if pm:
        lines.append("## active_hole 进度 — pre_mortem 三场景填实率 (iteration 1)")
        lines.append(f"- 字段存在:           **{pm.get('has_field_count', 0)} / {pm.get('total_stocks', 0)}** ({pm.get('has_field_pct', 0)}%)")
        lines.append(f"- 三场景齐全:         **{pm.get('three_scenes_full_count', 0)} / {pm.get('total_stocks', 0)}** ({pm.get('three_scenes_full_pct', 0)}%)")
        lines.append(f"- 阈值合规(≥3绝对):   **{pm.get('threshold_compliance_count', 0)} / {pm.get('total_stocks', 0)}** ({pm.get('threshold_compliance_pct', 0)}%)")
        lines.append(f"- sell_trigger 闭环:  **{pm.get('sell_link_closed_count', 0)} / {pm.get('total_stocks', 0)}** ({pm.get('sell_link_closed_pct', 0)}%)")
        lines.append(f"- 历史类比引用:       **{pm.get('analog_cited_count', 0)} / {pm.get('total_stocks', 0)}** ({pm.get('analog_cited_pct', 0)}%)")
        lines.append("")
    dd = report.get("debate_discipline", {})
    if dd:
        lines.append("## active_hole 进度 — 辩论纪律 (iteration 3 落地)")
        lines.append(f"- agent skill cite:   **{dd.get('agent_skill_cite_count', 0)} / {dd.get('agent_count', 0)}** ({dd.get('agent_skill_cite_pct', 0)}%)")
        lines.append(f"- agent 必读 skill 段: **{dd.get('agent_must_read_count', 0)} / {dd.get('agent_count', 0)}** ({dd.get('agent_must_read_pct', 0)}%)")
        lines.append(f"- 含 debate_rounds 的 stock: **{dd.get('stocks_with_debate_rounds', 0)}**")
        lines.append(f"- methodology_used 应用率:   **{dd.get('debate_methodology_used_pct', 0)}%** ({dd.get('debate_methodology_used_count', 0)})")
        lines.append(f"- 派别切入引用率:           **{dd.get('debate_party_cite_pct', 0)}%** ({dd.get('debate_party_cite_count', 0)})")
        lines.append("")
    da = report.get("data_acquisition", {})
    if da:
        al = da.get("agent_layer", {})
        lines.append("## active_hole 进度 — 数据采集 SOP (iteration 4 落地, 5 层防御纵深第 5 层 mine 监控)")
        lines.append(f"- v4-data-desk skill cite:    {'✓' if al.get('data_desk_skill_cite') else '✗'}")
        lines.append(f"- v4-data-desk 必读 skill 段:  {'✓' if al.get('data_desk_must_read_section') else '✗'}")
        lines.append(f"- v4-data-desk schema 字段:   {'✓' if al.get('data_desk_schema_field') else '✗'} (F1 修复关键)")
        lines.append(f"- 扫描单元数: {da.get('total_units_scanned', 0)}")
        lines.append(f"- 含 acquisition_audit 字段: **{da.get('units_with_acquisition_audit', 0)}** ({da.get('units_with_acquisition_audit_pct', 0)}%)")
        lines.append(f"- 5 子键齐: {da.get('five_keys_full_count', 0)} ({da.get('five_keys_full_pct', 0)}%)")
        lines.append(f"- 无 Goodhart 占位: {da.get('no_placeholder_count', 0)} ({da.get('no_placeholder_pct', 0)}%)")
        lines.append(f"- TAM 多源 ≥3 + 多机构 pass: {da.get('tam_3source_pass_count', 0)} ({da.get('tam_3source_pass_pct', 0)}%)")
        if da.get("placeholder_hits_sample"):
            lines.append(f"- ⚠️ Goodhart 占位样本: {da['placeholder_hits_sample']}")
        if da.get("tier3_only_hits_sample"):
            lines.append(f"- ⚠️ 全 Tier 3 取数样本: {da['tier3_only_hits_sample']}")
        lines.append("")
    fa_data = report.get("financial_analysis", {})
    if fa_data:
        lines.append("## active_hole 进度 — 财务分析 SOP (iteration 5 落地, 5 层防御纵深第 5 层)")
        lines.append(f"- agent skill cite (4 stock-analyst): **{fa_data.get('agent_skill_cite_count', 0)} / {fa_data.get('agent_count', 0)}** ({fa_data.get('agent_skill_cite_pct', 0)}%)")
        lines.append(f"- agent 必读段:                      **{fa_data.get('agent_must_read_count', 0)} / {fa_data.get('agent_count', 0)}** ({fa_data.get('agent_must_read_pct', 0)}%)")
        lines.append(f"- stocks 含 financial_analysis:      **{fa_data.get('stocks_with_financial_analysis', 0)}** ({fa_data.get('stocks_with_financial_analysis_pct', 0)}%)")
        lines.append(f"- dupont_5y 三因子完整:              **{fa_data.get('dupont_full_pct', 0)}%**")
        lines.append(f"- roic_range 区间形式:               **{fa_data.get('roic_range_pct', 0)}%**")
        lines.append(f"- cashflow 5 年序列:                 **{fa_data.get('cashflow_full_pct', 0)}%**")
        lines.append(f"- product_molecule_model 字段齐:     **{fa_data.get('products_full_pct', 0)}%**")
        lines.append(f"- red_flags 5 类齐:                  **{fa_data.get('red_flags_5_pct', 0)}%**")
        lines.append(f"- falsification_signals ≥1:         **{fa_data.get('falsify_pct', 0)}%**")
        lines.append("")
    ff_data = report.get("five_forces", {})
    if ff_data:
        lines.append("## active_hole 进度 — 五力分析 (iter 6 落地, 5 层防御纵深第 5 层)")
        lines.append(f"- agent skill cite (6 agent): **{ff_data.get('agent_skill_cite_count', 0)} / {ff_data.get('agent_count', 0)}** ({ff_data.get('agent_skill_cite_pct', 0)}%)")
        lines.append(f"- stocks 含 five_forces:       **{ff_data.get('stocks_with_five_forces', 0)}** ({ff_data.get('stocks_with_five_forces_pct', 0)}%)")
        lines.append(f"- moat_rating enum 合规:       **{ff_data.get('moat_enum_pass_pct', 0)}%**")
        lines.append(f"- 含 synthesis 5 力交叉编织:   **{ff_data.get('stocks_with_synthesis', 0)}** ({ff_data.get('stocks_with_synthesis_pct', 0)}%)")
        lines.append("")
    va = report.get("verified_audit", {})
    if va and "compliance_pct" in va:
        lines.append("## 根因 3.1 — verify_audit 自动审计 (iteration 2 落地)")
        lines.append(f"- 完全合规:       **{va.get('stocks_clean', 0)} / {va.get('total_stocks', 0)}** ({va.get('compliance_pct', 0)}%)")
        lines.append(f"- 含 fatal 违规: **{va.get('stocks_with_fatal', 0)}**")
        sc = va.get("severity_count", {})
        lines.append(f"- fatal 计数:    {sc.get('fatal', 0)}")
        lines.append(f"- should 计数:   {sc.get('should', 0)}")
        lines.append(f"- 详见:           data/v4/_loop/verify_audit.md")
        lines.append("")
    lines.append("## 候选洞 (排序后)")
    for i, h in enumerate(holes, 1):
        lines.append(f"### {i}. [{h['priority']}] {h['title']}")
        lines.append(f"- 违反: {h['violated_practice']}")
        lines.append(f"- shallow_score: {h['shallow_score']}")
        lines.append(f"- 伤害: {h['harm_to_profit']}")
        lines.append(f"- 证据: {h['evidence']}")
    return "\n".join(lines) + "\n"


def load_verify_audit() -> dict:
    """读取 v4_verify_audit.py 输出, 集成进 mine 报告(iteration 2 落地)"""
    audit_file = LOOP_DIR / "verify_audit.json"
    if not audit_file.exists():
        return {"_note": "运行 python3 scripts/v4_verify_audit.py 生成"}
    try:
        return json.loads(audit_file.read_text(encoding="utf-8"))
    except Exception as e:
        return {"_error": str(e)}


def main() -> int:
    LOOP_DIR.mkdir(parents=True, exist_ok=True)
    stocks = load_jsons(STOCKS_DIR)
    industries = load_jsons(INDUSTRIES_DIR)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "stock_count": len(stocks),
        "industry_count": len(industries),
        "ruler_coverage": scan_ruler_coverage(stocks),
        "shallow_phrases": scan_shallow_phrases(stocks),
        "verified_holes": scan_verified_holes(stocks),
        "falsifiable_gap": scan_falsifiable_gap(stocks),
        "pre_mortem_field": scan_pre_mortem_field(stocks),
        "debate_discipline": scan_debate_discipline(stocks),
        "data_acquisition": scan_data_acquisition(stocks),
        "financial_analysis": scan_financial_analysis(stocks),
        "five_forces": scan_five_forces(stocks),
        "director_lazy": scan_director_vs_subagent_depth(stocks),
        "verified_audit": load_verify_audit(),
    }

    holes = build_candidate_holes(report)

    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT_MD.write_text(render_md(report, holes), encoding="utf-8")

    appended = write_state_backlog(holes)

    print(f"[mine] stocks={len(stocks)} industries={len(industries)}")
    print(f"[mine] candidate holes: {len(holes)}")
    print(f"[mine] appended to backlog: {appended}")
    print(f"[mine] report: {REPORT_MD.relative_to(ROOT)}")
    print(f"[mine] state:  {STATE_FILE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
