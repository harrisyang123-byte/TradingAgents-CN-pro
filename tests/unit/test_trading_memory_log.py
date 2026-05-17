import pytest

from tradingagents.agents.utils.trading_memory_log import TradingMemoryLog


@pytest.mark.unit
class TestTradingMemoryLog:

    def _make_log(self, tmp_path, max_entries=None):
        path = tmp_path / "test_memory.md"
        config = {"memory_log_path": str(path)}
        if max_entries is not None:
            config["memory_log_max_entries"] = max_entries
        return TradingMemoryLog(config), path

    def test_store_decision_creates_file(self, tmp_path):
        log, path = self._make_log(tmp_path)
        log.store_decision("600519.SH", "2025-01-15", "Buy - strong fundamentals")
        assert path.exists()
        content = path.read_text()
        assert "600519.SH" in content
        assert "pending" in content

    def test_store_decision_dedup(self, tmp_path):
        log, path = self._make_log(tmp_path)
        log.store_decision("600519.SH", "2025-01-15", "Buy")
        log.store_decision("600519.SH", "2025-01-15", "Buy again")
        entries = log.load_entries()
        assert len(entries) == 1

    def test_load_entries_empty(self, tmp_path):
        log, _ = self._make_log(tmp_path)
        assert log.load_entries() == []

    def test_load_entries_parses_fields(self, tmp_path):
        log, _ = self._make_log(tmp_path)
        log.store_decision("600519.SH", "2025-01-15", "Buy recommendation")
        entries = log.load_entries()
        assert len(entries) == 1
        e = entries[0]
        assert e["date"] == "2025-01-15"
        assert e["ticker"] == "600519.SH"
        assert e["rating"] == "Buy"
        assert e["pending"] is True

    def test_get_pending_entries(self, tmp_path):
        log, _ = self._make_log(tmp_path)
        log.store_decision("600519.SH", "2025-01-15", "Buy")
        log.store_decision("000858.SZ", "2025-01-16", "Hold")
        pending = log.get_pending_entries()
        assert len(pending) == 2

    def test_update_with_outcome(self, tmp_path):
        log, path = self._make_log(tmp_path)
        log.store_decision("600519.SH", "2025-01-15", "Buy signal")
        log.update_with_outcome(
            "600519.SH", "2025-01-15",
            raw_return=0.042, alpha_return=0.021,
            holding_days=5, reflection="Good call",
        )
        entries = log.load_entries()
        assert len(entries) == 1
        e = entries[0]
        assert e["pending"] is False
        assert e["raw"] == "+4.2%"
        assert e["alpha"] == "+2.1%"
        assert e["reflection"] == "Good call"

    def test_get_past_context_same_ticker(self, tmp_path):
        log, _ = self._make_log(tmp_path)
        log.store_decision("600519.SH", "2025-01-15", "Buy")
        log.update_with_outcome(
            "600519.SH", "2025-01-15",
            raw_return=0.05, alpha_return=0.02,
            holding_days=5, reflection="Worked well",
        )
        ctx = log.get_past_context("600519.SH")
        assert "600519.SH" in ctx
        assert "Worked well" in ctx

    def test_get_past_context_empty(self, tmp_path):
        log, _ = self._make_log(tmp_path)
        assert log.get_past_context("600519.SH") == ""

    def test_batch_update_with_outcomes(self, tmp_path):
        log, _ = self._make_log(tmp_path)
        log.store_decision("600519.SH", "2025-01-15", "Buy")
        log.store_decision("000858.SZ", "2025-01-15", "Sell")
        log.store_decision("000001.SZ", "2025-01-15", "Hold")
        log.batch_update_with_outcomes([
            {"trade_date": "2025-01-15", "ticker": "600519.SH",
             "raw_return": 0.03, "alpha_return": 0.01, "holding_days": 5,
             "reflection": "OK"},
            {"trade_date": "2025-01-15", "ticker": "000858.SZ",
             "raw_return": -0.02, "alpha_return": -0.04, "holding_days": 5,
             "reflection": "Bad"},
        ])
        entries = log.load_entries()
        resolved = [e for e in entries if not e["pending"]]
        pending = [e for e in entries if e["pending"]]
        assert len(resolved) == 2
        assert len(pending) == 1

    def test_rotation_drops_oldest(self, tmp_path):
        log, _ = self._make_log(tmp_path, max_entries=2)
        for i in range(3):
            log.store_decision("600519.SH", f"2025-01-{15+i}", "Buy")
            log.update_with_outcome(
                "600519.SH", f"2025-01-{15+i}",
                raw_return=0.01 * i, alpha_return=0.005 * i,
                holding_days=5, reflection=f"Reflection {i}",
            )
        entries = log.load_entries()
        resolved = [e for e in entries if not e["pending"]]
        assert len(resolved) == 2

    def test_no_log_path_is_noop(self):
        log = TradingMemoryLog({})
        log.store_decision("X", "2025-01-01", "Buy")
        assert log.load_entries() == []
        assert log.get_pending_entries() == []
        assert log.get_past_context("X") == ""
