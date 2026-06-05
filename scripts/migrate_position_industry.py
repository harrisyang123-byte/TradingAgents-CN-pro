"""历史持仓 name + industry 字段批量补填

用法：
    python scripts/migrate_position_industry.py [--dry-run] [--user-id USER_ID]

补填逻辑：
  - name 为空时通过 HTTP API 调用 add_position 重构入口补填
  - industry 为空或=未分类时重新分类
"""

import asyncio
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def _get_fund_name(code: str) -> str:
    try:
        from app.services.fund_service import FundService
        info = await FundService().get_basic_info(code)
        return (info or {}).get("name", "") or ""
    except Exception:
        return ""


async def _get_stock_name(code: str) -> str:
    try:
        import akshare as ak
        df = await asyncio.to_thread(ak.stock_individual_info_em, symbol=code)
        if df is not None and not df.empty:
            nr = df[df["item"] == "股票简称"]
            if not nr.empty:
                return str(nr["value"].iloc[0])
    except Exception:
        pass
    return ""


async def migrate(dry_run=False, user_id=None):
    from app.core.database import get_mongo_db
    from app.services.industry_classifier import classify_by_akshare

    db = get_mongo_db()
    query = {"$or": [
        {"name": {"$in": [None, ""]}},
        {"industry": {"$in": [None, "", "未分类"]}},
    ]}
    if user_id:
        query["user_id"] = user_id

    cursor = db["paper_positions"].find(query)
    positions = await cursor.to_list(None)
    print(f"找到 {len(positions)} 条待补填记录")

    filled_name = 0
    filled_industry = 0
    errors = 0

    for pos in positions:
        code = pos.get("code", "")
        itype = pos.get("instrument_type", "stock")
        updates = {}

        # 补填 name
        name = pos.get("name", "")
        if not name:
            try:
                if itype in ("fund", "etf", "other", "bond"):
                    name = await _get_fund_name(code)
                else:
                    name = await _get_stock_name(code)
                if name:
                    updates["name"] = name
                    filled_name += 1
            except Exception as e:
                print(f"  ✗ {code}: name 查询失败 {e}")

        # 补填 industry
        industry = pos.get("industry", "")
        if not industry or industry == "未分类":
            try:
                industry = await classify_by_akshare(
                    code=code, name=name, instrument_type=itype
                )
                updates["industry"] = industry
                filled_industry += 1
            except Exception as e:
                print(f"  ✗ {code}: 行业分类失败 {e}")

        if updates:
            print(f"  {'[dry]' if dry_run else '✓'} {code} name={updates.get('name', pos.get('name',''))} industry={updates.get('industry', pos.get('industry',''))}")
            if not dry_run:
                await db["paper_positions"].update_one(
                    {"_id": pos["_id"]}, {"$set": updates}
                )

    print(f"\n完成: 补填 name {filled_name} 条，industry {filled_industry} 条，错误 {errors} 条")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="补填历史持仓 name + industry")
    parser.add_argument("--dry-run", action="store_true", help="仅预览")
    parser.add_argument("--user-id", type=str, help="指定用户")
    args = parser.parse_args()
    asyncio.run(migrate(dry_run=args.dry_run, user_id=args.user_id))
