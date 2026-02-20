"""FTP folder contents check module."""
from __future__ import annotations

import ftplib

from monitor.results import CheckResult


def check_ftp_folder(
    name: str,
    host: str,
    username: str,
    password: str,
    path: str = "/",
    port: int = 21,
    expected_min_files: int = 1,
    use_tls: bool = False,
) -> CheckResult:
    """Connect to an FTP server and check the contents of a directory.

    Parameters
    ----------
    name:
        Human-readable name for this check.
    host:
        FTP server hostname or IP address.
    username:
        FTP username.
    password:
        FTP password.
    path:
        Remote directory path to inspect.
    port:
        FTP port (default: 21).
    expected_min_files:
        Minimum number of files that must be present in *path*.
    use_tls:
        When ``True``, use FTP_TLS instead of plain FTP.

    Returns
    -------
    CheckResult
        ``passed=True`` when *path* contains at least *expected_min_files*
        entries.
    """
    try:
        ftp_class = ftplib.FTP_TLS if use_tls else ftplib.FTP
        with ftp_class() as ftp:
            ftp.connect(host=host, port=port, timeout=30)
            ftp.login(user=username, passwd=password)
            if use_tls:
                ftp.prot_p()  # type: ignore[attr-defined]
            entries = ftp.nlst(path)

        file_count = len(entries)

        if file_count < expected_min_files:
            return CheckResult(
                name=name,
                passed=False,
                message=(
                    f"FTP path '{path}' contains {file_count} entry/entries; "
                    f"expected at least {expected_min_files}."
                ),
                details={"path": path, "file_count": file_count},
            )

        return CheckResult(
            name=name,
            passed=True,
            message=(
                f"FTP path '{path}' contains {file_count} entry/entries."
            ),
            details={"path": path, "file_count": file_count},
        )

    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            name=name,
            passed=False,
            message=f"FTP check failed: {exc}",
        )
