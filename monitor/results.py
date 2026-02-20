"""Shared CheckResult dataclass used across all check modules."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CheckResult:
    """Result of a single monitoring check."""

    name: str
    passed: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return f"[{status}] {self.name}: {self.message}"
