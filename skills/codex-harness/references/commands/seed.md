---
description: Crystallize interview results into an IMMUTABLE seed spec (YAML). Run ONLY after /interview reaches ambiguity ≤ 0.2. Extracts ontology, AC, constraints. Once created, seeds cannot be modified — only versioned.
---

## Trace Discipline

- Trace is evidence bookkeeping only. It records which command references, persona references, specs, docs, and source files informed the work.
- Never let trace bookkeeping replace the primary behavior of the current command or persona.
- Ask the required interview questions, produce the required seed/TRD/tasks/code/evaluation, and use trace as supporting evidence while doing that work.
- When practical, mark loaded files with `.harness/trace/mark-loaded-file.sh --path "<file>"`, but do not stall or loop on trace setup before serving the user.
- If trace tooling is unavailable, continue the command and explicitly mention the trace limitation in the final output.



# /seed — Seed Specification Generator

> 인터뷰 결과를 불변 스펙으로 결정화한다

## Trace Metadata

- Rule ID: `RULE-SEED-001`
- Runtime Trace 시작: 스크립트가 있으면 Phase 0 전에 `.harness/trace/record-runtime-trace.sh --step seed --request-type spec-generation --summary "<user request summary>"`를 실행한다.
- Loaded File Trace 기록: command/reference/agent 파일을 읽은 뒤, 스크립트가 있으면 `.harness/trace/mark-loaded-file.sh --path "<file>"`로 loaded 기록을 남긴다. 특히 현재 command 파일 자체를 먼저 기록한다. 설치 프로젝트는 `.harness/codex-harness/commands/seed.md`, 템플릿 레포는 `commands/seed.md`를 사용한다.
- AI-facing Trace 출력: `.harness/trace/latest-runtime-trace-final.json`을 우선 참고하고, 없으면 `.harness/trace/latest-runtime-trace.json`을 참고한다. selected, loaded, applied evidence를 구분해서 설명한다.
- 산출물 명시: `[하네스 추적]`의 `산출물`에는 생성/수정/검증한 파일 경로와 결과를 반드시 적는다. 파일 산출물이 없으면 `없음 - <이유>`를 적는다.
- 명세 근거 출력: 현재 command 파일의 Rule ID를 포함해 명시적으로 적용한 `file_path#RULE-ID` 근거를 최종 응답의 `[명세 근거]`에 포함한다. 적용할 Rule ID가 정말 없을 때만 `[명세 근거]` 블록과 `No explicit spec rule found.` 문구를 강제로 출력하지 않는다.
- Final Trace Gate 검증: 명세 근거 블록을 `.harness/trace/current-spec-evidence.md`에 저장하고 `python3 .harness/trace/finalize-runtime-trace.py --expect-step seed --evidence-file .harness/trace/current-spec-evidence.md --require-command-evidence --require-loaded-selected command --policy .harness/trace/trace-policy.json --require-policy`를 실행한다. 현재 command evidence가 누락되면 `python3 .harness/trace/finalize-runtime-trace.py --expect-step seed --require-command-evidence --require-loaded-selected command --policy .harness/trace/trace-policy.json --require-policy`를 실행해 누락을 FAIL로 드러낸다. 실패하면 `Trace 검증: FAIL`을 보고하고 runtime verification이 된 것처럼 말하지 않는다.
- Trace 누락 방지: Runtime Trace 시작, 현재 command 파일 loaded 기록, Final Trace Gate는 이 command의 preflight/postflight gate다. 누락되면 `Trace 검증: FAIL` 또는 `WARNING`과 이유를 보고하고 runtime-verified라고 말하지 않는다.

## Instructions

You are now the **Seed Architect** agent. Your job is to transform the interview into an immutable specification.

### Phase 0: State Audit (FIRST STEP)

`RULE-SEED-001`

1. `RULE-SEED-001-01` **Scan `.harness/ouroboros/seeds/`** — list existing `seed-v*.yaml`
   - If latest seed's goal matches current interview topic → this is a **new version** (e.g., seed-v2 extends seed-v1)
   - If topics differ → fresh seed (seed-v1 of new feature)
2. `RULE-SEED-001-02` **Verify latest interview** in `.harness/ouroboros/interviews/` is ≤ 24h old and ambiguity ≤ 0.2
   - If stale or ambiguous → prompt user to run `/interview` again
3. `RULE-SEED-001-03` **Check scale** — small feature (1-2 files)? → use `seed-spec-minimal.yaml` template
   - Large feature (multiple layers)? → use full `seed-spec.yaml` template

### Rules
`RULE-SEED-002`

1. `RULE-SEED-002-01` 인터뷰 결과가 없으면 먼저 `/interview`를 실행하라고 안내
2. `RULE-SEED-002-02` 시드는 한번 생성되면 수정하지 않는다 (새 버전을 만들어야 함)
3. `RULE-SEED-002-03` 모든 필드가 채워져야 한다 — TODO나 TBD 금지

### Subagent Delegation

온톨로지 추출의 정확도를 높이기 위해 **subagent를 활용**합니다:

```
1. Subagent(Ontologist) → 인터뷰에서 도메인 모델 추출
   - 엔티티, 관계, 액션을 독립적으로 추출
   - 결과를 메인 에이전트에 반환

2. Main Agent(Seed Architect) → 추출된 온톨로지로 시드 스펙 결정화
```

**Codex에서 subagent 사용**:
- 복잡한 인터뷰의 경우 `Agent` 도구로 Ontologist를 별도 spawn하여 온톨로지 추출을 위임
- Ontologist는 `.harness/codex-harness/agents/ontologist.md`의 페르소나를 따름
- 결과를 받아 Seed Architect가 최종 스펙을 조립

### Process

1. **Read** the latest interview from `.harness/ouroboros/interviews/`
2. **Choose template** based on scale (see Phase 0):
   - Minimal (`.harness/ouroboros/templates/seed-spec-minimal.yaml`) — small feature, 1-3 files, single layer
   - Full (`.harness/ouroboros/templates/seed-spec.yaml`) — multi-layer, multi-entity, or complex domain
3. **Delegate** ontology extraction to Ontologist subagent (full mode only; for complex domains)
4. **Extract** ontology (domain model) from answers (full mode)
5. **Crystallize** into seed spec YAML
6. **Validate** all required fields are present
7. **Save** to `.harness/ouroboros/seeds/seed-v{N}.yaml`

### Seed Spec Format

```yaml
# Seed Specification v{N}
# Generated: YYYY-MM-DD
# Source Interview: {interview-file}
# WARNING: This file is immutable. To change, create a new version.

version: {N}
created: "YYYY-MM-DDTHH:MM:SS"
interview_ref: "{interview-file}"

goal:
  summary: "{one-line goal}"
  detail: "{2-3 sentences expanding the goal}"
  non_goals:
    - "{what this is NOT}"

constraints:
  must:
    - "{absolute requirement}"
  must_not:
    - "{absolute prohibition}"
  should:
    - "{preferred but negotiable}"

acceptance_criteria:
  - id: "AC-001"
    description: "{testable criterion}"
    verification: "manual | automated | both"
    priority: "must | should | nice"
    complexity: "low | medium | high"
    # low: 단순 CRUD, 설정, UI → Direct 구현
    # medium: 비즈니스 로직, 데이터 변환 → Pair Mode 선택적
    # high: 결제/보안/외부연동/복잡한 상태 → Pair Mode 강제
  - id: "AC-002"
    description: "..."

ontology:
  entities:
    - name: "{EntityName}"
      fields:
        - name: "{fieldName}"
          type: "{string | number | boolean | date | reference}"
          required: true
      relationships:
        - target: "{OtherEntity}"
          type: "{has_many | belongs_to | has_one}"
  actions:
    - name: "{actionName}"
      actor: "{who performs this}"
      input: "{what goes in}"
      output: "{what comes out}"
      side_effects:
        - "{what changes}"

scope:
  mvp:
    - "{what's in MVP}"
  future:
    - "{what's deferred}"

tech_decisions:
  - decision: "{what was decided}"
    reason: "{why}"
    alternatives_considered:
      - "{what else was considered}"
```

### Validation Checklist

Before saving, verify:
- [ ] Goal summary is one clear sentence
- [ ] At least 1 must constraint
- [ ] At least 1 must_not constraint
- [ ] At least 2 acceptance criteria
- [ ] All AC are testable (not vague)
- [ ] All AC have complexity field (low/medium/high)
- [ ] Ontology has at least 1 entity
- [ ] MVP scope is defined
- [ ] No TODO/TBD placeholders

### Complexity 판단 기준

AC의 complexity를 다음 기준으로 판단:

| Complexity | 기준 | 예시 |
|-----------|------|------|
| **low** | 단일 레이어, 명확한 입출력, 표준 패턴 | CRUD 엔드포인트, 정적 페이지, 설정 파일 |
| **medium** | 2+ 레이어 관련, 비즈니스 규칙 포함, 데이터 변환 | 필터링/정렬 로직, API 통합, 데이터 집계 |
| **high** | 3 레이어 전체, 외부 연동, 보안, 복잡한 상태 관리 | 결제/정산, 인증/권한, 실시간 통신, 트랜잭션 |

### Output

```
Seed v{N} generated: .harness/ouroboros/seeds/seed-v{N}.yaml

Ontology: {N} entities, {M} actions
Acceptance Criteria: {K} items ({must} must, {should} should)
  - low complexity:    {n} → Direct 구현 (skip 가능)
  - medium complexity: {n} → Pair Mode
  - high complexity:   {n} → Pair Mode + Test Designer
MVP Scope: {items}

Next steps (순서 중요 — 건너뛰지 않는다):
  1. /trd        — 3-tier 기술 설계서 작성 및 논의점 확인
  2. /decompose  — AC를 원자적 레이어별 태스크로 분해
  3. /run        — Double Diamond 실행

Skip 조건: AC 전체가 low complexity이고 단일 레이어만 변경할 경우에만
           /trd와 /decompose를 생략하고 /run으로 바로 진행할 수 있다.
```

### Replay 확인 지점

`/seed` 완료 후, `[하네스 추적]`의 `다음 단계`에 아래 두 선택지를 함께 제안한다:

```text
1. `/trd`로 진행
2. `/replay-test seed <case>`로 seed trace, 필수 Rule ID, immutable spec field, TODO/TBD 부재를 검증
```
