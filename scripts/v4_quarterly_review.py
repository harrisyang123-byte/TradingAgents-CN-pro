#!/usr/bin/env python3
"""
v4_quarterly_review.py — 季度复盘报告 (OpenSpec change 阶段 C3)

扫描所有单元的 historical_alpha → 按层(asset/industry/stock)汇总命中率/平均alpha/
胜负 case/系统性偏差 → 输出 markdown 复盘报告。

用法:
  python3 scripts/v4_quarterly_review.py                       # 输出到 planning/v4/quarterly-review-YYYY-Qx.md
  python3 scripts/v4_quarterly_review.py --stdout              # 打印不落盘

前提: 各单元已通过 v4_replay --backfill 回填 historical_alpha。
铁律: 无 historical_alpha 的单元标'待回填',不编造命中率。
"""
import argparse, json, glob, os
from datetime import datetime
from collections import defaultdict

DATA = "data/v4"


def collect_units():
    units = []
    for sub in ["assets", "industries", "stocks", "allocation"]:
        for f in glob.glob(f"{DATA}/{sub}/*.json"):
            try:
                d = json.load(open(f))
                units.append((sub, d))
            except Exception:
                pass
    return units


def review():
    units = collect_units()
    layer_stats = defaultdict(lambda: {"total": 0, "with_alpha": 0, "hit": 0, "miss": 0,
                                       "flat": 0, "other": 0, "cases": []})
    for sub, d in units:
        p = d.get("payload", {})
        ha = p.get("historical_alpha")
        layer = {"assets": "大类", "industries": "行业", "stocks": "个股", "allocation": "配比"}[sub]
        s = layer_stats[layer]
        s["total"] += 1
        if not ha:
            continue
        s["with_alpha"] += 1
        hit = ha.get("hit", "")
        if hit == "hit":
            s["hit"] += 1
        elif hit == "miss":
            s["miss"] += 1
        elif hit in ("flat", "neutral_ok"):
            s["flat"] += 1
        else:
            s["other"] += 1
        s["cases"].append({
            "unit": d.get("unit_id"), "name": p.get("name", ""),
            "hit": hit, "note": ha.get("alpha_note", "")[:80]
        })
    return layer_stats


def to_markdown(stats):
    q = (datetime.utcnow().month - 1) // 3 + 1
    yr = datetime.utcnow().year
    lines = [f"# v4 季度复盘报告 — {yr} Q{q}", "",
             f"> 生成: {datetime.utcnow().isoformat()[:10]} | 数据源: 各单元 historical_alpha 回填", ""]

    # 总览表
    lines.append("## 一、各层命中率总览")
    lines.append("")
    lines.append("| 层 | 单元数 | 已回填alpha | 命中 | 未命中 | 持平 | 其它 | 命中率* |")
    lines.append("|---|---|---|---|---|---|---|---|")
    total_ha = total_hit = total_miss = 0
    for layer in ["大类", "行业", "个股", "配比"]:
        s = stats.get(layer)
        if not s:
            continue
        wa = s["with_alpha"]
        hr = f"{s['hit']/(s['hit']+s['miss'])*100:.0f}%" if (s['hit']+s['miss']) > 0 else "n/a"
        lines.append(f"| {layer} | {s['total']} | {wa} | {s['hit']} | {s['miss']} | "
                     f"{s['flat']} | {s['other']} | {hr} |")
        total_ha += wa; total_hit += s['hit']; total_miss += s['miss']
    overall = f"{total_hit/(total_hit+total_miss)*100:.0f}%" if (total_hit+total_miss) > 0 else "n/a"
    lines.append(f"| **合计** | - | {total_ha} | {total_hit} | {total_miss} | - | - | **{overall}** |")
    lines.append("")
    lines.append("> *命中率 = 命中/(命中+未命中)，持平/其它不计入分母")
    lines.append("")

    # 胜负 case
    lines.append("## 二、胜负 case 明细")
    lines.append("")
    for layer in ["大类", "行业", "个股", "配比"]:
        s = stats.get(layer)
        if not s or not s["cases"]:
            continue
        lines.append(f"### {layer}")
        for c in s["cases"]:
            mark = {"hit": "✅", "miss": "❌", "flat": "➖", "neutral_ok": "➖"}.get(c["hit"], "🔍")
            lines.append(f"- {mark} **{c['unit']}** {c['name']}: {c['note']}")
        lines.append("")

    # 系统性偏差 + 改进建议(框架)
    lines.append("## 三、系统性偏差识别")
    lines.append("")
    if total_ha == 0:
        lines.append("⚠️ **尚无回填 alpha 的单元** — 需先用 `v4_replay --backfill` 联网回填(沙箱无外网,待生产环境)。")
        lines.append("当前 historical_alpha 多为 tracking/待回填状态,无法统计系统性偏差。")
    else:
        lines.append(f"- 已回填 {total_ha} 个单元,命中 {total_hit}/未命中 {total_miss}")
        lines.append("- (系统性偏差分析需积累 ≥1 季度多版本数据后才有统计意义)")
    lines.append("")
    lines.append("## 四、改进建议")
    lines.append("")
    lines.append("- 生产环境部署后用 AKShare 联网回填全部 stock 的 historical_alpha")
    lines.append("- 积累 2-3 季度后,识别系统性偏差(如:是否系统性高估目标价/是否对某行业判断更准)")
    lines.append("- 偏差反哺 director prompt(C4: critic 消费 historical_alpha 拷问'上次错了这次为何对')")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stdout", action="store_true")
    args = ap.parse_args()
    stats = review()
    md = to_markdown(stats)
    if args.stdout:
        print(md)
    else:
        q = (datetime.utcnow().month - 1) // 3 + 1
        out = f"planning/v4/quarterly-review-{datetime.utcnow().year}-Q{q}.md"
        open(out, "w").write(md)
        print(f"季度复盘报告 → {out}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
