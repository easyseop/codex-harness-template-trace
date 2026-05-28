# 하네스 Trace

Harness Trace는 기존 하네스의 workflow, command 의미, agent 역할, gate 기준을 바꾸지 않고 관측 가능성만 추가하기 위한 구조입니다.

목표는 단순합니다.

```text
Codex가 각 단계에서 어떤 파일과 어떤 Rule ID를 근거로 판단했는지
사람이 나중에 확인할 수 있게 남긴다.
```

중요한 점은, 이 trace가 Codex의 내부 생각을 들여다보는 기능은 아니라는 것입니다. 대신 외부에서 확인 가능한 파일, Rule ID, 해시, evidence 연결 관계를 남깁니다.

## Trace 종류

| 구분 | 의미 |
|------|------|
| AI-facing Trace | Codex가 사용자에게 보여주는 설명용 trace입니다. `[하네스 추적]` 형태로 출력됩니다. |
| Runtime Trace | `.harness/trace` 아래에 저장되는 실행 로그입니다. selected, loaded, applied 증거를 파일로 남깁니다. |

AI-facing Trace는 가능한 경우 `.harness/trace/latest-runtime-trace-final.json`을 우선 참고해야 합니다. final trace가 없으면 `.harness/trace/latest-runtime-trace.json`을 참고합니다.

Runtime Trace가 없을 때 Codex는 임의로 Rule ID나 evidence를 꾸며내면 안 됩니다. 다만 현재 command 파일의 Rule ID는 command 수행 자체에 적용되는 명시 규칙으로 봅니다. 적용할 `file_path#RULE-ID` 근거가 정말 없을 때만 `[명세 근거]` 블록을 출력하지 않습니다.

## Trace 기본 구조

Trace는 한 파일에서만 동작하지 않습니다. 역할은 크게 네 층으로 나뉩니다.

```text
1. 지시 계층
   AGENTS.md, templates/AGENTS.md.hbs, commands/*.md
  Codex에게 trace를 출력하고 기록하라고 지시합니다.

2. 실행 기록 계층
   record-runtime-trace.sh, mark-loaded-file.sh
   selected / loaded 증거를 파일로 기록합니다.

3. 검증 계층
   finalize-runtime-trace.py, trace-policy.json
   Spec Evidence가 실제 loaded 파일과 Rule ID에 의해 뒷받침되는지 검증합니다.

4. Replay 검증 계층
   tests/replay/*.py, commands/replay-test.md
   replay에서 trace와 output이 기대값을 만족하는지 검증합니다.
```

## 중요한 전제: 업무 기준의 원천은 commands/*.md

각 Ouroboros 단계에서 무엇을 읽고, 어떤 순서로 판단하고, 어떤 산출물을 만들어야 하는지는 기본적으로 각 command md 파일에 정의되어 있습니다.

예를 들면:

| 단계 | 업무 기준의 원천 |
|------|------------------|
| `/interview` | `commands/interview.md` |
| `/seed` | `commands/seed.md` |
| `/trd` | `commands/trd.md` |
| `/decompose` | `commands/decompose.md` |
| `/run` | `commands/run.md` |
| `/evaluate` | `commands/evaluate.md` |
| `/evolve` | `commands/evolve.md` |

따라서 하네스의 의미 기준은 다음처럼 봐야 합니다.

```text
commands/*.md
  실제 업무 지시서입니다.
  이 단계에서 무엇을 읽고, 어떤 규칙을 따르고, 어떤 결과를 만들어야 하는지의 원천입니다.

record-runtime-trace.sh
  commands/*.md의 의미를 바꾸는 파일이 아닙니다.
  해당 step에서 참고 후보가 되어야 할 파일을 selected로 기록하는 trace용 보조 selector입니다.

trace-policy.json
  selected 후보를 새로 고르는 파일이 아닙니다.
  이미 selected된 파일 중 반드시 loaded로 남겨야 하는 핵심 파일을 정하는 보강 정책입니다.
```

즉:

```text
하네스 동작 의미의 원천 = commands/*.md
selected 기록 구현 = record-runtime-trace.sh
loaded 강제 정책 = trace-policy.json
```

만약 `commands/*.md`의 실제 지시와 `record-runtime-trace.sh`의 selected 후보가 어긋난다면, command md의 의미를 우선합니다. 이 경우 command md를 바꾸는 것이 아니라, trace selector나 trace policy를 command md에 맞게 보정해야 합니다.

새로운 파일이나 Rule ID를 추가할 때는 다음 순서로 확인합니다.

1. 해당 단계의 `commands/*.md`에서 실제로 참고해야 하는 파일인지 확인합니다.
2. trace에 selected로 남겨야 한다면 `record-runtime-trace.sh` selector에 반영합니다.
3. selected된 뒤 반드시 loaded로 남겨야 하는 핵심 파일이면 `trace-policy.json`에 반영합니다.
4. replay에서 검증해야 하는 Rule ID라면 `tests/cases/*.yaml`의 `expected_trace` 또는 `--changed-rule-file`, `--changed-rule-id`로 확인합니다.

## 구현 파일 역할

| 파일 | 역할 |
|------|------|
| `trace/record-runtime-trace.sh` | `selected`를 만듭니다. workflow step 기준으로 command/reference/agent 후보 파일을 고르고, 그 파일 안의 Rule ID를 기록합니다. |
| `trace/mark-loaded-file.sh` | `loaded`를 만듭니다. Codex가 읽었다고 보고한 파일의 경로, sha256, 크기, 수정 시간, Rule ID를 기록합니다. |
| `trace/finalize-runtime-trace.py` | `applied`를 검증합니다. Spec Evidence의 `file_path#RULE-ID`가 실제 loaded 파일 안에 있는지 확인합니다. |
| `trace/trace-policy.json` | step별 최소 required loaded 정책을 정의합니다. selected에 이미 들어온 핵심 파일만 loaded 필수로 강제합니다. |
| `init.sh` | trace 도구들을 대상 프로젝트의 `.harness/trace/`로 설치합니다. |
| `tests/replay/trace_assert.py` | replay에서 loaded Rule ID, applied Rule ID, loaded file, trace confidence를 검증합니다. |
| `tests/replay/replay_runner.py` | replay 결과를 저장하고, 변경된 rule file / Rule ID가 replay에서 누락되지 않았는지 확인합니다. |

## Codex에게 지시를 내리는 Markdown 파일

아래 md 파일들은 Codex가 trace를 언제, 어떻게 남겨야 하는지 지시합니다.

| 파일 | 지시 내용 |
|------|-----------|
| `AGENTS.md` | 이 템플릿 레포 자체에서 `[하네스 추적]`, `[명세 근거]` 출력 원칙을 정의합니다. |
| `templates/AGENTS.md.hbs` | `init.sh`로 새 프로젝트에 설치될 `AGENTS.md` 템플릿입니다. 실제 사용 프로젝트에는 이 내용이 들어갑니다. |
| `commands/interview.md` | `/interview` 단계에서 Runtime Trace 시작, loaded 기록, final trace gate 실행을 지시합니다. |
| `commands/seed.md` | `/seed` 단계에서 Runtime Trace 시작, loaded 기록, final trace gate 실행을 지시합니다. |
| `commands/trd.md` | `/trd` 단계에서 Runtime Trace 시작, loaded 기록, final trace gate 실행을 지시합니다. |
| `commands/decompose.md` | `/decompose` 단계에서 Runtime Trace 시작, loaded 기록, final trace gate 실행을 지시합니다. |
| `commands/run.md` | `/run` 단계에서 Runtime Trace 시작, loaded 기록, final trace gate 실행을 지시합니다. |
| `commands/evaluate.md` | `/evaluate` 단계에서 Runtime Trace 시작, loaded 기록, final trace gate 실행을 지시합니다. |
| `commands/evolve.md` | `/evolve` 단계에서 Runtime Trace 시작, loaded 기록, final trace gate 실행을 지시합니다. |
| `commands/replay-test.md` | replay가 Harness Trace, Spec Evidence, output, lineage, changed Rule ID coverage를 어떻게 검증해야 하는지 정의합니다. |

## 각 command md에 들어간 공통 지시

핵심 Ouroboros command에는 공통으로 네 가지 trace 지시가 들어갑니다.

1. Runtime Trace 시작:

```bash
.harness/trace/record-runtime-trace.sh --step <step> --request-type <type> --summary "<user request summary>"
```

2. command/reference/agent 파일을 읽은 뒤 loaded 기록:

```bash
.harness/trace/mark-loaded-file.sh --path "<file>"
```

3. command evidence를 포함한 명세 근거 블록 저장:

```text
.harness/trace/current-spec-evidence.md
```

4. command Rule ID를 포함해 명시 근거가 있으면 최종 사용자 응답에 명세 근거 출력:

```text
[명세 근거]
1. <file_path>#<rule_id>
   규칙: "<기존 규칙 문장 또는 짧은 요약>"
   적용 결과: <이 규칙이 현재 산출물이나 판단에 반영된 결과>
```

현재 command 파일의 Rule ID는 command 수행 자체에 적용되는 명시 규칙입니다. 적용할 `file_path#RULE-ID` 근거가 정말 없으면 `[명세 근거]` 블록과 `No explicit spec rule found.` 문구를 강제로 출력하지 않습니다.

5. 최종 trace gate 실행:

```bash
python3 .harness/trace/finalize-runtime-trace.py \
  --expect-step <step> \
  --evidence-file .harness/trace/current-spec-evidence.md \
  --require-command-evidence \
  --require-loaded-selected command \
  --policy .harness/trace/trace-policy.json \
  --require-policy
```

현재 command 파일에도 Rule ID가 없어 명세 근거가 없으면 `--evidence-file` 없이 실행합니다.

```bash
python3 .harness/trace/finalize-runtime-trace.py \
  --expect-step <step> \
  --require-loaded-selected command \
  --policy .harness/trace/trace-policy.json \
  --require-policy
```

final trace gate는 `Trace 검증: PASS`, `Trace 검증: WARNING`, `Trace 검증: FAIL`과 이유를 출력합니다. `FAIL`이면 해당 trace를 runtime-verified라고 말하면 안 됩니다. `WARNING`이면 산출물은 진행할 수 있지만, 어떤 trace 증거가 약한지 함께 설명해야 합니다.

주의할 점이 있습니다. md 지시만으로 trace 누락을 완전히 막을 수는 없습니다. 현재 구조는 누락이 생겼을 때 finalizer가 `FAIL` 또는 `WARNING`과 이유를 드러내게 만드는 방식입니다. trace 시작, loaded 기록, finalizer 실행 자체를 절대 빠뜨리지 않게 하려면 Codex hook, command wrapper, 또는 API 기반 runner처럼 명령 실행을 감싸는 별도 실행기가 필요합니다.

## 단계별 Runtime Trace 시작 명령

| command md | Runtime Trace 시작 옵션 |
|------------|--------------------------|
| `commands/interview.md` | `--step interview --request-type requirements-clarification` |
| `commands/seed.md` | `--step seed --request-type spec-generation` |
| `commands/trd.md` | `--step trd --request-type technical-design` |
| `commands/decompose.md` | `--step decompose --request-type task-decomposition` |
| `commands/run.md` | `--step run --request-type implementation` |
| `commands/evaluate.md` | `--step evaluate --request-type verification` |
| `commands/evolve.md` | `--step evolve --request-type system-evolution` |

## selected / loaded / evidence / applied

Trace는 다음 네 단계를 구분합니다.

| 단계 | 누가 만드나 | 의미 | 신뢰도 |
|------|-------------|------|--------|
| `selected` | `record-runtime-trace.sh` | 하네스가 step 기준으로 참고 후보 파일을 고릅니다. | 높음. selector 기반이라 재현 가능합니다. |
| `loaded` | Codex가 호출한 `mark-loaded-file.sh` | Codex가 읽었다고 보고한 파일의 해시와 Rule ID를 남깁니다. | 중간. 파일 증거는 남지만 OS-level Read hook은 아닙니다. |
| `evidence` | Codex의 `[명세 근거]` 출력 | 최종 판단 근거를 `file_path#RULE-ID` 형태로 설명합니다. | 중간. Codex가 작성합니다. |
| `applied` | `finalize-runtime-trace.py` | evidence가 실제 loaded 파일과 Rule ID에 의해 검증되는지 확인합니다. | 높음. 스크립트가 검증합니다. |

쉽게 말하면:

```text
selected
  이 단계에서 참고해야 할 후보 파일

loaded
 Codex가 실제로 읽었다고 기록한 파일

evidence
 Codex가 최종 판단 근거로 제시한 file#RULE-ID

applied
  evidence가 실제 loaded 파일과 Rule ID로 검증된 상태
```

## selected 후보는 무엇을 보고 정하나?

`selected`는 Codex가 실제로 읽었다는 뜻이 아닙니다. 이 단계에서 참고 후보가 되어야 할 파일을 `record-runtime-trace.sh`가 고른 목록입니다.

selector는 다음 기준으로 구성합니다.

```text
1. 해당 command 파일
   예: /run이면 commands/run.md
   설치된 프로젝트면 .harness/codex-harness/commands/run.md

2. command md에 직접 읽거나 확인하라고 적힌 파일
   예: /run의 latest seed, docs/TRD.md, .harness/ouroboros/tasks/*

3. command md에서 호출하거나 따르라고 한 agent/persona
   예: /run의 navigator.md, test-designer.md

4. 전역 최상위 규칙
   예: ARCHITECTURE_INVARIANTS.md
   특히 /run처럼 architecture rule이 중요한 단계
```

즉:

```text
selected = command md + 단계별 참고 지시 + agent/persona + 전역 규칙을 바탕으로 만든 참고 후보
```

selector의 구현 위치는 `trace/record-runtime-trace.sh`입니다. 만약 `commands/*.md`의 지시와 selector 후보가 어긋난다면 command md가 우선이며, selector를 command md에 맞게 보정해야 합니다.

## selected와 loaded 조합 해석

`selected`와 `loaded`는 서로 다른 의미입니다.

- `selected`: 하네스가 예상한 참고 후보
- `loaded`: Codex가 실제 읽었다고 기록한 파일

따라서 네 가지 조합이 나올 수 있습니다.

| 상태 | 해석 |
|------|------|
| selected에 있고 loaded에도 있음 | 예상 후보를 실제로 읽었다고 기록 |
| selected에 있는데 loaded에 없음 | 안 읽었거나 loaded 기록 누락 |
| selected에 없는데 loaded에 있음 | 예상 밖 추가 참고. selector 개선 후보일 수 있음 |
| selected에 없고 loaded에도 없음 | 관련 없음 |

중요한 한계가 있습니다. loaded가 없다는 것은 “파일을 읽지 않았다”의 확정 증거가 아닙니다. 현재 구조에서는 “읽지 않았거나, 읽었지만 `mark-loaded-file.sh` 기록이 빠졌거나, 경로가 달라 매칭되지 않았다”까지만 알 수 있습니다.

`loaded_not_selected`는 항상 나쁜 신호가 아닙니다. Codex가 작업 중 필요한 추가 문서를 찾아 읽었다는 뜻일 수 있습니다. 같은 파일이 반복적으로 중요하게 등장한다면 selector나 `trace-policy.json`에 반영할지 검토합니다.

## LLM과 Trace 동작 구조

이 섹션은 Codex가 실제 작업을 수행할 때, AI-facing Trace와 Runtime Trace가 어떤 순서로 연결되는지 설명합니다.

먼저 둘의 역할을 구분해야 합니다.

| 구분 | 역할 | 저장/출력 위치 |
|------|------|----------------|
| AI-facing Trace | 사용자가 보는 설명입니다. Codex가 현재 단계, 참고 파일, 적용 Rule ID, 다음 단계를 `[하네스 추적]`으로 보여줍니다. | 대화 화면 |
| Runtime Trace | 나중에 검증할 수 있는 실행 기록입니다. selected, loaded, applied evidence를 JSON/JSONL로 남깁니다. | `.harness/trace/**` |

두 trace의 관계는 다음과 같습니다.

```text
Runtime Trace
  실제 파일 선택, loaded 기록, evidence 검증 결과를 남김
        |
        v
AI-facing Trace
  Runtime Trace를 참고해 사용자에게 사람이 읽기 쉬운 설명으로 출력
```

즉, AI-facing Trace는 가능하면 Runtime Trace를 기반으로 출력되어야 합니다. Runtime Trace가 없거나 검증에 실패했다면, Codex는 그 사실을 사용자에게 알려야 하며 검증된 것처럼 말하면 안 됩니다.

### 1단계. 사용자가 workflow command를 실행

예를 들어 사용자가 `/run`, `/evaluate`, `/decompose` 같은 명령을 실행합니다.

```text
사용자
  -> /run
```

이때 Codex는 해당 command md를 읽고 수행합니다.

```text
/run
  -> commands/run.md
```

중요한 점은, 각 단계의 실제 업무 기준은 `commands/*.md`에 있다는 것입니다. Trace 스크립트는 그 업무 기준을 바꾸지 않고, 관측 로그를 남기는 보조 구조입니다.

### 2단계. Runtime Trace session 시작

각 command md에는 Runtime Trace를 먼저 시작하라는 지시가 들어 있습니다.

예를 들어 `/run` 단계에서는 다음 명령을 실행합니다.

```bash
.harness/trace/record-runtime-trace.sh --step run --request-type implementation --summary "<user request summary>"
```

이 명령은 Codex가 이미 읽은 파일을 기록하는 명령이 아닙니다.

이 명령의 역할은:

```text
이 step에서 원래 참고 후보가 되어야 하는 파일은 무엇인가?
```

를 step selector 기준으로 기록하는 것입니다.

이 단계에서 Runtime Trace에는 주로 다음이 생깁니다.

```yaml
workflow_step: run
request_type: implementation
selected_command_files:
selected_reference_files:
selected_agent_files:
selected_rule_ids:
trace_id:
trace_confidence: selected_only
```

AI-facing Trace는 이 정보를 사용해 “현재 단계와 참고 후보 파일”을 설명할 수 있습니다. 하지만 이 시점의 신뢰도는 `selected_only`입니다. 즉, 아직 Codex가 실제로 읽었다고 기록한 단계는 아닙니다.

### 3단계. Codex가 command/reference/agent 파일을 읽음

Codex는 command md의 지시에 따라 필요한 파일을 읽습니다.

예를 들면 `/run`에서는 다음과 같은 파일이 필요할 수 있습니다.

```text
commands/run.md
ARCHITECTURE_INVARIANTS.md
docs/TRD.md
.harness/ouroboros/seeds/seed-v*.yaml
.harness/ouroboros/tasks/*.yaml
agents/navigator.md
agents/test-designer.md
```

이 목록의 원천은 두 가지입니다.

```text
commands/*.md
  실제 업무상 무엇을 봐야 하는지 정의

record-runtime-trace.sh
  그 내용을 trace selected 후보로 기록하기 위한 selector
```

### 4단계. 읽은 파일을 loaded로 기록

Codex가 파일을 읽었다고 판단하면, 해당 파일을 loaded로 남겨야 합니다.

```bash
.harness/trace/mark-loaded-file.sh --path "<file>"
```

예:

```bash
.harness/trace/mark-loaded-file.sh --path commands/run.md
.harness/trace/mark-loaded-file.sh --path ARCHITECTURE_INVARIANTS.md
```

이때 Runtime Trace에는 파일별로 다음 정보가 남습니다.

```yaml
path:
sha256:
size_bytes:
mtime:
rule_ids:
loaded_by: mark-loaded-file
```

이 단계부터 Runtime Trace의 신뢰도는 `selected_only`보다 올라갑니다. 왜냐하면 단순 후보가 아니라, 특정 시점의 파일 내용과 Rule ID가 해시와 함께 기록되기 때문입니다.

다만 이것은 여전히 OS-level Read hook은 아닙니다. 즉, Codex 내부의 파일 읽기 동작을 자동 감청한 것은 아닙니다. Codex가 command md 지시에 따라 `mark-loaded-file.sh`를 호출해 남기는 외부 증거입니다.

### 5단계. Codex가 작업 결과와 명세 근거 작성

Codex는 command md의 업무 규칙에 따라 실제 판단이나 산출물을 만듭니다.

그 뒤 판단 근거가 있으면 `[명세 근거]`로 작성해야 합니다.

```text
[명세 근거]
1. commands/run.md#RULE-RUN-001
   규칙: "<기존 규칙 문장 또는 짧은 요약>"
   적용 결과: <이 규칙이 현재 산출물이나 판단에 반영된 결과>
```

명세 근거는 AI-facing Trace의 일부입니다. 즉, 사용자가 화면에서 볼 수 있는 설명입니다.

하지만 여기서 끝나면 Codex의 자기보고에 가깝습니다. 그래서 다음 단계에서 Runtime Trace finalizer가 이 evidence를 검증합니다.

### 6단계. Runtime Trace로 command evidence 검증

Codex는 command evidence를 포함한 명세 근거 블록을 파일로 저장하고 finalizer를 실행합니다.

```bash
python3 .harness/trace/finalize-runtime-trace.py \
  --expect-step <step> \
  --evidence-file .harness/trace/current-spec-evidence.md \
  --require-command-evidence \
  --require-loaded-selected command \
  --policy .harness/trace/trace-policy.json \
  --require-policy
```

현재 command 파일에도 Rule ID가 없어 명세 근거가 없으면 `--evidence-file` 없이 finalizer를 실행합니다.

finalizer는 다음을 확인합니다.

- Runtime Trace의 workflow_step이 현재 command step과 일치하는가
- 명세 근거가 존재하는가
- `file_path#RULE-ID` 형식의 evidence가 있는가
- evidence에 적힌 파일이 실제로 존재하는가
- evidence에 적힌 Rule ID가 그 파일 안에 실제로 있는가
- evidence에 적힌 파일이 loaded로 기록되어 있는가
- command 파일이 loaded로 기록되어 있는가
- `trace-policy.json` 기준으로 required loaded 파일이 누락되지 않았는가

finalizer는 결과를 세 단계로 나눕니다.

| 상태 | 의미 |
|------|------|
| `PASS` | required loaded와 명세 근거 검증이 통과했습니다. |
| `WARNING` | 필수 조건은 통과했지만 optional selected 파일이 loaded로 남지 않았거나, selected 밖 loaded가 있습니다. 실제 미참고인지 기록 누락인지는 구분하지 않습니다. |
| `FAIL` | required loaded가 누락됐거나, 명세 근거의 파일/Rule ID/loaded 기록이 맞지 않습니다. |

검증 결과는 이유와 함께 Runtime Trace final 파일에 저장됩니다.

```text
.harness/trace/latest-runtime-trace-final.json
.harness/trace/sessions/<trace_id>/final-runtime-trace.json
```

대표 필드는 다음과 같습니다.

```text
trace_status: PASS | WARNING | FAIL
trace_reasons.pass: 통과 이유
trace_reasons.warning: 경고 이유
trace_reasons.failure: 실패 이유
optional_selected_not_loaded: 필수는 아니지만 loaded 기록이 없는 selected 파일
```

이때 `trace_confidence`는 상황에 따라 다음처럼 결정됩니다.

```text
selected_only
  selected 후보만 있음

loaded_files_recorded
  loaded 파일 기록은 있으나 applied evidence 검증은 아직 약함

applied_evidence_verified
  명세 근거의 file_path#RULE-ID가 loaded 파일 안에서 검증됨

applied_evidence_mismatch
  명세 근거가 실제 파일, Rule ID, loaded 기록과 맞지 않음
```

### 7단계. AI-facing Trace 출력

마지막으로 Codex는 사용자에게 `[하네스 추적]`과 `[명세 근거]`를 출력합니다. 현재 command 파일에 Rule ID가 있다면 command evidence는 반드시 포함하고, 추가 spec/persona/domain evidence는 실제로 적용했을 때만 포함합니다.

이때 AI-facing Trace는 가능한 경우 Runtime Trace final 결과를 기준으로 작성해야 합니다.

```text
[하네스 추적]
현재 단계:
요청 유형:
적용한 command 파일:
적용한 reference 파일:
적용한 agent 파일:
적용한 핵심 Rule ID:
산출물:
Trace 신뢰도:
Trace 검증:
다음 단계:
```

상호관계는 이렇게 정리할 수 있습니다.

```text
Runtime Trace가 성공적으로 finalized 됨
  -> AI-facing Trace에서 Trace 검증: PASS 또는 verified 상태를 말할 수 있음

Runtime Trace가 selected_only 수준임
  -> AI-facing Trace에서 후보 파일 기준이라고 밝혀야 함

loaded 누락 또는 evidence mismatch 발생
  -> AI-facing Trace에서 Trace 검증: FAIL을 말해야 함
  -> runtime-verified라고 말하면 안 됨

명시 근거가 없음
  -> 명세 근거 블록을 출력하지 않음
  -> No explicit spec rule found. 문구도 강제하지 않음
```

즉, Runtime Trace는 “기계가 남기는 검증 가능한 기록”이고, AI-facing Trace는 “그 기록을 사용자가 이해할 수 있게 풀어쓴 설명”입니다.

가장 이상적인 흐름은 다음과 같습니다.

```text
commands/*.md 지시
  -> record-runtime-trace.sh로 selected 기록
  -> mark-loaded-file.sh로 loaded 기록
  -> Codex가 Spec Evidence 작성
  -> finalize-runtime-trace.py로 applied 검증
  -> Runtime Trace final 생성
  -> AI-facing Trace가 final trace 기반으로 출력
```

## Trace 신뢰 모델

Harness Trace는 Codex의 숨은 사고 과정을 보여준다고 주장하지 않습니다. 대신 외부에서 확인 가능한 증거를 연결합니다.

| 질문 | 남는 증거 | 검증 방법 | 증명하지 못하는 것 |
|------|-----------|-----------|--------------------|
| 이 단계에서 어떤 파일이 참고 후보였나? | `selected_command_files`, `selected_reference_files`, `selected_agent_files` | `record-runtime-trace.sh`의 step별 selector | Codex가 실제로 그 파일을 읽었다는 것 |
| 어떤 파일을 읽었다고 기록했나? | `loaded_files` | `mark-loaded-file.sh`가 path, sha256, size, mtime, Rule ID 기록 | Codex가 그 파일을 완전히 이해했다는 것 |
| 어떤 Rule ID를 적용 근거로 제시했나? | `applied_rule_ids`, `spec_evidence.references` | `finalize-runtime-trace.py`가 `file_path#RULE-ID`를 loaded 파일과 대조 | 적용 결과가 의미적으로 완벽하다는 것 |
| 산출물이 규칙을 실제로 지켰나? | replay/gate/evaluate 결과 | output assertion, forbidden pattern, gate, evaluate | 모든 도메인 의미의 완전한 정답성 |

신뢰도는 이렇게 해석합니다.

```text
selected_only
  참고 후보 파일만 기록된 상태입니다.
  방향을 잡는 데는 유용하지만, 증거로는 약합니다.

loaded_files_recorded
  읽었다고 표시한 파일의 해시와 Rule ID가 남은 상태입니다.
  selected_only보다 강하지만, Codex 내부 Read hook은 아닙니다.

applied_evidence_verified
  Spec Evidence의 file_path#RULE-ID가 실제 loaded 파일 안에 존재함을 검증한 상태입니다.
  trace만 놓고 보면 가장 강한 상태입니다.

applied_evidence_verified + gate/replay/evaluate PASS
  근거 인용과 산출물 검증이 함께 통과한 상태입니다.
  이 하네스에서 가장 신뢰할 수 있는 상태입니다.
```

## 신뢰 경고 신호

아래 상태가 보이면 trace를 그대로 믿으면 안 됩니다.

- `trace_status`가 `FAIL`
- `trace_confidence`가 `applied_evidence_mismatch`
- Spec Evidence가 인용한 Rule ID가 실제 파일에 없음
- Spec Evidence가 인용한 파일이 loaded 기록에 없음
- 새 Rule ID를 추가했는데 replay case의 `expected_trace`가 갱신되지 않음

`trace_status`가 `WARNING`이면 무조건 실패는 아니지만, `trace_reasons.warning`을 읽고 “실제 미참고인지, loaded 기록 누락인지, selector 보정 후보인지”를 확인해야 합니다.

## loaded의 한계

`loaded`는 자동 OS hook이 아닙니다. 즉, Codex가 파일을 여는 순간을 운영체제 수준에서 감청하는 구조는 아닙니다.

현재 구조는 다음 방식입니다.

```text
Codex가 파일을 읽었다고 판단
  -> mark-loaded-file.sh --path <file> 호출
  -> 스크립트가 해당 파일의 존재 여부, 해시, 크기, 수정 시간, Rule ID 기록
```

따라서 `loaded`는 “Codex가 실제로 읽었다고 보고했고, 그 시점의 파일 내용이 무엇인지 검증 가능하다”는 의미입니다.

이것만으로 Codex의 내부 이해를 증명할 수는 없습니다. 그래서 최종 신뢰도는 `applied` 검증과 replay/gate/evaluate 결과를 함께 봐야 합니다.

## Trace Policy

`trace-policy.json`은 “이 step에서는 최소한 어떤 selected 파일을 loaded로 남겨야 하는가”를 정의합니다.

중요한 원칙:

- policy는 selected에 없는 파일을 억지로 required loaded로 만들지 않습니다.
- policy에 적힌 파일이라도 현재 step의 selected 목록에 없으면 `policy_paths_not_selected`에 보고만 됩니다.
- 따라서 policy는 라우터가 고르지 않은 파일을 끌어들이는 장치가 아닙니다.
- policy는 이미 selected된 핵심 파일을 실제 loaded로 남겼는지 확인하는 장치입니다.

예를 들어 `/run`에서 `ARCHITECTURE_INVARIANTS.md`가 selected되면, policy 때문에 loaded가 필수가 됩니다.

반대로 `ARCHITECTURE_INVARIANTS.md`가 policy에는 있지만 이번 selected에 없다면 실패시키지 않고 `policy_paths_not_selected`에만 기록합니다.

## Runtime Trace 실행 흐름

1. trace session을 시작합니다.

```bash
.harness/trace/record-runtime-trace.sh --step run --request-type implementation --summary "Implement AC-001"
```

2. command/reference/agent 파일을 읽은 뒤 loaded로 기록합니다.

```bash
.harness/trace/mark-loaded-file.sh --path .harness/codex-harness/commands/run.md
.harness/trace/mark-loaded-file.sh --path ARCHITECTURE_INVARIANTS.md
```

3. 명세 근거를 파일로 저장한 뒤 applied evidence를 검증합니다.

```bash
python3 .harness/trace/finalize-runtime-trace.py \
  --expect-step run \
  --evidence-file .harness/trace/current-spec-evidence.md \
  --require-command-evidence \
  --require-loaded-selected command \
  --policy .harness/trace/trace-policy.json \
  --require-policy
```

최종 결과는 아래 파일에 저장됩니다.

```text
.harness/trace/latest-runtime-trace-final.json
.harness/trace/sessions/<trace_id>/final-runtime-trace.json
```

## Trace 명령어와 옵션

| 명령/옵션 | 언제 쓰나 | 의미 | 실패/경고 조건 |
|-----------|-----------|------|----------------|
| `record-runtime-trace.sh` | command 시작 전 | Runtime Trace session을 만들고 selected 후보 파일을 기록합니다. | `--step`이 없으면 실패 |
| `--step <step>` | `record-runtime-trace.sh` | `/run`, `/evaluate` 같은 현재 workflow step을 기록합니다. | 비어 있으면 trace 시작 실패 |
| `--request-type <type>` | `record-runtime-trace.sh` | 요청 유형 metadata를 기록합니다. | 값이 부정확해도 스크립트가 검증하지는 않음 |
| `--summary "<summary>"` | `record-runtime-trace.sh` | 사용자 요청 요약을 기록합니다. | 값이 없어도 실행 가능 |
| `mark-loaded-file.sh` | 파일을 읽은 직후 | 파일 경로, 해시, 크기, 수정 시간, Rule ID를 loaded 기록으로 남깁니다. | 파일이 없거나 trace_id를 못 찾으면 실패 |
| `--path <file>` | `mark-loaded-file.sh` | loaded로 남길 파일 경로입니다. | 파일이 없으면 실패 |
| `--trace-id <id>` | `mark-loaded-file.sh` | 특정 trace session에 loaded 기록을 남깁니다. | 없으면 latest trace를 사용 |
| `finalize-runtime-trace.py` | 최종 응답 직전 | selected, loaded, evidence를 대조해 final trace를 만듭니다. | 검증 결과에 따라 PASS/WARNING/FAIL |
| `--expect-step <step>` | `finalize-runtime-trace.py` | finalizer가 검증하는 trace가 현재 command step인지 확인합니다. | 다른 step trace면 FAIL |
| `--evidence-file <file>` | `finalize-runtime-trace.py` | `[명세 근거]` 블록 파일을 입력으로 받습니다. | 파일이 없으면 실패 |
| `--require-command-evidence` | `finalize-runtime-trace.py` | 현재 command 파일의 `file_path#RULE-ID` evidence를 필수로 요구합니다. | command evidence가 없거나 검증 실패하면 FAIL |
| `--require-loaded-selected command` | `finalize-runtime-trace.py` | selected command 파일이 loaded에 있는지 확인합니다. | command 파일 loaded 기록이 없으면 FAIL |
| `--require-loaded-selected all` | `finalize-runtime-trace.py` | 모든 selected 파일이 loaded에 있는지 확인합니다. | 너무 강하므로 일반 workflow에는 권장하지 않음 |
| `--policy <trace-policy.json>` | `finalize-runtime-trace.py` | step별 required loaded 정책을 적용합니다. | policy의 selected 핵심 파일이 loaded에 없으면 FAIL |
| `--require-policy` | `finalize-runtime-trace.py` | policy 파일이 없거나 읽을 수 없으면 실패시킵니다. | policy 파일 누락 시 FAIL |

`--require-command-evidence`는 hallucination을 줄이기 위한 절충안입니다. 현재 command 파일의 대표 Rule ID는 최소 실행 근거로 강제하지만, spec/persona/domain Rule ID는 실제로 적용했을 때만 적습니다. 즉, evidence 누락은 줄이되 억지 Rule ID 생성을 강요하지 않는 방식입니다.

## Runtime Trace 스키마

Runtime Trace JSON에는 대표적으로 다음 항목이 들어갑니다.

```yaml
trace_schema_version: trace schema version
timestamp: ISO-8601 timestamp
workflow_step: interview | seed | trd | decompose | run | evaluate | evolve | review | other
request_type: user-provided request category
selected_command_files: step router가 선택한 command markdown 파일
selected_reference_files: seed spec, TRD, task, architecture invariant, gate rule 등 reference 파일
selected_agent_files: step에서 호출된 agent/persona 파일
selected_files: command/reference/agent로 묶은 selected 파일
selected_rule_ids: selected 파일에서 발견한 Rule ID
loaded_files: mark-loaded-file.sh로 loaded 처리된 파일 목록
loaded_rule_ids: loaded 파일에서 발견한 Rule ID
applied_rule_ids: Spec Evidence에서 인용되고 검증된 Rule ID
rule_source_paths: Rule ID가 발견된 파일 경로
trace_id: runtime trace 식별자
trace_session_dir: trace session별 artifact 디렉터리
trace_confidence: selected_only | loaded_files_recorded | applied_evidence_verified | applied_evidence_mismatch
user_request_summary: 사용자 요청 요약
```

## Rule ID 규칙

Rule ID는 기존 규칙의 의미를 바꾸지 않고 식별자만 붙이기 위한 값입니다.

예시는 다음과 같습니다.

- `RULE-INTERVIEW-*`
- `RULE-SEED-*`
- `RULE-TRD-*`
- `RULE-DECOMP-*`
- `RULE-RUN-*`
- `RULE-EVAL-*`
- `RULE-EVOLVE-*`
- `RULE-APP-3TIER-*`
- `RULE-DP-*`
- `RULE-MSG-*`
- `RULE-SCA-*`

새 Rule ID를 추가할 때는 기존 규칙 문장을 재작성하지 말고, 기존 섹션 제목이나 규칙 위에 식별자만 붙이는 것을 원칙으로 합니다.

## 세부 Rule ID 규칙

섹션 단위 Rule ID만 있으면 Spec Evidence가 너무 넓어질 수 있습니다.

예를 들어 아래처럼만 되어 있으면:

```text
RULE-EVAL-PERSONA-001
  1. Stage 1 실패 시 Stage 2로 넘어가지 않는다
  2. AC 준수 여부는 코드 증거로 판단한다
  3. scope creep을 표시한다
```

Codex가 `RULE-EVAL-PERSONA-001`만 인용했을 때, 정확히 1번을 근거로 삼았는지 2번을 근거로 삼았는지 알기 어렵습니다.

그래서 부모 Rule ID는 유지하고, 각 문장이나 항목에는 하위 Rule ID를 붙입니다.

```text
RULE-EVAL-PERSONA-001
  1. RULE-EVAL-PERSONA-001-01 Stage 1 실패 시 Stage 2로 넘어가지 않는다
  2. RULE-EVAL-PERSONA-001-02 AC 준수 여부는 코드 증거로 판단한다
  3. RULE-EVAL-PERSONA-001-03 scope creep을 표시한다
```

사용 원칙:

- 부모 ID는 섹션이나 규칙 묶음을 가리킵니다.
- 하위 ID는 구체적인 문장, 체크리스트 항목, 판단 기준을 가리킵니다.
- 기존 문장의 의미는 바꾸지 않습니다.
- `RULE-...-001.1`처럼 점을 쓰지 않고 `RULE-...-001-01`처럼 하이픈을 씁니다. 현재 trace 정규식이 이 형태를 안정적으로 인식하기 때문입니다.
- 명세 근거에는 가능한 경우 부모 ID보다 하위 ID를 우선 인용합니다.

## 사용자 출력 템플릿

각 주요 단계에서 Codex는 아래 형식의 하네스 추적을 출력해야 합니다.

```text
[하네스 추적]
현재 단계:
요청 유형:
적용한 command 파일:
적용한 reference 파일:
적용한 agent 파일:
적용한 핵심 Rule ID:
산출물:
Trace 신뢰도:
Trace 검증:
다음 단계:
```

판단이나 작업 근거가 있는 경우에는 명세 근거를 출력해야 합니다.

```text
[명세 근거]
1. <file_path>#<rule_id>
   규칙: "<기존 규칙 문장 또는 짧은 요약>"
   적용 결과: <이 규칙이 현재 산출물이나 판단에 반영된 결과>
```

명시적으로 적용할 규칙을 찾지 못한 경우에는 근거를 꾸며내지 말고 `[명세 근거]` 블록을 생략합니다. 하지만 현재 command 파일에 Rule ID가 있다면 그 Rule ID는 command 수행 자체의 명시 규칙으로 취급합니다.

## Replay와의 관계

Trace는 “어떤 파일과 Rule ID를 근거로 삼았다고 기록했는가”를 보여줍니다.

Replay는 “그 근거가 기대한 결과와 연결됐는가”를 빠르게 확인합니다.

따라서 규칙 파일을 수정한 뒤에는 전체 workflow를 다시 돌리지 않고, 관련 step replay를 실행해 다음을 확인할 수 있습니다.

- 새 Rule ID가 `expected_trace`에 반영됐는가
- 실제 trace에도 새 Rule ID가 나왔는가
- 산출물에 기대 문구가 포함됐는가
- 금지 패턴이 포함되지 않았는가
- 기대한 FAIL을 evaluate가 제대로 감지했는가

변경된 rule file을 알고 있다면 replay runner에 명시할 수 있습니다.

```bash
python3 tests/replay/replay_runner.py tests/cases/<case-file>.yaml \
  --changed-rule-file ARCHITECTURE_INVARIANTS.md \
  --changed-rule-id RULE-APP-SQLSELECT-001
```

이 방식은 하네스가 모든 변경 의도를 자동으로 안다고 과장하지 않습니다. 대신 사용자가 바꾼 파일을 알려주면, replay가 그 변경을 놓친 채 PASS하는 위험을 줄입니다.
