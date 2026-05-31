"""Seed daily quote data for P0-1a stocks using BaoStock."""
import os, sys, asyncio
os.chdir("/Users/yangyanyu/AI-Coding-Engine/domains/tradingagents-cn")
sys.path.insert(0, ".")

import baostock as bs
import pandas as pd
from datetime import datetime

STOCKS = ["603663", "002517", "603236", "000063", "002415", "002001", "002050"]


def fetch_baostock(code: str):
    prefix = "sh." if code.startswith("6") else "sz."
    rs = bs.query_history_k_data_plus(
        prefix + code,
        "date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,"
        "tradestatus,pctChg,peTTM,pbMRQ,psTTM,pcfNcfTTM,isST",
        start_date="2025-01-01", end_date="2026-05-30",
        frequency="d", adjustflag="2",
    )
    rows = []
    while (rs.error_code == "0") and rs.next():
        rows.append(rs.get_row_data())
    if not rows:
        return None
    df = pd.DataFrame(rows, columns=[
        "date", "code", "open", "high", "low", "close", "preclose",
        "volume", "amount", "adjustflag", "turn", "tradestatus",
        "pctChg", "peTTM", "pbMRQ", "psTTM", "pcfNcfTTM", "isST",
    ])
    for c in ["open", "high", "low", "close", "preclose", "volume", "amount",
              "turn", "pctChg", "peTTM", "pbMRQ", "psTTM", "pcfNcfTTM"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


async def seed():
    from dotenv import load_dotenv
    load_dotenv()
    import motor.motor_asyncio
    url = os.getenv("MONGODB_CONNECTION_STRING")
    db_name = os.getenv("MONGODB_DATABASE", "tradingagentscn")
    # Resolve the actual database name (same logic as app)
    from app.core.config import settings
    db_name = settings.MONGO_DB
    print(f"DB: {db_name}")

    client = motor.motor_asyncio.AsyncIOMotorClient(url)
    db = client[db_name]

    bs.login()

    total = 0
    for code in STOCKS:
        df = fetch_baostock(code)
        if df is None or df.empty:
            print(f"  {code}: no data")
            continue
        # Upsert: delete old, insert new
        await db["stock_daily_quotes"].delete_many({"code": code})
        records = []
        for _, row in df.iterrows():
            records.append({
                "code": code,
                "symbol": code,
                "date": str(row["date"]),
                "open": row["open"],
                "high": row["high"],
                "low": row["low"],
                "close": row["close"],
                "pre_close": row["preclose"],
                "volume": row["volume"],
                "amount": row["amount"],
                "turnover_rate": row.get("turn"),
                "change_pct": row.get("pctChg"),
                "pe_ttm": row.get("peTTM"),
                "pb": row.get("pbMRQ"),
                "created_at": datetime.utcnow().isoformat(),
            })
        if records:
            await db["stock_daily_quotes"].insert_many(records)
            total += len(records)
            print(f"  {code}: {len(records)} rows")

    bs.logout()
    print(f"Done: {total} records for {len(STOCKS)} stocks")


if __name__ == "__main__":
    asyncio.run(seed())
