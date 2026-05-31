"""统一行业 Bucket 映射 — LLM 驱动的投资主题分类

分类原则：按公司实际业务分类，而非按数据源标签。
消费 ≠ 互联网，宽基 ≠ 行业基金，每个 bucket 对应一组可独立决策的投资方向。

18 个投资主题：
  消费（必选）- 食品饮料、白酒、调味品、日用品、农业
  消费（可选）- 家电、汽车、奢侈品、旅游、纺织服装
  互联网/平台 - 社交、游戏、电商、短视频、搜索、云计算
  半导体 - 芯片设计、制造、封测、设备
  人工智能/软件 - AI应用、SaaS、IT服务
  新能源（发电）- 光伏、风电、储能、锂电、电力设备
  新能源车 - 整车、电池、热管理、零部件
  通信/5G - 通信设备、光模块、运营商
  金融/保险 - 银行、券商、保险
  医药健康 - 制药、器械、CXO、医美
  高端制造 - 机器人、军工、航空航天、工业自动化
  化工/材料 - 化工品、新材料、稀土、有色
  基建/地产 - 建筑、建材、房地产
  能源/公用 - 电力、煤炭、油气、水务
  债券/固收 - 利率债、信用债、货基
  宽基指数 - 沪深300、中证500、A500、创业板 ETF
  全球配置 - QDII、海外宽基、黄金
  现金 - 可用现金、逆回购
"""

from typing import Dict, List, Optional
import json
import logging

logger = logging.getLogger(__name__)

BUCKETS = {
    "消费（必选）": "食品饮料、白酒、调味品、日用品、农业",
    "消费（可选）": "家电、汽车、奢侈品、旅游、纺织服装",
    "互联网/平台": "社交、游戏、电商、短视频、搜索、云计算",
    "半导体": "芯片设计、制造、封测、设备",
    "人工智能/软件": "AI应用、SaaS、IT服务",
    "新能源（发电）": "光伏、风电、储能、锂电、电力设备",
    "新能源车": "整车、电池、热管理、零部件",
    "通信/5G": "通信设备、光模块、运营商",
    "金融/保险": "银行、券商、保险",
    "医药健康": "制药、器械、CXO、医美",
    "高端制造": "机器人、军工、航空航天、工业自动化",
    "化工/材料": "化工品、新材料、稀土、有色",
    "基建/地产": "建筑、建材、房地产",
    "能源/公用": "电力、煤炭、油气、水务",
    "债券/固收": "利率债、信用债、货基",
    "宽基指数": "沪深300、中证500、A500、创业板 ETF",
    "全球配置": "QDII、海外宽基、黄金",
    "现金": "可用现金、逆回购",
}


async def classify_batch_with_llm(
    positions: List[dict],
    llm=None,
    db=None,
) -> Dict[str, str]:
    """用 LLM 批量分类持仓标的。

    Args:
        positions: [{code, name, instrument_type, market, ...}]
        llm: LLM 实例
        db: MongoDB 数据库连接

    Returns:
        {code: bucket_name}
    """
    if not positions:
        return {}

    # 检查缓存
    code_to_bucket: Dict[str, str] = {}
    uncached: List[dict] = []
    if db is not None:
        codes = [p["code"] for p in positions]
        cursor = db["industry_classification_cache"].find(
            {"code": {"$in": codes}}
        )
        async for doc in cursor:
            code_to_bucket[doc["code"]] = doc.get("bucket", "")
        cached_codes = set(code_to_bucket.keys())
        uncached = [p for p in positions if p["code"] not in cached_codes]
    else:
        uncached = list(positions)

    if not uncached:
        return code_to_bucket

    # 分批：超过 18 只时分批，每批最多 15 只（含余量）
    BATCH_SIZE = 18
    from langchain_core.messages import HumanMessage
    import re

    for batch_start in range(0, len(uncached), BATCH_SIZE):
        batch = uncached[batch_start:batch_start + BATCH_SIZE]

        # 构建 LLM prompt
        bucket_list = "\n".join(
            f"- {name}" for name in BUCKETS.keys()
        )
        items_text = "\n".join(
            f"{i+1}. code={p.get('code','?')} name={p.get('name','?')} "
            f"type={p.get('instrument_type','stock')}"
            for i, p in enumerate(batch)
        )

        prompt = f"""分类以下 {len(batch)} 个投资标的至标准投资主题。

主题列表：
{bucket_list}

分类规则：
- 根据公司/基金的实际业务判断
- 沪深300/中证500/A500/创业板等ETF → 宽基指数
- 纳指/标普/恒生/QDII/海外/黄金 → 全球配置
- 债基/货基 → 债券/固收
- 选择最主要的一个分类

标的：
{items_text}

仅输出一个JSON，key=code，value=分类名：
```json
{{"000001": "半导体", "00700": "互联网/平台"}}
```"""

        # LLM 分类（最多重试 2 次）
        for attempt in range(2):
            try:
                if llm is None:
                    raise ValueError("LLM 不可用")

                response = llm.invoke([HumanMessage(content=prompt)])
                text = response.content if hasattr(response, "content") else str(response)

                # 优先匹配 ```json ... ``` 再匹配裸 JSON
                match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', text)
                if not match:
                    match = re.search(r'\{[\s\S]*\}', text)
                if match:
                    try:
                        result = json.loads(match.group(1) if match.lastindex else match.group(0))
                    except json.JSONDecodeError:
                        result = json.loads(match.group(0))
                    for code, raw_bucket in result.items():
                        bucket = _match_bucket(str(raw_bucket))
                        if bucket:
                            code_to_bucket[code] = bucket
                            if db is not None:
                                try:
                                    await db["industry_classification_cache"].update_one(
                                        {"code": code},
                                        {"$set": {"code": code, "bucket": bucket,
                                                  "name": next((p.get("name","") for p in batch if p["code"]==code), "")}},
                                        upsert=True,
                                    )
                                except Exception:
                                    pass
                break  # 成功则跳出重试循环
            except Exception as e:
                if attempt == 1:
                    logger.warning(f"LLM 分类失败 (batch {batch_start}): {e}")
                continue

    # 未分类的兜底
    for p in uncached:
        if p["code"] not in code_to_bucket:
            code_to_bucket[p["code"]] = _fallback_classify(
                p["code"], p.get("name", ""), p.get("instrument_type", "stock")
            )

    return code_to_bucket


def _normalize_bucket_name(name: str) -> str:
    """归一化 bucket 名：去除多余空格、统一括号、精确匹配"""
    if not name:
        return ""
    name = name.strip().replace(" ", "").replace("　", "")
    # 全角括号 → 半角
    name = name.replace("（", "(").replace("）", ")")
    # 模糊匹配回标准名
    for bk in BUCKETS:
        bk_norm = bk.replace("（", "(").replace("）", ")")
        if name == bk_norm or name == bk or name in bk or bk in name:
            return bk
    return ""


def _match_bucket(name: str) -> str:
    """宽松匹配 bucket 名"""
    cleaned = _normalize_bucket_name(name)
    if cleaned:
        return cleaned
    # 最后尝试：包含匹配
    for bk in BUCKETS:
        if any(c in name for c in [bk[:2], bk[-2:]]):
            return bk
    return ""


async def _map_l1_to_buckets_with_llm(
    l1_names: list[str], llm, db=None
) -> dict[str, str]:
    """用 LLM 把 L1 行业名映射到 18-bucket 体系。返回 {l1_name: bucket}"""
    if not l1_names or not llm:
        return {}

    # 检查缓存
    result: dict[str, str] = {}
    uncached = list(l1_names)
    if db:
        cursor = db["industry_coverage_bucket_map"].find(
            {"l1_name": {"$in": l1_names}}
        )
        async for doc in cursor:
            result[doc["l1_name"]] = doc.get("bucket", "")
            if doc["l1_name"] in uncached:
                uncached.remove(doc["l1_name"])
    if not uncached:
        return result

    bucket_names = ", ".join(BUCKETS.keys())
    names_text = "\n".join(f"- {n}" for n in uncached)
    prompt = (
        f"将以下行业名称映射到这 18 个投资主题之一：{bucket_names}\n\n"
        f"行业名：\n{names_text}\n\n"
        f'输出 JSON: {{"L1行业名": "bucket名"}}'
    )
    try:
        from langchain_core.messages import HumanMessage
        resp = llm.invoke([HumanMessage(content=prompt)])
        text = resp.content if hasattr(resp, "content") else str(resp)
        import re, json
        m = re.search(r'\{[\s\S]*\}', text)
        if m:
            parsed = json.loads(m.group(0))
            for l1_name, bucket in parsed.items():
                matched = _match_bucket(str(bucket))
                if matched and l1_name in uncached:
                    result[l1_name] = matched
                    if db:
                        try:
                            await db["industry_coverage_bucket_map"].update_one(
                                {"l1_name": l1_name},
                                {"$set": {"l1_name": l1_name, "bucket": matched}},
                                upsert=True,
                            )
                        except Exception:
                            pass
    except Exception:
        pass

    # 未映射的回退
    for name in uncached:
        if name not in result:
            # 关键词兜底
            for bk in BUCKETS:
                if bk[:2] in name or name[:2] in bk[:2]:
                    result[name] = bk
                    break
            if name not in result:
                result[name] = ""

    return result


def _fallback_classify(code: str, name: str, instrument_type: str) -> str:
    """LLM 不可用时的关键词回退（A 股个票 + 基金/ETF）"""
    # 宽基指数
    for kw in ["沪深300", "中证500", "中证A500", "A500", "创业板",
               "上证50", "科创50", "中证红利", "红利低波"]:
        if kw in name: return "宽基指数"
    # 全球配置
    for kw in ["纳指", "纳斯达克", "标普", "恒生", "港股通", "全球",
               "QDII", "海外", "黄金"]:
        if kw in name: return "全球配置"
    # 债券
    for kw in ["债", "债券", "纯债", "信用债", "可转债", "利率债",
               "货基", "货币", "短融"]:
        if kw in name: return "债券/固收"
    # 行业关键词
    kw_map = {
        "消费（必选）": ["食品", "白酒", "农业", "调味"],
        "消费（可选）": ["家电", "汽车", "旅游", "纺织"],
        "互联网/平台": ["互联网", "中概", "恒生科技", "游戏", "传媒", "社交", "电商"],
        "半导体": ["半导体", "芯片", "科创"],
        "人工智能/软件": ["人工智能", "AI", "科技", "计算机", "软件"],
        "新能源（发电）": ["新能源", "光伏", "电池", "碳中和", "电力", "绿色"],
        "新能源车": ["新能源车", "智能车", "电车"],
        "通信/5G": ["通信", "5G"],
        "金融/保险": ["券商", "银行", "保险", "金融", "红利", "高股息"],
        "医药健康": ["医药", "医疗", "生物", "医美"],
        "高端制造": ["军工", "国防", "机器人", "工业", "制造"],
        "化工/材料": ["化工", "有色", "稀土", "新材料"],
        "基建/地产": ["地产", "基建"],
        "能源/公用": ["煤炭", "油气"],
    }
    for bucket, kws in kw_map.items():
        for kw in kws:
            if kw in name:
                return bucket
    # A 股个票无分类 → 其他（等 LLM 修复后会消除）
    return "其他"
