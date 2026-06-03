#!/usr/bin/env python3
"""save_step.py — 单步 Agent 输出渐进式保存到 MongoDB

用法:
    python scripts/save_step.py --dir <data_dir> --step <step_name>

每步 Agent 完成后立即调用，将输出写入 MongoDB agent_steps collection。
失败不阻塞流程——只输出 warning 到 stderr。
"""

import argparse
import json
import os
import sys
import asyncio
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


async def save_step(data_dir: str, step_name: str) -> bool:
    """读 step JSON 文件 → 写 MongoDB agent_steps collection"""
    step_file = Path(data_dir) / f"{step_name.replace('-r2', '_r2')}.json"

    # 尝试几种文件名格式
    if not step_file.exists():
        # 尝试 step{N}_{name}.json 格式
        step_map = {
            "l1-strategist": "step1_strategist.json",
            "l1-contrarian": "step2_contrarian.json",
            "l1-strategist-r2": "step1_strategist_r2.json",
            "l1-judge": "step3_judge.json",
            "l2-scout": "step4_scout.json",
            "l3-analyst": "step5_analyst.json",
            "l3-strategist": "step6_strategist.json",
            "l3-analyst-r2": "step5_analyst_r2.json",
            "l3-strategist-r2": "step6_strategist_r2.json",
            "l4-cio": "step7_cio.json",
            "l4-risk": "step8_risk.json",
            "l4-cio-final": "step9_final.json",
        }
        mapped = step_map.get(step_name, "")
        if mapped:
            step_file = Path(data_dir) / mapped

    if not step_file.exists():
        print(f"[WARNING] Agent step file not found: {step_file}", file=sys.stderr)
        return False

    try:
        with open(step_file, "r") as f:
            output_data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"[WARNING] Failed to read {step_file}: {e}", file=sys.stderr)
        return False

    try:
        from app.core.database import init_database, get_mongo_db
        await init_database()
        db = get_mongo_db()

        doc = {
            "run_id": Path(data_dir).name,
            "step_name": step_name,
            "data_dir": str(data_dir),
            "output": output_data,
            "created_at": datetime.utcnow(),
        }
        await db["agent_steps"].update_one(
            {"run_id": doc["run_id"], "step_name": step_name},
            {"$set": doc},
            upsert=True,
        )
        return True
    except Exception as e:
        print(f"[WARNING] MongoDB save failed for {step_name}: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Save single agent step to MongoDB")
    parser.add_argument("--dir", required=True, help="Data directory (data/advisor_runs/{ts}/)")
    parser.add_argument("--step", required=True, help="Agent step name (e.g., l1-strategist)")
    args = parser.parse_args()

    success = asyncio.run(save_step(args.dir, args.step))
    sys.exit(0 if success else 0)  # 总是 exit 0，失败不阻塞流程


if __name__ == "__main__":
    main()
