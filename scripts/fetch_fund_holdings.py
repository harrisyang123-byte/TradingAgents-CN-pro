"""批量拉取基金重仓股数据 — Step 1"""
import asyncio
import sys
import os
import logging

sys.path.insert(0, "/Users/yangyanyu/AI-Coding-Engine/domains/tradingagents-cn")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("fund_holdings_fetch")

os.environ.setdefault("MONGODB_HOST", "localhost")
os.environ.setdefault("MONGODB_PORT", "27017")
os.environ.setdefault("MONGODB_DATABASE", "tradingagentscn")

from app.core.database import init_database, get_mongo_db
from app.services.fund_service import FundService

FUND_CODES = [
    "270042", "024245", "110008", "110017", "007029", "012733",
    "019058", "009052", "000307", "012734", "110020", "010736",
    "000205", "006327", "161130", "270010", "022424", "270023",
    "003765", "008987", "012629", "005063", "013180", "009881",
    "270044", "003376", "GF-GLOBAL-STABLE",
]


async def fetch_all():
    await init_database()
    db = get_mongo_db()
    service = FundService()
    service._db = db  # 复用已初始化的 db

    results = {}
    errors = []
    total = len(FUND_CODES)
    batch_size = 5

    for i in range(0, total, batch_size):
        batch = FUND_CODES[i : i + batch_size]
        logger.info(f"批次 {i // batch_size + 1}: {batch}")

        async def fetch_one(code):
            try:
                holdings = await asyncio.wait_for(
                    service.get_top_holdings(code), timeout=20.0
                )
                return code, holdings, None
            except Exception as e:
                return code, None, str(e)

        batch_results = await asyncio.gather(*[fetch_one(c) for c in batch])

        for code, holdings, err in batch_results:
            if err:
                logger.warning(f"  {code}: 失败 - {err}")
                errors.append((code, err))
            elif holdings is None:
                logger.warning(f"  {code}: 返回 None（AKShare 异常）")
                errors.append((code, "返回 None"))
            elif len(holdings) == 0:
                logger.info(f"  {code}: 无重仓股数据（QDII/ETF/货基）")
                results[code] = []
            else:
                names = [h["stock_name"] for h in holdings[:5]]
                logger.info(f"  {code}: {len(holdings)} 只重仓股 - {names}")
                results[code] = holdings

        # 批次间短暂等待，避免 AKShare 限流
        if i + batch_size < total:
            await asyncio.sleep(1.5)

    print("\n=== 汇总 ===")
    print(f"成功获取: {len(results)} 只基金")
    print(f"有重仓股: {sum(1 for v in results.values() if v)} 只")
    print(f"无数据(QDII/ETF): {sum(1 for v in results.values() if not v)} 只")
    print(f"失败: {len(errors)} 只")
    if errors:
        for code, err in errors:
            print(f"  - {code}: {err}")

    # 汇总所有底层股票
    all_stocks = set()
    for code, holdings in results.items():
        for h in holdings:
            all_stocks.add((h["stock_code"], h["stock_name"]))

    print(f"\n底层股票去重: {len(all_stocks)} 只")
    for sc, sn in sorted(all_stocks, key=lambda x: x[0]):
        print(f"  {sc} {sn}")

    # 保存股票列表供下一步使用
    with open("/tmp/fund_underlying_stocks.txt", "w") as f:
        for sc, sn in sorted(all_stocks, key=lambda x: x[0]):
            f.write(f"{sc}\t{sn}\n")

    return results, all_stocks


if __name__ == "__main__":
    asyncio.run(fetch_all())
