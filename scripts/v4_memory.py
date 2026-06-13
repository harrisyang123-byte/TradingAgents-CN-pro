"""v4 跨次 memory 长期记忆系统 (D0-5/2026-06-13)

借鉴 TradingAgents 设计: 每个 agent 独立 memory, 跨股/跨次累积经验避免重复犯错。

Memory schema (data/v4/_memory/<agent_id>.json):
{
  "agent_id": "v4-stock-director",
  "version": "v1",
  "updated_at": "ISO8601",
  "past_decisions": [
    {"date":"...", "stock":"...", "verdict":"...", "actual":"hit|miss|tracking", "lesson":"..."}
  ],
  "mistakes": [
    {"pattern":"...", "instances":["stock_code v1"], "rule":"避免方法"}
  ],
  "patterns": [
    {"pattern":"行为模式总结", "calibration":"应用方法"}
  ]
}

agent 开辩前 read(agent_id) 看历史 → 完成判断后 append_decision/append_mistake/append_pattern.
"""

from __future__ import annotations
import json
import os
import datetime
from pathlib import Path
from typing import Any, Optional

# 默认 memory 目录(可被环境变量覆盖)
MEMORY_DIR = Path(os.environ.get("V4_MEMORY_DIR", "data/v4/_memory"))


def _ensure_dir() -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def _today() -> str:
    return datetime.date.today().isoformat()


def read(agent_id: str) -> dict[str, Any]:
    """读取 agent 的 memory; 不存在返回空骨架"""
    _ensure_dir()
    p = MEMORY_DIR / f"{agent_id}.json"
    if not p.exists():
        return {
            "agent_id": agent_id,
            "version": "v1",
            "updated_at": "",
            "past_decisions": [],
            "mistakes": [],
            "patterns": [],
        }
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        # 损坏时返回空骨架, 不抛
        return {
            "agent_id": agent_id,
            "version": "v1",
            "updated_at": "",
            "past_decisions": [],
            "mistakes": [],
            "patterns": [],
        }


def write(agent_id: str, data: dict[str, Any]) -> None:
    """覆盖写入"""
    _ensure_dir()
    p = MEMORY_DIR / f"{agent_id}.json"
    data.setdefault("agent_id", agent_id)
    data.setdefault("version", "v1")
    data["updated_at"] = _today()
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def append_decision(
    agent_id: str,
    stock: str,
    verdict: str,
    actual: str = "tracking",
    lesson: str = "",
    extra: Optional[dict[str, Any]] = None,
) -> None:
    """记录一次判断"""
    m = read(agent_id)
    rec: dict[str, Any] = {
        "date": _today(),
        "stock": stock,
        "verdict": verdict,
        "actual": actual,
        "lesson": lesson,
    }
    if extra:
        rec.update(extra)
    m.setdefault("past_decisions", []).append(rec)
    write(agent_id, m)


def append_mistake(
    agent_id: str,
    pattern: str,
    instances: Optional[list[str]] = None,
    rule: str = "",
) -> None:
    """记录一次错误模式"""
    m = read(agent_id)
    m.setdefault("mistakes", []).append({
        "pattern": pattern,
        "instances": instances or [],
        "rule": rule,
        "discovered_at": _today(),
    })
    write(agent_id, m)


def append_pattern(agent_id: str, pattern: str, calibration: str = "") -> None:
    """记录一次行为模式总结"""
    m = read(agent_id)
    m.setdefault("patterns", []).append({
        "pattern": pattern,
        "calibration": calibration,
        "discovered_at": _today(),
    })
    write(agent_id, m)


def summary_for_prompt(agent_id: str, max_records: int = 10) -> str:
    """生成可塞入 prompt 的紧凑摘要(供 agent 开辩前读)"""
    m = read(agent_id)
    out_lines = [f"# {agent_id} 历史经验摘要 (updated: {m.get('updated_at','-')})"]

    decisions = (m.get("past_decisions") or [])[-max_records:]
    if decisions:
        out_lines.append(f"\n## 最近 {len(decisions)} 次判断")
        for d in decisions:
            out_lines.append(
                f"- [{d.get('date')}] {d.get('stock')} → {d.get('verdict')} "
                f"(实际: {d.get('actual','tracking')}) {d.get('lesson','')}"
            )

    mistakes = m.get("mistakes") or []
    if mistakes:
        out_lines.append(f"\n## 已识别错误模式 ({len(mistakes)} 条)")
        for ms in mistakes[-5:]:
            out_lines.append(f"- {ms.get('pattern')} → 规则: {ms.get('rule')}")

    patterns = m.get("patterns") or []
    if patterns:
        out_lines.append(f"\n## 行为模式校准 ({len(patterns)} 条)")
        for p in patterns[-5:]:
            out_lines.append(f"- {p.get('pattern')} → 校准: {p.get('calibration')}")

    return "\n".join(out_lines)


def list_agents() -> list[str]:
    """列出所有有 memory 的 agent"""
    _ensure_dir()
    return [p.stem for p in MEMORY_DIR.glob("*.json")]


# CLI: python scripts/v4_memory.py <agent_id> 看 summary
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print(summary_for_prompt(sys.argv[1]))
    else:
        print("Usage: python scripts/v4_memory.py <agent_id>")
        print(f"\nExisting agents: {list_agents()}")
