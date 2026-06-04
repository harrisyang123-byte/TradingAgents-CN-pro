"""行业景气打分引擎

对全量18大行业按5类信号打分，输出景气排行榜。
信号来源：资金流向 / 北向资金 / PE分位 / PMI-PPI / 政策文件（新闻+官网爬虫）

用法：
    from app.services.industry_vitality import score_all_industries
    scores = await score_all_industries()
    top3 = [s for s in scores if s["top3_flag"]]
"""

from __future__ import annotations
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# 18大行业 bucket（与 industry_buckets.BUCKETS 一致，排除现金）
INDUSTRY_BUCKETS = [
    "消费（必选）", "消费（可选）", "互联网/平台", "半导体", "人工智能/软件",
    "新能源（发电）", "新能源车", "通信/5G", "金融/保险", "医药健康",
    "高端制造", "化工/材料", "基建/地产", "能源/公用",
    "债券/固收", "宽基指数", "全球配置", "现金",
]

# 各维度权重（等权初版，后续可调整）
SIGNAL_WEIGHTS = {
    "fund_flow": 0.20,      # 行业资金流向
    "north_flow": 0.20,     # 北向资金
    "pe_percentile": 0.25,  # PE历史分位（低分位=便宜=加分）
    "pmi_ppi": 0.15,        # PMI/PPI宏观先行
    "policy": 0.20,         # 政策文件信号
}

# 官网政策爬虫 URL 列表
POLICY_URLS = [
    "https://www.gov.cn/zhengce/",          # 国务院政策
    "https://www.ndrc.gov.cn/xxgk/jd/",    # 发改委最新动态
    "https://www.csrc.gov.cn/csrc/c100028/", # 证监会最新公告
]

# 行业关键词（用于政策信号匹配）
INDUSTRY_POLICY_KEYWORDS: Dict[str, List[str]] = {
    "消费（必选）": ["消费", "食品", "农业", "粮食", "乡村振兴"],
    "消费（可选）": ["家电", "汽车", "旅游", "内需", "促消费"],
    "互联网/平台": ["互联网", "平台经济", "数字经济", "数据要素", "反垄断"],
    "半导体": ["半导体", "芯片", "集成电路", "国产替代", "科创"],
    "人工智能/软件": ["人工智能", "AI", "大模型", "算力", "数字化"],
    "新能源（发电）": ["新能源", "光伏", "风电", "储能", "碳中和", "双碳"],
    "新能源车": ["新能源汽车", "电动车", "充电桩", "换电"],
    "通信/5G": ["5G", "通信", "算力网络", "工业互联网"],
    "金融/保险": ["金融", "银行", "保险", "资本市场", "股市"],
    "医药健康": ["医药", "医疗", "生物技术", "创新药", "医保"],
    "高端制造": ["制造业", "机器人", "航空", "军工", "国防"],
    "化工/材料": ["化工", "新材料", "稀土", "有色金属"],
    "基建/地产": ["房地产", "基础设施", "城镇化", "建筑"],
    "能源/公用": ["煤炭", "油气", "电力", "能源安全"],
    "债券/固收": ["债券", "利率", "降准", "降息"],
    "宽基指数": ["A股", "资本市场", "上市公司"],
    "全球配置": ["海外", "全球", "黄金", "外汇"],
    "现金": [],
}


@dataclass
class IndustryVitalityScore:
    industry: str
    total_score: float = 0.0
    signal_breakdown: Dict[str, float] = field(default_factory=dict)
    data_completeness: float = 1.0  # 0-1，可用信号比例
    top3_flag: bool = False
    signals_used: List[str] = field(default_factory=list)
    signals_failed: List[str] = field(default_factory=list)


async def score_all_industries() -> List[IndustryVitalityScore]:
    """对全量18大行业打分，返回按分数降序排列的列表。前3名标注 top3_flag=True。"""

    # 并行获取所有信号数据
    fund_flows, north_data, pe_data, macro_data, policy_data = await asyncio.gather(
        _fetch_fund_flows(),
        _fetch_north_signal(),
        _fetch_pe_percentiles(),
        _fetch_macro_signal(),
        _fetch_policy_signals(),
        return_exceptions=True,
    )

    # 异常降级为空
    fund_flows = fund_flows if not isinstance(fund_flows, Exception) else {}
    north_data = north_data if not isinstance(north_data, Exception) else {}
    pe_data = pe_data if not isinstance(pe_data, Exception) else {}
    macro_data = macro_data if not isinstance(macro_data, Exception) else {}
    policy_data = policy_data if not isinstance(policy_data, Exception) else {}

    scores: List[IndustryVitalityScore] = []

    for industry in INDUSTRY_BUCKETS:
        score_obj = IndustryVitalityScore(industry=industry)
        weighted_sum = 0.0
        available_weight = 0.0

        # 1. 行业资金流向
        fund_score = _score_fund_flow(industry, fund_flows)
        if fund_score is not None:
            weighted_sum += fund_score * SIGNAL_WEIGHTS["fund_flow"]
            available_weight += SIGNAL_WEIGHTS["fund_flow"]
            score_obj.signal_breakdown["fund_flow"] = round(fund_score, 1)
            score_obj.signals_used.append("fund_flow")
        else:
            score_obj.signals_failed.append("fund_flow")

        # 2. 北向资金
        north_score = _score_north_flow(north_data)
        if north_score is not None:
            weighted_sum += north_score * SIGNAL_WEIGHTS["north_flow"]
            available_weight += SIGNAL_WEIGHTS["north_flow"]
            score_obj.signal_breakdown["north_flow"] = round(north_score, 1)
            score_obj.signals_used.append("north_flow")
        else:
            score_obj.signals_failed.append("north_flow")

        # 3. PE分位（低分位=估值便宜=加分）
        pe_score = _score_pe_percentile(industry, pe_data)
        if pe_score is not None:
            weighted_sum += pe_score * SIGNAL_WEIGHTS["pe_percentile"]
            available_weight += SIGNAL_WEIGHTS["pe_percentile"]
            score_obj.signal_breakdown["pe_percentile"] = round(pe_score, 1)
            score_obj.signals_used.append("pe_percentile")
        else:
            score_obj.signals_failed.append("pe_percentile")

        # 4. PMI/PPI
        macro_score = _score_macro(macro_data)
        if macro_score is not None:
            weighted_sum += macro_score * SIGNAL_WEIGHTS["pmi_ppi"]
            available_weight += SIGNAL_WEIGHTS["pmi_ppi"]
            score_obj.signal_breakdown["pmi_ppi"] = round(macro_score, 1)
            score_obj.signals_used.append("pmi_ppi")
        else:
            score_obj.signals_failed.append("pmi_ppi")

        # 5. 政策文件
        policy_score = _score_policy(industry, policy_data)
        if policy_score is not None:
            weighted_sum += policy_score * SIGNAL_WEIGHTS["policy"]
            available_weight += SIGNAL_WEIGHTS["policy"]
            score_obj.signal_breakdown["policy"] = round(policy_score, 1)
            score_obj.signals_used.append("policy")
        else:
            score_obj.signals_failed.append("policy")

        # 归一化（用可用权重归一化，而非总权重）
        if available_weight > 0:
            score_obj.total_score = round(weighted_sum / available_weight * 100, 1)
        score_obj.data_completeness = round(available_weight / sum(SIGNAL_WEIGHTS.values()), 2)

        scores.append(score_obj)

    # 按分数降序排列，前3名标注 top3_flag
    scores.sort(key=lambda x: x.total_score, reverse=True)
    for i, s in enumerate(scores[:3]):
        s.top3_flag = True

    logger.info(f"[IndustryVitality] 打分完成，前3名: {[s.industry for s in scores[:3]]}")
    return scores


# ── 信号获取函数 ────────────────────────────────────


async def _fetch_fund_flows() -> Dict[str, float]:
    """获取行业资金流向，返回 {行业关键词: 净流入百分比}"""
    try:
        from app.services.market_signals import fetch_sector_flows
        flows = await fetch_sector_flows()
        result = {}
        for item in flows:
            name = item.get("name") or item.get("行业", "")
            net = item.get("net_inflow") or item.get("净额", 0)
            if name and net is not None:
                result[name] = float(net)
        return result
    except Exception as e:
        logger.debug(f"行业资金流向获取失败: {e}")
        return {}


async def _fetch_north_signal() -> Dict[str, Any]:
    """获取北向资金信号"""
    try:
        from app.services.market_signals import fetch_north_flow
        return await fetch_north_flow()
    except Exception as e:
        logger.debug(f"北向资金获取失败: {e}")
        return {}


async def _fetch_pe_percentiles() -> Dict[str, float]:
    """获取各行业PE历史分位，返回 {行业名: 分位数(0-100)}"""
    try:
        import akshare as ak
        df = await asyncio.to_thread(ak.stock_board_industry_pe_em, symbol="近一年")
        if df is None or df.empty:
            return {}
        result = {}
        for _, row in df.iterrows():
            name = str(row.get("行业", "")).strip()
            pe = row.get("市盈率(动)", None)
            if name and pe is not None:
                result[name] = float(pe)
        return result
    except Exception as e:
        logger.debug(f"行业PE分位获取失败: {e}")
        return {}


async def _fetch_macro_signal() -> Dict[str, Any]:
    """获取PMI/PPI宏观信号"""
    try:
        from app.services.market_signals import fetch_macro_indicators
        return await fetch_macro_indicators()
    except Exception as e:
        logger.debug(f"宏观信号获取失败: {e}")
        return {}


async def _fetch_policy_signals() -> Dict[str, int]:
    """获取政策文件信号，返回 {行业bucket: 政策提及次数}"""
    result: Dict[str, int] = {ind: 0 for ind in INDUSTRY_BUCKETS}

    # 先用 AKShare 新闻接口（快速，覆盖广）
    news_texts = await _fetch_news_texts()

    # 再用官网爬虫（权威，慢）
    gov_texts = await _fetch_gov_texts()

    all_texts = news_texts + gov_texts

    for industry, keywords in INDUSTRY_POLICY_KEYWORDS.items():
        count = 0
        for text in all_texts:
            for kw in keywords:
                if kw in text:
                    count += 1
                    break  # 每篇文章只计一次
        result[industry] = count

    return result


async def _fetch_news_texts() -> List[str]:
    """从 AKShare 新闻接口获取近7天新闻标题"""
    try:
        import akshare as ak
        df = await asyncio.to_thread(ak.news_cctv, date=_recent_date())
        if df is None or df.empty:
            return []
        texts = []
        for col in ["title", "标题", "content", "内容"]:
            if col in df.columns:
                texts.extend(df[col].dropna().tolist())
        return [str(t) for t in texts[:200]]
    except Exception as e:
        logger.debug(f"AKShare 新闻获取失败: {e}")
        return []


async def _fetch_gov_texts() -> List[str]:
    """从官网爬虫获取政策文件标题（含反爬降级）"""
    texts = []
    for url in POLICY_URLS:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    # 简单提取 <a> 标签文本作为标题
                    import re
                    titles = re.findall(r'<a[^>]*>([^<]{4,50})</a>', resp.text)
                    texts.extend(titles[:50])
        except Exception as e:
            logger.debug(f"官网爬虫失败 {url}: {e}，降级为新闻接口")
    return texts


def _recent_date() -> str:
    """返回最近工作日的日期字符串"""
    from datetime import date, timedelta
    d = date.today()
    # 避免周末
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.strftime("%Y%m%d")


# ── 打分函数 ────────────────────────────────────────


def _score_fund_flow(industry: str, flows: Dict[str, float]) -> Optional[float]:
    """行业资金流向打分（0-100）。净流入越大分越高。"""
    if not flows:
        return None
    # 用行业关键词匹配资金流向数据
    keywords = INDUSTRY_POLICY_KEYWORDS.get(industry, [industry[:2]])
    matched_flow = None
    for name, net in flows.items():
        for kw in keywords + [industry[:2]]:
            if kw and kw in name:
                matched_flow = net
                break
        if matched_flow is not None:
            break
    if matched_flow is None:
        return 50.0  # 无数据时中性分

    # 归一化：净流入 > 50亿→100分，< -50亿→0分
    score = 50.0 + (matched_flow / 50.0) * 50.0
    return max(0.0, min(100.0, score))


def _score_north_flow(north_data: Dict[str, Any]) -> Optional[float]:
    """北向资金打分（全市场信号，对所有行业同等影响）"""
    if not north_data:
        return None
    net = north_data.get("north_net", 0)
    days = north_data.get("north_days", 0)
    # 连续净流入天数加权
    score = 50.0 + (net / 30.0) * 30.0 + days * 5.0
    return max(0.0, min(100.0, score))


def _score_pe_percentile(industry: str, pe_data: Dict[str, float]) -> Optional[float]:
    """PE分位打分（低分位=便宜=高分）。注意：成长行业PE高不一定贵。"""
    if not pe_data:
        return None
    # 尝试关键词匹配
    keywords = INDUSTRY_POLICY_KEYWORDS.get(industry, [])
    matched_pe = None
    for name, pe in pe_data.items():
        if any(kw in name for kw in keywords + [industry[:2]]) if keywords else industry[:2] in name:
            matched_pe = pe
            break
    if matched_pe is None:
        return 50.0  # 无匹配时中性

    # PE历史均值参考：A股整体约15-20x，高科技约30-50x
    # 低PE加分，高PE减分，但不线性（避免成长行业被过度惩罚）
    # 使用对数缩放
    import math
    if matched_pe <= 0:
        return 50.0
    log_pe = math.log(matched_pe)
    # log(15)≈2.7 → 70分，log(30)≈3.4 → 50分，log(60)≈4.1 → 30分
    score = 70.0 - (log_pe - 2.7) * 28.0
    return max(10.0, min(90.0, score))


def _score_macro(macro_data: Dict[str, Any]) -> Optional[float]:
    """PMI/PPI宏观打分（全市场信号）"""
    if not macro_data:
        return None
    pmi = macro_data.get("pmi")
    if pmi is None:
        return None
    # PMI > 50 扩张（加分），< 50 收缩（减分）
    score = 50.0 + (float(pmi) - 50.0) * 10.0
    return max(0.0, min(100.0, score))


def _score_policy(industry: str, policy_data: Dict[str, int]) -> Optional[float]:
    """政策文件打分（提及次数越多，政策支持越强）"""
    if not policy_data:
        return None
    count = policy_data.get(industry, 0)
    # 提及5次以上→满分，0次→基础50分
    score = 50.0 + min(count, 10) * 5.0
    return min(100.0, score)
