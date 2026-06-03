#!/usr/bin/env python3
"""save_to_mongodb.py — 最终处方保存到 MongoDB

用法:
    python scripts/save_to_mongodb.py --dir <data_dir>

读 step9_final.json(CIO终裁) + conflicts.json → 组装 PortfolioAdvice → 写 MongoDB。
重试最多 3 次(间隔 2s)，失败保留所有输出文件。
"""

import argparse
import json
import os
import sys
import asyncio
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


async def save_to_mongodb(data_dir: str) -> bool:
    """读 CIO 终裁 + 冲突报告 → 写 MongoDB portfolio_advice"""
    step9_path = Path(data_dir) / "step9_final.json"
    conflicts_path = Path(data_dir) / "conflicts.json"

    if not step9_path.exists():
        print(f"错误: CIO 终裁文件不存在: {step9_path}")
        return False

    try:
        with open(step9_path, "r") as f:
            final = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"错误: 无法读取 {step9_path}: {e}")
        return False

    conflicts = []
    if conflicts_path.exists():
        try:
            with open(conflicts_path, "r") as f:
                conflicts = json.load(f).get("conflicts", [])
        except (json.JSONDecodeError, IOError):
            pass

    # 组装 PortfolioAdvice 文档
    run_id = Path(data_dir).name
    prescription = final.get("prescription", [])
    cio_verdict = final.get("cio_verdict", "")

    doc = {
        "run_id": run_id,
        "source": "claude-code-workflow-v1",
        "user_id": final.get("user_id", ""),
        "cio_verdict": cio_verdict,
        "prescription": prescription,
        "conflicts": conflicts,
        "conflict_count": len(conflicts),
        "created_at": datetime.utcnow(),
        "data_dir": str(data_dir),
    }

    # 重试 3 次写 MongoDB
    from app.core.database import init_database, get_mongo_db
    await init_database()
    db = get_mongo_db()

    for attempt in range(3):
        try:
            # 用 run_id + source 做 upsert key
            await db["portfolio_advice"].update_one(
                {"run_id": run_id, "source": "claude-code-workflow-v1"},
                {"$set": doc},
                upsert=True,
            )
            print(f"✅ 处方已保存到 MongoDB (run_id={run_id}, {len(prescription)} items)")
            return True
        except Exception as e:
            if attempt < 2:
                print(f"[WARNING] MongoDB 写入失败 (attempt {attempt+1}/3): {e}")
                time.sleep(2)
            else:
                print(f"❌ MongoDB 写入全部失败 (3 attempts): {e}")
                print(f"   输出文件保留在 {data_dir}")
                print(f"   可手动重新执行: python scripts/save_to_mongodb.py --dir {data_dir}")
                return False

    return False


def main():
    parser = argparse.ArgumentParser(description="Save final prescription to MongoDB")
    parser.add_argument("--dir", required=True, help="Data directory (data/advisor_runs/{ts}/)")
    args = parser.parse_args()

    success = asyncio.run(save_to_mongodb(args.dir))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
