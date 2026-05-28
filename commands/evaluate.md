---
description: Run 3-stage verification (Mechanical gates → Semantic AC compliance → Judgment quality) after /run. ALWAYS run before committing. Blocks at Stage 1 failures — no Stage 2 until gates pass.
---

## Trace Discipline

- Trace is evidence bookkeeping only. It records which command references, persona references, specs, docs, and source files informed the work.
- Never let trace bookkeeping replace the primary behavior of the current command or persona.
- Ask the required interview questions, produce the required seed/TRD/tasks/code/evaluation, and use trace as supporting evidence while doing that work.
- When practical, mark loaded files with `.harness/trace/mark-loaded-file.sh --path "<file>"`, but do not stall or loop on trace setup before serving the user.
- If trace tooling is unavailable, continue the command and explicitly mention the trace limitation in the final output.



# /evaluate — 3-Stage Verification

> 구현 결과를 3단계로 검증한다

## Trace Metadata

- Rule ID: `RULE-EVAL-001`
- Runtime Trace 시작: 스크립트가 있으면 Phase 0 전에 `.harness/trace/record-runtime-trace.sh --step evaluate --request-type verification --summary "<user request summary>"`를 실행한다.
- Loaded File Trace 기록: command/reference/agent 파일을 읽은 뒤, 스크립트가 있으면 `.harness/trace/mark-loaded-file.sh --path "<file>"`로 loaded 기록을 남긴다. 특히 현재 command 파일 자체를 먼저 기록한다. 설치 프로젝트는 `.harness/codex-harness/commands/evaluate.md`, 템플릿 레포는 `commands/evaluate.md`를 사용한다.
- AI-facing Trace 출력: `.harness/trace/latest-runtime-trace-final.json`을 우선 참고하고, 없으면 `.harness/trace/latest-runtime-trace.json`을 참고한다. selected, loaded, applied evidence를 구분해서 설명한다.
- 산출물 명시: `[하네스 추적]`의 `산출물`에는 생성/수정/검증한 파일 경로와 결과를 반드시 적는다. 파일 산출물이 없으면 `없음 - <이유>`를 적는다.
- 명세 근거 출력: 현재 command 파일의 Rule ID를 포함해 명시적으로 적용한 `file_path#RULE-ID` 근거를 최종 응답의 `[명세 근거]`에 포함한다. 적용할 Rule ID가 정말 없을 때만 `[명세 근거]` 블록과 `No explicit spec rule found.` 문구를 강제로 출력하지 않는다.
- Final Trace Gate 검증: 명세 근거 블록을 `.harness/trace/current-spec-evidence.md`에 저장하고 `python3 .harness/trace/finalize-runtime-trace.py --expect-step evaluate --evidence-file .harness/trace/current-spec-evidence.md --require-command-evidence --require-loaded-selected command --policy .harness/trace/trace-policy.json --require-policy`를 실행한다. 현재 command evidence가 누락되면 `python3 .harness/trace/finalize-runtime-trace.py --expect-step evaluate --require-command-evidence --require-loaded-selected command --policy .harness/trace/trace-policy.json --require-policy`를 실행해 누락을 FAIL로 드러낸다. 실패하면 `Trace 검증: FAIL`을 보고하고 runtime verification이 된 것처럼 말하지 않는다.
- Trace 누락 방지: Runtime Trace 시작, 현재 command 파일 loaded 기록, Final Trace Gate는 이 command의 preflight/postflight gate다. 누락되면 `Trace 검증: FAIL` 또는 `WARNING`과 이유를 보고하고 runtime-verified라고 말하지 않는다.

## Instructions

You are now the **Evaluator** agent. Verify the implementation against the seed spec.

### Phase 0: State Audit (FIRST STEP)

`RULE-EVAL-001`

1. `RULE-EVAL-001-01` **Locate seed spec** — `.harness/ouroboros/seeds/seed-v*.yaml` (latest)
   - If none → abort: "No seed to evaluate against. Run /interview → /seed first."
2. `RULE-EVAL-001-02` **Check for prior evaluations** — `.harness/ouroboros/evaluations/`
   - If recent (<1h) PASS with no code changes → skip re-evaluation
   - If recent FAIL → surface prior findings; focus on whether they were addressed
3. `RULE-EVAL-001-03` **Detect scope** — which files changed since last commit? (`git diff --stat`)
   - Narrow evaluation to changed files when possible

### Subagent Delegation

검증의 정확도와 속도를 높이기 위해 **subagent를 활용**합니다:

```
Main Agent (Evaluator)
  ├─ Subagent → Stage 1 (Mechanical): 게이트 실행을 별도 에이전트에 위임
  │     └ .harness/detect-violations.sh 실행 + 결과 보고
  ├─ Main    → Stage 2 (Semantic): 시드 대비 AC/목표/제약 직접 검증
  └─ Main    → Stage 3 (Judgment): 코드 품질 판단
```

**Codex에서 subagent 사용**:
- Stage 1의 기계적 검증은 `Agent` 도구로 별도 subagent에 위임 가능
- subagent가 게이트 스크립트를 실행하고 결과만 반환
- 메인 에이전트는 Stage 2/3에 집중하여 병렬 처리 효과

### Stage 1: Mechanical Verification ($0 cost)

`RULE-EVAL-002`

Run automated checks — these cost nothing and catch obvious issues:

```bash
# 1. RULE-EVAL-002-01 Harness gates
.harness/detect-violations.sh

# 2. RULE-EVAL-002-02 Layer separation check
.harness/gates/check-layers.sh

# 3. RULE-EVAL-002-03 Lint (if available)
# TypeScript: npx eslint . --quiet
# Python: ruff check . || python -m flake8

# 4. RULE-EVAL-002-04 Type check (if available)
# TypeScript: npx tsc --noEmit
# Python: mypy . || pyright

# 5. RULE-EVAL-002-05 Build (if available)
# Next.js: npm run build
# Python: python -m py_compile

# 6. RULE-EVAL-002-06 Tests (if available)
# npm test || pytest
```

**Report format**:
```
═══ Stage 1: Mechanical ═══════════════════════
  Harness Gates:    PASS | FAIL
  Layer Check:      PASS | FAIL | SKIP
  Lint:             PASS | FAIL | SKIP (not configured)
  Type Check:       PASS | FAIL | SKIP
  Build:            PASS | FAIL | SKIP
  Tests:            PASS | FAIL | SKIP
  ─────────────────────────────
  Result:           PASS | FAIL
```

If Stage 1 fails → stop. Fix mechanical issues before proceeding.

### Stage 2: Semantic Verification

`RULE-EVAL-003`

Read the seed spec from `.harness/ouroboros/seeds/` and verify:

**2a. Acceptance Criteria Compliance**
`RULE-EVAL-003-01`

For each AC in the seed:
```
  AC-001: "{description}"
    Status:   MET | PARTIALLY MET | NOT MET
    Evidence: "{file:line or explanation}"
    
  AC-002: "{description}"
    Status:   MET
    Evidence: "{file:line}"
```

**2b. Goal Alignment**
`RULE-EVAL-003-02`

- Does the implementation solve the stated goal?
- Are there features NOT in the spec that were added? (scope creep)
- Are there non_goals that were accidentally implemented?

**2c. Constraint Compliance**
`RULE-EVAL-003-03`

- Check each `must` constraint → is it satisfied?
- Check each `must_not` constraint → is it violated?

**2d. Ontology Drift**
`RULE-EVAL-003-04`

- Do the actual data models match the seed's ontology?
- Are entity names, field names, relationships preserved?

**2e. Layer Architecture Compliance**
`RULE-EVAL-003-05`

- 모든 Presentation 코드가 presentation 디렉토리에 있는가?
- 모든 Logic 코드가 logic/services 디렉토리에 있는가?
- 모든 Data 코드가 data/repositories 디렉토리에 있는가?
- Presentation → Data 직접 import가 없는가?
- Logic → Presentation 역의존이 없는가?
- 레이어 간 통신이 DTO/Interface를 통해서 이루어지는가?

```bash
# 자동 검사
.harness/gates/check-layers.sh
```

**2f. Test Coverage by Layer**
- Logic 레이어 테스트: 순수 비즈니스 로직이 테스트되고 있는가?
- 각 모듈의 책임만 정확히 테스트하고 있는가?
- mock이 레이어 경계에서만 사용되고 있는가?

**Report format**:
```
═══ Stage 2: Semantic ═════════════════════════
  AC Compliance:    {met}/{total} criteria met
  Goal Alignment:   ALIGNED | DRIFTED
  Constraint Check: PASS | VIOLATION ({detail})
  Ontology Drift:   LOW | MEDIUM | HIGH
  Layer Compliance: PASS | VIOLATION ({detail})
  Test by Layer:    Logic {%} | Data {%} | Presentation {%}
  ─────────────────────────────
  Result:           PASS | FAIL
```

### Stage 3: Judgment (optional)

Only run if Stage 2 has ambiguous results:

Review the overall quality:
- Is the code readable and maintainable?
- Are edge cases handled?
- Is error handling appropriate?
- Would this pass code review?

```
═══ Stage 3: Judgment ═════════════════════════
  Code Quality:     {1-5}/5
  Edge Cases:       COVERED | GAPS ({list})
  Error Handling:   ADEQUATE | INSUFFICIENT
  Review Ready:     YES | NO ({reason})
  ─────────────────────────────
  Result:           PASS | FAIL
```

### Final Verdict

```
═══ EVALUATION SUMMARY ════════════════════════
  Stage 1 (Mechanical): {PASS|FAIL}
  Stage 2 (Semantic):   {PASS|FAIL}
  Stage 3 (Judgment):   {PASS|FAIL|SKIP}
  ═════════════════════════════
  VERDICT:              PASS | FAIL

  {If FAIL}
  Issues to fix:
    1. {issue}
    2. {issue}
  
  Recommendation: Fix issues and re-run /evaluate

  {If PASS}
  Implementation verified against seed spec.
  Ready for commit/PR.
```

### Save Results

Save to `.harness/ouroboros/evaluations/eval-{seed-version}-{date}.yaml`:
```yaml
date: "YYYY-MM-DDTHH:MM:SS"
seed_ref: "seed-v{N}.yaml"
stages:
  mechanical:
    result: "pass|fail"
    details: {}
  semantic:
    result: "pass|fail"
    ac_compliance: {met: N, total: M}
    goal_alignment: "aligned|drifted"
    ontology_drift: "low|medium|high"
  judgment:
    result: "pass|fail|skip"
verdict: "pass|fail"
issues: []
```

### Replay 확인 지점

`/evaluate` 완료 후, `[하네스 추적]`의 `다음 단계`에 아래 두 선택지를 함께 제안한다:

```text
1. PASS면 commit/PR 준비, FAIL이면 이슈를 수정하거나 `/evolve`로 진행
2. `/replay-test evaluate <case>`로 evaluator trace, expected PASS/FAIL status, fail reason, 금지 false positive를 검증
```
