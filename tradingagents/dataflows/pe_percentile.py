"""PE 历史分位计算 — 三市场统一接口

为 CIO 决策卡片提供 `suggested_price` 所需的价格锚点数据。

数据密度因市场而异：
- A 股: BaoStock 每日 PE(TTM)，~1200 数据点，精确分位
- 港股: AKShare 年度 EPS_TTM + 每日股价，~9 数据点
- 美股: yfinance 年度 Basic EPS + 5年价格，~5 数据点
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

logger = logging.getLogger("default")


def _infer_market(code: str) -> str:
    if ".SH" in code or ".SZ" in code:
        return "cn"
    if ".HK" in code:
        return "hk"
    if any(code.endswith(s) for s in (".US", ".L", ".TO")):
        return "us"
    if code.isdigit() and len(code) == 5:
        return "hk"
    if code.isdigit() and len(code) == 6:
        return "cn"
    if code.isalpha() and 1 <= len(code) <= 5:
        return "us"
    return "unknown"


def _percentile(values: list, current: float) -> float | None:
    if not values or current is None:
        return None
    n = sum(1 for v in values if v < current)
    return round(n / len(values) * 100, 1)


def _suggested_judgment(pe: float | None, pct: float | None, pe_range: str | None, ma20: float | None,
                        price: float | None) -> str:
    if pct is not None:
        if pct <= 25:
            pos = "估值偏低"
        elif pct <= 75:
            pos = "估值合理"
        else:
            pos = "估值偏高"
        return f"PE {pe:.1f} 处于历史 {pct:.0f}% 分位，{pos}"
    if ma20 and price:
        if price < ma20 * 0.95:
            return f"现价 ¥{price:.0f} 低于 MA20（¥{ma20:.0f}），短期有支撑"
        elif price > ma20 * 1.05:
            return f"现价 ¥{price:.0f} 高于 MA20（¥{ma20:.0f}），短期溢价"
        return f"现价 ¥{price:.0f} 在 MA20（¥{ma20:.0f}）附近"
    if pe:
        return f"PE(TTM) {pe:.1f}，无历史分位参考"
    return "估值数据不可用"


# ── A 股: BaoStock ───────────────────────────────────────────

def _compute_cn(code: str) -> dict:
    bs = None
    try:
        import baostock as bs
        import pandas as pd

        # Strip .SH/.SZ suffix from Scout-format codes (e.g. "600519.SH" → "600519")
        clean_code = code.replace(".SH", "").replace(".SZ", "").replace(".sh", "").replace(".sz", "")
        bs_code = f"sh.{clean_code}" if clean_code.startswith(("6", "68")) else f"sz.{clean_code}"
        lg = bs.login()
        if lg.error_code != "0":
            logger.warning(f"[PE-CN] BaoStock 登录失败: {lg.error_msg}")
            return _empty_result(code, "cn", "data_unavailable")

        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=5 * 365)).strftime("%Y-%m-%d")

        rs = bs.query_history_k_data_plus(
            code=bs_code,
            fields="date,close,peTTM,pbMRQ",
            start_date=start_date,
            end_date=end_date,
            frequency="d",
            adjustflag="3",
        )

        if rs.error_code != "0":
            logger.warning(f"[PE-CN] BaoStock 查询失败: {rs.error_msg}")
            return _empty_result(code, "cn", "data_unavailable")

        data = rs.data
        if not data or len(data) < 20:
            logger.warning(f"[PE-CN] {code} 数据不足 ({len(data)} 行)")
            return _empty_result(code, "cn", "insufficient_history")

        df = pd.DataFrame(data, columns=["date", "close", "peTTM", "pbMRQ"])
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df["peTTM"] = pd.to_numeric(df["peTTM"], errors="coerce")
        df["pbMRQ"] = pd.to_numeric(df["pbMRQ"], errors="coerce")

        valid = df[df["peTTM"] > 0]
        if len(valid) < 10:
            return _empty_result(code, "cn", "negative_earnings")

        last = valid.iloc[-1]
        current_price = float(last["close"])
        pe_ttm = float(last["peTTM"])
        pb = float(last["pbMRQ"]) if pd.notna(last["pbMRQ"]) else None

        # MA20
        ma20_vals = df["close"].dropna().tail(20)
        ma20 = round(float(ma20_vals.mean()), 2) if len(ma20_vals) >= 5 else None

        # PE 分位
        pe_history = valid["peTTM"].dropna().tolist()
        pct = _percentile(pe_history, pe_ttm)
        pe_min = round(min(pe_history), 2)
        pe_max = round(max(pe_history), 2)
        pe_range = f"{pe_min} - {pe_max}"

        judgment = _suggested_judgment(pe_ttm, pct, pe_range, ma20, current_price)

        return {
            "code": code, "market": "cn",
            "current_price": round(current_price, 2),
            "pe_ttm": round(pe_ttm, 2),
            "pb": round(pb, 2) if pb else None,
            "ma20": ma20,
            "pe_percentile_5y": pct,
            "pe_range_5y": pe_range,
            "pe_percentile_source": "daily",
            "pe_data_points": len(pe_history),
            "judgment": judgment,
        }

    except Exception as e:
        logger.error(f"[PE-CN] {code} 计算失败: {e}")
        return _empty_result(code, "cn", "data_unavailable", str(e))
    finally:
        if bs is not None:
            try:
                bs.logout()
            except Exception:
                pass


# ── 港股: AKShare ────────────────────────────────────────────

def _compute_hk(code: str) -> dict:
    try:
        import akshare as ak
        import pandas as pd

        # 年度 EPS_TTM
        df_fin = ak.stock_financial_hk_analysis_indicator_em(symbol=code)
        if df_fin is None or df_fin.empty:
            return _empty_result(code, "hk", "data_unavailable")

        # 取所有期 EPS_TTM (9 年数据)
        eps_rows = []
        for _, row in df_fin.iterrows():
            eps_val = row.get("EPS_TTM")
            if pd.notna(eps_val) and float(eps_val) > 0:
                eps_rows.append({
                    "date": str(row.get("REPORT_DATE", "")),
                    "eps_ttm": float(eps_val),
                })

        if not eps_rows:
            return _empty_result(code, "hk", "negative_earnings")

        # 按 REORT_DATE 降序排列，确保 [0] 为最新数据
        eps_rows.sort(key=lambda x: x["date"], reverse=True)

        # 每日价格
        try:
            df_price = ak.stock_hk_daily(symbol=code, adjust="qfq")
        except Exception:
            df_price = pd.DataFrame()

        if df_price is None or df_price.empty:
            return _empty_result(code, "hk", "data_unavailable")

        # Normalize price columns
        price_col = "close" if "close" in df_price.columns else (
            "收盘" if "收盘" in df_price.columns else None)
        if price_col is None:
            for col in df_price.columns:
                if col.lower() in ("close", "收盘", "adj close"):
                    price_col = col
                    break
        if price_col is None:
            price_col = df_price.columns[3] if len(df_price.columns) > 3 else df_price.columns[-1]
        df_price["date_clean"] = pd.to_datetime(df_price["date"] if "date" in df_price.columns else df_price.index).strftime("%Y-%m-%d")
        df_price["price"] = pd.to_numeric(df_price[price_col], errors="coerce")

        latest_price = float(df_price["price"].dropna().iloc[-1]) if not df_price["price"].dropna().empty else None
        ma20 = round(float(df_price["price"].dropna().tail(20).mean()), 2) if len(df_price["price"].dropna()) >= 5 else None

        # 根据最近的 EPS_TTM 计算当前 PE
        latest_eps = eps_rows[0]["eps_ttm"]
        pe_ttm = round(latest_price / latest_eps, 2) if latest_price and latest_eps else None

        # 构建历史 PE 数据点：每个年报日期的 PE = 当日股价 / 当期 EPS_TTM
        pe_history = []
        for eps in eps_rows:
            price_at_date = None
            for _, pr in df_price.iterrows():
                if eps["date"] and pr.get("date_clean", "").startswith(eps["date"][:7]):
                    price_at_date = float(pr["price"]) if pd.notna(pr["price"]) else None
                    break
            if price_at_date and price_at_date > 0:
                pe_at = price_at_date / eps["eps_ttm"]
                if 0 < pe_at < 1000:
                    pe_history.append(round(pe_at, 2))

        pct = _percentile(pe_history, pe_ttm) if pe_ttm and len(pe_history) >= 3 else None
        pe_range = f"{min(pe_history):.1f} - {max(pe_history):.1f}" if pe_history else None

        judgment = _suggested_judgment(pe_ttm, pct, pe_range, ma20, latest_price)

        return {
            "code": code, "market": "hk",
            "current_price": round(latest_price, 2) if latest_price else None,
            "pe_ttm": pe_ttm,
            "pb": None,
            "ma20": ma20,
            "pe_percentile_5y": pct,
            "pe_range_5y": pe_range,
            "pe_percentile_source": "annual" if pe_history else "data_unavailable",
            "pe_data_points": len(pe_history),
            "judgment": judgment,
        }

    except Exception as e:
        logger.error(f"[PE-HK] {code} 计算失败: {e}")
        return _empty_result(code, "hk", "data_unavailable", str(e))


# ── 美股: yfinance ───────────────────────────────────────────

def _compute_us(code: str) -> dict:
    try:
        import yfinance as yf
        import pandas as pd

        t = yf.Ticker(code)
        info = t.info
        if not info:
            return _empty_result(code, "us", "data_unavailable")

        # 当前 PE / 价格
        pe_ttm = info.get("trailingPE")
        pb = info.get("priceToBook")
        current_price = info.get("currentPrice") or info.get("regularMarketPrice")

        # MA20 from 1-month history
        hist_1m = t.history(period="1mo")
        ma20 = round(float(hist_1m["Close"].tail(20).mean()), 2) if not hist_1m.empty and len(hist_1m) >= 5 else None

        if current_price is None and not hist_1m.empty:
            current_price = float(hist_1m["Close"].iloc[-1])

        # 年度 EPS 历史
        financials = t.financials
        if financials is None or financials.empty:
            return _empty_result(code, "us", "data_unavailable")

        # Extract annual Basic EPS
        eps_key = None
        for k in ["Basic EPS", "Diluted EPS"]:
            if k in financials.index:
                eps_key = k
                break

        if eps_key is None:
            # Try quarterly
            qf = t.quarterly_financials
            if qf is not None and not qf.empty and "Basic EPS" in qf.index:
                eps_key = "Basic EPS"
                financials = qf

        if eps_key is None:
            return _empty_result(code, "us", "data_unavailable")

        # 5-year daily price history for annual PE computation
        hist_5y = t.history(period="5y")
        pe_history = []

        for col in financials.columns:
            annual_eps = financials.loc[eps_key, col]
            if isinstance(annual_eps, pd.Series):
                annual_eps = annual_eps.iloc[0]
            annual_eps = float(annual_eps) if pd.notna(annual_eps) else None
            if not annual_eps or annual_eps <= 0:
                continue

            # Find approximate price at fiscal year end
            col_date = col if isinstance(col, pd.Timestamp) else pd.Timestamp(col)
            try:
                nearest = hist_5y.iloc[hist_5y.index.get_indexer([col_date], method="nearest")[0]]
                price_at = float(nearest["Close"])
                pe_at = round(price_at / annual_eps, 2)
                if 0 < pe_at < 1000:
                    pe_history.append(pe_at)
            except (IndexError, KeyError):
                continue

        pct = _percentile(pe_history, pe_ttm) if pe_ttm and len(pe_history) >= 3 else None
        pe_range = f"{min(pe_history):.1f} - {max(pe_history):.1f}" if pe_history else None

        judgment = _suggested_judgment(pe_ttm, pct, pe_range, ma20, float(current_price) if current_price else None)

        return {
            "code": code, "market": "us",
            "current_price": round(float(current_price), 2) if current_price else None,
            "pe_ttm": round(float(pe_ttm), 2) if pe_ttm else None,
            "pb": round(float(pb), 2) if pb else None,
            "ma20": ma20,
            "pe_percentile_5y": pct,
            "pe_range_5y": pe_range,
            "pe_percentile_source": "annual" if pe_history else "data_unavailable",
            "pe_data_points": len(pe_history),
            "judgment": judgment,
        }

    except Exception as e:
        logger.error(f"[PE-US] {code} 计算失败: {e}")
        return _empty_result(code, "us", "data_unavailable", str(e))


# ── 统一接口 ──────────────────────────────────────────────────

def _empty_result(code: str, market: str, source: str, error: str = "") -> dict:
    return {
        "code": code, "market": market,
        "current_price": None,
        "pe_ttm": None,
        "pb": None,
        "ma20": None,
        "pe_percentile_5y": None,
        "pe_range_5y": None,
        "pe_percentile_source": source,
        "pe_data_points": 0,
        "judgment": f"数据不可用{f': {error}' if error else ''}",
    }


def compute_pe_context(code: str, market: str = "") -> dict:
    """计算单只标的 PE 历史分位

    Args:
        code: 标的代码 (如 600519, 00700, AAPL)
        market: cn / hk / us，为空时自动推断

    Returns:
        {current_price, pe_ttm, pb, ma20, pe_percentile_5y, pe_range_5y,
         pe_percentile_source, pe_data_points, judgment}
    """
    if not market:
        market = _infer_market(code)

    if market == "cn":
        return _compute_cn(code)
    elif market == "hk":
        return _compute_hk(code)
    elif market == "us":
        return _compute_us(code)
    else:
        return _empty_result(code, market, "unknown_market")


# 非股票类型，无需 PE 估值
_SKIP_INSTRUMENT_TYPES = frozenset({"fund", "etf"})


def enrich_price_context(positions: list, candidates: list) -> dict:
    """批量为持仓和候选标的计算 PE 分位

    Args:
        positions: [{code, market?, instrument_type?, ...}]
        candidates: [{code, market?, instrument_type?, ...}]

    Returns:
        {code: pe_context_dict}
    """
    results = {}
    seen = set()

    for pos in positions:
        code = pos.get("code", "")
        if not code or code in seen:
            continue
        seen.add(code)
        inst_type = pos.get("instrument_type", "stock")
        if inst_type in _SKIP_INSTRUMENT_TYPES:
            results[code] = _empty_result(code, _infer_market(code), "non_stock_instrument")
            continue
        market = pos.get("market", "") or _infer_market(code)
        logger.info(f"[PE] 计算 {code} ({market}) ...")
        results[code] = compute_pe_context(code, market)

    for c in candidates:
        code = c.get("code", "")
        if not code or code in seen:
            continue
        seen.add(code)
        inst_type = c.get("instrument_type", "stock")
        if inst_type in _SKIP_INSTRUMENT_TYPES:
            results[code] = _empty_result(code, _infer_market(code), "non_stock_instrument")
            continue
        market = c.get("market", "") or _infer_market(code)
        logger.info(f"[PE] 计算 {code} ({market}) ...")
        results[code] = compute_pe_context(code, market)

    return results
