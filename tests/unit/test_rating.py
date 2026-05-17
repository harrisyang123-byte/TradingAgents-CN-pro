import pytest

from tradingagents.agents.utils.rating import parse_rating


@pytest.mark.unit
class TestRating:

    def test_parse_buy(self):
        assert parse_rating("I recommend to Buy this stock") == "Buy"

    def test_parse_strong_buy(self):
        assert parse_rating("Strong Buy recommendation") == "Buy"

    def test_parse_sell(self):
        assert parse_rating("Sell immediately") == "Sell"

    def test_parse_strong_sell(self):
        assert parse_rating("Strong sell signal") == "Sell"

    def test_parse_hold(self):
        assert parse_rating("Hold for now") == "Hold"

    def test_parse_neutral(self):
        assert parse_rating("Neutral outlook") == "Hold"

    def test_parse_overweight(self):
        assert parse_rating("Overweight position") == "Overweight"

    def test_parse_underweight(self):
        assert parse_rating("Underweight recommendation") == "Underweight"

    def test_parse_empty_returns_default(self):
        assert parse_rating("") == "Hold"
        assert parse_rating("", default="Sell") == "Sell"

    def test_parse_no_match_returns_default(self):
        assert parse_rating("no rating keywords here") == "Hold"

    def test_parse_case_insensitive(self):
        assert parse_rating("BUY NOW") == "Buy"
        assert parse_rating("SELL ALL") == "Sell"
