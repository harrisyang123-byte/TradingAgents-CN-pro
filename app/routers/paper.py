from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, Any, List, Tuple
from datetime import datetime
import logging
import re
import uuid

from app.routers.auth_db import get_current_user
from app.core.database import get_mongo_db
from app.core.response import ok

router = APIRouter(prefix="/portfolio", tags=["portfolio"])
logger = logging.getLogger("webapi")


class PlaceOrderRequest(BaseModel):
    code: str = Field(..., description="股票代码（支持A股/港股/美股）")
    side: Literal["buy", "sell"]
    quantity: int = Field(..., gt=0)
    price: float = Field(..., gt=0, description="成交价格（用户填写）")
    market: Optional[str] = Field(None, description="市场类型 (CN/HK/US)，不传则自动识别")
    analysis_id: Optional[str] = None


class AddPositionRequest(BaseModel):
    code: str = Field(..., description="股票代码（支持A股/港股/美股）")
    quantity: float = Field(..., gt=0)
    avg_cost: float = Field(..., gt=0, description="买入均价")
    buy_date: Optional[str] = Field(None, description="买入日期 (YYYY-MM-DD)")
    notes: Optional[str] = Field(None, description="备注")
    market: Optional[str] = Field(None, description="市场类型 (CN/HK/US)，不传则自动识别")
    instrument_type: Optional[str] = Field(None, description="标的类型: stock/etf/fund/bond/other，不传默认为 stock")
    name: Optional[str] = Field(None, description="名称（可选，不传则自动查询）")


class UpdatePositionRequest(BaseModel):
    quantity: Optional[float] = Field(None, ge=0)
    avg_cost: Optional[float] = Field(None, gt=0)
    notes: Optional[str] = None
    instrument_type: Optional[str] = Field(None, description="标的类型: stock/etf/fund/bond/other")


class UpdateAccountRequest(BaseModel):
    total_invested: Optional[float] = Field(None, ge=0, description="总投入资金（人民币）")
    available_cash: Optional[float] = Field(None, ge=0, description="可用现金（人民币）")


def _detect_market_and_code(code: str) -> Tuple[str, str]:
    """检测股票代码的市场类型并标准化代码"""
    code = code.strip().upper()

    if code.endswith('.HK'):
        return ('HK', code[:-3].zfill(5))

    if re.match(r'^[A-Z]+$', code):
        return ('US', code)

    if re.match(r'^\d{4,5}$', code):
        return ('HK', code.zfill(5))

    if re.match(r'^\d{6}$', code):
        return ('CN', code)

    return ('CN', code.zfill(6))


CURRENCY_MAP = {"CN": "CNY", "HK": "HKD", "US": "USD"}


async def _get_or_create_account(user_id: str) -> Dict[str, Any]:
    """获取或创建账户（单账户单钱包人民币）"""
    db = get_mongo_db()
    acc = await db["paper_accounts"].find_one({"user_id": user_id})
    if not acc:
        now = datetime.utcnow().isoformat()
        acc = {
            "user_id": user_id,
            "available_cash": 0.0,
            "total_invested": 0.0,
            "created_at": now,
            "updated_at": now,
        }
        await db["paper_accounts"].insert_one(acc)
    else:
        # 兼容旧格式：多币种 cash dict → 单一 available_cash
        cash_val = acc.get("cash")
        if isinstance(cash_val, dict):
            migrated_cash = float(cash_val.get("CNY", 0.0))
            await db["paper_accounts"].update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "available_cash": migrated_cash,
                        "total_invested": acc.get("total_invested", 0.0),
                        "updated_at": datetime.utcnow().isoformat(),
                    },
                    "$unset": {"cash": "", "realized_pnl": "", "settings": ""},
                },
            )
            acc = await db["paper_accounts"].find_one({"user_id": user_id})
        elif "available_cash" not in acc:
            migrated_cash = float(cash_val or 0.0) if cash_val is not None else 0.0
            await db["paper_accounts"].update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "available_cash": migrated_cash,
                        "total_invested": acc.get("total_invested", 0.0),
                        "updated_at": datetime.utcnow().isoformat(),
                    },
                },
            )
            acc = await db["paper_accounts"].find_one({"user_id": user_id})
    return acc


async def _get_last_price(code: str, market: str, instrument_type: str = "stock") -> Optional[float]:
    """获取最新价格（支持多市场）"""
    db = get_mongo_db()

    if market == "CN":
        if instrument_type == "other":
            try:
                nav_doc = await db["fund_nav_cache"].find_one({"code": code})
                if nav_doc and nav_doc.get("nav") is not None:
                    return float(nav_doc["nav"])
            except Exception:
                pass
            return None

        q = await db["market_quotes"].find_one(
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

        basic_info = await db["stock_basic_info"].find_one(
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

            service = ForeignStockService(db=db)
            quote = await service.get_quote(market, code, force_refresh=False)
            if quote:
                price = quote.get("price") or quote.get("current_price") or quote.get("close")
                if price and float(price) > 0:
                    return float(price)
        except Exception as e:
            logger.error(f"获取{market}股价格失败 {code}: {e}")
            return None

    return None


async def _create_transaction(user_id: str, code: str, market: str, side: str,
                              quantity: int, price: float, notes: str = None):
    """创建交易记录"""
    db = get_mongo_db()
    currency = CURRENCY_MAP.get(market, "CNY")
    now_iso = datetime.utcnow().isoformat()
    trade_doc = {
        "user_id": user_id,
        "code": code,
        "market": market,
        "currency": currency,
        "side": side,
        "quantity": quantity,
        "price": price,
        "amount": round(price * quantity, 2),
        "timestamp": now_iso,
    }
    if notes:
        trade_doc["notes"] = notes
    await db["paper_trades"].insert_one(trade_doc)


# ── Account endpoints ──────────────────────────────────────

@router.get("/account", response_model=dict)
async def get_account(current_user: dict = Depends(get_current_user)):
    """获取账户信息：总投入、可用现金、总资产、总盈亏"""
    db = get_mongo_db()
    acc = await _get_or_create_account(current_user["id"])

    positions = await db["paper_positions"].find({"user_id": current_user["id"]}).to_list(None)
    total_market_value_cny = 0.0
    total_pnl = 0.0
    for p in positions:
        code = p.get("code")
        market = p.get("market", "CN")
        qty = int(p.get("quantity", 0))
        avg_cost = float(p.get("avg_cost", 0))
        currency = CURRENCY_MAP.get(market, "CNY")
        last = await _get_last_price(code, market, p.get("instrument_type", "stock"))
        if last is not None:
            rate = 1.0
            if currency != "CNY":
                rate_doc = await db["exchange_rates"].find_one({"currency": currency})
                if rate_doc:
                    rate = float(rate_doc.get("rate", 1.0))
            total_market_value_cny += last * qty * rate
            total_pnl += round((last - avg_cost) * qty * rate, 2)

    available_cash = float(acc.get("available_cash", 0.0))
    total_invested = float(acc.get("total_invested", 0.0))
    total_assets = round(total_market_value_cny + available_cash, 2)
    total_pnl = round(total_pnl, 2)
    total_pnl_pct = round(total_pnl / total_invested * 100, 2) if total_invested > 0 else 0.0

    return ok({
        "total_invested": round(total_invested, 2),
        "available_cash": round(available_cash, 2),
        "total_assets": total_assets,
        "total_pnl": total_pnl,
        "total_pnl_pct": total_pnl_pct,
        "updated_at": acc.get("updated_at"),
    })


@router.put("/account", response_model=dict)
async def update_account(payload: UpdateAccountRequest, current_user: dict = Depends(get_current_user)):
    """设置总投入和可用现金"""
    acc = await _get_or_create_account(current_user["id"])
    db = get_mongo_db()

    updates: Dict[str, Any] = {"updated_at": datetime.utcnow().isoformat()}
    if payload.total_invested is not None:
        updates["total_invested"] = payload.total_invested
    if payload.available_cash is not None:
        updates["available_cash"] = payload.available_cash

    await db["paper_accounts"].update_one(
        {"user_id": current_user["id"]}, {"$set": updates}
    )
    return ok({"message": "账户已更新"})


@router.get("/summary", response_model=dict)
async def get_summary(current_user: dict = Depends(get_current_user)):
    """组合总览：总资产、总盈亏、每只持仓的市值/仓位占比/盈亏"""
    from app.services.portfolio_service import PortfolioService
    service = PortfolioService()
    summary = await service.get_portfolio_summary(current_user["id"])
    return ok(summary)


# ── Position CRUD endpoints ────────────────────────────────

@router.get("/positions", response_model=dict)
async def list_positions(current_user: dict = Depends(get_current_user)):
    """获取持仓列表"""
    db = get_mongo_db()
    items = await db["paper_positions"].find({"user_id": current_user["id"]}).to_list(None)
    enriched: List[Dict[str, Any]] = []
    for p in items:
        code = p.get("code")
        market = p.get("market", "CN")
        currency = p.get("currency", "CNY")
        qty = int(p.get("quantity", 0))
        avg_cost = float(p.get("avg_cost", 0.0))

        last = await _get_last_price(code, market, p.get("instrument_type", "stock"))
        mkt = round((last or 0.0) * qty, 2)
        enriched.append({
            "code": code,
            "market": market,
            "currency": currency,
            "quantity": qty,
            "avg_cost": avg_cost,
            "last_price": last,
            "market_value": mkt,
            "unrealized_pnl": None if last is None else round((last - avg_cost) * qty, 2),
            "buy_date": p.get("buy_date"),
            "notes": p.get("notes"),
            "instrument_type": p.get("instrument_type", "stock"),
        })
    return ok({"items": enriched})


@router.post("/positions", response_model=dict)
async def add_position(payload: AddPositionRequest, current_user: dict = Depends(get_current_user)):
    """创建/追加持仓"""
    db = get_mongo_db()

    if payload.market:
        market = payload.market.upper()
        normalized_code = payload.code.strip().upper()
    else:
        market, normalized_code = _detect_market_and_code(payload.code)

    currency = CURRENCY_MAP.get(market, "CNY")
    now_iso = datetime.utcnow().isoformat()

    pos = await db["paper_positions"].find_one(
        {"user_id": current_user["id"], "code": normalized_code}
    )

    if pos:
        old_qty = int(pos.get("quantity", 0))
        old_cost = float(pos.get("avg_cost", 0.0))
        new_qty = old_qty + payload.quantity
        new_avg = round(
            (old_cost * old_qty + payload.avg_cost * payload.quantity) / new_qty, 4
        )
        await db["paper_positions"].update_one(
            {"_id": pos["_id"]},
            {"$set": {"quantity": new_qty, "avg_cost": new_avg, "updated_at": now_iso}},
        )
    else:
        # 持仓录入时自动查 name + 前置行业分类
        pos_name = getattr(payload, "name", "") or ""
        itype = payload.instrument_type or "stock"
        if not pos_name:
            try:
                if itype in ("fund", "etf", "other", "bond"):
                    from app.services.fund_service import FundService
                    info = await FundService().get_basic_info(normalized_code)
                    if info and info.get("name"):
                        pos_name = info["name"]
                else:
                    import akshare as ak
                    import asyncio
                    df = await asyncio.to_thread(ak.stock_individual_info_em, symbol=normalized_code)
                    if df is not None and not df.empty:
                        nr = df[df["item"] == "股票简称"]
                        if not nr.empty:
                            pos_name = str(nr["value"].iloc[0])
            except Exception as e:
                logger.debug(f"自动查名称失败 {normalized_code}: {e}")

        from app.services.industry_classifier import classify_by_akshare
        try:
            industry = await classify_by_akshare(
                code=normalized_code,
                name=pos_name,
                instrument_type=itype,
            )
        except Exception:
            industry = "未分类"

        new_pos = {
            "user_id": current_user["id"],
            "code": normalized_code,
            "name": pos_name,
            "market": market,
            "currency": currency,
            "quantity": payload.quantity,
            "avg_cost": payload.avg_cost,
            "buy_date": payload.buy_date,
            "notes": payload.notes,
            "instrument_type": itype,
            "industry": industry,
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        await db["paper_positions"].insert_one(new_pos)

    await _create_transaction(
        current_user["id"], normalized_code, market, "buy",
        payload.quantity, payload.avg_cost, payload.notes,
    )

    return ok({"message": "持仓已添加", "code": normalized_code, "market": market})


@router.put("/positions/{code}", response_model=dict)
async def update_position(code: str, payload: UpdatePositionRequest,
                          current_user: dict = Depends(get_current_user)):
    """修改持仓字段"""
    db = get_mongo_db()
    _, normalized_code = _detect_market_and_code(code)

    pos = await db["paper_positions"].find_one(
        {"user_id": current_user["id"], "code": normalized_code}
    )
    if not pos:
        raise HTTPException(status_code=404, detail=f"未找到持仓: {normalized_code}")

    updates: Dict[str, Any] = {"updated_at": datetime.utcnow().isoformat()}
    if payload.quantity is not None:
        updates["quantity"] = payload.quantity
    if payload.avg_cost is not None:
        updates["avg_cost"] = payload.avg_cost
    if payload.notes is not None:
        updates["notes"] = payload.notes
    if payload.instrument_type is not None:
        updates["instrument_type"] = payload.instrument_type
    # 补填 name 和 industry（不重新分类已有数据的行业）
    changed = False
    if not pos.get("name"):
        itype = pos.get("instrument_type", "stock")
        try:
            if itype in ("fund", "etf", "other", "bond"):
                from app.services.fund_service import FundService
                info = await FundService().get_basic_info(normalized_code)
                if info and info.get("name"):
                    updates["name"] = info["name"]
            elif _is_a_share_code(normalized_code):
                import akshare as ak
                import asyncio
                df = await asyncio.to_thread(ak.stock_individual_info_em, symbol=normalized_code)
                if df is not None and not df.empty:
                    nr = df[df["item"] == "股票简称"]
                    if not nr.empty:
                        updates["name"] = str(nr["value"].iloc[0])
        except Exception:
            pass
        changed = True
    if not pos.get("industry"):
        from app.services.industry_classifier import classify_by_akshare
        try:
            n = updates.get("name", pos.get("name", ""))
            updates["industry"] = await classify_by_akshare(
                code=normalized_code, name=n,
                instrument_type=pos.get("instrument_type", "stock"),
            )
        except Exception:
            updates["industry"] = "未分类"
        changed = True

    await db["paper_positions"].update_one({"_id": pos["_id"]}, {"$set": updates})

    await _create_transaction(
        current_user["id"], normalized_code, pos.get("market", "CN"), "adjust",
        payload.quantity or pos.get("quantity", 0),
        payload.avg_cost or pos.get("avg_cost", 0.0),
    )

    return ok({"message": "持仓已更新", "code": normalized_code})


@router.delete("/positions/{code}", response_model=dict)
async def delete_position(code: str, current_user: dict = Depends(get_current_user)):
    """删除持仓"""
    db = get_mongo_db()
    _, normalized_code = _detect_market_and_code(code)

    result = await db["paper_positions"].delete_one(
        {"user_id": current_user["id"], "code": normalized_code}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail=f"未找到持仓: {normalized_code}")

    return ok({"message": "持仓已删除", "code": normalized_code})


# ── Order endpoint ──────────────────────────────────────────

@router.post("/order", response_model=dict)
async def place_order(payload: PlaceOrderRequest, current_user: dict = Depends(get_current_user)):
    """提交订单：用户填写价格，buy 增持仓扣现金，sell 减持仓加现金"""
    db = get_mongo_db()

    if payload.market:
        market = payload.market.upper()
        normalized_code = payload.code.strip().upper()
    else:
        market, normalized_code = _detect_market_and_code(payload.code)

    side = payload.side
    qty = int(payload.quantity)
    price = payload.price
    analysis_id = payload.analysis_id
    now_iso = datetime.utcnow().isoformat()
    notional = round(price * qty, 2)

    acc = await _get_or_create_account(current_user["id"])

    if side == "buy":
        available_cash = float(acc.get("available_cash", 0.0))
        if available_cash < notional:
            raise HTTPException(
                status_code=400,
                detail=f"可用现金不足：需要 {notional:.2f}，可用 {available_cash:.2f}",
            )

        await db["paper_accounts"].update_one(
            {"user_id": current_user["id"]},
            {"$set": {
                "available_cash": round(available_cash - notional, 2),
                "updated_at": now_iso,
            }},
        )

        pos = await db["paper_positions"].find_one(
            {"user_id": current_user["id"], "code": normalized_code}
        )
        currency = CURRENCY_MAP.get(market, "CNY")

        if not pos:
            new_pos = {
                "user_id": current_user["id"],
                "code": normalized_code,
                "market": market,
                "currency": currency,
                "quantity": qty,
                "avg_cost": price,
                "instrument_type": "stock",
                "created_at": now_iso,
                "updated_at": now_iso,
            }
            await db["paper_positions"].insert_one(new_pos)
        else:
            old_qty = int(pos.get("quantity", 0))
            old_cost = float(pos.get("avg_cost", 0.0))
            new_qty = old_qty + qty
            new_avg = round((old_cost * old_qty + price * qty) / new_qty, 4)
            await db["paper_positions"].update_one(
                {"_id": pos["_id"]},
                {"$set": {"quantity": new_qty, "avg_cost": new_avg, "updated_at": now_iso}},
            )

    else:  # sell
        pos = await db["paper_positions"].find_one(
            {"user_id": current_user["id"], "code": normalized_code}
        )
        if not pos or int(pos.get("quantity", 0)) < qty:
            current_qty = int(pos.get("quantity", 0)) if pos else 0
            raise HTTPException(
                status_code=400,
                detail=f"卖出数量超过持仓：需要 {qty}，持有 {current_qty}",
            )

        old_qty = int(pos["quantity"])
        new_qty = old_qty - qty

        available_cash = float(acc.get("available_cash", 0.0))
        await db["paper_accounts"].update_one(
            {"user_id": current_user["id"]},
            {"$set": {
                "available_cash": round(available_cash + notional, 2),
                "updated_at": now_iso,
            }},
        )

        if new_qty == 0:
            await db["paper_positions"].delete_one({"_id": pos["_id"]})
        else:
            await db["paper_positions"].update_one(
                {"_id": pos["_id"]},
                {"$set": {"quantity": new_qty, "updated_at": now_iso}},
            )

    order_doc = {
        "user_id": current_user["id"],
        "code": normalized_code,
        "market": market,
        "side": side,
        "quantity": qty,
        "price": price,
        "amount": notional,
        "status": "filled",
        "created_at": now_iso,
        "filled_at": now_iso,
    }
    if analysis_id:
        order_doc["analysis_id"] = analysis_id
    await db["paper_orders"].insert_one(order_doc)

    await _create_transaction(
        current_user["id"], normalized_code, market, side, qty, price,
    )

    return ok({"order": {k: v for k, v in order_doc.items() if k != "_id"}})


# ── Portfolio Overview ─────────────────────────────────────

@router.get("/overview", response_model=dict)
async def get_portfolio_overview(current_user: dict = Depends(get_current_user)):
    """组合总揽：行业覆盖矩阵（持仓现状 + 分析覆盖 + 处方建议）

    v3: 优先读最近一次 COMPLETED advice 的 industry_matrix 或 synthesis_result。
    无 industry_matrix 时降级到现有拼接逻辑（向后兼容）。
    """
    db = get_mongo_db()
    user_id = current_user["id"]

    # 尝试读最近一次 advice 的 industry_matrix
    latest_advice = await db["portfolio_advice"].find_one(
        {"user_id": user_id, "status": "COMPLETED"},
        sort=[("created_at", -1)],
    )

    synthesis = (latest_advice or {}).get("synthesis_result", {}) or {}
    from app.services.portfolio_service import PortfolioService
    pf_svc = PortfolioService()
    pf_summary = await pf_svc.get_portfolio_summary(user_id)
    total_assets = pf_summary.get("total_assets", 0)
    matrix = synthesis.get("industry_matrix", []) or latest_advice.get("industry_matrix", [])

    # 主路径: market_intel.industries (L1 行业研究员输出，最新数据源)
    market_intel_industries = (latest_advice or {}).get("market_intel", {}).get("industries", []) if latest_advice else []
    if not matrix and market_intel_industries:
        matrix = market_intel_industries

    if matrix:
        # v3 新数据源：直接使用 advice 中的矩阵，注入 positions_detail
        matrix_list = list(matrix)

        # 构建 prescription code → rx_item 映射，用于注入 positions_detail
        prescriptions = (latest_advice or {}).get("prescription", []) if latest_advice else []
        code_to_rx: Dict[str, Dict[str, Any]] = {rx["code"]: rx for rx in prescriptions if rx.get("code")}

        for row in matrix_list:
            codes = row.get("codes", []) or []
            row["positions_detail"] = [code_to_rx[c] for c in codes if c in code_to_rx]

        total = len(matrix_list)
        covered = sum(1 for r in matrix_list if r.get("coverage_status", r.get("go_nogo", "")) in ("covered", "Go", "GO"))
        stale = sum(1 for r in matrix_list if r.get("coverage_status") == "stale")
        never = sum(1 for r in matrix_list if r.get("coverage_status") == "never")

        return ok({
            "matrix": matrix_list,
            "total_industries": total,
            "covered_count": covered,
            "stale_count": stale,
            "never_count": never,
            "latest_advice_at": latest_advice.get("created_at", "") if latest_advice else "",
            "data_score": latest_advice.get("data_score", 0) if latest_advice else 0,
            "total_assets": round(total_assets, 0) if total_assets else 0,
        })

    # 降级：使用 industry_classification_cache 做 code→bucket 映射
    from app.services.industry_buckets import BUCKETS
    portfolio_summary = pf_summary
    positions = portfolio_summary.get("positions", [])

    # 从 cache 建立 code→bucket 映射，cache 无则归入"未分类"
    cache_docs = await db["industry_classification_cache"].find({}).to_list(None)
    code_to_bucket = {c["code"]: c["bucket"] for c in cache_docs if c.get("code") and c.get("bucket")}

    industry_positions: Dict[str, List[Dict[str, Any]]] = {}
    for p in positions:
        ind = code_to_bucket.get(p.get("code", ""), "") or "未分类"
        industry_positions.setdefault(ind, []).append(p)

    # 从 industry_coverage 读取覆盖数据，只保留合法 BUCKETS 名称
    valid_buckets = set(BUCKETS.keys())
    coverage_docs = await db["industry_coverage"].find(
        {"user_id": user_id}
    ).sort("analyzed_at", -1).to_list(None)
    coverage_map: Dict[str, Dict[str, Any]] = {}
    for doc in coverage_docs:
        l1_name = doc.get("industry_name", "")
        if l1_name and l1_name in valid_buckets and l1_name not in coverage_map:
            coverage_map[l1_name] = doc

    latest_prescriptions = latest_advice.get("prescription", []) if latest_advice else []

    # 构建矩阵
    all_industries = set(list(industry_positions.keys()) + list(coverage_map.keys()))
    matrix_list = []
    from datetime import datetime, timezone

    for ind_name in sorted(all_industries):
        pos_list = industry_positions.get(ind_name, [])
        cov = coverage_map.get(ind_name, {})
        total_weight = sum(p.get("weight", 0) for p in pos_list)
        position_codes = [p.get("code", "") for p in pos_list]

        if cov and cov.get("status") == "completed":
            try:
                at_dt = datetime.fromisoformat(str(cov.get("analyzed_at", "")).replace("Z", "+00:00"))
                if at_dt.tzinfo is None:
                    at_dt = at_dt.replace(tzinfo=timezone.utc)
                days_ago = (datetime.now(timezone.utc) - at_dt).days
                coverage_status = "stale" if days_ago > 30 else "covered"
            except Exception:
                coverage_status = "covered"
        else:
            coverage_status = "never"

        target_weight = 0.0
        for rx in latest_prescriptions:
            if rx.get("code") in position_codes:
                target_weight += rx.get("target_weight", 0)

        matrix_list.append({
            "industry": ind_name,
            "market": cov.get("market", "cn"),
            "lifecycle": cov.get("lifecycle", ""),
            "go_nogo": cov.get("go_nogo", ""),
            "confidence": cov.get("confidence", ""),
            "coverage_status": coverage_status,
            "holdings_weight": round(total_weight, 2),
            "target_weight": round(target_weight, 2),
            "delta": round(target_weight - total_weight, 2),
            "position_count": len(pos_list),
            "position_codes": position_codes,
            "position_names": [p.get("name", p.get("code", "")) for p in pos_list],
            "reasoning": cov.get("reasoning", ""),
        })

    # 现金行
    cash_weight = portfolio_summary.get("available_cash", 0) / max(portfolio_summary.get("total_assets", 1), 1) * 100
    cash_rx = next((rx for rx in latest_prescriptions if rx.get("code") == "CASH"), None)
    matrix_list.append({
        "industry": "现金",
        "market": "",
        "lifecycle": "",
        "go_nogo": "",
        "confidence": "",
        "coverage_status": "covered",
        "holdings_weight": round(cash_weight, 2),
        "target_weight": round(cash_rx.get("target_weight", cash_weight) if cash_rx else cash_weight, 2),
        "delta": round((cash_rx.get("target_weight", cash_weight) if cash_rx else cash_weight) - cash_weight, 2),
        "position_count": 0,
        "position_codes": [],
        "position_names": [],
        "reasoning": cash_rx.get("reasoning", "") if cash_rx else "",
    })

    return ok({
        "matrix": matrix_list,
        "total_industries": len(matrix_list),
        "covered_count": sum(1 for r in matrix_list if r["coverage_status"] == "covered"),
        "stale_count": sum(1 for r in matrix_list if r["coverage_status"] == "stale"),
        "never_count": sum(1 for r in matrix_list if r["coverage_status"] == "never"),
        "latest_advice_at": latest_advice.get("created_at", "") if latest_advice else "",
        "data_score": 0,
        "total_assets": round(total_assets, 0) if total_assets else 0,
    })


# ── Other endpoints ─────────────────────────────────────────

@router.get("/orders", response_model=dict)
async def list_orders(limit: int = Query(50, ge=1, le=200),
                      current_user: dict = Depends(get_current_user)):
    db = get_mongo_db()
    cursor = db["paper_orders"].find({"user_id": current_user["id"]}).sort("created_at", -1).limit(limit)
    items = await cursor.to_list(None)
    cleaned = [{k: v for k, v in it.items() if k != "_id"} for it in items]
    return ok({"items": cleaned})


@router.post("/reset", response_model=dict)
async def reset_account(confirm: bool = Query(False),
                        current_user: dict = Depends(get_current_user)):
    """重置账户"""
    if not confirm:
        raise HTTPException(status_code=400, detail="请设置 confirm=true 以确认重置")
    db = get_mongo_db()
    await db["paper_accounts"].delete_many({"user_id": current_user["id"]})
    await db["paper_positions"].delete_many({"user_id": current_user["id"]})
    await db["paper_orders"].delete_many({"user_id": current_user["id"]})
    await db["paper_trades"].delete_many({"user_id": current_user["id"]})
    acc = await _get_or_create_account(current_user["id"])
    return ok({"message": "账户已重置"})


# ── Portfolio Advice endpoints ─────────────────────────────

@router.post("/advice", response_model=dict)
async def generate_advice(current_user: dict = Depends(get_current_user)):
    """触发组合顾问分析"""
    db = get_mongo_db()

    positions = await db["paper_positions"].find({"user_id": current_user["id"]}).to_list(None)
    if not positions:
        raise HTTPException(status_code=400, detail="无持仓，无法生成组合建议")

    existing = await db["portfolio_advice"].find_one(
        {"user_id": current_user["id"], "status": {"$in": ["GENERATING", "RUNNING"]}},
    )
    if existing:
        raise HTTPException(status_code=409, detail="已有正在生成的建议，请等待完成")

    advice_id = str(uuid.uuid4())
    now_iso = datetime.utcnow().isoformat()
    await db["portfolio_advice"].insert_one({
        "advice_id": advice_id,
        "user_id": current_user["id"],
        "status": "GENERATING",
        "current_step": "准备数据",
        "created_at": now_iso,
        "updated_at": now_iso,
    })

    from app.services.portfolio_advisor_service import PortfolioAdvisorService
    advisor_svc = PortfolioAdvisorService()
    await advisor_svc.generate_advice(current_user["id"], advice_id)

    return ok({"advice_id": advice_id, "status": "GENERATING"})


@router.get("/advice/latest", response_model=dict)
async def get_latest_advice(current_user: dict = Depends(get_current_user)):
    """获取最新的组合建议"""
    db = get_mongo_db()
    doc = await db["portfolio_advice"].find_one(
        {"user_id": current_user["id"]},
        sort=[("created_at", -1)],
    )
    if not doc:
        raise HTTPException(status_code=404, detail="暂无组合建议")
    return ok(_clean_advice(doc))


@router.get("/advice/{advice_id}", response_model=dict)
async def get_advice(advice_id: str, current_user: dict = Depends(get_current_user)):
    """获取指定组合建议"""
    db = get_mongo_db()
    doc = await db["portfolio_advice"].find_one({"advice_id": advice_id})
    if not doc:
        raise HTTPException(status_code=404, detail="建议不存在")
    if doc.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="无权访问")
    return ok(_clean_advice(doc))


@router.get("/advice", response_model=dict)
async def list_advice(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
):
    """分页获取历史组合建议"""
    db = get_mongo_db()
    skip = (page - 1) * page_size
    cursor = (
        db["portfolio_advice"]
        .find({"user_id": current_user["id"]})
        .sort("created_at", -1)
        .skip(skip)
        .limit(page_size)
    )
    items = await cursor.to_list(None)
    total = await db["portfolio_advice"].count_documents({"user_id": current_user["id"]})
    return ok({
        "items": [_clean_advice(d) for d in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


def _clean_advice(doc: Dict[str, Any]) -> Dict[str, Any]:
    """清理 MongoDB 文档为 JSON 可序列化格式"""
    return {k: v for k, v in doc.items() if k != "_id"}
