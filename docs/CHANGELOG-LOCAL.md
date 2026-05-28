# Local Change Log

이 파일은 외부망에서 작업한 변경분을 집에서 개인 GitHub 레포에 커밋할 때 참고하기 위한 간단 이력입니다.

## v3.1 후보 - Trace 출력 누락 및 JSON 안정성 보완

### 1. 산출물 명시 강화

- 변경: `[하네스 추적]`의 `산출물:`을 비워두지 말고, 생성/수정/검증한 파일 경로와 결과를 쓰도록 강화했습니다.
- 이유: 실제 실행 결과에서 산출물이 명확히 보이지 않는 문제가 있었기 때문입니다.
- 기대 효과: 각 단계가 무엇을 만들었는지 trace만 보고도 확인할 수 있습니다.

### 2. 명세 근거 누락 방지 강화

- 변경: 현재 command 파일의 Rule ID를 command 수행 자체의 명시 규칙으로 보고, `[명세 근거]`에 최소 1개 이상 포함하도록 보강했습니다.
- 이유: command Rule ID가 있는데도 evidence가 생략되는 문제가 있었기 때문입니다.
- 기대 효과: 각 단계의 판단 근거가 더 안정적으로 사용자 출력에 남습니다.

### 3. `적용 이유`를 `적용 결과`로 변경

- 변경: `[명세 근거]` 양식의 `적용 이유:`를 `적용 결과:`로 바꿨습니다.
- 이유: 사용자가 보고 싶은 것은 단순 이유보다 “이 규칙이 산출물에 어떻게 반영됐는지”였기 때문입니다.
- 기대 효과: evidence가 실제 결과와 더 직접적으로 연결됩니다.

### 4. command evidence 누락 시 finalizer 실패 처리

- 변경: core command finalizer 실행에 `--require-command-evidence`를 추가했습니다.
- 이유: 전체 evidence를 억지로 강제하지 않고, 현재 command 파일 Rule ID라는 최소 실행 근거만 필수로 잡기 위해서입니다.
- 기대 효과: command 근거 누락은 `Trace 검증: FAIL`로 드러나고, 추가 spec/persona/domain evidence는 실제로 적용했을 때만 남길 수 있습니다.

### 5. Runtime Trace JSON 생성 안정화

- 변경: `record-runtime-trace.sh`, `mark-loaded-file.sh`의 JSON 문자열/배열 생성을 Python 표준 `json` 모듈 기반으로 바꿨습니다.
- 이유: summary나 path에 줄바꿈, 따옴표, 역슬래시, 한글이 들어갈 때 JSON 문법 오류가 날 수 있었기 때문입니다.
- 기대 효과: trace JSON/JSONL 생성 안정성이 높아집니다.

### 6. JSON 오류 메시지 개선

- 변경: finalizer가 JSON/JSONL 파싱 실패 시 파일 경로, line, column을 출력하도록 개선했습니다.
- 이유: JSON 문법 오류가 났을 때 어느 파일의 어느 위치가 문제인지 바로 알기 위해서입니다.
- 기대 효과: 디버깅 시간이 줄어듭니다.

## v3 후보 - Trace 신뢰도 및 누락 방지 개선

### 1. 사용자 출력 한국어화

- 변경: `[Harness Trace]`, `[Spec Evidence]`, `Trace Verification` 등 사용자-facing trace 문구를 `[하네스 추적]`, `[명세 근거]`, `Trace 검증` 중심으로 정리했습니다.
- 이유: 팀원이 하네스 trace를 처음 봐도 의미를 바로 이해할 수 있게 하기 위해서입니다.
- 기대 효과: trace 로그와 README 설명의 용어가 맞춰져 온보딩이 쉬워집니다.

### 2. `[하네스 추적]` 양식에 `산출물` 추가

- 변경: 필수 출력 양식에 `산출물:` 항목을 추가했습니다.
- 이유: 각 단계에서 무엇이 생성됐는지 trace와 함께 확인하기 위해서입니다.
- 기대 효과: trace가 단순 설명이 아니라 실제 workflow 결과와 연결됩니다.

### 3. 명세 근거 출력 조건 보강

- 변경: 현재 command 파일의 Rule ID도 명시 규칙으로 보고 `[명세 근거]`에 최소 1개 이상 포함하도록 보강했습니다.
- 이유: command 자체가 적용 규칙인데도 evidence가 생략되는 문제를 줄이기 위해서입니다.
- 기대 효과: 각 단계의 판단 근거가 사용자 출력과 runtime trace에 더 안정적으로 남습니다.

### 4. finalizer에 `PASS / WARNING / FAIL`과 이유 추가

- 변경: `trace/finalize-runtime-trace.py`가 `trace_status`, `trace_reasons.pass`, `trace_reasons.warning`, `trace_reasons.failure`를 저장하고 콘솔에도 이유를 출력하도록 개선했습니다.
- 이유: loaded 누락이나 evidence 불일치가 났을 때 왜 실패했는지 바로 알기 위해서입니다.
- 기대 효과: trace 실패 원인을 사람이 다시 추적하는 시간이 줄어듭니다.

### 5. optional selected 파일은 `WARNING`으로 분리

- 변경: required loaded 누락은 `FAIL`, optional selected 파일의 loaded 미기록은 `WARNING`으로 분리했습니다.
- 이유: selected에 있었지만 실제 참고하지 않았을 수 있는 파일까지 무조건 실패로 단정하지 않기 위해서입니다.
- 기대 효과: trace 검증이 더 정직해지고, 과도한 FAIL을 줄입니다.

### 6. `--expect-step`으로 이전 trace 오사용 방지

- 변경: finalizer에 `--expect-step <step>` 옵션을 추가하고 각 command가 자기 step을 넘기도록 했습니다.
- 이유: `/run` 실행 중 이전 `/seed`나 `/evaluate` trace를 잘못 검증하는 상황을 막기 위해서입니다.
- 기대 효과: 현재 command의 Runtime Trace가 없거나 다른 단계 trace를 잡으면 `FAIL`로 드러납니다.

### 7. trace 누락 방지 지시 강화

- 변경: `AGENTS.md`, `templates/AGENTS.md.hbs`, 각 Ouroboros command에 Runtime Trace 시작, 현재 command loaded 기록, final trace gate 실행을 preflight/postflight gate로 명시했습니다.
- 이유: Codex가 trace 시작이나 finalizer 실행을 빠뜨리는 경우를 줄이기 위해서입니다.
- 기대 효과: md 기반 하네스 안에서 가능한 수준의 강제성이 높아집니다.

### 8. trace 한계 문서화

- 변경: README와 `trace/README.md`에 loaded가 OS read hook이 아니며, loaded 없음만으로 실제 미열람과 기록 누락을 구분할 수 없다고 명시했습니다.
- 이유: trace 신뢰도를 과장하지 않기 위해서입니다.
- 기대 효과: 팀이 trace를 감사 가능한 외부 증거로 쓰되, 한계도 함께 이해할 수 있습니다.

### 9. replay 결과 trace에 상태와 이유 포함

- 변경: replay runner가 `trace_status`와 `trace_reasons`를 actual trace markdown에 포함하도록 했습니다.
- 이유: replay 결과에서도 왜 PASS/WARNING/FAIL이 났는지 함께 보이게 하기 위해서입니다.
- 기대 효과: replay artifact만 봐도 trace 검증 상태를 파악할 수 있습니다.

## 추천 커밋 메시지

```text
feat: improve runtime trace verification and Korean trace output
```

또는 조금 더 나누면:

```text
feat: add trace status reasons and step verification
docs: clarify trace reliability and limitations
```
