"""Tests for the App Insights check module."""
from unittest.mock import MagicMock, patch

from monitor.checks.app_insights_check import check_app_insights_errors


def _mock_response(error_count):
    resp = MagicMock()
    resp.json.return_value = {
        "tables": [{"rows": [[error_count]]}]
    }
    resp.raise_for_status = MagicMock()
    return resp


def test_app_insights_passes_no_errors():
    with patch("requests.get", return_value=_mock_response(0)):
        result = check_app_insights_errors(
            name="Test AI",
            app_id="app123",
            api_key="key123",
            max_error_count=0,
        )

    assert result.passed is True
    assert result.details["error_count"] == 0


def test_app_insights_fails_errors_exceed_threshold():
    with patch("requests.get", return_value=_mock_response(5)):
        result = check_app_insights_errors(
            name="Test AI",
            app_id="app123",
            api_key="key123",
            max_error_count=0,
        )

    assert result.passed is False
    assert result.details["error_count"] == 5


def test_app_insights_passes_within_threshold():
    with patch("requests.get", return_value=_mock_response(3)):
        result = check_app_insights_errors(
            name="Test AI",
            app_id="app123",
            api_key="key123",
            max_error_count=5,
        )

    assert result.passed is True


def test_app_insights_empty_rows():
    resp = MagicMock()
    resp.json.return_value = {"tables": [{"rows": []}]}
    resp.raise_for_status = MagicMock()

    with patch("requests.get", return_value=resp):
        result = check_app_insights_errors(
            name="Test AI",
            app_id="app123",
            api_key="key123",
            max_error_count=0,
        )

    assert result.passed is True
    assert result.details["error_count"] == 0


def test_app_insights_fails_on_exception():
    with patch("requests.get", side_effect=Exception("API error")):
        result = check_app_insights_errors(
            name="Test AI",
            app_id="app123",
            api_key="key123",
        )

    assert result.passed is False
    assert "API error" in result.message
