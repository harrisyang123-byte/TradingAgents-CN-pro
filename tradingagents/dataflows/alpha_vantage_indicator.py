"""Alpha Vantage technical indicator API wrapper."""

from datetime import datetime, timedelta

from .alpha_vantage_common import _make_api_request

_INDICATOR_DESCRIPTIONS = {
    "close_50_sma": "50 SMA: Medium-term trend indicator.",
    "close_200_sma": "200 SMA: Long-term trend benchmark.",
    "close_10_ema": "10 EMA: Responsive short-term average.",
    "macd": "MACD: Momentum via differences of EMAs.",
    "macds": "MACD Signal: EMA smoothing of the MACD line.",
    "macdh": "MACD Histogram: Gap between MACD and signal.",
    "rsi": "RSI: Overbought/oversold momentum indicator.",
    "boll": "Bollinger Middle: 20 SMA baseline.",
    "boll_ub": "Bollinger Upper Band: 2 std dev above middle.",
    "boll_lb": "Bollinger Lower Band: 2 std dev below middle.",
    "atr": "ATR: Average true range volatility measure.",
    "vwma": "VWMA: Volume-weighted moving average.",
}

_API_FUNCTION_MAP = {
    "close_50_sma": ("SMA", {"time_period": "50"}),
    "close_200_sma": ("SMA", {"time_period": "200"}),
    "close_10_ema": ("EMA", {"time_period": "10"}),
    "macd": ("MACD", {}),
    "macds": ("MACD", {}),
    "macdh": ("MACD", {}),
    "rsi": ("RSI", {}),
    "boll": ("BBANDS", {"time_period": "20"}),
    "boll_ub": ("BBANDS", {"time_period": "20"}),
    "boll_lb": ("BBANDS", {"time_period": "20"}),
    "atr": ("ATR", {}),
}

_COL_NAME_MAP = {
    "macd": "MACD",
    "macds": "MACD_Signal",
    "macdh": "MACD_Hist",
    "boll": "Real Middle Band",
    "boll_ub": "Real Upper Band",
    "boll_lb": "Real Lower Band",
    "rsi": "RSI",
    "atr": "ATR",
    "close_10_ema": "EMA",
    "close_50_sma": "SMA",
    "close_200_sma": "SMA",
}


def get_indicator(
    symbol: str,
    indicator: str,
    curr_date: str,
    look_back_days: int,
    interval: str = "daily",
    time_period: int = 14,
    series_type: str = "close",
) -> str:
    """Return Alpha Vantage technical indicator values over a time window."""
    if indicator not in _API_FUNCTION_MAP and indicator != "vwma":
        raise ValueError(
            f"Indicator {indicator} not supported. Choose from: "
            f"{list(_API_FUNCTION_MAP.keys()) + ['vwma']}"
        )

    curr_date_dt = datetime.strptime(curr_date, "%Y-%m-%d")
    before = curr_date_dt - timedelta(days=look_back_days)

    if indicator == "vwma":
        return (
            f"## VWMA for {symbol}:\n\n"
            "VWMA is not directly available from Alpha Vantage API.\n\n"
            + _INDICATOR_DESCRIPTIONS.get("vwma", "")
        )

    func_name, extra_params = _API_FUNCTION_MAP[indicator]
    params = {
        "symbol": symbol,
        "interval": interval,
        "series_type": series_type,
        "datatype": "csv",
    }
    if "time_period" not in extra_params and func_name in ("RSI", "ATR"):
        params["time_period"] = str(time_period)
    params.update(extra_params)

    try:
        data = _make_api_request(func_name, params)
        lines = data.strip().split("\n")
        if len(lines) < 2:
            return f"Error: No data returned for {indicator}"

        header = [col.strip() for col in lines[0].split(",")]
        try:
            date_col_idx = header.index("time")
        except ValueError:
            return f"Error: 'time' column not found. Columns: {header}"

        target_col = _COL_NAME_MAP.get(indicator)
        value_col_idx = header.index(target_col) if target_col and target_col in header else 1

        result_data = []
        for line in lines[1:]:
            if not line.strip():
                continue
            values = line.split(",")
            if len(values) > value_col_idx:
                try:
                    date_str = values[date_col_idx].strip()
                    date_dt = datetime.strptime(date_str, "%Y-%m-%d")
                    if before <= date_dt <= curr_date_dt:
                        result_data.append((date_dt, values[value_col_idx].strip()))
                except (ValueError, IndexError):
                    continue

        result_data.sort(key=lambda x: x[0])
        ind_string = "".join(
            f"{dt.strftime('%Y-%m-%d')}: {val}\n" for dt, val in result_data
        ) or "No data available for the specified date range.\n"

        return (
            f"## {indicator.upper()} from {before.strftime('%Y-%m-%d')} to {curr_date}:\n\n"
            + ind_string
            + "\n"
            + _INDICATOR_DESCRIPTIONS.get(indicator, "")
        )
    except Exception as e:
        return f"Error retrieving {indicator} data: {e}"
