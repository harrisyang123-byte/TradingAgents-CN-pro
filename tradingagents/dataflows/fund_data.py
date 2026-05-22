"""基金数据工具层：为基金分析 Agent 提供数据"""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_fund_basic_info(code: str) -> str:
    """获取基金基础信息和投资策略"""
    try:
        import akshare as ak
        df = ak.fund_individual_basic_info_xq(symbol=code)
        if df is None or df.empty:
            return f"无法获取基金 {code} 的基础信息"

        info = {}
        for _, row in df.iterrows():
            key = str(row.get("item", "")).strip()
            val = row.get("value")
            if val is not None and str(val) not in ("nan", "<NA>", "None"):
                info[key] = str(val)

        lines = [f"基金代码: {code}"]
        for field in ["基金名称", "基金全称", "基金类型", "成立时间", "最新规模",
                      "基金公司", "基金经理", "业绩比较基准", "投资目标", "投资策略"]:
            if field in info:
                val = info[field]
                if len(val) > 200:
                    val = val[:200] + "..."
                lines.append(f"{field}: {val}")

        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"get_fund_basic_info {code}: {e}")
        return f"获取基金基础信息失败: {e}"


def get_fund_performance(code: str) -> str:
    """获取基金历史业绩和同类排名"""
    try:
        import akshare as ak
        lines = [f"基金 {code} 业绩数据:"]

        # 历史业绩
        try:
            df = ak.fund_individual_achievement_xq(symbol=code)
            if df is not None and not df.empty:
                lines.append("\n【历史业绩】")
                for _, row in df.iterrows():
                    lines.append(
                        f"  {row.get('业绩类型','')} {row.get('周期','')}:"
                        f" 收益={row.get('本产品区间收益','')}%,"
                        f" 最大回撤={row.get('本产品最大回撒','')}%,"
                        f" 同类排名={row.get('周期收益同类排名','')}"
                    )
        except Exception as e:
            lines.append(f"历史业绩获取失败: {e}")

        # 风险收益分析
        try:
            df2 = ak.fund_individual_analysis_xq(symbol=code)
            if df2 is not None and not df2.empty:
                lines.append("\n【风险收益分析】")
                for _, row in df2.iterrows():
                    lines.append(
                        f"  {row.get('周期','')}:"
                        f" 较同类风险收益比={row.get('较同类风险收益比','')},"
                        f" 年化波动率={row.get('年化波动率','')}%,"
                        f" 年化夏普比率={row.get('年化夏普比率','')},"
                        f" 最大回撤={row.get('最大回撤','')}%"
                    )
        except Exception as e:
            lines.append(f"风险收益分析获取失败: {e}")

        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"get_fund_performance {code}: {e}")
        return f"获取基金业绩数据失败: {e}"


def get_fund_risk_metrics(code: str) -> str:
    """获取基金风险指标：同类排名走势、回撤历史"""
    try:
        import akshare as ak
        lines = [f"基金 {code} 风险指标:"]

        # 同类排名走势（取最近 20 条）
        try:
            df = ak.fund_open_fund_info_em(symbol=code, indicator="同类排名走势")
            if df is not None and not df.empty:
                recent = df.tail(20)
                lines.append(f"\n【近期同类排名走势（最近{len(recent)}条）】")
                for _, row in recent.iterrows():
                    lines.append(
                        f"  {row.get('报告日期','')}: "
                        f"近三月排名={row.get('同类型排名-每日近三月排名','')}"
                        f"/{row.get('总排名-每日近三月排名','')}"
                    )
        except Exception as e:
            lines.append(f"同类排名走势获取失败: {e}")

        # 净值走势摘要（最近 30 条）
        try:
            df2 = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
            if df2 is not None and not df2.empty:
                recent = df2.tail(30)
                nav_min = recent["单位净值"].min()
                nav_max = recent["单位净值"].max()
                nav_latest = recent["单位净值"].iloc[-1]
                lines.append(f"\n【近30日净值摘要】")
                lines.append(f"  最新净值: {nav_latest:.4f}")
                lines.append(f"  区间最低: {nav_min:.4f}")
                lines.append(f"  区间最高: {nav_max:.4f}")
                lines.append(f"  区间涨跌: {((nav_latest - recent['单位净值'].iloc[0]) / recent['单位净值'].iloc[0] * 100):.2f}%")
        except Exception as e:
            lines.append(f"净值走势获取失败: {e}")

        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"get_fund_risk_metrics {code}: {e}")
        return f"获取基金风险指标失败: {e}"


def get_fund_holdings_or_index(code: str, fund_type: str = "") -> str:
    """
    获取基金持仓数据：
    - 主动型基金：返回前十大重仓股
    - QDII/指数型：返回资产配置 + 指数信息
    """
    try:
        import akshare as ak
        from datetime import datetime

        lines = [f"基金 {code} 持仓数据:"]
        is_passive = any(k in fund_type.upper() for k in ["QDII", "ETF", "指数", "INDEX"])

        if not is_passive:
            # 尝试获取重仓股
            current_year = str(datetime.now().year)
            prev_year = str(datetime.now().year - 1)
            df = None
            for year in [current_year, prev_year]:
                try:
                    df = ak.fund_portfolio_hold_em(symbol=code, date=year)
                    if df is not None and not df.empty:
                        break
                except Exception:
                    continue

            if df is not None and not df.empty:
                lines.append(f"\n【前十大重仓股（最新报告期）】")
                for _, row in df.head(10).iterrows():
                    lines.append(
                        f"  {row.get('股票代码','')} {row.get('股票名称','')}:"
                        f" 占净值{row.get('占净值比例','')}%,"
                        f" 季度={row.get('季度','')}"
                    )
                return "\n".join(lines)

        # QDII/指数型或无重仓股数据：返回资产配置
        lines.append(f"\n【资产配置（{fund_type or '指数/QDII'}型基金）】")
        try:
            df2 = ak.fund_individual_detail_hold_xq(symbol=code, date="20241231")
            if df2 is not None and not df2.empty:
                for _, row in df2.iterrows():
                    lines.append(f"  {row.get('资产类型','')}: {row.get('仓位占比','')}%")
        except Exception as e:
            lines.append(f"  资产配置获取失败: {e}")

        # 从基础信息获取业绩比较基准（指数信息）
        try:
            df3 = ak.fund_individual_basic_info_xq(symbol=code)
            if df3 is not None and not df3.empty:
                for _, row in df3.iterrows():
                    if row.get("item") == "业绩比较基准":
                        lines.append(f"\n【跟踪指数】{row.get('value','')}")
                        break
        except Exception:
            pass

        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"get_fund_holdings_or_index {code}: {e}")
        return f"获取基金持仓数据失败: {e}"


def get_fund_nav_history_summary(code: str) -> str:
    """获取基金净值历史摘要（用于分析，不是完整数据）"""
    try:
        import akshare as ak
        df = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
        if df is None or df.empty:
            return f"无法获取基金 {code} 净值历史"

        df = df.sort_values("净值日期").reset_index(drop=True)

        # 计算关键指标
        nav_latest = df["单位净值"].iloc[-1]
        nav_1y = df[df["净值日期"] >= df["净值日期"].iloc[-1] - "365 days" if hasattr(df["净值日期"].iloc[-1], "__sub__") else df.tail(250)]["单位净值"].iloc[0] if len(df) > 250 else df["单位净值"].iloc[0]

        # 用字符串比较日期
        date_str = str(df["净值日期"].iloc[-1])
        one_year_ago = f"{int(date_str[:4])-1}{date_str[4:]}"
        df_1y = df[df["净值日期"].astype(str) >= one_year_ago]
        nav_1y_start = df_1y["单位净值"].iloc[0] if not df_1y.empty else df["单位净值"].iloc[0]

        return_1y = (nav_latest - nav_1y_start) / nav_1y_start * 100

        lines = [
            f"基金 {code} 净值历史摘要:",
            f"  最新净值: {nav_latest:.4f}",
            f"  成立以来最低: {df['单位净值'].min():.4f}",
            f"  成立以来最高: {df['单位净值'].max():.4f}",
            f"  近1年收益率: {return_1y:.2f}%",
            f"  数据起始: {df['净值日期'].iloc[0]}",
            f"  数据截止: {df['净值日期'].iloc[-1]}",
            f"  总交易日数: {len(df)}",
        ]
        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"get_fund_nav_history_summary {code}: {e}")
        return f"获取净值历史摘要失败: {e}"
