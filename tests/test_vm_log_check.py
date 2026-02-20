"""Tests for the VM log check module."""
from unittest.mock import MagicMock, patch

from monitor.checks.vm_log_check import check_vm_log, _quote


def _make_ssh_client(stdout_data: str):
    channel = MagicMock()

    stdout = MagicMock()
    stdout.read.return_value = stdout_data.encode()

    client = MagicMock()
    client.exec_command.return_value = (MagicMock(), stdout, MagicMock())
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    return client


def test_vm_log_text_found_passes_when_expected():
    client = _make_ssh_client("INFO: started\nERROR: something failed\n")

    with patch("paramiko.SSHClient", return_value=client):
        result = check_vm_log(
            name="Test Log",
            hostname="myvm.azure.com",
            username="azureuser",
            log_path="/var/log/app.log",
            search_text="ERROR",
            expect_text_absent=False,
        )

    assert result.passed is True
    assert result.details["text_found"] is True
    assert result.details["match_count"] == 1


def test_vm_log_text_absent_passes_when_expected_absent():
    client = _make_ssh_client("INFO: started\nINFO: running fine\n")

    with patch("paramiko.SSHClient", return_value=client):
        result = check_vm_log(
            name="Test Log",
            hostname="myvm.azure.com",
            username="azureuser",
            log_path="/var/log/app.log",
            search_text="ERROR",
            expect_text_absent=True,
        )

    assert result.passed is True
    assert result.details["text_found"] is False


def test_vm_log_text_found_fails_when_expected_absent():
    client = _make_ssh_client("ERROR: critical failure\n")

    with patch("paramiko.SSHClient", return_value=client):
        result = check_vm_log(
            name="Test Log",
            hostname="myvm.azure.com",
            username="azureuser",
            log_path="/var/log/app.log",
            search_text="ERROR",
            expect_text_absent=True,
        )

    assert result.passed is False
    assert result.details["text_found"] is True


def test_vm_log_text_not_found_fails_when_expected_present():
    client = _make_ssh_client("INFO: all good\n")

    with patch("paramiko.SSHClient", return_value=client):
        result = check_vm_log(
            name="Test Log",
            hostname="myvm.azure.com",
            username="azureuser",
            log_path="/var/log/app.log",
            search_text="ERROR",
            expect_text_absent=False,
        )

    assert result.passed is False
    assert result.details["text_found"] is False


def test_vm_log_fails_on_exception():
    with patch("paramiko.SSHClient", side_effect=Exception("no route to host")):
        result = check_vm_log(
            name="Test Log",
            hostname="myvm.azure.com",
            username="azureuser",
            log_path="/var/log/app.log",
            search_text="ERROR",
        )

    assert result.passed is False
    assert "no route to host" in result.message


def test_quote_simple():
    assert _quote("/var/log/app.log") == "'/var/log/app.log'"


def test_quote_with_single_quote():
    assert _quote("path/with'quote") == "'path/with'\\''quote'"
