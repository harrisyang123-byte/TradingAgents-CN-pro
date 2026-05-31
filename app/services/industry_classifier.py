"""行业分类工具：从持仓列表反推行业归属（统一 Bucket 映射）"""

from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


async def classify_holdings_industries(
    db,
    positions: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    """
    从持仓列表反推行业归属，使用统一 15 bucket 分类。

    优先级:
      1. stock_basic_info.industry（A 股 Tushare）
      2. stock_basic_info_hk.sector/industry（HK/US yfinance 缓存）
      3. 基金名称关键词 → bucket
      4. 知名公司硬编码映射
      5. "其他"

    Returns:
        {bucket_name: [position_obj, ...], ...}
    """
    from app.services.industry_buckets import classify as bucket_classify

    # ── 收集所有 A 股代码，批量查 stock_basic_info ──
    cn_codes = [
        p["code"] for p in positions
        if p.get("market") in ("A股", "cn") and p.get("instrument_type") not in ("fund", "etf")
    ]
    cn_info: Dict[str, Dict[str, Any]] = {}
    if cn_codes:
        cursor = db["stock_basic_info"].find(
            {"code": {"$in": cn_codes}},
            {"code": 1, "industry": 1, "name": 1},
        )
        async for doc in cursor:
            cn_info[doc["code"]] = doc

    # ── 收集所有 HK/US 代码，批量查 stock_basic_info_hk ──
    hk_us_codes = [
        p["code"] for p in positions
        if p.get("market") in ("港股", "hk", "美股", "us") and p.get("instrument_type") not in ("fund", "etf")
    ]
    hk_info: Dict[str, Dict[str, Any]] = {}
    if hk_us_codes:
        cursor = db["stock_basic_info_hk"].find(
            {"code": {"$in": hk_us_codes}},
            {"code": 1, "sector": 1, "industry": 1, "name": 1},
        )
        async for doc in cursor:
            hk_info[doc["code"]] = doc

    # ── 对未缓存的 HK/US 代码，尝试 yfinance 查询并缓存 ──
    uncached_hk = [c for c in hk_us_codes if c not in hk_info]
    if uncached_hk:
        new_entries = await _fetch_hk_us_industries(uncached_hk)
        for entry in new_entries:
            code = entry["code"]
            hk_info[code] = entry
            try:
                await db["stock_basic_info_hk"].update_one(
                    {"code": code},
                    {"$set": {**entry, "cached_at": __import__("datetime").datetime.utcnow()}},
                    upsert=True,
                )
            except Exception:
                pass

    # ── 逐只分类 ──
    bucket_map: Dict[str, List[Dict[str, Any]]] = {}
    for p in positions:
        code = p.get("code", "")
        instr_type = p.get("instrument_type", "stock")
        name = p.get("name", "")
        market = p.get("market", "")

        # 收集行业来源
        sw_industry = ""
        gics_industry = ""
        gics_sector = ""

        if code in cn_info:
            sw_industry = cn_info[code].get("industry", "") or ""
        elif code in hk_info:
            gics_industry = hk_info[code].get("industry", "") or ""
            gics_sector = hk_info[code].get("sector", "") or ""

        bucket = bucket_classify(
            code=code,
            name=name,
            instrument_type=instr_type,
            sw_industry=sw_industry,
            gics_industry=gics_industry,
            gics_sector=gics_sector,
        )

        bucket_map.setdefault(bucket, []).append(p)

    return bucket_map


async def _fetch_hk_us_industries(codes: List[str]) -> List[Dict[str, Any]]:
    """通过 yfinance 批量获取 HK/US 股票的 industry/sector。"""
    results = []
    try:
        import yfinance as yf
        import re
    except ImportError:
        logger.warning("yfinance 不可用，跳过 HK/US 行业查询")
        return results

    for code in codes:
        try:
            # 规范化 yfinance ticker
            ticker = code
            clean = re.sub(r'\.(HK|hk)$', '', code).lstrip('0') or '0'
            if re.match(r'^\d{4,5}$', clean):
                ticker = f"{clean}.HK"
            elif not re.search(r'[A-Z]{2,5}', code):
                # 纯数字 → 港股
                ticker = f"{code.lstrip('0')}.HK"

            tk = yf.Ticker(ticker)
            info = tk.info or {}
            sector = info.get("sector", "")
            industry = info.get("industry", "")
            if sector or industry:
                results.append({
                    "code": code,
                    "sector": sector,
                    "industry": industry,
                    "name": info.get("longName") or info.get("shortName", ""),
                    "source": "yfinance",
                })
            else:
                results.append({
                    "code": code,
                    "sector": "",
                    "industry": "",
                    "name": "",
                    "source": "yfinance_empty",
                })
        except Exception as e:
            logger.warning(f"yfinance 查询失败 {code}: {e}")
            results.append({"code": code, "sector": "", "industry": "", "name": "", "source": "error"})

    return results
