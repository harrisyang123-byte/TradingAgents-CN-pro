from langchain_core.tools import tool
from typing import Annotated

import tradingagents.dataflows.interface as interface


@tool
def get_indicators(
    symbol: Annotated[str, "ticker symbol of the company"],
    indicator: Annotated[str, "technical indicator to get the analysis and report of"],
    curr_date: Annotated[str, "The current trading date you are trading on, YYYY-mm-dd"],
    look_back_days: Annotated[int, "how many days to look back"] = 30,
) -> str:
    """
    Retrieve a single technical indicator for a given ticker symbol.
    Args:
        symbol (str): Ticker symbol of the company, e.g. AAPL, 600519, 0700.HK
        indicator (str): A single technical indicator name, e.g. 'rsi', 'macd'. Call this tool once per indicator.
        curr_date (str): The current trading date you are trading on, YYYY-mm-dd
        look_back_days (int): How many days to look back, default is 30
    Returns:
        str: A formatted dataframe containing the technical indicators.
    """
    indicators = [i.strip().lower() for i in indicator.split(",") if i.strip()]
    results = []
    for ind in indicators:
        try:
            results.append(
                interface.get_stock_stats_indicators_window(
                    symbol, ind, curr_date, look_back_days, True
                )
            )
        except ValueError as e:
            results.append(str(e))
    return "\n\n".join(results)
