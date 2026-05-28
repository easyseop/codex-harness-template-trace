#!/usr/bin/env bash
# Record Runtime Trace from selected harness files.
# Usage:
#   .harness/trace/record-runtime-trace.sh --step run --request-type implementation --summary "Implement AC-001"

set -euo pipefail

STEP=""
REQUEST_TYPE="unspecified"
SUMMARY=""

while [ $# -gt 0 ]; do
  case "$1" in
    --step|--workflow-step) STEP="$2"; shift 2 ;;
    --request-type) REQUEST_TYPE="$2"; shift 2 ;;
    --summary|--user-request-summary) SUMMARY="$2"; shift 2 ;;
    *) shift ;;
  esac
done

if [ -z "$STEP" ]; then
  echo "Usage: $0 --step <workflow_step> [--request-type <type>] [--summary <summary>]" >&2
  exit 1
fi

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
TRACE_DIR="$ROOT/.harness/trace"
mkdir -p "$TRACE_DIR"

timestamp() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

json_escape() {
  python3 -c 'import json, sys; print(json.dumps(sys.argv[1], ensure_ascii=False)[1:-1])' "$1"
}

json_array() {
  python3 - "$@" <<'PY'
import json
import sys

items = [item for item in sys.argv[1:] if item]
print(json.dumps(items, ensure_ascii=False, separators=(",", ":")))
PY
}

add_if_exists() {
  local path="$1"
  shift
  if [ -e "$ROOT/$path" ]; then
    eval "$1+=(\"\$path\")"
  fi
}

latest_file() {
  local pattern="$1"
  find "$ROOT" -path "$ROOT/$pattern" -type f 2>/dev/null | sort | tail -n 1 | sed "s#^$ROOT/##"
}

COMMAND_FILES=()
SPEC_FILES=()
PERSONA_FILES=()

add_if_exists ".harness/codex-harness/commands/$STEP.md" COMMAND_FILES
add_if_exists "commands/$STEP.md" COMMAND_FILES

case "$STEP" in
  interview)
    add_if_exists ".harness/codex-harness/agents/interviewer.md" PERSONA_FILES
    add_if_exists "agents/interviewer.md" PERSONA_FILES
    add_if_exists ".harness/ouroboros/scoring/ambiguity-checklist.yaml" SPEC_FILES
    ;;
  seed)
    add_if_exists ".harness/codex-harness/agents/seed-architect.md" PERSONA_FILES
    add_if_exists ".harness/codex-harness/agents/ontologist.md" PERSONA_FILES
    add_if_exists "agents/seed-architect.md" PERSONA_FILES
    add_if_exists "agents/ontologist.md" PERSONA_FILES
    add_if_exists ".harness/ouroboros/templates/seed-spec.yaml" SPEC_FILES
    add_if_exists ".harness/ouroboros/templates/seed-spec-minimal.yaml" SPEC_FILES
    latest="$(latest_file ".harness/ouroboros/interviews/*.yaml")"; [ -n "$latest" ] && SPEC_FILES+=("$latest")
    ;;
  trd)
    add_if_exists ".harness/codex-harness/agents/architect.md" PERSONA_FILES
    add_if_exists "agents/architect.md" PERSONA_FILES
    add_if_exists "ARCHITECTURE_INVARIANTS.md" SPEC_FILES
    latest="$(latest_file ".harness/ouroboros/seeds/seed-v*.yaml")"; [ -n "$latest" ] && SPEC_FILES+=("$latest")
    ;;
  decompose)
    latest="$(latest_file ".harness/ouroboros/seeds/seed-v*.yaml")"; [ -n "$latest" ] && SPEC_FILES+=("$latest")
    add_if_exists "docs/TRD.md" SPEC_FILES
    ;;
  run)
    add_if_exists ".harness/codex-harness/agents/navigator.md" PERSONA_FILES
    add_if_exists ".harness/codex-harness/agents/test-designer.md" PERSONA_FILES
    add_if_exists "agents/navigator.md" PERSONA_FILES
    add_if_exists "agents/test-designer.md" PERSONA_FILES
    add_if_exists "ARCHITECTURE_INVARIANTS.md" SPEC_FILES
    add_if_exists "docs/TRD.md" SPEC_FILES
    latest="$(latest_file ".harness/ouroboros/seeds/seed-v*.yaml")"; [ -n "$latest" ] && SPEC_FILES+=("$latest")
    while IFS= read -r task; do SPEC_FILES+=("${task#$ROOT/}"); done < <(find "$ROOT/.harness/ouroboros/tasks" -type f 2>/dev/null | sort)
    ;;
  evaluate)
    add_if_exists ".harness/codex-harness/agents/evaluator.md" PERSONA_FILES
    add_if_exists "agents/evaluator.md" PERSONA_FILES
    add_if_exists ".harness/gates/GATES.md" SPEC_FILES
    add_if_exists ".harness/gates/rules/boundaries.yaml" SPEC_FILES
    add_if_exists ".harness/gates/rules/structure.yaml" SPEC_FILES
    latest="$(latest_file ".harness/ouroboros/seeds/seed-v*.yaml")"; [ -n "$latest" ] && SPEC_FILES+=("$latest")
    ;;
  evolve)
    for p in contrarian simplifier researcher architect hacker; do
      add_if_exists ".harness/codex-harness/agents/$p.md" PERSONA_FILES
      add_if_exists "agents/$p.md" PERSONA_FILES
    done
    latest="$(latest_file ".harness/ouroboros/evaluations/*.yaml")"; [ -n "$latest" ] && SPEC_FILES+=("$latest")
    latest="$(latest_file ".harness/ouroboros/seeds/seed-v*.yaml")"; [ -n "$latest" ] && SPEC_FILES+=("$latest")
    ;;
esac

# Older bash versions can treat an empty array expansion as unbound under
# nounset. The arrays are intentionally allowed to be empty when a step has
# no matching installed files yet.
set +u
ALL_FILES=("${COMMAND_FILES[@]}" "${SPEC_FILES[@]}" "${PERSONA_FILES[@]}")
set -u
RULE_IDS=()
RULE_PATHS=()

set +u
for file in "${ALL_FILES[@]}"; do
  [ -f "$ROOT/$file" ] || continue
  ids="$(grep -Eo 'RULE-[A-Z0-9-]+-[0-9]+' "$ROOT/$file" 2>/dev/null | sort -u || true)"
  [ -n "$ids" ] || continue
  RULE_PATHS+=("$file")
  while IFS= read -r id; do
    [ -n "$id" ] && RULE_IDS+=("$id")
  done <<EOF_IDS
$ids
EOF_IDS
done
set -u

TRACE_ID="trace-$(date -u +%Y%m%dT%H%M%SZ)-$$"
OUT="$TRACE_DIR/runtime-trace.jsonl"
LATEST="$TRACE_DIR/latest-runtime-trace.json"
SESSION_DIR="$TRACE_DIR/sessions/$TRACE_ID"
mkdir -p "$SESSION_DIR"
touch "$SESSION_DIR/loaded-files.jsonl"

set +u
record=$(printf '{"trace_schema_version":"1.1","timestamp":"%s","workflow_step":"%s","request_type":"%s","selected_command_files":%s,"selected_reference_files":%s,"selected_agent_files":%s,"selected_files":{"command":%s,"reference":%s,"agent":%s},"selected_rule_ids":%s,"loaded_files":[],"loaded_rule_ids":[],"applied_rule_ids":[],"rule_source_paths":%s,"trace_id":"%s","trace_session_dir":"%s","trace_confidence":"selected_only","user_request_summary":"%s"}' \
  "$(timestamp)" \
  "$(json_escape "$STEP")" \
  "$(json_escape "$REQUEST_TYPE")" \
  "$(json_array "${COMMAND_FILES[@]}")" \
  "$(json_array "${SPEC_FILES[@]}")" \
  "$(json_array "${PERSONA_FILES[@]}")" \
  "$(json_array "${COMMAND_FILES[@]}")" \
  "$(json_array "${SPEC_FILES[@]}")" \
  "$(json_array "${PERSONA_FILES[@]}")" \
  "$(json_array "${RULE_IDS[@]}")" \
  "$(json_array "${RULE_PATHS[@]}")" \
  "$(json_escape "$TRACE_ID")" \
  "$(json_escape ".harness/trace/sessions/$TRACE_ID")" \
  "$(json_escape "$SUMMARY")")
set -u

printf '%s\n' "$record" >> "$OUT"
printf '%s\n' "$record" > "$LATEST"
printf '%s\n' "$record" > "$SESSION_DIR/selected-runtime-trace.json"
printf '%s\n' "$LATEST"
