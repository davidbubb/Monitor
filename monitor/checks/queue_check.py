"""Azure Storage Queue check module."""
from __future__ import annotations

from monitor.results import CheckResult


def check_storage_queue(
    name: str,
    connection_string: str,
    queue_name: str,
    max_message_count: int = 100,
) -> CheckResult:
    """Check the approximate message count of an Azure Storage queue.

    Parameters
    ----------
    name:
        Human-readable name for this check.
    connection_string:
        Azure Storage connection string.
    queue_name:
        Name of the queue to inspect.
    max_message_count:
        Maximum number of messages allowed before the check fails.

    Returns
    -------
    CheckResult
        ``passed=True`` when the queue message count is <=
        *max_message_count*.
    """
    try:
        from azure.storage.queue import QueueServiceClient  # noqa: PLC0415

        queue_client = QueueServiceClient.from_connection_string(
            connection_string
        ).get_queue_client(queue_name)

        properties = queue_client.get_queue_properties()
        message_count = properties.approximate_message_count

        if message_count > max_message_count:
            return CheckResult(
                name=name,
                passed=False,
                message=(
                    f"Queue '{queue_name}' has ~{message_count} message(s); "
                    f"maximum allowed is {max_message_count}."
                ),
                details={
                    "queue_name": queue_name,
                    "message_count": message_count,
                },
            )

        return CheckResult(
            name=name,
            passed=True,
            message=(
                f"Queue '{queue_name}' has ~{message_count} message(s) "
                f"(threshold: {max_message_count})."
            ),
            details={
                "queue_name": queue_name,
                "message_count": message_count,
            },
        )

    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            name=name,
            passed=False,
            message=f"Storage queue check failed: {exc}",
        )
