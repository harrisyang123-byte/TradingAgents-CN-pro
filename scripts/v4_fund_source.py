"""v4 基金穿透取数脚本 (Level 1, 2026-06-13)

支持取基金重仓股 + 行业分布 + 基金基本信息, 缓存到 data/v4/_funds/<code>.json.

AKShare 接口:
- fund_portfolio_hold_em: 基金持仓明细(前 10 重仓股)
- fund_individual_basic_info_xq / fund_individual_basic_info_em: 基金基本信息
- fund_portfolio_industry_allocation_em: 行业资产配置

沙箱无外网 → 返回 data_status="manual_required" + 标注 schema, 让用户在生产环境跑实数据.

CLI:
  python scripts/v4_fund_source.py 110008      # 取单只
  python scripts/v4_fund_source.py --all       # 用户 holdings 全跑
  python scripts/v4_fund_source.py --status    # 看缓存状态
"""

from __future__ import annotations
import json
import os
import sys
import datetime
from pathlib import Path
from typing import Any, Optional

FUNDS_DIR = Path("data/v4/_funds")
HOLDINGS_FILE = Path("data/v4/_inputs/holdings.json")


def _ensure_dir() -> None:
    FUNDS_DIR.mkdir(parents=True, exist_ok=True)


def _today() -> str:
    return datetime.date.today().isoformat()


# 基金穿透 schema (data 字段定义)
FUND_DATA_SCHEMA: dict[str, str] = {
    # 基本信息
    "fund_code": "基金代码",
    "fund_name": "基金全名",
    "fund_type": "基金类型 (股票型/混合型/债券型/QDII/ETF联接/货币型/商品型)",
    "fund_company": "基金公司",
    "establishment_date": "成立日",
    "asset_size_yi": "最新规模(亿元)",
    "manager": "基金经理",
    "management_fee_pct": "管理费率 %",
    "custodian_fee_pct": "托管费率 %",
    "benchmark": "业绩比较基准",

    # 持仓数据 (Level 1 核心)
    "top_holdings": "前 10 重仓股 [{code, name, weight, industry}]",
    "holdings_as_of": "持仓数据基准日 (季报/半年报披露)",
    "stock_position_pct": "股票仓位 % (相对净值)",
    "bond_position_pct": "债券仓位 %",
    "cash_position_pct": "现金仓位 %",

    # 行业分布
    "industry_exposure": "行业暴露 {半导体: 12%, 新能源: 8%, ...}",
    "industry_top3": "前 3 大行业 [{industry, weight}]",

    # 风格 (Level 2 用,Level 1 占位)
    "style_size": "规模风格 (大盘/中盘/小盘)",
    "style_growth_value": "成长价值风格",
}


def _try_fetch_akshare(code: str) -> dict[str, Any]:
    """用 AKShare 取真数据;失败返回 None"""
    try:
        import akshare as ak
    except ImportError:
        return {"available": False, "note": "akshare 未安装"}

    out: dict[str, Any] = {
        "fund_code": code,
        "fetched_at": _today(),
        "source": "akshare",
        "_errors": [],
    }

    # 1. 基本信息(雪球或东财)
    try:
        df = ak.fund_individual_basic_info_xq(symbol=code)
        if df is not None and not df.empty:
            kv = dict(zip(df["item"], df["value"]))
            out["fund_name"] = kv.get("基金全称", kv.get("基金简称", ""))
            out["fund_type"] = kv.get("基金类型", "")
            out["fund_company"] = kv.get("基金公司", "")
            out["establishment_date"] = str(kv.get("成立日期", ""))
            out["manager"] = kv.get("基金经理", "")
            # 规模数据可能在另一个接口
    except Exception as e:
        out["_errors"].append(f"basic_info:{type(e).__name__}")

    # 2. 重仓股(季报)
    try:
        df = ak.fund_portfolio_hold_em(symbol=code, date=str(datetime.date.today().year))
        if df is not None and not df.empty:
            # 取最新一期的前 10
            latest = df.head(10)
            holdings = []
            for _, row in latest.iterrows():
                holdings.append({
                    "code": str(row.get("股票代码", "")),
                    "name": row.get("股票名称", ""),
                    "weight": float(row.get("占净值比例", 0) or 0),
                    "shares": int(row.get("持股数", 0) or 0) if "持股数" in row else None,
                })
            out["top_holdings"] = holdings
            out["holdings_as_of"] = str(df.iloc[0].get("季度", ""))
    except Exception as e:
        out["_errors"].append(f"holdings:{type(e).__name__}")

    # 3. 行业分布
    try:
        df = ak.fund_portfolio_industry_allocation_em(symbol=code,
                                                      date=str(datetime.date.today().year))
        if df is not None and not df.empty:
            industry_exposure = {}
            for _, row in df.head(20).iterrows():
                industry = row.get("行业类别", row.get("行业名称", ""))
                weight = float(row.get("占净值比例", 0) or 0)
                if industry and weight > 0:
                    industry_exposure[industry] = weight
            out["industry_exposure"] = industry_exposure
            top3 = sorted(industry_exposure.items(), key=lambda x: -x[1])[:3]
            out["industry_top3"] = [{"industry": k, "weight": v} for k, v in top3]
    except Exception as e:
        out["_errors"].append(f"industry:{type(e).__name__}")

    # 判定可用性
    has_holdings = bool(out.get("top_holdings"))
    has_industry = bool(out.get("industry_exposure"))
    if has_holdings or has_industry:
        out["available"] = True
        out["data_status"] = "verified"
    else:
        out["available"] = False
        out["data_status"] = "fetch_failed"

    return out


def fetch_one(code: str, force: bool = False) -> dict[str, Any]:
    """取单只基金穿透数据.

    优先级:
    1. holdings.json 里的 `_fund_passthrough` 字段(用户本地填充,沙箱友好) ← 推荐
    2. data/v4/_funds/<code>.json 缓存(7 天内有效)
    3. AKShare 联网取数(沙箱无外网会失败)
    4. fallback 返回 manual_required schema 占位
    """
    _ensure_dir()
    cache_path = FUNDS_DIR / f"{code}.json"

    # 1. 先看 holdings.json 是否已填 _fund_passthrough(用户本地数据)
    if HOLDINGS_FILE.exists():
        try:
            h = json.loads(HOLDINGS_FILE.read_text(encoding="utf-8"))
            for p in h.get("positions", []):
                if p.get("code") == code and p.get("_fund_passthrough"):
                    fp = p["_fund_passthrough"]
                    out = {
                        "fund_code": code,
                        "fund_name": p.get("name", ""),
                        "fetched_at": _today(),
                        "available": True,
                        "data_status": fp.get("_data_status", "estimated"),
                        "source": "holdings_user_filled",
                        **fp,
                    }
                    cache_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
                    return out
        except Exception:
            pass

    # 2. 看缓存
    if cache_path.exists() and not force:
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            fetched = cached.get("fetched_at", "")
            if fetched and fetched >= str(datetime.date.today() - datetime.timedelta(days=7)):
                return cached
        except Exception:
            pass

    # 3. 尝试 AKShare 取真数据
    data = _try_fetch_akshare(code)

    if not data.get("available"):
        # 沙箱无外网或失败 → 返回 schema 占位
        data = {
            "fund_code": code,
            "fetched_at": _today(),
            "available": False,
            "data_status": "manual_required",
            "note": (
                "沙箱无外网 AKShare 失败. 生产环境跑此脚本可获取真数据. "
                "schema 见 FUND_DATA_SCHEMA. 本次输出含占位字段供 classifier/aggregator 消费."
            ),
            "schema": FUND_DATA_SCHEMA,
            "errors": data.get("_errors", []),
        }

    cache_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def fetch_holdings_funds() -> list[dict[str, Any]]:
    """从 holdings.json 读所有基金代码,逐个取数"""
    if not HOLDINGS_FILE.exists():
        print(f"❌ {HOLDINGS_FILE} 不存在", file=sys.stderr)
        return []

    h = json.loads(HOLDINGS_FILE.read_text(encoding="utf-8"))
    funds = [p for p in h.get("positions", []) if p.get("instrument_type") in ("fund", "etf")]
    print(f"📊 holdings 中识别到 {len(funds)} 只基金/ETF, 开始取数")

    results = []
    for i, p in enumerate(funds, 1):
        code = p.get("code", "")
        name = p.get("name", "")
        if not code:
            continue
        print(f"  [{i}/{len(funds)}] {code} {name[:25]}", end=" ")
        data = fetch_one(code)
        status = data.get("data_status", "?")
        print(f"→ {status}")
        results.append(data)

    return results


def status_summary() -> None:
    """汇总缓存状态"""
    _ensure_dir()
    files = list(FUNDS_DIR.glob("*.json"))
    print(f"📊 _funds 缓存: {len(files)} 文件")
    by_status: dict[str, int] = {}
    for f in files:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            s = d.get("data_status", "unknown")
            by_status[s] = by_status.get(s, 0) + 1
        except Exception:
            by_status["parse_error"] = by_status.get("parse_error", 0) + 1
    for s, n in sorted(by_status.items()):
        print(f"  {s}: {n}")


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if not argv:
        print(__doc__)
        return 1

    if "--status" in argv:
        status_summary()
        return 0

    if "--all" in argv:
        force = "--force" in argv
        results = fetch_holdings_funds()
        verified = sum(1 for r in results if r.get("data_status") == "verified")
        manual = sum(1 for r in results if r.get("data_status") == "manual_required")
        print(f"\n✅ 完成. 共 {len(results)} 只 / verified={verified} / manual_required={manual}")
        return 0

    # 取单只
    code = argv[0]
    force = "--force" in argv
    data = fetch_one(code, force=force)
    print(json.dumps(data, ensure_ascii=False, indent=2)[:1000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
