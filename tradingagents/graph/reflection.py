# TradingAgents/graph/reflection.py

from typing import Dict, Any
from langchain_openai import ChatOpenAI

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger
logger = get_logger("default")


class Reflector:
    """Handles reflection on decisions and updating memory."""

    def __init__(self, quick_thinking_llm: ChatOpenAI):
        """Initialize the reflector with an LLM."""
        self.quick_thinking_llm = quick_thinking_llm
        self.log_reflection_prompt = self._get_log_reflection_prompt()

    def _get_log_reflection_prompt(self) -> str:
        """Concise prompt for reflect_on_final_decision (Phase B log entries)."""
        return (
            "你是一位交易分析师，正在复盘自己过去的决策（现在已知实际结果）。\n"
            "用2-4句纯文本写出反思（不要使用列表、标题或markdown格式）。\n\n"
            "依次覆盖：\n"
            "1. 方向判断是否正确？（引用alpha数据）\n"
            "2. 投资论据中哪些成立、哪些失败？\n"
            "3. 一条可用于下次类似分析的具体教训。\n\n"
            "简洁精确。你的输出将被存入决策日志并在未来被其他分析师参考。"
        )

    def reflect_on_final_decision(
        self,
        final_decision: str,
        raw_return: float,
        alpha_return: float,
        benchmark_name: str = "沪深300",
    ) -> str:
        """Single reflection call on the final trade decision with outcome context."""
        messages = [
            ("system", self.log_reflection_prompt),
            (
                "human",
                (
                    f"原始收益: {raw_return:+.1%}\n"
                    f"相对 {benchmark_name} 的 Alpha: {alpha_return:+.1%}\n\n"
                    f"最终决策:\n{final_decision}"
                ),
            ),
        ]
        return self.quick_thinking_llm.invoke(messages).content

