"""Shared model catalog used by CLI prompts and lightweight validation."""

from __future__ import annotations

from typing import Dict, List, Tuple

ModelOption = Tuple[str, str]
ProviderModeOptions = Dict[str, Dict[str, List[ModelOption]]]


_GLM_MODELS: Dict[str, List[ModelOption]] = {
    "quick": [
        ("GLM-5-Turbo - 快速，可切换思考模式", "glm-5-turbo"),
        ("GLM-4.7 - 上一代旗舰", "glm-4.7"),
        ("GLM-4.5-Air - 轻量级", "glm-4.5-air"),
        ("GLM-4-Flash - 免费额度", "glm-4-flash"),
        ("Custom model ID", "custom"),
    ],
    "deep": [
        ("GLM-5.1 - 最新旗舰, 204K ctx", "glm-5.1"),
        ("GLM-5 - 旗舰, 204K ctx", "glm-5"),
        ("GLM-4.7 - 上一代旗舰", "glm-4.7"),
        ("GLM-4-Plus - 增强版", "glm-4-plus"),
        ("Custom model ID", "custom"),
    ],
}


_QWEN_MODELS: Dict[str, List[ModelOption]] = {
    "quick": [
        ("Qwen 3.6 Flash - 最新快速版", "qwen3.6-flash"),
        ("Qwen 3.5 Flash - 上一代快速版", "qwen3.5-flash"),
        ("Qwen Turbo - 经济实惠", "qwen-turbo"),
        ("Custom model ID", "custom"),
    ],
    "deep": [
        ("Qwen 3.6 Plus - 旗舰版", "qwen3.6-plus"),
        ("Qwen 3.5 Plus - 上一代旗舰", "qwen3.5-plus"),
        ("Qwen 3 Max - Agent 和工具使用优化", "qwen3-max"),
        ("Qwen Max - 通用旗舰", "qwen-max"),
        ("Custom model ID", "custom"),
    ],
}


_MINIMAX_MODELS: Dict[str, List[ModelOption]] = {
    "quick": [
        ("MiniMax-M2.7-highspeed - 快速版, ~100 TPS", "MiniMax-M2.7-highspeed"),
        ("MiniMax-M2.5-highspeed - 上一代快速版", "MiniMax-M2.5-highspeed"),
        ("Custom model ID", "custom"),
    ],
    "deep": [
        ("MiniMax-M2.7 - 旗舰, 204K ctx", "MiniMax-M2.7"),
        ("MiniMax-M2.5 - 上一代旗舰", "MiniMax-M2.5"),
        ("Custom model ID", "custom"),
    ],
}


MODEL_OPTIONS: ProviderModeOptions = {
    "openai": {
        "quick": [
            ("GPT-5.4 Mini - 快速, 强编码和工具调用", "gpt-5.4-mini"),
            ("GPT-5.4 Nano - 最经济", "gpt-5.4-nano"),
            ("GPT-4.1 Mini - 上一代快速版", "gpt-4.1-mini"),
            ("GPT-4o Mini - 经典快速版", "gpt-4o-mini"),
            ("Custom model ID", "custom"),
        ],
        "deep": [
            ("GPT-5.5 - 最新旗舰, 1M context", "gpt-5.5"),
            ("GPT-5.4 - 上一代旗舰, 性价比高", "gpt-5.4"),
            ("GPT-5.2 - 推理优化", "gpt-5.2"),
            ("o4-mini - 推理模型", "o4-mini"),
            ("GPT-4o - 经典通用", "gpt-4o"),
            ("Custom model ID", "custom"),
        ],
    },
    "anthropic": {
        "quick": [
            ("Claude Sonnet 4.6 - 速度与智能平衡", "claude-sonnet-4-6"),
            ("Claude Haiku 4.5 - 最快", "claude-haiku-4-5"),
            ("Claude Sonnet 4.5 - 上一代高性能", "claude-sonnet-4-5"),
            ("Custom model ID", "custom"),
        ],
        "deep": [
            ("Claude Opus 4.7 - 最新旗舰", "claude-opus-4-7"),
            ("Claude Opus 4.6 - 旗舰智能", "claude-opus-4-6"),
            ("Claude Opus 4.5 - 上一代旗舰", "claude-opus-4-5"),
            ("Claude Sonnet 4.6 - 平衡选择", "claude-sonnet-4-6"),
            ("Custom model ID", "custom"),
        ],
    },
    "google": {
        "quick": [
            ("Gemini 3 Flash - 最新快速版 (preview)", "gemini-3-flash-preview"),
            ("Gemini 2.5 Flash - 稳定快速", "gemini-2.5-flash"),
            ("Gemini 3.1 Flash Lite - 最经济 (GA)", "gemini-3.1-flash-lite"),
            ("Custom model ID", "custom"),
        ],
        "deep": [
            ("Gemini 3.1 Pro - 推理优先 (preview)", "gemini-3.1-pro-preview"),
            ("Gemini 3 Flash - 最新快速版 (preview)", "gemini-3-flash-preview"),
            ("Gemini 2.5 Pro - 稳定专业版", "gemini-2.5-pro"),
            ("Custom model ID", "custom"),
        ],
    },
    "xai": {
        "quick": [
            ("Grok 4.20 (Non-Reasoning)", "grok-4.20-non-reasoning"),
            ("Grok 4 Fast (Non-Reasoning)", "grok-4-fast-non-reasoning"),
            ("Custom model ID", "custom"),
        ],
        "deep": [
            ("Grok 4.20 (Reasoning) - 最新推理模型", "grok-4.20-reasoning"),
            ("Grok 4 Fast (Reasoning)", "grok-4-fast-reasoning"),
            ("Custom model ID", "custom"),
        ],
    },
    "deepseek": {
        "quick": [
            ("DeepSeek V4 Flash - 最新快速版", "deepseek-v4-flash"),
            ("DeepSeek V3.2 Chat", "deepseek-chat"),
            ("Custom model ID", "custom"),
        ],
        "deep": [
            ("DeepSeek V4 Pro - 最新旗舰", "deepseek-v4-pro"),
            ("DeepSeek V3.2 Reasoner", "deepseek-reasoner"),
            ("DeepSeek V3.2 Chat", "deepseek-chat"),
            ("Custom model ID", "custom"),
        ],
    },
    "qwen": _QWEN_MODELS,
    "qwen-cn": _QWEN_MODELS,
    "glm": _GLM_MODELS,
    "glm-cn": _GLM_MODELS,
    "minimax": _MINIMAX_MODELS,
    "minimax-cn": _MINIMAX_MODELS,
    "openrouter": {
        "quick": [("Custom model ID", "custom")],
        "deep": [("Custom model ID", "custom")],
    },
    "aihubmix": {
        "quick": [
            ("GPT-4o Mini", "gpt-4o-mini"),
            ("Custom model ID", "custom"),
        ],
        "deep": [
            ("GPT-4o", "gpt-4o"),
            ("Custom model ID", "custom"),
        ],
    },
    "ollama": {
        "quick": [
            ("Qwen3:latest (8B)", "qwen3:latest"),
            ("llama3.1", "llama3.1"),
            ("Custom model ID", "custom"),
        ],
        "deep": [
            ("Qwen3:latest (8B)", "qwen3:latest"),
            ("llama3.1", "llama3.1"),
            ("Custom model ID", "custom"),
        ],
    },
    "custom_openai": {
        "quick": [("Custom model ID", "custom")],
        "deep": [("Custom model ID", "custom")],
    },
}


def get_model_options(provider: str, mode: str) -> List[ModelOption]:
    return MODEL_OPTIONS[provider.lower()][mode]


def get_known_models() -> Dict[str, List[str]]:
    return {
        provider: sorted(
            {
                value
                for options in mode_options.values()
                for _, value in options
                if value != "custom"
            }
        )
        for provider, mode_options in MODEL_OPTIONS.items()
    }
