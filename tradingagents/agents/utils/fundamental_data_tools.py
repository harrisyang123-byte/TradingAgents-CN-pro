from langchain_core.tools import tool
from typing import Annotated

from tradingagents.utils.stock_utils import StockUtils


@tool
def get_fundamentals(
    ticker: Annotated[str, "ticker symbol"],
    curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"],
) -> str:
    """
    Retrieve comprehensive fundamental data for a given ticker symbol.
    Automatically detects market type (A-share, HK, US) and uses the appropriate data source.
    Args:
        ticker (str): Ticker symbol of the company
        curr_date (str): Current date you are trading at, yyyy-mm-dd
    Returns:
        str: A formatted report containing comprehensive fundamental data
    """
    import tradingagents.dataflows.interface as interface

    market_info = StockUtils.get_market_info(ticker)

    if market_info["is_china"]:
        return interface.get_china_stock_fundamentals_tushare(ticker, curr_date)
    elif market_info["is_hk"]:
        return interface.get_fundamentals_openai(ticker, curr_date)
    else:
        return interface.get_fundamentals_openai(ticker, curr_date)


@tool
def get_balance_sheet(
    ticker: Annotated[str, "ticker symbol"],
    freq: Annotated[str, "reporting frequency: annual/quarterly"] = "quarterly",
    curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"] = None,
) -> str:
    """
    Retrieve balance sheet data for a given ticker symbol.
    Args:
        ticker (str): Ticker symbol of the company
        freq (str): Reporting frequency: annual/quarterly (default quarterly)
        curr_date (str): Current date you are trading at, yyyy-mm-dd
    Returns:
        str: A formatted report containing balance sheet data
    """
    import tradingagents.dataflows.interface as interface

    market_info = StockUtils.get_market_info(ticker)
    if market_info["is_china"]:
        return interface.get_china_stock_fundamentals_tushare(ticker, curr_date)
    if market_info["is_hk"]:
        return _hk_financial_stmt_unavailable(ticker, "balance sheet", curr_date)
    return interface.get_simfin_balance_sheet(ticker, freq, curr_date)


@tool
def get_cashflow(
    ticker: Annotated[str, "ticker symbol"],
    freq: Annotated[str, "reporting frequency: annual/quarterly"] = "quarterly",
    curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"] = None,
) -> str:
    """
    Retrieve cash flow statement data for a given ticker symbol.
    Args:
        ticker (str): Ticker symbol of the company
        freq (str): Reporting frequency: annual/quarterly (default quarterly)
        curr_date (str): Current date you are trading at, yyyy-mm-dd
    Returns:
        str: A formatted report containing cash flow statement data
    """
    import tradingagents.dataflows.interface as interface

    market_info = StockUtils.get_market_info(ticker)
    if market_info["is_china"]:
        return interface.get_china_stock_fundamentals_tushare(ticker, curr_date)
    if market_info["is_hk"]:
        return _hk_financial_stmt_unavailable(ticker, "cash flow", curr_date)
    return interface.get_simfin_cashflow(ticker, freq, curr_date)


@tool
def get_income_statement(
    ticker: Annotated[str, "ticker symbol"],
    freq: Annotated[str, "reporting frequency: annual/quarterly"] = "quarterly",
    curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"] = None,
) -> str:
    """
    Retrieve income statement data for a given ticker symbol.
    Args:
        ticker (str): Ticker symbol of the company
        freq (str): Reporting frequency: annual/quarterly (default quarterly)
        curr_date (str): Current date you are trading at, yyyy-mm-dd
    Returns:
        str: A formatted report containing income statement data
    """
    import tradingagents.dataflows.interface as interface

    market_info = StockUtils.get_market_info(ticker)
    if market_info["is_china"]:
        return interface.get_china_stock_fundamentals_tushare(ticker, curr_date)
    if market_info["is_hk"]:
        return _hk_financial_stmt_unavailable(ticker, "income statement", curr_date)
    return interface.get_simfin_income_statements(ticker, freq, curr_date)


def _hk_financial_stmt_unavailable(ticker: str, stmt_type: str, curr_date: str) -> str:
    """港股财务报表数据不可用时的降级提示"""
    return (
        f"⚠️ 港股 {ticker} 的 {stmt_type} 报表数据不可用。"
        f"SimFin 数据库仅覆盖美股，不包含港股财务报表。"
        f"请基于已有的行情数据和技术面信息继续分析，不要为缺失的财务数据反复调用工具。"
        f"（数据获取时间: {curr_date}）"
    )
