#!/usr/bin/env python3
"""import_v4.py — v4 单元产物幂等导入 MongoDB（FR-009 AC9.5）

git pull 拿到 data/v4/**/*.json 后，按 (user_id, unit_id) 幂等 upsert 入 v4_units 集合。
重复导入不产生重复或脏数据（$set 整个信封）。前端读 Mongo 即与本地运行一致。

用法:
  python scripts/import_v4.py --user-id <id>                 # 导入 data/v4 下全部单元
  python scripts/import_v4.py --user-id <id> --unit asset:equity   # 仅导入指定单元
  python scripts/import_v4.py --user-id <id> --dry-run        # 只列出将导入什么，不写库
"""

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from app.services.v4 import v4_unit_store as store  # noqa: E402


def _collect_envelopes(unit_filter: str) -> list:
    """重建索引并读取所有（或指定）单元信封。"""
    store.rebuild_index()
    envs = []
    for u in store.list_units():
        uid = u["unit_id"]
        if unit_filter and uid != unit_filter:
            continue
        env = store.read_unit(uid)
        if env and env.get("unit_id"):
            envs.append(env)
    return envs


def main() -> int:
    ap = argparse.ArgumentParser(description="v4 单元产物幂等导入 MongoDB")
    ap.add_argument("--user-id", required=True, help="导入归属用户 ID")
    ap.add_argument("--unit", default="", help="仅导入指定 unit_id（默认全部）")
    ap.add_argument("--dry-run", action="store_true", help="只列出，不写库")
    args = ap.parse_args()

    envs = _collect_envelopes(args.unit)
    if not envs:
        print("（无可导入的 v4 单元；先在本地 analyze 或确认 data/v4 存在产物）")
        return 0

    print(f"待导入 {len(envs)} 个单元（user_id={args.user_id}）：")
    for e in envs:
        print(f"  · {e['unit_id']:<32} v{e.get('version')} status={e.get('status')}")

    if args.dry_run:
        print("（dry-run：未写库）")
        return 0

    # 连库 upsert
    try:
        from app.core.database import get_mongo_db_sync
        db = get_mongo_db_sync()
    except Exception as e:
        print(f"❌ Mongo 不可用，无法导入: {e}", file=sys.stderr)
        return 1

    # 确保唯一索引（幂等）
    try:
        db["v4_units"].create_index([("user_id", 1), ("unit_id", 1)], unique=True)
    except Exception:
        pass

    imported = 0
    skipped = 0
    for env in envs:
        uid = env["unit_id"]
        # 校验 unit_id 格式合法，拒绝非法单元入库（防脏数据，与 /import 路由口径一致）
        try:
            store.parse_unit_id(uid)
        except ValueError as e:
            print(f"⚠️  跳过非法 unit_id={uid!r}: {e}", file=sys.stderr)
            skipped += 1
            continue
        doc = dict(env)
        doc["user_id"] = args.user_id
        db["v4_units"].update_one(
            {"user_id": args.user_id, "unit_id": uid},
            {"$set": doc},
            upsert=True,
        )
        imported += 1

    msg = f"✅ 幂等导入完成：{imported} 个单元 upsert 入 v4_units（重复导入不产脏数据）"
    if skipped:
        msg += f"；跳过 {skipped} 个非法单元"
    print(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
