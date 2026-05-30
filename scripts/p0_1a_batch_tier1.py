"""P0-1a: Batch run Tier 1 analysis for 7 A-share holdings (with retry)."""
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
DELAY = 30  # seconds between stocks
MAX_RETRIES = 3
RETRY_BACKOFF = [15, 30, 60]  # seconds to wait before each retry


async def init_db():
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

    for attempt in range(1 + MAX_RETRIES):
        create_res = await svc.create_analysis_task(USER_ID, req)
        task_id = create_res.get("task_id")
        if not task_id:
            print(f"[{idx}/{total}] ❌ {code} 创建失败 (attempt {attempt+1})")
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF[attempt]
                print(f"  重试等待 {wait}s...")
                await asyncio.sleep(wait)
            continue

        if attempt == 0:
            print(f"[{idx}/{total}] 📝 {code} → {task_id[:12]}...")
        else:
            print(f"[{idx}/{total}] 🔄 {code} retry {attempt} → {task_id[:12]}...")

        try:
            await svc.execute_analysis_background(task_id, USER_ID, req)
        except Exception as e:
            err_msg = str(e)
            if "Rate limited" in err_msg or "Too Many Requests" in err_msg:
                print(f"[{idx}/{total}] ⏳ {code}: rate limited (attempt {attempt+1})")
                if attempt < MAX_RETRIES:
                    wait = RETRY_BACKOFF[attempt]
                    print(f"  重试等待 {wait}s...")
                    await asyncio.sleep(wait)
                continue
            else:
                print(f"[{idx}/{total}] ❌ {code}: {type(e).__name__}: {e}")
                return None

        from app.core.database import get_mongo_db
        db = get_mongo_db()
        doc = await db["analysis_reports"].find_one(
            {"stock_symbol": code, "status": "completed"}
        )
        if doc:
            rec = doc.get("recommendation", "N/A")
            print(f"[{idx}/{total}] ✅ {code} 完成 评级={rec[:80] if rec else 'N/A'}")
            return task_id
        else:
            print(f"[{idx}/{total}] ⚠️  {code} 未产出报告 (attempt {attempt+1})")
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF[attempt]
                print(f"  重试等待 {wait}s...")
                await asyncio.sleep(wait)
            continue

    print(f"[{idx}/{total}] ❌ {code} 最终失败（{MAX_RETRIES+1}次尝试）")
    return None


async def main():
    await init_db()
    svc = SimpleAnalysisService()
    total = len(STOCKS)
    results = {"success": 0, "failed": 0}
    print(f"P0-1a 批量 Tier1: {total} 只 A 股 (delay={DELAY}s, retries={MAX_RETRIES})")
    for i, code in enumerate(STOCKS, 1):
        task_id = await run_one(svc, code, i, total)
        if task_id:
            results["success"] += 1
        else:
            results["failed"] += 1
        if i < total:
            print(f"  ⏳ 等待 {DELAY}s 再处理下一只...")
            await asyncio.sleep(DELAY)
    print(f"P0-1a 完成: {results['success']}/{total} 成功, {results['failed']}/{total} 失败")


if __name__ == "__main__":
    asyncio.run(main())
