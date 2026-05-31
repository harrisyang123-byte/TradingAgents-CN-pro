"""统一行业 Bucket 映射 — 15 个投资主题 + 现金

映射路径：代码 → (stock_basic_info / yfinance / 名称关键词) → bucket_map → bucket

目的：将 A 股（申万行业）、HK/US（GICS）、基金（名称关键词）三套分类体系统一到
同一套投资可操作的粗粒度 bucket，消除"其他"品类。
"""

from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

# ── 16 个投资主题 Bucket ──────────────────────────────

BUCKETS = {
    "消费/互联网": "电商、社交、游戏、IP、零售、食品饮料、家电",
    "半导体":     "芯片设计、制造、封测、设备",
    "人工智能":   "AI 算力、算法、应用、软件",
    "新能源":     "光伏、风电、储能、锂电材料",
    "新能源车":   "整车、电池、热管理、零部件",
    "通信/5G":    "通信设备、光模块、运营商、卫星",
    "金融/保险":  "银行、券商、保险、金融IT",
    "医药健康":   "制药、器械、CXO、医疗、医美",
    "高端制造":   "工业自动化、机器人、军工、航空航天",
    "家电/电子":  "白电、黑电、消费电子、元器件",
    "化工/材料":  "化工品、新材料、稀土、塑料",
    "基建/地产":  "建筑、建材、房地产、工程机械",
    "能源/公用":  "电力、煤炭、油气、水务、环保",
    "债券/固收":  "利率债、信用债、货基、短融",
    "全球/QDII":  "美股宽基、港股宽基、全球配置",
    "现金":       "可用现金、逆回购、货基预留",
}

# ── 申万一级行业 → Bucket ─────────────────────────────

SHENWAN_TO_BUCKET: Dict[str, str] = {
    # 消费/互联网
    "食品饮料":   "消费/互联网",
    "休闲服务":   "消费/互联网",
    "商业贸易":   "消费/互联网",
    "纺织服装":   "消费/互联网",
    "轻工制造":   "消费/互联网",
    "传媒":       "消费/互联网",
    "家用电器":   "消费/互联网",
    "农林牧渔":   "消费/互联网",
    # 半导体
    "电子":       "半导体",
    # 人工智能
    "计算机":     "人工智能",
    # 新能源
    "电气设备":   "新能源",
    "公用事业":   "能源/公用",
    # 新能源车
    "汽车":       "新能源车",
    # 通信/5G
    "通信":       "通信/5G",
    # 金融/保险
    "银行":       "金融/保险",
    "非银金融":   "金融/保险",
    "综合金融":   "金融/保险",
    # 医药健康
    "医药生物":   "医药健康",
    "美容护理":   "医药健康",
    # 高端制造
    "机械设备":   "高端制造",
    "国防军工":   "高端制造",
    "电力设备":   "新能源",
    # 化工/材料
    "基础化工":   "化工/材料",
    "有色金属":   "化工/材料",
    "钢铁":       "化工/材料",
    # 基建/地产
    "建筑装饰":   "基建/地产",
    "建筑材料":   "基建/地产",
    "房地产":     "基建/地产",
    # 能源/公用
    "煤炭":       "能源/公用",
    "石油石化":   "能源/公用",
    "环保":       "能源/公用",
    # 交通运输
    "交通运输":   "基建/地产",
    # 综合 → 兜底
    "综合":       "高端制造",
}

# ── GICS Sector/Industry → Bucket ──────────────────────

GICS_TO_BUCKET: Dict[str, str] = {
    # Consumer
    "Consumer Cyclical":              "消费/互联网",
    "Consumer Defensive":             "消费/互联网",
    "Specialty Retail":               "消费/互联网",
    "Internet Retail":                "消费/互联网",
    "Luxury Goods":                   "消费/互联网",
    "Travel Services":                "消费/互联网",
    "Restaurants":                    "消费/互联网",
    "Beverages":                      "消费/互联网",
    "Packaged Foods":                 "消费/互联网",
    "Household & Personal Products":  "消费/互联网",
    "Entertainment":                  "消费/互联网",
    "Electronic Gaming & Multimedia": "消费/互联网",
    "Media":                          "消费/互联网",
    "Apparel":                        "消费/互联网",
    "Food":                           "消费/互联网",
    "Tobacco":                        "消费/互联网",
    "Education & Training Services":  "消费/互联网",
    # Technology
    "Technology":                     "半导体",
    "Semiconductors":                 "半导体",
    "Semiconductor Equipment & Materials": "半导体",
    "Software":                       "人工智能",
    "Software—Application":           "人工智能",
    "Software—Infrastructure":        "人工智能",
    "Information Technology Services": "人工智能",
    "Communication Equipment":        "通信/5G",
    "Hardware":                       "家电/电子",
    "Consumer Electronics":           "家电/电子",
    "Electronic Components":          "家电/电子",
    # Auto / Energy
    "Auto Manufacturers":             "新能源车",
    "Auto Parts":                     "新能源车",
    "Solar":                          "新能源",
    "Utilities":                      "能源/公用",
    "Utilities—Independent Power":    "能源/公用",
    "Utilities—Renewable":            "新能源",
    "Oil & Gas":                      "能源/公用",
    # Financial
    "Financial Services":             "金融/保险",
    "Banks":                          "金融/保险",
    "Insurance":                      "金融/保险",
    "Capital Markets":                "金融/保险",
    "Credit Services":                "金融/保险",
    "Fintech":                        "金融/保险",
    # Healthcare
    "Healthcare":                     "医药健康",
    "Biotechnology":                  "医药健康",
    "Drug Manufacturers":             "医药健康",
    "Medical Devices":                "医药健康",
    "Diagnostics & Research":         "医药健康",
    "Health Information Services":    "医药健康",
    # Industrial
    "Industrials":                    "高端制造",
    "Aerospace & Defense":            "高端制造",
    "Machinery":                      "高端制造",
    "Industrial Products":            "高端制造",
    "Robotics":                       "高端制造",
    "Engineering & Construction":     "基建/地产",
    "Construction":                   "基建/地产",
    "Building Products":              "基建/地产",
    # Materials
    "Basic Materials":                "化工/材料",
    "Chemicals":                      "化工/材料",
    "Specialty Chemicals":            "化工/材料",
    "Metals & Mining":                "化工/材料",
    "Steel":                          "化工/材料",
    # Real Estate
    "Real Estate":                    "基建/地产",
    "Real Estate—Development":        "基建/地产",
    "Real Estate Services":           "基建/地产",
    # Telecom / Energy
    "Telecommunications":             "通信/5G",
    "Telecom Services":               "通信/5G",
    "Energy":                         "能源/公用",
    "Coal":                           "能源/公用",
    # Transport
    "Airlines":                       "基建/地产",
    "Transportation":                 "基建/地产",
    "Marine Shipping":                "基建/地产",
    "Railroads":                      "基建/地产",
}

# ── 基金名称关键词 → Bucket ────────────────────────────

FUND_KW_TO_BUCKET: Dict[str, str] = {
    "纳指": "全球/QDII", "纳斯达克": "全球/QDII", "标普": "全球/QDII",
    "恒生": "全球/QDII", "港股": "全球/QDII", "全球": "全球/QDII",
    "QDII": "全球/QDII", "海外": "全球/QDII",
    "科创": "半导体", "创业板": "高端制造",
    "中证500": "高端制造", "沪深300": "金融/保险", "上证50": "金融/保险",
    "中证A500": "高端制造", "A500": "高端制造",
    "债": "债券/固收", "债券": "债券/固收", "纯债": "债券/固收",
    "信用债": "债券/固收", "可转债": "债券/固收", "利率债": "债券/固收",
    "黄金": "全球/QDII", "原油": "能源/公用",
    "医药": "医药健康", "医疗": "医药健康", "生物": "医药健康",
    "消费": "消费/互联网", "食品": "消费/互联网", "白酒": "消费/互联网",
    "半导体": "半导体", "芯片": "半导体",
    "军工": "高端制造", "国防": "高端制造",
    "新能源": "新能源", "光伏": "新能源", "电池": "新能源",
    "券商": "金融/保险", "银行": "金融/保险", "保险": "金融/保险",
    "人工智能": "人工智能", "AI": "人工智能", "科技": "人工智能",
    "汽车": "新能源车", "智能车": "新能源车", "电车": "新能源车",
    "红利": "金融/保险", "高股息": "金融/保险",
    "电力": "能源/公用", "碳中和": "新能源",
    "通信": "通信/5G", "5G": "通信/5G",
    "家电": "家电/电子", "电子": "家电/电子",
    "化工": "化工/材料", "有色": "化工/材料", "稀土": "化工/材料",
    "地产": "基建/地产", "基建": "基建/地产",
    "煤炭": "能源/公用", "油气": "能源/公用",
    "工业": "高端制造", "制造": "高端制造", "机器人": "高端制造",
    "互联网": "消费/互联网", "中概": "消费/互联网",
    "增强": "金融/保险",  # 增强型指数 → 默认大盘
}

# ── 公司名 → Bucket（硬编码知名公司，yfinance 失败时的兜底）──

KNOWN_COMPANY_BUCKETS: Dict[str, str] = {
    "00700": "消费/互联网",  # Tencent
    "09992": "消费/互联网",  # Pop Mart
    "01810": "家电/电子",    # Xiaomi
    "09988": "消费/互联网",  # Alibaba
    "09961": "消费/互联网",  # Trip.com
    "09618": "消费/互联网",  # JD.com
    "09888": "人工智能",     # Baidu
    "02015": "新能源车",     # Li Auto
    "09866": "新能源车",     # NIO
    "01211": "新能源车",     # BYD
    "02318": "金融/保险",    # Ping An
    "00941": "通信/5G",      # China Mobile
    "00883": "能源/公用",    # CNOOC
    "09999": "消费/互联网",  # NetEase
    "01024": "消费/互联网",  # Kuaishou
    "02013": "消费/互联网",  # Weimob
    "01833": "医药健康",     # Ping An Health
    "02269": "医药健康",     # WuXi Biologics
    "09926": "医药健康",     # Akeso
    "09633": "医药健康",     # Nongfu Spring → 消费/互联网
    "09901": "消费/互联网",  # New Oriental
    "09626": "消费/互联网",  # Bilibili
    "06618": "医药健康",     # JD Health
    "06098": "基建/地产",    # Country Garden
    "02382": "家电/电子",    # Sunny Optical
    "01299": "金融/保险",    # AIA
    "00005": "金融/保险",    # HSBC
    "00388": "金融/保险",    # HKEX
    "00939": "金融/保险",    # CCB
    "01398": "金融/保险",    # ICBC
}


def swan_to_bucket(sw_industry: str) -> str:
    """申万行业 → bucket"""
    if not sw_industry:
        return ""
    sw_industry = sw_industry.strip()
    # 精确匹配
    if sw_industry in SHENWAN_TO_BUCKET:
        return SHENWAN_TO_BUCKET[sw_industry]
    # 子串匹配（如 "化学制品" 包含 "化工"）
    for key, bucket in SHENWAN_TO_BUCKET.items():
        if key in sw_industry or sw_industry in key:
            return bucket
    return ""


def gics_to_bucket(gics_industry: str, gics_sector: str = "") -> str:
    """GICS industry/sector → bucket"""
    if gics_industry:
        gics_industry = gics_industry.strip()
        if gics_industry in GICS_TO_BUCKET:
            return GICS_TO_BUCKET[gics_industry]
        for key, bucket in GICS_TO_BUCKET.items():
            if key.lower() in gics_industry.lower():
                return bucket
    if gics_sector:
        gics_sector = gics_sector.strip()
        if gics_sector in GICS_TO_BUCKET:
            return GICS_TO_BUCKET[gics_sector]
    return ""


def code_to_bucket(code: str) -> str:
    """知名公司兜底映射"""
    return KNOWN_COMPANY_BUCKETS.get(code, "")


def fund_name_to_bucket(name: str) -> str:
    """基金名称关键词 → bucket"""
    if not name:
        return ""
    for kw, bucket in FUND_KW_TO_BUCKET.items():
        if kw in name:
            return bucket
    return ""


def classify(code: str, name: str, instrument_type: str,
             sw_industry: str = "", gics_industry: str = "",
             gics_sector: str = "") -> str:
    """综合分类入口。

    优先级:
    1. 知名公司兜底 (code)
    2. 申万行业 → bucket (A 股)
    3. GICS → bucket (HK/US)
    4. 基金名称关键词 (fund/etf)
    5. 其他
    """
    bucket = ""

    # 1. 知名公司
    bucket = code_to_bucket(code)
    if bucket:
        return bucket

    # 2. 申万行业
    if sw_industry:
        bucket = swan_to_bucket(sw_industry)
        if bucket:
            return bucket

    # 3. GICS
    bucket = gics_to_bucket(gics_industry, gics_sector)
    if bucket:
        return bucket

    # 4. 基金关键词
    if instrument_type in ("fund", "etf"):
        bucket = fund_name_to_bucket(name)
        if bucket:
            return bucket

    # 5. 兜底
    return "其他"
