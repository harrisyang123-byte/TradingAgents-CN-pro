"""行业分类工具：LLM 驱动 + MongoDB 缓存 + 关键词回退

新增 classify_by_akshare：持仓录入时用 AKShare 股票基本信息优先分类，
消除 /overview 接口的运行时 LLM 分类开销。
"""

from typing import Dict, List, Any, Optional
import asyncio
import logging

logger = logging.getLogger(__name__)


async def classify_by_akshare(code: str, name: str = "", instrument_type: str = "stock") -> str:
    """持仓录入时的行业分类。

    策略（按优先级）：
      1. fund/etf/other 类型：直接用名称关键词匹配（name 为空时先查 FundService）
      2. A股股票：AKShare stock_individual_info_em 的「行业」字段
      3. _fallback_classify 关键词匹配（港股/美股/fallback）
      4. 返回「未分类」（不阻断录入）

    Returns:
        18大行业 bucket 名称，失败时返回「未分类」
    """
    from app.services.industry_buckets import _match_bucket, _fallback_classify

    # fund/etf/other：跳过 AKShare 股票接口，直接用名称关键词
    if instrument_type in ("fund", "etf", "other", "bond"):
        effective_name = name
        if not effective_name:
            # name 为空时先查 FundService 获取名称
            try:
                from app.services.fund_service import FundService
                svc = FundService()
                info = await svc.get_basic_info(code)
                if info and info.get("name"):
                    effective_name = info["name"]
            except Exception as e:
                logger.debug(f"FundService 查名称失败 {code}: {e}")
        if effective_name:
            bucket = _fallback_classify(code, effective_name, instrument_type)
            if bucket != "其他":
                return bucket
        return "未分类"

    # A股：用 AKShare 获取申万行业，再映射到 18-bucket
    if _is_a_share(code):
        try:
            import akshare as ak
            # AKShare 需要 6 位纯数字代码
            clean_code = code.replace("SH", "").replace("SZ", "").strip()
            df = await asyncio.to_thread(ak.stock_individual_info_em, symbol=clean_code)
            if df is not None and not df.empty:
                # AKShare stock_individual_info_em 字段名为「行业」（非「所属行业」）
                industry_row = df[df["item"].isin(["行业", "所属行业"])]
                if not industry_row.empty:
                    raw_industry = str(industry_row["value"].iloc[0]).strip()
                    # 去除申万子分类后缀（如「白酒Ⅱ」→「白酒」）
                    import re
                    raw_industry = re.sub(r'[ⅠⅡⅢIiⅣⅤ]+$', '', raw_industry).strip()
                    # 尝试直接映射到 bucket
                    bucket = _match_bucket(raw_industry)
                    if bucket:
                        return bucket
                    # 映射失败：用关键词 fallback（传入原始行业名作为 name 辅助）
                    bucket = _fallback_classify(code, raw_industry or name, instrument_type)
                    return bucket if bucket != "其他" else "未分类"
        except Exception as e:
            logger.debug(f"AKShare 行业分类失败 {code}: {e}")

    # 非A股 或 AKShare 失败：关键词 fallback
    if name:
        bucket = _fallback_classify(code, name, instrument_type)
        if bucket != "其他":
            return bucket

    return "未分类"


def _is_a_share(code: str) -> bool:
    """判断是否为A股代码（6位数字）"""
    clean = code.replace("SH", "").replace("SZ", "").replace(".", "").strip()
    return clean.isdigit() and len(clean) == 6


async def classify_holdings_industries(
    db,
    positions: List[Dict[str, Any]],
    llm=None,
) -> Dict[str, List[Dict[str, Any]]]:
    """从持仓列表反推行业归属。

    策略：
      1. LLM 批量分类（基于公司名+基金名直接判断业务，最准）
      2. Cache 到 MongoDB industry_classification_cache
      3. LLM 不可用时回退到关键词

    Returns:
        {bucket_name: [position_obj, ...]}
    """
    from app.services.industry_buckets import classify_batch_with_llm

    # 标注 market 字段（港股代码含 .HK 或无后缀纯数字但非 A 股开头）
    for p in positions:
        if not p.get("market"):
            code = p.get("code", "")
            if ".HK" in code or ".hk" in code:
                p["market"] = "港股"
            elif code.isdigit() and len(code) == 5:
                p["market"] = "港股"
            elif code.isdigit() and len(code) == 6:
                p["market"] = "A股"
            elif code.isalpha() and len(code) <= 5:
                p["market"] = "美股"

    code_to_bucket = await classify_batch_with_llm(
        positions, llm=llm, db=db
    )

    bucket_map: Dict[str, List[Dict[str, Any]]] = {}
    for p in positions:
        code = p.get("code", "")
        bucket = code_to_bucket.get(code, "其他")
        bucket_map.setdefault(bucket, []).append(p)

    return bucket_map
