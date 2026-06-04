"""历史持仓行业字段批量补填

为 paper_positions 集合中 industry 字段为空的历史记录补填行业分类。
使用 AKShare 优先，关键词回退，失败标记为「未分类」。

用法：
    python scripts/migrate_position_industry.py [--dry-run] [--user-id USER_ID]
"""

import asyncio
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def migrate(dry_run: bool = False, user_id: str = None):
    from app.database import get_mongo_db
    from app.services.industry_classifier import classify_by_akshare

    db = get_mongo_db()

    query = {"industry": {"$in": [None, "", "未分类"]}}
    if user_id:
        query["user_id"] = user_id

    cursor = db["paper_positions"].find(query)
    positions = await cursor.to_list(None)

    print(f"找到 {len(positions)} 条需要补填的持仓记录")
    if dry_run:
        print("[dry-run] 不会写入数据库")

    success = 0
    failed = 0
    unclassified = 0

    for pos in positions:
        code = pos.get("code", "")
        instrument_type = pos.get("instrument_type", "stock")
        try:
            industry = await classify_by_akshare(
                code=code,
                name="",
                instrument_type=instrument_type,
            )
        except Exception as e:
            print(f"  ✗ {code}: 分类异常 {e}")
            industry = "未分类"
            failed += 1

        if industry == "未分类":
            unclassified += 1
        else:
            success += 1

        print(f"  {'[dry]' if dry_run else '✓'} {code} → {industry}")

        if not dry_run:
            await db["paper_positions"].update_one(
                {"_id": pos["_id"]},
                {"$set": {"industry": industry}},
            )

    print(f"\n迁移完成：成功 {success}，未分类 {unclassified}，异常 {failed}，共 {len(positions)} 条")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="补填历史持仓行业字段")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不写入")
    parser.add_argument("--user-id", type=str, help="只迁移指定用户的持仓")
    args = parser.parse_args()

    asyncio.run(migrate(dry_run=args.dry_run, user_id=args.user_id))
