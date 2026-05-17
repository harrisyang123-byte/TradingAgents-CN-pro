"""小红书情绪数据源

通过外部数据采集服务获取小红书笔记。
服务地址可配置（默认 localhost:8002）。
小红书无稳定公开 API，此源需要单独部署数据采集服务。

依赖: httpx (CN fork 已有)
"""

import logging

import httpx

from tradingagents.agents.analysts.sources import (
    BaseSentimentSource,
    SentimentData,
    SentimentReport,
    register,
)

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "http://localhost:8002"


@register("xiaohongshu")
class XiaohongshuSource(BaseSentimentSource):
    """Fetch sentiment data from 小红书 via external collection service."""

    name = "xiaohongshu"

    def __init__(self, base_url: str = _DEFAULT_BASE_URL):
        self.base_url = base_url.rstrip("/")

    async def fetch(self, tickers: list[str]) -> dict[str, SentimentReport]:
        results: dict[str, SentimentReport] = {}

        async with httpx.AsyncClient(timeout=10.0) as client:
            for ticker in tickers:
                report = SentimentReport(ticker=ticker)
                try:
                    resp = await client.get(
                        f"{self.base_url}/api/v1/search",
                        params={"q": ticker, "limit": 10},
                    )

                    if resp.is_success:
                        data = resp.json()
                        notes = data if isinstance(data, list) else data.get("notes", data.get("data", []))

                        for note in notes[:10]:
                            report.items.append(SentimentData(
                                source=self.name,
                                ticker=ticker,
                                title=note.get("title", ""),
                                content=note.get("desc", note.get("content", ""))[:300],
                                url=note.get("url", note.get("link", "")),
                                timestamp=note.get("time", note.get("date", "")),
                            ))

                        report.summary = f"小红书: {len(report.items)} 篇笔记 ({ticker})"
                    else:
                        report.summary = f"HTTP {resp.status_code}"

                except httpx.ConnectError:
                    logger.debug("xiaohongshu: cannot connect to %s", self.base_url)
                    report.summary = "小红书数据服务未启动"
                except httpx.TimeoutException:
                    report.summary = "timeout"
                except Exception as e:
                    logger.warning("xiaohongshu: fetch failed for %s: %s", ticker, e)
                    report.summary = f"error: {e}"

                results[ticker] = report

        return results
