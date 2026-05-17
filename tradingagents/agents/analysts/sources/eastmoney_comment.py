"""东方财富千股千评情绪数据源

通过 akshare 获取 A 股千股千评数据，包括：
- 综合得分、关注指数、机构参与度（stock_comment_em）
- 散户参与意愿时序（stock_comment_detail_scrd_desire_em）
- 综合评价历史评分（stock_comment_detail_zhpj_lspf_em）

对标 TG upstream StockTwits 的角色：量化散户情绪方向和强度。

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


def _normalize_code(ticker: str) -> Optional[str]:
    upper = ticker.upper()
    for suffix in _A_SHARE_MARKETS:
        if upper.endswith(suffix):
            return upper.replace(suffix, "")
    return None


@register("eastmoney_comment")
class EastMoneyCommentSource(BaseSentimentSource):
    """千股千评 + 散户参与意愿 + 历史评分。"""

    name = "eastmoney_comment"

    async def fetch(self, tickers: list[str]) -> dict[str, SentimentReport]:
        import importlib

        results: dict[str, SentimentReport] = {}

        for ticker in tickers:
            report = SentimentReport(ticker=ticker)
            if not _is_a_share(ticker):
                logger.debug("eastmoney_comment: skipping non-A-share ticker %s", ticker)
                continue

            code = _normalize_code(ticker)
            if code is None:
                continue

            try:
                akshare = importlib.import_module("akshare")

                self._fetch_comment_summary(akshare, code, ticker, report)
                self._fetch_desire(akshare, code, ticker, report)
                self._fetch_rating_history(akshare, code, ticker, report)

                report.summary = f"千股千评: {len(report.items)} data points for {code}"

            except ImportError:
                logger.warning("eastmoney_comment: akshare not installed")
                report.summary = "akshare not available"
            except Exception as e:
                logger.warning("eastmoney_comment: failed for %s: %s", code, e)
                report.summary = f"fetch error: {e}"

            results[ticker] = report

        return results

    def _fetch_comment_summary(self, akshare, code, ticker, report):
        """千股千评综合数据：得分、关注指数、机构参与度。"""
        try:
            df = akshare.stock_comment_em()
            if df is None or df.empty:
                return
            row = df[df["代码"] == code]
            if row.empty:
                return
            row = row.iloc[0]
            score = row.get("综合得分", "N/A")
            rank = row.get("目前排名", "N/A")
            attention = row.get("关注指数", "N/A")
            institution = row.get("机构参与度", "N/A")
            trend = row.get("上升", 0)
            trend_str = f"↑{trend}" if trend > 0 else f"↓{abs(trend)}" if trend < 0 else "→"

            report.items.append(SentimentData(
                source=self.name,
                ticker=ticker,
                title=f"千股千评综合: 得分 {score:.1f}, 排名 {rank} ({trend_str})",
                content=f"关注指数: {attention}, 机构参与度: {float(institution)*100:.1f}%",
            ))
        except Exception as e:
            logger.debug("eastmoney_comment: comment summary failed: %s", e)

    def _fetch_desire(self, akshare, code, ticker, report):
        """散户参与意愿（最近 5 个交易日）。"""
        try:
            df = akshare.stock_comment_detail_scrd_desire_em(symbol=code)
            if df is None or df.empty:
                return
            recent = df.tail(5)
            lines = []
            for _, row in recent.iterrows():
                date = row.get("交易日期", "")
                desire = row.get("参与意愿", 0)
                change = row.get("参与意愿变化", 0)
                change_str = f"+{change:.1f}" if change > 0 else f"{change:.1f}"
                lines.append(f"{date}: {desire:.1f} ({change_str})")

            report.items.append(SentimentData(
                source=self.name,
                ticker=ticker,
                title="散户参与意愿 (近5日)",
                content=" | ".join(lines),
            ))
        except Exception as e:
            logger.debug("eastmoney_comment: desire failed: %s", e)

    def _fetch_rating_history(self, akshare, code, ticker, report):
        """综合评价历史评分（最近 5 个交易日）。"""
        try:
            df = akshare.stock_comment_detail_zhpj_lspf_em(symbol=code)
            if df is None or df.empty:
                return
            recent = df.tail(5)
            lines = []
            for _, row in recent.iterrows():
                date = row.get("交易日", "")
                score = row.get("评分", 0)
                lines.append(f"{date}: {score:.1f}")

            report.items.append(SentimentData(
                source=self.name,
                ticker=ticker,
                title="综合评价评分 (近5日)",
                content=" | ".join(lines),
            ))
        except Exception as e:
            logger.debug("eastmoney_comment: rating history failed: %s", e)
