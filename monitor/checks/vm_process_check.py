"""Azure VM process running check module."""
from __future__ import annotations

import csv
from datetime import datetime
import platform
import subprocess
import tempfile
import time
from pathlib import Path

from monitor.results import CheckResult


def check_vm_process(
    name: str,
    hostname: str,
    username: str,
    process_name: str,
    port: int = 22,
    password: str | None = None,
    key_file: str | None = None,
    known_hosts_file: str | None = None,
    connect_timeout: int = 30,
    protocol: str = "ssh",
    screenshot_path: str | None = None,
    rdp_launch_wait_seconds: int = 6,
    close_rdp_on_finish: bool = True,
) -> CheckResult:
    """Verify that a named process is running on a VM.

    Parameters
    ----------
    name:
        Human-readable name for this check.
    hostname:
        VM hostname or IP address.
    username:
        SSH username.
    process_name:
        Name of the process to look for (matched using ``pgrep -x``).
    port:
        SSH port (default: 22).
    password:
        SSH password (used when *key_file* is not provided).
    key_file:
        Path to the private key file for SSH authentication.
    known_hosts_file:
        Path to a known_hosts file used for host key verification.
        When ``None`` the system default (``~/.ssh/known_hosts``) is loaded.
        The connection is rejected if the host key is not found.
    connect_timeout:
        SSH connection timeout in seconds (SSH mode only).
    protocol:
        Connection protocol for this check. Supported values are ``ssh``
        and ``rdp``.
    screenshot_path:
        Optional local path where a screenshot should be saved when using
        ``protocol='rdp'``.
    rdp_launch_wait_seconds:
        Seconds to wait after launching the RDP client before running the
        process query.
    close_rdp_on_finish:
        Whether to close ``mstsc.exe`` at the end of an RDP check.

    Returns
    -------
    CheckResult
        ``passed=True`` when at least one process with *process_name* is
        running on the VM.
    """
    protocol_normalized = protocol.strip().lower()
    if protocol_normalized == "ssh":
        return _check_vm_process_ssh(
            name=name,
            hostname=hostname,
            username=username,
            process_name=process_name,
            port=port,
            password=password,
            key_file=key_file,
            known_hosts_file=known_hosts_file,
            connect_timeout=connect_timeout,
        )

    if protocol_normalized == "rdp":
        return _check_vm_process_rdp(
            name=name,
            hostname=hostname,
            username=username,
            process_name=process_name,
            password=password,
            screenshot_path=screenshot_path,
            rdp_launch_wait_seconds=rdp_launch_wait_seconds,
            close_rdp_on_finish=close_rdp_on_finish,
        )

    return CheckResult(
        name=name,
        passed=False,
        message=(
            "VM process check failed: unsupported protocol "
            f"'{protocol}'. Use 'ssh' or 'rdp'."
        ),
    )


def _check_vm_process_ssh(
    name: str,
    hostname: str,
    username: str,
    process_name: str,
    port: int,
    password: str | None,
    key_file: str | None,
    known_hosts_file: str | None,
    connect_timeout: int,
) -> CheckResult:
    """SSH implementation of VM process check."""
    try:
        import paramiko  # noqa: PLC0415

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
        if known_hosts_file:
            client.load_host_keys(known_hosts_file)
        else:
            client.load_system_host_keys()
        try:
            client.connect(
                hostname=hostname,
                port=port,
                username=username,
                password=password,
                key_filename=key_file,
                timeout=connect_timeout,
                look_for_keys=key_file is None and password is None,
            )

            # pgrep -x matches the exact process name.
            # Exit code 0 means at least one matching process was found.
            command = f"pgrep -x {_quote(process_name)}"
            _, stdout, _ = client.exec_command(command)
            exit_status = stdout.channel.recv_exit_status()
            pids = stdout.read().decode().strip()
        finally:
            client.close()

        if exit_status == 0:
            pid_list = pids.split()
            return CheckResult(
                name=name,
                passed=True,
                message=(
                    f"Process '{process_name}' is running "
                    f"(PID(s): {', '.join(pid_list)})."
                ),
                details={
                    "process_name": process_name,
                    "pids": pid_list,
                },
            )

        return CheckResult(
            name=name,
            passed=False,
            message=f"Process '{process_name}' is NOT running.",
            details={"process_name": process_name, "pids": []},
        )

    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            name=name,
            passed=False,
            message=f"VM process check failed: {exc}",
        )


def _check_vm_process_rdp(
    name: str,
    hostname: str,
    username: str,
    process_name: str,
    password: str | None,
    screenshot_path: str | None,
    rdp_launch_wait_seconds: int,
    close_rdp_on_finish: bool,
) -> CheckResult:
    """RDP implementation that opens mstsc, checks process, and can screenshot."""
    if platform.system() != "Windows":
        return CheckResult(
            name=name,
            passed=False,
            message="RDP process checks are only supported on Windows.",
        )

    if not password:
        return CheckResult(
            name=name,
            passed=False,
            message="RDP process check requires a password.",
        )

    target = f"TERMSRV/{hostname}"
    rdp_process: subprocess.Popen[str] | None = None

    try:
        _run_cmd(["cmdkey", f"/generic:{target}", f"/user:{username}", f"/pass:{password}"])

        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".rdp", encoding="utf-8") as fh:
            fh.write(f"full address:s:{hostname}\n")
            fh.write(f"username:s:{username}\n")
            fh.write("prompt for credentials:i:0\n")
            rdp_file = fh.name

        rdp_process = subprocess.Popen(["mstsc", rdp_file])
        if rdp_launch_wait_seconds > 0:
            time.sleep(rdp_launch_wait_seconds)

        tasklist = _run_cmd(
            [
                "tasklist",
                "/S",
                hostname,
                "/U",
                username,
                "/P",
                password,
                "/FI",
                f"IMAGENAME eq {process_name}",
                "/FO",
                "CSV",
                "/NH",
            ]
        )
        process_rows = _parse_tasklist_csv(tasklist.stdout)

        screenshot_saved_to: str | None = None
        screenshot_error: str | None = None
        if screenshot_path:
            try:
                screenshot_saved_to = _build_timestamped_screenshot_path(screenshot_path)
                _capture_screenshot_windows(screenshot_saved_to)
            except Exception as exc:  # noqa: BLE001
                screenshot_error = str(exc)

        if process_rows:
            pids = [row.get("PID", "") for row in process_rows if row.get("PID")]
            details = {
                "protocol": "rdp",
                "process_name": process_name,
                "pids": pids,
                "matched_rows": process_rows,
            }
            if screenshot_saved_to:
                details["screenshot_path"] = screenshot_saved_to
            if screenshot_error:
                details["screenshot_error"] = screenshot_error

            return CheckResult(
                name=name,
                passed=True,
                message=(
                    f"Process '{process_name}' is running (via RDP/tasklist). "
                    f"PID(s): {', '.join(pids) if pids else 'unknown'}."
                ),
                details=details,
            )

        details = {
            "protocol": "rdp",
            "process_name": process_name,
            "pids": [],
        }
        if screenshot_saved_to:
            details["screenshot_path"] = screenshot_saved_to
        if screenshot_error:
            details["screenshot_error"] = screenshot_error

        return CheckResult(
            name=name,
            passed=False,
            message=f"Process '{process_name}' is NOT running (via RDP/tasklist).",
            details=details,
        )

    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            name=name,
            passed=False,
            message=f"VM process RDP check failed: {exc}",
        )
    finally:
        try:
            _run_cmd(["cmdkey", f"/delete:{target}"], check=False)
        except Exception:  # noqa: BLE001
            pass

        if close_rdp_on_finish:
            try:
                _run_cmd(["taskkill", "/IM", "mstsc.exe", "/F"], check=False)
            except Exception:  # noqa: BLE001
                pass

        if rdp_process is not None:
            try:
                rdp_process.terminate()
            except Exception:  # noqa: BLE001
                pass


def _run_cmd(args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run a command and return a text-mode completed process."""
    return subprocess.run(args, capture_output=True, text=True, check=check)


def _parse_tasklist_csv(output: str) -> list[dict[str, str]]:
    """Parse tasklist /FO CSV /NH output into a list of process rows."""
    clean_lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not clean_lines:
        return []

    first_line = clean_lines[0].lower()
    if first_line.startswith("info:"):
        return []

    rows: list[dict[str, str]] = []
    reader = csv.reader(clean_lines)
    for row in reader:
        if len(row) < 2:
            continue
        rows.append(
            {
                "Image Name": row[0],
                "PID": row[1],
                "Session Name": row[2] if len(row) > 2 else "",
                "Session#": row[3] if len(row) > 3 else "",
                "Mem Usage": row[4] if len(row) > 4 else "",
            }
        )

    return rows


def _capture_screenshot_windows(destination_path: str) -> None:
    """Capture the current desktop screenshot to *destination_path* on Windows."""
    destination = Path(destination_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    ps_script = (
        "Add-Type -AssemblyName System.Windows.Forms;"
        "Add-Type -AssemblyName System.Drawing;"
        "$bounds=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds;"
        "$bmp=New-Object System.Drawing.Bitmap($bounds.Width,$bounds.Height);"
        "$graphics=[System.Drawing.Graphics]::FromImage($bmp);"
        "$graphics.CopyFromScreen($bounds.Location,[System.Drawing.Point]::Empty,$bounds.Size);"
        f"$bmp.Save('{_escape_powershell_single_quoted(str(destination))}');"
        "$graphics.Dispose();"
        "$bmp.Dispose();"
    )
    _run_cmd(["powershell", "-NoProfile", "-Command", ps_script])


def _build_timestamped_screenshot_path(base_path: str) -> str:
    """Build a timestamped screenshot path based on *base_path*.

    Example:
    ``artifacts/rdp-check.png`` -> ``artifacts/rdp-check_20260326_154500.png``
    """
    path = Path(base_path)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if path.suffix:
        filename = f"{path.stem}_{timestamp}{path.suffix}"
    else:
        filename = f"{path.name}_{timestamp}"

    return str(path.with_name(filename))


def _escape_powershell_single_quoted(value: str) -> str:
    """Escape a value so it can be safely used in PowerShell single quotes."""
    return value.replace("'", "''")


def _quote(value: str) -> str:
    """Return *value* wrapped in single quotes with internal quotes escaped."""
    return "'" + value.replace("'", "'\\''") + "'"
