#!/usr/bin/env python3
"""collect_v4.py — v4 单元输入包采集（FR-001 / AC2.1 / AC1.4）

为指定单元拼装多维输入包，落到 data/v4/inputs/，供 v4-*.md 子 Agent 用 Read 读取。
脱 LLM、纯 Python。两种持仓来源（AC1.4）：
  1. --portfolio-file holdings.json （AI 代跑，脱 Mongo）
  2. Mongo（本地运行，best-effort，缺库降级为空持仓——零持仓大类仍可分析 AC2.5）

产物：
  inputs/portfolio_classified.json   七大类穿透归类全景（FR-001）
  inputs/asset_<class>.json          单大类输入包（holdings + macro + 数据可得性）
  inputs/data_macro.json             宏观快照（可得则填，缺失标 missing，AC2.1 降级）
"""

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from app.services.v4 import asset_classes as ac  # noqa: E402
from app.services.v4 import v4_classifier  # noqa: E402
from app.services.v4 import v4_unit_store as store  # noqa: E402


def _inputs_dir() -> Path:
    d = store.data_root() / "inputs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write_json(path: Path, obj) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def load_positions(portfolio_file: str, user_id: str) -> tuple:
    """返回 (positions, source)。"""
    if portfolio_file:
        p = Path(portfolio_file)
        if not p.exists():
            print(f"⚠ 持仓文件不存在: {portfolio_file}，按零持仓处理", file=sys.stderr)
            return [], "file_missing"
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            print(f"⚠ 持仓文件解析失败: {e}，按零持仓处理", file=sys.stderr)
            return [], "file_error"
        if isinstance(data, dict):
            positions = data.get("positions") or data.get("holdings") or []
        elif isinstance(data, list):
            positions = data
        else:
            positions = []
        return positions, "portfolio_file"

    # Mongo best-effort（同步 pymongo，缺库则降级）
    try:
        from app.core.database import get_mongo_db_sync
        db = get_mongo_db_sync()
        rows = list(db["paper_positions"].find({"user_id": user_id}))
        positions = []
        for r in rows:
            positions.append({
                "code": r.get("code") or r.get("symbol", ""),
                "name": r.get("name", ""),
                "weight": r.get("weight", 0),
                "market_value": r.get("market_value", 0),
                "instrument_type": r.get("instrument_type", "stock"),
            })
        return positions, "mongo"
    except Exception as e:
        print(f"⚠ Mongo 持仓读取失败（{e}），按零持仓处理（零持仓大类仍可分析）", file=sys.stderr)
        return [], "mongo_unavailable"


def build_macro_snapshot() -> dict:
    """宏观快照（档 A 22 指标）。

    国内基本面/利率硬数据（LPR/国债收益率/CPI/PPI/PMI/M2/两融）由 AKShare 官方口径
    接口程序化拉取——可复现、带发布日期、不撞搜索引擎陈旧缓存（修复 cn10y 被搜成
    过时 2.7% 之类的坑）。海外/实时/大宗（US市场/汇率/原油黄金铜/风险情绪）AKShare
    时效差或不覆盖，留 missing 骨架，由第 2 阶段 data-desk 联网补齐。

    降级而非崩溃：akshare 未装/无网/接口变更时，对应指标保持 missing，不中断采集。
    """
    from datetime import datetime, timezone
    from app.services.v4 import macro_source  # noqa: E402

    indicators, filled, ak_err = macro_source.build_macro_indicators()
    n_verified = sum(1 for v in indicators.values() if v.get("status") == "verified")

    if n_verified == 0:
        availability = "unavailable"
    elif n_verified >= 15:
        availability = "available"
    else:
        availability = "partial"

    if ak_err:
        note = (f"AKShare 不可用（{ak_err}）——全部指标待第 2 阶段联网补齐。"
                "Agent 必须用 web 搜索/抓取补 LPR/国债/CPI/PMI 等，evidence 标 verified+来源，不得编造。")
    else:
        note = (f"国内硬数据已由 AKShare 程序化填充（{n_verified} 项 verified：{', '.join(filled)}）。"
                "海外/实时/大宗及 reverse_repo_7d/tsf_yoy 等 missing 项，需第 2 阶段 data-desk 联网补齐"
                "（evidence 标 verified+来源 URL，多源冲突标分歧不调和，不得编造）。")

    return {
        "tier": "global",
        "action": "fetched" if filled else "skeleton",
        "source": "akshare (collect_v4 程序化) + needs_web_fetch（海外/实时/大宗）",
        "data_availability": availability,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "ttl_hours": 12,
        "akshare_filled": filled,
        "note": note,
        "indicators": indicators,
        "evidence": [],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="v4 单元输入包采集")
    ap.add_argument("--selector", required=True, help="单元选择器，如 asset:equity")
    ap.add_argument("--user-id", default="")
    ap.add_argument("--verb", default="analyze")
    ap.add_argument("--portfolio-file", default="")
    args = ap.parse_args()

    try:
        info = store.parse_unit_id(args.selector)
    except ValueError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1

    inputs = _inputs_dir()

    # 1. 持仓 → 七大类穿透归类
    positions, source = load_positions(args.portfolio_file, args.user_id)
    classified = v4_classifier.classify_holdings(positions)
    classified["source"] = source
    _write_json(inputs / "portfolio_classified.json", classified)
    print(f"  ✓ 穿透归类 {classified['position_count']} 条持仓（来源={source}）")

    # 2. 宏观快照
    macro = build_macro_snapshot()
    _write_json(inputs / "data_macro.json", macro)
    print(f"  ✓ 宏观快照（{macro['data_availability']}）")

    # 3. 按单元类型拼装专属输入包
    ut, key = info["unit_type"], info["key"]
    if ut in ("asset", "plan"):
        if not ac.is_valid_class(key):
            print(f"❌ 未知大类: {key}（合法: {','.join(ac.CLASS_KEYS)}）", file=sys.stderr)
            return 1
        bucket = classified["by_class"].get(key, {})
        pack = {
            "asset_class": key,
            "label": ac.label_of(key),
            "max_drill_depth": ac.max_drill_depth(key),
            "ttl_days": ac.get_class(key)["ttl_days"],
            "current_weight": bucket.get("weight", 0.0),
            "current_market_value": bucket.get("market_value", 0.0),
            "tradable": bucket.get("tradable", []),
            "holding_only_exposure": bucket.get("holding_only_exposure", 0.0),
            "holdings": bucket.get("holdings", []),
            "macro_context": macro,
            "data_availability": {
                "portfolio": source,
                "macro": macro["data_availability"],
            },
            "zero_holding": bucket.get("market_value", 0.0) == 0 and not bucket.get("holdings"),
        }
        out_name = f"asset_{key}.json" if ut == "asset" else f"plan_{key}.json"
        _write_json(inputs / out_name, pack)
        print(f"  ✓ {ut}:{key} 输入包 → inputs/{out_name}"
              + ("（零持仓，仍可分析是否值得择机配置）" if pack["zero_holding"] else ""))
    else:
        # alloc:* 单元不需要专属输入包（直接读上游 asset:*/industry:*/stock:* 落盘单元）；
        # industry:<name> / stock:<code> 拼装专属输入包（FR-006）。
        if ut == "industry":
            _build_industry_pack(inputs, key, classified, macro)
        elif ut == "stock":
            _build_stock_pack(inputs, key, classified, macro, args.user_id)
        else:
            print(f"  · {ut}:{key} 采集：已产出归类与宏观快照（alloc 单元直接读上游落盘单元）")

    print(f"✅ collect_v4 完成 → {inputs}")
    return 0


def _safe(s: str) -> str:
    import re as _re
    return _re.sub(r"[/\\:\*\?\"<>\|（）()\s]+", "_", str(s)) or "_"


def _build_industry_pack(inputs: Path, name: str, classified: dict, macro: dict) -> None:
    """行业深辩输入包（FR-006 AC6.2）：候选信息 + 景气信号(best-effort) + 权益持仓敞口。"""
    from app.services.v4 import industry_candidates as ic

    # 候选元信息（rationale/kind）
    cand_meta = next((c for c in ic.builtin_candidates() if c["name"] == name), None)

    # best-effort 景气信号
    vitality = {"available": False, "note": "未取到实时景气信号，行业分析降级为 LLM 知识 + 可得行情"}
    try:
        import asyncio
        from app.services.industry_vitality import score_all_industries
        scores = asyncio.run(score_all_industries())
        hit = next((s for s in scores
                    if ic._VITALITY_HINT.get(getattr(s, "industry", "")) == name
                    or getattr(s, "industry", "") == name), None)
        if hit:
            vitality = {
                "available": True,
                "total_score": round(float(getattr(hit, "total_score", 0) or 0), 3),
                "top3_flag": bool(getattr(hit, "top3_flag", False)),
                "signal_breakdown": getattr(hit, "signal_breakdown", {}),
            }
    except Exception as e:
        vitality["error"] = str(e)

    # 权益持仓中属于该行业关键词的敞口（粗匹配，供 agent 参考）
    equity_bucket = classified.get("by_class", {}).get(ac.EQUITY, {})
    related = [h for h in equity_bucket.get("holdings", [])
               if name.split("/")[0] in (h.get("name", "") + h.get("code", ""))]

    pack = {
        "industry": name,
        "candidate_meta": cand_meta,
        "vitality": vitality,
        "related_holdings": related,
        "macro_context": macro,
        "data_availability": {"vitality": vitality["available"], "macro": macro["data_availability"]},
    }
    out = inputs / f"industry_{_safe(name)}.json"
    _write_json(out, pack)
    print(f"  ✓ industry:{name} 输入包 → inputs/{out.name}"
          + ("" if vitality["available"] else "（景气降级，仅 LLM 知识）"))


def _build_stock_pack(inputs: Path, code: str, classified: dict, macro: dict, user_id: str) -> None:
    """个股输入包（FR-006 AC6.4）：基本面/行情(best-effort) + 所属行业推断。"""
    # 从持仓里找该 code 的名称/行业线索
    name = code
    industry = ""
    for h in classified.get("by_class", {}).get(ac.EQUITY, {}).get("holdings", []):
        if h.get("code") == code:
            name = h.get("name") or code
            break

    # best-effort 取个股基本面：① AKShare 程序化(优先,可复现) ② Mongo 兜底 ③ 都无则降级
    fundamentals = {"available": False, "note": "未取到个股基本面，分析降级为 LLM 知识 + 可得行情"}
    # ① AKShare 个股硬数据（股价/市值/PE/PB分位/财务/涨幅）—— data-desk 的个股取数能力
    try:
        from app.services.v4 import stock_source
        ak_res = stock_source.build_stock_fundamentals(code)
        if ak_res.get("available"):
            fundamentals = ak_res
            d = ak_res.get("data", {})
            industry = d.get("industry_em") or industry
            name = d.get("name") or name
    except Exception as e:
        fundamentals.setdefault("note", "")
        fundamentals["akshare_error"] = str(e)
    # ② Mongo 兜底（仅当 AKShare 未取到时）
    if not fundamentals.get("available"):
        try:
            from app.core.database import get_mongo_db_sync
            db = get_mongo_db_sync()
            doc = db["stock_basic_info"].find_one({"code": code}) or db["stocks"].find_one({"code": code})
            if doc:
                doc.pop("_id", None)
                industry = doc.get("industry") or industry
                fundamentals = {"available": True, "source": "mongo", "data": {k: v for k, v in doc.items()
                                if k in ("name", "industry", "pe", "pb", "total_mv", "roe")}}
                name = doc.get("name") or name
        except Exception as e:
            fundamentals.setdefault("mongo_error", str(e))

    pack = {
        "code": code,
        "name": name,
        "industry": industry,  # 编排器据此 Read 所属行业 verdict
        "fundamentals": fundamentals,
        "macro_context": macro,
        "data_availability": {"fundamentals": fundamentals["available"], "macro": macro["data_availability"]},
    }
    out = inputs / f"stock_{_safe(code)}.json"
    _write_json(out, pack)
    print(f"  ✓ stock:{code} 输入包 → inputs/{out.name}"
          + (f"（行业={industry}）" if industry else "（未推断出所属行业，agent 将仅按个股数据分析）"))


if __name__ == "__main__":
    sys.exit(main())
