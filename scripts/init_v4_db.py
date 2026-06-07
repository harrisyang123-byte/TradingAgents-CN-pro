#!/usr/bin/env python3
"""init_v4_db.py — v4 MongoDB 集合与索引初始化（design §5.6）

集合：
  v4_units    单元信封 upsert 落地，(user_id, unit_id) 唯一索引（AC9.5）
  v4_run_log  单元运行记录（run_id；触发时间/模式/结果/耗时，NFR3）

幂等：重复运行不报错（索引已存在则跳过）。
"""

import os
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from pymongo import ASCENDING, MongoClient


def build_mongo_uri() -> str:
    # 优先用应用统一配置；失败回退环境变量（脚本可脱离 FastAPI 运行）
    try:
        from app.core.config import settings
        if getattr(settings, "MONGO_URI", None):
            return settings.MONGO_URI
    except Exception:
        pass
    host = os.getenv("MONGODB_HOST", "localhost")
    port = int(os.getenv("MONGODB_PORT", "27017"))
    db = os.getenv("MONGODB_DATABASE", "tradingagents")
    user = os.getenv("MONGODB_USERNAME", "")
    pwd = os.getenv("MONGODB_PASSWORD", "")
    if user and pwd:
        return f"mongodb://{user}:{pwd}@{host}:{port}/{db}?authSource=admin"
    return f"mongodb://{host}:{port}/{db}"


def db_name() -> str:
    try:
        from app.core.config import settings
        if getattr(settings, "MONGO_DB", None):
            return settings.MONGO_DB
    except Exception:
        pass
    return os.getenv("MONGODB_DATABASE", "tradingagents")


def main() -> int:
    uri = build_mongo_uri()
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    db = client[db_name()]

    # v4_units：(user_id, unit_id) 唯一
    db["v4_units"].create_index(
        [("user_id", ASCENDING), ("unit_id", ASCENDING)],
        unique=True,
        name="uniq_user_unit",
    )
    db["v4_units"].create_index([("user_id", ASCENDING), ("unit_type", ASCENDING)], name="user_type")
    db["v4_units"].create_index([("status", ASCENDING)], name="status_idx")

    # v4_run_log
    db["v4_run_log"].create_index([("run_id", ASCENDING)], unique=True, name="uniq_run")
    db["v4_run_log"].create_index(
        [("user_id", ASCENDING), ("unit_id", ASCENDING), ("started_at", ASCENDING)],
        name="user_unit_time",
    )

    print("✅ v4 集合与索引就绪：v4_units / v4_run_log")
    print(f"   DB = {db_name()}")
    client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
