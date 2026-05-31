"""风险总监工具 — 读 CIO 初稿 + 压力测试"""

from langchain_core.tools import tool
import json


def create_risk_tools(state_provider):
    """创建 Risk Director 工具列表。"""

    @tool
    def get_prescription_draft() -> str:
        """读取 CIO 初稿处方的摘要。"""
        state = state_provider()
        presc = state.get("prescription", [])
        lines = []
        for p in presc:
            lines.append(
                f"- {p.get('code')} {p.get('name')}: "
                f"{p.get('action')} → {p.get('target_weight', 0)}%")
        return "\n".join(lines) if lines else "无处方"

    @tool
    def check_stress_scenario(scenario: str) -> str:
        """获取情景压力测试结果。
        scenario: 'market_crash' / 'sector_rotation' / 'rate_hike'"""
        state = state_provider()
        stress_context = state.get("exposure_context", "")
        return stress_context[:2000] if stress_context else "无压力测试数据"

    return [get_prescription_draft, check_stress_scenario]
