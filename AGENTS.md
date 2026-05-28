# AGENTS.md — AI Harness Template

This is the harness template repository itself.

## Project Overview

AI 에이전트 하네스 엔지니어링 + Ouroboros(명세 기반 개발) 통합 오픈소스 템플릿.
두 가지 버전: Lite(bash only) / Pro(Python enhanced).

## Rules

1. **Lite는 외부 의존성 없음** — bash/sed/grep만 사용. commands/agents는 마크다운
2. **Pro는 Python 3.11+** — pydantic, pyyaml, aiosqlite, rich, typer
3. **민감 데이터 제로** — API 키, JWT, DB URL, 비즈니스 로직 절대 포함 금지
4. **스택 자동 감지** — init.sh가 프로젝트 타입을 알아서 판단
5. **점진적 채택** — 전부 쓸 필요 없이 개별 컴포넌트 선택 가능

## Harness Trace & Spec Evidence

이 레포는 기존 하네스 동작을 유지합니다. trace metadata를 추가하더라도 기존 command/spec/agent/evaluation 규칙을 삭제, 재작성, 요약 대체하지 마세요.

### Trace 종류

- **AI-facing Trace**: 주요 workflow 단계에서 사용자에게 보여주는 설명용 trace입니다.
- **Runtime Trace**: selected, loaded, applied evidence 기록을 `.harness/trace` 아래에 남기는 실행 로그입니다. 가능하면 `.harness/trace/latest-runtime-trace-final.json`을 우선 사용하고, 없으면 `.harness/trace/latest-runtime-trace.json`을 사용하세요.

### Runtime 신뢰도 수준

- `selected`: router가 선택한 command/reference/agent 파일입니다.
- `loaded`: `.harness/trace/mark-loaded-file.sh --path <file>`로 읽었다고 명시 기록한 파일입니다.
- `applied`: Spec Evidence에서 인용되고 `python3 .harness/trace/finalize-runtime-trace.py --evidence-file <file>`로 검증된 Rule ID입니다.

Rule ID가 loaded 파일 또는 finalized runtime trace에 없으면 runtime-verified라고 설명하지 마세요.

각 command를 실행할 때는 현재 실행 중인 command 파일 자체를 먼저 loaded로 기록하세요. 설치된 프로젝트에서는 `.harness/codex-harness/commands/<step>.md`, 템플릿 레포에서는 `commands/<step>.md`를 사용합니다.

### Trace 누락 방지

각 command의 업무 본문을 시작하기 전에 반드시 해당 command md의 Trace Metadata를 먼저 수행하세요.
1. Runtime Trace를 시작합니다.
2. 현재 command 파일 자체를 loaded로 기록합니다.
3. command/reference/agent 파일을 실제로 읽을 때마다 즉시 loaded로 기록합니다.
4. 최종 응답 직전에 final trace gate를 실행합니다.

이 절차를 수행하지 못하면 누락 사유를 밝히고 `Trace 검증: FAIL` 또는 `Trace 검증: WARNING`을 출력하세요. trace가 누락된 산출물을 runtime-verified라고 말하지 마세요.

### 라우팅 원칙

workflow step 기준으로 selected 파일을 식별하세요.
- command files: `commands/<step>.md` 또는 설치된 `.harness/codex-harness/commands/<step>.md`
- reference files: 해당 단계와 관련된 seed spec, TRD, task file, architecture invariant, gate rule file
- agent files: 해당 단계에서 호출된 `agents/*.md`, methodology persona, 또는 설치된 `.harness/codex-harness/agents/*.md`

### 필수 사용자 출력

각 주요 단계에서 아래 형식으로 출력하세요.

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

`산출물:`은 비워두지 마세요. 파일 산출물이 있으면 경로와 생성/수정/검증 결과를 쓰고, 파일 산출물이 없으면 `없음 - <이유>`를 명시하세요.

각 command 수행 자체는 현재 command 파일의 Rule ID를 적용하는 것으로 간주합니다. 따라서 현재 command 파일에 Rule ID가 있으면 `[명세 근거]`에 최소 1개 이상 포함하세요. 명시적으로 적용한 `file_path#RULE-ID` 근거가 정말 없을 때만 `[명세 근거]` 블록을 생략하고, `No explicit spec rule found.` 문구도 강제로 출력하지 마세요.

```text
[명세 근거]
1. <file_path>#<rule_id>
   규칙: "<기존 규칙 문장 또는 짧은 요약>"
   적용 결과: <이 규칙이 현재 산출물이나 판단에 반영된 결과>
```

부모 Rule ID와 더 구체적인 하위 Rule ID가 함께 있으면, 넓은 부모 ID만 인용하지 말고 `RULE-EVAL-PERSONA-001-02`처럼 현재 판단에 가장 구체적으로 적용되는 하위 Rule ID를 인용하세요.

Runtime Trace 도구가 있으면, `[명세 근거]` 블록을 `.harness/trace/current-spec-evidence.md`에 저장하고 아래 명령을 실행하세요.

```bash
python3 .harness/trace/finalize-runtime-trace.py \
  --expect-step <step> \
  --evidence-file .harness/trace/current-spec-evidence.md \
  --require-command-evidence \
  --require-loaded-selected command \
  --policy .harness/trace/trace-policy.json \
  --require-policy
```

현재 command 파일에도 Rule ID가 없어 `[명세 근거]`를 출력하지 않은 경우에만 `--evidence-file` 없이 아래 명령을 실행하세요.

```bash
python3 .harness/trace/finalize-runtime-trace.py \
  --expect-step <step> \
  --require-loaded-selected command \
  --policy .harness/trace/trace-policy.json \
  --require-policy
```

finalized trace가 성공한 경우에만 검증된 trace로 사용하세요. finalizer가 `PASS`, `WARNING`, `FAIL`과 이유를 출력하면 그 상태와 이유를 사용자에게 그대로 요약하세요. 실패하면 누락된 loaded 파일 또는 불일치한 evidence와 함께 `Trace 검증: FAIL`을 출력하고, runtime verification이 된 것처럼 말하지 마세요. loaded 기록이 없다는 사실만으로 실제 미열람과 `mark-loaded-file.sh` 호출 누락을 구분하지 마세요. finalized trace가 없으면 runtime verification을 암시하지 말고 사용 가능한 confidence level(`selected_only` 또는 `loaded_files_recorded`)을 명시하세요.

## Structure

- `init.sh` — Lite 설치 스크립트 (Harness + Ouroboros commands/agents + methodology dispatcher)
- `lib/` — 공유 유틸리티 (detect-stack, render-template, colors, **methodology.sh**)
- `templates/` — 프로젝트에 복사할 템플릿 파일
- `gates/` — CI/CD 게이트 스크립트 (check-boundaries, check-secrets, check-spec)
- `boundaries/` — Codex 권한 프리셋 + hooks
- `commands/` — Ouroboros 슬래시 커맨드 (interview, seed, run, evaluate, evolve, unstuck, pm) + `/methodology`
- `agents/` — 11개 에이전트 페르소나 정의
- `ouroboros/` — 시드 스펙 템플릿, 모호성 체크리스트
- `methodology/` — 플러그인 시스템 (스키마, 레지스트리, 상태 템플릿)
- `methodologies/` — 번들 메서드 플러그인 13종 (ouroboros, living-spec, parallel-change, bmad-lite, exploration, strangler-fig, incident-review, threat-model-lite, observability-first, rfc-driven, tdd-strict, lean-mvp, mikado-method)
- `feedback/` — 피드백 루프 도구
- `examples/` — 스택별 예시
- `pro/` — Pro 버전 (Python 엔진, CLI, hooks)
- `docs/` — 가이드 (methodology-guide.md, methodology-catalog.md, CODEBASE-GUIDE.md)

## Methodology System

하네스 코어는 **고정**. 메서드는 **플러그인**으로 사용자가 선택·조합.

```bash
/methodology list                           # 사용 가능한 메서드
/methodology use ouroboros                  # 단일 활성화
/methodology compose ouroboros bmad-lite    # 다중 조합
```

번들 16종:
- 0→1 / 1→N: ouroboros (default) · living-spec · parallel-change · bmad-lite · lean-mvp · ddd-lite · shape-up
- 모든 단계: exploration · threat-model-lite · rfc-driven · tdd-strict · bdd
- 운영 / 시스템: strangler-fig · incident-review · observability-first
- 리팩터링: mikado-method

자세한 내용은 `docs/methodology-guide.md`, `docs/methodology-catalog.md`.
