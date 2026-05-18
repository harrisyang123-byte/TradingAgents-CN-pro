"""Tier 2 组合顾问 LangGraph — 三角色独立分析 → 辩论 → CIO 裁决"""

from __future__ import annotations
import time
from typing import Dict, Any, Optional, Callable

from langgraph.graph import END, StateGraph, START

from tradingagents.agents.advisors import (
    AdvisorState,
    create_portfolio_analyst,
    create_strategist,
    create_scout,
    create_cio,
)
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


def _create_debate_node(llm, role: str):
    """创建辩论节点——每个角色读对方观点后补充自己的"""

    role_label = {
        "analyst": "持仓分析师",
        "strategist": "策略师",
        "scout": "侦察兵",
    }[role]

    assessment_key = {
        "analyst": "analyst_assessment",
        "strategist": "strategist_assessment",
        "scout": "scout_assessment",
    }[role]

    response_key = {
        "analyst": "analyst_response",
        "strategist": "strategist_response",
        "scout": "scout_response",
    }[role]

    def debate_node(state: dict) -> dict:
        debate = state.get("advisor_debate_state", {})
        history = debate.get("history", "")
        own_assessment = state.get(assessment_key, "")

        other_responses = []
        for other_role, other_key in [
            ("analyst", "analyst_response"),
            ("strategist", "strategist_response"),
            ("scout", "scout_response"),
        ]:
            if other_role != role:
                resp = debate.get(other_key, "")
                if resp:
                    other_responses.append(f"[{other_role}]: {resp[:1000]}")

        prompt = f"""你是组合顾问团队的{role_label}，正在参与团队辩论。

你此前的独立评估：
{own_assessment[:1500]}

其他成员的最新观点：
{chr(10).join(other_responses) if other_responses else '尚无其他成员发言'}

辩论历史：
{history[-2000:] if history else '首轮辩论'}

请针对其他成员的观点：
1. 指出你同意的部分（及理由）
2. 指出你不同意的部分（及理由）
3. 补充你认为被忽视的重要因素
4. 更新你的操作建议（如有变化）

保持你的角色视角，用中文简洁回答。"""

        from langchain_core.messages import HumanMessage
        response = llm.invoke([HumanMessage(content=prompt)])
        text = response.content if hasattr(response, "content") else str(response)

        new_history = history + f"\n\n[{role_label} 辩论]: {text}"
        new_debate = dict(debate)
        new_debate[response_key] = text
        new_debate["history"] = new_history
        new_debate["current_speaker"] = role

        return {"advisor_debate_state": new_debate}

    return debate_node


def _should_continue_debate(state: dict) -> str:
    """辩论轮数控制"""
    debate = state.get("advisor_debate_state", {})
    count = debate.get("count", 0)
    max_rounds = state.get("debate_rounds", 2)
    if count >= max_rounds:
        return "CIO"
    return "debate_analyst"


def _increment_debate_round(state: dict) -> dict:
    """辩论轮次计数器"""
    debate = dict(state.get("advisor_debate_state", {}))
    debate["count"] = debate.get("count", 0) + 1
    return {"advisor_debate_state": debate}


class AdvisorGraph:
    """Tier 2 组合顾问引擎"""

    def __init__(self, llm, config: Dict[str, Any] = None):
        self.llm = llm
        self.config = config or {}
        self.graph = self._build_graph()

    def _build_graph(self) -> Any:
        analyst_node = create_portfolio_analyst(self.llm)
        strategist_node = create_strategist(self.llm)
        scout_node = create_scout(self.llm)
        cio_node = create_cio(self.llm)

        debate_analyst = _create_debate_node(self.llm, "analyst")
        debate_strategist = _create_debate_node(self.llm, "strategist")
        debate_scout = _create_debate_node(self.llm, "scout")

        workflow = StateGraph(AdvisorState)

        workflow.add_node("Analyst", analyst_node)
        workflow.add_node("Strategist", strategist_node)
        workflow.add_node("Scout", scout_node)
        workflow.add_node("debate_analyst", debate_analyst)
        workflow.add_node("debate_strategist", debate_strategist)
        workflow.add_node("debate_scout", debate_scout)
        workflow.add_node("debate_counter", _increment_debate_round)
        workflow.add_node("CIO", cio_node)

        workflow.add_edge(START, "Analyst")
        workflow.add_edge("Analyst", "Strategist")
        workflow.add_edge("Strategist", "Scout")
        workflow.add_edge("Scout", "debate_analyst")

        workflow.add_edge("debate_analyst", "debate_strategist")
        workflow.add_edge("debate_strategist", "debate_scout")
        workflow.add_edge("debate_scout", "debate_counter")

        workflow.add_conditional_edges(
            "debate_counter",
            _should_continue_debate,
            {
                "debate_analyst": "debate_analyst",
                "CIO": "CIO",
            },
        )

        workflow.add_edge("CIO", END)

        return workflow.compile()

    def propagate_advice(
        self,
        portfolio_summary: Dict[str, Any],
        tier1_reports: list,
        non_held_reports: list,
        progress_callback: Optional[Callable] = None,
        **config_overrides,
    ) -> Dict[str, Any]:
        """执行组合顾问分析

        Returns:
            包含 prescription, cio_verdict, debate history 的结果字典
        """
        init_state: AdvisorState = {
            "portfolio_summary": portfolio_summary,
            "tier1_reports": tier1_reports,
            "non_held_reports": non_held_reports,
            "analyst_assessment": "",
            "strategist_assessment": "",
            "scout_assessment": "",
            "advisor_debate_state": {
                "history": "",
                "current_speaker": "",
                "analyst_response": "",
                "strategist_response": "",
                "scout_response": "",
                "count": 0,
            },
            "prescription": [],
            "cio_verdict": "",
            "report_staleness_days": config_overrides.get(
                "report_staleness_days",
                self.config.get("report_staleness_days", 7),
            ),
            "max_single_weight": config_overrides.get(
                "max_single_weight",
                self.config.get("max_single_weight", 30.0),
            ),
            "max_industry_weight": config_overrides.get(
                "max_industry_weight",
                self.config.get("max_industry_weight", 50.0),
            ),
            "debate_rounds": config_overrides.get(
                "debate_rounds",
                self.config.get("advisor_debate_rounds", 2),
            ),
        }

        node_mapping = {
            "Analyst": "持仓分析师",
            "Strategist": "策略师",
            "Scout": "侦察兵",
            "debate_analyst": "辩论 - 分析师",
            "debate_strategist": "辩论 - 策略师",
            "debate_scout": "辩论 - 侦察兵",
            "debate_counter": None,
            "CIO": "CIO 裁决",
        }

        start_time = time.time()
        final_state = dict(init_state)

        for chunk in self.graph.stream(init_state, stream_mode="updates"):
            for node_name, node_update in chunk.items():
                if node_name.startswith("__"):
                    continue
                final_state.update(node_update)

                label = node_mapping.get(node_name)
                if label and progress_callback:
                    try:
                        progress_callback(label)
                    except Exception:
                        pass

        elapsed = time.time() - start_time
        logger.info(f"[AdvisorGraph] 完成，耗时 {elapsed:.1f}s")

        return {
            "prescription": final_state.get("prescription", []),
            "cio_verdict": final_state.get("cio_verdict", ""),
            "analyst_assessment": final_state.get("analyst_assessment", ""),
            "strategist_assessment": final_state.get("strategist_assessment", ""),
            "scout_assessment": final_state.get("scout_assessment", ""),
            "debate_history": final_state.get("advisor_debate_state", {}).get("history", ""),
            "elapsed_seconds": round(elapsed, 2),
        }
