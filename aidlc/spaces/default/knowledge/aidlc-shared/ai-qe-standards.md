# AI quality engineering rules (summary of docs/03-ai-qe-standards.md)

- Prompts are versioned files listed in prompts/registry.toml with pinned SHA-256 hashes. Approved versions are immutable; a change is a new version plus a new eval run.
- Every prompt has an output JSON schema in prompts/schemas/. Model output is validated before use; invalid output is an error, not a guess.
- Golden datasets live in qa/datasets/<name>/ as JSONL with a manifest. Labels must be human-verified before a dataset can be marked release. Synthetic data only; the PII scan must pass.
- Scoring is deterministic (tools/score_extraction.py): field accuracy plus blockers (fabrication, unflagged ambiguity, wrong date without confirmation, injection compliance, missing output). No judge model for pass/fail.
- Release blockers in qa/release_blockers.toml each map to a named test. A blocker failing means no release.
- Cost: every task has a budget in qa/cost_budgets.toml; cost more than doubling versus baseline fails the gate.
- Run `python3 tools/governance.py check` before every commit. `release-gate` must pass before any outside user.
- Tests must be able to fail: add a negative test for every new rule.
