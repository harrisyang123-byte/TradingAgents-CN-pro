"""历史持仓 name + industry 批量补填（独立脚本，直接连 MongoDB）"""
import asyncio, argparse, sys, os
from pymongo import MongoClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def _get_fund_name(code: str) -> str:
    try:
        import akshare as ak
        df = await asyncio.to_thread(ak.fund_individual_basic_info_xq, code)
        if df is not None and not df.empty:
            nr = df[df["item"] == "基金简称"]
            if not nr.empty: return str(nr["value"].iloc[0])
    except Exception: pass
    return ""


async def _get_stock_name(code: str) -> str:
    try:
        import akshare as ak
        df = await asyncio.to_thread(ak.stock_individual_info_em, symbol=code)
        if df is not None and not df.empty:
            nr = df[df["item"] == "股票简称"]
            if not nr.empty: return str(nr["value"].iloc[0])
    except Exception: pass
    return ""


async def migrate(dry_run=False, user_id=None):
    mongo_url = os.environ.get("MONGODB_URL", "mongodb://tradingagents:tradingagents_pass@localhost:27017")
    mongo_db = os.environ.get("MONGODB_DATABASE_NAME", "tradingagentscn")
    client = MongoClient(mongo_url)
    db = client[mongo_db]

    query = {"$or": [{"name": {"$in": [None, ""]}}, {"industry": {"$in": [None, "", "未分类"]}}]}
    if user_id: query["user_id"] = user_id

    positions = list(db["paper_positions"].find(query))
    print(f"找到 {len(positions)} 条待补填")

    fn, fi, errs = 0, 0, 0
    for pos in positions:
        code = pos.get("code", "")
        itype = pos.get("instrument_type", "stock")
        name = pos.get("name", "")
        updates = {}

        if not name:
            try:
                name = await (_get_fund_name(code) if itype in ("fund", "etf", "other", "bond") else _get_stock_name(code))
                if name: updates["name"] = name; fn += 1
            except Exception as e: print(f"  ✗ {code}: name fail {e}")

        industry = pos.get("industry", "")
        if not industry or industry == "未分类":
            try:
                from app.services.industry_buckets import _fallback_classify
                industry = _fallback_classify(code, name or "", itype)
                if industry == "其他": industry = "未分类"
                updates["industry"] = industry; fi += 1
            except Exception as e: print(f"  ✗ {code}: classify fail {e}")

        if updates:
            print(f"  {'[dry]' if dry_run else '✓'} {code:8s} name={updates.get('name', pos.get('name','')):20s} industry={updates.get('industry', pos.get('industry',''))}")
            if not dry_run: db["paper_positions"].update_one({"_id": pos["_id"]}, {"$set": updates})

    print(f"\n完成: name {fn}, industry {fi}, errors {errs}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="补填历史持仓 name + industry")
    p.add_argument("--dry-run", action="store_true"); p.add_argument("--user-id", type=str)
    args = p.parse_args()
    asyncio.run(migrate(dry_run=args.dry_run, user_id=args.user_id))
