"""industry_candidates.py — 权益深链内置候选行业（FR-006 AC6.1）

提供「值得深辩的候选行业」清单，依据：
  1. 内置长期投资主题（结构性赛道，穿越周期）
  2. 风口/景气方向（best-effort 复用 industry_vitality.score_all_industries，缺库/缺网降级）

CLI 对话由 AI 据此询问/推荐用户「先深度分析哪些行业」（AC6.1）；
用户可全采纳、可自选、可加自定义行业。本模块纯产出建议，不触发任何 LLM。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger("webapi")

# ── 内置候选行业（长期主题 + 风口，申万/投资主题口径） ──────────────────
# theme：长期结构性赛道；cyclical：景气驱动方向。rationale 供 AI 对话向用户解释。
BUILTIN_CANDIDATES: List[Dict[str, Any]] = [
    {"name": "人工智能/算力", "kind": "theme", "rationale": "AI 大模型驱动算力/推理长期需求，产业链最长"},
    {"name": "半导体/国产替代", "kind": "theme", "rationale": "国产替代 + 周期复苏双驱动，自主可控政策强支撑"},
    {"name": "创新药/生物科技", "kind": "theme", "rationale": "人口老龄化 + 出海授权（BD）兑现，长期景气"},
    {"name": "新能源车/智能驾驶", "kind": "theme", "rationale": "渗透率提升 + 智驾平权，结构性成长"},
    {"name": "高端制造/机器人", "kind": "theme", "rationale": "人形机器人 + 工业自动化，制造升级主线"},
    {"name": "军工/国防", "kind": "theme", "rationale": "地缘紧张 + 装备更新周期，订单能见度高"},
    {"name": "电力/公用事业", "kind": "cyclical", "rationale": "高股息防御 + 电改红利，低波稳现金流"},
    {"name": "消费（可选）", "kind": "cyclical", "rationale": "内需政策刺激下的顺周期修复弹性"},
    {"name": "有色/资源", "kind": "cyclical", "rationale": "供给约束 + 货币宽松下的资源再定价"},
    {"name": "互联网/平台", "kind": "theme", "rationale": "降本增效 + AI 应用落地，估值修复"},
]

# vitality 引擎的 18 bucket → 候选行业名的粗映射（增强用，非必需）
_VITALITY_HINT = {
    "人工智能/软件": "人工智能/算力",
    "半导体": "半导体/国产替代",
    "医药健康": "创新药/生物科技",
    "新能源车": "新能源车/智能驾驶",
    "高端制造": "高端制造/机器人",
    "能源/公用": "电力/公用事业",
    "消费（可选）": "消费（可选）",
    "化工/材料": "有色/资源",
    "互联网/平台": "互联网/平台",
}


def builtin_candidates() -> List[Dict[str, Any]]:
    """返回内置候选行业清单（深拷贝，调用方可安全修改）。"""
    return [dict(c) for c in BUILTIN_CANDIDATES]


async def recommend_candidates(top_n: int = 6) -> Dict[str, Any]:
    """产出候选行业推荐：内置清单 + best-effort 景气榜增强。

    返回：
      {
        "candidates": [{name, kind, rationale, vitality_score?, top3?}],
        "vitality_available": bool,
        "note": str
      }
    缺库/缺网时仅给内置清单并标注降级（不报错，AC6.1）。
    """
    candidates = builtin_candidates()
    by_name = {c["name"]: c for c in candidates}
    vitality_available = False
    note = "内置长期主题候选；未取到实时景气榜，排序按内置优先级"

    try:
        from app.services.industry_vitality import score_all_industries

        scores = await score_all_industries()
        vitality_available = True
        note = "内置候选 + 实时景气榜增强排序"
        for s in scores:
            ind = getattr(s, "industry", None)
            mapped = _VITALITY_HINT.get(ind)
            if mapped and mapped in by_name:
                by_name[mapped]["vitality_score"] = round(float(getattr(s, "total_score", 0) or 0), 3)
                by_name[mapped]["top3"] = bool(getattr(s, "top3_flag", False))
        # 景气榜 top3 里若有未在内置清单的方向，补进候选
        for s in scores:
            if getattr(s, "top3_flag", False):
                mapped = _VITALITY_HINT.get(getattr(s, "industry", ""), getattr(s, "industry", ""))
                if mapped and mapped not in by_name:
                    extra = {
                        "name": mapped, "kind": "cyclical",
                        "rationale": "当前景气榜 top3 新方向",
                        "vitality_score": round(float(getattr(s, "total_score", 0) or 0), 3),
                        "top3": True,
                    }
                    candidates.append(extra)
                    by_name[mapped] = extra
    except Exception as e:  # 缺 Mongo / 缺网 / 引擎异常 → 降级
        logger.info("候选行业景气增强降级（仅用内置清单）: %s", e)

    # 排序：top3 优先 → vitality_score 降序 → 内置顺序
    def _sort_key(c: Dict[str, Any]):
        return (
            0 if c.get("top3") else 1,
            -(c.get("vitality_score") or 0),
        )

    candidates.sort(key=_sort_key)
    return {
        "candidates": candidates[:top_n] if top_n else candidates,
        "all_candidates": candidates,
        "vitality_available": vitality_available,
        "note": note,
    }
