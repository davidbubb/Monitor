"""Azure VM process running check module."""
from __future__ import annotations

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
) -> CheckResult:
    """SSH into an Azure VM and verify that a named process is running.

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
        SSH connection timeout in seconds.

    Returns
    -------
    CheckResult
        ``passed=True`` when at least one process with *process_name* is
        running on the VM.
    """
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


def _quote(value: str) -> str:
    """Return *value* wrapped in single quotes with internal quotes escaped."""
    return "'" + value.replace("'", "'\\''") + "'"
