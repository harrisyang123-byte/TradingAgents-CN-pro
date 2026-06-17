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
