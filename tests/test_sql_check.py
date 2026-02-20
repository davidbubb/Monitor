"""Tests for the SQL check module."""
import sys
from unittest.mock import MagicMock, patch

from monitor.checks.sql_check import check_sql


def _make_cursor(rows):
    cursor = MagicMock()
    cursor.fetchall.return_value = rows
    return cursor


def _make_connection(cursor):
    conn = MagicMock()
    conn.cursor.return_value = cursor
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    return conn


def _pyodbc_module(conn):
    """Return a mock pyodbc module whose connect() returns *conn*."""
    mock_pyodbc = MagicMock()
    mock_pyodbc.connect.return_value = conn
    return mock_pyodbc


def test_sql_check_passes_with_enough_rows():
    rows = [("value1",), ("value2",)]
    cursor = _make_cursor(rows)
    conn = _make_connection(cursor)

    with patch.dict(sys.modules, {"pyodbc": _pyodbc_module(conn)}):
        result = check_sql(
            name="Test SQL",
            connection_string="fake_conn",
            query="SELECT 1",
            expected_min_rows=1,
        )

    assert result.passed is True
    assert result.details["row_count"] == 2


def test_sql_check_fails_with_too_few_rows():
    cursor = _make_cursor([])
    conn = _make_connection(cursor)

    with patch.dict(sys.modules, {"pyodbc": _pyodbc_module(conn)}):
        result = check_sql(
            name="Test SQL",
            connection_string="fake_conn",
            query="SELECT 1",
            expected_min_rows=1,
        )

    assert result.passed is False
    assert result.details["row_count"] == 0


def test_sql_check_passes_zero_expected():
    cursor = _make_cursor([])
    conn = _make_connection(cursor)

    with patch.dict(sys.modules, {"pyodbc": _pyodbc_module(conn)}):
        result = check_sql(
            name="Test SQL",
            connection_string="fake_conn",
            query="SELECT 1",
            expected_min_rows=0,
        )

    assert result.passed is True


def test_sql_check_fails_on_exception():
    mock_pyodbc = MagicMock()
    mock_pyodbc.connect.side_effect = Exception("connection error")

    with patch.dict(sys.modules, {"pyodbc": mock_pyodbc}):
        result = check_sql(
            name="Test SQL",
            connection_string="fake_conn",
            query="SELECT 1",
        )

    assert result.passed is False
    assert "connection error" in result.message

