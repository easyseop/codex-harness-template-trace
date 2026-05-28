"""Assertions for replayed workflow output."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def load_output(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def check_output(output: str, expected: dict[str, Any]) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []

    for item in expected.get("must_include", []) or []:
        needle = str(item)
        results.append({
            "section": "Output Check",
            "status": "PASS" if needle in output else "FAIL",
            "item": needle,
        })

    for item in expected.get("must_not_include", []) or []:
        needle = str(item)
        results.append({
            "section": "Forbidden Pattern Check",
            "status": "PASS" if needle not in output else "FAIL",
            "item": needle,
        })

    if expected.get("must_include_no_explicit_spec_rule_found"):
        needle = "No explicit spec rule found."
        results.append({
            "section": "Output Check",
            "status": "PASS" if needle in output else "FAIL",
            "item": needle,
        })

    return results


def check_expected_result(output: str, expected: dict[str, Any]) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    status = expected.get("status")
    if status:
        needle = f"Status: {status}"
        results.append({
            "section": "Output Check",
            "status": "PASS" if needle in output else "FAIL",
            "item": needle,
        })

    for reason in expected.get("expected_fail_reasons", []) or expected.get("fail_reasons", []) or []:
        needle = str(reason)
        results.append({
            "section": "Output Check",
            "status": "PASS" if needle in output else "FAIL",
            "item": needle,
        })

    return results
