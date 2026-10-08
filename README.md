# DeepAIRA starter pack (working codename)

A repo-ready scaffold for building a life-admin platform with AI-DLC and AI quality engineering. It contains the documents, instructions, prompts, golden datasets, context rules and the checks that bind them together.

## Read in this order
1. `docs/00-project-brief.md`
2. `docs/01-architecture-decisions.md` - decisions and the tool for every AI-DLC phase/stage
3. `docs/02` privacy, `docs/03` AI-QE standards, `docs/04` tool vetting, `docs/05` context map
4. `docs/06-open-items.md` - what is unverified or undecided
5. `docs/07-inception-kickoff.md` - how to start

## Layout
| Path | Purpose |
|---|---|
| `CLAUDE.md`, `aidlc/.../aidlc-shared/` | Instructions loaded by Claude Code and every AI-DLC stage |
| `prompts/` | Versioned prompts, output schemas, `registry.toml` |
| `qa/datasets/` | Golden datasets + manifests (31 AI-drafted seed cases) |
| `qa/*.toml` | Contexts, data map, tool register, release blockers, cost budgets |
| `src/deepaira/` | Empty context packages |
| `.importlinter` | Import contracts generated from `qa/contexts.toml` |
| `tools/` | `governance.py` (all consistency checks), `score_extraction.py` (deterministic scorer) |
| `tests/` | Tests for the tools (unittest, pytest-compatible) |

## Honest status
- Seed dataset labels are AI-drafted; they need human review.
- Nothing is approved: prompts are drafts, tools are pending vetting, no eval has run.
- Import contracts have not been executed; run `lint-imports`.
- Thresholds marked [ESTIMATE] are starting points.
- `governance.py release-gate` fails today on purpose.
