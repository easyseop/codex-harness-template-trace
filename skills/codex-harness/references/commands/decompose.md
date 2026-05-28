## Trace Discipline

- Trace is evidence bookkeeping only. It records which command references, persona references, specs, docs, and source files informed the work.
- Never let trace bookkeeping replace the primary behavior of the current command or persona.
- Ask the required interview questions, produce the required seed/TRD/tasks/code/evaluation, and use trace as supporting evidence while doing that work.
- When practical, mark loaded files with `.harness/trace/mark-loaded-file.sh --path "<file>"`, but do not stall or loop on trace setup before serving the user.
- If trace tooling is unavailable, continue the command and explicitly mention the trace limitation in the final output.

---
description: Break seed AC into atomic layer-aware tasks BEFORE /run. USE WHENEVER implementation spans multiple files or layers. Prevents mega-prompts; each unit is independently implementable and testable.
---

# /decompose — Atomic Task Decomposition

> /run 전에 태스크를 원자적 단위로 분해하고 검증합니다.
> 메가 프롬프트를 방지하고, 각 단위가 독립적으로 구현/테스트 가능하도록 합니다.

## Trace Metadata

- Rule ID: `RULE-DECOMP-001`
- Runtime Trace 시작: 스크립트가 있으면 decomposition 전에 `.harness/trace/record-runtime-trace.sh --step decompose --request-type task-decomposition --summary "<user request summary>"`를 실행한다.
- Loaded File Trace 기록: command/reference/agent 파일을 읽은 뒤, 스크립트가 있으면 `.harness/trace/mark-loaded-file.sh --path "<file>"`로 loaded 기록을 남긴다. 특히 현재 command 파일 자체를 먼저 기록한다. 설치 프로젝트는 `.harness/codex-harness/commands/decompose.md`, 템플릿 레포는 `commands/decompose.md`를 사용한다.
- AI-facing Trace 출력: `.harness/trace/latest-runtime-trace-final.json`을 우선 참고하고, 없으면 `.harness/trace/latest-runtime-trace.json`을 참고한다. selected, loaded, applied evidence를 구분해서 설명한다.
- 산출물 명시: `[하네스 추적]`의 `산출물`에는 생성/수정/검증한 파일 경로와 결과를 반드시 적는다. 파일 산출물이 없으면 `없음 - <이유>`를 적는다.
- 명세 근거 출력: 현재 command 파일의 Rule ID를 포함해 명시적으로 적용한 `file_path#RULE-ID` 근거를 최종 응답의 `[명세 근거]`에 포함한다. 적용할 Rule ID가 정말 없을 때만 `[명세 근거]` 블록과 `No explicit spec rule found.` 문구를 강제로 출력하지 않는다.
- Final Trace Gate 검증: 명세 근거 블록을 `.harness/trace/current-spec-evidence.md`에 저장하고 `python3 .harness/trace/finalize-runtime-trace.py --expect-step decompose --evidence-file .harness/trace/current-spec-evidence.md --require-command-evidence --require-loaded-selected command --policy .harness/trace/trace-policy.json --require-policy`를 실행한다. 현재 command evidence가 누락되면 `python3 .harness/trace/finalize-runtime-trace.py --expect-step decompose --require-command-evidence --require-loaded-selected command --policy .harness/trace/trace-policy.json --require-policy`를 실행해 누락을 FAIL로 드러낸다. 실패하면 `Trace 검증: FAIL`을 보고하고 runtime verification이 된 것처럼 말하지 않는다.
- Trace 누락 방지: Runtime Trace 시작, 현재 command 파일 loaded 기록, Final Trace Gate는 이 command의 preflight/postflight gate다. 누락되면 `Trace 검증: FAIL` 또는 `WARNING`과 이유를 보고하고 runtime-verified라고 말하지 않는다.

## Instructions

You are the **Task Decomposer**. Your job is to break down seed spec acceptance criteria into atomic, implementable units.

### Why Decompose?

- AI 에이전트는 큰 태스크보다 작은 태스크에서 정확도가 높다
- 원자적 태스크는 독립적으로 테스트 가능하다
- 실패 시 롤백 범위가 작다
- 진행률 추적이 명확하다

### Decomposition Rules

`RULE-DECOMP-001`

**1. `RULE-DECOMP-001-01` Atomic Unit Criteria**

각 태스크는 다음 조건을 모두 만족해야 합니다:
- [ ] `RULE-DECOMP-001-01-01` **단일 레이어** — 한 태스크가 하나의 레이어(P/L/D)만 터치
- [ ] `RULE-DECOMP-001-01-02` **단일 AC** — 한 태스크가 하나의 Acceptance Criteria에 기여
- [ ] `RULE-DECOMP-001-01-03` **독립 테스트 가능** — 다른 태스크 완료 없이도 테스트 가능
- [ ] `RULE-DECOMP-001-01-04` **30분 이내 구현** — 너무 크면 더 분해
- [ ] `RULE-DECOMP-001-01-05` **명확한 완료 기준** — "~가 되면 완료"

**2. `RULE-DECOMP-001-02` Decomposition Process**

시드 스펙의 각 AC를 분해합니다:

```
AC-001: "사용자가 검색어를 입력하면 관련 매물을 보여준다"
    ↓
Task 1 [Data]:    검색 쿼리 레포지토리 메서드 구현 + 테스트
Task 2 [Logic]:   검색 필터링 서비스 (거리 2km, 미판매) + 테스트
Task 3 [Logic]:   검색 결과 정렬/페이지네이션 서비스 + 테스트
Task 4 [Present]: 검색 API 엔드포인트 + 테스트
Task 5 [Present]: 검색 UI 컴포넌트 + 테스트
```

**3. `RULE-DECOMP-001-03` Dependency Ordering**

태스크 간 의존성을 명시하고 실행 순서를 결정합니다:

```
Task 1 (Data)
    ↓
Task 2 (Logic) ← depends on Task 1
Task 3 (Logic) ← depends on Task 1
    ↓
Task 4 (Present) ← depends on Task 2, 3
Task 5 (Present) ← depends on Task 4
```

### Validation Checklist

분해 완료 후 검증:

```
═══ Decomposition Validation ══════════════════════
  Total tasks:     {N}
  By layer:        Data: {n} | Logic: {n} | Present: {n}
  Dependencies:    {dependency graph valid? YES/NO}
  All testable:    {YES/NO}
  All < 30min:     {YES/NO}
  AC coverage:     {all ACs covered? YES/NO}
  ─────────────────────────────
  Result:          VALID | NEEDS_REFINE
```

### Anti-patterns to Detect

| Anti-pattern | 증상 | 해결 |
|-------------|------|------|
| **Mega Task** | 하나의 태스크가 여러 레이어를 터치 | 레이어별로 분할 |
| **Orphan Task** | 어떤 AC에도 기여하지 않는 태스크 | 제거 또는 AC에 연결 |
| **Circular Dep** | 태스크 A→B→A 순환 의존 | 공통 부분을 별도 태스크로 추출 |
| **Missing Test** | 테스트 작성이 계획에 없음 | 각 태스크에 테스트 포함 |
| **Too Small** | 한 줄짜리 태스크 | 관련 태스크와 병합 |

### Output Format

```yaml
decomposition:
  seed_ref: "seed-v1.yaml"
  total_tasks: N
  tasks:
    - id: "T-001"
      ac_ref: "AC-001"
      layer: "data"
      description: "검색 쿼리 레포지토리 메서드 구현"
      test: "검색 조건별 쿼리 결과 검증"
      depends_on: []
      estimated_minutes: 20
    - id: "T-002"
      ac_ref: "AC-001"
      layer: "logic"
      description: "검색 필터링 서비스 구현"
      test: "거리/판매상태 필터 로직 단위 테스트"
      depends_on: ["T-001"]
      estimated_minutes: 25
  execution_order:
    - phase: 1
      tasks: ["T-001"]
    - phase: 2
      tasks: ["T-002", "T-003"]
    - phase: 3
      tasks: ["T-004", "T-005"]
```

### After Decomposition

분해가 완료되면:
1. 사용자에게 태스크 목록과 실행 순서를 제시
2. 확인 후 `/run`으로 각 태스크를 순서대로 실행
3. 각 태스크 완료 시 즉시 테스트 실행
4. 태스크 실패 시 `/rollback`으로 해당 태스크만 되돌림

### Replay 확인 지점

`/decompose` 완료 후, `[하네스 추적]`의 `다음 단계`에 아래 두 선택지를 함께 제안한다:

```text
1. `/run`으로 진행
2. `/replay-test decompose <case>`로 decomposition trace, 필수 Rule ID, atomic task, dependency ordering, 금지 task pattern을 검증
```
