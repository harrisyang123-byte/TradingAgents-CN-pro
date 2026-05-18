"""组合总览服务：汇率、仓位汇总、持仓上下文构造"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging

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
            df = ak.currency_boc_safe()
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

    async def _get_last_price(self, code: str, market: str) -> Optional[float]:
        """获取最新价格（复用 paper.py 的逻辑）"""
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

    async def get_portfolio_summary(self, user_id: str) -> Dict[str, Any]:
        """聚合所有持仓，计算总资产、总盈亏、仓位占比"""
        acc = await self.db["paper_accounts"].find_one({"user_id": user_id})
        available_cash = float(acc.get("available_cash", 0.0)) if acc else 0.0
        total_invested = float(acc.get("total_invested", 0.0)) if acc else 0.0

        positions = await self.db["paper_positions"].find({"user_id": user_id}).to_list(None)

        position_details: List[Dict[str, Any]] = []
        total_market_value_cny = 0.0

        for p in positions:
            code = p.get("code")
            market = p.get("market", "CN")
            currency = p.get("currency", "CNY")
            qty = int(p.get("quantity", 0))
            avg_cost = float(p.get("avg_cost", 0.0))

            last_price = await self._get_last_price(code, market)
            exchange_rate = await self._get_exchange_rate(currency)

            market_value_local = round((last_price or 0.0) * qty, 2)
            market_value_cny = round(market_value_local * exchange_rate, 2)
            total_market_value_cny += market_value_cny

            cost_cny = round(avg_cost * qty * exchange_rate, 2)
            pnl_cny = round(market_value_cny - cost_cny, 2) if last_price else None
            pnl_pct = round((last_price - avg_cost) / avg_cost * 100, 2) if last_price and avg_cost > 0 else None

            position_details.append({
                "code": code,
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
                "instrument_type": p.get("instrument_type", "stock"),
            })

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
                f"  {pos['code']}({pos['market']}/{inst}): "
                f"{pos['quantity']}股 × ¥{pos['avg_cost']:.2f} | "
                f"市值¥{pos['market_value_cny']:,.2f} | "
                f"仓位{pos['weight']:.1f}% | "
                f"盈亏{pnl_str}"
            )

        if len(summary["positions"]) > 20:
            lines.append(f"  ... 及其他 {len(summary['positions']) - 20} 只持仓")

        return "\n".join(lines)
