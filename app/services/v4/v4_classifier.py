"""v4_classifier.py — 持仓七大类穿透归类（FR-001）

把任意持仓（A股/港股/美股个股、各类基金/ETF、债、现金、商品、REITs、虚拟币）
归入七大类资产体系。无法判定的入 `unclassified` 桶并标「待人工归类」，不丢弃（AC1.1）。

区分（AC1.2）：
  - tradable        有市场代码、可下钻到标的（个股/ETF/REITs/债基/货基…）
  - holding_only    纯持有型敞口（实物房产、实物金条、活期存款/各国现金），只记敞口不荐标的

入口同时支持 Mongo 持仓与 --portfolio-file（AC1.4）：本模块只接收已加载的 positions 列表，
由 collect_v4.py 决定数据来源。纯 stdlib + 关键词，可独立测试；A股可选 AKShare 增强（非必需）。
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.services.v4 import asset_classes as ac

# ── 关键词规则（按优先级从特殊到一般） ────────────────────────────────
# 每条：(类别, [关键词...])。先匹配到的胜出。
_KEYWORD_RULES = [
    (ac.PRECIOUS_METAL, ["黄金", "白银", "铂金", "钯金", "贵金属", "上海金", "沪金", "金etf", "金交所", "gold", "silver", "au(t+d)", "ag(t+d)", "au99"]),
    (ac.ALTERNATIVE, ["比特币", "以太坊", "以太币", "虚拟币", "数字货币", "加密", "bitcoin", "ethereum", "btc", "eth", "crypto"]),
    (ac.REAL_ESTATE, ["reit", "reits", "房地产", "不动产", "地产", "物流仓储", "产业园", "保障房", "实物房产", "房产"]),
    (ac.COMMODITY, ["原油", "天然气", "能源化工", "工业金属", "有色", "铜", "铝", "螺纹", "焦煤", "焦炭", "农产品", "大豆", "玉米", "豆粕", "白糖", "棉花", "商品期货", "南华商品"]),
    (ac.FIXED_INCOME, ["国债", "政金债", "地方债", "政府债", "企业债", "信用债", "可转债", "转债", "债券", "债基", "纯债", "中长期债", "短债", "利率债", "城投", "国开债", "收益债", "回报债", "添利债", "中债", "债a", "债b", "债c", "债指数"]),
    (ac.CASH, ["货币基金", "货币市场", "货基", "现金", "活期", "存款", "逆回购", "同业存单", "理财", "宝"]),
]

# 多资产/投顾组合：无法穿透到单一大类，标待人工归类（AC1.1，不静默丢入权益）
_MIXED_ASSET_HINTS = ["投顾组合", "多元配置", "多元稳健", "多资产", "全球多元", "fof", "资产配置组合", "稳健配置组合"]

# 现金/持有型强信号（用于 tradable vs holding_only）
_HOLDING_ONLY_HINTS = ["实物", "活期", "存款", "现金", "房产", "金条", "金币"]


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def _match_keyword(name: str) -> str:
    n = _norm(name)
    if not n:
        return ""
    for klass, kws in _KEYWORD_RULES:
        for kw in kws:
            if kw.lower() in n:
                return klass
    return ""


def _is_a_share(code: str) -> bool:
    clean = (code or "").replace("SH", "").replace("SZ", "").replace(".", "").strip()
    return clean.isdigit() and len(clean) == 6


def _looks_like_stock(code: str, instrument_type: str) -> bool:
    if instrument_type in ("stock",):
        return True
    c = (code or "").strip()
    # A股6位 / 港股5位数字 / 美股字母代码
    if c.isdigit() and len(c) in (5, 6):
        return True
    if c.replace(".", "").isalpha() and 1 <= len(c.replace(".HK", "").replace(".US", "")) <= 5:
        return True
    return False


def classify_position(pos: Dict[str, Any]) -> Dict[str, Any]:
    """对单条持仓判定大类 + tradable/holding_only。"""
    code = str(pos.get("code", "") or "")
    name = str(pos.get("name", "") or "")
    itype = _norm(pos.get("instrument_type", "") or "")
    text = f"{name} {code}"

    # 1. 名称/代码关键词
    klass = _match_keyword(text)

    # 1.5 多资产/投顾组合 → 待人工归类（无法穿透到单一大类，不静默丢入权益，AC1.1）
    if not klass:
        n_lower = _norm(text)
        if any(h in n_lower for h in _MIXED_ASSET_HINTS):
            klass = ac.UNCLASSIFIED

    # 2. instrument_type 兜底
    if not klass:
        if itype == "bond":
            klass = ac.FIXED_INCOME
        elif itype == "cash":
            klass = ac.CASH
        elif itype in ("stock", "etf"):
            klass = ac.EQUITY
        elif itype == "fund":
            # 普通基金：默认权益（股票型/混合），除非名称命中其它类
            klass = ac.EQUITY
        elif _looks_like_stock(code, itype):
            klass = ac.EQUITY

    # 3. 仍未定 → unclassified（不丢弃）
    if not klass:
        klass = ac.UNCLASSIFIED

    # tradable vs holding_only
    holding_only = False
    n = _norm(name)
    if any(h in n for h in _HOLDING_ONLY_HINTS):
        # 但货币基金/债基这类有代码的仍是 tradable；只有真正实物/活期存款是 holding_only
        if klass == ac.CASH and ("货币基金" in name or "货基" in name or "逆回购" in name or "存单" in name):
            holding_only = False
        elif klass == ac.REAL_ESTATE and ("reit" in n):
            holding_only = False
        else:
            holding_only = True
    # 无市场代码的现金/房产/贵金属敞口视为 holding_only
    if not code and klass in (ac.CASH, ac.REAL_ESTATE, ac.PRECIOUS_METAL, ac.COMMODITY):
        holding_only = True

    return {
        "code": code,
        "name": name,
        "asset_class": klass,
        "tradable": not holding_only,
        "weight": float(pos.get("weight", 0) or 0),
        "market_value": float(pos.get("market_value", 0) or 0),
        "instrument_type": itype or "unknown",
    }


def classify_holdings(positions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """对整组持仓归类，按七大类（+unclassified）聚合。

    返回：
      {
        "by_class": {<class>: {"label","weight","market_value",
                                "tradable":[...], "holding_only_exposure":float,
                                "holdings":[...]}},
        "unclassified": [...]（待人工归类，AC1.1）,
        "total_market_value": float, "position_count": int
      }
    """
    by_class: Dict[str, Dict[str, Any]] = {}
    total_mv = 0.0
    for key in ac.CLASS_KEYS + [ac.UNCLASSIFIED]:
        by_class[key] = {
            "asset_class": key,
            "label": ac.label_of(key),
            "weight": 0.0,
            "market_value": 0.0,
            "tradable": [],
            "holding_only_exposure": 0.0,
            "holdings": [],
        }

    for pos in positions or []:
        c = classify_position(pos)
        klass = c["asset_class"]
        bucket = by_class[klass]
        bucket["weight"] += c["weight"]
        bucket["market_value"] += c["market_value"]
        bucket["holdings"].append(c)
        if c["tradable"]:
            bucket["tradable"].append({"code": c["code"], "name": c["name"], "weight": c["weight"]})
        else:
            bucket["holding_only_exposure"] += c["market_value"] or c["weight"]
        total_mv += c["market_value"]

    # 四舍五入
    for b in by_class.values():
        b["weight"] = round(b["weight"], 2)
        b["market_value"] = round(b["market_value"], 2)
        b["holding_only_exposure"] = round(b["holding_only_exposure"], 2)

    return {
        "by_class": by_class,
        "unclassified": by_class[ac.UNCLASSIFIED]["holdings"],
        "total_market_value": round(total_mv, 2),
        "position_count": len(positions or []),
    }
