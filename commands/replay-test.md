---
description: fixture 기반으로 Ouroboros workflow 한 단계를 replay하고 하네스 추적, 명세 근거, output 기대값을 검증한다. 테스트 전용 명령이며 실제 개발 산출물을 만들지 않는다.
argument-hint: "<target_step> <case> | YAML block with target_step and case"
---

## Trace Discipline

- Trace is evidence bookkeeping only. It records which command references, persona references, specs, docs, and source files informed the work.
- Never let trace bookkeeping replace the primary behavior of the current command or persona.
- Ask the required interview questions, produce the required seed/TRD/tasks/code/evaluation, and use trace as supporting evidence while doing that work.
- When practical, mark loaded files with `.harness/trace/mark-loaded-file.sh --path "<file>"`, but do not stall or loop on trace setup before serving the user.
- If trace tooling is unavailable, continue the command and explicitly mention the trace limitation in the final output.



# /replay-test — 단계 Replay Test

> 기존 하네스 추적 / 명세 근거 로직을 수정하지 않고, 특정 workflow 단계만 fixture 기반으로 재실행해 trace와 산출물을 검증한다.

## 범위

`/replay-test`는 검증 명령이지 개발 명령이 아닙니다.

## Command 실행 구조

Ouroboros workflow command reference는 shell program이 아니라 Markdown 지시문입니다.

- 원본 command 파일은 `commands/*.md`에 있습니다.
- `init.sh`는 이 파일들을 `.harness/codex-harness/commands/*.md`로 복사합니다.
- 사용자가 `/run`, `/decompose` 등을 입력하면 Codex가 해당 workflow command reference를 읽고 수행하는 runtime입니다.
- `tests/replay/replay_runner.py`는 slash-command runtime이 아닙니다. replay prompt를 준비하고, lineage를 기록하고, 실제 replay artifact를 검증하는 도구입니다.

따라서 신뢰 가능한 stage replay는 실제 artifact가 어떻게 만들어졌는지 명확히 기록해야 합니다.

금지:
- production feature artifact를 생성하거나 수정하지 않는다
- `/interview`, `/seed`, `/trd`, `/decompose`, `/run`, `/evaluate`, `/evolve`를 대체하지 않는다
- 기존 하네스 추적 / 명세 근거 동작을 바꾸지 않는다
- 별도 `/trace` 명령을 만들지 않는다

허용:
- `tests/cases/*.yaml` 읽기
- `tests/fixtures/**` 읽기
- `tests/replay/replay_runner.py` 실행
- replay result artifact를 `tests/results/**` 아래에 쓰기
- 명시적으로 필요한 경우 replay 전용 captured output을 `tests/expected/` 또는 임시 replay scratch path에 쓰기

## 사용법

Positional:

```text
/replay-test interview banking_message_customer_inquiry
/replay-test seed data_pipeline_cdc
/replay-test trd data_pipeline_cdc
/replay-test decompose data_pipeline_cdc
/replay-test evaluate data_pipeline_missing_quality
```

YAML block:

```yaml
target_step: /decompose
case: data_pipeline_cdc
```

## 실행 지시

1. test case를 찾는다.
   - positional form은 `tests/cases/test_<step>_<case>.yaml`로 매핑한다
   - YAML form은 `target_step`과 `case`를 사용한다
   - 매칭되는 파일이 여러 개면 사용자에게 하나를 선택하게 한다
2. case YAML을 완전히 읽는다.
3. `input_fixtures`에 나열된 모든 파일을 읽는다.
4. fixture를 직전 상태로 보고 요청된 `target_step`만 replay한다.
5. case가 명시적으로 `mode: e2e`라고 하지 않는 한 전체 Ouroboros workflow를 실행하지 않는다.
6. 해당 step의 하네스 추적, 명세 근거, output을 캡처한다.
7. assertion을 실행한다.

```bash
python3 tests/replay/replay_runner.py tests/cases/<case-file>.yaml
```

8. 사용자가 rule/spec 파일이 바뀌었다고 말하며 재검증을 요청하면, 어떤 파일이 바뀌었는지 물어보고 runner에 전달한다.

```bash
python3 tests/replay/replay_runner.py tests/cases/<case-file>.yaml \
  --changed-rule-file ARCHITECTURE_INVARIANTS.md
```

새로 추가되었거나 변경된 정확한 Rule ID를 알고 있으면 명시적으로 전달한다.

```bash
python3 tests/replay/replay_runner.py tests/cases/<case-file>.yaml \
  --changed-rule-file ARCHITECTURE_INVARIANTS.md \
  --changed-rule-id RULE-APP-SQLSELECT-001
```

9. artifact가 아래 위치에 저장되었는지 확인한다.
   - `tests/results/runs/<timestamp>_<test_id>/`
   - `tests/results/latest/<test_id>/`
10. 지정된 형식으로 보고하고 artifact path를 함께 포함한다.

최신 실행 결과를 baseline으로 승격하려면 사용자의 명시 요청이 있을 때 아래 명령을 사용한다.

```bash
python3 tests/replay/replay_runner.py tests/cases/<case-file>.yaml --promote-baseline
```

사용자가 baseline 승격을 명시적으로 요청하지 않는 한 `tests/results/baseline/<test_id>/`는 절대 갱신하지 않는다.

## 실행 모드

### `captured`

case YAML에 미리 지정된 `actual_trace`와 `actual_output`을 읽어 검증합니다.

문서 예시, 빠른 assertion 확인, 가져온 과거 artifact 검증에 사용합니다.

### `codex_mediated`

현재 Codex 세션을 command runtime으로 사용합니다.

별도 Codex CLI runner 없이 하네스 설계 동작을 검증할 때 권장되는 모드입니다.

흐름:

```bash
python3 tests/replay/replay_runner.py tests/cases/<case-file>.yaml \
  --execution-modecodex_mediated \
  --prepare-replay
```

그 다음:

1. 출력된 `replay_prompt.md`를 연다.
2. prompt에 지정된 target command file을 읽는다. 예: `commands/decompose.md`
3. 나열된 fixture를 읽는다.
4. fixture 상태에 대해서만 target command 지시를 적용한다.
5. 새로 생성한 artifact를 출력된 경로에 쓴다.
   - `actual_trace.md`
   - `actual_output.md`
6. 아래 명령을 실행한다.

```bash
python3 tests/replay/replay_runner.py tests/cases/<case-file>.yaml \
  --execution-modecodex_mediated \
  --run-dir tests/results/runs/<run_id>
```

이 모드에서 runner는 `tests/expected/**`를 actual output 대체물로 사용하지 않습니다. 반드시 해당 run에서 실제 artifact를 만들어야 합니다.

### `codex_cli`

향후 Codex CLI/API 기반 non-interactive executor를 위한 예약 모드입니다. `codex_mediated`와 같은 lineage contract를 따라야 합니다.

## 리니지

모든 replay 결과는 artifact가 어디에서 왔는지 기록합니다.

- execution mode
- target command file path와 sha256
- command file의 git commit
- case file path와 sha256
- input fixture path와 sha256
- 각 fixture의 추정 source step
- 제공된 경우 parent result reference
- actual trace/output sha256
- model 또는 executor label

이 lineage는 `replay_result.yaml`과 `lineage.yaml`에 모두 기록됩니다.

## Runtime Trace 검증

Replay test는 Runtime Trace를 여러 수준에서 검증할 수 있습니다.

- `must_include_rule_ids`: 기존 trace check와 호환됩니다. Rule ID가 selected, loaded, applied 또는 raw trace text에 있으면 통과합니다.
- `must_include_loaded_rule_ids`: Rule ID가 `loaded_rule_ids`에 있을 때만 통과합니다.
- `must_include_applied_rule_ids`: Rule ID가 applied 명세 근거로 인용됐을 때만 통과합니다.
- `must_include_loaded_files`: 파일이 명시적으로 loaded 처리됐을 때만 통과합니다.
- `trace_confidence_in`: 허용할 confidence level을 제한합니다. 예: `loaded_files_recorded`, `applied_evidence_verified`
- `must_verify_spec_evidence: true`: `finalize-runtime-trace.py`가 인용된 `file_path#RULE-ID` evidence를 loaded file 기준으로 검증해야 합니다.

예시:

```yaml
expected_trace:
  must_include_loaded_files:
    - commands/decompose.md
    - tests/fixtures/seed/data_pipeline_cdc_seed.yaml
  must_include_loaded_rule_ids:
    - RULE-DECOMP-001
  must_include_applied_rule_ids:
    - RULE-DECOMP-001
  trace_confidence_in:
    - applied_evidence_verified
  must_verify_spec_evidence: true
```

## 변경 Rule 반영 검증

rule/spec 파일 변경 후 replay를 사용할 때, runner는 변경된 rule이 조용히 누락되지 않았는지 확인할 수 있습니다.

지원 입력:

```yaml
changed_rule_files:
  - ARCHITECTURE_INVARIANTS.md
changed_rule_ids:
  - RULE-APP-SQLSELECT-001
```

또는 CLI:

```bash
python3 tests/replay/replay_runner.py tests/cases/<case-file>.yaml \
  --changed-rule-file ARCHITECTURE_INVARIANTS.md \
  --changed-rule-id RULE-APP-SQLSELECT-001
```

동작:

- `--changed-rule-id`가 주어지면 해당 Rule ID가 `expected_trace`와 actual trace에 모두 있어야 합니다.
- `--changed-rule-file`만 주어지면 runner는 먼저 `git diff HEAD -- <file>`에서 새로 추가된 Rule ID를 찾습니다.
- git diff에 추가된 Rule ID가 없으면, 해당 파일의 Rule ID 중 하나 이상이 `expected_trace`와 actual trace에 포함됐는지 확인합니다.
- 이 방식은 의도적으로 명시적입니다. runner는 모든 변경 파일이 모든 replay case와 관련 있는지 안다고 주장하지 않습니다.

## 단계별 Fixture 입력

| 대상 단계 | Fixture 입력 |
|-------------|----------------|
| `/interview` | user request와 선택적 `turns` fixture |
| `/seed` | interview output fixture |
| `/trd` | seed output fixture |
| `/decompose` | seed output + TRD output fixture |
| `/run` | decomposed task fixture |
| `/evaluate` | run output fixture |
| `/evolve` | evaluation result fixture |

## 인터뷰 Replay 전략

### 단일 턴 인터뷰 Test

하나의 user request fixture를 사용합니다. 다음을 검증합니다.
- `expected_request_type`
- `must_ask_about`
- `must_not_ask_about`
- `must_include_rule_ids`
- 필수 하네스 추적 field

### 멀티 턴 인터뷰 Replay Test

원문 요청과 사용자 답변 turn이 포함된 fixture를 사용합니다. 다음을 검증합니다.
- 각 turn에서 필요한 질문이 이어지는가
- ambiguity가 충분히 낮아지면 인터뷰를 종료하는가
- `interview_output.yaml` 형태가 있는가
- `ambiguity_score_lte`를 만족하는가

## 필수 결과 형식

```text
[Replay Test 결과]
테스트 ID:
대상 단계:
케이스:
입력 Fixture:

[하네스 추적 확인]
PASS/FAIL - <rule_id>

[산출물 확인]
PASS/FAIL - <expected item>

[금지 패턴 확인]
PASS/FAIL - <forbidden item>

결과: PASS or FAIL

[Replay 산출물]
replay_result: tests/results/runs/<run_id>/replay_result.yaml
actual_trace: tests/results/runs/<run_id>/actual_trace.md
actual_output: tests/results/runs/<run_id>/actual_output.md
diff: tests/results/runs/<run_id>/diff.md
summary: tests/results/runs/<run_id>/summary.md
lineage: tests/results/runs/<run_id>/lineage.yaml
latest_dir: tests/results/latest/<test_id>
```

## `/evaluate` Replay 의미

`/evaluate` replay test에서 `결과: PASS`는 evaluator가 기대한 결과를 제대로 감지했다는 뜻입니다.

예를 들어 case가 `status: FAIL`을 기대한다면, captured evaluation output이 기대한 이유로 실패했을 때만 Replay Test가 PASS입니다.
