"""SQL database check module."""
from __future__ import annotations

from monitor.results import CheckResult


def check_sql(
    name: str,
    connection_string: str,
    query: str,
    expected_min_rows: int = 1,
) -> CheckResult:
    """Connect to a SQL database, run *query*, and verify results.

    Parameters
    ----------
    name:
        Human-readable name for this check.
    connection_string:
        ODBC connection string for the target database.
    query:
        SQL query to execute.
    expected_min_rows:
        Minimum number of rows the result set must contain.
        Set to 0 to only verify that the query executes without error.

    Returns
    -------
    CheckResult
        ``passed=True`` when the query succeeds and returns at least
        *expected_min_rows* rows.
    """
    try:
        import pyodbc  # noqa: PLC0415

        with pyodbc.connect(connection_string, timeout=30) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            row_count = len(rows)

        if row_count < expected_min_rows:
            return CheckResult(
                name=name,
                passed=False,
                message=(
                    f"Query returned {row_count} row(s); "
                    f"expected at least {expected_min_rows}."
                ),
                details={"row_count": row_count},
            )

        return CheckResult(
            name=name,
            passed=True,
            message=f"Query returned {row_count} row(s).",
            details={"row_count": row_count},
        )

    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            name=name,
            passed=False,
            message=f"SQL check failed: {exc}",
        )
