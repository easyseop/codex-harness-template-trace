# Codex Port Notes

This repository is the Codex-oriented port of the AI Harness Template with Trace & Replay Test.

The framework design is intentionally preserved:

- Ouroboros workflow remains `interview -> seed -> trd -> decompose -> run -> evaluate -> evolve`.
- `.harness/ouroboros/**` remains the canonical workspace for interviews, seed specs, tasks, evaluations, and templates.
- Runtime Trace still records selected, loaded, evidence, and applied rule IDs.
- Replay Test still validates command behavior against fixtures.
- Gates and methodology plugins remain under `.harness`.
- Pair Mode still separates Navigator, Driver, Test Designer, and Evaluator roles.

The runtime adapter changed:

- `CLAUDE.md` became `AGENTS.md`.
- `.claude/commands` became `.harness/codex-harness/commands`.
- `.claude/agents` became `.harness/codex-harness/agents`.
- `.claude-plugin` became `.codex-plugin`.
- Claude-specific `Agent(...)`, `SendMessage`, and background-agent wording is treated as a role orchestration pattern. Codex may execute it through available multi-agent tools or through a sequential persona fallback.

Install into another project with:

```bash
./init.sh /path/to/project --yes
```

Then use Codex with the generated `AGENTS.md` and `.harness/codex-harness/**` references.
