"""行业分类工具：LLM 驱动 + MongoDB 缓存 + 关键词回退"""

from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


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
