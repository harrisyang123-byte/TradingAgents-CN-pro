"""P0-1a: Parallel Tier 1 analysis for remaining A-share holdings."""
import asyncio
import os
import sys

os.chdir("/Users/yangyanyu/AI-Coding-Engine/domains/tradingagents-cn")
sys.path.insert(0, ".")

from app.services.simple_analysis_service import SimpleAnalysisService
from app.models.analysis import SingleAnalysisRequest, AnalysisParameters

STOCKS = ["603236", "000063", "002415", "002001", "002050"]
USER_ID = "6a094caea814b57d3357fa0b"
MAX_RETRIES = 2
RETRY_BACKOFF = [15, 30]


async def init_db():
    from app.core.database import init_database
    await init_database()
    from app.core.config import settings
    print(f"DB: {settings.MONGO_DB}")


async def run_one(svc, code):
    req = SingleAnalysisRequest(
        symbol=code,
        parameters=AnalysisParameters(
            research_depth="标准",
            market_type="A股",
            instrument_type="stock",
            selected_analysts=["market", "fundamentals"],
        ),
    )

    for attempt in range(1 + MAX_RETRIES):
        create_res = await svc.create_analysis_task(USER_ID, req)
        task_id = create_res.get("task_id")
        if not task_id:
            print(f"❌ {code} 创建失败 (attempt {attempt+1})")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_BACKOFF[attempt])
            continue

        if attempt == 0:
            print(f"▶ {code} → {task_id[:12]}")
        else:
            print(f"🔄 {code} retry {attempt} → {task_id[:12]}")

        try:
            await svc.execute_analysis_background(task_id, USER_ID, req)
        except Exception as e:
            err_msg = str(e)
            if "Rate limited" in err_msg or "Too Many Requests" in err_msg:
                print(f"⏳ {code}: rate limited (attempt {attempt+1})")
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_BACKOFF[attempt])
                continue
            else:
                print(f"❌ {code}: {type(e).__name__}: {e}")
                return code, None

        from app.core.database import get_mongo_db
        db = get_mongo_db()
        doc = await db["analysis_reports"].find_one(
            {"stock_symbol": code, "status": "completed"}
        )
        if doc:
            rec = doc.get("recommendation", "N/A")
            action = doc.get("decision", {}).get("action", "?")
            print(f"✅ {code} {action} | {rec[:100] if rec else 'N/A'}")
            return code, task_id
        else:
            print(f"⚠️  {code} 无报告 (attempt {attempt+1})")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_BACKOFF[attempt])
            continue

    print(f"❌ {code} 最终失败")
    return code, None


async def main():
    await init_db()
    svc = SimpleAnalysisService()
    print(f"P0-1a 并行: {len(STOCKS)} 只同时启动\n")

    tasks = [run_one(svc, code) for code in STOCKS]
    results = await asyncio.gather(*tasks)

    success = sum(1 for _, tid in results if tid)
    failed = sum(1 for _, tid in results if not tid)
    print(f"\n完成: {success}/{len(STOCKS)} 成功, {failed}/{len(STOCKS)} 失败")


if __name__ == "__main__":
    asyncio.run(main())
