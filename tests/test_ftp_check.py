"""Tests for the FTP folder check module."""
from unittest.mock import MagicMock, patch

from monitor.checks.ftp_check import check_ftp_folder


def _ftp_with_entries(entries):
    ftp = MagicMock()
    ftp.nlst.return_value = entries
    ftp.__enter__ = MagicMock(return_value=ftp)
    ftp.__exit__ = MagicMock(return_value=False)
    return ftp


def test_ftp_check_passes_with_files():
    ftp = _ftp_with_entries(["file1.txt", "file2.txt"])

    with patch("ftplib.FTP", return_value=ftp):
        result = check_ftp_folder(
            name="Test FTP",
            host="ftp.example.com",
            username="user",
            password="pass",
            path="/uploads",
            expected_min_files=1,
        )

    assert result.passed is True
    assert result.details["file_count"] == 2


def test_ftp_check_fails_empty_folder():
    ftp = _ftp_with_entries([])

    with patch("ftplib.FTP", return_value=ftp):
        result = check_ftp_folder(
            name="Test FTP",
            host="ftp.example.com",
            username="user",
            password="pass",
            path="/uploads",
            expected_min_files=1,
        )

    assert result.passed is False
    assert result.details["file_count"] == 0


def test_ftp_check_passes_zero_expected():
    ftp = _ftp_with_entries([])

    with patch("ftplib.FTP", return_value=ftp):
        result = check_ftp_folder(
            name="Test FTP",
            host="ftp.example.com",
            username="user",
            password="pass",
            path="/uploads",
            expected_min_files=0,
        )

    assert result.passed is True


def test_ftp_check_fails_on_exception():
    with patch("ftplib.FTP", side_effect=Exception("connection refused")):
        result = check_ftp_folder(
            name="Test FTP",
            host="ftp.example.com",
            username="user",
            password="pass",
        )

    assert result.passed is False
    assert "connection refused" in result.message
