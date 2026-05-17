import threading
from unittest.mock import MagicMock

import pytest

from tradingagents.utils.stats_handler import StatsCallbackHandler


@pytest.mark.unit
class TestStatsHandler:

    def test_initial_stats_zero(self):
        h = StatsCallbackHandler()
        stats = h.get_stats()
        assert stats["llm_calls"] == 0
        assert stats["tool_calls"] == 0
        assert stats["tokens_in"] == 0
        assert stats["tokens_out"] == 0

    def test_on_llm_start_increments(self):
        h = StatsCallbackHandler()
        for _ in range(3):
            h.on_llm_start({}, [])
        assert h.get_stats()["llm_calls"] == 3

    def test_on_chat_model_start_increments(self):
        h = StatsCallbackHandler()
        h.on_chat_model_start({}, [[]])
        assert h.get_stats()["llm_calls"] == 1

    def test_on_tool_start_increments(self):
        h = StatsCallbackHandler()
        h.on_tool_start({}, "input")
        h.on_tool_start({}, "input2")
        assert h.get_stats()["tool_calls"] == 2

    def test_on_llm_end_extracts_tokens(self):
        from langchain_core.messages import AIMessage

        h = StatsCallbackHandler()
        msg = AIMessage(content="test")
        msg.usage_metadata = {"input_tokens": 100, "output_tokens": 50}
        gen = MagicMock()
        gen.message = msg
        response = MagicMock()
        response.generations = [[gen]]
        h.on_llm_end(response)
        stats = h.get_stats()
        assert stats["tokens_in"] == 100
        assert stats["tokens_out"] == 50

    def test_on_llm_end_no_metadata_safe(self):
        h = StatsCallbackHandler()
        response = MagicMock()
        response.generations = [[]]
        h.on_llm_end(response)
        assert h.get_stats()["tokens_in"] == 0

    def test_thread_safety(self):
        h = StatsCallbackHandler()
        def call_n_times(n):
            for _ in range(n):
                h.on_llm_start({}, [])

        threads = [threading.Thread(target=call_n_times, args=(100,)) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert h.get_stats()["llm_calls"] == 1000
