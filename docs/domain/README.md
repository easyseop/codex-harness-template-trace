# 외부망 개발과 사내 도메인 주입 가이드

이 문서는 `/run` 단계와 사내 개발 도메인 주입에 대해 나눈 질문과 답변을 팀 공유용으로 정리한 문서입니다.

목표는 분명합니다.

```text
외부망에서 최대한 완성도 있게 개발한 뒤,
내부망 반입 후 추가 개발을 최소화한다.
```

---

## 핵심 결론

사내 개발 도메인은 `/run` 때 처음 넣으면 늦습니다.

가능하면 아래 순서처럼 **/seed, /trd, /decompose 전에** 반영해야 합니다.

```text
도메인 규칙/업무 용어
  → /interview 또는 /seed 전에 반영

내부 API/DB/아키텍처 제약
  → /trd 전에 반영

내부망 반입 전략과 교체 지점
  → /decompose 전에 반영

구현 세부 힌트
  → /run 중 참고

실제 내부망 연결값
  → 내부망 반입 후 적용
```

`/run`은 이미 정리된 명세와 설계를 구현하는 단계에 가깝습니다. 따라서 도메인 지식이 `/run` 이후에 들어오면, 이미 잘못된 전제로 구현된 부분을 내부망에서 다시 고쳐야 할 가능성이 큽니다.

---

## Q1. `/run`에서 사내 도메인을 넣으면 안 되나?

넣을 수는 있지만, 가장 좋은 시점은 아닙니다.

`/run`은 보통 아래 입력을 참고합니다.

```text
- 최신 seed spec
- docs/TRD.md
- .harness/ouroboros/tasks/*
- ARCHITECTURE_INVARIANTS.md
- commands/run.md
```

따라서 `/run`에서 도메인을 처음 주입하면 구현 일부에는 반영될 수 있지만, 명세, 기술 설계, 태스크 분해가 이미 틀어졌을 수 있습니다.

권장 흐름은 다음과 같습니다.

```text
/interview
  도메인에서 더 물어봐야 할 질문 식별

/seed
  업무 용어, 상태 전이, 핵심 규칙을 명세에 반영

/trd
  내부 API/DB 계약, adapter 경계, mock 전략을 설계에 반영

/decompose
  내부망 반입 시 교체할 지점을 태스크로 분해

/run
  위 계약을 기준으로 구현

/evaluate
  내부망 반입 체크리스트로 검증
```

---

## Q2. 새 command를 만드는 게 좋나, 기존 md를 수정하는 게 좋나?

둘 다 필요하지만 역할을 나누는 것이 좋습니다.

```text
항상 적용되어야 하는 도메인/표준
  → md 문서로 둔다

도메인 문서를 만들고, 점검하고, 갱신하는 절차
  → command로 만든다
```

### md 파일에 두는 것이 맞는 것

| 대상 | 권장 위치 | 이유 |
|------|-----------|------|
| 레이어 규칙, 금지 아키텍처, 보안 불변 규칙 | `ARCHITECTURE_INVARIANTS.md` | 모든 단계에 항상 적용되는 최상위 규칙 |
| 코딩 컨벤션, 테스트 기준, 네이밍 | `docs/code-convention.yaml` 또는 별도 standards 문서 | 반복 적용되는 표준 |
| 사내 업무 용어, 상태 전이, 핵심 도메인 규칙 | `docs/domain/*.md` | `/seed`, `/trd`, `/run`, `/evaluate`가 공통 참고 |
| 내부 API/DB 계약의 반출 가능한 요약 | `docs/domain/api-contracts.redacted.md`, `docs/domain/data-contracts.md` | 외부망에서 내부망 연결부를 미리 설계하기 위함 |
| 내부망 반입 전 체크리스트 | `docs/domain/import-readiness-checklist.md` | `/evaluate`에서 검증 기준으로 사용하기 좋음 |

### command로 만드는 것이 맞는 것

| command | 역할 |
|---------|------|
| `/domain-context` 또는 `/prepare-import` | 반출 가능한 도메인 정보를 수집하고, 민감정보를 제거하고, 도메인 문서 누락을 점검 |

command는 “도메인 문서를 만드는 절차”입니다. 기존 `/seed`, `/trd`, `/decompose`, `/run`, `/evaluate`는 그 문서를 읽고 반영하는 단계입니다.

---

## Q3. 도메인 문서는 어디에 두는 게 좋나?

하나의 경로에 모으고, 영역별로 나누는 것이 좋습니다.

권장 구조:

```text
docs/domain/
  README.md
  glossary.md
  business-rules.md
  data-contracts.md
  api-contracts.redacted.md
  integration-boundaries.md
  import-readiness-checklist.md
  examples.redacted.md
```

각 파일의 역할은 다음과 같습니다.

| 파일 | 역할 |
|------|------|
| `README.md` | 도메인 pack의 목적, 민감정보 금지 원칙, 문서 읽는 순서 |
| `glossary.md` | 사내 용어, 약어, 도메인 개념 정의 |
| `business-rules.md` | 상태 전이, 업무 규칙, 예외 조건, 금지 처리 |
| `data-contracts.md` | 데이터 모델, 필드 의미, 검증 규칙. 실제 운영 데이터는 제외 |
| `api-contracts.redacted.md` | 내부 API 계약의 반출 가능한 요약. 실제 URL/token 제외 |
| `integration-boundaries.md` | 내부망에서 교체해야 할 adapter/interface 경계 |
| `import-readiness-checklist.md` | 내부망 반입 전 확인할 항목 |
| `examples.redacted.md` | 민감정보가 제거된 예시 요청/응답, 케이스 |

---

## 단계별로 어떤 도메인 문서를 참고하나?

| 단계 | 주로 참고할 도메인 문서 |
|------|--------------------------|
| `/interview` | `README.md`, `glossary.md`, `business-rules.md` |
| `/seed` | `glossary.md`, `business-rules.md`, `data-contracts.md` |
| `/trd` | `api-contracts.redacted.md`, `integration-boundaries.md`, `data-contracts.md` |
| `/decompose` | `integration-boundaries.md`, `import-readiness-checklist.md` |
| `/run` | seed, TRD, task, `integration-boundaries.md`, api/data contracts |
| `/evaluate` | `import-readiness-checklist.md`, `business-rules.md`, `integration-boundaries.md` |

---

## 외부망 도메인 문서에 넣어도 되는 것

```text
- 업무 용어
- 상태 전이
- 입력/출력 필드 의미
- 검증 규칙
- 내부 API의 형태
- adapter로 분리해야 할 지점
- 내부망 반입 후 바꿔 끼울 부분
- 민감정보가 제거된 예시
```

## 넣으면 안 되는 것

```text
- 실제 고객 데이터
- 운영 DB 접속 정보
- 내부 시스템 URL
- API key/token
- 사내 비밀 정책 원문
- 식별 가능한 로그/샘플
```

---

## 권장 운영 방식

1. 외부망에 반출 가능한 도메인 pack을 `docs/domain/`에 작성한다.
2. `/interview` 또는 `/seed` 전에 도메인 pack을 먼저 확인한다.
3. `/seed`에서 도메인 규칙을 명세에 반영한다.
4. `/trd`에서 내부망 연결부를 adapter/interface로 분리한다.
5. `/decompose`에서 내부망 반입 전 교체 지점을 태스크로 드러낸다.
6. `/run`에서는 내부 의존성을 직접 붙이지 않고 fake/adapter/interface 기준으로 구현한다.
7. `/evaluate`에서 `import-readiness-checklist.md` 기준으로 내부망 반입 준비 상태를 검증한다.

---

## 향후 하네스에 추가하면 좋은 것

현재 문서는 가이드입니다. 더 강하게 운영하려면 다음을 추가할 수 있습니다.

```text
commands/domain-context.md
  도메인 pack을 생성/점검하는 command

commands/seed.md
commands/trd.md
commands/decompose.md
commands/run.md
commands/evaluate.md
  docs/domain/README.md가 있으면 읽기 순서를 따르도록 최소 지시 추가

trace/record-runtime-trace.sh
  docs/domain/*를 단계별 selected 후보에 포함

trace/trace-policy.json
  핵심 도메인 문서가 loaded에서 빠지면 Trace Verification: FAIL 처리

tests/cases/*
  도메인 규칙이 output과 trace에 반영되는지 replay case 추가
```

---

## 한 줄 요약

사내 도메인 지식은 `/run` 때 처음 주입하는 것이 아니라, `docs/domain/`에 반출 가능한 계약 문서로 정리한 뒤 `/seed`와 `/trd` 전에 반영하는 것이 좋습니다. command는 도메인 문서를 만드는 절차로 두고, md 문서는 항상 참고되는 기준으로 두는 방식이 가장 안전합니다.
