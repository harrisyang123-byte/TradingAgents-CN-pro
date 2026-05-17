import pytest

from cli.main import MessageBuffer


@pytest.mark.unit
class TestMessageBuffer:

    def test_init_for_analysis_subset(self):
        mb = MessageBuffer()
        mb.init_for_analysis(["market", "news"])
        assert "Market Analyst" in mb.agent_status
        assert "News Analyst" in mb.agent_status
        assert "Social Analyst" not in mb.agent_status
        assert "Fundamentals Analyst" not in mb.agent_status
        assert "Bull Researcher" in mb.agent_status
        assert "Portfolio Manager" in mb.agent_status

    def test_init_for_analysis_full(self):
        mb = MessageBuffer()
        mb.init_for_analysis(["market", "social", "news", "fundamentals"])
        assert len(mb.agent_status) == 12
        assert "market_report" in mb.report_sections
        assert "sentiment_report" in mb.report_sections

    def test_report_sections_filtered(self):
        mb = MessageBuffer()
        mb.init_for_analysis(["market"])
        assert "market_report" in mb.report_sections
        assert "sentiment_report" not in mb.report_sections
        assert "investment_plan" in mb.report_sections

    def test_get_completed_reports_count_zero(self):
        mb = MessageBuffer()
        mb.init_for_analysis(["market", "news"])
        assert mb.get_completed_reports_count() == 0

    def test_get_completed_reports_count_increments(self):
        mb = MessageBuffer()
        mb.init_for_analysis(["market"])
        mb.report_sections["market_report"] = "test content"
        mb.agent_status["Market Analyst"] = "completed"
        assert mb.get_completed_reports_count() == 1

    def test_get_completed_reports_requires_both_conditions(self):
        mb = MessageBuffer()
        mb.init_for_analysis(["market"])
        mb.report_sections["market_report"] = "content"
        assert mb.get_completed_reports_count() == 0

    def test_processed_message_ids(self):
        mb = MessageBuffer()
        mb.init_for_analysis(["market"])
        assert len(mb._processed_message_ids) == 0
        mb._processed_message_ids.add("msg-1")
        assert "msg-1" in mb._processed_message_ids

    def test_init_clears_state(self):
        mb = MessageBuffer()
        mb.add_message("test", "content")
        mb.init_for_analysis(["market"])
        assert len(mb.messages) == 0
        assert mb.current_report is None
