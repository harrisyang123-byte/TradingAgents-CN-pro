"""Task 0 验证：v4 状态机五态 + 单元存储隔离 + 运行锁。

运行：python3 scripts/test/test_v4_unit_store.py
（独立可跑，自动用临时目录，不污染 data/v4）
"""
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))
os.environ["V4_DATA_ROOT"] = tempfile.mkdtemp(prefix="v4test_")

from app.services.v4 import v4_state as st  # noqa: E402
from app.services.v4 import v4_unit_store as store  # noqa: E402

_ok = True


def check(name, cond):
    global _ok
    print(("PASS" if cond else "FAIL"), name)
    _ok = _ok and bool(cond)


def run():
    # 1. gray
    status, _ = st.compute_status(None, unit_id="asset:equity")
    check("gray=未运行", status == st.GRAY)

    # 2. 写读 + version bump + 单元隔离
    store.write_unit(store.new_envelope("asset:equity", {"verdict": {"stance": "bullish"}},
                                        fingerprint="sha256:aaa", status="green"))
    e2 = store.read_unit("asset:equity")
    check("写读往返", e2 and e2["payload"]["verdict"]["stance"] == "bullish")
    check("version=1", e2["version"] == 1)
    store.write_unit(store.new_envelope("asset:equity", {"x": 1}, status="green"))
    check("version bump=2", store.read_unit("asset:equity")["version"] == 2)
    store.write_unit(store.new_envelope("asset:cash", {"y": 1}, status="green"))
    check("写 cash 不动 equity", store.read_unit("asset:equity")["version"] == 2)

    # 3. green
    status, _ = st.compute_status(store.read_unit("asset:equity"), unit_id="asset:equity")
    check("green=新鲜", status == st.GREEN)

    # 4. yellow TTL
    old = store.new_envelope("industry:test", {"v": 1}, status="green", ttl_days=7)
    old["generated_at"] = (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
    status, reason = st.compute_status(old, unit_id="industry:test")
    check("yellow=TTL过期", status == st.YELLOW and bool(reason))

    # 5. yellow 上游递增 + 约束链仅报警
    alloc = store.new_envelope("alloc:portfolio", {"equity_quota": 55},
                               upstream=[{"unit_id": "asset:equity", "version": 1, "fingerprint": "x"}],
                               status="green")
    status, reason = st.compute_status(alloc, unit_id="alloc:portfolio")
    check("yellow=上游递增", status == st.YELLOW and "asset:equity" in (reason or ""))
    warns = st.check_constraint_chain(alloc)
    check("约束链报警不修正", any(w["issue"] == "stale" for w in warns)
          and alloc["payload"]["equity_quota"] == 55)

    # 6. red
    status, _ = st.compute_status(store.new_envelope("stock:000001", {}, status="red", error="boom"),
                                  unit_id="stock:000001")
    check("red=失败", status == st.RED)

    # 7. 锁
    lp = store.acquire_lock("asset:equity")
    check("获锁成功", lp.exists() and store.is_locked("asset:equity"))
    try:
        store.acquire_lock("asset:equity")
        check("重复获锁应失败", False)
    except store.LockError:
        check("重复获锁抛 LockError", True)
    store.release_lock("asset:equity")
    check("释放后未锁", not store.is_locked("asset:equity"))

    store.acquire_lock("plan:cash")
    status, _ = st.compute_status(None, unit_id="plan:cash")
    check("blue=运行中", status == st.BLUE)
    store.release_lock("plan:cash")

    # 8. 路径映射
    check("alloc:industry 路径", store.path_for("alloc:industry:AI算力").name == "industry_AI算力.json")
    check("stock 路径", store.path_for("stock:000001").name == "000001.json")
    check("索引列出单元", len(store.list_units()) >= 2)

    print("\nRESULT:", "ALL PASS" if _ok else "HAS FAILURES")
    return 0 if _ok else 1


if __name__ == "__main__":
    sys.exit(run())
