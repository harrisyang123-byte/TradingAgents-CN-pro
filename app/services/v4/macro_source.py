"""v4 宏观硬数据源 — AKShare 程序化取数（替代纯手工联网）。

档 A 的 22 个公共宏观指标里，**国内基本面 / 利率硬数据**（LPR、国债收益率、
CPI、PPI、PMI、M2）由 AKShare 官方口径接口程序化拉取——可复现、带发布日期、
不会撞搜索引擎缓存的陈旧文本（如 cn10y 曾被搜成过时的 2.7%，实际 1.71%）。

**海外 / 实时 / 大宗**（US 市场、汇率、原油黄金铜、风险情绪）AKShare 时效性差
或不覆盖，仍由第 2 阶段 Agent 联网补齐——本模块只把它们留成 missing 骨架。

设计铁律（对齐 data-desk「降级而非崩溃」）：
- 每个接口独立 try/except；akshare 未安装 / 无网 / 接口变更 → 该指标保持 missing，
  绝不抛异常中断采集。
- 只取数、标 verified + 来源接口 + as_of 日期，不做任何投资研判。
- 不编造：取不到就 missing。
"""

from __future__ import annotations

from typing import Any

# 22 个指标的元数据：单位、默认 note、是否仅联网可得（akshare 不覆盖）。
# 顺序与 v4-data-desk.md 档 A 清单一致。
INDICATOR_META: dict[str, dict[str, Any]] = {
    # 货币 / 利率
    "lpr_1y": {"unit": "%"},
    "lpr_5y": {"unit": "%"},
    "reverse_repo_7d": {"unit": "%", "web_only": True, "note": "7天逆回购政策利率；AKShare 无干净接口，需联网"},
    "cn10y": {"unit": "%"},
    "term_spread": {"unit": "%", "note": "10Y-2Y 期限利差"},
    # 物价 / 景气
    "cpi_yoy": {"unit": "%"},
    "ppi_yoy": {"unit": "%"},
    "pmi_mfg": {"unit": "index"},
    "pmi_nonmfg": {"unit": "index"},
    # 信用 / 流动性
    "tsf_yoy": {"unit": "%", "web_only": True, "note": "社融存量同比；AKShare shrzgm 为增量口径，需联网取存量同比"},
    "m2_yoy": {"unit": "%"},
    "margin_balance": {"unit": "万亿元", "note": "两融余额（沪深合计）"},
    # 汇率
    "usdcny": {"unit": "CNY/USD", "web_only": True, "note": "人民币兑美元；实时，走联网"},
    "dxy": {"unit": "index", "web_only": True, "note": "美元指数；实时，走联网"},
    # 跨市场 / 海外敞口
    "us10y": {"unit": "%"},
    "fed_funds": {"unit": "%", "web_only": True, "note": "美联储目标利率；走联网"},
    "sp500": {"unit": "point", "web_only": True, "note": "标普500；实时，走联网"},
    "nasdaq": {"unit": "point", "web_only": True, "note": "纳斯达克综指；实时，走联网"},
    # 风险情绪
    "vix": {"unit": "index", "web_only": True, "note": "VIX 恐慌指数；实时，走联网"},
    # 大宗 / 避险
    "brent": {"unit": "USD/bbl", "web_only": True, "note": "布伦特原油；实时，走联网"},
    "gold": {"unit": "USD/oz", "web_only": True, "note": "COMEX/伦敦金；实时，走联网"},
    "copper": {"unit": "USD/t", "web_only": True, "note": "LME铜；实时，走联网"},
}


def _skeleton() -> dict[str, dict[str, Any]]:
    """生成 22 指标全 missing 骨架，带单位与默认 note。"""
    out: dict[str, dict[str, Any]] = {}
    for key, meta in INDICATOR_META.items():
        item: dict[str, Any] = {"value": None, "status": "missing"}
        if meta.get("unit"):
            item["unit"] = meta["unit"]
        if meta.get("note"):
            item["note"] = meta["note"]
        out[key] = item
    return out


def _ym(month_label: str) -> str:
    """'2026年04月份' → '2026-04'；解析失败返回原串。"""
    try:
        s = str(month_label)
        y = s.split("年")[0]
        m = s.split("年")[1].split("月")[0]
        return f"{int(y):04d}-{int(m):02d}"
    except Exception:
        return str(month_label)


def _set(inds: dict, key: str, value, as_of: str, interface: str, note: str = "") -> None:
    meta = INDICATOR_META.get(key, {})
    item = {
        "value": value,
        "status": "verified",
        "as_of": as_of,
        "source_url": f"akshare:{interface}",
    }
    if meta.get("unit"):
        item["unit"] = meta["unit"]
    if note:
        item["note"] = note
    inds[key] = item


def _notna(v) -> bool:
    try:
        import math
        return v is not None and not (isinstance(v, float) and math.isnan(v))
    except Exception:
        return v is not None


# ---- 逐接口取数（每个独立 try/except，失败留 missing） ----

def _fill_lpr(ak, inds: dict, filled: list) -> None:
    try:
        df = ak.macro_china_lpr()
        row = df.iloc[-1]  # 升序，末行最新
        as_of = str(row["TRADE_DATE"])[:10]
        if _notna(row.get("LPR1Y")):
            _set(inds, "lpr_1y", round(float(row["LPR1Y"]), 4), as_of, "macro_china_lpr")
            filled.append("lpr_1y")
        if _notna(row.get("LPR5Y")):
            _set(inds, "lpr_5y", round(float(row["LPR5Y"]), 4), as_of, "macro_china_lpr")
            filled.append("lpr_5y")
    except Exception as e:
        inds["lpr_1y"].setdefault("note", f"akshare 取数失败: {type(e).__name__}")


def _fill_bond(ak, inds: dict, filled: list) -> None:
    """bond_zh_us_rate 一接口给 cn10y / term_spread / us10y（日频）。"""
    try:
        df = ak.bond_zh_us_rate()
        # 中国列：取最后一个非空的 10Y
        cn = df.dropna(subset=["中国国债收益率10年"])
        if not cn.empty:
            r = cn.iloc[-1]
            as_of = str(r["日期"])[:10]
            _set(inds, "cn10y", round(float(r["中国国债收益率10年"]), 4), as_of, "bond_zh_us_rate")
            filled.append("cn10y")
            if _notna(r.get("中国国债收益率10年-2年")):
                _set(inds, "term_spread", round(float(r["中国国债收益率10年-2年"]), 4), as_of,
                     "bond_zh_us_rate", "10Y-2Y 期限利差")
                filled.append("term_spread")
        # 美国列：单独取最后非空（通常比中国列滞后 1 个交易日）
        us = df.dropna(subset=["美国国债收益率10年"])
        if not us.empty:
            r = us.iloc[-1]
            _set(inds, "us10y", round(float(r["美国国债收益率10年"]), 4), str(r["日期"])[:10],
                 "bond_zh_us_rate", "美10年期国债，服务海外敞口")
            filled.append("us10y")
    except Exception as e:
        inds["cn10y"].setdefault("note", f"akshare 取数失败: {type(e).__name__}")


def _fill_cpi(ak, inds: dict, filled: list) -> None:
    try:
        df = ak.macro_china_cpi()  # 降序，head 最新
        r = df.iloc[0]
        v = r["全国-同比增长"]
        if _notna(v):
            _set(inds, "cpi_yoy", round(float(v), 2), _ym(r["月份"]), "macro_china_cpi", "全国 CPI 当月同比")
            filled.append("cpi_yoy")
    except Exception as e:
        inds["cpi_yoy"].setdefault("note", f"akshare 取数失败: {type(e).__name__}")


def _fill_ppi(ak, inds: dict, filled: list) -> None:
    try:
        df = ak.macro_china_ppi()  # 降序，head 最新
        r = df.iloc[0]
        v = r["当月同比增长"]
        if _notna(v):
            _set(inds, "ppi_yoy", round(float(v), 2), _ym(r["月份"]), "macro_china_ppi", "工业生产者出厂价格当月同比")
            filled.append("ppi_yoy")
    except Exception as e:
        inds["ppi_yoy"].setdefault("note", f"akshare 取数失败: {type(e).__name__}")


def _fill_pmi(ak, inds: dict, filled: list) -> None:
    try:
        df = ak.macro_china_pmi()  # 降序，head 最新
        r = df.iloc[0]
        as_of = _ym(r["月份"])
        if _notna(r.get("制造业-指数")):
            _set(inds, "pmi_mfg", round(float(r["制造业-指数"]), 2), as_of, "macro_china_pmi", "官方 NBS 口径制造业 PMI")
            filled.append("pmi_mfg")
        if _notna(r.get("非制造业-指数")):
            _set(inds, "pmi_nonmfg", round(float(r["非制造业-指数"]), 2), as_of, "macro_china_pmi", "官方 NBS 口径非制造业 PMI")
            filled.append("pmi_nonmfg")
    except Exception as e:
        inds["pmi_mfg"].setdefault("note", f"akshare 取数失败: {type(e).__name__}")


def _fill_m2(ak, inds: dict, filled: list) -> None:
    try:
        df = ak.macro_china_money_supply()  # 降序，head 最新
        r = df.iloc[0]
        v = r["货币和准货币(M2)-同比增长"]
        if _notna(v):
            _set(inds, "m2_yoy", round(float(v), 2), _ym(r["月份"]), "macro_china_money_supply", "M2 同比")
            filled.append("m2_yoy")
    except Exception as e:
        inds["m2_yoy"].setdefault("note", f"akshare 取数失败: {type(e).__name__}")


def _fill_margin(ak, inds: dict, filled: list) -> None:
    """两融余额 = 上交所 + 深交所融资融券余额（元 → 万亿元）。best-effort，任一缺失则降级。"""
    try:
        import datetime
        ed = datetime.date.today()
        sd = ed - datetime.timedelta(days=15)
        sse_bal = szse_bal = None
        as_of = None
        try:
            df = ak.stock_margin_sse(start_date=sd.strftime("%Y%m%d"), end_date=ed.strftime("%Y%m%d"))
            if df is not None and not df.empty:
                r = df.iloc[-1]
                sse_bal = float(r["融资融券余额"])
                as_of = str(r["信用交易日期"])[:10] if "信用交易日期" in df.columns else None
        except Exception:
            pass
        try:
            df2 = ak.stock_margin_szse(date=ed.strftime("%Y%m%d"))
            if df2 is not None and not df2.empty:
                col = next((c for c in df2.columns if "融资融券余额" in str(c)), None)
                if col:
                    szse_bal = float(df2[col].iloc[0])
        except Exception:
            pass
        if sse_bal is not None:
            total = sse_bal + (szse_bal or 0)
            note = "沪深合计" if szse_bal is not None else "仅上交所（深交所当日未取到，偏低）"
            _set(inds, "margin_balance", round(total / 1e12, 4), as_of or ed.strftime("%Y-%m-%d"),
                 "stock_margin_sse+szse", note)
            filled.append("margin_balance")
    except Exception as e:
        inds["margin_balance"].setdefault("note", f"akshare 取数失败: {type(e).__name__}")


def build_macro_indicators() -> tuple[dict, list, str | None]:
    """返回 (indicators 22 指标 dict, akshare 已填充的 key 列表, akshare 不可用原因或 None)。"""
    inds = _skeleton()
    filled: list[str] = []
    try:
        import akshare as ak  # type: ignore
    except Exception as e:  # noqa: BLE001
        return inds, filled, f"akshare 未安装/不可用: {type(e).__name__}"

    _fill_lpr(ak, inds, filled)
    _fill_bond(ak, inds, filled)
    _fill_cpi(ak, inds, filled)
    _fill_ppi(ak, inds, filled)
    _fill_pmi(ak, inds, filled)
    _fill_m2(ak, inds, filled)
    _fill_margin(ak, inds, filled)
    return inds, filled, None
