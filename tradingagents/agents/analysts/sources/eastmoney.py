"""东方财富个股热搜数据源

通过 akshare 获取 A 股个股的热搜概念和关联热度。
港股 ticker 自动跳过（不报错）。

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


def _is_a_share(ticker: str) -> bool:
    upper = ticker.upper()
    return any(upper.endswith(suffix) for suffix in _A_SHARE_MARKETS)


def _to_prefixed(ticker: str) -> Optional[str]:
    """Convert '600519.SH' to 'SH600519' for akshare hot keyword API."""
    upper = ticker.upper()
    for suffix, prefix in _EXCHANGE_PREFIX.items():
        if upper.endswith(suffix):
            code = upper.replace(suffix, "")
            return f"{prefix}{code}"
    return None


@register("eastmoney")
class EastMoneySource(BaseSentimentSource):
    """Fetch hot keyword/concept data from 东方财富 via akshare."""

    name = "eastmoney"

    async def fetch(self, tickers: list[str]) -> dict[str, SentimentReport]:
        import importlib

        results: dict[str, SentimentReport] = {}

        for ticker in tickers:
            report = SentimentReport(ticker=ticker)
            if not _is_a_share(ticker):
                logger.debug("eastmoney: skipping non-A-share ticker %s", ticker)
                continue

            prefixed = _to_prefixed(ticker)
            if prefixed is None:
                continue

            try:
                akshare = importlib.import_module("akshare")
                df = akshare.stock_hot_keyword_em(symbol=prefixed)

                if df is not None and not df.empty:
                    for _, row in df.head(10).iterrows():
                        concept = str(row.get("概念名称", ""))
                        heat = row.get("热度", 0)
                        ts = str(row.get("时间", ""))
                        item = SentimentData(
                            source=self.name,
                            ticker=ticker,
                            title=f"{concept} (热度: {heat})",
                            timestamp=ts,
                        )
                        report.items.append(item)

                    report.summary = (
                        f"East Money: {len(report.items)} hot concepts for {prefixed}"
                    )
                else:
                    report.summary = f"East Money: no hot concepts for {prefixed}"

            except ImportError:
                logger.warning("eastmoney: akshare not installed, skipping")
                report.summary = "akshare not available"
            except Exception as e:
                logger.warning("eastmoney: failed to fetch %s: %s", prefixed, e)
                report.summary = f"fetch error: {e}"

            results[ticker] = report

        return results
