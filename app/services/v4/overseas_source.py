"""v4 海外个股硬数据源 — 美股 / 港股 程序化取数（data-desk 海外能力）。

定位：补 `stock_source.py`（仅 A股 AKShare）的空白。用户核心诉求——
「国内信息别人都知道了，要更新的外国信息」赚信息差，前提是能程序化取到
海外 verified 硬数据，而非靠 LLM 训练记忆（违反 RULE-DATA-VERIFIED 红线）。

数据源（均免费、可程序化、带可追溯 URL）：
- 主源 yfinance（Yahoo Finance）：美股 / 港股 / 全球股价·市值·PE·PB·财务，无需 API key
- 备源 stooq（CSV 直拉）：yfinance 限流(429)时的价格兜底，无需 key

红线遵守（AGENTS.md RULE-DATA-VERIFIED）：
- 每个数字字段带 `*_source`（含 URL/接口名），可被 v4_unit_cli.py 契约校验追溯
- 取不到一律标 missing / available=False，**绝不编造、绝不用训练记忆填**
- 库未装 / 无网 / 限流 → 降级 available=False + note，绝不抛异常

代码规范：
- 美股：字母代码（AAPL / NVDA / TSM）
- 港股：5 位数字 + `.HK`（00700.HK）或裸 5 位（00700 → 自动补 .HK）
"""

from __future__ import annotations

import datetime
import re
from typing import Any

_YF_BASE = "https://finance.yahoo.com/quote"
_STOOQ_BASE = "https://stooq.com/q/d/l"


def _today() -> str:
    return datetime.date.today().strftime("%Y-%m-%d")


def _safe_float(v) -> float | None:
    try:
        import math
        f = float(v)
        return None if math.isnan(f) else f
    except Exception:
        return None


def classify_market(code: str) -> str:
    """识别市场：a_share / hk / us / unknown。"""
    c = (code or "").strip().upper()
    if c.isdigit() and len(c) == 6:
        return "a_share"
    if c.endswith(".HK") or (c.isdigit() and len(c) == 5):
        return "hk"
    if re.fullmatch(r"[A-Z]{1,5}(\.[A-Z]{1,3})?", c):
        return "us"
    return "unknown"


def _yf_symbol(code: str, market: str) -> str:
    """规整为 yfinance symbol。港股裸 5 位补 .HK；美股原样。"""
    c = (code or "").strip().upper()
    if market == "hk":
        if c.endswith(".HK"):
            return c
        return c.zfill(4) + ".HK" if c.isdigit() else c + ".HK"
    return c


def _fetch_yfinance(code: str, market: str, out: dict) -> bool:
    """主源：yfinance。取现价/市值/PE/PB/财务比率。成功返回 True。"""
    try:
        import yfinance as yf  # type: ignore
    except Exception as e:  # noqa: BLE001
        out.setdefault("_errors", []).append(f"yfinance_import:{type(e).__name__}")
        return False

    sym = _yf_symbol(code, market)
    src_url = f"{_YF_BASE}/{sym}"
    try:
        t = yf.Ticker(sym)
        info = {}
        # yfinance 新版 .info 可能抛/限流；fast_info 更稳，先取 fast_info
        try:
            fi = t.fast_info
            out["price"] = _safe_float(getattr(fi, "last_price", None))
            out["total_mv"] = _safe_float(getattr(fi, "market_cap", None))
            out["currency"] = getattr(fi, "currency", None)
        except Exception as e:  # noqa: BLE001
            out.setdefault("_errors", []).append(f"yf_fastinfo:{type(e).__name__}")
        # .info 取估值/财务比率（限流时整体 try）
        try:
            info = t.info or {}
        except Exception as e:  # noqa: BLE001
            out.setdefault("_errors", []).append(f"yf_info:{type(e).__name__}")
        if info:
            out["name"] = info.get("shortName") or info.get("longName") or out.get("name")
            out["price"] = out.get("price") or _safe_float(info.get("currentPrice"))
            out["total_mv"] = out.get("total_mv") or _safe_float(info.get("marketCap"))
            out["pe_ttm"] = _safe_float(info.get("trailingPE"))
            out["pe_forward"] = _safe_float(info.get("forwardPE"))
            out["pb"] = _safe_float(info.get("priceToBook"))
            out["dividend_yield"] = _safe_float(info.get("dividendYield"))
            out["roe"] = _safe_float(info.get("returnOnEquity"))
            out["profit_margin"] = _safe_float(info.get("profitMargins"))
            out["revenue_growth"] = _safe_float(info.get("revenueGrowth"))
            out["sector"] = info.get("sector")
            out["industry_yf"] = info.get("industry")
            out["currency"] = out.get("currency") or info.get("currency")
        out["price_date"] = _today()
        out["_source_url"] = src_url
        # 关键字段命中即算成功
        return any(out.get(k) is not None for k in ("price", "pe_ttm", "total_mv"))
    except Exception as e:  # noqa: BLE001
        out.setdefault("_errors", []).append(f"yfinance:{type(e).__name__}")
        return False


def _fetch_stooq_price(code: str, market: str, out: dict) -> bool:
    """备源：stooq CSV 直拉收盘价（yfinance 拿不到价格时兜底）。

    stooq symbol：美股 `aapl.us`，港股 `0700.hk`。
    """
    if out.get("price") is not None:
        return False
    try:
        import csv
        import io
        import urllib.request

        c = (code or "").strip().upper().replace(".HK", "")
        if market == "us":
            sym = c.lower() + ".us"
        elif market == "hk":
            sym = (c.zfill(4) if c.isdigit() else c).lower() + ".hk"
        else:
            return False
        url = f"{_STOOQ_BASE}/?s={sym}&i=d"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:  # noqa: S310
            text = resp.read().decode("utf-8", errors="ignore")
        rows = list(csv.DictReader(io.StringIO(text)))
        if rows and rows[-1].get("Close"):
            out["price"] = _safe_float(rows[-1]["Close"])
            out["price_date"] = rows[-1].get("Date") or _today()
            out["price_source"] = f"stooq:{sym}"
            out["_stooq_url"] = url
            return out["price"] is not None
    except Exception as e:  # noqa: BLE001
        out.setdefault("_errors", []).append(f"stooq:{type(e).__name__}")
    return False


def build_overseas_fundamentals(code: str) -> dict[str, Any]:
    """取美股/港股个股硬数据。签名与 stock_source.build_stock_fundamentals 同构。

    返回 {available, data{...}, note, errors, source}。
    失败/A股/不可用 → available=False + note，绝不抛异常。
    """
    market = classify_market(code)
    if market == "a_share":
        return {"available": False, "note": f"A股代码（{code}）走 stock_source(AKShare)，不在 overseas_source"}
    if market == "unknown":
        return {"available": False, "note": f"无法识别市场（{code}）；需主 agent 联网核实"}

    data: dict[str, Any] = {"code": code, "market": market, "as_of": _today(), "source": "yfinance"}
    ok = _fetch_yfinance(code, market, data)
    if data.get("price") is None:
        # 价格兜底走 stooq
        if _fetch_stooq_price(code, market, data):
            ok = True

    errors = data.pop("_errors", [])
    verified_keys = [k for k in ("price", "pe_ttm", "pe_forward", "pb", "total_mv", "roe") if data.get(k) is not None]
    return {
        "available": ok,
        "data": data if ok else {},
        "verified_fields": verified_keys,
        "note": (
            f"海外个股硬数据程序化取得（yfinance/stooq），verified 字段={verified_keys}；"
            "5 力/竞争/TAM 等仍需主 agent 联网 web_search 补，缺失标 missing 不编造"
            if ok else
            f"海外个股取数未拿到关键字段（yfinance 未装/限流/无网），降级需联网核实；errors={errors}"
        ),
        "errors": errors,
        "source": data.get("source", "yfinance"),
    }


def build_any_stock_fundamentals(code: str) -> dict[str, Any]:
    """统一入口：A股 → stock_source；美股/港股 → overseas_source。

    供 collect_v4 / data-desk 调用，自动按市场路由，调用方无需判断。
    """
    market = classify_market(code)
    if market == "a_share":
        try:
            from app.services.v4 import stock_source
            return stock_source.build_stock_fundamentals(code)
        except Exception as e:  # noqa: BLE001
            return {"available": False, "note": f"stock_source 不可用: {type(e).__name__}"}
    return build_overseas_fundamentals(code)
