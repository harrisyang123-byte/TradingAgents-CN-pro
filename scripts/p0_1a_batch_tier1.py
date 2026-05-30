"""P0-1a: Batch run Tier 1 analysis for 7 A-share holdings."""
import asyncio
import os
import sys

os.chdir("/Users/yangyanyu/AI-Coding-Engine/domains/tradingagents-cn")
sys.path.insert(0, ".")

from app.services.simple_analysis_service import SimpleAnalysisService
from app.models.analysis import SingleAnalysisRequest, AnalysisParameters
from app.core.database import DatabaseManager

STOCKS = ["603663", "002517", "603236", "000063", "002415", "002001", "002050"]
USER_ID = "6a094caea814b57d3357fa0b"
DELAY = 2


async def init_db():
    """Manually init DB (normally done by FastAPI lifespan)."""
    from app.core.database import init_database
    await init_database()
    from app.core.config import settings
    print(f"DB connected: {settings.MONGO_DB}")


async def run_one(svc, code, idx, total):
    req = SingleAnalysisRequest(
        symbol=code,
        parameters=AnalysisParameters(
            research_depth="标准",
            market_type="A股",
            instrument_type="stock",
            selected_analysts=["market", "fundamentals"],
        ),
    )
    create_res = await svc.create_analysis_task(USER_ID, req)
    task_id = create_res.get("task_id")
    if not task_id:
        print(f"[{idx}/{total}] ❌ {code} 创建失败")
        return None
    print(f"[{idx}/{total}] 📝 {code} → {task_id[:12]}...")

    try:
        await svc.execute_analysis_background(task_id, USER_ID, req)
    except Exception as e:
        print(f"[{idx}/{total}] ❌ {code}: {type(e).__name__}: {e}")
        return None

    from app.core.database import get_mongo_db
    db = get_mongo_db()
    doc = await db["analysis_reports"].find_one(
        {"stock_symbol": code, "status": "completed"}
    )
    if doc:
        print(f"[{idx}/{total}] ✅ {code} 完成 评级={doc.get('recommendation','N/A')}")
    else:
        print(f"[{idx}/{total}] ⚠️  {code} 未产出报告")
    return task_id


async def main():
    await init_db()
    svc = SimpleAnalysisService()
    total = len(STOCKS)
    print(f"P0-1a 批量 Tier1: {total} 只 A 股")
    for i, code in enumerate(STOCKS, 1):
        await run_one(svc, code, i, total)
        if i < total:
            await asyncio.sleep(DELAY)
    print("P0-1a 完成")


if __name__ == "__main__":
    asyncio.run(main())
