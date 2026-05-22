"""基金详情 API 路由"""

from fastapi import APIRouter, Depends, HTTPException
import logging

from app.routers.auth_db import get_current_user
from app.core.response import ok, fail
from app.services.fund_service import FundService

router = APIRouter(prefix="/fund", tags=["fund"])
logger = logging.getLogger("webapi")

_fund_service: FundService = None


def _get_fund_service() -> FundService:
    global _fund_service
    if _fund_service is None:
        _fund_service = FundService()
    return _fund_service


@router.get("/basic-info")
async def get_basic_info(
    code: str,
    current_user: dict = Depends(get_current_user),
    svc: FundService = Depends(_get_fund_service),
):
    """获取基金基础信息：名称、类型、规模、成立日期、基金经理"""
    if not code or not code.strip():
        raise HTTPException(status_code=400, detail="基金代码不能为空")

    data = await svc.get_basic_info(code.strip())
    if data is None:
        raise HTTPException(status_code=404, detail="基金不存在或数据获取失败")

    return ok(data)


@router.get("/top-holdings")
async def get_top_holdings(
    code: str,
    current_user: dict = Depends(get_current_user),
    svc: FundService = Depends(_get_fund_service),
):
    """获取基金前十大重仓股"""
    if not code or not code.strip():
        raise HTTPException(status_code=400, detail="基金代码不能为空")

    data = await svc.get_top_holdings(code.strip())
    if data is None:
        raise HTTPException(status_code=504, detail="数据获取超时，请稍后重试")

    return ok(data)


@router.get("/nav-history")
async def get_nav_history(
    code: str,
    period: str = "1年",
    current_user: dict = Depends(get_current_user),
    svc: FundService = Depends(_get_fund_service),
):
    """获取基金净值历史走势，period: 1月/3月/6月/1年/3年/成立来"""
    if not code or not code.strip():
        raise HTTPException(status_code=400, detail="基金代码不能为空")

    data = await svc.get_nav_history(code.strip(), period)
    if data is None:
        raise HTTPException(status_code=504, detail="数据获取超时，请稍后重试")

    return ok(data)


@router.get("/sector-distribution")
async def get_sector_distribution(
    code: str,
    current_user: dict = Depends(get_current_user),
    svc: FundService = Depends(_get_fund_service),
):
    """获取基金行业分布"""
    if not code or not code.strip():
        raise HTTPException(status_code=400, detail="基金代码不能为空")

    data = await svc.get_sector_distribution(code.strip())
    if data is None:
        raise HTTPException(status_code=504, detail="数据获取超时，请稍后重试")

    return ok(data)
