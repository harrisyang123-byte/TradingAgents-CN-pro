"""基金数据服务：AKShare 数据获取 + 30 天缓存"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import asyncio
import logging
import time

from app.core.database import get_mongo_db

logger = logging.getLogger("webapi")

CACHE_TTL_DAYS = 30


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
            df = await asyncio.to_thread(ak.fund_individual_basic_info_xq, code)
            if df is None or df.empty:
                return None

            info = {}
            for _, row in df.iterrows():
                key = str(row.get("item", "")).strip()
                val = row.get("value")
                if key == "基金简称":
                    info["name"] = val
                elif key == "基金代码":
                    info["code"] = val
                elif key == "基金类型":
                    info["type"] = val
                elif key == "最新规模":
                    # 格式: "420.50亿元" → 420.50
                    if val:
                        val_str = str(val).replace("亿元", "").replace("亿元", "").strip()
                        try:
                            info["scale"] = float(val_str)
                        except ValueError:
                            info["scale"] = None
                elif key == "成立日期":
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
            df = await asyncio.to_thread(ak.fund_portfolio_hold_em, code)
            if df is None or df.empty:
                return []

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

    async def get_sector_distribution(self, code: str) -> Optional[List[Dict[str, Any]]]:
        """获取基金行业分布

        绕过 akshare (版本 1.18.60 列数硬编码已不兼容东方财富新字段数)，
        直接调天天基金 API，从最近可查年份中取最新季度的行业配置。
        """
        cache_key = f"fund_sector_distribution:{code}"
        cached = await self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        try:
            import requests as _requests
        except Exception:
            return []

        url = "https://api.fund.eastmoney.com/f10/HYPZ/"
        headers = {
            "Referer": "https://fundf10.eastmoney.com/",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        }

        # 先取 ListYears，按最近年份尝试
        try:
            r = await asyncio.to_thread(
                _requests.get, url,
                params={"fundCode": code, "year": "2025"},
                headers=headers,
                timeout=15,
            )
            data = r.json()
            years = sorted(
                [int(y) for y in (data.get("Data", {}) or {}).get("ListYears", [])],
                reverse=True,
            )
        except Exception:
            years = []
        if not years:
            years = list(range(2024, 2012, -1))

        sectors_raw = []
        chosen_year = None
        for y in years[:6]:  # 最多试6年
            try:
                params = {"fundCode": code, "year": str(y)}
                r = await asyncio.to_thread(_requests.get, url, params=params, headers=headers, timeout=15)
                d = r.json()
                quarters = (d.get("Data", {}) or {}).get("QuarterInfos", []) or []
                # 取最新一个季度（API 已按 Quarter 降序）
                for q in quarters:
                    items = q.get("HYPZInfo", []) or []
                    if items:
                        sectors_raw = items
                        chosen_year = y
                        break
                if sectors_raw:
                    break
            except Exception:
                continue

        if not sectors_raw:
            await self._set_cache(cache_key, [])
            return []

        sectors = []
        for item in sectors_raw:
            name = str(item.get("HYMC", ""))
            ratio_str = item.get("ZJZBL")
            try:
                ratio = float(ratio_str) if ratio_str else 0.0
            except (ValueError, TypeError):
                ratio = 0.0
            if name and ratio > 0:
                sectors.append({"sector_name": name, "ratio": ratio})

        logger.info(
            f"基金行业分布 {code} (数据年份={chosen_year}): {len(sectors)} 个行业"
        )
        await self._set_cache(cache_key, sectors)
        return sectors
