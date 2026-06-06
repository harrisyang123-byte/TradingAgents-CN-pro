"""v3_advisor_runner — subprocess 驱动 run.sh 的两阶段 runner

提供:
    run_plan(user_id, goal) -> task_id, run_dir
        收集数据 → 跑 v3 到 industry → 返回推荐行业

    run_execute(task_id, run_dir, user_id, selected_industries) -> None
        写 selected_industries.json → 跑 scout→synth → ingest 落库
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("webapi")

SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
PROJECT_ROOT = SCRIPTS_DIR.parent
DATA_BASE_DIR = PROJECT_ROOT / "data" / "advisor_runs"


async def _run_subprocess(cmd: List[str], cwd: str = None) -> tuple:
    """运行子进程，返回 (returncode, stdout, stderr)"""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd or str(PROJECT_ROOT),
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode, stdout.decode("utf-8", errors="replace"), stderr.decode("utf-8", errors="replace")


def _find_python() -> str:
    """查找项目 Python（同 run.sh 逻辑）"""
    for candidate in [
        str(PROJECT_ROOT / ".venv" / "bin" / "python"),
        str(PROJECT_ROOT / "venv" / "bin" / "python"),
    ]:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return "python3"


async def run_collect(user_id: str, run_dir: Path) -> bool:
    """Phase 1: 数据收集 → run_dir

    关键市场数据（宏观/水温/北向）缺失时，collect_data.py 会按「数据盲区不出处方」
    硬闸返回非 0，这里捕获其 stdout 中的中止原因供上层透传给前端。
    """
    run_dir.mkdir(parents=True, exist_ok=True)
    python = _find_python()
    collect_script = str(SCRIPTS_DIR / "collect_data.py")

    rc, out, err = await _run_subprocess(
        [python, collect_script, "--user-id", user_id, "--out-dir", str(run_dir)]
    )
    if rc != 0:
        # 提取硬闸中止原因（❌ 之后的关键数据缺失说明），透传给前端
        reason = ""
        if "数据盲区不出处方" in out:
            lines = [ln.strip() for ln in out.splitlines()
                     if "未取到" in ln or "数据盲区不出处方" in ln]
            reason = " ".join(lines)[:300]
        run_collect.last_error = reason or err[:300] or "数据收集失败"
        logger.error(f"[v3-runner] collect 失败: {(reason or err)[:500]}")
        return False
    run_collect.last_error = ""
    return True


async def run_analyze(user_id: str, run_dir: Path, to_stage: Optional[str] = None) -> bool:
    """Phase 2: Agent 推理（via run.sh analyze）"""
    cmd = [
        str(SCRIPTS_DIR / "run.sh"),
        "analyze",
        "--data-dir", str(run_dir),
        "--user-id", user_id,
    ]
    if to_stage:
        cmd.extend(["--to", to_stage])

    rc, out, err = await _run_subprocess(cmd)
    if rc != 0:
        logger.error(f"[v3-runner] analyze 失败 (to={to_stage}): {err[:500]}")
        return False
    return True


async def run_ingest(user_id: str, run_dir: Path) -> bool:
    """Phase 3: ingest 落库"""
    python = _find_python()
    ingest_script = str(SCRIPTS_DIR / "ingest_advice.py")

    rc, out, err = await _run_subprocess(
        [python, ingest_script, "--data-dir", str(run_dir), "--user-id", user_id]
    )
    if rc != 0:
        logger.error(f"[v3-runner] ingest 失败: {err[:500]}")
        return False
    return True


def read_industry_allocations(run_dir: Path) -> list:
    """读取 industry_allocations.json 返回行业列表"""
    path = run_dir / "industry_allocations.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data if isinstance(data, list) else data.get("allocations", [])
        return items
    except Exception as e:
        logger.warning(f"[v3-runner] 读取 industry_allocations 失败: {e}")
        return []


def write_selected_industries(run_dir: Path, industries: List[str]) -> None:
    """写入 selected_industries.json 供 scout/pm 过滤"""
    path = run_dir / "selected_industries.json"
    path.write_text(json.dumps(industries, ensure_ascii=False), encoding="utf-8")


async def plan(user_id: str) -> dict:
    """两阶段 plan: collect + analyze --to industry

    Returns:
        {"run_dir": str, "industries": [...], "error": str|None}
    """
    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S") + f"_{uuid.uuid4().hex[:6]}"
    run_dir = DATA_BASE_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # Phase 1: collect
    if not await run_collect(user_id, run_dir):
        reason = getattr(run_collect, "last_error", "") or "数据收集失败"
        return {"run_dir": str(run_dir), "industries": [], "error": reason}

    # Phase 2: analyze --to industry
    if not await run_analyze(user_id, run_dir, to_stage="industry"):
        return {"run_dir": str(run_dir), "industries": [], "error": "行业分析失败"}

    # 读取产出
    allocations = read_industry_allocations(run_dir)
    industries = []
    for a in allocations:
        if not isinstance(a, dict):
            continue
        industries.append({
            "industry": a.get("industry", ""),
            "market": a.get("market", "cn"),
            "go_nogo": a.get("go_nogo", ""),
            "stance": a.get("stance", ""),
            "final_weight": a.get("final_weight", 0),
            "vitality_level": a.get("vitality_level", ""),
            "reasoning": a.get("reasoning", ""),
            "lifecycle": a.get("lifecycle", ""),
            "priority": a.get("priority", 0),
        })

    return {"run_dir": str(run_dir), "industries": industries, "error": None}


async def execute(user_id: str, run_dir_str: str, selected_industries: List[str]) -> dict:
    """两阶段 execute: 写 selected_industries → analyze from scout → ingest

    Returns:
        {"error": str|None}
    """
    run_dir = Path(run_dir_str)
    if not run_dir.exists():
        return {"error": f"数据目录不存在: {run_dir_str}"}

    # 写入用户选择
    write_selected_industries(run_dir, selected_industries)

    # Phase 2 续: analyze --from scout（industry 阶段已缓存）
    if not await run_analyze(user_id, run_dir, to_stage=None):
        return {"error": "Agent 推理失败"}

    # Phase 3: ingest
    if not await run_ingest(user_id, run_dir):
        return {"error": "保存到数据库失败"}

    return {"error": None}
