# AI Harness Trace Fork 요약본

이 문서는 긴 README를 다 읽기 전에 팀원이 빠르게 큰 그림을 잡기 위한 요약본입니다.

## 한 줄 요약

이 레포는 원본 `studioKjm/ai-harness-template`의 동작 철학과 workflow는 그대로 두고, AI가 어떤 파일과 어떤 Rule ID를 근거로 판단했는지 추적할 수 있게 만든 팀용 Trace fork입니다.

## 왜 만들었나

AI가 결과를 만들었을 때 팀이 확인하고 싶은 것은 “답이 그럴듯한가”만이 아닙니다.

- 어떤 workflow command reference 문서를 기준으로 실행했는가?
- 어떤 reference/rule/artifact 문서를 읽고 판단했는가?
- 어떤 agent persona가 관여했는가?
- 어떤 Rule ID가 실제 판단 근거였는가?
- 명시 규칙이 없는데 AI가 임의로 근거를 만든 것은 아닌가?
- 규칙을 바꿨을 때 전체 workflow를 다시 돌리지 않고도 빠르게 검증할 수 있는가?

이 fork는 위 질문에 답하기 위해 만들어졌습니다.

## 원본과 다른 점

원본 하네스의 핵심 흐름은 그대로 유지했습니다.

```text
/interview -> /seed -> /trd -> /decompose -> /run -> /evaluate -> /evolve
```

추가된 것은 기능 변경이 아니라 관측과 검증 레이어입니다.

| 구분 | 원본 | 이 fork |
|------|------|---------|
| Workflow | 명세 기반 Ouroboros 단계 실행 | 동일 |
| Command 의미 | 기존 command md 기준 | 동일 |
| Agent 역할 | 기존 persona 기준 | 동일 |
| Trace | 제한적 자기 설명 | Harness Trace / Spec Evidence 출력 |
| Runtime 기록 | 별도 구조 없음 | `.harness/trace` Runtime Trace 구조 추가 |
| 단계별 검증 | 전체 루프 재실행 중심 | `/replay-test`로 특정 단계만 fixture 검증 |
| 결과 이력 | 테스트 결과 저장 구조 없음 | `tests/results`에 run/latest/baseline 저장 |
| Rule 변경 검증 | 수동 확인 필요 | 변경 rule file / Rule ID를 replay에서 명시 검증 |

## 추가된 핵심 기능

### 1. Harness Trace

각 주요 단계에서 현재 단계, 요청 유형, 적용된 command/reference/agent 파일, 핵심 Rule ID, 다음 단계를 출력합니다.

```text
[Harness Trace]
Current Step:
Request Type:
Applied Command Files:
Applied Reference Files:
Applied Agent Files:
Key Rules Applied:
Next Step:
```

### 2. Spec Evidence

가능한 경우 판단 근거를 파일 경로와 Rule ID로 보여줍니다.

```text
[Spec Evidence]
1. <file_path>#<rule_id>
   Rule: "<기존 규칙 문장 또는 짧은 요약>"
   Applied because: <이 규칙이 현재 작업에 적용되는 이유>
```

명시 규칙이 없으면 근거를 꾸며내지 않고 `No explicit spec rule found.`를 출력합니다.

### 3. Runtime Trace

Trace가 단순한 AI 자기보고에 머물지 않도록, Runtime Trace는 `selected`, `loaded`, `applied`를 구분해 기록합니다.

| 구분 | 의미 |
|------|------|
| `selected` | 하네스 라우터가 단계 기준으로 선택한 파일 |
| `loaded` | 단계 진행 중 명시적으로 읽었다고 표시한 파일과 sha256 |
| `applied` | 최종 Spec Evidence에 인용한 Rule ID가 loaded file 안에 실제 존재하는지 검증한 결과 |

대표 항목:

- timestamp
- workflow_step
- request_type
- selected_command_files
- selected_reference_files
- selected_agent_files
- selected_rule_ids
- loaded_files
- loaded_rule_ids
- applied_rule_ids
- trace_confidence
- rule_source_paths
- trace_id
- user_request_summary

단, 이것도 Codex 내부의 실제 Read 호출을 OS 수준으로 감청하는 것은 아닙니다. 대신 파일 해시와 Rule ID 검증으로 “선택 후보 목록”보다 더 신뢰할 수 있는 evidence chain을 남기는 방식입니다.

## Trace를 왜 신뢰할 수 있나

이 하네스는 AI의 생각을 들여다보는 도구가 아닙니다. 대신 외부에서 확인 가능한 증거를 단계별로 남깁니다.

| 단계 | 무엇을 증명하나 | 검증 방법 |
|------|----------------|-----------|
| `selected` | 이 workflow step에서 참고해야 할 파일 후보가 무엇인지 | `record-runtime-trace.sh`의 step별 선택 로직과 JSON 기록 |
| `loaded` | 특정 파일을 읽었다고 표시했고, 그 시점의 파일 내용이 무엇인지 | `mark-loaded-file.sh`가 path, sha256, size, mtime, Rule ID 기록 |
| `applied` | 최종 Spec Evidence에 인용한 Rule ID가 실제 loaded file 안에 있는지 | `finalize-runtime-trace.py`가 `file_path#RULE-ID` 검증 |
| behavior | 산출물이 그 규칙을 실제로 지켰는지 | replay assertion, forbidden pattern, gate, evaluate |

그래서 trace는 다음 수준으로 해석합니다.

```text
selected_only: 참고 후보 기록. 낮은 신뢰도.
loaded_files_recorded: 파일 해시와 Rule ID가 기록됨. 중간 신뢰도.
applied_evidence_verified: 인용한 Rule ID가 loaded file 안에 실제 존재함. 중간~높은 신뢰도.
applied_evidence_verified + gate/replay/evaluate PASS: 근거와 산출물 검증이 연결됨. 가장 신뢰 가능.
```

주의할 점도 있습니다.

- `loaded_files`는 Codex 내부 Read 호출을 자동 감청한 기록은 아닙니다.
- Rule ID가 존재한다는 것은 “규칙을 정확히 이해했다”는 뜻은 아닙니다.
- 최종 신뢰도는 Trace Evidence와 산출물 검증을 함께 봐야 올라갑니다.
- `trace-policy.json`은 selected에 없는 파일을 억지로 요구하지 않고, selected된 핵심 파일의 loaded 누락만 강하게 잡습니다.

### 4. Replay Test

`/replay-test`는 실제 개발 명령이 아닙니다. 특정 단계의 직전 산출물을 fixture로 넣고, trace와 output이 기대대로 나오는지 확인하는 검증 명령입니다.

예:

```text
/replay-test decompose data_pipeline_cdc
/replay-test evaluate data_pipeline_missing_quality
```

검증하는 것:

- 기대한 Rule ID가 Harness Trace에 포함되는가
- 추가한 규칙이 산출물에 반영되는가
- 기존 규칙을 깨지 않았는가
- 금지 패턴이 산출물에 없는가
- 명시 규칙이 없을 때 `No explicit spec rule found`를 출력하는가

규칙 파일을 바꾼 뒤에는 변경 파일을 명시해 replay가 새 Rule ID를 놓치지 않는지 확인할 수 있습니다.

```bash
python3 tests/replay/replay_runner.py tests/cases/<case-file>.yaml \
  --changed-rule-file ARCHITECTURE_INVARIANTS.md \
  --changed-rule-id RULE-APP-SQLSELECT-001
```

## 빈 프로젝트에서 사용하는 방법

이 레포는 작업할 프로젝트 자체가 아니라 설치용 템플릿입니다.

```bash
tar -xzf ai-harness-template-trace-fork.tar.gz
cd ai-harness-template

mkdir ../my-empty-project
cd ../my-empty-project
git init

cd ../ai-harness-template
./init.sh ../my-empty-project

cd ../my-empty-project
 codex
```

Codex 안에서는 기존 workflow처럼 사용합니다.

```text
/interview
/seed
/trd
/decompose
/run
/evaluate
/evolve
```

## Replay 결과 저장 위치

Replay Test 결과는 화면 출력으로 끝나지 않고 파일로 저장됩니다.

```text
tests/results/
  runs/<timestamp>_<test_id>/
    replay_result.yaml
    actual_trace.md
    actual_output.md
    diff.md
    summary.md
    lineage.yaml

  latest/<test_id>/
    replay_result.yaml
    actual_trace.md
    actual_output.md
    diff.md
    summary.md

  baseline/<test_id>/
    replay_result.yaml
    actual_trace.md
    actual_output.md
```

`runs`는 실행 이력, `latest`는 최신 결과, `baseline`은 명시적으로 승격한 기준 결과입니다.

## 신뢰도 기준

Replay에는 신뢰도 수준이 있습니다.

| 모드 | 의미 | 권장 용도 |
|------|------|-----------|
| `captured` | 저장된 actual trace/output을 검증 | assertion 로직 빠른 확인 |
| `codex_mediated` | Codex 세션이 command md와 fixture를 읽고 actual을 새로 생성 | 하네스 설계 검증 |
| `codex_cli` | 향후 CLI/API 자동 실행용 예약 | 추후 확장 |

하네스 설계의 신뢰성을 확인하려면 `codex_mediated` 모드를 기준으로 봐야 합니다.

## 팀원이 먼저 보면 좋은 파일

| 파일 | 역할 |
|------|------|
| `README.md` | 전체 설명과 설치/운영 매뉴얼 |
| `SUMMARY.md` | 팀 공유용 짧은 요약 |
| `commands/replay-test.md` | `/replay-test` 명령 설계 |
| `tests/replay/replay_runner.py` | Replay Test 실행/검증 runner |
| `trace/README.md` | Runtime Trace 구조 설명 |
| `trace/record-runtime-trace.sh` | Runtime Trace 기록 스크립트 |
| `trace/mark-loaded-file.sh` | 명시적으로 읽은 파일의 sha256과 Rule ID 기록 |
| `trace/finalize-runtime-trace.py` | Spec Evidence의 `file_path#RULE-ID` 검증 |

## 기억할 점

이 fork의 목적은 AI를 무조건 신뢰하게 만드는 것이 아닙니다.

목적은 AI가 내린 판단을 사람이 검토할 수 있도록 근거를 남기고, 그 근거 출력과 산출물이 계속 기대대로 동작하는지 빠르게 확인하는 것입니다.
