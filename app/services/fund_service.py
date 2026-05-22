"""基金数据服务：AKShare 数据获取 + 30 天缓存"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import asyncio
import logging
import time

from app.core.database import get_mongo_db

logger = logging.getLogger("webapi")

CACHE_TTL_DAYS = 30
NAV_CACHE_TTL_DAYS = 1  # 净值每日更新


class FundService:
    def __init__(self):
        self._db = None
        # 内存缓存: {key: {data, cached_at}}
        self._memory_cache: Dict[str, Dict[str, Any]] = {}

    @property
    def db(self):
        if self._db is None:
            self._db = get_mongo_db()
        return self._db

    def _is_cache_valid(self, cached_at: float) -> bool:
        return time.time() - cached_at < CACHE_TTL_DAYS * 86400

    async def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """先查内存缓存，再查 MongoDB 缓存"""
        mem = self._memory_cache.get(cache_key)
        if mem and self._is_cache_valid(mem["cached_at"]):
            return mem["data"]

        doc = await self.db["fund_data_cache"].find_one({"key": cache_key})
        if doc:
            cached_at = doc.get("cached_at", 0)
            if self._is_cache_valid(cached_at):
                self._memory_cache[cache_key] = {"data": doc["data"], "cached_at": cached_at}
                return doc["data"]

        return None

    async def _set_cache(self, cache_key: str, data: Any):
        """写入内存 + MongoDB 缓存"""
        now = time.time()
        self._memory_cache[cache_key] = {"data": data, "cached_at": now}
        await self.db["fund_data_cache"].update_one(
            {"key": cache_key},
            {"$set": {"key": cache_key, "data": data, "cached_at": now}},
            upsert=True,
        )

    async def get_basic_info(self, code: str) -> Optional[Dict[str, Any]]:
        """获取基金基础信息"""
        cache_key = f"fund_basic_info:{code}"

        cached = await self._get_from_cache(cache_key)
        if cached:
            return cached

        try:
            import akshare as ak
            df = await asyncio.to_thread(ak.fund_individual_basic_info_xq, symbol=code)
            if df is None or df.empty:
                return None

            info = {}
            for _, row in df.iterrows():
                key = str(row.get("item", "")).strip()
                val = row.get("value")
                if key in ("基金简称", "基金名称"):
                    info["name"] = val
                elif key == "基金代码":
                    info["code"] = val
                elif key == "基金类型":
                    info["type"] = val
                elif key == "最新规模":
                    # 格式: "267.93亿" 或 "420.50亿元" → 267.93
                    if val:
                        val_str = str(val).replace("亿元", "").replace("亿", "").strip()
                        try:
                            info["scale"] = float(val_str)
                        except ValueError:
                            info["scale"] = None
                elif key in ("成立日期", "成立时间"):
                    info["establishment_date"] = str(val) if val else None
                elif key == "基金经理":
                    info["manager"] = str(val) if val else None

            result = {
                "code": code,
                "name": info.get("name"),
                "type": info.get("type"),
                "scale": info.get("scale"),
                "establishment_date": info.get("establishment_date"),
                "manager": info.get("manager"),
            }

            await self._set_cache(cache_key, result)
            return result
        except Exception as e:
            logger.warning(f"获取基金基础信息失败 {code}: {e}")
            return None

    async def get_top_holdings(self, code: str) -> Optional[List[Dict[str, Any]]]:
        """获取基金前十大重仓股"""
        cache_key = f"fund_top_holdings:{code}"

        cached = await self._get_from_cache(cache_key)
        if cached:
            return cached

        try:
            import akshare as ak
            from datetime import datetime
            current_year = str(datetime.now().year)
            df = await asyncio.to_thread(ak.fund_portfolio_hold_em, symbol=code, date=current_year)
            if df is None or df.empty:
                # 尝试上一年
                prev_year = str(datetime.now().year - 1)
                df = await asyncio.to_thread(ak.fund_portfolio_hold_em, symbol=code, date=prev_year)

            if df is None or df.empty:
                # 无数据：可能是 QDII/ETF/货币基金，缓存空结果避免重复请求
                result: List[Dict[str, Any]] = []
                await self._set_cache(cache_key, result)
                return result

            holdings = []
            for _, row in df.head(10).iterrows():
                holdings.append({
                    "stock_code": str(row.get("股票代码", "")),
                    "stock_name": str(row.get("股票名称", "")),
                    "ratio": float(row.get("占净值比例", 0)) if row.get("占净值比例") else 0,
                    "change": float(row.get("较上期变化", 0)) if row.get("较上期变化") else None,
                })

            await self._set_cache(cache_key, holdings)
            return holdings
        except Exception as e:
            logger.warning(f"获取基金持仓失败 {code}: {e}")
            return None

    async def get_nav_history(self, code: str, period: str = "1年") -> Optional[List[Dict[str, Any]]]:
        """获取基金净值历史走势（缓存 1 天）"""
        cache_key = f"fund_nav_history:{code}:{period}"

        # 净值用 1 天 TTL
        mem = self._memory_cache.get(cache_key)
        if mem and time.time() - mem["cached_at"] < NAV_CACHE_TTL_DAYS * 86400:
            return mem["data"]
        doc = await self.db["fund_data_cache"].find_one({"key": cache_key})
        if doc and time.time() - doc.get("cached_at", 0) < NAV_CACHE_TTL_DAYS * 86400:
            self._memory_cache[cache_key] = {"data": doc["data"], "cached_at": doc["cached_at"]}
            return doc["data"]

        try:
            import akshare as ak
            df = await asyncio.to_thread(
                ak.fund_open_fund_info_em, symbol=code, indicator="单位净值走势", period=period
            )
            if df is None or df.empty:
                return []

            # 按日期排序，取最近 N 条
            df = df.sort_values("净值日期").reset_index(drop=True)
            limit_map = {"1月": 30, "3月": 90, "6月": 180, "1年": 365, "3年": 1095, "成立来": None}
            limit = limit_map.get(period, 365)
            if limit:
                df = df.tail(limit)

            result = [
                {
                    "date": str(row["净值日期"]),
                    "nav": float(row["单位净值"]) if row["单位净值"] else None,
                    "daily_return": float(row["日增长率"]) if row["日增长率"] else None,
                }
                for _, row in df.iterrows()
            ]

            await self._set_cache(cache_key, result)
            return result
        except Exception as e:
            logger.warning(f"获取基金净值历史失败 {code}: {e}")
            return None

    async def get_sector_distribution(self, code: str) -> Optional[List[Dict[str, Any]]]:
        """获取基金行业分布"""
        cache_key = f"fund_sector_distribution:{code}"

        cached = await self._get_from_cache(cache_key)
        if cached:
            return cached

        try:
            import akshare as ak
            try:
                df = await asyncio.to_thread(ak.fund_portfolio_industry_allocation_em, symbol=code)
            except ValueError as e:
                # 某些基金（如 270042）在 AKShare 解析数据时因为列数不匹配会抛出 ValueError，这里做容错处理
                logger.warning(f"获取基金 {code} 行业分布数据源解析失败: {e}")
                return []

            if df is None or df.empty:
                return []

            sectors = []
            if df is not None and not df.empty and "行业类别" in df.columns:
                for _, row in df.iterrows():
                    sectors.append({
                        "sector_name": str(row.get("行业类别", "")),
                        "ratio": float(row.get("占净值比例", 0)) if row.get("占净值比例") else 0,
                    })

            await self._set_cache(cache_key, sectors)
            return sectors
        except Exception as e:
            logger.warning(f"获取基金行业分布失败 {code}: {e}")
            return None
