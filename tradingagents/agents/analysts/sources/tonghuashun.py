"""同花顺概念板块数据源

通过 akshare 获取同花顺概念板块列表，
检查目标 ticker 是否属于当日热门概念板块。

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


def _is_a_share(ticker: str) -> bool:
    upper = ticker.upper()
    return any(upper.endswith(suffix) for suffix in _A_SHARE_MARKETS)


def _extract_code(ticker: str) -> Optional[str]:
    """Extract bare numeric code from ticker like '600519.SH' -> '600519'."""
    upper = ticker.upper()
    for suffix in _A_SHARE_MARKETS:
        if upper.endswith(suffix):
            return upper.replace(suffix, "")
    return None


@register("tonghuashun")
class TonghuashunSource(BaseSentimentSource):
    """Fetch concept board data from 同花顺 via akshare."""

    name = "tonghuashun"

    async def fetch(self, tickers: list[str]) -> dict[str, SentimentReport]:
        import importlib

        results: dict[str, SentimentReport] = {}

        for ticker in tickers:
            report = SentimentReport(ticker=ticker)
            if not _is_a_share(ticker):
                logger.debug("tonghuashun: skipping non-A-share ticker %s", ticker)
                results[ticker] = report
                continue

            code = _extract_code(ticker)
            if code is None:
                results[ticker] = report
                continue

            try:
                akshare = importlib.import_module("akshare")
            except ImportError:
                logger.warning("tonghuashun: akshare not installed, skipping")
                report.summary = "akshare not available"
                results[ticker] = report
                continue

            try:
                concept_df = akshare.stock_board_concept_name_ths()
                if concept_df is None or concept_df.empty:
                    report.summary = "同花顺: 无概念板块数据"
                    results[ticker] = report
                    continue

                top_concepts = concept_df.head(20)

                name_col = "概念名称" if "概念名称" in top_concepts.columns else top_concepts.columns[0]

                for _, row in top_concepts.iterrows():
                    concept_name = str(row.get(name_col, ""))
                    if not concept_name:
                        continue

                    try:
                        members = akshare.stock_board_concept_info_ths(symbol=concept_name)
                        if members is None or members.empty:
                            continue

                        code_col = None
                        for candidate in ["代码", "股票代码"]:
                            if candidate in members.columns:
                                code_col = candidate
                                break
                        if code_col is None:
                            continue

                        if code not in members[code_col].astype(str).values:
                            continue

                        change = row.get("涨跌幅", row.get("涨幅", "N/A"))
                        report.items.append(SentimentData(
                            source=self.name,
                            ticker=ticker,
                            title=f"同花顺概念板块: {concept_name}",
                            content=f"板块涨跌幅: {change}%",
                        ))
                    except Exception as e:
                        logger.debug("tonghuashun: concept %s lookup failed: %s", concept_name, e)
                        continue

            except Exception as e:
                logger.warning("tonghuashun: failed to fetch concepts: %s", e)
                report.summary = f"fetch error: {e}"
                results[ticker] = report
                continue

            if report.items:
                report.summary = f"同花顺: {code} 属于 {len(report.items)} 个热门概念板块"
            else:
                report.summary = f"同花顺: {code} 不在前20热门概念板块中"

            results[ticker] = report

        return results
