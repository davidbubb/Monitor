"""Main DevOps Monitor runner."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from monitor.checks.app_insights_check import check_app_insights_errors
from monitor.checks.ftp_check import check_ftp_folder
from monitor.checks.function_check import check_azure_function
from monitor.checks.queue_check import check_storage_queue
from monitor.checks.sql_check import check_sql
from monitor.checks.vm_log_check import check_vm_log
from monitor.checks.vm_process_check import check_vm_process
from monitor.results import CheckResult


def run_checks(config: dict[str, Any]) -> list[CheckResult]:
    """Execute all configured checks and return their results.

    Parameters
    ----------
    config:
        Dictionary loaded from ``config.json``.

    Returns
    -------
    list[CheckResult]
        Results for every configured check in the order they were run.
    """
    results: list[CheckResult] = []

    for cfg in config.get("sql_checks", []):
        results.append(
            check_sql(
                name=cfg["name"],
                connection_string=cfg["connection_string"],
                query=cfg["query"],
                expected_min_rows=cfg.get("expected_min_rows", 1),
            )
        )

    for cfg in config.get("azure_function_checks", []):
        results.append(
            check_azure_function(
                name=cfg["name"],
                function_url=cfg["function_url"],
                function_key=cfg.get("function_key"),
                expected_status_code=cfg.get("expected_status_code", 200),
            )
        )

    for cfg in config.get("app_insights_checks", []):
        results.append(
            check_app_insights_errors(
                name=cfg["name"],
                app_id=cfg["app_id"],
                api_key=cfg["api_key"],
                max_error_count=cfg.get("max_error_count", 0),
                hours=cfg.get("hours", 24),
            )
        )

    for cfg in config.get("storage_queue_checks", []):
        results.append(
            check_storage_queue(
                name=cfg["name"],
                connection_string=cfg["connection_string"],
                queue_name=cfg["queue_name"],
                max_message_count=cfg.get("max_message_count", 100),
            )
        )

    for cfg in config.get("ftp_checks", []):
        results.append(
            check_ftp_folder(
                name=cfg["name"],
                host=cfg["host"],
                port=cfg.get("port", 21),
                username=cfg["username"],
                password=cfg["password"],
                path=cfg.get("path", "/"),
                expected_min_files=cfg.get("expected_min_files", 1),
                use_tls=cfg.get("use_tls", False),
            )
        )

    for cfg in config.get("vm_log_checks", []):
        results.append(
            check_vm_log(
                name=cfg["name"],
                hostname=cfg["hostname"],
                port=cfg.get("port", 22),
                username=cfg["username"],
                password=cfg.get("password"),
                key_file=cfg.get("key_file"),
                known_hosts_file=cfg.get("known_hosts_file"),
                log_path=cfg["log_path"],
                search_text=cfg["search_text"],
                expect_text_absent=cfg.get("expect_text_absent", False),
            )
        )

    for cfg in config.get("vm_process_checks", []):
        results.append(
            check_vm_process(
                name=cfg["name"],
                hostname=cfg["hostname"],
                port=cfg.get("port", 22),
                username=cfg["username"],
                password=cfg.get("password"),
                key_file=cfg.get("key_file"),
                known_hosts_file=cfg.get("known_hosts_file"),
                process_name=cfg["process_name"],
            )
        )

    return results


def print_results(results: list[CheckResult]) -> None:
    """Print a formatted summary of all check results to stdout."""
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)

    for result in results:
        print(result)

    print()
    print(f"Results: {passed} passed, {failed} failed out of {len(results)} check(s).")


def main(config_path: str = "config.json") -> int:
    """Entry point.

    Parameters
    ----------
    config_path:
        Path to the JSON configuration file.

    Returns
    -------
    int
        Exit code: 0 if all checks passed, 1 if any check failed.
    """
    path = Path(config_path)
    if not path.exists():
        print(f"ERROR: Configuration file not found: {config_path}", file=sys.stderr)
        return 1

    with path.open(encoding="utf-8") as fh:
        config = json.load(fh)

    results = run_checks(config)
    print_results(results)

    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    cfg = sys.argv[1] if len(sys.argv) > 1 else "config.json"
    sys.exit(main(cfg))
