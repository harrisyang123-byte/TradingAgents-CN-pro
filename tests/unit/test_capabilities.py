import pytest

from tradingagents.llm_clients.capabilities import get_capabilities, _DEFAULT


@pytest.mark.unit
class TestCapabilities:

    def test_deepseek_chat_supports_tool_choice(self):
        caps = get_capabilities("deepseek-chat")
        assert caps.supports_tool_choice is True

    def test_deepseek_reasoner_no_tool_choice(self):
        caps = get_capabilities("deepseek-reasoner")
        assert caps.supports_tool_choice is False

    def test_deepseek_reasoner_requires_roundtrip(self):
        caps = get_capabilities("deepseek-reasoner")
        assert caps.requires_reasoning_content_roundtrip is True

    def test_qwen_default(self):
        caps = get_capabilities("qwen-plus")
        assert caps.supports_tool_choice is True
        assert caps.preferred_structured_method == "function_calling"

    def test_glm_default(self):
        caps = get_capabilities("glm-4")
        assert caps.supports_tool_choice is True

    def test_unknown_model_returns_default(self):
        caps = get_capabilities("totally-unknown-model-xyz")
        assert caps is _DEFAULT

    def test_pattern_matching_deepseek_v4(self):
        caps = get_capabilities("deepseek-v4-something")
        assert caps.requires_reasoning_content_roundtrip is True

    def test_pattern_matching_qwen_wildcard(self):
        caps = get_capabilities("qwen-anything-new")
        assert caps.supports_tool_choice is True
        assert caps.preferred_structured_method == "function_calling"

    def test_exact_match_takes_precedence(self):
        caps = get_capabilities("deepseek-chat")
        assert caps.supports_tool_choice is True
        assert caps.requires_reasoning_content_roundtrip is False
