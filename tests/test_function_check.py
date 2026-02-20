"""Tests for the Azure Function check module."""
from unittest.mock import MagicMock, patch

from monitor.checks.function_check import check_azure_function


def _mock_response(status_code):
    resp = MagicMock()
    resp.status_code = status_code
    return resp


def test_function_check_passes_200():
    with patch("requests.get", return_value=_mock_response(200)):
        result = check_azure_function(
            name="Test Function",
            function_url="https://example.com/api/func",
            expected_status_code=200,
        )

    assert result.passed is True
    assert result.details["status_code"] == 200


def test_function_check_fails_non_200():
    with patch("requests.get", return_value=_mock_response(500)):
        result = check_azure_function(
            name="Test Function",
            function_url="https://example.com/api/func",
            expected_status_code=200,
        )

    assert result.passed is False
    assert result.details["status_code"] == 500


def test_function_check_with_key_sets_header():
    with patch("requests.get", return_value=_mock_response(200)) as mock_get:
        check_azure_function(
            name="Test Function",
            function_url="https://example.com/api/func",
            function_key="secret-key",
        )
    _, kwargs = mock_get.call_args
    assert kwargs["headers"]["x-functions-key"] == "secret-key"


def test_function_check_fails_on_exception():
    with patch("requests.get", side_effect=Exception("timeout")):
        result = check_azure_function(
            name="Test Function",
            function_url="https://example.com/api/func",
        )

    assert result.passed is False
    assert "timeout" in result.message
