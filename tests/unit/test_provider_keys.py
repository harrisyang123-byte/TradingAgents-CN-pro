import pytest

from tradingagents.llm_clients.provider_keys import (
    normalize_provider_key,
    env_key_for_provider,
    default_backend_url,
)


@pytest.mark.unit
class TestProviderKeys:

    def test_normalize_none(self):
        assert normalize_provider_key(None) == ""

    def test_normalize_empty(self):
        assert normalize_provider_key("") == ""

    def test_normalize_case_insensitive(self):
        assert normalize_provider_key("DASHSCOPE") == "qwen"

    def test_normalize_chinese_alibaba(self):
        assert normalize_provider_key("百炼") == "qwen"

    def test_normalize_chinese_zhipu(self):
        assert normalize_provider_key("智谱AI") == "glm"

    def test_normalize_xai(self):
        assert normalize_provider_key("xai") == "xai"

    def test_env_key_openai(self):
        assert env_key_for_provider("openai") == "OPENAI_API_KEY"

    def test_env_key_xai(self):
        assert env_key_for_provider("xai") == "XAI_API_KEY"

    def test_env_key_unknown(self):
        assert env_key_for_provider("nonexistent") == ""

    def test_default_url_all_known_providers(self):
        for provider in ["openai", "deepseek", "qwen", "glm", "xai"]:
            url = default_backend_url(provider)
            assert url.startswith("http"), f"{provider} has no URL"
