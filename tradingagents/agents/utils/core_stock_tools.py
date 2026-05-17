from langchain_core.tools import tool
from typing import Annotated

from tradingagents.utils.stock_utils import StockUtils


@tool
def get_stock_data(
    symbol: Annotated[str, "ticker symbol of the company"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """
    Retrieve stock price data (OHLCV) for a given ticker symbol.
    Automatically detects market type (A-share, HK, US) and uses the appropriate data source.
    Args:
        symbol (str): Ticker symbol of the company, e.g. AAPL, 600519, 0700.HK
        start_date (str): Start date in yyyy-mm-dd format
        end_date (str): End date in yyyy-mm-dd format
    Returns:
        str: A formatted dataframe containing the stock price data.
    """
    import tradingagents.dataflows.interface as interface

    market_info = StockUtils.get_market_info(symbol)

    if market_info["is_china"]:
        return interface.get_china_stock_data_unified(symbol, start_date, end_date)
    elif market_info["is_hk"]:
        return interface.get_hk_stock_data_unified(symbol, start_date, end_date)
    else:
        return interface.get_YFin_data_online(symbol, start_date, end_date)
