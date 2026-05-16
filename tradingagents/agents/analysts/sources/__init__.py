"""Sentiment source registry.

Each sentiment source implements BaseSentimentSource and registers itself
with the @register decorator. Sources are fetched in parallel by the
sentiment_analyst pre-fetch framework.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class SentimentData:
    """Normalized sentiment data from a single source."""
    source: str
    ticker: str
    title: str = ""
    content: str = ""
    url: str = ""
    timestamp: str = ""
    sentiment_score: Optional[float] = None  # -1.0 to 1.0
    error: Optional[str] = None


@dataclass
class SentimentReport:
    """Aggregated sentiment report from all enabled sources."""
    ticker: str
    items: list[SentimentData] = field(default_factory=list)
    summary: str = ""

    def format_text(self) -> str:
        """Format the report as plain text for injection into agent state."""
        if not self.items and not self.summary:
            return ""

        lines = [f"=== Sentiment Report for {self.ticker} ===", ""]
        for item in self.items:
            if item.error:
                lines.append(f"[{item.source}] Error: {item.error}")
            else:
                score = f" ({item.sentiment_score:+.2f})" if item.sentiment_score is not None else ""
                lines.append(f"[{item.source}]{score} {item.title}")
                if item.content:
                    lines.append(f"   {item.content[:200]}")
                lines.append("")
        if self.summary:
            lines.append(f"Summary: {self.summary}")
        return "\n".join(lines)


class BaseSentimentSource(ABC):
    """Abstract base class for sentiment data sources.

    Subclasses must set `name` as a class attribute and implement `fetch()`.
    """
    name: str = ""

    @abstractmethod
    async def fetch(self, tickers: list[str]) -> dict[str, SentimentReport]:
        """Fetch sentiment data for the given tickers.

        Args:
            tickers: List of ticker symbols to fetch data for.

        Returns:
            Dict mapping ticker -> SentimentReport.
        """


# Global registry: name -> class
REGISTRY: dict[str, type[BaseSentimentSource]] = {}


def register(name: str):
    """Decorator to register a sentiment source class.

    Usage:
        @register("eastmoney")
        class EastMoneySource(BaseSentimentSource):
            name = "eastmoney"
            ...
    """
    def wrapper(cls: type[BaseSentimentSource]) -> type[BaseSentimentSource]:
        REGISTRY[name] = cls
        return cls
    return wrapper


def get_enabled_sources(
    names: list[str],
    source_config: Optional[dict[str, Any]] = None,
) -> list[BaseSentimentSource]:
    """Instantiate enabled sentiment sources by name.

    Args:
        names: List of source names to enable (from config).
        source_config: Optional per-source init kwargs keyed by source name.
            e.g. {"wechat_mp": {"base_url": "http://..."}}

    Returns:
        List of instantiated source objects. Unknown names are silently skipped.
    """
    source_config = source_config or {}
    sources = []
    for name in names:
        cls = REGISTRY.get(name)
        if cls is not None:
            kwargs = source_config.get(name, {})
            sources.append(cls(**kwargs))
    return sources
