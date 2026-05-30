"""
敞口引擎（Exposure Engine）

基金持仓拆解 → 底层股票敞口 → 合并矩阵
让组合顾问看到穿透基金后的真实风险暴露面。
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.core.database import get_mongo_db

logger = logging.getLogger("webapi")


@dataclass
class StockExposure:
    code: str
    name: str
    sector: str = ""
    direct_weight: float = 0.0
    fund_derived_weight: float = 0.0
    total_weight: float = 0.0
    fund_sources: List[str] = field(default_factory=list)  # 哪些基金持有此标的


@dataclass
class ExposureMatrix:
    stock_exposures: List[StockExposure] = field(default_factory=list)
    sector_concentration: Dict[str, float] = field(default_factory=dict)
    top_overlaps: List[StockExposure] = field(default_factory=list)  # 被多只基金持有的标的
    stale_funds: List[Dict[str, Any]] = field(default_factory=list)
    hhi: float = 0.0
    penetration_ratio: float = 0.0  # 已穿透比例

    @property
    def summary(self) -> str:
        if not self.stock_exposures:
            return "无持仓数据"

        total_count = len(self.stock_exposures)
        sorted_by_weight = sorted(self.stock_exposures, key=lambda x: x.total_weight, reverse=True)
        top5 = sorted_by_weight[:5]
        top5_pct = sum(x.total_weight for x in top5)

        lines = [
            f"敞口矩阵: {total_count} 只底层标的",
            f"Top-5 占比: {top5_pct:.1f}%",
            f"HHI 集中度: {self.hhi:.3f}",
            f"穿透率: {self.penetration_ratio:.1f}%",
        ]

        if self.top_overlaps:
            overlaps_desc = ", ".join(
                f"{x.name}({x.total_weight:.1f}%, 来自{','.join(x.fund_sources)})"
                for x in self.top_overlaps[:5]
            )
            lines.append(f"重叠暴露: {overlaps_desc}")

        if self.stale_funds:
            stale_names = [f["name"] for f in self.stale_funds]
            lines.append(f"数据过期: {', '.join(stale_names)}")

        if self.hhi > 0.15:
            lines.append("⚠ 集中度偏高 (HHI > 0.15)")

        sector_sorted = sorted(self.sector_concentration.items(), key=lambda x: x[1], reverse=True)
        if sector_sorted and sector_sorted[0][1] > 40:
            lines.append(f"⚠ 行业集中: {sector_sorted[0][0]} 占比 {sector_sorted[0][1]:.1f}%")

        return "\n".join(lines)


class ExposureService:
    """敞口引擎：穿透基金持仓，计算真实敞口矩阵"""

    STALE_DAYS = 45

    def __init__(self):
        self._db = None

    @property
    def db(self):
        if self._db is None:
            self._db = get_mongo_db()
        return self._db

    async def compute(self, portfolio_summary: Dict[str, Any]) -> ExposureMatrix:
        """计算组合的穿透敞口矩阵"""
        positions = portfolio_summary.get("positions", [])
        if not positions:
            return ExposureMatrix()

        stocks = [p for p in positions if p.get("instrument_type") == "stock"]
        funds = [p for p in positions if p.get("instrument_type") == "fund"]
        others = [p for p in positions if p.get("instrument_type") not in ("stock", "fund")]

        total_weight = sum(p.get("weight", 0) for p in positions)
        if total_weight == 0:
            return ExposureMatrix()

        # 归一化权重
        norm = 100.0 / total_weight if total_weight > 0 else 1.0

        exposure_map: Dict[str, StockExposure] = {}

        # 1. 直接个股
        for pos in stocks:
            code = pos.get("code", "")
            if not code:
                continue
            w = pos.get("weight", 0) * norm
            exposure_map[code] = StockExposure(
                code=code,
                name=pos.get("name", code),
                direct_weight=w,
                total_weight=w,
            )

        # 2. 基金穿透
        penetrated_weight = 0.0
        stale_funds: List[Dict[str, Any]] = []
        fund_tasks = [self._resolve_fund_holdings(f, norm) for f in funds]
        fund_results = await asyncio.gather(*fund_tasks)

        for fund_pos, fund_matrix in zip(funds, fund_results):
            fund_weight = fund_pos.get("weight", 0) * norm
            fund_code = fund_pos.get("code", "")
            fund_name = fund_pos.get("name", fund_code)

            if not fund_matrix:
                continue

            holdings, is_stale = fund_matrix
            if is_stale:
                stale_funds.append({"code": fund_code, "name": fund_name})

            if not holdings:
                continue

            penetrated_weight += fund_weight  # type: ignore[operator]

            for h in holdings:
                sc = h.get("stock_code", "")
                sn = h.get("stock_name", sc)
                ratio = float(h.get("ratio", 0))
                derived_w = fund_weight * ratio / 100.0

                if sc in exposure_map:
                    exp = exposure_map[sc]
                    exp.fund_derived_weight += derived_w
                    exp.total_weight += derived_w
                    exp.fund_sources.append(fund_code)
                else:
                    exposure_map[sc] = StockExposure(
                        code=sc,
                        name=sn,
                        fund_derived_weight=derived_w,
                        total_weight=derived_w,
                        fund_sources=[fund_code],
                    )

        # 3. 集中度
        all_exposures = list(exposure_map.values())
        all_exposures.sort(key=lambda x: x.total_weight, reverse=True)
        self._compute_hhi(all_exposures, norm)
        top_overlaps = [e for e in all_exposures if len(e.fund_sources) > 1][:10]

        # 4. 行业分布
        sector_map: Dict[str, float] = defaultdict(float)
        for exp in all_exposures:
            sector = self._get_sector(exp.code)
            exp.sector = sector
            sector_map[sector] += exp.total_weight

        penetration_ratio = penetrated_weight / 100.0 * 100 if total_weight > 0 else 0

        hhi_value = sum(e.total_weight ** 2 for e in all_exposures) / 10000  # normalize to 0-1

        return ExposureMatrix(
            stock_exposures=all_exposures,
            sector_concentration=dict(sorted(sector_map.items(), key=lambda x: x[1], reverse=True)),
            top_overlaps=top_overlaps,
            stale_funds=stale_funds,
            hhi=round(hhi_value, 4),
            penetration_ratio=round(penetration_ratio, 1),
        )

    async def _resolve_fund_holdings(
        self, fund_pos: Dict[str, Any], norm: float
    ) -> Optional[tuple]:
        """获取基金前十大重仓股，返回 (holdings, is_stale)"""
        code = fund_pos.get("code", "")
        if not code:
            return None

        try:
            from app.services.fund_service import FundService

            fund_svc = FundService()
            holdings = await fund_svc.get_top_holdings(code)
            if not holdings:
                return None

            # 检查数据新鲜度
            cache_key = f"fund_top_holdings:{code}"
            cached_doc = await self.db["fund_data_cache"].find_one({"key": cache_key})
            is_stale = False
            if cached_doc:
                cached_at = cached_doc.get("updated_at")
                if cached_at:
                    if isinstance(cached_at, str):
                        cached_at = datetime.fromisoformat(cached_at.replace("Z", "+00:00"))
                    if datetime.utcnow() - cached_at.replace(tzinfo=None) > timedelta(days=self.STALE_DAYS):
                        is_stale = True

            return holdings, is_stale
        except Exception as e:
            logger.warning(f"获取基金持仓失败 {code}: {e}")
            return None

    def _get_sector(self, code: str) -> str:
        """获取标的行业分类（简化版，后续可对接 get_industry_for_code）"""
        try:
            from tradingagents.dataflows.industry import get_industry_for_code
            return get_industry_for_code(code) or "未知"
        except Exception:
            return "未知"

    def _compute_hhi(self, exposures: List[StockExposure], norm: float) -> None:
        """计算 HHI 已移到 compute() 中内联"""
        pass

    def format_context_for_advisor(self, matrix: ExposureMatrix) -> str:
        """将敞口矩阵格式化为 AdvisorGraph 可读的上下文"""
        if not matrix.stock_exposures:
            return ""

        lines = [
            "## 敞口矩阵（基金穿透后真实暴露）",
            "",
            f"底层标的数: {len(matrix.stock_exposures)} | 穿透率: {matrix.penetration_ratio:.1f}% | HHI: {matrix.hhi:.3f}",
            "",
            "### Top-10 底层敞口",
            "| 标的 | 行业 | 直接 | 基金穿透 | 合计 |",
            "|------|------|------|----------|------|",
        ]

        for e in matrix.stock_exposures[:10]:
            lines.append(
                f"| {e.name}({e.code}) | {e.sector} | {e.direct_weight:.1f}% | "
                f"{e.fund_derived_weight:.1f}% | {e.total_weight:.1f}% |"
            )

        if matrix.top_overlaps:
            lines.append("")
            lines.append("### 重叠暴露（被多只基金持有）")
            for e in matrix.top_overlaps[:5]:
                lines.append(f"- {e.name}: {e.total_weight:.1f}% (来自 {', '.join(e.fund_sources)})")

        if matrix.sector_concentration:
            lines.append("")
            lines.append("### 行业集中度")
            for sector, weight in list(matrix.sector_concentration.items())[:5]:
                lines.append(f"- {sector}: {weight:.1f}%")

        if matrix.stale_funds:
            stale = ", ".join(f"{f['name']}({f['code']})" for f in matrix.stale_funds)
            lines.append(f"\n⚠ 数据过期: {stale}")

        return "\n".join(lines)
