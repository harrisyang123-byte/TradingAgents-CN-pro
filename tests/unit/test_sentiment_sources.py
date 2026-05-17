import asyncio
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from tradingagents.agents.analysts.sources import REGISTRY, get_enabled_sources


@pytest.mark.unit
class TestSourceRegistry:

    def test_registry_contains_all_sources(self):
        expected = {"eastmoney", "eastmoney_comment", "wechat_mp",
                    "xueqiu", "tonghuashun", "xiaohongshu"}
        assert expected.issubset(set(REGISTRY.keys()))

    def test_get_enabled_sources_filters(self):
        sources = get_enabled_sources(["eastmoney"])
        assert len(sources) == 1
        assert sources[0].name == "eastmoney"

    def test_get_enabled_sources_unknown_skipped(self):
        sources = get_enabled_sources(["eastmoney", "nonexistent"])
        assert len(sources) == 1


@pytest.mark.unit
class TestEastMoneySource:

    def test_skips_non_a_share(self):
        sources = get_enabled_sources(["eastmoney"])
        result = asyncio.run(sources[0].fetch(["AAPL"]))
        assert "AAPL" not in result or len(result.get("AAPL", MagicMock()).items) == 0

    def test_fetch_a_share(self, monkeypatch):
        mock_df = pd.DataFrame({
            "概念名称": ["白酒", "消费"],
            "热度": [1000, 500],
            "时间": ["2025-01-15", "2025-01-15"],
        })
        mock_ak = MagicMock()
        mock_ak.stock_hot_keyword_em.return_value = mock_df
        monkeypatch.setattr("importlib.import_module", lambda name: mock_ak if name == "akshare" else __import__(name))

        sources = get_enabled_sources(["eastmoney"])
        result = asyncio.run(sources[0].fetch(["600519.SH"]))
        report = result["600519.SH"]
        assert len(report.items) == 2
        assert "白酒" in report.items[0].title


@pytest.mark.unit
class TestXueqiuSource:

    def test_skips_non_a_share(self):
        sources = get_enabled_sources(["xueqiu"])
        result = asyncio.run(sources[0].fetch(["0700.HK"]))
        report = result.get("0700.HK")
        assert report is not None
        assert len(report.items) == 0

    def test_fetch_with_mock(self, monkeypatch):
        mock_df = pd.DataFrame({
            "股票代码": ["SH600519", "SZ000858"],
            "股票简称": ["贵州茅台", "五粮液"],
            "关注": [100000, 50000],
            "最新价": [1800.0, 160.0],
        })
        mock_ak = MagicMock()
        mock_ak.stock_hot_tweet_xq.return_value = mock_df
        mock_ak.stock_hot_follow_xq.return_value = mock_df
        mock_ak.stock_hot_deal_xq.return_value = mock_df
        monkeypatch.setattr("importlib.import_module", lambda name: mock_ak if name == "akshare" else __import__(name))

        sources = get_enabled_sources(["xueqiu"])
        result = asyncio.run(sources[0].fetch(["600519.SH"]))
        report = result["600519.SH"]
        assert len(report.items) == 3
        assert "雪球" in report.items[0].title


@pytest.mark.unit
class TestTonghuashunSource:

    def test_skips_non_a_share(self):
        sources = get_enabled_sources(["tonghuashun"])
        result = asyncio.run(sources[0].fetch(["AAPL"]))
        report = result.get("AAPL")
        assert report is not None
        assert len(report.items) == 0


@pytest.mark.unit
class TestXiaohongshuSource:

    def test_service_unreachable(self):
        sources = get_enabled_sources(["xiaohongshu"])
        result = asyncio.run(sources[0].fetch(["600519.SH"]))
        report = result["600519.SH"]
        assert "未启动" in report.summary or "unreachable" in report.summary.lower()
