"""Tests for the VM process check module."""
from unittest.mock import MagicMock, patch

from monitor.checks.vm_process_check import check_vm_process, _quote


def _make_ssh_client(exit_status: int, stdout_data: str = ""):
    channel = MagicMock()
    channel.recv_exit_status.return_value = exit_status

    stdout = MagicMock()
    stdout.read.return_value = stdout_data.encode()
    stdout.channel = channel

    client = MagicMock()
    client.exec_command.return_value = (MagicMock(), stdout, MagicMock())
    return client


def test_vm_process_passes_when_running():
    client = _make_ssh_client(exit_status=0, stdout_data="1234\n5678\n")

    with patch("paramiko.SSHClient", return_value=client):
        result = check_vm_process(
            name="Test Process",
            hostname="myvm.azure.com",
            username="azureuser",
            process_name="nginx",
        )

    assert result.passed is True
    assert "1234" in result.details["pids"]
    assert "5678" in result.details["pids"]


def test_vm_process_fails_when_not_running():
    client = _make_ssh_client(exit_status=1)

    with patch("paramiko.SSHClient", return_value=client):
        result = check_vm_process(
            name="Test Process",
            hostname="myvm.azure.com",
            username="azureuser",
            process_name="nginx",
        )

    assert result.passed is False
    assert result.details["pids"] == []


def test_vm_process_fails_on_exception():
    with patch("paramiko.SSHClient", side_effect=Exception("auth failed")):
        result = check_vm_process(
            name="Test Process",
            hostname="myvm.azure.com",
            username="azureuser",
            process_name="nginx",
        )

    assert result.passed is False
    assert "auth failed" in result.message


def test_quote_simple():
    assert _quote("nginx") == "'nginx'"


def test_quote_with_single_quote():
    assert _quote("it's a process") == "'it'\\''s a process'"
