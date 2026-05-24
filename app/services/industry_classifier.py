"""行业分类工具：从持仓列表反推行业归属"""

from typing import Dict, List, Any


def _infer_fund_industry(name: str) -> str:
    """从基金/ETF 名称关键词推断行业"""
    if not name:
        return ""
    kw_map = {
        "纳指": "海外科技", "纳斯达克": "海外科技", "标普": "海外科技",
        "科创": "科创板", "创业板": "创业板",
        "中证500": "中盘宽基", "沪深300": "大盘宽基", "上证50": "大盘宽基",
        "债": "债券", "债券": "债券", "纯债": "债券", "信用债": "债券",
        "黄金": "黄金", "原油": "能源",
        "医药": "医药健康", "医疗": "医药健康", "生物": "医药健康",
        "消费": "消费", "食品": "消费",
        "半导体": "半导体", "芯片": "半导体",
        "军工": "军工", "国防": "军工",
        "新能源": "新能源", "光伏": "新能源", "电池": "新能源",
        "券商": "金融", "银行": "金融", "保险": "金融",
        "恒生": "港股", "港股": "港股",
        "人工智能": "AI", "AI": "AI", "科技": "科技",
        "汽车": "汽车", "智能车": "汽车",
        "红利": "红利", "高股息": "红利",
    }
    for kw, industry in kw_map.items():
        if kw in name:
            return industry
    return ""


async def classify_holdings_industries(
    db,
    positions: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    """
    从持仓列表反推行业归属。

    Returns:
        {industry_name: [position_obj, ...], ...}
        分类优先级：stock_basic_info.industry > 名称关键词推断 > "其他"
    """
    stock_codes = [
        p["code"] for p in positions
        if p.get("instrument_type") in ("stock", "etf", None)
    ]
    stock_info_map: Dict[str, Dict[str, Any]] = {}
    if stock_codes:
        cursor = db["stock_basic_info"].find(
            {"code": {"$in": stock_codes}},
            {"code": 1, "industry": 1, "sector": 1},
        )
        async for doc in cursor:
            stock_info_map[doc["code"]] = doc

    industry_map: Dict[str, List[Dict[str, Any]]] = {}
    for p in positions:
        code = p.get("code", "")
        instr_type = p.get("instrument_type", "stock")
        name = p.get("name", "")

        ind = ""
        if code in stock_info_map:
            ind = stock_info_map[code].get("industry") or stock_info_map[code].get("sector") or ""
        if not ind and instr_type in ("fund", "etf"):
            ind = _infer_fund_industry(name)
        if not ind:
            ind = "其他"

        industry_map.setdefault(ind, []).append(p)

    return industry_map
