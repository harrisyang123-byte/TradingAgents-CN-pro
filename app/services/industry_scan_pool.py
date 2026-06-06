"""行业扫描池自动构建

每次分析启动时，自动合并持仓行业 + watchlist + 景气前3名，
输出带来源标注的行业列表。
"""

from __future__ import annotations
import logging
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Any, Set

from app.services.industry_vitality import score_all_industries

logger = logging.getLogger(__name__)

# 排除非可投资行业
INVESTABLE_BUCKETS = {
    "消费（必选）", "消费（可选）", "互联网/平台", "半导体", "人工智能/软件",
    "新能源（发电）", "新能源车", "通信/5G", "金融/保险", "医药健康",
    "高端制造", "化工/材料", "基建/地产", "能源/公用",
}

CURRENCY_BUCKETS = {"债券/固收", "宽基指数", "全球配置", "现金"}


@dataclass
class IndustryScanItem:
    industry: str
    source: str  # holding / watchlist / vitality
    vitality_score: float = 0.0
    cached: bool = False  # industry_coverage 缓存是否有效


@dataclass
class IndustryScanPool:
    industries: List[IndustryScanItem] = field(default_factory=list)

    def to_industry_list(self) -> List[str]:
        return [i.industry for i in self.industries]

    def to_source_map(self) -> Dict[str, str]:
        return {i.industry: i.source for i in self.industries}

    def to_dict(self) -> List[dict]:
        return [
            {"industry": i.industry, "source": i.source, "vitality_score": i.vitality_score,
             "cached": i.cached}
            for i in self.industries
        ]


async def build_scan_pool(db, user_id: str, vitality_scores=None,
                          all_industries: bool = False) -> IndustryScanPool:
    """构建行业扫描池：持仓行业 + watchlist + 景气前3名 合并去重

    深辩范围设计（方案②，长期主义）：
      - 持仓 + watchlist → 必跑深辩
      - 景气 top3 新方向 → 自动补充进深辩，**无估值闸**
        （估值约束交给下游裁判/PM 调权重与买点，不在准入处否决）
      - 货币/类现金 bucket（现金/债券固收/宽基/全球配置）不进行业深辩，
        那是大类资产层的职责。

    vitality_scores: 可选，外部预算好的 score_all_industries() 结果，
        避免重复触发昂贵的全量景气扫描（采数阶段已算过一次）。

    all_industries: 全量行业开关（方案①）。为 True 时，景气榜不再只取
        top3，而是把全部可投资行业（已排除货币/类现金 bucket）都纳入
        深辩范围。持仓/watchlist 仍保留各自来源标注，其余补充项标注
        source="vitality"。用于"全量行业深辩"场景。
    """

    scan_set: Dict[str, IndustryScanItem] = {}

    # 1. 持仓行业（必选）
    cursor = db["paper_positions"].find(
        {"user_id": user_id, "industry": {"$nin": [None, "", "未分类"]}},
        {"industry": 1},
    )
    async for doc in cursor:
        ind = doc["industry"]
        if ind not in scan_set:
            scan_set[ind] = IndustryScanItem(industry=ind, source="holding")

    # 2. watchlist（必选）
    cursor = db["watchlist"].find({"user_id": user_id})
    async for doc in cursor:
        ind = doc["industry"]
        if ind not in scan_set:
            scan_set[ind] = IndustryScanItem(industry=ind, source="watchlist")

    # 3. 景气打分（默认补 top3 新方向；all_industries=True 时纳入全部可投资行业，均无估值闸）
    try:
        vitality_results = vitality_scores if vitality_scores is not None else await score_all_industries()
        if all_industries:
            candidates = list(vitality_results)
        else:
            candidates = [s for s in vitality_results if s.top3_flag]
    except Exception as e:
        logger.warning(f"[ScanPool] 景气打分失败: {e}")
        candidates = []

    for score in candidates:
        # 货币/类现金 bucket 归大类资产层管，不进行业深辩
        if score.industry in CURRENCY_BUCKETS:
            continue
        if score.industry not in scan_set:
            scan_set[score.industry] = IndustryScanItem(
                industry=score.industry,
                source="vitality",
                vitality_score=score.total_score,
            )

    # 4. 去重后构建扫描池
    pool = IndustryScanPool(industries=list(scan_set.values()))

    # 5. 检查 industry_coverage 缓存是否有效
    now_iso = datetime.utcnow().isoformat()
    for item in pool.industries:
        try:
            cov = await db["industry_coverage"].find_one(
                {"user_id": user_id, "industry_name": item.industry},
                {"expires_at": 1},
            )
            if cov:
                expires = cov.get("expires_at", "")
                if expires and expires > now_iso:
                    item.cached = True
        except Exception:
            pass

    cached_count = sum(1 for i in pool.industries if i.cached)

    logger.info(
        f"[ScanPool] 构建完成，扫描 {len(pool.industries)} 个行业: "
        f"持仓{sum(1 for i in pool.industries if i.source == 'holding')} + "
        f"watchlist{sum(1 for i in pool.industries if i.source == 'watchlist')} + "
        f"景气{sum(1 for i in pool.industries if i.source == 'vitality')}"
        f"，缓存有效 {cached_count} 个"
    )
    return pool
