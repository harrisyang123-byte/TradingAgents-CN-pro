"""v4_unit_store.py — v4 分析单元信封读写 / 索引 / 运行锁

落盘是 git 传输载体（FR-009 AC9.3）：data/v4/**/*.json，diff 友好可 review。
本模块纯 stdlib，脚本（无 FastAPI）与后端路由均可复用。

核心职责：
  - unit_id ⇄ 落盘路径映射（§5.1）
  - 统一信封 schema 构造 / 读 / 覆盖式写（只动本单元，不触碰其它，NFR4.2 / AC9.4）
  - _units.json 索引维护（AC4.5）
  - _locks/<unit_id>.lock 运行锁：去重 / 排队 / 防并发重入（AC4.7）
"""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.v4 import SCHEMA_VERSION
from app.services.v4 import asset_classes as ac

# ── 落盘根目录（data/ 已整体 .gitignore，AC9.6） ────────────────────────
_ENV_ROOT = os.getenv("V4_DATA_ROOT", "").strip()


def data_root() -> Path:
    """v4 数据根目录。默认 <repo>/data/v4，可用 V4_DATA_ROOT 覆盖。"""
    if _ENV_ROOT:
        return Path(_ENV_ROOT)
    # app/services/v4/v4_unit_store.py → 上溯 3 层到 repo 根
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / "data" / "v4"


def _index_path() -> Path:
    return data_root() / "_units.json"


def _locks_dir() -> Path:
    return data_root() / "_locks"


# ── unit_id 解析与路径映射 ─────────────────────────────────────────────
def parse_unit_id(unit_id: str) -> Dict[str, str]:
    """解析 unit_id → {unit_type, key}。

    格式：
      asset:<class> / plan:<class> / industry:<name> / stock:<code>
      alloc:portfolio / alloc:equity_industries / alloc:industry:<name>
    """
    if ":" not in unit_id:
        raise ValueError(f"非法 unit_id（缺少类型前缀）: {unit_id}")
    prefix, rest = unit_id.split(":", 1)

    if prefix == "asset":
        return {"unit_type": "asset", "key": rest}
    if prefix == "plan":
        return {"unit_type": "plan", "key": rest}
    if prefix == "industry":
        return {"unit_type": "industry", "key": rest}
    if prefix == "stock":
        return {"unit_type": "stock", "key": rest}
    if prefix == "alloc":
        # alloc:portfolio / alloc:equity_industries / alloc:industry:<name>
        if rest.startswith("industry:"):
            return {"unit_type": "alloc_industry", "key": rest.split(":", 1)[1]}
        return {"unit_type": "alloc", "key": rest}
    raise ValueError(f"未知 unit_id 前缀: {unit_id}")


def _safe_name(name: str) -> str:
    """文件名安全化：替换路径分隔符与控制字符（保留中文）。"""
    s = re.sub(r"[/\\\x00-\x1f]", "_", name).strip()
    return s or "_"


def path_for(unit_id: str) -> Path:
    """unit_id → 落盘 JSON 路径（§5.1）。"""
    info = parse_unit_id(unit_id)
    ut, key = info["unit_type"], info["key"]
    root = data_root()
    if ut == "asset":
        return root / "assets" / f"{_safe_name(key)}.json"
    if ut == "plan":
        return root / "plans" / f"{_safe_name(key)}.json"
    if ut == "industry":
        return root / "industries" / f"{_safe_name(key)}.json"
    if ut == "stock":
        return root / "stocks" / f"{_safe_name(key)}.json"
    if ut == "alloc":
        return root / "allocation" / f"{_safe_name(key)}.json"
    if ut == "alloc_industry":
        return root / "allocation" / f"industry_{_safe_name(key)}.json"
    raise ValueError(f"无法映射路径: {unit_id}")


def unit_type_of(unit_id: str) -> str:
    """返回归一化单元类型（用于 TTL 分档：asset/plan/alloc/industry/stock）。"""
    info = parse_unit_id(unit_id)
    ut = info["unit_type"]
    if ut == "alloc_industry":
        return "alloc"
    return ut


# ── 时间工具 ───────────────────────────────────────────────────────────
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── 信封构造 / 读 / 写 ─────────────────────────────────────────────────
def new_envelope(
    unit_id: str,
    payload: Optional[Dict[str, Any]] = None,
    *,
    fingerprint: str = "",
    upstream: Optional[List[Dict[str, Any]]] = None,
    run_mode: str = "local",
    ttl_days: Optional[int] = None,
    status: str = "blue",
    error: Optional[str] = None,
    version: int = 1,
) -> Dict[str, Any]:
    """构造统一单元信封（§1.2）。version 由调用方/写入时递增。"""
    ut = unit_type_of(unit_id)
    return {
        "unit_id": unit_id,
        "unit_type": parse_unit_id(unit_id)["unit_type"],
        "schema_version": SCHEMA_VERSION,
        "version": version,
        "fingerprint": fingerprint,
        "upstream": upstream or [],
        "status": status,
        "ttl_days": ttl_days if ttl_days is not None else ac.ttl_for_unit_type(ut),
        "generated_at": utc_now_iso(),
        "run_mode": run_mode,
        "error": error,
        "payload": payload or {},
    }


def read_unit(unit_id: str) -> Optional[Dict[str, Any]]:
    """读取单元信封；不存在返回 None。"""
    p = path_for(unit_id)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def write_unit(envelope: Dict[str, Any], *, bump_version: bool = True) -> Dict[str, Any]:
    """覆盖式写入单个单元文件（只动本单元，不触碰其它，AC9.4 / NFR4.2）。

    bump_version=True 时：在已有版本基础上 +1（每次重跑 +1，下游据此判 stale）。
    写完同步更新 _units.json 索引。
    """
    unit_id = envelope["unit_id"]
    p = path_for(unit_id)
    p.parent.mkdir(parents=True, exist_ok=True)

    if bump_version:
        existing = read_unit(unit_id)
        base = existing["version"] if existing and isinstance(existing.get("version"), int) else 0
        envelope["version"] = base + 1

    envelope.setdefault("generated_at", utc_now_iso())
    # 原子写：先写临时文件再 rename
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)

    _update_index_entry(envelope)
    return envelope


# ── _units.json 索引（AC4.5） ──────────────────────────────────────────
def load_index() -> Dict[str, Any]:
    p = _index_path()
    if not p.exists():
        return {"schema_version": SCHEMA_VERSION, "units": {}, "updated_at": None}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"schema_version": SCHEMA_VERSION, "units": {}, "updated_at": None}


def _write_index(index: Dict[str, Any]) -> None:
    p = _index_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    index["updated_at"] = utc_now_iso()
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


def _index_summary(envelope: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "unit_id": envelope["unit_id"],
        "unit_type": envelope.get("unit_type"),
        "version": envelope.get("version"),
        "fingerprint": envelope.get("fingerprint"),
        "status": envelope.get("status"),
        "ttl_days": envelope.get("ttl_days"),
        "generated_at": envelope.get("generated_at"),
        "upstream": envelope.get("upstream", []),
        "error": envelope.get("error"),
        "path": str(path_for(envelope["unit_id"]).relative_to(data_root())),
    }


def _update_index_entry(envelope: Dict[str, Any]) -> None:
    index = load_index()
    index.setdefault("units", {})[envelope["unit_id"]] = _index_summary(envelope)
    _write_index(index)


def rebuild_index() -> Dict[str, Any]:
    """扫描 data/v4 下所有单元文件，重建 _units.json。"""
    root = data_root()
    index: Dict[str, Any] = {"schema_version": SCHEMA_VERSION, "units": {}}
    if root.exists():
        for sub in ("assets", "plans", "industries", "stocks", "allocation"):
            d = root / sub
            if not d.is_dir():
                continue
            for f in sorted(d.glob("*.json")):
                if f.name.endswith(".tmp"):
                    continue
                try:
                    env = json.loads(f.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue
                uid = env.get("unit_id")
                if uid:
                    index["units"][uid] = _index_summary(env)
    _write_index(index)
    return index


def list_units(prefix: Optional[str] = None) -> List[Dict[str, Any]]:
    """列出索引中的单元摘要，可按 unit_id 前缀过滤。"""
    units = load_index().get("units", {})
    out = [u for uid, u in units.items() if (prefix is None or uid.startswith(prefix))]
    return sorted(out, key=lambda u: u.get("unit_id", ""))


# ── 运行锁（AC4.7：去重 / 排队 / 防并发重入） ──────────────────────────
class LockError(RuntimeError):
    """获锁失败（该单元正在运行）。"""


def _lock_path(unit_id: str) -> Path:
    return _locks_dir() / f"{_safe_name(unit_id)}.lock"


def _is_pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


# 锁过期（秒）：持锁进程已死或超时则视为陈旧锁可抢占
LOCK_STALE_SECONDS = int(os.getenv("V4_LOCK_STALE_SECONDS", "3600"))


def acquire_lock(unit_id: str) -> Path:
    """获取单元运行锁。已被活跃进程持有 → 抛 LockError（AC4.7）。"""
    lp = _lock_path(unit_id)
    lp.parent.mkdir(parents=True, exist_ok=True)

    if lp.exists():
        try:
            info = json.loads(lp.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            info = {}
        pid = int(info.get("pid", -1))
        ts = float(info.get("ts", 0))
        stale = (time.time() - ts) > LOCK_STALE_SECONDS
        if not stale and _is_pid_alive(pid):
            raise LockError(
                f"单元 {unit_id} 正在运行（pid={pid}, since={info.get('since')}），"
                f"请等待完成或稍后重试"
            )
        # 陈旧锁：抢占
    payload = {
        "unit_id": unit_id,
        "pid": os.getpid(),
        "ts": time.time(),
        "since": utc_now_iso(),
    }
    lp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return lp


def release_lock(unit_id: str) -> None:
    lp = _lock_path(unit_id)
    try:
        if lp.exists():
            lp.unlink()
    except OSError:
        pass


def is_locked(unit_id: str) -> bool:
    """该单元当前是否被活跃进程持锁（blue 运行态）。"""
    lp = _lock_path(unit_id)
    if not lp.exists():
        return False
    try:
        info = json.loads(lp.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    pid = int(info.get("pid", -1))
    ts = float(info.get("ts", 0))
    if (time.time() - ts) > LOCK_STALE_SECONDS:
        return False
    return _is_pid_alive(pid)
