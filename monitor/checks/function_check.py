"""Azure Function invocation check module."""
from __future__ import annotations

from monitor.results import CheckResult


def check_azure_function(
    name: str,
    function_url: str,
    function_key: str | None = None,
    expected_status_code: int = 200,
    timeout: int = 30,
) -> CheckResult:
    """Invoke an Azure Function HTTP trigger and verify the response.

    Parameters
    ----------
    name:
        Human-readable name for this check.
    function_url:
        Full URL of the Azure Function HTTP trigger.
    function_key:
        Optional function-level or host-level API key.
    expected_status_code:
        HTTP status code that indicates a successful invocation.
    timeout:
        Request timeout in seconds.

    Returns
    -------
    CheckResult
        ``passed=True`` when the function responds with
        *expected_status_code*.
    """
    try:
        import requests  # noqa: PLC0415

        headers: dict[str, str] = {}
        if function_key:
            headers["x-functions-key"] = function_key

        response = requests.get(
            function_url,
            headers=headers,
            timeout=timeout,
        )
        status_code = response.status_code

        if status_code != expected_status_code:
            return CheckResult(
                name=name,
                passed=False,
                message=(
                    f"Function returned HTTP {status_code}; "
                    f"expected {expected_status_code}."
                ),
                details={"status_code": status_code},
            )

        return CheckResult(
            name=name,
            passed=True,
            message=f"Function invocation succeeded (HTTP {status_code}).",
            details={"status_code": status_code},
        )

    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            name=name,
            passed=False,
            message=f"Azure Function check failed: {exc}",
        )
