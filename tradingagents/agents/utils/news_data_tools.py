from langchain_core.tools import tool
from typing import Annotated, Optional

from tradingagents.utils.stock_utils import StockUtils


@tool
def get_news(
    ticker: Annotated[str, "Ticker symbol"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """
    Retrieve news data for a given ticker symbol.
    Automatically detects market type and uses the appropriate news source.
    Args:
        ticker (str): Ticker symbol
        start_date (str): Start date in yyyy-mm-dd format
        end_date (str): End date in yyyy-mm-dd format
    Returns:
        str: A formatted string containing news data
    """
    import tradingagents.dataflows.interface as interface

    market_info = StockUtils.get_market_info(ticker)

    if market_info["is_china"] or market_info["is_hk"]:
        from tradingagents.dataflows.providers.china.akshare import AKShareProvider

        provider = AKShareProvider()
        clean_ticker = (
            ticker.replace(".SH", "").replace(".SZ", "").replace(".SS", "")
            .replace(".XSHG", "").replace(".XSHE", "").replace(".HK", "")
        )
        news_df = provider.get_stock_news_sync(symbol=clean_ticker)
        if news_df is not None and not news_df.empty:
            items = []
            for _, row in news_df.iterrows():
                title = row.get("新闻标题", "") or row.get("标题", "")
                time_str = row.get("发布时间", "") or row.get("时间", "")
                items.append(f"- {title} [{time_str}]")
            return "\n".join(items)
        return f"No news found for {ticker} in the specified date range."
    else:
        return interface.get_finnhub_news(ticker, end_date, 7)


@tool
def get_global_news(
    curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    look_back_days: Annotated[Optional[int], "Days to look back"] = None,
    limit: Annotated[Optional[int], "Max articles to return"] = None,
) -> str:
    """
    Retrieve global news data.
    Args:
        curr_date (str): Current date in yyyy-mm-dd format
        look_back_days (int): Number of days to look back
        limit (int): Maximum number of articles to return
    Returns:
        str: A formatted string containing global news data
    """
    import tradingagents.dataflows.interface as interface

    if look_back_days is None:
        look_back_days = 7
    if limit is None:
        limit = 5
    return interface.get_reddit_global_news(curr_date, look_back_days, limit)


@tool
def get_insider_transactions(
    ticker: Annotated[str, "ticker symbol"],
) -> str:
    """
    Retrieve insider transaction information about a company.
    Args:
        ticker (str): Ticker symbol of the company
    Returns:
        str: A report of insider transaction data
    """
    import tradingagents.dataflows.interface as interface

    market_info = StockUtils.get_market_info(ticker)
    if market_info["is_china"] or market_info["is_hk"]:
        return "Insider transaction data is not available for this market."
    return interface.get_finnhub_company_insider_transactions(ticker, None, 30)
