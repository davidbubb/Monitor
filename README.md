# Monitor

A Python application to perform DevOps health checks.

## Features

- **SQL Database** – Connect to SQL databases and run queries; verify result-set size.
- **Azure Function** – Invoke an Azure Function HTTP trigger and verify the HTTP response code.
- **Azure App Insights** – Query Application Insights for exceptions in the past 24 hours (configurable).
- **Azure Storage Queue** – Check the approximate message count of an Azure Storage queue.
- **FTP Folder** – Connect to an FTP server and verify the contents of a remote directory.
- **VM Log File** – SSH into an Azure VM, read a log file, and search for specific text.
- **VM Process** – SSH into an Azure VM and verify that a named process is running.

## Quick Start

```bash
pip install -r requirements.txt
python -m monitor.runner config.json
```

The runner exits with code **0** if all checks pass, or **1** if any check fails.

## Configuration

Copy `config.json` and fill in your real values:

```json
{
  "sql_checks": [...],
  "azure_function_checks": [...],
  "app_insights_checks": [...],
  "storage_queue_checks": [...],
  "ftp_checks": [...],
  "vm_log_checks": [...],
  "vm_process_checks": [...]
}
```

See the bundled `config.json` for a complete example with all supported fields.

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```
