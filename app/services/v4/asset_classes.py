"""asset_classes.py — v4 七大类资产体系常量（AC1.3 / AC4.3）

单一真源：七大类 class 枚举、最深下钻层级、分档 TTL。
前端常量（frontend/src/views/Portfolio/v4/assetClasses.ts）须与此保持一致。

下钻层级语义（max_drill_depth）：
  - "industry_stock"   能完整走 大类→行业→个股 三层（仅权益）
  - "instrument"       下钻到品种/工具层（可交易：ETF/REITs/债基/相关股）
  - "holding_structure" 仅持有结构建议（现金等纯持有型）
"""

from __future__ import annotations

from typing import Dict, List, Optional

# ── 七大类资产（固定枚举） ──────────────────────────────────────────────
EQUITY = "equity"
FIXED_INCOME = "fixed_income"
CASH = "cash"
COMMODITY = "commodity"
PRECIOUS_METAL = "precious_metal"
REAL_ESTATE = "real_estate"
ALTERNATIVE = "alternative"

# 无法归类桶（AC1.1：不丢弃，标「待人工归类」）
UNCLASSIFIED = "unclassified"

# 下钻层级常量
DRILL_INDUSTRY_STOCK = "industry_stock"
DRILL_INSTRUMENT = "instrument"
DRILL_HOLDING_STRUCTURE = "holding_structure"

# ── 分档 TTL（天，可配置，AC4.3） ──────────────────────────────────────
# 通过环境变量覆盖：V4_TTL_ASSET / V4_TTL_INDUSTRY / V4_TTL_STOCK / V4_TTL_ALLOC
import os


def _ttl(env_key: str, default: int) -> int:
    try:
        v = int(os.getenv(env_key, "").strip() or default)
        return v if v > 0 else default
    except (ValueError, TypeError):
        return default


TTL_DAYS = {
    "asset": _ttl("V4_TTL_ASSET", 14),        # 大类分析：半月级
    "plan": _ttl("V4_TTL_ASSET", 14),         # 非权益方案随大类档
    "alloc": _ttl("V4_TTL_ALLOC", 7),         # 配比：周级
    "industry": _ttl("V4_TTL_INDUSTRY", 7),   # 行业深辩：周级
    "stock": _ttl("V4_TTL_STOCK", 5),         # 个股：更短
}


# ── 七大类配置表（AC1.3） ──────────────────────────────────────────────
ASSET_CLASSES: List[Dict] = [
    {
        "key": EQUITY,
        "label_zh": "权益",
        "examples": "公司股票（A股、港股、美股）、股票型基金、ETF",
        "max_drill_depth": DRILL_INDUSTRY_STOCK,
        "ttl_days": TTL_DAYS["asset"],
        "order": 1,
    },
    {
        "key": FIXED_INCOME,
        "label_zh": "固定收益",
        "examples": "国债、地方政府债、企业债、可转债、债券基金",
        "max_drill_depth": DRILL_INSTRUMENT,
        "ttl_days": TTL_DAYS["asset"],
        "order": 2,
    },
    {
        "key": CASH,
        "label_zh": "现金及等价物",
        "examples": "活期存款、货币基金、短期国债、逆回购（各国货币）",
        "max_drill_depth": DRILL_HOLDING_STRUCTURE,
        "ttl_days": TTL_DAYS["asset"],
        "order": 3,
    },
    {
        "key": COMMODITY,
        "label_zh": "大宗商品",
        "examples": "能源（原油、天然气）、工业金属（铜、铝）、农产品",
        "max_drill_depth": DRILL_INSTRUMENT,
        "ttl_days": TTL_DAYS["asset"],
        "order": 4,
    },
    {
        "key": PRECIOUS_METAL,
        "label_zh": "贵金属",
        "examples": "黄金、白银、铂金（独立于大宗商品）",
        "max_drill_depth": DRILL_INSTRUMENT,
        "ttl_days": TTL_DAYS["asset"],
        "order": 5,
    },
    {
        "key": REAL_ESTATE,
        "label_zh": "房地产",
        "examples": "REITs、实物房产、房地产私募基金",
        "max_drill_depth": DRILL_INSTRUMENT,
        "ttl_days": TTL_DAYS["asset"],
        "order": 6,
    },
    {
        "key": ALTERNATIVE,
        "label_zh": "另类投资",
        "examples": "虚拟币（比特币、以太坊）等",
        "max_drill_depth": DRILL_INSTRUMENT,
        "ttl_days": TTL_DAYS["asset"],
        "order": 7,
    },
]

# 快速索引
CLASS_KEYS: List[str] = [c["key"] for c in ASSET_CLASSES]
_CLASS_BY_KEY: Dict[str, Dict] = {c["key"]: c for c in ASSET_CLASSES}

# 非权益六类（用于 plan:<class>）
NON_EQUITY_KEYS: List[str] = [k for k in CLASS_KEYS if k != EQUITY]


def get_class(key: str) -> Optional[Dict]:
    """按 key 取大类配置；未知返回 None。"""
    return _CLASS_BY_KEY.get(key)


def is_valid_class(key: str) -> bool:
    return key in _CLASS_BY_KEY


def label_of(key: str) -> str:
    c = _CLASS_BY_KEY.get(key)
    if c:
        return c["label_zh"]
    if key == UNCLASSIFIED:
        return "待人工归类"
    return key


def is_equity(key: str) -> bool:
    return key == EQUITY


def max_drill_depth(key: str) -> str:
    c = _CLASS_BY_KEY.get(key)
    return c["max_drill_depth"] if c else DRILL_HOLDING_STRUCTURE


def ttl_for_unit_type(unit_type: str) -> int:
    """按单元类型返回 TTL 天数。"""
    return TTL_DAYS.get(unit_type, 7)
