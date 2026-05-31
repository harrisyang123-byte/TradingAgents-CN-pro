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

    # 构建 LLM prompt
    bucket_list = "\n".join(
        f"- {name}：{desc}" for name, desc in BUCKETS.items()
    )
    items_text = "\n".join(
        f"{i+1}. code={p.get('code','?')} name={p.get('name','?')} "
        f"type={p.get('instrument_type','stock')} market={p.get('market','')}"
        for i, p in enumerate(uncached)
    )

    prompt = f"""请将以下 {len(uncached)} 个投资标的分类到对应的投资主题中。

## 可选分类
{bucket_list}

## 分类规则
- 看公司/基金实际做什么业务，不看数据源标签
- 基金：从名称判断追踪的指数或投资方向。沪深300/中证500/A500/创业板 → 宽基指数
- 纳指/标普/恒生/全球/QDII/黄金 → 全球配置
- 债基/货基 → 债券/固收
- 现金 → 现金
- 如果一只标的横跨多个分类，选最主要的那一个

## 标的列表
{items_text}

## 输出格式
只输出一个 JSON 对象，key 是 code，value 是分类名：
```json
{{"000001": "消费（必选）", "00700": "互联网/平台", ...}}
```"""

    # LLM 分类
    try:
        from langchain_core.messages import HumanMessage

        if llm is None:
            raise ValueError("LLM 不可用")

        # 尝试用 bind_tools 的低成本模型分类（非 agent 调用，单次 LLM）
        response = llm.invoke([HumanMessage(content=prompt)])
        text = response.content if hasattr(response, "content") else str(response)

        # 提取 JSON — 支持多行和嵌套
        import re
        # 优先匹配 ```json ... ``` 代码块
        match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', text)
        if not match:
            # 匹配裸 JSON 对象
            match = re.search(r'\{[\s\S]*\}', text)
        if match:
            result = json.loads(match.group(0))
            for code, bucket in result.items():
                if bucket in BUCKETS:
                    code_to_bucket[code] = bucket
                    # 缓存到 MongoDB
                    if db is not None:
                        try:
                            await db["industry_classification_cache"].update_one(
                                {"code": code},
                                {"$set": {"code": code, "bucket": bucket, "name": next((p.get("name","") for p in uncached if p["code"]==code), "")}},
                                upsert=True,
                            )
                        except Exception:
                            pass
    except Exception as e:
        logger.warning(f"LLM 分类失败，回退到关键词: {e}")
        # 回退：关键词 + 映射
        for p in uncached:
            code = p["code"]
            name = p.get("name", "")
            inst = p.get("instrument_type", "stock")
            bucket = _fallback_classify(code, name, inst)
            code_to_bucket[code] = bucket

    # 未分类的兜底
    for p in uncached:
        if p["code"] not in code_to_bucket:
            code_to_bucket[p["code"]] = _fallback_classify(
                p["code"], p.get("name", ""), p.get("instrument_type", "stock")
            )

    return code_to_bucket


def _fallback_classify(code: str, name: str, instrument_type: str) -> str:
    """LLM 不可用时的关键词回退"""
    # 宽基指数
    broad_index_kw = ["沪深300", "中证500", "中证A500", "A500", "创业板",
                      "上证50", "科创50", "中证红利", "红利低波"]
    for kw in broad_index_kw:
        if kw in name:
            return "宽基指数"

    # 全球配置
    global_kw = ["纳指", "纳斯达克", "标普", "恒生", "港股通", "全球",
                 "QDII", "海外", "黄金"]
    for kw in global_kw:
        if kw in name:
            return "全球配置"

    # 债券
    bond_kw = ["债", "债券", "纯债", "信用债", "可转债", "利率债",
               "货基", "货币", "短融"]
    for kw in bond_kw:
        if kw in name:
            return "债券/固收"

    # 行业关键词 → bucket
    if instrument_type in ("fund", "etf"):
        kw_map = {
            "消费（必选）": ["食品", "白酒", "消费", "农业"],
            "消费（可选）": ["家电", "汽车", "旅游"],
            "互联网/平台": ["互联网", "中概", "恒生科技"],
            "半导体": ["半导体", "芯片", "科创"],
            "人工智能/软件": ["人工智能", "AI", "科技", "计算机"],
            "新能源（发电）": ["新能源", "光伏", "电池", "碳中和", "电力"],
            "新能源车": ["新能源车", "智能车", "电车"],
            "通信/5G": ["通信", "5G"],
            "金融/保险": ["券商", "银行", "保险", "金融", "红利", "高股息"],
            "医药健康": ["医药", "医疗", "生物", "医美"],
            "高端制造": ["军工", "国防", "机器人", "工业", "制造"],
            "化工/材料": ["化工", "有色", "稀土"],
            "基建/地产": ["地产", "基建"],
            "能源/公用": ["煤炭", "油气"],
        }
        for bucket, kws in kw_map.items():
            for kw in kws:
                if kw in name:
                    return bucket

    return "其他"
