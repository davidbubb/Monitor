"""Azure Application Insights error check module."""
from __future__ import annotations

import datetime

from monitor.results import CheckResult


def check_app_insights_errors(
    name: str,
    app_id: str,
    api_key: str,
    max_error_count: int = 0,
    hours: int = 24,
) -> CheckResult:
    """Query Azure Application Insights for exceptions/errors.

    Uses the Application Insights REST API directly so that no additional
    Azure SDK credential setup is required beyond a read-only API key.

    Parameters
    ----------
    name:
        Human-readable name for this check.
    app_id:
        The Application Insights application ID (found in API Access settings).
    api_key:
        A read-only Application Insights API key.
    max_error_count:
        Maximum number of errors/exceptions that are acceptable.
        Set to 0 to fail if any errors exist.
    hours:
        Look-back window in hours (default: 24).

    Returns
    -------
    CheckResult
        ``passed=True`` when the error count is <= *max_error_count*.
    """
    try:
        import requests  # noqa: PLC0415

        end_time = datetime.datetime.now(datetime.timezone.utc)
        start_time = end_time - datetime.timedelta(hours=hours)
        timespan = (
            f"{start_time.strftime('%Y-%m-%dT%H:%M:%SZ')}/"
            f"{end_time.strftime('%Y-%m-%dT%H:%M:%SZ')}"
        )

        query = (
            "exceptions | summarize error_count = count() "
            "| project error_count"
        )

        url = (
            f"https://api.applicationinsights.io/v1/apps/{app_id}/query"
        )
        headers = {"x-api-key": api_key}
        params = {"query": query, "timespan": timespan}

        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        rows = data.get("tables", [{}])[0].get("rows", [])
        error_count = int(rows[0][0]) if rows else 0

        if error_count > max_error_count:
            return CheckResult(
                name=name,
                passed=False,
                message=(
                    f"Found {error_count} error(s) in the past {hours}h; "
                    f"maximum allowed is {max_error_count}."
                ),
                details={"error_count": error_count, "hours": hours},
            )

        return CheckResult(
            name=name,
            passed=True,
            message=(
                f"Found {error_count} error(s) in the past {hours}h "
                f"(threshold: {max_error_count})."
            ),
            details={"error_count": error_count, "hours": hours},
        )

    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            name=name,
            passed=False,
            message=f"App Insights check failed: {exc}",
        )
