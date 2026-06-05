"""事前风控规则引擎（Pre-trade Risk Rules）

规则引擎是非LLM的确定性检查器，在PM方案输出后、Risk Director运行前
硬拦截违规方案。违规打回对应行业PM重做（最多2次）。

规则：
1. 单股上限：target_weight ≤ max_single_weight
2. 行业上限：行业实际配仓加总 ≤ 行业配额 final_weight
3. 总仓位上限：所有行业配仓加总 ≤ total_weight_limit
4. 现金下限：现金仓位 ≥ cash_floor

返回值：
    violations: [] 表示通过
    violations: [{industry, rule, code, current, limit, message}] 表示违规
"""

from __future__ import annotations
from typing import Dict, Any, List


def Violation(industry: str, rule: str, code: str, current: float, limit: float, message: str) -> Dict[str, Any]:
    """创建违规范例"""
    return {
        "industry": industry,
        "rule": rule,
        "code": code,
        "current": current,
        "limit": limit,
        "message": message,
    }


def check_pm_positions(
    pm_results: List[Dict[str, Any]],
    total_weight_limit: float,
    cash_floor: float,
    max_single_weight: float,
) -> List[Dict[str, Any]]:
    """检查所有行业PM方案是否有违规

    Args:
        pm_results: 各行业PM结果列表
        total_weight_limit: 总仓位上限
        cash_floor: 现金下限
        max_single_weight: 单标的上限

    Returns:
        违规列表，空=通过
    """
    violations: List[Dict[str, Any]] = []
    total_allocated = 0.0

    for pm in pm_results:
        industry = pm.get("industry", "")
        final_weight = pm.get("final_weight", 0)
        positions = pm.get("positions", [])
        industry_total = 0.0

        for pos in positions:
            code = pos.get("code", "")
            tw = float(pos.get("target_weight", 0))
            industry_total += tw

            # 规则1：单股上限
            if tw > max_single_weight:
                violations.append(Violation(
                    industry=industry, rule="single_stock_limit",
                    code=code, current=tw, limit=max_single_weight,
                    message=f"{code} target_weight {tw}% 超过单股上限 {max_single_weight}%",
                ))

        # 规则2：行业上限
        if industry_total > final_weight:
            violations.append(Violation(
                industry=industry, rule="industry_weight_limit",
                code="",
                current=round(industry_total, 1), limit=final_weight,
                message=f"{industry} 配仓总计 {industry_total:.1f}% 超过行业配额 {final_weight}%",
            ))

        total_allocated += industry_total

    # 规则3：总仓位上限
    if total_allocated > total_weight_limit:
        violations.append(Violation(
            industry="*", rule="total_weight_limit",
            code="", current=round(total_allocated, 1), limit=total_weight_limit,
            message=f"总配仓 {total_allocated:.1f}% 超过总仓位上限 {total_weight_limit}%",
        ))

    # 规则4：现金下限（检查是否有现金行业）
    cash_pm = next((p for p in pm_results if p.get("industry") == "现金"), None)
    if cash_pm:
        cash_positions = cash_pm.get("positions", [])
        cash_weight = sum(float(p.get("target_weight", 0)) for p in cash_positions)
        if cash_weight < cash_floor:
            violations.append(Violation(
                industry="现金", rule="cash_floor",
                code="", current=cash_weight, limit=cash_floor,
                message=f"现金 {cash_weight}% 低于现金下限 {cash_floor}%",
            ))
    elif cash_floor > 0:
        violations.append(Violation(
            industry="*", rule="cash_floor",
            code="", current=0, limit=cash_floor,
            message=f"无现金行业配仓，但要求不低于 {cash_floor}%",
        ))

    return violations


def auto_truncate(
    pm_results: List[Dict[str, Any]],
    total_weight_limit: float,
    max_single_weight: float,
) -> List[Dict[str, Any]]:
    """第3次违规时强制截断到边界。

    按比例缩放超出部分，确保所有约束满足。
    返回修正后的 pm_results。
    """
    import copy
    fixed = copy.deepcopy(pm_results)

    for pm in fixed:
        industry = pm.get("industry", "")
        final_weight = pm.get("final_weight", 0)
        positions = pm.get("positions", [])
        industry_total = sum(float(p.get("target_weight", 0)) for p in positions)

        # 规则1：单股超限截断
        for pos in positions:
            tw = float(pos.get("target_weight", 0))
            if tw > max_single_weight:
                pos["target_weight"] = max_single_weight
                pos["reasoning"] = pos.get("reasoning","") + f"\n【风控自动截断】target_weight 从 {tw}% 调整为 {max_single_weight}%"

        # 规则2：行业超限按比例缩放
        if industry_total > final_weight and industry_total > 0:
            ratio = final_weight / industry_total
            for pos in positions:
                old_tw = pos.get("target_weight", 0)
                pos["target_weight"] = round(float(old_tw) * ratio, 1)
                pos["reasoning"] = pos.get("reasoning","") + "\n【风控自动截断】行业超限，按比例缩放"

    # 规则3：总仓位超限按行业比例缩放
    all_total = sum(
        sum(float(p.get("target_weight", 0)) for p in pm.get("positions", []))
        for pm in fixed
    )
    if all_total > total_weight_limit and all_total > 0:
        ratio = total_weight_limit / all_total
        for pm in fixed:
            for pos in pm["positions"]:
                pos["target_weight"] = round(float(pos.get("target_weight", 0)) * ratio, 1)

    return fixed
