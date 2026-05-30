"""组合总览服务：汇率、仓位汇总、持仓上下文构造"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import asyncio
import logging

from pymongo import UpdateOne
from app.core.database import get_mongo_db

logger = logging.getLogger("webapi")


class PortfolioService:
    def __init__(self):
        self._db = None

    @property
    def db(self):
        if self._db is None:
            self._db = get_mongo_db()
        return self._db

    async def _get_exchange_rate(self, currency: str) -> float:
        """获取外币兑人民币汇率，结果缓存到 MongoDB（TTL 24h）"""
        if currency == "CNY":
            return 1.0

        cached = await self.db["exchange_rates"].find_one({"currency": currency})
        if cached:
            cached_at = cached.get("cached_at", "")
            try:
                cached_time = datetime.fromisoformat(cached_at)
                if datetime.utcnow() - cached_time < timedelta(hours=24):
                    return float(cached.get("rate", 1.0))
            except Exception:
                pass

        try:
            import akshare as ak
            df = await asyncio.wait_for(
                asyncio.to_thread(ak.currency_boc_safe),
                timeout=10.0,
            )
            rate = None
            if currency == "HKD":
                row = df[df["货币名称"].str.contains("港币")]
                if not row.empty:
                    rate = float(row.iloc[0]["中行折算价"]) / 100
            elif currency == "USD":
                row = df[df["货币名称"].str.contains("美元")]
                if not row.empty:
                    rate = float(row.iloc[0]["中行折算价"]) / 100

            if rate and rate > 0:
                await self.db["exchange_rates"].update_one(
                    {"currency": currency},
                    {"$set": {
                        "currency": currency,
                        "rate": rate,
                        "cached_at": datetime.utcnow().isoformat(),
                    }},
                    upsert=True,
                )
                return rate
        except Exception as e:
            logger.warning(f"汇率获取失败 {currency}: {e}")

        if cached:
            return float(cached.get("rate", 1.0))

        fallback = {"HKD": 0.92, "USD": 7.25}
        return fallback.get(currency, 1.0)

    async def _get_fund_nav(self, code: str) -> Optional[float]:
        """获取场外基金最新单位净值，缓存对齐北京时间 21:00 (UTC 13:00) 净值发布时间"""
        cached = await self.db["fund_nav_cache"].find_one({"code": code})
        if cached:
            try:
                cached_time = datetime.fromisoformat(cached["cached_at"])
                now_utc = datetime.utcnow()
                # 北京时间 21:00 = UTC 13:00
                cutoff_utc = now_utc.replace(hour=13, minute=0, second=0, microsecond=0)
                if now_utc.hour < 13:
                    cutoff_utc -= timedelta(days=1)
                if cached_time >= cutoff_utc:
                    return float(cached["nav"])
            except Exception:
                pass

        try:
            import akshare as ak
            df = await asyncio.wait_for(
                asyncio.to_thread(ak.fund_open_fund_info_em, symbol=code),
                timeout=10.0,
            )
            if df is None or df.empty:
                return None

            latest = df.iloc[-1]
            nav = float(latest["单位净值"])
            nav_date = str(latest.get("净值日期", ""))

            if nav <= 0:
                return None

            # 非交易日去重：同一净值日期只更新 cached_at，不覆盖 nav
            if cached and cached.get("nav_date") == nav_date:
                await self.db["fund_nav_cache"].update_one(
                    {"code": code},
                    {"$set": {"cached_at": datetime.utcnow().isoformat()}},
                )
                return float(cached["nav"])

            await self.db["fund_nav_cache"].update_one(
                {"code": code},
                {"$set": {
                    "code": code,
                    "nav": nav,
                    "nav_date": nav_date,
                    "cached_at": datetime.utcnow().isoformat(),
                }},
                upsert=True,
            )
            return nav

        except Exception as e:
            logger.warning(f"基金净值获取失败 {code}: {e}")
            if cached:
                return float(cached.get("nav"))
            return None

    async def _get_position_name(self, code: str, instrument_type: str) -> str:
        """解析持仓名称：stock/etf 查 stock_basic_info，fund 查 fund_nav_cache"""
        if instrument_type in ("fund", "other"):
            cache = await self.db["fund_nav_cache"].find_one({"code": code})
            name = cache.get("name") if cache else None
            if name:
                return name
            try:
                import akshare as ak
                info = await asyncio.to_thread(ak.fund_individual_basic_info_xq, symbol=code)
                if info is not None and not info.empty:
                    # 字段名是"基金名称"，不是"基金简称"
                    row = info[info["item"] == "基金名称"]
                    name = str(row.iloc[0]["value"]) if not row.empty else None
                if name:
                    await self.db["fund_nav_cache"].update_one(
                        {"code": code},
                        {"$set": {"name": name}},
                        upsert=True,
                    )
                    return name
            except Exception as e:
                logger.warning(f"获取基金名称失败 {code}: {e}")
            return code

        # stock/etf/bond/other: 查 stock_basic_info
        info = await self.db["stock_basic_info"].find_one(
            {"code": code}, {"name": 1}
        )
        if info and info.get("name"):
            return info["name"]
        # HK/US: check market-specific collections
        for coll_name in ["stock_basic_info_hk", "stock_basic_info_us"]:
            info = await self.db[coll_name].find_one({"code": code}, {"name": 1})
            if info and info.get("name"):
                return info["name"]
        # 本地无数据，实时从 AKShare 查并写入缓存
        try:
            import akshare as ak
            df = await asyncio.to_thread(ak.stock_individual_info_em, symbol=code)
            name = None
            if df is not None and not df.empty:
                row = df[df["item"] == "股票简称"]
                if not row.empty:
                    name = str(row.iloc[0]["value"])
            if name:
                await self.db["stock_basic_info"].update_one(
                    {"code": code},
                    {"$set": {"code": code, "name": name}},
                    upsert=True,
                )
                return name
        except Exception as e:
            logger.warning(f"AKShare 查询股票名称失败 {code}: {e}")

        # HK/US fallback: try yfinance
        try:
            import yfinance as yf
            clean = str(code).lstrip("0") or "0"
            ticker_sym = f"{clean.zfill(4)}.HK"
            ticker = await asyncio.to_thread(lambda: yf.Ticker(ticker_sym))
            info = await asyncio.to_thread(lambda: ticker.info)
            name = info.get("longName") or info.get("shortName")
            if name:
                await self.db["stock_basic_info"].update_one(
                    {"code": code},
                    {"$set": {"code": code, "name": name}},
                    upsert=True,
                )
                return name
        except Exception as e:
            logger.warning(f"yfinance 查询股票名称失败 {code}: {e}")
        return code

    async def _get_last_price(self, code: str, market: str, instrument_type: str = "stock") -> Optional[float]:
        """获取最新价格（复用 paper.py 的逻辑）"""
        if instrument_type in ("fund", "other"):
            return await self._get_fund_nav(code)

        if market == "CN":
            q = await self.db["market_quotes"].find_one(
                {"$or": [{"code": code}, {"symbol": code}]},
                {"_id": 0, "close": 1},
            )
            if q and q.get("close") is not None:
                try:
                    price = float(q["close"])
                    if price > 0:
                        return price
                except Exception:
                    pass

            basic_info = await self.db["stock_basic_info"].find_one(
                {"$or": [{"code": code}, {"symbol": code}]},
                {"_id": 0, "current_price": 1},
            )
            if basic_info and basic_info.get("current_price") is not None:
                try:
                    price = float(basic_info["current_price"])
                    if price > 0:
                        return price
                except Exception:
                    pass
            return None

        elif market in ["HK", "US"]:
            try:
                from app.services.foreign_stock_service import ForeignStockService
                service = ForeignStockService(db=self.db)
                quote = await service.get_quote(market, code, force_refresh=False)
                if quote:
                    price = quote.get("price") or quote.get("current_price") or quote.get("close")
                    if price and float(price) > 0:
                        return float(price)
            except Exception as e:
                logger.error(f"获取{market}股价格失败 {code}: {e}")

        return None

    async def _fetch_position_detail(self, p: dict) -> dict:
        """并行安全：获取单个持仓的价格、名称、汇率（带超时）"""
        code = p.get("code")
        market = p.get("market", "CN")
        currency = p.get("currency", "CNY")
        qty = int(p.get("quantity", 0))
        avg_cost = float(p.get("avg_cost", 0.0))
        instr_type = p.get("instrument_type", "stock")

        async def _safe_price():
            try:
                return await asyncio.wait_for(
                    self._get_last_price(code, market, instr_type),
                    timeout=8.0,
                )
            except Exception:
                return None

        async def _safe_rate():
            try:
                return await asyncio.wait_for(
                    self._get_exchange_rate(currency),
                    timeout=5.0,
                )
            except Exception:
                return {"HKD": 0.92, "USD": 7.25}.get(currency, 1.0)

        async def _safe_name():
            try:
                return await asyncio.wait_for(
                    self._get_position_name(code, instr_type),
                    timeout=12.0,
                )
            except Exception:
                return code

        last_price, exchange_rate, name = await asyncio.gather(
            _safe_price(), _safe_rate(), _safe_name(),
        )

        market_value_local = round((last_price or 0.0) * qty, 2)
        market_value_cny = round(market_value_local * exchange_rate, 2)

        cost_cny = round(avg_cost * qty * exchange_rate, 2)
        pnl_cny = round(market_value_cny - cost_cny, 2) if last_price else None
        pnl_pct = round((last_price - avg_cost) / avg_cost * 100, 2) if last_price and avg_cost > 0 else None

        return {
            "code": code,
            "name": name,
            "market": market,
            "currency": currency,
            "quantity": qty,
            "avg_cost": avg_cost,
            "last_price": last_price,
            "exchange_rate": exchange_rate,
            "market_value_cny": market_value_cny,
            "pnl_cny": pnl_cny,
            "pnl_pct": pnl_pct,
            "weight": 0.0,
            "buy_date": p.get("buy_date"),
            "notes": p.get("notes"),
            "instrument_type": instr_type,
        }

    async def _refresh_cn_market_quotes(self, codes: List[str]) -> None:
        """批量刷新 A 股实时行情到 market_quotes（使用新浪财经 API，兼容代理环境）"""
        if not codes:
            return
        try:
            import re as _re
            from urllib.request import Request, urlopen as _urlopen

            # 构建新浪行情 URL（新浪 API 可穿透 Clash/代理）
            sina_codes = []
            for c in codes:
                c = str(c).strip()
                if c.startswith(("6", "68")):
                    sina_codes.append(f"sh{c}")
                elif c.startswith(("0", "3")):
                    sina_codes.append(f"sz{c}")
                elif c.startswith(("8", "4")):
                    sina_codes.append(f"bj{c}")
            if not sina_codes:
                return

            url = "http://hq.sinajs.cn/list=" + ",".join(sina_codes)

            def _fetch():
                req = Request(url, headers={
                    "User-Agent": "Mozilla/5.0",
                    "Referer": "https://finance.sina.com.cn",
                })
                with _urlopen(req, timeout=10.0) as resp:
                    return resp.read().decode("gb2312", errors="replace")

            text = await asyncio.wait_for(asyncio.to_thread(_fetch), timeout=12.0)

            now = datetime.utcnow()
            bulk_ops = []
            for line in text.strip().split("\n"):
                m = _re.match(r'var hq_str_(\w+)=\"(.*)\"', line)
                if not m:
                    continue
                sym = m.group(1)
                fields = m.group(2).split(",")
                if len(fields) < 4:
                    continue
                code = sym[2:]  # 去掉 sh/sz/bj 前缀
                try:
                    price_val = float(fields[3])
                except (ValueError, TypeError):
                    continue
                if price_val <= 0:
                    continue
                name = fields[0]
                bulk_ops.append(
                    UpdateOne(
                        {"code": code},
                        {"$set": {
                            "code": code,
                            "name": name,
                            "close": price_val,
                            "open": float(fields[1] or 0),
                            "pre_close": float(fields[2] or 0),
                            "high": float(fields[4] or 0),
                            "low": float(fields[5] or 0),
                            "updated_at": now,
                        }},
                        upsert=True,
                    )
                )
            if bulk_ops:
                col = self.db["market_quotes"]
                await col.bulk_write(bulk_ops, ordered=False)
                logger.info(f"批量刷新 {len(bulk_ops)} 只 A 股行情到 market_quotes（新浪来源）")
        except asyncio.TimeoutError:
            logger.warning("新浪行情批量刷新超时(12s)")
        except Exception as e:
            logger.error(f"批量刷新 A 股行情失败: {e}")

    async def get_portfolio_summary(self, user_id: str) -> Dict[str, Any]:
        """聚合所有持仓，计算总资产、总盈亏、仓位占比"""
        acc = await self.db["paper_accounts"].find_one({"user_id": user_id})
        available_cash = float(acc.get("available_cash", 0.0)) if acc else 0.0
        total_invested = float(acc.get("total_invested", 0.0)) if acc else 0.0

        positions = await self.db["paper_positions"].find({"user_id": user_id}).to_list(None)

        # 批量刷新 A 股实时行情（一次 AKShare 调用覆盖全部 CN 持仓）
        cn_codes = [p["code"] for p in positions if p.get("market", "CN") == "CN" and p.get("instrument_type", "stock") not in ("fund", "other")]
        if cn_codes:
            await self._refresh_cn_market_quotes(cn_codes)

        # 并行获取价格+名称+汇率，35个持仓从串行 ~100s 降至 ~8s
        position_details: List[Dict[str, Any]] = await asyncio.gather(
            *[self._fetch_position_detail(p) for p in positions]
        )

        total_market_value_cny = sum(p["market_value_cny"] for p in position_details)

        total_assets = round(total_market_value_cny + available_cash, 2)
        total_pnl = round(total_assets - total_invested, 2) if total_invested > 0 else 0.0
        total_pnl_pct = round(total_pnl / total_invested * 100, 2) if total_invested > 0 else 0.0

        for pos in position_details:
            if total_assets > 0:
                pos["weight"] = round(pos["market_value_cny"] / total_assets * 100, 2)

        return {
            "total_invested": round(total_invested, 2),
            "available_cash": round(available_cash, 2),
            "total_assets": total_assets,
            "total_market_value_cny": round(total_market_value_cny, 2),
            "total_pnl": total_pnl,
            "total_pnl_pct": total_pnl_pct,
            "positions": position_details,
        }

    async def get_portfolio_context(self, user_id: str) -> str:
        """构造持仓摘要字符串供分析引擎使用"""
        summary = await self.get_portfolio_summary(user_id)

        if not summary["positions"]:
            return ""

        lines = [
            "=== 用户持仓信息 ===",
            f"总投入: ¥{summary['total_invested']:,.2f}",
            f"可用现金: ¥{summary['available_cash']:,.2f}",
            f"总资产: ¥{summary['total_assets']:,.2f}",
            f"总盈亏: ¥{summary['total_pnl']:,.2f} ({summary['total_pnl_pct']:+.2f}%)",
            "",
            "持仓明细:",
        ]

        sorted_positions = sorted(
            summary["positions"],
            key=lambda x: x["market_value_cny"],
            reverse=True,
        )

        for i, pos in enumerate(sorted_positions[:20]):
            pnl_str = f"¥{pos['pnl_cny']:,.2f} ({pos['pnl_pct']:+.2f}%)" if pos["pnl_cny"] is not None else "N/A"
            inst = pos.get("instrument_type", "stock")
            lines.append(
                f"  {pos['code']} {pos.get('name', '')} ({pos['market']}/{inst}): "
                f"{pos['quantity']}股 × ¥{pos['avg_cost']:.2f} | "
                f"市值¥{pos['market_value_cny']:,.2f} | "
                f"仓位{pos['weight']:.1f}% | "
                f"盈亏{pnl_str}"
            )

        if len(summary["positions"]) > 20:
            lines.append(f"  ... 及其他 {len(summary['positions']) - 20} 只持仓")

        return "\n".join(lines)
