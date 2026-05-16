"""东方财富情绪数据源

通过 akshare 获取 A 股个股的相关新闻和热度数据。
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

# Ticker suffixes indicating A-share markets
_A_SHARE_MARKETS = {".SZ", ".SS", ".SH"}


def _is_a_share(ticker: str) -> bool:
    """Check if ticker is an A-share stock."""
    upper = ticker.upper()
    return any(upper.endswith(suffix) for suffix in _A_SHARE_MARKETS)


def _normalize_ticker(ticker: str) -> Optional[str]:
    """Normalize A-share ticker for akshare.

    akshare uses formats like: '000001' (no suffix for SZ), '600519'
    (no suffix for SH/SS).

    Returns:
        Normalized ticker, or None if not an A-share.
    """
    upper = ticker.upper()
    for suffix in _A_SHARE_MARKETS:
        if upper.endswith(suffix):
            return upper.replace(suffix, "")
    return None


@register("eastmoney")
class EastMoneySource(BaseSentimentSource):
    """Fetch sentiment data from 东方财富 (East Money) via akshare."""

    name = "eastmoney"

    async def fetch(self, tickers: list[str]) -> dict[str, SentimentReport]:
        """Fetch east money news/heat data for A-share tickers.

        Args:
            tickers: List of ticker symbols.

        Returns:
            Dict mapping ticker -> SentimentReport.
        """
        import importlib

        results: dict[str, SentimentReport] = {}

        for ticker in tickers:
            report = SentimentReport(ticker=ticker)
            if not _is_a_share(ticker):
                logger.debug("eastmoney: skipping non-A-share ticker %s", ticker)
                continue

            code = _normalize_ticker(ticker)
            if code is None:
                continue

            try:
                # Use akshare to get news — lazy import to avoid startup cost
                akshare = importlib.import_module("akshare")
                news_df = akshare.stock_info_ths_zjlx(
                    symbol=code, date=""
                )
                if news_df is not None and not news_df.empty:
                    for _, row in news_df.head(10).iterrows():
                        item = SentimentData(
                            source=self.name,
                            ticker=ticker,
                            title=str(row.get("新闻标题", "")),
                            content=str(row.get("新闻内容", "")),
                            timestamp=str(row.get("发布时间", "")),
                        )
                        report.items.append(item)

                    report.summary = (
                        f"East Money: {len(report.items)} articles found for {code}"
                    )
                else:
                    report.summary = f"East Money: no articles for {code}"
                    logger.debug("eastmoney: no data for %s", code)

            except ImportError:
                logger.warning("eastmoney: akshare not installed, skipping")
                report.summary = "akshare not available"
            except Exception as e:
                logger.warning("eastmoney: failed to fetch %s: %s", code, e)
                report.summary = f"fetch error: {e}"

            results[ticker] = report

        return results
