"""情景压力测试服务 — 预设宏观情景，估算组合回撤"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class StressScenario:
    """压力测试情景定义"""
    name: str
    description: str
    severity: str  # mild / moderate / severe / extreme
    impact_map: Dict[str, float] = field(default_factory=dict)
    # 行业 → 预估跌幅(%), 如 {"科技": -25, "金融": -10, "消费": -8}
    broad_market_impact: float = 0.0  # 大盘整体跌幅(%)


# 预设情景
PRESET_SCENARIOS: List[StressScenario] = [
    StressScenario(
        name="关税升级",
        description="中美关税全面加征至60%，出口链受重创",
        severity="severe",
        impact_map={
            "电子": -30, "机械设备": -28, "家电": -25, "纺织服装": -25,
            "汽车": -22, "电力设备": -20, "基础化工": -18, "轻工制造": -20,
            "计算机": -15, "通信": -18, "国防军工": -5, "医药生物": -10,
            "食品饮料": -8, "银行": -12, "房地产": -10, "公用事业": -5,
        },
        broad_market_impact=-15,
    ),
    StressScenario(
        name="人民币贬值10%",
        description="人民币兑美元单边贬值10%，资本外流加剧",
        severity="moderate",
        impact_map={
            "银行": -15, "房地产": -20, "非银金融": -18,
            "电子": 5, "纺织服装": 8, "家用电器": 5, "汽车": 3,
            "食品饮料": -10, "医药生物": -12, "计算机": -8,
        },
        broad_market_impact=-5,
    ),
    StressScenario(
        name="美债利率+200bp",
        description="美联储意外加息，全球流动性收紧",
        severity="moderate",
        impact_map={
            "科技": -25, "成长": -28, "新能源": -22, "医药生物": -18,
            "银行": 5, "保险": 3, "公用事业": -5, "消费": -10,
            "房地产": -20, "汽车": -15,
        },
        broad_market_impact=-12,
    ),
    StressScenario(
        name="A股流动性危机",
        description="成交量萎缩至3000亿以下，融资盘爆仓连锁反应",
        severity="extreme",
        impact_map={
            "券商": -35, "中小盘": -40, "创业板": -35,
            "银行": -10, "保险": -15, "公用事业": -8,
            "食品饮料": -20, "医药生物": -22, "电子": -30,
        },
        broad_market_impact=-25,
    ),
    StressScenario(
        name="全球衰退",
        description="全球经济同步衰退，大宗商品暴跌",
        severity="extreme",
        impact_map={
            "有色金属": -35, "煤炭": -35, "石油石化": -35, "钢铁": -30,
            "基础化工": -28, "机械设备": -25, "电子": -25,
            "银行": -20, "保险": -22, "房地产": -25,
            "食品饮料": -12, "医药生物": -8, "公用事业": -5,
        },
        broad_market_impact=-20,
    ),
]


class StressTestService:
    """组合压力测试引擎"""

    @staticmethod
    def estimate_impact(
        positions: List[Dict[str, Any]],
        scenario: StressScenario,
        sector_map: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """估算给定情景下组合的预期回撤"""
        total_assets = sum(
            p.get("market_value_cny", 0) for p in positions
        )
        if total_assets == 0:
            return {"scenario": scenario.name, "total_impact_pct": 0, "total_impact_cny": 0}

        position_impacts = []
        total_loss = 0.0

        for pos in positions:
            code = pos.get("code", "")
            name = pos.get("name", code)
            mv = pos.get("market_value_cny", 0)
            weight = pos.get("weight", 0)
            instr = pos.get("instrument_type", "stock")

            # 基金/ETF用整体市场跌幅估算
            if instr in ("fund", "etf"):
                impact_pct = scenario.broad_market_impact * 0.8
            else:
                # 个股用行业映射
                sector = (sector_map or {}).get(code, "未知")
                impact_pct = scenario.impact_map.get(
                    sector, scenario.broad_market_impact
                )

            loss_cny = mv * (impact_pct / 100)
            total_loss += loss_cny

            if abs(impact_pct) > 5:
                position_impacts.append({
                    "code": code,
                    "name": name,
                    "sector": sector if instr == "stock" else instr,
                    "weight": weight,
                    "market_value": mv,
                    "impact_pct": round(impact_pct, 1),
                    "loss_cny": round(loss_cny, 0),
                })

        position_impacts.sort(key=lambda x: abs(x["loss_cny"]), reverse=True)

        total_impact_pct = round(total_loss / total_assets * 100, 1) if total_assets else 0

        return {
            "scenario": scenario.name,
            "severity": scenario.severity,
            "description": scenario.description,
            "total_impact_pct": total_impact_pct,
            "total_impact_cny": round(total_loss, 0),
            "top_impacts": position_impacts[:10],
        }

    @classmethod
    def run_all(
        cls,
        positions: List[Dict[str, Any]],
        sector_map: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, Any]]:
        """运行全部预设情景"""
        return [cls.estimate_impact(positions, s, sector_map) for s in PRESET_SCENARIOS]

    @staticmethod
    def format_context_for_advisor(
        stress_results: List[Dict[str, Any]],
    ) -> str:
        """将压力测试结果格式化为 CIO/Risk Director 可读上下文"""
        if not stress_results:
            return ""

        lines = [
            "## 情景压力测试",
            "",
            "| 情景 | 严重度 | 组合预估回撤 | 预估亏损 |",
            "|------|--------|-------------|----------|",
        ]

        worst = stress_results[0]
        for r in stress_results:
            sev_emoji = {"mild": "🟡", "moderate": "🟠", "severe": "🔴", "extreme": "⛔"}.get(
                r.get("severity", ""), "⚪"
            )
            lines.append(
                f"| {r['scenario']} | {sev_emoji} {r['severity']} | "
                f"{r['total_impact_pct']:+.1f}% | ¥{r['total_impact_cny']:+,.0f} |"
            )
            if abs(r.get("total_impact_pct", 0)) > abs(worst.get("total_impact_pct", 0)):
                worst = r

        lines.append("")
        lines.append(f"**最差情景**: {worst['scenario']}，组合回撤 {worst['total_impact_pct']:+.1f}%，亏损 ¥{worst['total_impact_cny']:+,.0f}")

        # Top 5 最脆弱的持仓
        all_impacts = []
        for r in stress_results:
            for imp in r.get("top_impacts", [])[:3]:
                all_impacts.append({**imp, "scenario": r["scenario"]})

        all_impacts.sort(key=lambda x: abs(x["loss_cny"]), reverse=True)
        unique = {}
        for imp in all_impacts:
            if imp["code"] not in unique:
                unique[imp["code"]] = imp
        top5 = list(unique.values())[:5]

        lines.append("")
        lines.append("**最脆弱持仓** (多情景下预估亏损最大的5只):")
        for imp in top5:
            lines.append(
                f"- {imp['name']}({imp['code']}): {imp['impact_pct']:+.1f}% | "
                f"亏损 ¥{imp['loss_cny']:,.0f} ({imp['scenario']}情景)"
            )

        if worst and abs(worst.get("total_impact_pct", 0)) > 20:
            lines.append("")
            lines.append("⚠ **极端风险警告**: 最差情景下组合回撤可能超过20%，建议检查是否有对冲手段。")

        return "\n".join(lines)
