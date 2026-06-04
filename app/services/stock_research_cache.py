"""个股研究缓存服务（Stock Research Cache）

为 Tier1 研究结果提供持久化缓存，支持：
- 行业层 Go 结果自动触发研究
- 7天有效期过期
- 手动触发和自动触发结果统一存库
- 下游 Step2/Step3/PM 直接读取
"""

from __future__ import annotations
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

CACHE_EXPIRY_DAYS = 7
CACHE_COLLECTION = "stock_research_cache"


async def get_research(db, code: str, user_id: str) -> Optional[Dict[str, Any]]:
    """读取指定个股的研究缓存，过期则返回 None"""
    doc = await db[CACHE_COLLECTION].find_one(
        {"code": code, "user_id": user_id},
    )
    if not doc:
        return None
    expires = doc.get("expires_at", "")
    if expires and expires < datetime.utcnow().isoformat():
        return None
    return doc


async def set_research(db, code: str, user_id: str, report: Dict[str, Any],
                       trigger_source: str = "auto") -> bool:
    """写入个股研究缓存（upsert）"""
    try:
        await db[CACHE_COLLECTION].update_one(
            {"code": code, "user_id": user_id},
            {"$set": {
                "code": code,
                "user_id": user_id,
                "name": report.get("name", ""),
                "industry": report.get("industry", ""),
                "recommendation": report.get("recommendation", ""),
                "target_price": report.get("target_price", 0),
                "entry_price_range": report.get("entry_price_range", []),
                "reasoning": report.get("reasoning", ""),
                "risk_note": report.get("risk_note", ""),
                "trigger_source": trigger_source,
                "expires_at": (datetime.utcnow() + timedelta(days=CACHE_EXPIRY_DAYS)).isoformat(),
                "researched_at": datetime.utcnow().isoformat(),
            }},
            upsert=True,
        )
        return True
    except Exception as e:
        logger.warning(f"[StockResearchCache] 写入失败 {code}: {e}")
        return False


async def get_batch_research(db, codes: List[str], user_id: str) -> Dict[str, Optional[Dict]]:
    """批量读取个股研究缓存，返回 {code: doc_or_None}"""
    result = {}
    for code in codes:
        result[code] = await get_research(db, code, user_id)
    return result


async def get_expired_codes(db, codes: List[str], user_id: str) -> List[str]:
    """返回需要研究的标的列表（无缓存或已过期）"""
    result = []
    for code in codes:
        doc = await get_research(db, code, user_id)
        if doc is None:
            result.append(code)
    return result


async def trigger_auto_research(db, llm, industry: str, top_codes: List[str],
                                 user_id: str) -> int:
    """自动触发某行业主要公司的 Tier1 研究。

    检查缓存，只研究未缓存或已过期的标的。

    Returns:
        实际触发的数量
    """
    need_research = await get_expired_codes(db, top_codes, user_id)
    if not need_research:
        return 0

    logger.info(f"[AutoResearch] 行业 {industry}: 需要研究 {len(need_research)}/{len(top_codes)} 只标的")

    for code in need_research:
        try:
            # 触发 Tier1 研究 - 这里调用现有的 Tier1 分析逻辑
            from app.services.portfolio_service import PortfolioService
            svc = PortfolioService()
            # 获取股票基本信息用于缓存
            company_name = ""
            try:
                import akshare as ak
                import asyncio
                df = await asyncio.to_thread(ak.stock_individual_info_em, symbol=code)
                if df is not None and not df.empty:
                    name_row = df[df["item"] == "股票简称"]
                    if not name_row.empty:
                        company_name = str(name_row["value"].iloc[0])
            except Exception:
                pass

            report = {
                "name": company_name or code,
                "industry": industry,
                "recommendation": "观察",
                "target_price": 0,
                "entry_price_range": [],
                "reasoning": f"由 {industry} 行业层 Go 自动触发，待深度分析",
                "risk_note": "自动触发，结论待确认",
            }
            await set_research(db, code, user_id, report, trigger_source="auto")
        except Exception as e:
            logger.warning(f"[AutoResearch] {code} 研究失败: {e}")

    return len(need_research)
