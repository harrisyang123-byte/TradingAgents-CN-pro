"""Sentiment analyst — pre-fetch + single LLM call.

Redesigned from the old tool-calling social_media_analyst. The old version
told the LLM to analyze social-media sentiment but only provided a tool
that returned placeholder data for CN/HK markets — causing hallucinated
reports. This version pre-fetches real data from the source registry
(eastmoney, wechat_mp, etc.) and injects it into the prompt so the LLM
analyses only what it is given, in a single invocation with no tool-calling.

Follows the same pattern as TG upstream's sentiment_analyst.py, adapted
for Chinese-market data sources.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tradingagents.agents.analysts.sources import (
    SentimentReport,
    get_enabled_sources,
)
from tradingagents.agents.utils.instrument_utils import build_instrument_context

logger = logging.getLogger(__name__)

_DEFAULT_SOURCES = ["eastmoney", "wechat_mp"]


def _run_async(coro):
    """Run an async coroutine from sync context."""
    try:
        return asyncio.run(coro)
    except RuntimeError:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()


async def _fetch_all(sources, tickers: list[str], timeout: float = 10.0):
    """Fetch sentiment data from all sources for all tickers."""
    reports: dict[str, SentimentReport] = {}
    for ticker in tickers:
        combined = SentimentReport(ticker=ticker)
        for source in sources:
            try:
                result = await asyncio.wait_for(
                    source.fetch([ticker]), timeout=timeout,
                )
                if ticker in result:
                    combined.items.extend(result[ticker].items)
            except asyncio.TimeoutError:
                logger.warning("Sentiment source '%s' timed out for %s", source.name, ticker)
            except Exception as e:
                logger.warning("Sentiment source '%s' failed for %s: %s", source.name, ticker, e)
        if combined.items:
            reports[ticker] = combined
    return reports


def _format_source_blocks(reports: dict[str, SentimentReport]) -> str:
    """Format fetched reports as XML-delimited blocks for prompt injection."""
    if not reports:
        return "<sentiment_data>\n暂无情绪数据可用。\n</sentiment_data>"

    parts = []
    for ticker, report in reports.items():
        by_source: dict[str, list] = {}
        for item in report.items:
            by_source.setdefault(item.source, []).append(item)

        for source_name, items in by_source.items():
            lines = []
            for item in items:
                ts = f"[{item.timestamp}] " if item.timestamp else ""
                score = f" (情绪分: {item.sentiment_score:+.2f})" if item.sentiment_score is not None else ""
                lines.append(f"{ts}{item.title}{score}")
                if item.content:
                    lines.append(f"  {item.content[:240]}")
            block = "\n".join(lines)
            parts.append(
                f"<start_of_{source_name}>\n{block}\n<end_of_{source_name}>"
            )

    return "\n\n".join(parts) if parts else "<sentiment_data>\n暂无情绪数据可用。\n</sentiment_data>"


def _build_system_message(
    *,
    ticker: str,
    source_blocks: str,
    source_names: list[str],
) -> str:
    """Assemble the sentiment analyst system message with data blocks."""
    source_desc = "、".join(source_names) if source_names else "无"
    return f"""您是一位专业的金融市场情绪分析师。您的任务是基于已为您预先收集的数据，为 {ticker} 撰写一份全面的情绪分析报告。

## 数据来源（已预抓取，嵌入在本提示中）

数据来源渠道：{source_desc}

{source_blocks}

## 分析方法（最佳实践）

1. **评估数据量和质量**。如果某个来源返回的数据较少或标注为"unavailable"，请明确指出数据局限性，不要凭空推测。
2. **识别情绪方向**。综合所有来源的数据判断：看涨（Bullish）/ 看跌（Bearish）/ 中性（Neutral）/ 混合（Mixed）。
3. **区分事实与观点**。新闻标题是事件，论坛评论是观点——两者都是输入，但权重不同。
4. **识别跨来源的一致性和分歧**。多个来源指向同一方向说明信号较强；来源之间的分歧本身也是一个信号。
5. **识别关键催化剂和风险**。找出推动情绪变化的核心事件：政策变化、财报、行业动态等。
6. **情绪不等于预测**。将结论定位为交易决策的参考信号之一，而非价格预测。

## 输出要求

请按以下顺序撰写报告：

1. **整体情绪方向** — Bullish / Bearish / Neutral / Mixed，附置信度说明
2. **逐来源分析** — 每个数据来源告诉了什么，引用具体数据
3. **跨来源一致性与分歧**
4. **关键催化剂与风险**
5. **Markdown 表格**总结关键情绪信号、方向、来源和证据

请用中文撰写所有分析内容。"""


def create_sentiment_analyst(
    llm,
    source_names: Optional[list[str]] = None,
    source_config: Optional[dict[str, Any]] = None,
):
    """Create a sentiment analyst node for the trading graph.

    Pre-fetches data from the source registry, injects into prompt,
    produces a sentiment report in a single LLM call.

    Args:
        llm: LangChain LLM instance.
        source_names: List of source names to enable (default: eastmoney, wechat_mp).
        source_config: Optional per-source kwargs keyed by source name.

    Returns:
        A callable graph node function.
    """
    if source_names is None:
        source_names = list(_DEFAULT_SOURCES)
    sources = get_enabled_sources(source_names, source_config)
    active_names = [s.name for s in sources]
    logger.info("SentimentAnalyst created with sources: %s", active_names or ["(none)"])

    def sentiment_analyst_node(state):
        ticker = state["company_of_interest"]
        instrument_context = build_instrument_context(ticker)

        reports = _run_async(_fetch_all(sources, [ticker]))
        source_blocks = _format_source_blocks(reports)

        item_count = sum(len(r.items) for r in reports.values())
        logger.info("[Sentiment Analyst] Pre-fetched %d items from %s for %s",
                     item_count, active_names, ticker)

        system_message = _build_system_message(
            ticker=ticker,
            source_blocks=source_blocks,
            source_names=active_names,
        )

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "您是一位有用的AI助手，与其他助手协作。"
                " 如果您或任何其他助手有最终交易提案：**买入/持有/卖出**或可交付成果，"
                " 请在您的回应前加上最终交易提案：**买入/持有/卖出**，以便团队知道停止。"
                "\n{system_message}\n"
                "供您参考，当前日期是{current_date}。{instrument_context}",
            ),
            MessagesPlaceholder(variable_name="messages"),
        ])

        prompt = prompt.partial(
            system_message=system_message,
            current_date=state.get("trade_date", ""),
            instrument_context=instrument_context,
        )

        chain = prompt | llm
        result = chain.invoke(state["messages"])

        return {
            "messages": [result],
            "sentiment_report": result.content,
        }

    return sentiment_analyst_node
