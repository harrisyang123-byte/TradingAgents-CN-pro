"""雪球热度数据源

通过 akshare 获取雪球讨论/关注/交易热度排行，
检查目标 ticker 是否在排行榜中。

依赖: akshare (CN fork 已有)
"""

import logging
from typing import Optional

from tradingagents.agents.analysts.sources import (
    BaseSentimentSource,
    SentimentData,
    SentimentReport,
    register,
)

logger = logging.getLogger(__name__)

_A_SHARE_MARKETS = {".SZ", ".SS", ".SH"}

_EXCHANGE_PREFIX = {".SH": "SH", ".SS": "SH", ".SZ": "SZ"}

_RANKING_ENDPOINTS = [
    ("stock_hot_tweet_xq", "讨论热度"),
    ("stock_hot_follow_xq", "关注人数"),
    ("stock_hot_deal_xq", "分享交易"),
]


def _is_a_share(ticker: str) -> bool:
    upper = ticker.upper()
    return any(upper.endswith(suffix) for suffix in _A_SHARE_MARKETS)


def _to_prefixed(ticker: str) -> Optional[str]:
    upper = ticker.upper()
    for suffix, prefix in _EXCHANGE_PREFIX.items():
        if upper.endswith(suffix):
            code = upper.replace(suffix, "")
            return f"{prefix}{code}"
    return None


@register("xueqiu")
class XueqiuSource(BaseSentimentSource):
    """Fetch hot ranking data from 雪球 via akshare."""

    name = "xueqiu"

    async def fetch(self, tickers: list[str]) -> dict[str, SentimentReport]:
        import importlib

        results: dict[str, SentimentReport] = {}

        for ticker in tickers:
            report = SentimentReport(ticker=ticker)
            if not _is_a_share(ticker):
                logger.debug("xueqiu: skipping non-A-share ticker %s", ticker)
                results[ticker] = report
                continue

            prefixed = _to_prefixed(ticker)
            if prefixed is None:
                results[ticker] = report
                continue

            try:
                akshare = importlib.import_module("akshare")
            except ImportError:
                logger.warning("xueqiu: akshare not installed, skipping")
                report.summary = "akshare not available"
                results[ticker] = report
                continue

            for func_name, label in _RANKING_ENDPOINTS:
                try:
                    func = getattr(akshare, func_name)
                    df = func(symbol="最热门")

                    if df is None or df.empty:
                        continue

                    code_col = "股票代码"
                    if code_col not in df.columns:
                        continue

                    match = df[df[code_col] == prefixed]
                    if match.empty:
                        continue

                    row = match.iloc[0]
                    rank = match.index[0] + 1
                    name = str(row.get("股票简称", ""))
                    attention = row.get("关注", 0)

                    report.items.append(SentimentData(
                        source=self.name,
                        ticker=ticker,
                        title=f"雪球{label}排名第{rank}: {name}",
                        content=f"关注/热度: {attention}, 最新价: {row.get('最新价', 'N/A')}",
                    ))
                except Exception as e:
                    logger.debug("xueqiu: %s failed: %s", func_name, e)

            if report.items:
                report.summary = f"雪球: {len(report.items)} 项排名数据 ({prefixed})"
            else:
                report.summary = f"雪球: {prefixed} 未进入热门排行榜"

            results[ticker] = report

        return results
