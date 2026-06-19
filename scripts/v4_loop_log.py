#!/usr/bin/env python3
"""v4_loop_log.py — loop done 账本的 append-only 持久化 + 对账恢复。

背景（2026-06-19 真实事故）：`optimization_state.json` 的 done/backlog 是同一大 JSON 里的数组，
任何写入都是「读旧的 → 内存改 → 整体覆写」。两个 actor（本地跑 / 会话 agent）交替操作时，
后写的整体覆盖先写的 → done 历史条目丢失（已亲历 iter7-11 条目丢失）。

根治：done 的**真账本**外移成 append-only 的 `done_log.jsonl`，每条洞追加一行、**永不覆写**。
主状态文件 optimization_state.json 仍存「当前态」(active_hole/backlog/meta)，但 done 历史以 jsonl 为准。

子命令：
  append   <entry.json>   把一条 done 洞追加到 done_log.jsonl（'a' 模式，不覆写已有行）
  reconcile               以 done_log.jsonl 为准，重建 optimization_state.json 的 done 数组
                          （去重按 id，保留最新；用于被覆写后恢复历史）
  list                    打印 done_log.jsonl 里所有洞的 id + completed_at（核对用）
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

LOOP_DIR = Path("data/v4/_loop")
STATE_FILE = LOOP_DIR / "optimization_state.json"
DONE_LOG = LOOP_DIR / "done_log.jsonl"


def _read_log() -> list[dict]:
    if not DONE_LOG.exists():
        return []
    out = []
    for ln in DONE_LOG.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            out.append(json.loads(ln))
        except ValueError:
            pass  # 跳过坏行，不中断
    return out


def cmd_append(entry_path: str) -> int:
    """追加一条 done 洞到 jsonl（永不覆写已有行）。"""
    entry = json.loads(Path(entry_path).read_text(encoding="utf-8"))
    if not entry.get("id"):
        print("entry 缺 id 字段", file=sys.stderr)
        return 1
    LOOP_DIR.mkdir(parents=True, exist_ok=True)
    with DONE_LOG.open("a", encoding="utf-8") as f:  # 'a' 模式：原子追加，不读不覆写
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"appended {entry['id']} → {DONE_LOG}")
    return 0


def cmd_reconcile() -> int:
    """以 done_log.jsonl 为准重建 state.done（被覆写后恢复历史）。按 id 去重保留最后出现。"""
    if not STATE_FILE.exists():
        print("state 文件不存在", file=sys.stderr)
        return 1
    state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    log_entries = _read_log()
    # 合并：state.done 现有 + jsonl 全部，按 id 去重(后出现覆盖)
    merged: dict[str, dict] = {}
    for e in state.get("done", []):
        if e.get("id"):
            merged[e["id"]] = e
    recovered = 0
    for e in log_entries:
        eid = e.get("id")
        if eid and eid not in merged:
            recovered += 1
        if eid:
            merged[eid] = e
    state["done"] = list(merged.values())
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"reconcile 完成: state.done 现 {len(state['done'])} 条（从 jsonl 找回 {recovered} 条）")
    return 0


def cmd_list() -> int:
    for e in _read_log():
        print(f"  {e.get('id', '?')}  {e.get('completed_at', '?')}  {e.get('title', '')[:50]}")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd = sys.argv[1]
    if cmd == "append":
        if len(sys.argv) < 3:
            print("用法: append <entry.json>", file=sys.stderr)
            return 1
        return cmd_append(sys.argv[2])
    if cmd == "reconcile":
        return cmd_reconcile()
    if cmd == "list":
        return cmd_list()
    print(f"未知子命令: {cmd}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
