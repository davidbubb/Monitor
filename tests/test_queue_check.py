"""Tests for the Azure Storage Queue check module."""
from unittest.mock import MagicMock, patch

from monitor.checks.queue_check import check_storage_queue


def _mock_queue_client(message_count):
    properties = MagicMock()
    properties.approximate_message_count = message_count

    queue_client = MagicMock()
    queue_client.get_queue_properties.return_value = properties
    return queue_client


def test_queue_check_passes_within_threshold():
    queue_client = _mock_queue_client(10)
    service_client = MagicMock()
    service_client.get_queue_client.return_value = queue_client

    with (
        patch("azure.storage.blob.BlobServiceClient"),
        patch(
            "azure.storage.queue.QueueServiceClient.from_connection_string",
            return_value=service_client,
        ),
    ):
        result = check_storage_queue(
            name="Test Queue",
            connection_string="fake_conn",
            queue_name="my-queue",
            max_message_count=100,
        )

    assert result.passed is True
    assert result.details["message_count"] == 10


def test_queue_check_fails_exceeds_threshold():
    queue_client = _mock_queue_client(200)
    service_client = MagicMock()
    service_client.get_queue_client.return_value = queue_client

    with (
        patch("azure.storage.blob.BlobServiceClient"),
        patch(
            "azure.storage.queue.QueueServiceClient.from_connection_string",
            return_value=service_client,
        ),
    ):
        result = check_storage_queue(
            name="Test Queue",
            connection_string="fake_conn",
            queue_name="my-queue",
            max_message_count=100,
        )

    assert result.passed is False
    assert result.details["message_count"] == 200


def test_queue_check_fails_on_exception():
    with patch(
        "azure.storage.queue.QueueServiceClient.from_connection_string",
        side_effect=Exception("auth error"),
    ):
        result = check_storage_queue(
            name="Test Queue",
            connection_string="fake_conn",
            queue_name="my-queue",
        )

    assert result.passed is False
    assert "auth error" in result.message
