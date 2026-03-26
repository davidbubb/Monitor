"""Tests for the VM process check module."""
from subprocess import CompletedProcess
from unittest.mock import MagicMock, patch

from monitor.checks.vm_process_check import (
    _build_timestamped_screenshot_path,
    _parse_tasklist_csv,
    _quote,
    check_vm_process,
)


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


def test_parse_tasklist_csv_with_rows():
    output = '"nginx.exe","1234","RDP-Tcp#2","2","8,192 K"\n'
    rows = _parse_tasklist_csv(output)
    assert len(rows) == 1
    assert rows[0]["Image Name"] == "nginx.exe"
    assert rows[0]["PID"] == "1234"


def test_parse_tasklist_csv_info_output():
    output = "INFO: No tasks are running which match the specified criteria.\n"
    rows = _parse_tasklist_csv(output)
    assert rows == []


def test_vm_process_rdp_passes_when_tasklist_finds_process():
    with (
        patch("monitor.checks.vm_process_check.platform.system", return_value="Windows"),
        patch("monitor.checks.vm_process_check.subprocess.Popen", return_value=MagicMock()),
        patch("monitor.checks.vm_process_check.time.sleep"),
        patch(
            "monitor.checks.vm_process_check._build_timestamped_screenshot_path",
            return_value="C:/tmp/rdp-shot_20260326_120000.png",
        ),
        patch("monitor.checks.vm_process_check._capture_screenshot_windows") as mock_shot,
        patch("monitor.checks.vm_process_check._run_cmd") as mock_run,
    ):
        mock_run.side_effect = [
            CompletedProcess(args=["cmdkey"], returncode=0, stdout="", stderr=""),
            CompletedProcess(
                args=["tasklist"],
                returncode=0,
                stdout='"myapp.exe","3321","RDP-Tcp#1","2","11,000 K"\n',
                stderr="",
            ),
            CompletedProcess(args=["cmdkey"], returncode=0, stdout="", stderr=""),
            CompletedProcess(args=["taskkill"], returncode=0, stdout="", stderr=""),
        ]

        result = check_vm_process(
            name="RDP Process",
            hostname="myvm.azure.com",
            username="domain\\user",
            password="secret",
            process_name="myapp.exe",
            protocol="rdp",
            screenshot_path="C:/tmp/rdp-shot.png",
        )

    assert result.passed is True
    assert result.details["protocol"] == "rdp"
    assert result.details["pids"] == ["3321"]
    assert result.details["screenshot_path"] == "C:/tmp/rdp-shot_20260326_120000.png"
    mock_shot.assert_called_once_with("C:/tmp/rdp-shot_20260326_120000.png")


def test_build_timestamped_screenshot_path_keeps_extension():
    with patch("monitor.checks.vm_process_check.datetime") as mock_datetime:
        mock_datetime.now.return_value.strftime.return_value = "20260326_120000"
        actual = _build_timestamped_screenshot_path("artifacts/rdp-check.png")

    assert actual == "artifacts\\rdp-check_20260326_120000.png"


def test_vm_process_rdp_fails_when_process_not_running():
    with (
        patch("monitor.checks.vm_process_check.platform.system", return_value="Windows"),
        patch("monitor.checks.vm_process_check.subprocess.Popen", return_value=MagicMock()),
        patch("monitor.checks.vm_process_check.time.sleep"),
        patch("monitor.checks.vm_process_check._run_cmd") as mock_run,
    ):
        mock_run.side_effect = [
            CompletedProcess(args=["cmdkey"], returncode=0, stdout="", stderr=""),
            CompletedProcess(
                args=["tasklist"],
                returncode=0,
                stdout="INFO: No tasks are running which match the specified criteria.\n",
                stderr="",
            ),
            CompletedProcess(args=["cmdkey"], returncode=0, stdout="", stderr=""),
            CompletedProcess(args=["taskkill"], returncode=0, stdout="", stderr=""),
        ]

        result = check_vm_process(
            name="RDP Process",
            hostname="myvm.azure.com",
            username="domain\\user",
            password="secret",
            process_name="myapp.exe",
            protocol="rdp",
        )

    assert result.passed is False
    assert result.details["protocol"] == "rdp"
    assert result.details["pids"] == []


def test_vm_process_rdp_requires_windows():
    with patch("monitor.checks.vm_process_check.platform.system", return_value="Linux"):
        result = check_vm_process(
            name="RDP Process",
            hostname="myvm.azure.com",
            username="domain\\user",
            password="secret",
            process_name="myapp.exe",
            protocol="rdp",
        )

    assert result.passed is False
    assert "Windows" in result.message


def test_vm_process_fails_on_unsupported_protocol():
    result = check_vm_process(
        name="Any Process",
        hostname="myvm.azure.com",
        username="user",
        process_name="myapp.exe",
        protocol="telnet",
    )
    assert result.passed is False
    assert "unsupported protocol" in result.message
