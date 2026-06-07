"""v4_state.py — v4 新鲜度状态机（纯只读，FR-004 / FR-005）

五色状态语言（NFR3.1）：
  gray   从未运行（无产物）
  blue   正在运行（持锁，尚无成功产物）
  green  新鲜有效
  yellow TTL 过期 或 上游版本递增（软提醒，旧结论仍可读，AC5.3）
  red    运行失败（error 非空）

铁律：本模块只计算颜色、只报警，**绝不触发重跑、绝不修正约束数值**（AC5.3 / AC5.5）。
指纹算法复用 scripts/stage_cache.py::_fingerprint（同一 sha256 口径，FR-005 / §4.3）。
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.services.v4 import v4_unit_store as store

# 状态常量
GRAY = "gray"
BLUE = "blue"
GREEN = "green"
YELLOW = "yellow"
RED = "red"


# ── 指纹算法（复用 stage_cache 口径） ──────────────────────────────────
def _fingerprint_local(inputs: List[str]) -> str:
    """与 scripts/stage_cache.py::_fingerprint 完全一致的 sha256 口径。"""
    h = hashlib.sha256()
    for path in inputs:
        p = Path(path)
        h.update(path.encode("utf-8"))
        h.update(b"\x00")
        if p.exists() and p.is_file():
            try:
                h.update(p.read_bytes())
            except OSError:
                h.update(b"<unreadable>")
        else:
            h.update(b"<missing>")
        h.update(b"\x01")
    return h.hexdigest()


def fingerprint(inputs: List[str]) -> str:
    """对输入文件集计算指纹。优先复用 stage_cache._fingerprint。"""
    try:
        import sys
        repo_root = Path(__file__).resolve().parents[3]
        scripts_dir = str(repo_root / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from stage_cache import _fingerprint as _sc_fp  # type: ignore
        return "sha256:" + _sc_fp(inputs)
    except ImportError:
        # 仅在 stage_cache 模块不可用时回退到本地等价实现；
        # 其它真实错误（如 OSError）不再被掩盖，交由调用方暴露。
        return "sha256:" + _fingerprint_local(inputs)


def content_fingerprint(content: str) -> str:
    """对任意字符串内容计算指纹（无文件时备用）。"""
    return "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()


# ── 时间工具 ───────────────────────────────────────────────────────────
def _parse_iso(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        s = ts.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def _age_days(generated_at: Optional[str], now: Optional[datetime] = None) -> Optional[float]:
    dt = _parse_iso(generated_at)
    if dt is None:
        return None
    now = now or datetime.now(timezone.utc)
    return (now - dt).total_seconds() / 86400.0


# ── 上游版本解析 ───────────────────────────────────────────────────────
def _current_upstream(
    upstream_resolver: Optional[Callable[[str], Optional[Dict[str, Any]]]],
    unit_id: str,
) -> Optional[Dict[str, Any]]:
    """获取上游单元当前信息 {version, fingerprint}。

    默认从落盘读取；传 resolver 可改读 Mongo/索引。
    """
    if upstream_resolver is not None:
        return upstream_resolver(unit_id)
    env = store.read_unit(unit_id)
    if env is None:
        # 退回索引
        idx = store.load_index().get("units", {}).get(unit_id)
        return idx
    return env


# ── 核心：状态计算（纯函数） ───────────────────────────────────────────
def compute_status(
    envelope: Optional[Dict[str, Any]],
    *,
    unit_id: Optional[str] = None,
    is_locked: Optional[bool] = None,
    upstream_resolver: Optional[Callable[[str], Optional[Dict[str, Any]]]] = None,
    now: Optional[datetime] = None,
) -> Tuple[str, Optional[str]]:
    """计算单元状态色 + stale 原因（§4.3 五步判定）。

    返回 (status, stale_reason)。stale_reason 仅在 yellow 时非空（可读文案）。
    """
    uid = unit_id or (envelope.get("unit_id") if envelope else None)

    # 锁状态优先用传入值，否则查锁文件
    locked = is_locked
    if locked is None and uid:
        try:
            locked = store.is_locked(uid)
        except Exception:
            locked = False

    # 步骤 1：无产物
    if envelope is None:
        if locked:
            return BLUE, None
        return GRAY, None

    # error 非空 → red
    if envelope.get("error"):
        return RED, None

    # 有锁但无成功产物（version 缺失/为 0）→ blue
    if locked and not envelope.get("generated_at"):
        return BLUE, None

    reasons: List[str] = []

    # 步骤 2：TTL 过期
    ttl = float(envelope.get("ttl_days", 0) or 0)
    age = _age_days(envelope.get("generated_at"), now)
    if ttl > 0 and age is not None and age >= ttl:
        reasons.append(f"已生成 {age:.0f} 天，超过 TTL {ttl:.0f} 天，建议刷新")

    # 步骤 3：上游版本递增 / 指纹不匹配
    for up in envelope.get("upstream", []) or []:
        up_id = up.get("unit_id")
        if not up_id:
            continue
        cur = _current_upstream(upstream_resolver, up_id)
        if cur is None:
            continue
        ref_ver = up.get("version")
        cur_ver = cur.get("version")
        if isinstance(ref_ver, int) and isinstance(cur_ver, int) and cur_ver > ref_ver:
            reasons.append(
                f"上游 {up_id} 已更新至 v{cur_ver}（本单元基于 v{ref_ver}），结论可能过时"
            )
            continue
        ref_fp = up.get("fingerprint")
        cur_fp = cur.get("fingerprint")
        if ref_fp and cur_fp and ref_fp != cur_fp:
            reasons.append(f"上游 {up_id} 输入已变化，结论可能过时")

    if reasons:
        return YELLOW, "；".join(reasons)

    # 步骤 4：新鲜
    return GREEN, None


# ── 约束链校验（仅报警，不修正，AC5.5 / NFR2.2） ───────────────────────
def check_constraint_chain(
    envelope: Dict[str, Any],
    *,
    upstream_resolver: Optional[Callable[[str], Optional[Dict[str, Any]]]] = None,
) -> List[Dict[str, str]]:
    """校验下游引用的上游约束是否来自过时版本。仅返回 warnings，不改任何数值。"""
    warnings: List[Dict[str, str]] = []
    for up in envelope.get("upstream", []) or []:
        up_id = up.get("unit_id")
        if not up_id:
            continue
        cur = _current_upstream(upstream_resolver, up_id)
        if cur is None:
            warnings.append({"upstream": up_id, "issue": "missing", "detail": "上游单元缺失"})
            continue
        ref_ver = up.get("version")
        cur_ver = cur.get("version")
        if isinstance(ref_ver, int) and isinstance(cur_ver, int) and ref_ver < cur_ver:
            warnings.append({
                "upstream": up_id,
                "issue": "stale",
                "detail": f"约束基于 {up_id} v{ref_ver}，当前已 v{cur_ver}（仅提醒，未自动修正）",
            })
    return warnings


def cli_hint(unit_id: str) -> str:
    """为单元生成「该如何在 CLI 触发」提示（AC4.6 / AC8.4）。"""
    return f'在 CLI 对话说「分析 {unit_id}」，或运行：./scripts/run_v4.sh analyze {unit_id}'


def status_label(status: str) -> str:
    return {
        GRAY: "未运行",
        BLUE: "运行中",
        GREEN: "新鲜",
        YELLOW: "待刷新",
        RED: "失败",
    }.get(status, status)
