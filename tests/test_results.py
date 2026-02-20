"""Tests for the shared CheckResult dataclass."""
import pytest

from monitor.results import CheckResult


def test_check_result_passed_str():
    result = CheckResult(name="My Check", passed=True, message="All good.")
    assert str(result) == "[PASS] My Check: All good."


def test_check_result_failed_str():
    result = CheckResult(name="My Check", passed=False, message="Something went wrong.")
    assert str(result) == "[FAIL] My Check: Something went wrong."


def test_check_result_details_default():
    result = CheckResult(name="My Check", passed=True, message="OK")
    assert result.details == {}


def test_check_result_details_provided():
    result = CheckResult(
        name="My Check",
        passed=True,
        message="OK",
        details={"row_count": 5},
    )
    assert result.details == {"row_count": 5}
