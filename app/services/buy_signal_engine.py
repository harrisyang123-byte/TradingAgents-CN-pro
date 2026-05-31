"""Buy Signal Engine — 四维打分 + 市场情绪 = 买入决策

四灯制：基本面 🟢 | 估值 🟢 | 情绪 🟢 | 资金 🟢
四灯全绿 = 最佳买点。每灯独立打分，数据可追溯。

质量分(25): L2 Scout 评分 + ROE + FCF
估值分(35): PE 分位 + MA20 位置 + 安全边际
情绪分(25): 千股千评 + 市场广度 + 北向资金方向
资金分(15): 行业资金流向 + 北向净流入 + 融资余额
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class BuySignal:
    code: str
    name: str = ""
    market: str = "cn"

    # 四维评分
    quality_score: float = 0.0       # 0-25
    valuation_score: float = 0.0     # 0-35
    sentiment_score: float = 0.0     # 0-25
    fund_flow_score: float = 0.0     # 0-15
    total_score: float = 0.0         # 0-100

    # 信号结果
    signal: str = ""                 # STRONG_BUY / BUY / HOLD / REDUCE / SELL
    confidence: str = ""             # 高 / 中 / 低
    price_range: str = ""            # "¥35-42"
    timing: str = ""                 # immediate / conditional / scheduled
    trigger_condition: str = ""      # 条件触发的具体条件

    # 四灯
    lights: Dict[str, str] = field(default_factory=lambda: {
        "quality": "⚪", "valuation": "⚪", "sentiment": "⚪", "fund_flow": "⚪",
    })

    # 溯源
    data_quality: Dict[str, Any] = field(default_factory=dict)
    missing_data: List[str] = field(default_factory=list)
    signal_details: Dict[str, str] = field(default_factory=dict)


class BuySignalEngine:
    """多信号融合的买入时机引擎"""

    def compute(
        self,
        code: str,
        name: str = "",
        market: str = "cn",
        pe_ctx: Optional[Dict] = None,
        scout_scores: Optional[Dict] = None,
        audit: Optional[Dict] = None,
        l1_industry: Optional[Dict] = None,
        market_signals: Optional[Dict] = None,
        stock_sentiment: Optional[Dict] = None,
        tier1_rating: str = "",
    ) -> BuySignal:
        """计算买入信号。

        Args:
            code: 标的代码
            name: 标的名称
            market: cn/hk/us
            pe_ctx: PE 分位计算上下文 {pe_percentile_5y, pe_ttm, pb, ma20, judgment, ...}
            scout_scores: L2 Scout 6维评分 {score_business_model, score_moat, score_management, score_financials, total_score, valuation}
            audit: 持仓体检 {health, pnl_pct, avg_cost, last_price, weight}
            l1_industry: L1 宏观裁判行业数据 {go_nogo, lifecycle, confidence}
            market_signals: 市场信号 {breadth, north_flow, flow_signal, macro}
            stock_sentiment: 个股情绪 {em_score, sentiment_label, sentiment_score}
            tier1_rating: Tier1 分析的评级（如 "buy"/"hold"/"sell"）
        """
        signal = BuySignal(code=code, name=name, market=market)
        pe_ctx = pe_ctx or {}
        scout_scores = scout_scores or {}
        audit = audit or {}
        l1_industry = l1_industry or {}
        market_signals = market_signals or {}
        stock_sentiment = stock_sentiment or {}

        # ── 维度一：质量分 (0-25) ──
        signal.quality_score = self._score_quality(scout_scores, tier1_rating)
        signal.lights["quality"] = self._light(signal.quality_score, 25)

        # ── 维度二：估值分 (0-35) ──
        signal.valuation_score = self._score_valuation(pe_ctx, audit)
        signal.lights["valuation"] = self._light(signal.valuation_score, 35)

        # ── 维度三：情绪分 (0-25) ──
        signal.sentiment_score = self._score_sentiment(
            stock_sentiment, market_signals, l1_industry
        )
        signal.lights["sentiment"] = self._light(signal.sentiment_score, 25)

        # ── 维度四：资金分 (0-15) ──
        signal.fund_flow_score = self._score_fund_flow(market_signals, l1_industry)
        signal.lights["fund_flow"] = self._light(signal.fund_flow_score, 15)

        # ── 综合 ──
        signal.total_score = (
            signal.quality_score
            + signal.valuation_score
            + signal.sentiment_score
            + signal.fund_flow_score
        )

        signal.signal = self._to_signal(signal.total_score)
        signal.confidence = self._confidence(signal, pe_ctx, scout_scores)
        signal.price_range = self._price_range(pe_ctx, audit)
        signal.timing = self._to_timing(signal, l1_industry, market_signals)
        signal.trigger_condition = self._trigger_condition(signal, pe_ctx, market_signals)

        # 数据质量
        signal.data_quality = {
            "has_pe": bool(pe_ctx.get("pe_percentile_source") and pe_ctx["pe_percentile_source"] != "data_unavailable"),
            "has_scout": bool(scout_scores),
            "has_sentiment": bool(stock_sentiment.get("em_score") or stock_sentiment.get("sentiment_label")),
            "has_fund_flow": bool(market_signals.get("north_net") is not None),
            "pe_source": pe_ctx.get("pe_percentile_source", "无"),
            "pe_data_points": pe_ctx.get("pe_data_points", 0),
        }
        signal.missing_data = [
            k for k, v in signal.data_quality.items()
            if isinstance(v, bool) and not v and k.startswith("has_")
        ]

        # 详情（可展示给用户）
        signal.signal_details = self._build_details(signal, pe_ctx, scout_scores, stock_sentiment, market_signals, audit)

        return signal

    # ── 评分逻辑 ─────────────────────────────────────

    def _score_quality(self, scout: Dict, tier1_rating: str) -> float:
        """质量分：L2 Scout 6维 > Tier1 评级"""
        if scout:
            bm = scout.get("score_business_model", 0) or 0
            mo = scout.get("score_moat", 0) or 0
            mg = scout.get("score_management", 0) or 0
            fi = scout.get("score_financials", 0) or 0
            score = (bm / 10 * 8) + (mo / 10 * 8) + (mg / 5 * 5) + (fi / 10 * 4)
            return round(min(score, 25), 1)

        # 无 Scout → Tier1 评级兜底
        rating_map = {"buy": 20, "strong_buy": 22, "hold": 13, "reduce": 7, "sell": 3}
        return float(rating_map.get(tier1_rating.lower(), 12))

    def _score_valuation(self, pe: Dict, audit: Dict) -> float:
        """估值分：PE分位 + MA20位置 + 安全边际"""
        score = 0.0
        pe_pct = pe.get("pe_percentile_5y")
        ma20 = pe.get("ma20")
        price = pe.get("current_price") or audit.get("last_price", 0)
        pe_ttm = pe.get("pe_ttm", 0)

        if pe_pct is not None and pe.get("pe_percentile_source") == "daily":
            # A 股：精确分位
            if pe_pct < 15:
                score += 18
            elif pe_pct < 30:
                score += 14
            elif pe_pct < 50:
                score += 8
            elif pe_pct < 75:
                score += 4
            else:
                score += 1
        elif pe_pct is not None:
            # 港股/美股：年度数据，折扣
            if pe_pct < 15:
                score += 12
            elif pe_pct < 30:
                score += 9
            elif pe_pct < 50:
                score += 5
            else:
                score += 2
        else:
            # 无 PE
            score += 5

        # MA20 相对位置
        if ma20 and price:
            if price < ma20 * 0.9:
                score += 8
            elif price < ma20:
                score += 5
            elif price < ma20 * 1.1:
                score += 3
            else:
                score += 1

        # 安全边际
        judgment = pe.get("judgment", "")
        if "低估" in str(judgment):
            score += 9
        elif "合理" in str(judgment):
            score += 5
        elif pe_pct is not None:
            score += 3
        else:
            score += 2

        return round(min(score, 35), 1)

    def _score_sentiment(
        self, stock: Dict, market: Dict, l1: Dict
    ) -> float:
        """情绪分：个股情绪 + 市场广度 + 行业情绪"""
        score = 10.0  # 中性基准

        # 个股情绪
        s_score = stock.get("sentiment_score", 50)
        if s_score >= 70: score += 6
        elif s_score >= 55: score += 3
        elif s_score >= 45: score += 0
        elif s_score >= 30: score -= 3
        else: score -= 5

        # 市场广度（恐惧时分数更高 → 逆向买入）
        breadth = market.get("breadth", {})
        bs = breadth.get("breadth_signal", "")
        breadth_map = {"恐慌": 6, "偏弱": 4, "中性": 0, "偏强": -2, "过热": -4}
        score += breadth_map.get(bs, 0)

        # 行业周期
        lifecycle = l1.get("lifecycle", "")
        if lifecycle in ("泡沫破裂期",):
            score += 3  # 逆向：泡沫破裂后是买点
        elif lifecycle in ("稳步成长期",):
            score += 2
        elif lifecycle in ("期望膨胀期",):
            score -= 3  # 过热不买

        return round(max(0, min(score, 25)), 1)

    def _score_fund_flow(self, market: Dict, l1: Dict) -> float:
        """资金分：北向流向 + 行业资金"""
        score = 7.0

        north_net = market.get("north_net", 0)
        north_days = market.get("north_days", 0)
        if north_net > 50: score += 4
        elif north_net > 10: score += 2
        elif north_net < -50: score -= 3
        elif north_net < -10: score -= 1
        if north_days >= 3: score += 2

        # 行业资金方向
        go_nogo = l1.get("go_nogo", "")
        if go_nogo == "Go": score += 2
        elif go_nogo == "NoGo": score -= 3

        return round(max(0, min(score, 15)), 1)

    # ── 信号输出 ─────────────────────────────────────

    def _to_signal(self, total: float) -> str:
        if total >= 75: return "STRONG_BUY"
        if total >= 60: return "BUY"
        if total >= 45: return "HOLD"
        if total >= 30: return "REDUCE"
        return "SELL"

    def _to_timing(self, s: BuySignal, l1: Dict, market: Dict) -> str:
        if s.signal in ("STRONG_BUY",):
            # 检查市场是否在恐慌中
            breadth = market.get("breadth", {})
            if breadth.get("breadth_signal") in ("恐慌", "偏弱"):
                return "immediate"  # 别人恐惧时立即买
            return "conditional"
        if s.signal == "BUY":
            lifecycle = l1.get("lifecycle", "")
            if lifecycle in ("泡沫破裂期",):
                return "immediate"
            return "conditional"
        if s.signal == "HOLD":
            return "scheduled"
        return "immediate"

    def _trigger_condition(self, s: BuySignal, pe: Dict, market: Dict) -> str:
        if s.timing != "conditional":
            return ""
        parts = []
        pe_pct = pe.get("pe_percentile_5y")
        if pe_pct is not None:
            parts.append(f"PE分位降至 {max(0, pe_pct - 10)}% 以下")
        if market.get("north_net", 0) < 0:
            parts.append("北向资金转为净流入")
        price = pe.get("current_price", 0)
        ma20 = pe.get("ma20", 0)
        if price and ma20 and price > ma20:
            parts.append(f"价格回调至 ¥{ma20:.0f} (MA20) 以下")
        return "；".join(parts) if parts else "观察市场企稳信号"

    def _price_range(self, pe: Dict, audit: Dict) -> str:
        """基于估值给出合理买入价格区间"""
        pe_pct = pe.get("pe_percentile_5y")
        price = pe.get("current_price") or audit.get("last_price", 0)
        ma20 = pe.get("ma20", 0)
        pe_ttm = pe.get("pe_ttm")

        if not price:
            return "数据不足"

        if pe_pct is not None and pe_pct < 50:
            # PE 低估或合理 → 当前价就是合理买入价附近
            low = round(price * 0.88, 1)
            high = round(price * 1.05, 1)
        elif ma20 and price:
            low = round(ma20 * 0.90, 1)
            high = round(ma20 * 1.05, 1)
        else:
            low = round(price * 0.85, 1)
            high = round(price, 1)

        return f"¥{low}-{high}"

    def _confidence(self, s: BuySignal, pe: Dict, scout: Dict) -> str:
        """置信度：基于数据完整度"""
        score = 0
        if pe.get("pe_percentile_source") == "daily":
            score += 3
        elif pe.get("pe_percentile_source") == "annual":
            score += 1
        if scout:
            score += 2
        if len(s.missing_data) == 0:
            score += 1
        if score >= 5: return "高"
        if score >= 3: return "中"
        return "低"

    def _light(self, score: float, max_score: float) -> str:
        ratio = score / max(max_score, 1)
        if ratio >= 0.70: return "🟢"
        if ratio >= 0.40: return "🟡"
        return "🔴"

    def _build_details(
        self, s: BuySignal, pe: Dict, scout: Dict,
        stock_sent: Dict, market: Dict, audit: Dict,
    ) -> Dict[str, str]:
        pe_pct = pe.get("pe_percentile_5y")
        return {
            "quality": (
                f"L2 Scout 总分 {scout.get('total_score','?')}/35"
                if scout else f"Tier1 评级: {s.signal_details.get('tier1','?')}"
            ),
            "valuation": (
                f"PE分位 {pe_pct:.0f}% · PE{pe.get('pe_ttm','?')}"
                if pe_pct is not None
                else f"MA20 ¥{pe.get('ma20',0):.0f}" if pe.get('ma20')
                else "估值数据不足"
            ),
            "sentiment": (
                f"{stock_sent.get('sentiment_label','?')} ({stock_sent.get('sentiment_score','?')}分)"
                if stock_sent else "情绪数据不足"
            ),
            "fund_flow": (
                f"北向 {'净流入' if market.get('north_net',0) > 0 else '净流出'} {abs(market.get('north_net',0)):.0f}亿"
                if market.get('north_net') is not None
                else "资金数据不足"
            ),
        }


# 全局单例
_engine: Optional[BuySignalEngine] = None


def get_buy_signal_engine() -> BuySignalEngine:
    global _engine
    if _engine is None:
        _engine = BuySignalEngine()
    return _engine
