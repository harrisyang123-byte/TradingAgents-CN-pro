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
    """投资决策全景树（D0-8 2026-06-13 重构）。

    用户核心洞察修复:
      1. 持仓归属大类/行业 — 不再与配置割裂, 持仓挂在它所属的大类→行业下
      2. 配比是同一笔钱的全局分配 — 顶层大类配比(当前 vs 目标) + capital_flow 资金流向
      3. 第一页可展开树 — 大类→行业→个股/基金, 就地钻取分析

    输出 asset_tree[] (大类树) + capital_flow (这笔钱怎么动) + recommendations。
    """
    holdings_path = repo / "data/v4/_inputs/holdings.json"
    if not holdings_path.exists():
        return None
    h = json.loads(holdings_path.read_text(encoding="utf-8"))
    positions = h.get("positions", []) or []
    total = sum(p.get("market_value", 0) or 0 for p in positions)
    if total <= 0:
        return None

    # 已分析个股 verdict 提取
    def _stock_verdict(code: str):
        sp = repo / f"data/v4/stocks/{code}.json"
        if not sp.exists():
            return None
        try:
            d = json.loads(sp.read_text(encoding="utf-8"))
            pl = d.get("payload", {}) or {}
            v = pl.get("verdict", {}) or {}
            if isinstance(v, dict) and v.get("stance"):
                ap = pl.get("action_plan", {}) or {}
                sl = ap.get("stop_loss", {})
                return {
                    "stance": v.get("stance"), "direction": v.get("direction"),
                    "confidence": v.get("confidence"), "summary": v.get("summary"),
                    "action": ap.get("immediate_action"),
                    "stop_loss": sl.get("hard") if isinstance(sl, dict) else sl,
                }
        except Exception:
            return None
        return None

    classified = classify_holdings(positions)
    by_class = classified.get("by_class", {}) or {}
    stock_inds = {}
    for uid, env in units.items():
        if uid.startswith("stock:"):
            pl = env.get("payload", {}) or {}
            c, ind = pl.get("code"), pl.get("industry")
            if c and ind:
                stock_inds[c] = ind
    agg = aggregate_full(classified, stock_inds)
    industries = agg.get("industries", {}) or {}
    overlap = agg.get("overlap_analysis", {}) or {}
    style = agg.get("style_factors", {}) or {}

    # 大类目标配比（从 overview asset_cards 取 target/action）
    try:
        ov = v4_query.build_overview(units)
        card_map = {c.get("asset_class"): c for c in ov.get("asset_cards", []) or []}
    except Exception:
        card_map = {}

    CLASS_LABELS = {
        "equity": "权益", "fixed_income": "固定收益", "cash": "现金及等价物",
        "commodity": "大宗商品", "precious_metal": "贵金属",
        "real_estate": "房地产", "alternative": "另类投资", "unclassified": "待穿透",
    }

    # 基金主题合并组（复用 detect_overlap）
    fund_groups = []
    grouped_codes = set()
    for t in overlap.get("theme_overlaps", []) or []:
        fs = sorted(t.get("funds", []) or [], key=lambda x: -(x.get("mv", 0) or 0))
        keep_n = 1 if t.get("theme") in ("黄金", "创业板/科创板", "医疗医药", "红利") else 2
        keep, sell = fs[:keep_n], fs[keep_n:]
        for f in fs:
            grouped_codes.add(f.get("code"))
        release = round(sum(f.get("mv", 0) or 0 for f in sell), 0)
        fund_groups.append({
            "theme": t.get("theme"), "fund_count": t.get("fund_count"), "total_mv": t.get("total_mv"),
            "keep": [{"code": f.get("code"), "name": f.get("name"), "mv": f.get("mv")} for f in keep],
            "sell": [{"code": f.get("code"), "name": f.get("name"), "mv": f.get("mv")} for f in sell],
            "release_mv": release,
            "action": (f"保留 {'、'.join(f.get('name','')[:14] for f in keep)}；卖出其余 {len(sell)} 只释放 ¥{release:.0f}"
                       if sell else "已是单只，无需合并"),
        })
    fund_groups.sort(key=lambda x: -(x.get("total_mv", 0) or 0))

    analyzed_count = 0

    def _holding_row(p):
        nonlocal analyzed_count
        code = p.get("code", "")
        row = {
            "code": code, "name": p.get("name", ""),
            "market_value": round(p.get("market_value", 0) or 0, 0),
            "weight": p.get("weight", 0),
            "instrument_type": p.get("instrument_type", ""),
            "analyzed": False, "stance": None, "action": None,
            "confidence": None, "summary": None, "stop_loss": None,
        }
        v = _stock_verdict(code) if p.get("instrument_type") == "stock" else None
        if v:
            analyzed_count += 1
            row.update({"analyzed": True, **v})
        return row

    # ── 收集推荐标的(有 stock 分析单元但不在持仓) by 行业 ──
    holding_codes = {p.get("code") for p in positions if p.get("code")}
    rec_by_ind = {}
    for uid, env in units.items():
        if not uid.startswith("stock:"):
            continue
        pl = env.get("payload", {}) or {}
        code, ind = pl.get("code"), (pl.get("industry") or "其他")
        if not code or code in holding_codes:
            continue  # 只收非持仓的推荐标的
        vc = pl.get("value_creation", {}) or {}
        av = vc.get("actionable_verdict", {}) or {}
        ev = vc.get("expert_valuation", {}) or {}
        vd = pl.get("verdict", {}) or {}
        rec_by_ind.setdefault(ind, []).append({
            "code": code, "name": pl.get("name", ""),
            "stance": av.get("stance") or (vd.get("stance") if isinstance(vd, dict) else None),
            "target_price": ev.get("target_price"),
            "pe": av.get("verified_pe"), "roic": av.get("roic_range") or av.get("roic_pct"),
            "is_recommendation": True,
        })

    # ── 构建大类树 ──────────────────────────────────────────
    asset_tree = []
    for key, label in CLASS_LABELS.items():
        group = by_class.get(key) if key != "unclassified" else None
        hs = (group or {}).get("holdings", []) or []
        if key == "unclassified":
            unc = classified.get("unclassified", []) or []
            hs = unc
        cls_val = sum(x.get("market_value", 0) or 0 for x in hs)
        card = card_map.get(key, {})
        current_pct = round(cls_val / total * 100, 1)
        target = card.get("target_weight")
        action = card.get("action")
        gap_value = round((target / 100 * total - cls_val), 0) if target is not None else None

        node = {
            "key": key, "label": label,
            "current_value": round(cls_val, 0), "current_pct": current_pct,
            "target_pct": target, "action": action, "gap_value": gap_value,
            "has_class_analysis": units.get(f"asset:{key}") is not None,
            "industries": [], "direct_holdings": [], "fund_themes": [],
        }
        if not hs and gap_value is None:
            continue

        if key == "equity":
            # 权益: 直接股票按行业分组 + 权益基金按主题
            stock_codes = {x.get("code") for x in hs if x.get("instrument_type") == "stock"}
            ind_nodes = []
            for ind_name, ind_data in industries.items():
                directs = [d for d in (ind_data.get("direct_holdings") or []) if d.get("code") in stock_codes]
                if not directs:
                    continue
                ind_nodes.append({
                    "name": ind_name,
                    "direct_value": round(ind_data.get("direct_yi", 0) or 0, 0),
                    "indirect_value": round(ind_data.get("indirect_yi", 0) or 0, 0),
                    "total_value": round(ind_data.get("total_yi", 0) or 0, 0),
                    "has_industry_analysis": units.get(f"industry:{ind_name}") is not None,
                    "holdings": [_holding_row(next(p for p in positions if p.get("code") == d.get("code")))
                                 for d in directs if any(p.get("code") == d.get("code") for p in positions)],
                    "indirect": [{"code": s.get("code"), "name": s.get("name"),
                                  "indirect_value": s.get("contribution_yi") or s.get("indirect_value")}
                                 for s in (ind_data.get("indirect_top") or [])][:3],
                })
            # 给持仓行业节点挂推荐标的 + 补充纯推荐行业(持仓未覆盖)
            covered = set()
            for n in ind_nodes:
                n["recommendations"] = rec_by_ind.get(n["name"], [])
                covered.add(n["name"])
            for ind_name, recs in rec_by_ind.items():
                if ind_name in covered:
                    continue
                ind_nodes.append({
                    "name": ind_name, "direct_value": 0, "indirect_value": 0, "total_value": 0,
                    "has_industry_analysis": units.get(f"industry:{ind_name}") is not None,
                    "holdings": [], "indirect": [], "recommendations": recs, "is_rec_only": True,
                })
            ind_nodes.sort(key=lambda x: -(x.get("total_value", 0) or 0))
            node["industries"] = ind_nodes
            # 权益基金主题
            node["fund_themes"] = [g for g in fund_groups
                                   if g["theme"] not in ("国债/信用债",) and g["theme"] not in ("黄金",)]
        else:
            # 非权益大类: 直接列持仓
            node["direct_holdings"] = [_holding_row(p) for p in sorted(hs, key=lambda x: -(x.get("market_value", 0) or 0))]
            if key == "fixed_income":
                node["fund_themes"] = [g for g in fund_groups if g["theme"] == "国债/信用债"]
            elif key == "precious_metal":
                node["fund_themes"] = [g for g in fund_groups if g["theme"] == "黄金"]
        asset_tree.append(node)

    # ── 资金流向（这笔钱怎么动）────────────────────────────
    sources, uses = [], []
    for node in asset_tree:
        gv = node.get("gap_value")
        if gv is None:
            continue
        if gv < -1000:  # 超配 → 资金来源
            sources.append({"desc": f"{node['label']} 当前 {node['current_pct']}% 高于目标 {node['target_pct']}%",
                            "amount": round(-gv, 0)})
        elif gv > 1000:  # 低配 → 资金去向
            uses.append({"desc": f"{node['label']} 当前 {node['current_pct']}% 低于目标 {node['target_pct']}%，需加仓",
                         "amount": round(gv, 0)})
    # 个股减仓也是来源 / 加仓是去向
    for node in asset_tree:
        for ind in node.get("industries", []):
            for hh in ind.get("holdings", []):
                if hh.get("stance") and "减" in hh["stance"]:
                    uses_note = hh.get("action") or ""
                    sources.append({"desc": f"{hh['name']} {hh['stance']}（{hh['weight']}%）", "amount": None, "note": uses_note})
                elif hh.get("stance") and "加" in hh["stance"]:
                    uses.append({"desc": f"{hh['name']} {hh['stance']}", "amount": None})
    # 基金合并释放
    total_fund_release = sum(g["release_mv"] for g in fund_groups)
    if total_fund_release > 0:
        sources.append({"desc": f"基金同主题合并（{sum(1 for g in fund_groups if g['sell'])} 组重复）",
                        "amount": round(total_fund_release, 0)})

    pending = (sum(1 for n in asset_tree for ind in n.get("industries", [])
                   for hh in ind.get("holdings", []) if hh.get("stance") and "持有" not in (hh.get("stance") or ""))
               + sum(1 for g in fund_groups if g.get("sell")))

    indirect = []
    for s in (overlap.get("summary", {}) or {}).get("indirect_concentration_top10", []) or []:
        indirect.append({
            "code": s.get("code"), "name": s.get("name"),
            "indirect_value": s.get("total_indirect_value"), "fund_count": s.get("fund_count"),
            "note": f"已通过 {s.get('fund_count')} 只基金间接持有 ¥{s.get('total_indirect_value'):.0f}，直接加仓前先算总暴露",
        })

    return {
        "as_of": h.get("as_of") or None,
        "summary": {
            "total_value": round(total, 0),
            "analyzed_count": analyzed_count,
            "total_stocks": sum(1 for p in positions if p.get("instrument_type") == "stock"),
            "total_funds": sum(1 for p in positions if p.get("instrument_type") in ("fund", "etf")),
            "pending_actions": pending,
            "style_region": style.get("region", {}),
            "config_note": "当前配比为实时计算（基于持仓市值）；目标配比来自 alloc:portfolio 单元。两者口径若有差异以实时为准。",
        },
        "asset_tree": asset_tree,
        "capital_flow": {"sources": sources, "uses": uses},
        "fund_groups": fund_groups,
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
