#!/usr/bin/env python3
"""Replay-test runner for Harness Trace assertions.

This runner does not execute the full Ouroboros workflow. It verifies a captured
stage replay using fixtures, expected trace rules, and expected output patterns.
Codex performs the actual stage replay from the workflow command reference; this
script keeps the mechanical assertions deterministic and cheap.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any
from datetime import datetime, timezone

from output_assert import check_expected_result, check_output, load_output
from trace_assert import applied_rule_ids, check_trace, load_trace, rule_ids


ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT / "tests" / "results"
EXECUTION_MODES = {"captured", "codex_mediated", "codex_cli"}
RULE_RE = re.compile(r"RULE-[A-Z0-9-]+-[0-9]+")


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if value in {"[]", ""}:
        return [] if value == "[]" else ""
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value.startswith("[") and value.endswith("]"):
        return json.loads(value.replace("'", '"'))
    return value.strip('"').strip("'")


def load_case(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore

        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except ModuleNotFoundError:
        return load_simple_yaml(path)


def dump_simple_yaml(value: Any, indent: int = 0) -> str:
    """Emit stable, readable YAML without requiring PyYAML."""

    lines: list[str] = []
    pad = " " * indent
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}{key}:")
                lines.append(dump_simple_yaml(item, indent + 2))
            else:
                lines.append(f"{pad}{key}: {format_yaml_scalar(item)}")
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}-")
                lines.append(dump_simple_yaml(item, indent + 2))
            else:
                lines.append(f"{pad}- {format_yaml_scalar(item)}")
    else:
        lines.append(f"{pad}{format_yaml_scalar(value)}")
    return "\n".join(lines)


def format_yaml_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text == "" or any(ch in text for ch in ":#[]{}*,&!|>'\"%@`"):
        return json.dumps(text, ensure_ascii=False)
    return text


def load_simple_yaml(path: Path) -> dict[str, Any]:
    """Parse the small YAML subset used by replay test cases.

    Supports top-level scalars, one-level nested dictionaries, and list values.
    Install PyYAML for full YAML support.
    """

    result: dict[str, Any] = {}
    current_key: str | None = None
    nested_key: str | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        if indent == 0 and ":" in stripped:
            key, value = stripped.split(":", 1)
            key = key.strip()
            value = value.strip()
            current_key = key
            nested_key = None
            result[key] = {} if value == "" else parse_scalar(value)
            continue

        if indent == 2 and current_key:
            container = result.setdefault(current_key, {})
            if stripped.startswith("- "):
                if not isinstance(container, list):
                    result[current_key] = []
                    container = result[current_key]
                container.append(parse_scalar(stripped[2:]))
            elif ":" in stripped:
                key, value = stripped.split(":", 1)
                key = key.strip()
                value = value.strip()
                nested_key = key
                if isinstance(container, dict):
                    container[key] = [] if value == "" else parse_scalar(value)
            continue

        if indent == 4 and current_key and nested_key:
            container = result.get(current_key, {})
            if isinstance(container, dict) and stripped.startswith("- "):
                items = container.setdefault(nested_key, [])
                if isinstance(items, list):
                    items.append(parse_scalar(stripped[2:]))

    return result


def resolve_path(path_value: str | None) -> Path | None:
    if not path_value:
        return None
    path = Path(path_value)
    return path if path.is_absolute() else ROOT / path


def sha256_file(path: Path | None) -> str:
    if not path or not path.exists() or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    return [str(value)] if str(value) else []


def rule_ids_from_text(text: str) -> set[str]:
    return set(RULE_RE.findall(text))


def rule_ids_in_file(path: Path | None) -> set[str]:
    if not path or not path.exists() or not path.is_file():
        return set()
    return rule_ids_from_text(path.read_text(encoding="utf-8", errors="ignore"))


def added_rule_ids_from_git_diff(path: Path | None) -> set[str]:
    if not path or not path.exists():
        return set()
    try:
        rel = relative(path)
        diff = subprocess.check_output(
            ["git", "diff", "--unified=0", "HEAD", "--", rel],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return set()

    added_lines = [
        line[1:]
        for line in diff.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]
    return rule_ids_from_text("\n".join(added_lines))


def expected_rule_ids(case_data: dict[str, Any]) -> set[str]:
    expected = case_data.get("expected_trace", {}) or {}
    ids: set[str] = set()
    for key in ["must_include_rule_ids", "must_include_loaded_rule_ids", "must_include_applied_rule_ids"]:
        ids.update(as_list(expected.get(key)))
    return ids


def changed_rule_inputs(
    case_data: dict[str, Any],
    changed_rule_files: list[str],
    changed_rule_ids: list[str],
) -> tuple[list[str], list[str]]:
    files = as_list(case_data.get("changed_rule_files")) + changed_rule_files
    ids = as_list(case_data.get("changed_rule_ids")) + changed_rule_ids
    return sorted(set(files)), sorted(set(ids))


def check_changed_rule_coverage(
    case_data: dict[str, Any],
    trace: dict[str, Any],
    changed_rule_files: list[str],
    changed_rule_ids: list[str],
) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    files, explicit_ids = changed_rule_inputs(case_data, changed_rule_files, changed_rule_ids)
    expected_ids = expected_rule_ids(case_data)
    actual_ids = rule_ids(trace)
    results: list[dict[str, str]] = []
    coverage: list[dict[str, Any]] = []

    for path_value in files:
        path = resolve_path(path_value)
        file_ids = sorted(rule_ids_in_file(path))
        added_ids = sorted(added_rule_ids_from_git_diff(path))
        checked_ids = sorted(set(explicit_ids) or set(added_ids))
        mode = "explicit_rule_ids" if explicit_ids else "git_added_rule_ids"

        if checked_ids:
            for rule_id in checked_ids:
                if explicit_ids and files:
                    results.append({
                        "section": "Harness Trace Check",
                        "status": "PASS" if rule_id in file_ids else "FAIL",
                        "item": f"changed rule exists in {path_value}: {rule_id}",
                    })
                results.append({
                    "section": "Harness Trace Check",
                    "status": "PASS" if rule_id in expected_ids else "FAIL",
                    "item": f"changed rule expected {rule_id} from {path_value}",
                })
                results.append({
                    "section": "Harness Trace Check",
                    "status": "PASS" if rule_id in actual_ids else "FAIL",
                    "item": f"changed rule traced {rule_id} from {path_value}",
                })
        elif file_ids:
            mode = "file_rule_presence"
            expected_overlap = sorted(set(file_ids) & expected_ids)
            actual_overlap = sorted(set(file_ids) & actual_ids)
            results.append({
                "section": "Harness Trace Check",
                "status": "PASS" if expected_overlap else "FAIL",
                "item": f"changed file expected at least one Rule ID from {path_value}",
            })
            results.append({
                "section": "Harness Trace Check",
                "status": "PASS" if actual_overlap else "FAIL",
                "item": f"changed file traced at least one Rule ID from {path_value}",
            })
        else:
            mode = "no_rule_ids_found"
            results.append({
                "section": "Harness Trace Check",
                "status": "FAIL",
                "item": f"changed rule file has no Rule IDs: {path_value}",
            })

        coverage.append({
            "path": path_value,
            "sha256": sha256_file(path),
            "file_rule_ids": file_ids,
            "git_added_rule_ids": added_ids,
            "explicit_rule_ids": explicit_ids,
            "checked_rule_ids": checked_ids,
            "coverage_mode": mode,
        })

    for rule_id in explicit_ids:
        if files:
            continue
        results.append({
            "section": "Harness Trace Check",
            "status": "PASS" if rule_id in expected_ids else "FAIL",
            "item": f"changed rule expected {rule_id}",
        })
        results.append({
            "section": "Harness Trace Check",
            "status": "PASS" if rule_id in actual_ids else "FAIL",
            "item": f"changed rule traced {rule_id}",
        })
        coverage.append({
            "path": "",
            "sha256": "",
            "file_rule_ids": [],
            "git_added_rule_ids": [],
            "explicit_rule_ids": explicit_ids,
            "checked_rule_ids": explicit_ids,
            "coverage_mode": "explicit_rule_ids",
        })

    return results, coverage


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return ""


def step_name(target_step: Any) -> str:
    return str(target_step or "").strip().lstrip("/")


def command_file_for_step(case_data: dict[str, Any]) -> Path | None:
    execution = case_data.get("execution", {}) or {}
    configured = execution.get("command_file")
    if configured:
        return resolve_path(configured)
    step = step_name(case_data.get("target_step"))
    if not step:
        return None
    candidate = ROOT / "commands" / f"{step}.md"
    return candidate if candidate.exists() else None


def make_run_id(test_id: str) -> tuple[str, str]:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}_{safe_name(test_id)}", timestamp


def run_dirs(test_id: str, run_id: str, run_dir_arg: str | None = None) -> tuple[Path, Path, Path]:
    if run_dir_arg:
        run_dir = resolve_path(run_dir_arg) or Path(run_dir_arg)
    else:
        run_dir = RESULTS_DIR / "runs" / run_id
    latest_dir = RESULTS_DIR / "latest" / safe_name(test_id)
    baseline_dir = RESULTS_DIR / "baseline" / safe_name(test_id)
    return run_dir, latest_dir, baseline_dir


def resolve_case(target_or_path: str, case: str | None) -> Path:
    candidate = Path(target_or_path)
    if candidate.exists():
        return candidate

    if case is None:
        raise SystemExit("Usage: replay_runner.py <case-file> OR <target_step> <case>")

    step = target_or_path.strip().lstrip("/")
    matches = sorted((ROOT / "tests" / "cases").glob(f"test_{step}_{case}.yaml"))
    if not matches:
        for path in sorted((ROOT / "tests" / "cases").glob("*.yaml")):
            data = load_case(path)
            target = str(data.get("target_step", "")).strip().lstrip("/")
            name = str(data.get("case", "")).strip()
            if target == step and name == case:
                matches.append(path)
        if not matches:
            raise SystemExit(f"No replay case found for step={step}, case={case}")
    if len(matches) > 1:
        names = ", ".join(str(path) for path in matches)
        raise SystemExit(f"Multiple replay cases matched: {names}")
    return matches[0]


def execution_mode(case_data: dict[str, Any], override: str | None) -> str:
    if override:
        return override
    execution = case_data.get("execution", {}) or {}
    mode = str(execution.get("mode", "captured"))
    if mode not in EXECUTION_MODES:
        raise SystemExit(f"Invalid execution mode: {mode}")
    return mode


def render(case_data: dict[str, Any], results: list[dict[str, str]]) -> str:
    lines = [
        "[Replay Test 결과]",
        f"테스트 ID: {case_data.get('test_id', '')}",
        f"대상 단계: {case_data.get('target_step', '')}",
        f"케이스: {case_data.get('case', '')}",
        "입력 Fixture:",
    ]
    for fixture in case_data.get("input_fixtures", []) or []:
        lines.append(f"- {fixture}")
    lines.append("")

    section_labels = {
        "Harness Trace Check": "하네스 추적 확인",
        "Output Check": "산출물 확인",
        "Forbidden Pattern Check": "금지 패턴 확인",
    }
    for section in ["Harness Trace Check", "Output Check", "Forbidden Pattern Check"]:
        lines.append(f"[{section_labels[section]}]")
        section_results = [item for item in results if item["section"] == section]
        if not section_results:
            lines.append("PASS - 기대값 없음")
        for item in section_results:
            lines.append(f"{item['status']} - {item['item']}")
        lines.append("")

    final = "PASS" if all(item["status"] == "PASS" for item in results) else "FAIL"
    lines.append(f"결과: {final}")
    return "\n".join(lines)


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def split_assertions(results: list[dict[str, str]], section: str) -> list[dict[str, str]]:
    return [item for item in results if item["section"] == section]


def extract_spec_evidence(output: str) -> str:
    for marker in ["[명세 근거]", "[Spec Evidence]"]:
        if marker in output:
            return marker + output.split(marker, 1)[1].strip()
    return "명시적인 명세 근거 블록이 actual output에 없습니다."


def render_trace_markdown(trace: dict[str, Any], output: str) -> str:
    lines = ["# 실제 Trace", ""]
    if trace:
        detected_rule_ids = sorted(rule_ids(trace))
        detected_applied_rule_ids = sorted(applied_rule_ids(trace))
        lines.extend([
            "## 하네스 추적",
            "",
            f"- workflow_step: {trace.get('workflow_step', '')}",
            f"- request_type: {trace.get('request_type', '')}",
            f"- trace_id: {trace.get('trace_id', '')}",
            f"- trace_status: {trace.get('trace_status', '')}",
            f"- trace_confidence: {trace.get('trace_confidence', '')}",
            f"- trace_reasons: {trace.get('trace_reasons', {})}",
            f"- selected_command_files: {trace.get('selected_command_files', [])}",
            f"- selected_reference_files: {trace.get('selected_reference_files', [])}",
            f"- selected_agent_files: {trace.get('selected_agent_files', [])}",
            f"- selected_rule_ids: {trace.get('selected_rule_ids', [])}",
            f"- loaded_rule_ids: {trace.get('loaded_rule_ids', [])}",
            f"- all_detected_rule_ids: {detected_rule_ids}",
            f"- applied_rule_ids: {detected_applied_rule_ids}",
            f"- selected_not_loaded: {trace.get('selected_not_loaded', [])}",
            "",
            "```json",
            json.dumps(trace, ensure_ascii=False, indent=2),
            "```",
            "",
        ])
    else:
        lines.extend(["## 하네스 추적", "", "구조화된 하네스 추적이 없습니다.", ""])

    lines.extend([
        "## 명세 근거",
        "",
        extract_spec_evidence(output),
        "",
    ])
    return "\n".join(lines)


def render_diff(expected_text: str, actual_text: str, expected_label: str, actual_label: str) -> str:
    diff = list(difflib.unified_diff(
        expected_text.splitlines(),
        actual_text.splitlines(),
        fromfile=expected_label,
        tofile=actual_label,
        lineterm="",
    ))
    if not diff:
        return "# Diff\n\nNo differences between expected and actual output.\n"
    return "# Diff\n\n```diff\n" + "\n".join(diff) + "\n```\n"


def render_summary(case_data: dict[str, Any], run_id: str, status: str, results: list[dict[str, str]]) -> str:
    failed = [item for item in results if item["status"] != "PASS"]
    lines = [
        "# Replay Test Summary",
        "",
        f"- Test ID: {case_data.get('test_id', '')}",
        f"- Target Step: {case_data.get('target_step', '')}",
        f"- Case: {case_data.get('case', '')}",
        f"- Run ID: {run_id}",
        f"- Status: {status}",
        f"- Assertions: {len(results)} total, {len(failed)} failed",
        "",
    ]
    if failed:
        lines.append("## Failed Assertions")
        lines.append("")
        for item in failed:
            lines.append(f"- {item['section']}: {item['item']}")
    else:
        lines.append("All replay assertions passed.")
    lines.append("")
    return "\n".join(lines)


def lineage_for(
    case_data: dict[str, Any],
    case_path: Path,
    run_id: str,
    timestamp: str,
    mode: str,
    command_file: Path | None,
    output_path: Path | None,
    trace_path: Path | None,
    artifact_paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    fixtures: list[dict[str, str]] = []
    for fixture in case_data.get("input_fixtures", []) or []:
        fixture_path = resolve_path(str(fixture))
        fixtures.append({
            "path": str(fixture),
            "sha256": sha256_file(fixture_path),
            "source_step": infer_fixture_source_step(str(fixture)),
            "source_run_id": fixture_source_run_id(case_data, str(fixture)),
        })

    lineage: dict[str, Any] = {
        "execution_mode": mode,
        "target_step": case_data.get("target_step", ""),
        "target_command_file": relative(command_file) if command_file else "",
        "target_command_sha256": sha256_file(command_file),
        "command_git_commit": git_commit(),
        "case_file": relative(case_path),
        "case_sha256": sha256_file(case_path),
        "input_fixtures": fixtures,
        "parent_results": case_data.get("parent_results", []) or [],
        "actual_output_sha256": sha256_file(output_path),
        "actual_trace_sha256": sha256_file(trace_path),
        "model_or_executor": executor_name(mode, case_data),
        "generated_at": timestamp,
        "run_id": run_id,
    }
    if artifact_paths:
        lineage["result_artifact_paths"] = artifact_paths
    return lineage


def infer_fixture_source_step(path: str) -> str:
    parts = Path(path).parts
    if "fixtures" in parts:
        idx = parts.index("fixtures")
        if idx + 1 < len(parts):
            return f"/{parts[idx + 1]}"
    return "external_fixture"


def fixture_source_run_id(case_data: dict[str, Any], fixture: str) -> str:
    sources = case_data.get("fixture_sources", {}) or {}
    if isinstance(sources, dict):
        value = sources.get(fixture)
        if value:
            return str(value)
    return "external_fixture"


def executor_name(mode: str, case_data: dict[str, Any]) -> str:
    execution = case_data.get("execution", {}) or {}
    if execution.get("executor"):
        return str(execution["executor"])
    if mode == "codex_mediated":
        return "Codex session"
    if mode == "codex_cli":
        return "Codex CLI"
    return "captured artifact"


def render_replay_prompt(case_data: dict[str, Any], case_path: Path, run_dir: Path, command_file: Path | None, mode: str) -> str:
    fixture_lines = []
    for fixture in case_data.get("input_fixtures", []) or []:
        fixture_lines.append(f"- {fixture}")
    fixtures = "\n".join(fixture_lines) or "- none"
    command_path = relative(command_file) if command_file else "(missing command file)"

    return f"""# Codex-Mediated Replay 프롬프트

Replay Test를 실행합니다. 이 작업은 운영 개발 작업이 아니라 검증 작업입니다.

## Replay 케이스

- test_id: {case_data.get('test_id', '')}
- target_step: {case_data.get('target_step', '')}
- case: {case_data.get('case', '')}
- execution_mode: {mode}
- case_file: {relative(case_path)}
- target_command_file: {command_path}

## 입력 Fixture

{fixtures}

## 지시사항

1. target command 파일을 끝까지 읽습니다.
2. 모든 input fixture를 끝까지 읽습니다.
3. target command 지시사항을 fixture 상태에만 적용합니다.
4. 운영 프로젝트 파일은 수정하지 않습니다.
5. replay로 생성한 하네스 추적과 명세 근거를 아래 파일에 작성합니다:
   `{relative(run_dir / 'actual_trace.md')}`
6. replay로 생성한 target step 산출물을 아래 파일에 작성합니다:
   `{relative(run_dir / 'actual_output.md')}`
7. 출력은 command 파일과 fixture에서 새로 생성해야 하며, `tests/expected`에서 복사하면 안 됩니다.
8. 두 파일을 작성한 뒤 아래 명령을 실행합니다:
   `python3 tests/replay/replay_runner.py {relative(case_path)} --execution-mode {mode} --run-dir {relative(run_dir)}`
"""


def prepare_replay(case_data: dict[str, Any], case_path: Path, mode: str, run_dir_arg: str | None) -> dict[str, str]:
    test_id = str(case_data.get("test_id", "unknown-test"))
    run_id, timestamp = make_run_id(test_id)
    run_dir, _, _ = run_dirs(test_id, run_id, run_dir_arg)
    workspace = run_dir / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)

    command_file = command_file_for_step(case_data)
    lineage = lineage_for(
        case_data=case_data,
        case_path=case_path,
        run_id=run_id,
        timestamp=timestamp,
        mode=mode,
        command_file=command_file,
        output_path=None,
        trace_path=None,
    )
    prompt = render_replay_prompt(case_data, case_path, run_dir, command_file, mode)

    (run_dir / "lineage.yaml").write_text(dump_simple_yaml(lineage) + "\n", encoding="utf-8")
    (run_dir / "replay_prompt.md").write_text(prompt, encoding="utf-8")
    (workspace / "README.md").write_text(
        "# Replay Workspace\n\nUse this directory for replay-only scratch files. Do not modify production artifacts.\n",
        encoding="utf-8",
    )

    return {
        "run_id": run_id,
        "run_dir": relative(run_dir),
        "replay_prompt": relative(run_dir / "replay_prompt.md"),
        "lineage": relative(run_dir / "lineage.yaml"),
        "actual_trace": relative(run_dir / "actual_trace.md"),
        "actual_output": relative(run_dir / "actual_output.md"),
    }


def write_artifacts(
    case_data: dict[str, Any],
    case_path: Path,
    trace: dict[str, Any],
    output: str,
    results: list[dict[str, str]],
    expected_output_path: Path | None,
    output_path: Path | None,
    trace_path: Path | None,
    mode: str,
    run_dir_arg: str | None,
    promote_baseline: bool,
    changed_rule_coverage: list[dict[str, Any]],
) -> dict[str, str]:
    test_id = str(case_data.get("test_id", "unknown-test"))
    if run_dir_arg:
        run_dir = resolve_path(run_dir_arg) or Path(run_dir_arg)
        run_id = run_dir.name
        timestamp = run_id.split("_", 1)[0] if "_" in run_id else datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    else:
        run_id, timestamp = make_run_id(test_id)
    status = "PASS" if all(item["status"] == "PASS" for item in results) else "FAIL"

    run_dir, latest_dir, baseline_dir = run_dirs(test_id, run_id, run_dir_arg)

    run_dir.mkdir(parents=True, exist_ok=True)
    latest_dir.mkdir(parents=True, exist_ok=True)

    expected_text = expected_output_path.read_text(encoding="utf-8") if expected_output_path else ""
    actual_text = output

    actual_trace_md = render_trace_markdown(trace, output)
    actual_output_md = actual_text or "No actual output captured.\n"
    diff_md = render_diff(expected_text, actual_text, "expected_output", "actual_output") if expected_text or actual_text else "# Diff\n\nNo output captured.\n"
    summary_md = render_summary(case_data, run_id, status, results)

    actual_rule_ids = sorted(rule_ids(trace))
    actual_applied_rule_ids = sorted(applied_rule_ids(trace))

    artifact_paths = {
        "replay_result": relative(run_dir / "replay_result.yaml"),
        "actual_trace": relative(run_dir / "actual_trace.md"),
        "actual_output": relative(run_dir / "actual_output.md"),
        "diff": relative(run_dir / "diff.md"),
        "summary": relative(run_dir / "summary.md"),
        "lineage": relative(run_dir / "lineage.yaml"),
    }
    command_file = command_file_for_step(case_data)
    lineage = lineage_for(
        case_data=case_data,
        case_path=case_path,
        run_id=run_id,
        timestamp=timestamp,
        mode=mode,
        command_file=command_file,
        output_path=output_path,
        trace_path=trace_path,
        artifact_paths=artifact_paths,
    )
    replay_result = {
        "test_id": test_id,
        "target_step": case_data.get("target_step", ""),
        "case": case_data.get("case", ""),
        "run_id": run_id,
        "timestamp": timestamp,
        "status": status,
        "input_fixtures": case_data.get("input_fixtures", []) or [],
        "expected_trace": case_data.get("expected_trace", {}) or {},
        "actual_rule_ids": actual_rule_ids,
        "actual_applied_rule_ids": actual_applied_rule_ids,
        "trace_assertions": split_assertions(results, "Harness Trace Check"),
        "output_assertions": split_assertions(results, "Output Check"),
        "forbidden_pattern_assertions": split_assertions(results, "Forbidden Pattern Check"),
        "changed_rule_coverage": changed_rule_coverage,
        "lineage": lineage,
        "result_artifact_paths": artifact_paths,
    }

    files = {
        "replay_result.yaml": dump_simple_yaml(replay_result) + "\n",
        "actual_trace.md": actual_trace_md,
        "actual_output.md": actual_output_md,
        "diff.md": diff_md,
        "summary.md": summary_md,
        "lineage.yaml": dump_simple_yaml(lineage) + "\n",
    }
    for name, content in files.items():
        (run_dir / name).write_text(content, encoding="utf-8")
        (latest_dir / name).write_text(content, encoding="utf-8")

    if promote_baseline:
        baseline_dir.mkdir(parents=True, exist_ok=True)
        for name in ["replay_result.yaml", "actual_trace.md", "actual_output.md", "lineage.yaml"]:
            shutil.copy2(run_dir / name, baseline_dir / name)

    artifact_paths["latest_dir"] = relative(latest_dir)
    if promote_baseline:
        artifact_paths["baseline_dir"] = relative(baseline_dir)
    return artifact_paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target_or_path")
    parser.add_argument("case", nargs="?")
    parser.add_argument("--execution-mode", choices=sorted(EXECUTION_MODES), help="How actual replay artifacts were produced")
    parser.add_argument("--prepare-replay", action="store_true", help="Create run directory, lineage, and replay prompt for Codex-mediated replay")
    parser.add_argument("--run-dir", help="Existing tests/results/runs/<run_id> directory to use")
    parser.add_argument("--actual-output", help="Actual target-step output produced by the replay")
    parser.add_argument("--actual-trace", help="Actual Harness Trace / Spec Evidence produced by the replay")
    parser.add_argument("--promote-baseline", action="store_true", help="Update tests/results/baseline/<test_id>/ from this run")
    parser.add_argument(
        "--changed-rule-file",
        action="append",
        default=[],
        help="Rule/spec file changed before this replay. Added Rule IDs from git diff must be expected and traced.",
    )
    parser.add_argument(
        "--changed-rule-id",
        action="append",
        default=[],
        help="Specific changed Rule ID that this replay must expect and trace.",
    )
    args = parser.parse_args()

    case_path = resolve_case(args.target_or_path, args.case)
    case_data = load_case(case_path)
    mode = execution_mode(case_data, args.execution_mode)

    if args.prepare_replay:
        prepared = prepare_replay(case_data, case_path, mode, args.run_dir)
        print("[Replay 준비 완료]")
        for key, value in prepared.items():
            print(f"{key}: {value}")
        return 0

    results: list[dict[str, str]] = []
    trace: dict[str, Any] = {}
    changed_rule_coverage: list[dict[str, Any]] = []

    default_run_dir = resolve_path(args.run_dir) if args.run_dir else None
    expected_output_path = resolve_path(
        case_data.get("expected_output_file")
        or case_data.get("expected_output_path")
        or case_data.get("actual_output")
        or case_data.get("captured_output")
    )
    output_path = (
        resolve_path(args.actual_output)
        or (default_run_dir / "actual_output.md" if default_run_dir and (default_run_dir / "actual_output.md").exists() else None)
    )
    if mode == "captured" and output_path is None:
        output_path = resolve_path(case_data.get("actual_output") or case_data.get("captured_output"))
    if mode != "captured" and output_path is None:
        raise SystemExit(f"{mode} replay requires an actual output file. Run --prepare-replay, write actual_output.md, then rerun with --run-dir.")
    output = ""
    if output_path:
        output = load_output(output_path)

    trace_path = (
        resolve_path(args.actual_trace)
        or (default_run_dir / "actual_trace.md" if default_run_dir and (default_run_dir / "actual_trace.md").exists() else None)
    )
    if mode == "captured" and trace_path is None:
        trace_path = resolve_path(case_data.get("actual_trace") or case_data.get("captured_trace"))
    if mode != "captured" and trace_path is None:
        raise SystemExit(f"{mode} replay requires an actual trace file. Run --prepare-replay, write actual_trace.md, then rerun with --run-dir.")
    if trace_path:
        trace = load_trace(trace_path)
        results.extend(check_trace(trace, case_data.get("expected_trace", {}) or {}))
    elif output:
        trace = {"raw_text": output, "loaded_rule_ids": []}
        results.extend(check_trace(trace, case_data.get("expected_trace", {}) or {}))

    changed_results, changed_rule_coverage = check_changed_rule_coverage(
        case_data,
        trace,
        args.changed_rule_file,
        args.changed_rule_id,
    )
    results.extend(changed_results)

    if output:
        results.extend(check_output(output, case_data.get("expected_output", {}) or {}))
        expected_result = case_data.get("expected_result", {}) or {}
        fail_reasons = case_data.get("expected_fail_reasons")
        if fail_reasons:
            expected_result["expected_fail_reasons"] = fail_reasons
        results.extend(check_expected_result(output, expected_result))

    artifacts = write_artifacts(
        case_data=case_data,
        case_path=case_path,
        trace=trace,
        output=output,
        results=results,
        expected_output_path=expected_output_path,
        output_path=output_path,
        trace_path=trace_path,
        mode=mode,
        run_dir_arg=args.run_dir,
        promote_baseline=args.promote_baseline,
        changed_rule_coverage=changed_rule_coverage,
    )

    report = render(case_data, results)
    lines = [report, "", "[Replay 산출물]"]
    for key, path in artifacts.items():
        lines.append(f"{key}: {path}")
    print("\n".join(lines))
    return 0 if all(item["status"] == "PASS" for item in results) else 1


if __name__ == "__main__":
    sys.exit(main())
