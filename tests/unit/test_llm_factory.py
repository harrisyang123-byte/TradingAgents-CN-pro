import pytest

from tradingagents.llm_clients.factory import create_llm_client, _OPENAI_COMPATIBLE


@pytest.mark.unit
class TestLLMFactory:

    def test_create_openai_client(self):
        client = create_llm_client("openai", "gpt-4o-mini")
        assert type(client).__name__ == "OpenAIClient"

    def test_create_deepseek_client(self):
        client = create_llm_client("deepseek", "deepseek-chat")
        assert type(client).__name__ == "OpenAIClient"
        assert client.provider == "deepseek"

    def test_create_xai_client(self):
        client = create_llm_client("xai", "grok-4.20-reasoning")
        assert type(client).__name__ == "OpenAIClient"
        assert client.provider == "xai"

    def test_create_qwen_via_dashscope_alias(self):
        client = create_llm_client("dashscope", "qwen-plus")
        assert type(client).__name__ == "OpenAIClient"

    def test_create_google_client(self):
        client = create_llm_client("google", "gemini-2.0-flash")
        assert type(client).__name__ == "GoogleClient"

    def test_create_anthropic_client(self):
        client = create_llm_client("anthropic", "claude-sonnet-4-20250514")
        assert type(client).__name__ == "AnthropicClient"

    def test_create_azure_client(self):
        client = create_llm_client("azure", "gpt-4o")
        assert type(client).__name__ == "AzureOpenAIClient"

    def test_unsupported_provider_raises(self):
        with pytest.raises(ValueError, match="Unsupported"):
            create_llm_client("nonexistent", "model")

    def test_all_openai_compatible_route_correctly(self):
        for provider in _OPENAI_COMPATIBLE:
            client = create_llm_client(provider, "test-model")
            assert type(client).__name__ == "OpenAIClient"
