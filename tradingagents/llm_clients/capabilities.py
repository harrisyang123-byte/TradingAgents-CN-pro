"""Declarative per-model capability table for OpenAI-compatible providers.

Single place that knows which model IDs reject which API parameters or
require which structured-output method.  LLM client subclasses consult
``get_capabilities(model_name)`` instead of hardcoding model-name
``if`` ladders.

Ported from TG upstream v0.2.5, extended with Chinese-market model entries
(qwen, glm, qianfan series).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal


StructuredMethod = Literal[
    "function_calling",
    "json_mode",
    "json_schema",
    "none",
]


@dataclass(frozen=True)
class ModelCapabilities:
    """What an OpenAI-compatible model accepts at the API level."""

    supports_tool_choice: bool
    supports_json_mode: bool
    supports_json_schema: bool
    preferred_structured_method: StructuredMethod
    requires_reasoning_content_roundtrip: bool = False


_DEEPSEEK_THINKING = ModelCapabilities(
    supports_tool_choice=False,
    supports_json_mode=True,
    supports_json_schema=False,
    preferred_structured_method="function_calling",
    requires_reasoning_content_roundtrip=True,
)

_DEEPSEEK_CHAT = ModelCapabilities(
    supports_tool_choice=True,
    supports_json_mode=True,
    supports_json_schema=False,
    preferred_structured_method="function_calling",
)

_MINIMAX_THINKING = ModelCapabilities(
    supports_tool_choice=False,
    supports_json_mode=False,
    supports_json_schema=False,
    preferred_structured_method="function_calling",
)

_QWEN_DEFAULT = ModelCapabilities(
    supports_tool_choice=True,
    supports_json_mode=True,
    supports_json_schema=False,
    preferred_structured_method="function_calling",
)

_GLM_DEFAULT = ModelCapabilities(
    supports_tool_choice=True,
    supports_json_mode=True,
    supports_json_schema=False,
    preferred_structured_method="function_calling",
)

_QIANFAN_DEFAULT = ModelCapabilities(
    supports_tool_choice=True,
    supports_json_mode=False,
    supports_json_schema=False,
    preferred_structured_method="function_calling",
)

_DEFAULT = ModelCapabilities(
    supports_tool_choice=True,
    supports_json_mode=True,
    supports_json_schema=True,
    preferred_structured_method="function_calling",
)


_BY_ID: dict[str, ModelCapabilities] = {
    # DeepSeek
    "deepseek-chat": _DEEPSEEK_CHAT,
    "deepseek-reasoner": _DEEPSEEK_THINKING,
    "deepseek-v4-flash": _DEEPSEEK_THINKING,
    "deepseek-v4-pro": _DEEPSEEK_THINKING,
    # MiniMax
    "MiniMax-M2.7": _MINIMAX_THINKING,
    "MiniMax-M2.7-highspeed": _MINIMAX_THINKING,
    "MiniMax-M2.5": _MINIMAX_THINKING,
    "MiniMax-M2.5-highspeed": _MINIMAX_THINKING,
    "MiniMax-M2.1": _MINIMAX_THINKING,
    "MiniMax-M2.1-highspeed": _MINIMAX_THINKING,
    "MiniMax-M2": _MINIMAX_THINKING,
    # Qwen (通义千问)
    "qwen-turbo": _QWEN_DEFAULT,
    "qwen-plus": _QWEN_DEFAULT,
    "qwen-max": _QWEN_DEFAULT,
    "qwen-long": _QWEN_DEFAULT,
    "qwen3-235b-a22b": _QWEN_DEFAULT,
    # GLM (智谱)
    "glm-4": _GLM_DEFAULT,
    "glm-4-plus": _GLM_DEFAULT,
    "glm-4-flash": _GLM_DEFAULT,
    "glm-4-long": _GLM_DEFAULT,
    "glm-5-plus": _GLM_DEFAULT,
    "coding-glm-5.1": _GLM_DEFAULT,
    "coding-glm-5.1-free": _GLM_DEFAULT,
    # Qianfan (百度千帆)
    "ernie-4.5-8k": _QIANFAN_DEFAULT,
    "ernie-4.5-turbo-8k": _QIANFAN_DEFAULT,
    "ernie-speed": _QIANFAN_DEFAULT,
}

_BY_PATTERN: list[tuple[re.Pattern[str], ModelCapabilities]] = [
    (re.compile(r"^deepseek-v\d"), _DEEPSEEK_THINKING),
    (re.compile(r"^deepseek-reasoner"), _DEEPSEEK_THINKING),
    (re.compile(r"^MiniMax-M\d"), _MINIMAX_THINKING),
    (re.compile(r"^qwen"), _QWEN_DEFAULT),
    (re.compile(r"^glm-"), _GLM_DEFAULT),
    (re.compile(r"^coding-glm"), _GLM_DEFAULT),
    (re.compile(r"^ernie"), _QIANFAN_DEFAULT),
]


def get_capabilities(model_name: str) -> ModelCapabilities:
    """Resolve capabilities by exact ID, then pattern, then default."""
    if model_name in _BY_ID:
        return _BY_ID[model_name]
    for pattern, caps in _BY_PATTERN:
        if pattern.match(model_name):
            return caps
    return _DEFAULT
