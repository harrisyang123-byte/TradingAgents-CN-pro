"""市场信号采集器 — 情绪、资金、广度、宏观

收集买点判断所需的实时市场数据：
- 北向/南向资金流向
- 市场涨跌家数（广度）
- 融资融券余额变化
- 行业资金流向排名
- 个股情绪（千股千评、雪球热度）
- 宏观指标（PMI/CPI）
"""

from typing import Dict, List, Optional, Any
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json

logger = logging.getLogger(__name__)


@dataclass
class MarketBreadth:
    """市场广度信号"""
    up_count: int = 0
    down_count: int = 0
    flat_count: int = 0
    up_ratio: float = 0.0           # 上涨占比
    limit_up: int = 0               # 涨停数
    limit_down: int = 0             # 跌停数
    breadth_signal: str = ""        # 过热/偏强/中性/偏弱/恐慌
    timestamp: str = ""


@dataclass
class CapitalFlow:
    """资金流向信号"""
    north_net: float = 0.0          # 北向净流入（亿）
    north_days: int = 0             # 北向连续净流入天数
    south_net: float = 0.0          # 南向净流入（亿）
    margin_balance: float = 0.0     # 融资余额（亿）
    margin_change_pct: float = 0.0  # 融资余额周变化
    sector_flows: List[Dict] = field(default_factory=list)  # Top 行业资金流向
    flow_signal: str = ""           # 大幅流入/流入/中性/流出/大幅流出


@dataclass
class SentimentSignal:
    """个股情绪信号"""
    code: str
    name: str = ""
    # 千股千评
    em_score: Optional[float] = None      # eastmoney 综合评分 0-100
    em_participation: Optional[str] = None  # 散户参与意愿
    # 雪球
    xq_hot_rank: Optional[int] = None     # 雪球热度排名
    # 新闻
    news_bias: Optional[str] = None       # 正面/负面/中性
    news_count: int = 0
    # 行业情绪
    sector_sentiment: Optional[str] = None  # 行业整体情绪方向
    # 综合
    sentiment_score: float = 50.0         # 0-100, 50=中性
    sentiment_label: str = ""             # 乐观/偏乐观/中性/偏悲观/悲观


@dataclass
class MacroSignal:
    """宏观经济信号"""
    pmi: Optional[float] = None           # 制造业 PMI
    pmi_trend: str = ""                   # 扩张/收缩/持平
    cpi: Optional[float] = None           # CPI 同比
    shibor_on: Optional[float] = None     # 隔夜 Shibor
    index_pct_change: float = 0.0         # 上证周涨跌幅
    macro_signal: str = ""                # 利好/中性/利空


# ── 北向资金 ───────────────────────────────────────

async def fetch_north_flow() -> Dict[str, Any]:
    """获取北向资金流向（沪深港通）"""
    try:
        import akshare as ak
        # 使用 stock_hsgt_hist_em 获取历史沪深港通资金流向
        df = ak.stock_hsgt_hist_em(symbol="北向资金")
        if df is None or df.empty:
            return {"north_net": 0, "north_days": 0, "source": "akshare_empty"}

        recent = df.tail(5)
        net_col = "净买入额" if "净买入额" in df.columns else df.columns[2]
        north_net = float(recent[net_col].iloc[-1]) if net_col else 0
        days = 0
        for _, row in recent[::-1].iterrows():
            val = float(row.get(net_col, 0)) if net_col else 0
            if val > 0:
                days += 1
            else:
                break
        return {
            "north_net": round(north_net, 1),
            "north_days": days,
            "source": "akshare",
        }
    except Exception as e:
        logger.warning(f"北向资金获取失败: {e}")
        return {"north_net": 0, "north_days": 0, "source": f"error: {e}"}


# ── 市场广度 ───────────────────────────────────────

async def fetch_market_breadth() -> Dict[str, Any]:
    """获取涨跌家数、涨停跌停数"""
    try:
        import akshare as ak
        df = ak.stock_zh_a_spot_em()
        if df is None or df.empty:
            return {}

        total = len(df)
        up = len(df[df["涨跌幅"] > 0]) if "涨跌幅" in df.columns else 0
        down = len(df[df["涨跌幅"] < 0]) if "涨跌幅" in df.columns else 0
        flat = total - up - down
        up_ratio = round(up / max(total, 1) * 100, 1)

        # 涨停跌停（涨跌幅 > 9.5% 或 < -9.5%）
        limit_up = len(df[df["涨跌幅"] > 9.5]) if "涨跌幅" in df.columns else 0
        limit_down = len(df[df["涨跌幅"] < -9.5]) if "涨跌幅" in df.columns else 0

        # 广度信号判定
        if up_ratio > 80:
            breadth_signal = "过热"
        elif up_ratio > 60:
            breadth_signal = "偏强"
        elif up_ratio > 40:
            breadth_signal = "中性"
        elif up_ratio > 20:
            breadth_signal = "偏弱"
        else:
            breadth_signal = "恐慌"

        return {
            "up_count": up, "down_count": down, "flat_count": flat,
            "up_ratio": up_ratio, "limit_up": limit_up, "limit_down": limit_down,
            "breadth_signal": breadth_signal, "total": total,
            "source": "akshare",
        }
    except Exception as e:
        logger.warning(f"市场广度获取失败: {e}")
        return {"breadth_signal": "数据不可用", "source": f"error: {e}"}


# ── 融资融券 ───────────────────────────────────────

async def fetch_margin_data() -> Dict[str, Any]:
    """获取融资融券余额"""
    try:
        import akshare as ak
        df = ak.macro_china_market_margin_sh()
        if df is not None and not df.empty:
            latest = df.iloc[-1]
            balance = float(latest.get("融资余额", 0)) / 1e8 if "融资余额" in df.columns else 0
            return {"margin_balance": round(balance, 0), "source": "akshare"}
        return {"margin_balance": 0, "source": "akshare_empty"}
    except Exception as e:
        logger.warning(f"融资融券数据获取失败: {e}")
        return {"margin_balance": 0, "source": f"error: {e}"}


# ── 个股情绪 ───────────────────────────────────────

async def fetch_stock_sentiment(code: str, name: str = "") -> Dict[str, Any]:
    """获取单只标的的市场情绪"""
    result = {"code": code, "name": name, "em_score": None, "xq_hot_rank": None}

    # 1. 千股千评（eastmoney comment）
    try:
        from tradingagents.dataflows.news.chinese_finance import get_chinese_social_sentiment
        sentiment_text = get_chinese_social_sentiment(code)
        if sentiment_text and "正面" in sentiment_text:
            result["news_bias"] = "正面"
        elif sentiment_text and "负面" in sentiment_text:
            result["news_bias"] = "负面"
        else:
            result["news_bias"] = "中性"
        result["news_count"] = 1
    except Exception:
        pass

    # 2. eastmoney 千股千评评分
    try:
        import akshare as ak
        df = ak.stock_comment_em(symbol=code)
        if df is not None and not df.empty:
            latest = df.iloc[0]
            result["em_score"] = float(latest.get("综合评价", 0)) if "综合评价" in df.columns else None
    except Exception:
        pass

    # 3. 行业情绪——从市场宽度反推
    breadth = await fetch_market_breadth()
    if breadth.get("breadth_signal"):
        bmap = {"过热": "偏乐观", "偏强": "偏乐观", "中性": "中性", "偏弱": "偏悲观", "恐慌": "悲观"}
        result["sector_sentiment"] = bmap.get(breadth["breadth_signal"], "中性")

    # 综合评分
    score = 50.0
    if result.get("em_score") is not None:
        score = float(result["em_score"])
    elif result.get("news_bias") == "正面":
        score = 65.0
    elif result.get("news_bias") == "负面":
        score = 35.0

    if score >= 70:
        result["sentiment_label"] = "乐观"
    elif score >= 55:
        result["sentiment_label"] = "偏乐观"
    elif score >= 45:
        result["sentiment_label"] = "中性"
    elif score >= 30:
        result["sentiment_label"] = "偏悲观"
    else:
        result["sentiment_label"] = "悲观"
    result["sentiment_score"] = score

    return result


# ── 行业资金流向排名 ────────────────────────────────

async def fetch_sector_flows() -> List[Dict]:
    """获取行业资金流向 Top 排名"""
    try:
        from tradingagents.agents.advisors.market_tools import get_sector_fund_flows
        result = get_sector_fund_flows.invoke({"market": "cn"})
        if isinstance(result, dict):
            return result.get("flows", result.get("data", []))
        if isinstance(result, str):
            try:
                parsed = json.loads(result)
                return parsed if isinstance(parsed, list) else []
            except Exception:
                return []
        return []
    except Exception as e:
        logger.warning(f"行业资金流向获取失败: {e}")
        return []


# ── 宏观指标 ───────────────────────────────────────

async def fetch_macro_indicators() -> Dict[str, Any]:
    """获取 PMI/CPI/Shibor 等宏观指标"""
    result = {}
    try:
        import akshare as ak
        # PMI
        try:
            df_pmi = ak.macro_china_pmi()
            if df_pmi is not None and not df_pmi.empty:
                latest = df_pmi.iloc[-1]
                result["pmi"] = float(latest.get("制造业", 0)) if "制造业" in df_pmi.columns else None
                result["pmi_trend"] = "扩张" if result.get("pmi", 50) and result["pmi"] >= 50 else "收缩"
        except Exception:
            pass

        # Shibor
        try:
            df_shibor = ak.rate_interbank(market="上海银行间同业拆放利率(Shibor)")
            if df_shibor is not None and not df_shibor.empty:
                result["shibor_on"] = float(df_shibor.iloc[0].get("利率", 0)) if "利率" in df_shibor.columns else None
        except Exception:
            pass
    except Exception as e:
        logger.warning(f"宏观指标获取失败: {e}")

    result["source"] = "akshare" if result else "unavailable"
    return result


# ── 综合市场快照 ────────────────────────────────────

async def collect_market_signals(codes: List[str] = None) -> Dict[str, Any]:
    """收集所有市场信号（可在 advisor graph 的 compute_buy_signals 节点中调用）"""
    results = {}

    # 并发收集
    breadth, north, macro = None, None, None
    try:
        breadth = await fetch_market_breadth()
        north = await fetch_north_flow()
        macro = await fetch_macro_indicators()
    except Exception as e:
        logger.warning(f"市场信号收集部分失败: {e}")

    results["breadth"] = breadth or {}
    results["north_flow"] = north or {}
    results["macro"] = macro or {}

    # 资金流向信号
    north_net = (north or {}).get("north_net", 0)
    north_days = (north or {}).get("north_days", 0)
    if north_net > 50:
        flow_signal = "大幅流入"
    elif north_net > 10:
        flow_signal = "流入"
    elif north_net > -10:
        flow_signal = "中性"
    elif north_net > -50:
        flow_signal = "流出"
    else:
        flow_signal = "大幅流出"
    results["flow_signal"] = flow_signal
    results["north_net"] = north_net
    results["north_days"] = north_days

    return results
