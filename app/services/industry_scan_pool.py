"""行业扫描池自动构建

每次分析启动时，自动合并持仓行业 + watchlist + 景气前3名，
输出带来源标注的行业列表。
"""

from __future__ import annotations
import logging
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


@dataclass
class IndustryScanPool:
    industries: List[IndustryScanItem] = field(default_factory=list)

    def to_industry_list(self) -> List[str]:
        return [i.industry for i in self.industries]

    def to_source_map(self) -> Dict[str, str]:
        return {i.industry: i.source for i in self.industries}

    def to_dict(self) -> List[dict]:
        return [
            {"industry": i.industry, "source": i.source, "vitality_score": i.vitality_score}
            for i in self.industries
        ]


async def build_scan_pool(db, user_id: str) -> IndustryScanPool:
    """构建行业扫描池：持仓行业 + watchlist + 景气前3名 合并去重"""

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

    # 3. 景气打分前3名（自动补充）
    try:
        vitality_results = await score_all_industries()
        top3 = [s for s in vitality_results if s.top3_flag]
    except Exception as e:
        logger.warning(f"[ScanPool] 景气打分失败: {e}")
        top3 = []

    for score in top3:
        if score.industry not in scan_set:
            scan_set[score.industry] = IndustryScanItem(
                industry=score.industry,
                source="vitality",
                vitality_score=score.total_score,
            )

    # 4. 去重后构建扫描池
    pool = IndustryScanPool(industries=list(scan_set.values()))

    logger.info(
        f"[ScanPool] 构建完成，扫描 {len(pool.industries)} 个行业: "
        f"持仓{sum(1 for i in pool.industries if i.source == 'holding')} + "
        f"watchlist{sum(1 for i in pool.industries if i.source == 'watchlist')} + "
        f"景气{sum(1 for i in pool.industries if i.source == 'vitality')}"
    )
    return pool
