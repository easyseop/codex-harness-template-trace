# Codex Harness Template with Trace & Replay Test

> 한국어 · [English original/reference](./README.en.md)

이 레포는 원본 `ai-harness-template-trace-fork`의 하네스 설계를 유지하면서 **Codex와 터미널/Warp 사용 흐름에 맞게 포팅한 버전**입니다.

핵심은 기존 프레임워크를 버리지 않는 것입니다.

- Ouroboros workflow 유지: `/interview -> /seed -> /trd -> /decompose -> /run -> /evaluate -> /evolve`
- Rule ID 기반 command/persona 규칙 유지
- Runtime Trace, Spec Evidence, Replay Test 유지
- gates, methodology plugin, 3-tier architecture enforcement 유지
- Claude 전용 표면만 Codex용으로 교체: `CLAUDE.md` -> `AGENTS.md`, `.claude/**` -> `.harness/codex-harness/**`, `.claude-plugin` -> `.codex-plugin`

## 빠른 설치

대상 프로젝트에 하네스를 설치합니다.

```bash
git clone https://github.com/easyseop/codex-harness-template-trace.git
cd codex-harness-template-trace
./init.sh /path/to/your-project --yes --methodology ouroboros
```

설치 후 대상 프로젝트에는 다음 파일과 디렉터리가 생깁니다.

```text
AGENTS.md
ARCHITECTURE_INVARIANTS.md
.harness/codex-harness/commands/
.harness/codex-harness/agents/
.harness/bin/harness
.harness/trace/
.harness/gates/
.harness/ouroboros/
```

## Warp/터미널에서 사용하기

이 포트는 Warp 같은 터미널에서 쓰기 쉽도록 `.harness/bin/harness` 래퍼를 설치합니다.

```bash
cd /path/to/your-project
.harness/bin/harness list
.harness/bin/harness interview "결제 부분 환불 기능을 만들고 싶다"
.harness/bin/harness seed
.harness/bin/harness trd
.harness/bin/harness decompose
.harness/bin/harness run
.harness/bin/harness evaluate
```

편하게 쓰려면 PATH에 추가하세요.

```bash
export PATH="$PWD/.harness/bin:$PATH"
harness interview "팀 과금 기능 추가"
```

중요한 점: `harness interview`는 일반 쉘이 직접 요구사항을 분석하는 실행기가 아닙니다. 설치된 command reference를 기준으로 **Codex에게 보낼 실행 프롬프트를 준비**합니다. Warp AI나 Codex에 출력된 프롬프트를 보내면 Codex가 해당 단계의 지시문을 읽고 작업합니다.

## Codex에서 사용하기

Codex 대화에서는 기존 하네스 흐름처럼 요청하면 됩니다.

```text
/interview "팀 과금 기능 추가"
/seed
/trd
/decompose
/run
/evaluate
```

또는 명시적으로:

```text
Codex Harness의 interview 단계로 "팀 과금 기능 추가" 요구사항을 정리해줘.
```

Codex는 `AGENTS.md`와 `.harness/codex-harness/commands/<step>.md`를 기준으로 동작합니다.

## 이 레포의 구조

| 경로 | 의미 |
|------|------|
| `AGENTS.md` | Codex가 이 템플릿 레포에서 따를 상위 지침 |
| `.codex-plugin/plugin.json` | Codex plugin manifest |
| `skills/codex-harness/` | Codex skill 진입점과 command/persona reference |
| `commands/*.md` | Ouroboros workflow 단계별 지시문 원본 |
| `agents/*.md` | Navigator, Evaluator 등 persona 원본 |
| `bin/harness` | Warp/터미널용 프롬프트 래퍼 |
| `trace/` | Runtime Trace, loaded file, evidence finalizer |
| `tests/replay/` | Replay Test runner |
| `gates/` | 구조/보안/spec/layer gate |
| `methodologies/` | 선택형 methodology plugin bundle |
| `templates/AGENTS.md.hbs` | 대상 프로젝트에 생성될 Codex 지침 템플릿 |

## Claude 원본과 달라진 점

| 원본 | Codex 포트 |
|------|------------|
| `CLAUDE.md` | `AGENTS.md` |
| `.claude/commands/*.md` | `.harness/codex-harness/commands/*.md` |
| `.claude/agents/*.md` | `.harness/codex-harness/agents/*.md` |
| `.claude-plugin/plugin.json` | `.codex-plugin/plugin.json` |
| Claude `Agent`/`SendMessage` 전제 | Codex subagent 가능 시 사용, 없으면 sequential persona fallback |
| Claude security CLI 전제 | `HARNESS_AI_SECURITY_CMD` 기반 격리 실행 커맨드 |

## Pair Mode

Pair Mode의 구조는 유지합니다.

```text
Navigator -> Driver(Codex) -> Test Designer -> Evaluator
```

다만 원본의 `Agent(...)`, `SendMessage`, background agent 호출은 Codex용 role adapter로 바뀌었습니다.

- multi-agent 도구가 있으면 Navigator/Test Designer를 별도 역할로 실행
- 없으면 메인 Codex 세션에서 Navigator/Test Designer persona를 순차 실행
- Test Designer는 seed spec과 AC만 기준으로 테스트를 설계해 구현 편향을 줄임

## 검증

이 포트에서 확인한 항목:

```bash
bash -n init.sh
bash -n gates/check-security-ai.sh
bash -n trace/record-runtime-trace.sh
python3 -m py_compile tests/replay/replay_runner.py tests/replay/trace_assert.py tests/replay/output_assert.py
./init.sh /tmp/codex-harness-install-test --yes --no-hooks --no-ci --methodology ouroboros
```

---

## 원본 Trace 설명

아래 내용은 기존 Trace/Replay Test 설계를 설명합니다. Codex 포트에서도 같은 설계를 유지합니다.

핵심 목적은 하나입니다.

```text
AI가 어떤 파일과 어떤 Rule ID를 근거로 판단했는지
사람이 나중에 확인할 수 있게 만든다.
```

기존 하네스의 workflow, command 의미, agent 역할, gate 기준은 바꾸지 않았습니다. 추가한 것은 관측 가능성, 검증, 결과 저장 구조입니다.

---

## 목차

1. [기존 하네스는 무엇인가](#기존-하네스는-무엇인가)
2. [이 레포에서 추가한 것](#이-레포에서-추가한-것)
3. [Trace가 필요한 이유](#trace가-필요한-이유)
4. [Trace 동작 구조](#trace-동작-구조)
5. [Trace 산출물](#trace-산출물)
6. [Trace를 어떻게 강제했나](#trace를-어떻게-강제했나)
7. [Replay Test란 무엇인가](#replay-test란-무엇인가)
8. [Replay Test 동작 구조](#replay-test-동작-구조)
9. [Replay Test 산출물](#replay-test-산출물)
10. [현재 신뢰도와 한계](#현재-신뢰도와-한계)
11. [앞으로 더 신뢰도를 높이려면](#앞으로-더-신뢰도를-높이려면)
12. [팀에서 얻는 효과](#팀에서-얻는-효과)
13. [빈 프로젝트에 적용하는 방법](#빈-프로젝트에-적용하는-방법)

---

## 기존 하네스는 무엇인가

기존 하네스는 AI가 바로 코딩부터 하지 않고, 정해진 단계에 따라 일하게 만드는 작업 구조입니다.

```text
/interview
  요구사항을 질문으로 명확히 함
        ↓
/seed
  인터뷰 결과를 명세로 정리
        ↓
/trd
  기술 설계와 레이어 영향을 정리
        ↓
/decompose
  구현 가능한 작은 작업으로 분해
        ↓
/run
  구현 수행
        ↓
/evaluate
  결과 검증
        ↓
/evolve
  배운 점을 다음 명세에 반영
```

중요한 점은 `commands/*.md`가 실행 파일이 아니라는 것입니다. 이 파일들은 Codex가 읽고 따르는 작업 지시문입니다.

```text
commands/run.md
        ↓ init.sh가 복사
.harness/codex-harness/commands/run.md
        ↓ 사용자가 Codex에서 /run 입력
Codex가 md 지시문을 읽고 작업 수행
```

따라서 하네스의 실제 의미는 각 command md에 있습니다. Trace와 Replay Test는 이 의미를 바꾸지 않고, 근거를 남기고 검증하는 보조 구조입니다.

기존 workflow의 대표 산출물은 다음과 같습니다.

| 단계 | 대표 산출물 |
|------|-------------|
| `/interview` | `.harness/ouroboros/interviews/*.yaml` |
| `/seed` | `.harness/ouroboros/seeds/seed-v*.yaml` |
| `/trd` | `docs/TRD.md` |
| `/decompose` | 태스크 분해 YAML, `/run`에서 참고할 작업 목록 |
| `/run` | 실제 코드, 테스트, 구현 변경 |
| `/evaluate` | `.harness/ouroboros/evaluations/*.yaml` |
| `/evolve` | 필요 시 다음 버전 seed spec |

---

## 이 레포에서 추가한 것

| 추가 기능 | 목적 |
|-----------|------|
| Harness Trace | 사용자가 보는 단계별 trace 출력 |
| Spec Evidence | 판단 근거를 `file_path#RULE-ID`로 표시 |
| Runtime Trace | 실제 선택, 로딩 기록, evidence 검증 결과를 파일로 저장 |
| Replay Test | 전체 workflow 없이 특정 단계만 fixture로 재검증 |
| Result 저장 구조 | replay 실행 이력, 최신 결과, baseline을 파일로 관리 |

---

## Trace가 필요한 이유

AI가 “하네스 기준에 따라 처리했습니다”라고 말하는 것만으로는 충분하지 않습니다.

우리가 알고 싶은 것은 더 구체적입니다.

- 어떤 command 파일을 기준으로 판단했는가?
- 어떤 seed, TRD, task, architecture rule을 참고했는가?
- 어떤 agent persona가 영향을 줬는가?
- 어떤 Rule ID가 실제 판단 근거로 쓰였는가?
- 명시 규칙이 없는데 근거를 꾸며낸 것은 아닌가?
- 새 규칙을 추가했을 때 실제 단계와 replay test에 반영됐는가?

Trace는 AI의 내부 생각을 보여주는 기능이 아닙니다. 대신 외부에서 확인 가능한 파일, Rule ID, 해시, 검증 결과를 남깁니다.

---

## Trace 동작 구조

Trace에는 두 종류가 있습니다.

| 종류 | 설명 | 위치 |
|------|------|------|
| AI-facing Trace | Codex가 사용자에게 보여주는 설명용 trace | 대화 화면 |
| Runtime Trace | 파일 선택, 로딩, evidence 검증 결과를 남기는 실행 로그 | `.harness/trace/**` |

두 trace의 관계는 다음과 같습니다.

```text
Runtime Trace
  selected, loaded, applied 기록을 파일로 남김
        ↓
AI-facing Trace
  Runtime Trace를 참고해 사용자에게 읽기 쉬운 형태로 출력
```

전체 흐름은 아래처럼 동작합니다.

```text
1. 사용자가 /run 같은 command 실행
        ↓
2. Codex가 해당 command md를 읽음
        ↓
3. record-runtime-trace.sh 실행
   이 단계에서 참고 후보 파일을 selected로 기록
        ↓
4. Codex가 command, reference, agent 파일을 읽음
        ↓
5. 읽은 파일마다 mark-loaded-file.sh 실행
   파일 경로, sha256, Rule ID를 loaded로 기록
        ↓
6. Codex가 [명세 근거] 작성
   file_path#RULE-ID 형태로 판단 근거를 제시
        ↓
7. finalize-runtime-trace.py 실행
   evidence가 실제 loaded 파일과 Rule ID에 의해 뒷받침되는지 확인
        ↓
8. Codex가 [하네스 추적]을 사용자에게 출력
```

### selected, loaded, evidence, applied

Trace는 네 단계를 구분합니다.

| 단계 | 쉽게 말하면 | 입력 | 출력 | 판단 기준 |
|------|-------------|------|------|-----------|
| `selected` | 이 단계에서 참고 후보가 되는 파일 | workflow step, request summary | selected command/reference/agent files | `record-runtime-trace.sh`에 정의된 단계별 선택 규칙 |
| `loaded` | Codex가 읽었다고 기록한 파일 | `--path <file>` | 파일 경로, sha256, Rule ID | Codex가 파일을 읽은 뒤 `mark-loaded-file.sh` 실행 |
| `evidence` | Codex가 최종 근거로 제시한 규칙 | `[명세 근거]` 문장 | `file_path#RULE-ID` | Codex가 현재 판단에 적용됐다고 설명 |
| `applied` | evidence가 실제 파일로 검증된 상태 | evidence file, loaded trace | 검증된 Rule ID, 실패 사유 | `finalize-runtime-trace.py`가 파일과 Rule ID 실존 여부 확인 |

이 중 `selected`와 `applied`는 스크립트가 판단하므로 비교적 강합니다. `loaded`와 `evidence`는 Codex가 남기는 기록을 바탕으로 하므로, 해시와 Rule ID 검증으로 보강하지만 완전한 OS-level read hook은 아닙니다.

`selected` 후보는 임의 추측이 아니라 다음 기준으로 만들어집니다.

```text
1. 해당 command 파일
   예: /run이면 commands/run.md, 설치된 프로젝트면 .harness/codex-harness/commands/run.md

2. command md에 직접 읽거나 확인하라고 적힌 파일
   예: /run의 latest seed, docs/TRD.md, .harness/ouroboros/tasks/*

3. command md에서 호출하거나 따르라고 한 agent/persona
   예: /run의 navigator.md, test-designer.md

4. 전역 최상위 규칙
   예: ARCHITECTURE_INVARIANTS.md
```

`selected`와 `loaded`의 조합은 아래처럼 해석합니다.

| 상태 | 해석 |
|------|------|
| selected에 있고 loaded에도 있음 | 예상 후보를 실제로 읽었다고 기록 |
| selected에 있는데 loaded에 없음 | 안 읽었거나 loaded 기록 누락 |
| selected에 없는데 loaded에 있음 | 예상 밖 추가 참고. selector 개선 후보일 수 있음 |
| selected에 없고 loaded에도 없음 | 관련 없음 |

중요한 한계가 있습니다. loaded가 없다는 것은 “파일을 읽지 않았다”의 확정 증거가 아닙니다. 현재 구조에서는 “읽지 않았거나, 읽었지만 `mark-loaded-file.sh` 기록이 빠졌거나, 경로가 달라 매칭되지 않았다”까지만 알 수 있습니다.

---

## Trace 산출물

Trace 실행 결과는 주로 `.harness/trace` 아래에 저장됩니다.

| 파일 | 의미 |
|------|------|
| `.harness/trace/runtime-trace.jsonl` | Runtime Trace 누적 로그 |
| `.harness/trace/latest-runtime-trace.json` | 가장 최근 selected, loaded 기록 |
| `.harness/trace/latest-runtime-trace-final.json` | evidence 검증까지 끝난 최종 trace |
| `.harness/trace/current-spec-evidence.md` | 최종 출력 전 저장한 Spec Evidence |
| `.harness/trace/sessions/<trace_id>/` | trace_id별 상세 기록 |

사용자 화면에는 아래 형식이 출력됩니다.

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

판단 근거가 있을 때는 아래 형식도 함께 출력합니다.

```text
[명세 근거]
1. <file_path>#<rule_id>
   규칙: "<기존 규칙 문장 또는 짧은 요약>"
   적용 결과: <이 규칙이 현재 산출물이나 판단에 반영된 결과>
```

`산출물:`은 반드시 채웁니다. 파일 산출물이 있으면 경로와 생성/수정/검증 결과를 적고, 파일 산출물이 없으면 `없음 - <이유>`를 적습니다.

현재 command 파일의 Rule ID도 명시 규칙으로 봅니다. 따라서 command 파일에 Rule ID가 있으면 `[명세 근거]`에 최소 1개 이상 적어야 합니다. 명시적으로 적용한 `file_path#RULE-ID` 근거가 정말 없으면 `[명세 근거]` 블록을 출력하지 않습니다. 이 경우 `No explicit spec rule found.` 문구도 강제로 출력하지 않습니다.

---

## Trace를 어떻게 강제했나

Trace는 단순히 “출력해 주세요”라고만 적어두지 않았습니다. 각 단계 command에 다음 절차를 넣었습니다.

```text
1. Runtime Trace 시작
   record-runtime-trace.sh 실행

2. 파일을 읽은 뒤 loaded 기록
   mark-loaded-file.sh --path <file> 실행

3. command Rule ID를 포함해 명시 근거가 있으면 명세 근거 출력
   적용할 Rule ID가 정말 없을 때만 [명세 근거] 블록을 생략

4. command evidence를 포함한 명세 근거 저장
   current-spec-evidence.md 생성

5. 최종 검증
   command evidence와 loaded 누락 여부를 검증

6. 검증 상태 출력
   Trace 검증: PASS / WARNING / FAIL과 이유 출력
```

finalizer의 의미는 “Codex가 진짜 이해했는지 증명”이 아닙니다. 대신 trace 증거가 서로 맞는지 확인합니다. required loaded가 빠지거나 명세 근거가 실제 파일/Rule ID/loaded 기록과 맞지 않으면 `FAIL`, optional selected 파일의 loaded 기록이 없거나 예상 밖 loaded가 있으면 `WARNING`, 필수 증거가 모두 맞으면 `PASS`입니다.

다만 md 지시만으로 trace 누락을 0으로 만들 수는 없습니다. 현재 구조는 command md와 `AGENTS.md`에 preflight/postflight gate를 강하게 명시하고, finalizer가 누락을 이유와 함께 드러내는 방식입니다. 진짜 강제 실행까지 하려면 Codex hook, command wrapper, 또는 API 기반 runner처럼 명령 실행 자체를 감싸는 구조가 추가로 필요합니다.

관련 파일은 다음과 같습니다.

| 파일 | 역할 |
|------|------|
| `AGENTS.md` | 이 템플릿 레포에서 trace 출력과 검증 원칙 정의 |
| `templates/AGENTS.md.hbs` | 새 프로젝트에 설치될 `AGENTS.md` 템플릿 |
| `commands/interview.md` | `/interview` trace 기록 지시 |
| `commands/seed.md` | `/seed` trace 기록 지시 |
| `commands/trd.md` | `/trd` trace 기록 지시 |
| `commands/decompose.md` | `/decompose` trace 기록 지시 |
| `commands/run.md` | `/run` trace 기록 지시 |
| `commands/evaluate.md` | `/evaluate` trace 기록 지시 |
| `commands/evolve.md` | `/evolve` trace 기록 지시 |
| `trace/record-runtime-trace.sh` | selected 후보 파일 기록 |
| `trace/mark-loaded-file.sh` | loaded 파일, 해시, Rule ID 기록 |
| `trace/finalize-runtime-trace.py` | Spec Evidence가 loaded 파일과 Rule ID로 검증되는지 확인 |
| `trace/trace-policy.json` | step별로 반드시 loaded로 남겨야 할 핵심 파일 정책 |

Trace 명령어와 옵션은 아래처럼 구분해서 보면 됩니다.

| 명령/옵션 | 쓰는 위치 | 의미 | 강제하는 것 | 강제하지 않는 것 |
|-----------|-----------|------|-------------|------------------|
| `record-runtime-trace.sh --step <step>` | command 시작 전 | 현재 workflow step의 trace session을 시작합니다. | `workflow_step`, selected 후보 파일 기록 | Codex가 실제로 읽었다는 사실 |
| `--request-type <type>` | `record-runtime-trace.sh` | 요청 유형을 기록합니다. | request_type metadata | 요청 유형의 정확성 자체 |
| `--summary "<summary>"` | `record-runtime-trace.sh` | 사용자 요청 요약을 기록합니다. | user_request_summary metadata | 요약의 완전성 |
| `mark-loaded-file.sh --path <file>` | 파일을 읽은 직후 | Codex가 읽었다고 보고한 파일을 loaded로 기록합니다. | path, sha256, size, mtime, Rule ID 기록 | 실제 이해 여부 |
| `finalize-runtime-trace.py --expect-step <step>` | 최종 응답 직전 | 현재 command와 Runtime Trace step이 같은지 확인합니다. | 이전 step trace 오사용 방지 | trace 생성 자체의 자동 실행 |
| `--evidence-file <file>` | `finalize-runtime-trace.py` | `[명세 근거]` 블록 파일을 입력으로 받습니다. | evidence의 file_path#RULE-ID 파싱 | evidence를 대신 생성하는 것 |
| `--require-command-evidence` | `finalize-runtime-trace.py` | 현재 command 파일 Rule ID가 evidence에 있는지 확인합니다. | 최소 command-level evidence | spec/persona/domain evidence 전체 강제 |
| `--require-loaded-selected command` | `finalize-runtime-trace.py` | selected command 파일이 loaded로 기록됐는지 확인합니다. | command 파일 loaded 기록 | 모든 selected 파일 loaded |
| `--policy trace/trace-policy.json` | `finalize-runtime-trace.py` | step별 required loaded 정책 파일을 사용합니다. | policy에 있는 selected 핵심 파일 검사 | selected에 없는 파일 강제 로딩 |
| `--require-policy` | `finalize-runtime-trace.py` | policy 파일이 없으면 실패시킵니다. | policy 누락 탐지 | policy 내용의 도메인 정답성 |

가장 중요한 옵션은 `--require-command-evidence`입니다. 이것은 모든 Rule Evidence를 억지로 만들라는 뜻이 아니라, 현재 command 파일의 대표 Rule ID만 최소 근거로 강제한다는 뜻입니다. 추가 spec/persona/domain evidence는 실제로 적용했을 때만 적고, 적은 경우에는 finalizer가 실제 파일과 Rule ID, loaded 기록을 검증합니다.

`trace-policy.json`은 selector가 고른 모든 파일을 무조건 강제하는 파일이 아닙니다. **selected 후보 중에서도 꼭 loaded로 남아야 하는 핵심 파일만** 정합니다.

예를 들어 `/run`에서는 현재 아래 파일이 핵심 loaded 대상입니다.

```text
commands/run.md 또는 .harness/codex-harness/commands/run.md
ARCHITECTURE_INVARIANTS.md
docs/TRD.md
```

이 파일들이 selected 되었는데 loaded 기록이 없으면 `finalize-runtime-trace.py`가 실패시키고, Codex는 `Trace 검증: FAIL`을 출력해야 합니다. 반대로 policy에 적혀 있어도 이번 selected 목록에 없는 파일은 억지로 끌어오지 않고 `policy_paths_not_selected`에 보고만 합니다.

정직하게 말하면, 이것은 Codex의 내부 사고 과정을 보는 장치가 아닙니다. 대신 “어떤 외부 문서가 선택됐고, 어떤 파일을 읽었다고 기록했으며, 어떤 Rule ID를 evidence로 제시했고, 그 evidence가 실제 파일에 존재하는지”를 확인하는 장치입니다.

---

## Replay Test란 무엇인가

Replay Test는 전체 workflow를 처음부터 다시 돌리지 않고, 특정 단계 하나만 fixture로 재실행해 검증하는 구조입니다.

예를 들어 `/decompose`만 검증하고 싶다면, 이전 단계에서 이미 만들어졌다고 가정하는 seed와 TRD fixture를 넣고 `/decompose` 결과만 확인합니다.

```text
전체 workflow 재실행
  /interview → /seed → /trd → /decompose → /run → /evaluate

Replay Test
  seed fixture + TRD fixture → /decompose만 검증
```

Replay Test는 실제 개발 명령이 아닙니다. 제품 코드나 운영 산출물을 만들기 위한 명령이 아니라, 하네스 설계가 의도대로 동작하는지 확인하는 검증 명령입니다.

---

## Replay Test 동작 구조

Replay Test의 입력은 case YAML과 fixture입니다.

```text
tests/cases/*.yaml
  어떤 단계를 검증할지, 어떤 Rule ID와 output을 기대할지 정의

tests/fixtures/**
  해당 단계 직전까지 이미 만들어졌다고 가정하는 입력 산출물
```

흐름은 다음과 같습니다.

```text
1. 사용자가 /replay-test 실행
        ↓
2. tests/cases/*.yaml 읽기
        ↓
3. input fixture 읽기
        ↓
4. target_step 하나만 replay
        ↓
5. actual_trace.md, actual_output.md 생성
        ↓
6. expected_trace, expected_output과 비교
        ↓
7. tests/results 아래에 결과 저장
```

### 실행 예시

```text
/replay-test decompose data_pipeline_cdc
/replay-test evaluate data_pipeline_missing_quality
```

또는 YAML 형태로도 표현할 수 있습니다.

```yaml
target_step: /decompose
case: data_pipeline_cdc
```

### `codex_mediated` 모드

하네스 설계를 검증할 때는 `codex_mediated` 흐름을 권장합니다.

```bash
python3 tests/replay/replay_runner.py tests/cases/test_decompose_data_pipeline_cdc.yaml \
  --execution-modecodex_mediated \
  --prepare-replay
```

이 명령은 먼저 `replay_prompt.md`를 만듭니다. 그 다음 Codex가 그 prompt와 target command md, fixture를 읽고 실제 `actual_trace.md`, `actual_output.md`를 작성합니다.

마지막으로 runner가 검증합니다.

```bash
python3 tests/replay/replay_runner.py tests/cases/test_decompose_data_pipeline_cdc.yaml \
  --execution-modecodex_mediated \
  --run-dir tests/results/runs/<run_id>
```

이 방식은 Python runner가 결과를 상상해서 만드는 것이 아닙니다. Codex가 command md와 fixture를 읽고 만든 실제 결과 파일을 runner가 검증합니다.

### 새 Rule ID를 추가했을 때

새 규칙을 추가했는데 replay case가 그 규칙을 확인하지 않으면, 잘못 PASS가 날 수 있습니다. 그래서 변경한 rule 파일이나 Rule ID를 runner에 넘길 수 있습니다.

```bash
python3 tests/replay/replay_runner.py tests/cases/<case-file>.yaml \
  --changed-rule-file ARCHITECTURE_INVARIANTS.md \
  --changed-rule-id RULE-APP-SQLSELECT-001
```

이렇게 하면 해당 Rule ID가 expected trace와 actual trace에 반영됐는지 확인합니다.

---

## Replay Test 산출물

Replay 결과는 화면에만 출력하지 않고 파일로 저장됩니다.

```text
tests/results/
  runs/
    <timestamp>_<test_id>/
      replay_result.yaml
      actual_trace.md
      actual_output.md
      diff.md
      summary.md
      lineage.yaml

  latest/
    <test_id>/
      replay_result.yaml
      actual_trace.md
      actual_output.md
      diff.md
      summary.md
      lineage.yaml

  baseline/
    <test_id>/
      replay_result.yaml
      actual_trace.md
      actual_output.md
```

각 파일의 의미는 다음과 같습니다.

| 파일 | 의미 |
|------|------|
| `replay_result.yaml` | PASS/FAIL, assertion 결과, 결과 파일 경로 |
| `actual_trace.md` | 실제 하네스 추적과 명세 근거 |
| `actual_output.md` | target step의 실제 산출물 |
| `diff.md` | 기대값과 실제값의 차이 |
| `summary.md` | 사람이 읽기 쉬운 요약 |
| `lineage.yaml` | case, fixture, command file, 실제 결과 파일의 출처와 해시 |

`runs`는 실행 이력을 계속 쌓고, `latest`는 같은 test_id의 최신 결과를 갱신합니다. `baseline`은 사용자가 명시적으로 승격할 때만 갱신합니다.

---

## 현재 신뢰도와 한계

이 레포의 Trace는 AI의 생각을 읽는 장치가 아닙니다. 대신 외부 증거를 남기고, 그 증거가 서로 맞는지 검증합니다.

| 항목 | 현재 신뢰도 | 이유 | 한계 |
|------|-------------|------|------|
| `selected` | 높음 | 단계별 선택 규칙이 후보 파일을 기록하므로 재현 가능 | 실제로 읽었다는 뜻은 아님 |
| `loaded` | 중간 | 파일 경로, sha256, Rule ID가 남음 | Codex가 `mark-loaded-file.sh`를 호출해야 함 |
| `evidence` | 중간 | `file_path#RULE-ID`로 근거를 명시 | Codex가 작성한 설명이므로 자기보고 성격이 있음 |
| `applied` | 높음 | 스크립트가 Rule ID 실존 여부와 loaded 여부를 검증 | evidence에 적지 않은 판단은 검증하지 못함 |
| AI-facing Trace | 중간 | Runtime Trace를 참고해 사용자에게 설명 | 최종 JSON을 보지 않으면 설명만으로는 부족 |
| Replay captured 모드 | 낮음~중간 | 저장된 sample을 빠르게 검증 | 실제 command 실행 결과가 아닐 수 있음 |
| Replaycodex_mediated 모드 | 중간~높음 | Codex가 command md와 fixture로 실제 결과를 새로 작성 | 완전한 비대화 자동 실행은 아님 |

현재 구조는 “완전한 실행 감시”라기보다 “검증 가능한 근거 기록”에 가깝습니다. 그래도 단순한 AI 자기보고보다 강한 이유는 다음과 같습니다.

- selected는 스크립트가 남깁니다.
- loaded는 파일 해시와 Rule ID를 함께 남깁니다.
- applied는 evidence가 실제 loaded 파일 안의 Rule ID인지 스크립트가 확인합니다.
- replay는 기대 Rule ID, output 문구, 금지 패턴을 자동으로 비교합니다.
- 결과는 `tests/results`에 남아 나중에 다시 확인할 수 있습니다.

---

## 앞으로 더 신뢰도를 높이려면

현재 구조를 더 강하게 만들려면 다음 작업이 필요합니다.

| 개선 작업 | 효과 |
|-----------|------|
| Codex CLI/API 기반 replay 실행기 | replay를 사람이 중간에 수행하지 않고 더 재현 가능하게 실행 |
| 실제 파일 read hook 연동 | Codex가 어떤 파일을 열었는지 더 직접적으로 수집 |
| rule file과 replay case의 연결 인덱스 | 새 Rule ID가 어떤 replay case에 반영되어야 하는지 더 쉽게 추적 |
| replay case 확장 | `/interview`, `/seed`, `/trd`, `/run`, `/evaluate` 단계별 검증 범위 확대 |
| CI gate 추가 | trace finalization 실패나 replay 실패를 PR 단계에서 차단 |
| baseline 승인 절차 | 기대 결과 변경이 임의로 덮어써지지 않도록 리뷰 흐름 추가 |

특히 가장 큰 개선점은 두 가지입니다.

1. Codex CLI/API 기반으로 replay를 완전 자동화하는 것
2. 실제 read hook이나 tool log를 연결해 loaded 기록의 신뢰도를 높이는 것

---

## 팀에서 얻는 효과

Trace와 Replay Test를 쓰면 다음 효과가 있습니다.

### 1. 레퍼런스 추적

AI가 어떤 command, reference, agent 파일을 근거로 판단했는지 추적할 수 있습니다.

### 2. Rule ID 기반 리뷰

“왜 이렇게 판단했는가?”를 감으로 묻는 대신, `file_path#RULE-ID` 기준으로 리뷰할 수 있습니다.

### 3. 하네스 구조 이해

처음 보는 팀원도 `/interview`, `/seed`, `/trd`, `/decompose`, `/run`, `/evaluate`, `/evolve`가 어떤 문서와 연결되는지 쉽게 볼 수 있습니다.

### 4. 새 규칙 추가 시 회귀 확인

새 Rule ID를 추가했을 때 replay로 특정 단계가 그 규칙을 반영하는지 빠르게 확인할 수 있습니다.

### 5. 전체 workflow 비용 절감

작은 규칙 변경을 확인하려고 매번 전체 우로보로스 루프를 다시 돌리지 않아도 됩니다.

### 6. 감사 가능한 산출물

trace, replay result, diff, lineage가 파일로 남기 때문에 나중에 팀원이 다시 확인할 수 있습니다.

---

## 빈 프로젝트에 적용하는 방법

이 템플릿 레포에서 바로 제품 개발을 하는 것이 아니라, 대상 프로젝트에 설치해서 사용합니다.

```bash
./init.sh /path/to/your-project
cd /path/to/your-project
codex
```

설치 후 대상 프로젝트에는 다음 구조가 생깁니다.

```text
.harness/codex-harness/commands/
  interview.md
  seed.md
  trd.md
  decompose.md
  run.md
  evaluate.md
  evolve.md

.harness/codex-harness/agents/
  *.md

.harness/trace/
  record-runtime-trace.sh
  mark-loaded-file.sh
  finalize-runtime-trace.py
  trace-policy.json
```

그 다음 Codex에서 아래 흐름을 사용합니다.

```text
/interview
/seed
/trd
/decompose
/run
/evaluate
/evolve
```

단계가 끝날 때는 다음 두 선택지를 비교하면 됩니다.

```text
1. 다음 workflow 단계로 진행
2. 다음 단계로 가기 전 /replay-test로 해당 단계 검증
```

더 자세한 문서는 아래를 참고하세요.

- Trace 상세 설명: [trace/README.md](./trace/README.md)
- Replay command 상세: [commands/replay-test.md](./commands/replay-test.md)
- 빠른 공유용 요약: [SUMMARY.md](./SUMMARY.md)
- 원본 영어 README 참고: [README.en.md](./README.en.md)
