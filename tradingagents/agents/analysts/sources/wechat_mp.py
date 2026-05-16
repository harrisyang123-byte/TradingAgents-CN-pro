"""微信公众号情绪数据源

通过 we-mp-rss Docker 服务获取公众号文章。
服务地址可配置（默认 localhost:8001）。

依赖: httpx (CN fork 已有)
"""

import json
import logging
from typing import Optional

import httpx

from tradingagents.agents.analysts.sources import (
    BaseSentimentSource,
    SentimentData,
    SentimentReport,
    register,
)

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "http://localhost:8001"


@register("wechat_mp")
class WeChatMPSource(BaseSentimentSource):
    """Fetch sentiment data from 微信公众号 articles via we-mp-rss."""

    name = "wechat_mp"

    def __init__(self, base_url: str = _DEFAULT_BASE_URL):
        """Initialize with we-mp-rss service URL.

        Args:
            base_url: Base URL of the we-mp-rss Docker service.
        """
        self.base_url = base_url.rstrip("/")

    async def fetch(self, tickers: list[str]) -> dict[str, SentimentReport]:
        """Fetch WeChat MP articles related to given tickers.

        Args:
            tickers: List of ticker symbols.

        Returns:
            Dict mapping ticker -> SentimentReport.
        """
        results: dict[str, SentimentReport] = {}

        async with httpx.AsyncClient(timeout=10.0) as client:
            for ticker in tickers:
                report = SentimentReport(ticker=ticker)
                try:
                    # Try searching the we-mp-rss article index
                    resp = await client.get(
                        f"{self.base_url}/api/v1/articles/search",
                        params={"q": ticker, "limit": 10},
                    )
                    if resp.status_code == 404:
                        # Endpoint may differ — try the query endpoint
                        resp = await client.post(
                            f"{self.base_url}/api/v1/query",
                            json={"query": ticker, "limit": 10},
                        )

                    if resp.is_success:
                        data = resp.json()
                        articles = []
                        if isinstance(data, list):
                            articles = data
                        elif isinstance(data, dict):
                            articles = data.get("articles", data.get("data", []))

                        for article in articles[:10]:
                            item = SentimentData(
                                source=self.name,
                                ticker=ticker,
                                title=article.get("title", ""),
                                content=article.get("summary", article.get("content", ""))[:300],
                                url=article.get("url", article.get("link", "")),
                                timestamp=article.get("pub_time", article.get("date", "")),
                            )
                            report.items.append(item)

                        report.summary = (
                            f"WeChat MP: {len(report.items)} articles for {ticker}"
                        )
                    else:
                        logger.debug(
                            "wechat_mp: HTTP %d for %s", resp.status_code, ticker
                        )
                        report.summary = f"HTTP {resp.status_code}"

                except httpx.ConnectError:
                    logger.warning(
                        "wechat_mp: cannot connect to %s (is the Docker service running?)",
                        self.base_url,
                    )
                    report.summary = "service unreachable"
                except httpx.TimeoutException:
                    logger.warning("wechat_mp: request timed out for %s", ticker)
                    report.summary = "timeout"
                except Exception as e:
                    logger.warning("wechat_mp: fetch failed for %s: %s", ticker, e)
                    report.summary = f"error: {e}"

                results[ticker] = report

        return results
