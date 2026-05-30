import pandas as pd
import yfinance as yf
from stockstats import wrap
from typing import Annotated
import os
from tradingagents.config.config_manager import config_manager

def get_config():
    """兼容性包装函数"""
    return config_manager.load_settings()


def _is_china_a_share(symbol: str) -> bool:
    """Check if symbol is a Chinese A-share (6-digit code, optionally with suffix)."""
    s = str(symbol).strip().upper()
    if s.endswith((".SH", ".SS", ".SZ", ".XSHG", ".XSHE")):
        return True
    return s.isdigit() and len(s) == 6


def _fetch_china_ohlcv(symbol: str, start_date: str, end_date: str):
    """Fetch OHLCV data for Chinese A-shares from MongoDB instead of yfinance."""
    code = str(symbol).strip().upper()
    for suffix in (".SH", ".SS", ".SZ", ".XSHG", ".XSHE"):
        code = code.replace(suffix, "")

    # Try app-level get_mongo_db first
    try:
        from app.core.database import get_mongo_db
        db = get_mongo_db()
        cursor = db["stock_daily_quotes"].find(
            {"code": code, "date": {"$gte": start_date, "$lte": end_date}},
            {"_id": 0, "date": 1, "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1},
        ).sort("date", 1)
        rows = list(cursor)
        if rows:
            df = pd.DataFrame(rows)
            df = df.rename(columns={
                "date": "Date", "open": "Open", "high": "High",
                "low": "Low", "close": "Close", "volume": "Volume",
            })
            df["Date"] = pd.to_datetime(df["Date"])
            return df
    except Exception:
        pass

    # Fall back: direct pymongo connection from settings
    try:
        from pymongo import MongoClient
        from app.core.config import settings
        client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client[settings.MONGO_DB]
        cursor = db["stock_daily_quotes"].find(
            {"code": code, "date": {"$gte": start_date, "$lte": end_date}},
            {"_id": 0, "date": 1, "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1},
        ).sort("date", 1)
        rows = list(cursor)
        client.close()
        if rows:
            df = pd.DataFrame(rows)
            df = df.rename(columns={
                "date": "Date", "open": "Open", "high": "High",
                "low": "Low", "close": "Close", "volume": "Volume",
            })
            df["Date"] = pd.to_datetime(df["Date"])
            return df
    except Exception:
        pass

    return None


class StockstatsUtils:
    @staticmethod
    def get_stock_stats(
        symbol: Annotated[str, "ticker symbol for the company"],
        indicator: Annotated[
            str, "quantitative indicators based off of the stock data for the company"
        ],
        curr_date: Annotated[
            str, "curr date for retrieving stock price data, YYYY-mm-dd"
        ],
        data_dir: Annotated[
            str,
            "directory where the stock data is stored.",
        ],
        online: Annotated[
            bool,
            "whether to use online tools to fetch data or offline tools. If True, will use online tools.",
        ] = False,
    ):
        df = None
        data = None

        if not online:
            try:
                data = pd.read_csv(
                    os.path.join(
                        data_dir,
                        f"{symbol}-YFin-data-2015-01-01-2025-03-25.csv",
                    )
                )
                df = wrap(data)
            except FileNotFoundError:
                raise Exception("Stockstats fail: Yahoo Finance data not fetched yet!")
        else:
            # Get today's date as YYYY-mm-dd to add to cache
            today_date = pd.Timestamp.today()
            curr_date = pd.to_datetime(curr_date)

            end_date = today_date
            start_date = today_date - pd.DateOffset(years=15)
            start_date = start_date.strftime("%Y-%m-%d")
            end_date = end_date.strftime("%Y-%m-%d")

            # Get config and ensure cache directory exists
            config = get_config()
            os.makedirs(config["data_cache_dir"], exist_ok=True)

            data_file = os.path.join(
                config["data_cache_dir"],
                f"{symbol}-YFin-data-{start_date}-{end_date}.csv",
            )

            if os.path.exists(data_file):
                data = pd.read_csv(data_file)
                data["Date"] = pd.to_datetime(data["Date"])
            elif _is_china_a_share(symbol):
                data = _fetch_china_ohlcv(symbol, start_date, end_date)
                if data is None or data.empty:
                    try:
                        from tradingagents.dataflows.interface import get_china_stock_data_unified
                        result = get_china_stock_data_unified(symbol, start_date, end_date)
                        if result and "❌" not in result:
                            import io
                            data = pd.read_csv(io.StringIO(result), skiprows=3)
                            if "Date" not in data.columns and "date" not in data.columns:
                                data = None
                    except Exception:
                        data = None
                    if data is None or data.empty:
                        data = yf.download(
                            symbol,
                            start=start_date,
                            end=end_date,
                            multi_level_index=False,
                            progress=False,
                            auto_adjust=True,
                        )
                        data = data.reset_index()
                data.to_csv(data_file, index=False)
            else:
                data = yf.download(
                    symbol,
                    start=start_date,
                    end=end_date,
                    multi_level_index=False,
                    progress=False,
                    auto_adjust=True,
                )
                data = data.reset_index()
                data.to_csv(data_file, index=False)

            df = wrap(data)
            df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
            curr_date = curr_date.strftime("%Y-%m-%d")

        df[indicator]  # trigger stockstats to calculate the indicator
        matching_rows = df[df["Date"].str.startswith(curr_date)]

        if not matching_rows.empty:
            indicator_value = matching_rows[indicator].values[0]
            return indicator_value
        else:
            return "N/A: Not a trading day (weekend or holiday)"
