"""Tests for the main runner module."""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from monitor.results import CheckResult
from monitor.runner import main, run_checks


def _passing(name="Check"):
    return CheckResult(name=name, passed=True, message="OK")


def _failing(name="Check"):
    return CheckResult(name=name, passed=False, message="FAIL")


def test_run_checks_sql():
    config = {
        "sql_checks": [
            {
                "name": "SQL1",
                "connection_string": "fake",
                "query": "SELECT 1",
            }
        ]
    }
    with patch(
        "monitor.runner.check_sql",
        return_value=_passing("SQL1"),
    ) as mock:
        results = run_checks(config)

    mock.assert_called_once()
    assert len(results) == 1
    assert results[0].passed is True


def test_run_checks_all_types():
    config = {
        "sql_checks": [{"name": "s", "connection_string": "c", "query": "q"}],
        "azure_function_checks": [{"name": "f", "function_url": "u"}],
        "app_insights_checks": [{"name": "a", "app_id": "id", "api_key": "k"}],
        "storage_queue_checks": [
            {"name": "q", "connection_string": "c", "queue_name": "n"}
        ],
        "ftp_checks": [
            {"name": "ftp", "host": "h", "username": "u", "password": "p"}
        ],
        "vm_log_checks": [
            {
                "name": "log",
                "hostname": "h",
                "username": "u",
                "log_path": "/l",
                "search_text": "t",
            }
        ],
        "vm_process_checks": [
            {"name": "proc", "hostname": "h", "username": "u", "process_name": "p"}
        ],
    }

    with (
        patch("monitor.runner.check_sql", return_value=_passing()),
        patch("monitor.runner.check_azure_function", return_value=_passing()),
        patch("monitor.runner.check_app_insights_errors", return_value=_passing()),
        patch("monitor.runner.check_storage_queue", return_value=_passing()),
        patch("monitor.runner.check_ftp_folder", return_value=_passing()),
        patch("monitor.runner.check_vm_log", return_value=_passing()),
        patch("monitor.runner.check_vm_process", return_value=_passing()),
    ):
        results = run_checks(config)

    assert len(results) == 7
    assert all(r.passed for r in results)


def test_main_returns_0_all_pass(tmp_path):
    config = {}
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config))

    exit_code = main(str(config_file))
    assert exit_code == 0


def test_main_returns_1_when_check_fails(tmp_path):
    config = {
        "sql_checks": [{"name": "s", "connection_string": "c", "query": "q"}]
    }
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config))

    with patch("monitor.runner.check_sql", return_value=_failing()):
        exit_code = main(str(config_file))

    assert exit_code == 1


def test_main_returns_1_missing_config():
    exit_code = main("/nonexistent/path/config.json")
    assert exit_code == 1
