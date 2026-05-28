---
name: codex-harness
description: Use when running or maintaining the Codex Harness: an Ouroboros specification-first workflow with interview, seed, TRD, decompose, run, evaluate, evolve, trace evidence, replay tests, gates, methodology plugins, and pair-mode roles adapted for Codex.
---

# Codex Harness

This skill adapts the original AI Harness framework to Codex while preserving its core design:

- Ouroboros workflow: `interview -> seed -> trd -> decompose -> run -> evaluate -> evolve`
- Rule ID based command and persona instructions
- Runtime Trace and Spec Evidence
- Replay Test fixtures and assertions
- Architecture gates and methodology plugins
- Pair Mode role separation: Navigator, Driver, Test Designer, Evaluator

## Workflow

When the user asks for a harness step, load the matching command reference from `references/commands/` and follow it as the step contract.

| User intent | Reference |
| --- | --- |
| clarify requirements | `references/commands/interview.md` |
| create seed spec | `references/commands/seed.md` |
| create technical design | `references/commands/trd.md` |
| decompose work | `references/commands/decompose.md` |
| implement | `references/commands/run.md` |
| evaluate | `references/commands/evaluate.md` |
| evolve spec | `references/commands/evolve.md` |
| recover from failure | `references/commands/unstuck.md` or `references/commands/rollback.md` |
| replay a step | `references/commands/replay-test.md` |

Before substantial code work, read `AGENTS.md` and `ARCHITECTURE_INVARIANTS.md` when present.

## Trace Discipline

If `.harness/trace/record-runtime-trace.sh` exists, start a runtime trace before doing the body of a harness step.

Use installed project paths first:

- Command references: `.harness/codex-harness/commands/<step>.md`
- Persona references: `.harness/codex-harness/agents/<persona>.md`
- Template repo fallback: `commands/<step>.md` and `agents/<persona>.md`

After reading a command, reference, or persona file, call `.harness/trace/mark-loaded-file.sh --path "<file>"` when available. Before the final response for a step, save Spec Evidence to `.harness/trace/current-spec-evidence.md` and run `.harness/trace/finalize-runtime-trace.py` according to the loaded command reference.

Do not claim runtime verification when trace finalization fails or was not run.

## Pair Mode In Codex

Preserve the Pair Mode role structure, but use Codex execution semantics:

- Navigator: planning and review persona. Load `references/agents/navigator.md`.
- Driver: the main Codex agent implementing the selected plan.
- Test Designer: independent test design persona. Load `references/agents/test-designer.md`.
- Evaluator: post-implementation verification persona. Load `references/agents/evaluator.md`.

If a multi-agent tool is available, the Navigator and Test Designer may run as separate agents. If not, perform the roles sequentially in the main Codex session and explicitly label which role is active. Keep Test Designer independent by deriving tests from the seed spec and acceptance criteria, not from the implementation details.

## Output

For major harness steps, include:

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

Also include `[명세 근거]` when a command or rule ID was applied.
