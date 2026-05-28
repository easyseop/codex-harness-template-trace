#!/usr/bin/env bash
# Mark a file as actually loaded/read for the current Runtime Trace session.
# This does not prove model comprehension; it records a verifiable file path,
# file hash, and Rule IDs for later [명세 근거] validation.
#
# Usage:
#   .harness/trace/mark-loaded-file.sh --path docs/TRD.md
#   .harness/trace/mark-loaded-file.sh --trace-id trace-... --path commands/run.md

set -euo pipefail

TRACE_ID=""
PATH_VALUE=""

while [ $# -gt 0 ]; do
  case "$1" in
    --trace-id) TRACE_ID="$2"; shift 2 ;;
    --path|--file) PATH_VALUE="$2"; shift 2 ;;
    *) shift ;;
  esac
done

if [ -z "$PATH_VALUE" ]; then
  echo "Usage: $0 --path <file> [--trace-id <trace_id>]" >&2
  exit 1
fi

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
TRACE_DIR="$ROOT/.harness/trace"
LATEST="$TRACE_DIR/latest-runtime-trace.json"

if [ -z "$TRACE_ID" ]; then
  if [ ! -f "$LATEST" ]; then
    echo "No latest runtime trace found. Run record-runtime-trace.sh first." >&2
    exit 1
  fi
  TRACE_ID="$(python3 - "$LATEST" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    print(json.load(handle).get("trace_id", ""))
PY
)"
fi

if [ -z "$TRACE_ID" ]; then
  echo "Unable to resolve trace_id." >&2
  exit 1
fi

case "$PATH_VALUE" in
  /*) FULL_PATH="$PATH_VALUE"; REL_PATH="${PATH_VALUE#$ROOT/}" ;;
  *) FULL_PATH="$ROOT/$PATH_VALUE"; REL_PATH="$PATH_VALUE" ;;
esac

if [ ! -f "$FULL_PATH" ]; then
  echo "File not found: $REL_PATH" >&2
  exit 1
fi

SESSION_DIR="$TRACE_DIR/sessions/$TRACE_ID"
mkdir -p "$SESSION_DIR"

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

SHA256="$(shasum -a 256 "$FULL_PATH" | awk '{print $1}')"
SIZE_BYTES="$(wc -c < "$FULL_PATH" | tr -d ' ')"
MTIME="$(date -u -r "$FULL_PATH" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u +"%Y-%m-%dT%H:%M:%SZ")"

RULE_IDS=()
ids="$(grep -Eo 'RULE-[A-Z0-9-]+-[0-9]+' "$FULL_PATH" 2>/dev/null | sort -u || true)"
if [ -n "$ids" ]; then
  while IFS= read -r id; do
    [ -n "$id" ] && RULE_IDS+=("$id")
  done <<EOF_IDS
$ids
EOF_IDS
fi

record=$(printf '{"timestamp":"%s","trace_id":"%s","path":"%s","sha256":"%s","size_bytes":%s,"mtime":"%s","rule_ids":%s,"loaded_by":"mark-loaded-file"}' \
  "$(timestamp)" \
  "$(json_escape "$TRACE_ID")" \
  "$(json_escape "$REL_PATH")" \
  "$(json_escape "$SHA256")" \
  "$SIZE_BYTES" \
  "$(json_escape "$MTIME")" \
  "$(json_array "${RULE_IDS[@]}")")

printf '%s\n' "$record" >> "$SESSION_DIR/loaded-files.jsonl"
printf '%s\n' "$record" >> "$TRACE_DIR/loaded-files.jsonl"
printf '%s\n' "$SESSION_DIR/loaded-files.jsonl"
