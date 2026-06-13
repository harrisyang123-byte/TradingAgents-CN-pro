#!/usr/bin/env python3
"""build_snapshot_v4.py — v4 单元 → 前端静态快照（FR-009 / NFR4.1）

把 data/v4 单元落盘组装成与 API **完全同构**的静态 JSON，输出到
frontend/public/snapshot/v4/，供前端在 VITE_STATIC_SNAPSHOT=1 时直接 fetch
（无后端 / 无 Mongo 也能看，与走 API 展示一致）。

文件名与 frontend/src/api/portfolioV4.ts loadSnapshot 对齐：
  overview.json            ← build_overview
  units_status.json        ← build_units_status
  asset_<class>.json   ×7  ← build_asset_detail
  industry_<name>.json ×N  ← build_industry_detail（按已落盘 industry 单元）

复用 app/services/v4/v4_query 的同一批纯函数，确保 API/快照零分叉（NFR4.1）。

用法:
  python scripts/build_snapshot_v4.py
  python scripts/build_snapshot_v4.py --out frontend/public/snapshot/v4
"""

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from app.services.v4 import asset_classes as ac  # noqa: E402
from app.services.v4 import v4_query, v4_unit_store as store  # noqa: E402
from app.services.v4.v4_classifier import classify_holdings  # noqa: E402
from app.services.v4.v4_aggregator import aggregate_full  # noqa: E402


def _load_units_from_files() -> dict:
    """从 data/v4 落盘读取全部单元 → {unit_id: envelope}（不连 Mongo）。"""
    store.rebuild_index()
    units = {}
    for u in store.list_units():
        env = store.read_unit(u["unit_id"])
        if env and env.get("unit_id"):
            units[env["unit_id"]] = env
    return units


def _write(out_dir: Path, name: str, data) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / name
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


def build_holdings_review(repo: Path, units: dict):
    """持仓体检 — 用户视角的「持仓 × 处理动作」统一视图（D0-7 2026-06-13）。

    回答用户三问:
      1. 我的持仓分析在哪 → stocks[] 逐项含 analyzed/stance/action + 可点进个股详情
      2. 基金穿透怎么用 → fund_groups[] 同主题分组 + 合并动作(保留谁/卖谁/释放多少)
      3. 穿透完怎么处理 → 每项都有 action; indirect_holdings 提示"已间接持有勿重复买"
    """
    holdings_path = repo / "data/v4/_inputs/holdings.json"
    if not holdings_path.exists():
        return None
    h = json.loads(holdings_path.read_text(encoding="utf-8"))
    positions = h.get("positions", []) or []
    total = sum(p.get("market_value", 0) or 0 for p in positions)
    if total <= 0:
        return None

    stocks, funds, cash, others = [], [], [], []
    for p in positions:
        it = p.get("instrument_type", "")
        if it == "stock":
            stocks.append(p)
        elif it in ("fund", "etf"):
            funds.append(p)
        elif it == "cash":
            cash.append(p)
        else:
            others.append(p)

    stock_val = sum(p.get("market_value", 0) or 0 for p in stocks)
    fund_val = sum(p.get("market_value", 0) or 0 for p in funds)
    cash_val = sum(p.get("market_value", 0) or 0 for p in cash)

    # 已分析股票 verdict 提取（读 data/v4/stocks/<code>.json）
    stock_rows = []
    analyzed_count = 0
    for p in sorted(stocks, key=lambda x: -(x.get("market_value", 0) or 0)):
        code = p.get("code", "")
        row = {
            "code": code, "name": p.get("name", ""),
            "market_value": round(p.get("market_value", 0) or 0, 0),
            "weight": p.get("weight", 0),
            "analyzed": False, "stance": None, "direction": None,
            "confidence": None, "summary": None, "action": None,
            "stop_loss": None, "target_weight": None,
        }
        sp = repo / f"data/v4/stocks/{code}.json"
        if sp.exists():
            try:
                d = json.loads(sp.read_text(encoding="utf-8"))
                pl = d.get("payload", {}) or {}
                v = pl.get("verdict", {}) or {}
                if isinstance(v, dict) and v.get("stance"):
                    row["analyzed"] = True
                    analyzed_count += 1
                    row["stance"] = v.get("stance")
                    row["direction"] = v.get("direction")
                    row["confidence"] = v.get("confidence")
                    row["summary"] = v.get("summary")
                    ap = pl.get("action_plan", {}) or {}
                    row["action"] = ap.get("immediate_action")
                    sl = ap.get("stop_loss", {})
                    row["stop_loss"] = sl.get("hard") if isinstance(sl, dict) else sl
            except Exception:
                pass
        stock_rows.append(row)

    # 基金穿透聚合（行业 + 风格 + 重叠）
    classified = classify_holdings(positions)
    stock_inds = {}
    for uid, env in units.items():
        if uid.startswith("stock:"):
            pl = env.get("payload", {}) or {}
            c, ind = pl.get("code"), pl.get("industry")
            if c and ind:
                stock_inds[c] = ind
    agg = aggregate_full(classified, stock_inds)
    overlap = agg.get("overlap_analysis", {}) or {}
    style = agg.get("style_factors", {}) or {}

    # 基金分组 + 合并动作（保留 mv 最大 1-2 只，其余建议卖出）
    fund_groups = []
    grouped_codes = set()
    for t in overlap.get("theme_overlaps", []) or []:
        fs = sorted(t.get("funds", []) or [], key=lambda x: -(x.get("mv", 0) or 0))
        keep_n = 1 if t.get("theme") in ("黄金", "创业板/科创板", "医疗医药", "红利") else 2
        keep, sell = fs[:keep_n], fs[keep_n:]
        for f in fs:
            grouped_codes.add(f.get("code"))
        release = round(sum(f.get("mv", 0) or 0 for f in sell), 0)
        if sell:
            action = (f"保留 {'、'.join(f.get('name','')[:14] for f in keep)}"
                      f"；可合并卖出其余 {len(sell)} 只释放 ¥{release:.0f}（降重复暴露+省管理费）")
        else:
            action = "已是单只，无需合并"
        fund_groups.append({
            "theme": t.get("theme"), "fund_count": t.get("fund_count"),
            "total_mv": t.get("total_mv"),
            "funds": fs,
            "keep": [{"code": f.get("code"), "name": f.get("name"), "mv": f.get("mv")} for f in keep],
            "sell": [{"code": f.get("code"), "name": f.get("name"), "mv": f.get("mv")} for f in sell],
            "release_mv": release, "action": action,
        })
    fund_groups.sort(key=lambda x: -(x.get("total_mv", 0) or 0))

    ungrouped = [
        {"code": f.get("code"), "name": f.get("name"),
         "market_value": round(f.get("market_value", 0) or 0, 0)}
        for f in funds if f.get("code") not in grouped_codes
    ]
    ungrouped.sort(key=lambda x: -(x.get("market_value", 0) or 0))

    indirect = []
    for s in (overlap.get("summary", {}) or {}).get("indirect_concentration_top10", []) or []:
        indirect.append({
            "code": s.get("code"), "name": s.get("name"),
            "indirect_value": s.get("total_indirect_value"),
            "fund_count": s.get("fund_count"),
            "note": (f"已通过 {s.get('fund_count')} 只基金间接持有 ¥{s.get('total_indirect_value'):.0f}，"
                     f"直接加仓前先算总暴露，避免双重重仓"),
        })

    pending = (sum(1 for r in stock_rows if r.get("stance") and "持有" not in (r.get("stance") or ""))
               + sum(1 for g in fund_groups if g.get("sell")))

    return {
        "as_of": h.get("as_of") or None,
        "summary": {
            "total_value": round(total, 0),
            "stock_value": round(stock_val, 0), "stock_pct": round(stock_val / total * 100, 1),
            "fund_value": round(fund_val, 0), "fund_pct": round(fund_val / total * 100, 1),
            "cash_value": round(cash_val, 0), "cash_pct": round(cash_val / total * 100, 1),
            "analyzed_count": analyzed_count, "total_stocks": len(stocks),
            "total_funds": len(funds), "pending_actions": pending,
            "style_region": style.get("region", {}),
            "style_fund_type": style.get("fund_type", {}),
        },
        "stocks": stock_rows,
        "fund_groups": fund_groups,
        "ungrouped_funds": ungrouped,
        "cash": [{"name": p.get("name"), "market_value": round(p.get("market_value", 0) or 0, 0),
                  "weight": p.get("weight", 0)} for p in cash],
        "indirect_holdings": indirect,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="v4 静态快照生成")
    ap.add_argument("--out", default="frontend/public/snapshot/v4", help="输出目录")
    args = ap.parse_args()

    out_dir = _REPO / args.out if not Path(args.out).is_absolute() else Path(args.out)
    units = _load_units_from_files()
    if not units:
        print("（data/v4 无单元产物；先 analyze 后再生成快照）")
        # 仍产出空 overview，保证前端不报错
    n = 0

    # overview.json（含 has_data / asset_classes，与路由一致）
    overview = v4_query.build_overview(units)
    overview["has_data"] = bool(units)
    overview["asset_classes"] = ac.ASSET_CLASSES
    _write(out_dir, "overview.json", overview)
    n += 1

    # units_status.json（与 /units/status 一致）
    _write(out_dir, "units_status.json",
           {"units": v4_query.build_units_status(units), "has_data": bool(units)})
    n += 1

    # asset_<class>.json ×7（与 /asset/{class} 一致）
    for cfg in ac.ASSET_CLASSES:
        klass = cfg["key"]
        _write(out_dir, f"asset_{klass}.json", v4_query.build_asset_detail(units, klass))
        n += 1

    # asset_unclassified.json：若存在 unclassified 单元（投顾组合等待穿透敞口），
    # 也生成详情快照，避免前端点击该卡片下钻时 404（与 build_overview 追加卡片对齐）。
    if units.get("asset:unclassified"):
        _write(out_dir, "asset_unclassified.json", v4_query.build_asset_detail(units, "unclassified"))
        n += 1

    # industry_<name>.json（按已落盘 industry 单元，文件名 = 原始行业名，与前端 encodeURIComponent 对齐）
    for uid in units:
        if uid.startswith("industry:"):
            name = uid.split(":", 1)[1]
            _write(out_dir, f"industry_{name}.json", v4_query.build_industry_detail(units, name))
            n += 1

    # stock_<code>.json（D0-3：个股详情，按已落盘 stock 单元）
    for uid in units:
        if uid.startswith("stock:"):
            code = uid.split(":", 1)[1]
            _write(out_dir, f"stock_{code}.json", v4_query.build_stock_detail(units, code))
            n += 1

    # holdings_review.json（D0-7：持仓体检 — 用户视角「持仓 × 处理动作」）
    hr = build_holdings_review(_REPO, units)
    if hr is not None:
        _write(out_dir, "holdings_review.json", hr)
        n += 1

    print(f"✅ v4 静态快照生成完成：{n} 个文件 → {out_dir}")
    print("   前端设 VITE_STATIC_SNAPSHOT=1 即直接 fetch 这些快照（与走 API 同构）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
