"""Azure VM log file reader and text search module."""
from __future__ import annotations

from monitor.results import CheckResult


def check_vm_log(
    name: str,
    hostname: str,
    username: str,
    log_path: str,
    search_text: str,
    port: int = 22,
    password: str | None = None,
    key_file: str | None = None,
    known_hosts_file: str | None = None,
    expect_text_absent: bool = False,
    connect_timeout: int = 30,
) -> CheckResult:
    """SSH into an Azure VM, read a log file, and search for text.

    Parameters
    ----------
    name:
        Human-readable name for this check.
    hostname:
        VM hostname or IP address.
    username:
        SSH username.
    log_path:
        Absolute path to the log file on the remote VM.
    search_text:
        Text to search for in the log file.
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
    expect_text_absent:
        When ``True``, the check **passes** only when *search_text* is
        **not** found in the log (e.g., checking that no errors exist).
        When ``False``, the check passes when *search_text* **is** found.
    connect_timeout:
        SSH connection timeout in seconds.

    Returns
    -------
    CheckResult
        Result according to the *expect_text_absent* flag.
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

            command = f"cat {_quote(log_path)}"
            _, stdout, _ = client.exec_command(command)
            log_contents = stdout.read().decode(errors="replace")
        finally:
            client.close()

        text_found = search_text in log_contents
        match_count = log_contents.count(search_text)

        if expect_text_absent:
            passed = not text_found
            if passed:
                message = (
                    f"Search text '{search_text}' not found in '{log_path}' "
                    "(as expected)."
                )
            else:
                message = (
                    f"Search text '{search_text}' found {match_count} "
                    f"time(s) in '{log_path}'."
                )
        else:
            passed = text_found
            if passed:
                message = (
                    f"Search text '{search_text}' found {match_count} "
                    f"time(s) in '{log_path}'."
                )
            else:
                message = (
                    f"Search text '{search_text}' not found in '{log_path}'."
                )

        return CheckResult(
            name=name,
            passed=passed,
            message=message,
            details={
                "log_path": log_path,
                "search_text": search_text,
                "text_found": text_found,
                "match_count": match_count,
            },
        )

    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            name=name,
            passed=False,
            message=f"VM log check failed: {exc}",
        )


def _quote(path: str) -> str:
    """Return *path* wrapped in single quotes with internal quotes escaped."""
    return "'" + path.replace("'", "'\\''") + "'"
