"""市场扫描工具函数 — AKShare (A股) + yfinance (港股/美股)

L1 工具（行业/宏观扫描）：
  - get_industry_rankings(market)
  - get_sector_fund_flows(market)
  - get_macro_indicators(market)

L2 工具（标的筛选）：
  - get_industry_constituents(industry, market)
  - get_company_profile(code, market)
  - get_financial_summary(code, market)
  - get_stock_quotes(code, market)
  - get_fund_rankings(fund_type, market)
"""

from langchain_core.tools import tool


# ── L1 工具 ────────────────────────────────────────────


@tool
def get_industry_rankings(market: str = "cn") -> dict:
    """获取行业/板块涨跌幅排名，识别当前市场热点和冷门方向。

    参数 market:
      - "cn": A股（AKShare 同花顺行业板块）
      - "hk": 港股（yfinance 恒生行业指数）
      - "us": 美股（yfinance S&P 500 sector ETFs）
    """
    if market == "cn":
        return _get_industry_rankings_cn()
    elif market in ("hk", "us"):
        return _get_industry_rankings_yf(market)
    return {"error": f"不支持的市场: {market}", "market": market, "fallback": True}


@tool
def get_sector_fund_flows(market: str = "cn") -> dict:
    """获取行业资金流向（主力净流入/流出），判断资金偏好。

    参数 market: "cn"（A股） / "hk" / "us"
    注意：港股/美股无公开免费的资金流向数据，非 cn 市场返回降级结果。
    """
    if market == "cn":
        return _get_sector_fund_flows_cn()
    return {
        "market": market,
        "fallback": True,
        "note": f"{market} 市场无公开免费的资金流向数据，请基于行业涨跌幅和宏观指标判断资金偏好",
        "data": [],
    }


@tool
def get_macro_indicators(market: str = "cn") -> dict:
    """获取宏观经济指标：大盘指数、利率、汇率。

    参数 market: "cn"（上证/深证/创业板） / "hk"（恒生） / "us"（S&P 500/Nasdaq/Dow）
    """
    if market == "cn":
        return _get_macro_indicators_cn()
    elif market in ("hk", "us"):
        return _get_macro_indicators_yf(market)
    return {"error": f"不支持的市场: {market}", "market": market, "fallback": True}


# ── L2 工具 ────────────────────────────────────────────


@tool
def get_industry_constituents(industry: str, market: str = "cn") -> dict:
    """获取指定行业/板块的成分股列表。

    参数:
      industry: 行业名称（如 "白酒"、"银行"、"新能源"）
      market: "cn" / "hk" / "us"
    """
    if market == "cn":
        return _get_industry_constituents_cn(industry)
    return {
        "industry": industry,
        "market": market,
        "fallback": True,
        "note": f"{market} 市场成分股查询请用 get_company_profile 逐只获取",
        "constituents": [],
    }


@tool
def get_company_profile(code: str, market: str = "cn") -> dict:
    """获取公司概况：主营业务、行业分类、上市时间、市值。

    参数:
      code: 股票代码（A股如 "600519"，港股如 "00700"，美股如 "AAPL"）
      market: "cn" / "hk" / "us"
    """
    if market == "cn":
        return _get_company_profile_cn(code)
    elif market in ("hk", "us"):
        return _get_company_profile_yf(code, market)
    return {"error": f"不支持的市场: {market}", "code": code, "fallback": True}


@tool
def get_financial_summary(code: str, market: str = "cn") -> dict:
    """获取财务摘要：PE、PB、ROE、营收增速、净利润率。

    参数:
      code: 股票代码
      market: "cn" / "hk" / "us"
    """
    if market == "cn":
        return _get_financial_summary_cn(code)
    elif market in ("hk", "us"):
        return _get_financial_summary_yf(code, market)
    return {"error": f"不支持的市场: {market}", "code": code, "fallback": True}


@tool
def get_stock_quotes(code: str, market: str = "cn") -> dict:
    """获取实时行情：最新价、涨跌幅、成交量、历史价格走势。

    参数:
      code: 股票代码
      market: "cn" / "hk" / "us"
    """
    if market == "cn":
        return _get_stock_quotes_cn(code)
    elif market in ("hk", "us"):
        return _get_stock_quotes_yf(code, market)
    return {"error": f"不支持的市场: {market}", "code": code, "fallback": True}


@tool
def get_fund_rankings(fund_type: str = "股票型", market: str = "cn") -> dict:
    """获取基金/ETF 同类排名和基本信息。

    参数:
      fund_type: 基金类型（"股票型" / "混合型" / "指数型" / "ETF"）
      market: "cn"（AKShare 公募基金） / "hk" / "us"（yfinance ETF）
    """
    if market == "cn":
        return _get_fund_rankings_cn(fund_type)
    elif market in ("hk", "us"):
        return _get_fund_rankings_yf(fund_type, market)
    return {"error": f"不支持的市场: {market}", "fallback": True}


# ── A股实现 (AKShare) ──────────────────────────────────


def _get_industry_rankings_cn() -> dict:
    try:
        import akshare as ak
        df = ak.stock_board_industry_name_ths()
        if df is None or df.empty:
            return {"market": "cn", "fallback": True, "note": "AKShare 返回空数据", "industries": []}
        top_col = df.columns[0]
        rankings = df.nlargest(30, "涨跌幅")[[top_col, "涨跌幅", "成交量"]].to_dict(orient="records")
        return {"market": "cn", "source": "同花顺行业板块", "industries": rankings}
    except Exception as e:
        return {"market": "cn", "fallback": True, "error": str(e), "note": "AKShare 行业数据不可用"}


def _get_sector_fund_flows_cn() -> dict:
    try:
        import akshare as ak
        df = ak.stock_sector_fund_flow_rank(indicator="今日", sector_type="行业资金流向")
        if df is None or df.empty:
            return {"market": "cn", "fallback": True, "note": "资金流向数据为空", "data": []}
        flows = df.head(20).to_dict(orient="records")
        return {"market": "cn", "source": "东方财富行业资金流向", "data": flows}
    except Exception as e:
        return {"market": "cn", "fallback": True, "error": str(e), "note": "资金流向数据不可用"}


def _get_macro_indicators_cn() -> dict:
    result = {"market": "cn", "indices": {}, "fallback": False}
    try:
        import akshare as ak
        df = ak.stock_zh_index_daily(symbol="sh000001")
        if df is not None and not df.empty:
            latest = df.iloc[-1]
            result["indices"]["上证指数"] = {"close": float(latest["close"]), "date": str(latest.name)}
    except Exception as e:
        result["indices"]["上证指数"] = {"error": str(e)}
    try:
        import akshare as ak
        df = ak.stock_zh_index_daily(symbol="sz399006")
        if df is not None and not df.empty:
            latest = df.iloc[-1]
            result["indices"]["创业板指"] = {"close": float(latest["close"]), "date": str(latest.name)}
    except Exception:
        pass
    if not result["indices"]:
        result["fallback"] = True
        result["note"] = "A股指数数据不可用"
    return result


def _get_industry_constituents_cn(industry: str) -> dict:
    try:
        import akshare as ak
        df = ak.stock_board_industry_info_ths(symbol=industry)
        if df is None or df.empty:
            return {"industry": industry, "market": "cn", "constituents": [], "fallback": True}
        constituents = df[["code", "name"]].head(50).to_dict(orient="records")
        return {"industry": industry, "market": "cn", "constituents": constituents}
    except Exception as e:
        return {"industry": industry, "market": "cn", "fallback": True, "error": str(e), "constituents": []}


def _get_company_profile_cn(code: str) -> dict:
    try:
        import akshare as ak
        df = ak.stock_individual_info_em(symbol=code)
        if df is None or df.empty:
            return {"code": code, "market": "cn", "fallback": True, "note": "未找到公司信息"}
        info = {}
        for _, row in df.iterrows():
            info[row["item"]] = row["value"]
        return {"code": code, "market": "cn", "profile": info}
    except Exception as e:
        return {"code": code, "market": "cn", "fallback": True, "error": str(e)}


def _get_financial_summary_cn(code: str) -> dict:
    try:
        import akshare as ak
        df = ak.stock_individual_analysis_em(symbol=code)
        if df is None or df.empty:
            return {"code": code, "market": "cn", "fallback": True, "note": "未找到财务数据"}
        financial = df.head(20).to_dict(orient="records")
        return {"code": code, "market": "cn", "financial": financial}
    except Exception as e:
        return {"code": code, "market": "cn", "fallback": True, "error": str(e)}


def _get_stock_quotes_cn(code: str) -> dict:
    try:
        import akshare as ak
        df = ak.stock_zh_a_spot_em()
        if df is None or df.empty:
            return {"code": code, "market": "cn", "fallback": True, "note": "行情数据为空"}
        match = df[df["代码"] == code]
        if match.empty:
            return {"code": code, "market": "cn", "fallback": True, "note": f"未找到代码 {code}"}
        row = match.iloc[0]
        return {
            "code": code,
            "market": "cn",
            "quote": {
                "name": str(row.get("名称", "")),
                "price": float(row.get("最新价", 0)),
                "change_pct": float(row.get("涨跌幅", 0)),
                "volume": float(row.get("成交量", 0)),
                "turnover": float(row.get("成交额", 0)),
                "pe": float(row.get("市盈率-动态", 0)) if row.get("市盈率-动态") else None,
            },
        }
    except Exception as e:
        return {"code": code, "market": "cn", "fallback": True, "error": str(e)}


def _get_fund_rankings_cn(fund_type: str) -> dict:
    try:
        import akshare as ak
        df = ak.fund_open_fund_info_em(symbol="全部", indicator="单位净值走势")
        if df is None or df.empty:
            return {"fund_type": fund_type, "market": "cn", "fallback": True, "funds": []}
        funds = df.head(30).to_dict(orient="records")
        return {"fund_type": fund_type, "market": "cn", "source": "天天基金", "funds": funds}
    except Exception as e:
        return {"fund_type": fund_type, "market": "cn", "fallback": True, "error": str(e), "funds": []}


# ── 港美股实现 (yfinance) ──────────────────────────────

# yfinance sector ETF tickers for industry rankings
_SECTOR_ETFS = {
    "hk": {
        "科技": "3067.HK",
        "金融": "2823.HK",
        "地产": "2822.HK",
        "消费": "2806.HK",
        "医药": "2835.HK",
        "能源": "2803.HK",
    },
    "us": {
        "科技": "XLK",
        "金融": "XLF",
        "医疗": "XLV",
        "能源": "XLE",
        "消费": "XLY",
        "工业": "XLI",
        "材料": "XLB",
        "公用事业": "XLU",
        "房地产": "XLRE",
        "通讯": "XLC",
    },
}

_INDEX_TICKERS = {
    "hk": {"恒生指数": "^HSI", "恒生科技": "^HSTECH", "国企指数": "^HSCE"},
    "us": {"标普500": "^GSPC", "纳斯达克": "^IXIC", "道琼斯": "^DJI"},
}


def _get_industry_rankings_yf(market: str) -> dict:
    try:
        import yfinance as yf
        sectors = _SECTOR_ETFS.get(market, {})
        if not sectors:
            return {"market": market, "fallback": True, "note": "无行业配置"}
        rankings = []
        for name, ticker in sectors.items():
            try:
                t = yf.Ticker(ticker)
                hist = t.history(period="5d")
                if len(hist) >= 2:
                    change_pct = float((hist["Close"].iloc[-1] / hist["Close"].iloc[-2] - 1) * 100)
                    rankings.append({"行业": name, "代码": ticker, "涨跌幅": round(change_pct, 2)})
            except Exception:
                rankings.append({"行业": name, "代码": ticker, "涨跌幅": None, "note": "数据获取失败"})
        rankings.sort(key=lambda x: x.get("涨跌幅") or -999, reverse=True)
        return {"market": market, "source": "yfinance sector ETFs", "industries": rankings}
    except Exception as e:
        return {"market": market, "fallback": True, "error": str(e), "note": "yfinance 不可用"}


def _get_macro_indicators_yf(market: str) -> dict:
    result = {"market": market, "indices": {}, "fallback": False}
    indices = _INDEX_TICKERS.get(market, {})
    try:
        import yfinance as yf
        for name, ticker in indices.items():
            try:
                t = yf.Ticker(ticker)
                hist = t.history(period="5d")
                if not hist.empty:
                    close = float(hist["Close"].iloc[-1])
                    change_pct = float((hist["Close"].iloc[-1] / hist["Close"].iloc[-2] - 1) * 100) if len(hist) >= 2 else None
                    result["indices"][name] = {"close": close, "change_pct": round(change_pct, 2) if change_pct else None}
            except Exception as e:
                result["indices"][name] = {"error": str(e)}
    except Exception as e:
        result["fallback"] = True
        result["error"] = str(e)
    return result


def _get_company_profile_yf(code: str, market: str) -> dict:
    try:
        import yfinance as yf
        suffix = ".HK" if market == "hk" else ""
        ticker_str = f"{code}{suffix}"
        t = yf.Ticker(ticker_str)
        info = t.info
        if not info or info.get("regularMarketPrice") is None:
            return {"code": code, "market": market, "fallback": True, "note": "yfinance 无此标的数据"}
        return {
            "code": code,
            "market": market,
            "profile": {
                "name": info.get("longName") or info.get("shortName", ""),
                "sector": info.get("sector", ""),
                "industry": info.get("industry", ""),
                "market_cap": info.get("marketCap"),
                "description": (info.get("longBusinessSummary", "") or "")[:500],
                "employees": info.get("fullTimeEmployees"),
                "country": info.get("country", ""),
            },
        }
    except Exception as e:
        return {"code": code, "market": market, "fallback": True, "error": str(e)}


def _get_financial_summary_yf(code: str, market: str) -> dict:
    try:
        import yfinance as yf
        suffix = ".HK" if market == "hk" else ""
        ticker_str = f"{code}{suffix}"
        t = yf.Ticker(ticker_str)
        info = t.info
        if not info:
            return {"code": code, "market": market, "fallback": True}
        return {
            "code": code,
            "market": market,
            "financial": {
                "pe_ttm": info.get("trailingPE"),
                "pe_forward": info.get("forwardPE"),
                "pb": info.get("priceToBook"),
                "roe": info.get("returnOnEquity"),
                "revenue_growth": info.get("revenueGrowth"),
                "profit_margin": info.get("profitMargins"),
                "debt_to_equity": info.get("debtToEquity"),
                "dividend_yield": info.get("dividendYield"),
            },
        }
    except Exception as e:
        return {"code": code, "market": market, "fallback": True, "error": str(e)}


def _get_stock_quotes_yf(code: str, market: str) -> dict:
    try:
        import yfinance as yf
        suffix = ".HK" if market == "hk" else ""
        ticker_str = f"{code}{suffix}"
        t = yf.Ticker(ticker_str)
        hist = t.history(period="1mo")
        if hist.empty:
            return {"code": code, "market": market, "fallback": True, "note": "无行情数据"}
        info = t.info
        latest_close = float(hist["Close"].iloc[-1])
        prev_close = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else latest_close
        change_pct = round((latest_close / prev_close - 1) * 100, 2)
        ma20 = round(float(hist["Close"].tail(20).mean()), 2)
        return {
            "code": code,
            "market": market,
            "quote": {
                "name": info.get("longName") or info.get("shortName", code),
                "price": latest_close,
                "change_pct": change_pct,
                "volume": float(hist["Volume"].iloc[-1]) if "Volume" in hist else None,
                "ma20": ma20,
                "pe": info.get("trailingPE"),
            },
        }
    except Exception as e:
        return {"code": code, "market": market, "fallback": True, "error": str(e)}


def _get_fund_rankings_yf(fund_type: str, market: str) -> dict:
    """港美股基金/ETF 排名，用代表性 ETF 列表"""
    etf_map = {
        "hk": [
            ("盈富基金", "2800.HK", "恒生指数"),
            ("南方A50", "2822.HK", "A股ETF"),
            ("华夏沪深300", "3188.HK", "A股ETF"),
            ("恒生科技ETF", "3032.HK", "科技"),
            ("安硕恒生科技", "3067.HK", "科技"),
            ("华夏恒生ESG", "3038.HK", "ESG"),
            ("南方恒生指数", "3037.HK", "恒生指数"),
            ("Global X 消费", "2806.HK", "消费"),
        ],
        "us": [
            ("SPY", "SPY", "标普500"),
            ("QQQ", "QQQ", "纳斯达克100"),
            ("VTI", "VTI", "全市场"),
            ("VEA", "VEA", "发达市场"),
            ("VWO", "VWO", "新兴市场"),
            ("IWM", "IWM", "罗素2000"),
            ("DIA", "DIA", "道琼斯"),
            ("GLD", "GLD", "黄金"),
        ],
    }
    etfs = etf_map.get(market, [])
    if not etfs:
        return {"fund_type": fund_type, "market": market, "fallback": True, "funds": []}

    result = []
    try:
        import yfinance as yf
        for name, ticker, category in etfs:
            try:
                t = yf.Ticker(ticker)
                info = t.info
                hist = t.history(period="1mo")
                ytd_return = None
                if len(hist) >= 21:
                    ytd_return = round(float(hist["Close"].iloc[-1] / hist["Close"].iloc[0] - 1) * 100, 2)
                result.append({
                    "name": name,
                    "code": ticker,
                    "category": category,
                    "ytd_return": ytd_return,
                    "expense_ratio": info.get("expenseRatio"),
                    "aum": info.get("totalAssets"),
                })
            except Exception:
                result.append({"name": name, "code": ticker, "category": category, "note": "数据获取失败"})
    except Exception as e:
        return {"fund_type": fund_type, "market": market, "fallback": True, "error": str(e), "funds": result}
    return {"fund_type": fund_type, "market": market, "source": "yfinance ETF", "funds": result}


# ── 工具列表导出 ────────────────────────────────────────

L1_TOOLS = [get_industry_rankings, get_sector_fund_flows, get_macro_indicators]

L2_TOOLS = [
    get_industry_constituents,
    get_company_profile,
    get_financial_summary,
    get_stock_quotes,
    get_fund_rankings,
]

ALL_MARKET_TOOLS = L1_TOOLS + L2_TOOLS
