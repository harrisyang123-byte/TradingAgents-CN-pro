"""Pre-fetch sentiment analysis framework.

Runs before the main agent pipeline begins, collecting sentiment data
from all enabled sources (eastmoney, wechat_mp, etc.) and injecting
the aggregated report into the agent state.

This is more efficient than having agents call sentiment tools during
execution, as it batches all fetches upfront and avoids extra LLM rounds.
"""

import asyncio
import logging
from typing import Any, Optional

from tradingagents.agents.analysts.sources import (
    BaseSentimentSource,
    SentimentReport,
    get_enabled_sources,
)

logger = logging.getLogger(__name__)


class SentimentAnalyst:
    """Pre-fetch sentiment analyst.

    Orchestrates multiple sentiment data sources, fetches data for
    each ticker, aggregates into a formatted report, and returns it
    for injection into the agent graph state.
    """

    def __init__(self, sources: list[BaseSentimentSource]):
        """Initialize with a list of enabled source instances.

        Args:
            sources: Instantiated sentiment sources from get_enabled_sources().
        """
        self.sources = sources

    async def fetch_all(
        self,
        tickers: list[str],
        timeout: float = 10.0,
    ) -> dict[str, SentimentReport]:
        """Fetch sentiment data from all sources for all tickers.

        Args:
            tickers: List of ticker symbols to fetch.
            timeout: Max seconds to wait for all sources (per ticker).

        Returns:
            Dict mapping ticker -> aggregated SentimentReport.
        """
        if not self.sources or not tickers:
            return {}

        reports: dict[str, SentimentReport] = {}
        for ticker in tickers:
            ticker_reports: dict[str, SentimentReport] = {}
            for source in self.sources:
                try:
                    result = await asyncio.wait_for(
                        source.fetch([ticker]),
                        timeout=timeout,
                    )
                    if ticker in result:
                        ticker_reports[source.name] = result[ticker]
                except asyncio.TimeoutError:
                    logger.warning(
                        "Sentiment source '%s' timed out for %s (>{timeout}s)",
                        source.name, ticker, timeout=timeout
                    )
                except Exception as e:
                    logger.warning(
                        "Sentiment source '%s' failed for %s: %s",
                        source.name, ticker, e
                    )

            # Aggregate into a single report per ticker
            combined = SentimentReport(ticker=ticker)
            for src_name, report in ticker_reports.items():
                combined.items.extend(report.items)
            # Simple summary: count of items per source
            parts = [f"{n}: {len(ticker_reports.get(n, SentimentReport(ticker=ticker)).items) or 0} items"
                     for n in [s.name for s in self.sources]]
            combined.summary = ", ".join(parts)
            if parts:
                reports[ticker] = combined

        return reports

    def format_state_text(
        self, reports: dict[str, SentimentReport]
    ) -> str:
        """Format aggregated reports into a text block for agent state.

        Args:
            reports: Reports from fetch_all().

        Returns:
            Formatted text suitable for AgentState.sentiment_context.
        """
        if not reports:
            return ""
        parts = []
        for ticker in sorted(reports.keys()):
            report = reports[ticker]
            text = report.format_text()
            if text:
                parts.append(text)
        return "\n---\n".join(parts)


def create_sentiment_analyst(
    source_names: Optional[list[str]] = None,
    source_config: Optional[dict[str, Any]] = None,
) -> SentimentAnalyst:
    """Factory: create SentimentAnalyst from source names.

    Args:
        source_names: List of source names to enable.
            Defaults to ["eastmoney", "wechat_mp"].
        source_config: Optional per-source kwargs keyed by source name.

    Returns:
        Configured SentimentAnalyst instance.
    """
    if source_names is None:
        source_names = ["eastmoney", "wechat_mp"]
    sources = get_enabled_sources(source_names, source_config)
    logger.info(
        "SentimentAnalyst created with sources: %s",
        [s.name for s in sources] or ["(none)"]
    )
    return SentimentAnalyst(sources)
