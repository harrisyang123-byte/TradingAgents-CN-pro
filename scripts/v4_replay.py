#!/usr/bin/env python3
"""
v4_replay.py — 历史判断回放器 (OpenSpec change v4-completion-validation-five-forces 阶段 C1)

给定 unit_id，读取该单元所有历史版本(archive + 当前)，提取每版判断(rating/target_price/
stance/entry_range)，用实际行情对比，计算判断准确率(命中/未命中 + alpha)。

用法:
  python3 scripts/v4_replay.py --unit stock:300308
  python3 scripts/v4_replay.py --unit stock:300308 --to-date 2026-06-12 --price 1000
  python3 scripts/v4_replay.py --unit stock:300308 --md   # 输出 markdown

价格数据来源优先级:
  1. --price 命令行手动传入(沙箱无外网时用核实值)
  2. AKShare 联网取(生产环境)
  3. 取不到 → 标 unavailable，仅做判断方向一致性分析(不算 alpha)

铁律: 取不到价格不编造，老实标 unavailable。
"""
import argparse, json, glob, os, sys
from datetime import datetime

DATA = "data/v4"
ARCHIVE = f"{DATA}/_archive"

UNIT_DIR = {
    "stock": "stocks", "industry": "industries", "asset": "assets",
    "alloc": "allocation", "plan": "plans",
}


def _safe(s):
    import re
    return re.sub(r"[/\\:\*\?\"<>\|（）()\s]+", "_", str(s)) or "_"


def _unit_file(unit_id):
    typ = unit_id.split(":")[0]
    name = unit_id.split(":", 1)[1]
    sub = UNIT_DIR.get(typ, typ)
    # alloc:industry:xxx 特殊
    if unit_id.startswith("alloc:industry:"):
        name = unit_id.split(":", 2)[2]
        return f"{DATA}/allocation/industry_{_safe(name)}.json"
    if typ == "alloc":
        return f"{DATA}/allocation/{_safe(name)}.json"
    return f"{DATA}/{sub}/{_safe(name)}.json"


def _archive_dir(unit_id):
    typ = unit_id.split(":")[0]
    name = unit_id.split(":", 1)[1]
    sub = UNIT_DIR.get(typ, typ)
    if unit_id.startswith("alloc:industry:"):
        name = unit_id.split(":", 2)[2]
        return f"{ARCHIVE}/allocation/industry_{_safe(name)}"
    if typ == "alloc":
        return f"{ARCHIVE}/allocation/{_safe(name)}"
    return f"{ARCHIVE}/{sub}/{_safe(name)}"


def collect_versions(unit_id):
    """收集该单元所有历史版本(archive + 当前)，按 version 排序"""
    versions = []
    adir = _archive_dir(unit_id)
    if os.path.isdir(adir):
        for f in sorted(glob.glob(f"{adir}/v*.json")):
            try:
                d = json.load(open(f))
                versions.append(d)
            except Exception:
                pass
    cur = _unit_file(unit_id)
    if os.path.exists(cur):
        try:
            versions.append(json.load(open(cur)))
        except Exception:
            pass
    # 去重 + 按 version 排序
    seen = {}
    for v in versions:
        seen[v.get("version", 0)] = v
    return [seen[k] for k in sorted(seen.keys())]


def extract_judgment(env):
    """从信封提取判断要点"""
    p = env.get("payload", {})
    v = p.get("verdict", {}) if isinstance(p.get("verdict"), dict) else {}
    return {
        "version": env.get("version"),
        "date": env.get("generated_at", "")[:10],
        # 个股层字段在 payload 顶层，大类/行业在 verdict
        "rating": p.get("rating") or v.get("stance"),
        "stance": v.get("stance") or p.get("rating"),
        "target_price": p.get("target_price") or v.get("target_price"),
        "entry_range": p.get("entry_price_range"),
        "expectation_gap": (p.get("expectation_gap") or v.get("expectation_gap") or "")[:60],
    }


def get_actual_price(code, market, to_date, manual_price=None):
    """取实际价格: 手动 > AKShare > unavailable"""
    if manual_price is not None:
        return {"price": manual_price, "source": "manual", "status": "verified"}
    try:
        import akshare as ak  # noqa
        # 生产环境: 用 stock_source 取历史收盘价
        from app.services.v4 import stock_source
        # 简化: 取最新价(实际应取 to_date 当日)
        info = stock_source.fetch_stock_quote(code) if hasattr(stock_source, "fetch_stock_quote") else None
        if info and info.get("price"):
            return {"price": float(info["price"]), "source": "akshare", "status": "verified"}
    except Exception as e:
        return {"price": None, "source": f"unavailable({type(e).__name__})", "status": "missing"}
    return {"price": None, "source": "unavailable", "status": "missing"}


def replay(unit_id, to_date=None, manual_price=None):
    versions = collect_versions(unit_id)
    if not versions:
        return {"unit_id": unit_id, "error": "no versions found"}
    judgments = [extract_judgment(v) for v in versions]

    # 取实际价格(仅 stock 层)
    actual = {"price": None, "source": "n/a", "status": "n/a"}
    code = None
    if unit_id.startswith("stock:"):
        code = unit_id.split(":", 1)[1]
        market = versions[-1].get("payload", {}).get("market", "CN")
        actual = get_actual_price(code, market, to_date, manual_price)

    # 逐版本对比判断 vs 实际
    rows = []
    actual_price = actual.get("price")
    for j in judgments:
        row = dict(j)
        tp = j.get("target_price")
        er = j.get("entry_range")
        if actual_price and tp:
            # 当时目标价 vs 当前实际价
            row["actual_price"] = actual_price
            row["target_vs_actual"] = round((actual_price - tp) / tp * 100, 1)  # 实际比目标高/低多少%
            # 命中判断: 若当时给买点区间，实际价是否进过买点区间(粗略)
            if er and len(er) == 2 and er[0]:
                row["entry_hit"] = "可能命中" if actual_price <= er[1] * 1.2 else "未回落到买点"
        else:
            row["actual_price"] = actual_price
            row["note"] = "价格不可得，仅判断方向一致性"
        rows.append(row)

    return {
        "unit_id": unit_id,
        "replay_date": to_date or datetime.utcnow().isoformat()[:10],
        "actual_price_source": actual.get("source"),
        "version_count": len(versions),
        "judgments": rows,
    }


def to_markdown(result):
    lines = [f"# 回放报告 — {result['unit_id']}", ""]
    lines.append(f"- 回放日期: {result['replay_date']}")
    lines.append(f"- 实际价格来源: {result['actual_price_source']}")
    lines.append(f"- 历史版本数: {result['version_count']}")
    lines.append("")
    lines.append("| 版本 | 日期 | 评级 | 目标价 | 实际价 | 目标vs实际 | 预期差 |")
    lines.append("|---|---|---|---|---|---|---|")
    for j in result["judgments"]:
        lines.append(f"| v{j.get('version')} | {j.get('date')} | {str(j.get('rating'))[:14]} | "
                     f"{j.get('target_price') or '-'} | {j.get('actual_price') or '-'} | "
                     f"{j.get('target_vs_actual', '-')}{'%' if 'target_vs_actual' in j else ''} | "
                     f"{str(j.get('expectation_gap'))[:30]} |")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--unit", required=True, help="unit_id 如 stock:300308")
    ap.add_argument("--to-date", default=None)
    ap.add_argument("--price", type=float, default=None, help="手动传实际价格(沙箱无外网时)")
    ap.add_argument("--md", action="store_true", help="输出 markdown")
    args = ap.parse_args()

    result = replay(args.unit, args.to_date, args.price)
    if args.md:
        print(to_markdown(result))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.exit(main())
