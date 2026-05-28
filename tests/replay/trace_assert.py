"""Assertions for Harness Trace replay tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_trace(path: str | Path) -> dict[str, Any]:
    trace_path = Path(path)
    text = trace_path.read_text(encoding="utf-8")
    if trace_path.suffix == ".jsonl":
        line = next((ln for ln in reversed(text.splitlines()) if ln.strip()), "{}")
        return json.loads(line)
    if trace_path.suffix == ".json":
        return json.loads(text)
    return {"raw_text": text, "loaded_rule_ids": _extract_rule_ids(text)}


def _extract_rule_ids(text: str) -> list[str]:
    import re

    return sorted(set(re.findall(r"RULE-[A-Z0-9-]+-[0-9]+", text)))


def rule_ids(trace: dict[str, Any]) -> set[str]:
    found: set[str] = set()
    for key in ["selected_rule_ids", "loaded_rule_ids", "applied_rule_ids"]:
        ids = trace.get(key)
        if isinstance(ids, list):
            found.update(str(item) for item in ids)
    if found:
        return found
    raw = trace.get("raw_text", "")
    if isinstance(raw, str):
        return set(_extract_rule_ids(raw))
    return set()


def applied_rule_ids(trace: dict[str, Any]) -> set[str]:
    ids = trace.get("applied_rule_ids")
    if isinstance(ids, list):
        return {str(item) for item in ids}
    return set()


def loaded_rule_ids(trace: dict[str, Any]) -> set[str]:
    ids = trace.get("loaded_rule_ids")
    if isinstance(ids, list):
        return {str(item) for item in ids}
    return set()


def loaded_file_paths(trace: dict[str, Any]) -> set[str]:
    loaded = trace.get("loaded_files")
    if not isinstance(loaded, list):
        return set()
    return {str(item.get("path", "")) for item in loaded if isinstance(item, dict) and item.get("path")}


def check_trace(trace: dict[str, Any], expected: dict[str, Any]) -> list[dict[str, str]]:
    found = rule_ids(trace)
    loaded = loaded_rule_ids(trace)
    applied = applied_rule_ids(trace)
    loaded_paths = loaded_file_paths(trace)
    results: list[dict[str, str]] = []

    for rule_id in expected.get("must_include_rule_ids", []) or []:
        results.append({
            "section": "Harness Trace Check",
            "status": "PASS" if rule_id in found else "FAIL",
            "item": str(rule_id),
        })

    for rule_id in expected.get("must_not_include_rule_ids", []) or []:
        results.append({
            "section": "Harness Trace Check",
            "status": "PASS" if rule_id not in found else "FAIL",
            "item": f"not {rule_id}",
        })

    for rule_id in expected.get("must_include_loaded_rule_ids", []) or []:
        results.append({
            "section": "Harness Trace Check",
            "status": "PASS" if rule_id in loaded else "FAIL",
            "item": f"loaded {rule_id}",
        })

    for rule_id in expected.get("must_include_applied_rule_ids", []) or []:
        results.append({
            "section": "Harness Trace Check",
            "status": "PASS" if rule_id in applied else "FAIL",
            "item": f"applied {rule_id}",
        })

    for path in expected.get("must_include_loaded_files", []) or []:
        results.append({
            "section": "Harness Trace Check",
            "status": "PASS" if path in loaded_paths else "FAIL",
            "item": f"loaded file {path}",
        })

    allowed_confidence = expected.get("trace_confidence_in") or []
    if allowed_confidence:
        confidence = str(trace.get("trace_confidence", ""))
        results.append({
            "section": "Harness Trace Check",
            "status": "PASS" if confidence in allowed_confidence else "FAIL",
            "item": f"trace_confidence in {allowed_confidence}",
        })

    if expected.get("must_verify_spec_evidence"):
        verification = trace.get("verification", {})
        verified = isinstance(verification, dict) and verification.get("all_applied_evidence_verified") is True
        results.append({
            "section": "Harness Trace Check",
            "status": "PASS" if verified else "FAIL",
            "item": "Spec Evidence verified against loaded files",
        })

    return results
