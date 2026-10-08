# 07 - Kickoff: from this pack to the first AI-DLC run

## Step 1 - Create the repo (about 15 minutes)
1. On GitHub create a **private** repo (suggested name `deepaira`). Do not add a README or license yet.
2. Unzip this pack, open the folder in VS Code, then in a terminal: `git init`, `git add .`, `git commit -m "Starter pack"`, add the remote, push.
3. Make sure Claude Code is signed in inside VS Code.

## Step 2 - Local checks
```
python3 tools/governance.py check          # 0 errors expected, warnings are the to-do list
python3 -m unittest discover -s tests -v   # governance + scorer tests
pip install ruff import-linter             # then:
lint-imports                               # first real run of the context contracts [not yet verified]
```
`python3 tools/governance.py release-gate` is **expected to fail** until prompts are approved, datasets are release, tools are vetted and actions are pinned.

## Step 3 - Install AI-DLC
Follow the README of awslabs/aidlc-workflows at the version you download (v2.10.0 was reviewed). The docs disagree on commands; see 06-open-items. Afterwards:
1. Re-read `.claude/settings.json`; remove broad pre-approved permissions you do not want; merge `config/claude-settings.snippet.json`.
2. Confirm which model provider it uses. The default may route through Bedrock; set it to the Anthropic API/Claude Code login you intend to use.
3. Keep `aidlc/spaces/default/knowledge/aidlc-shared/` as provided (loaded at every stage).

## Step 4 - Start Inception
In Claude Code:
```
/aidlc mvp --depth comprehensive --test-strategy comprehensive
```
Intent to give it: "Build DeepAIRA per docs/00-project-brief.md and docs/01-architecture-decisions.md." Stages will pause at approval gates.

## Gate checklist (before approving each stage)
- [ ] Does it respect CLAUDE.md and docs/01 (stack, contexts, tools)?
- [ ] Did it add any tool or dependency not in the register? Reject.
- [ ] Are unknowns marked [VERIFY] instead of invented?
- [ ] Does the stage list its tests/datasets/blockers?
- [ ] Is anything an LLM does being computed instead by the engine?
- [ ] `python3 tools/governance.py check` still has 0 errors.
- [ ] Cost: did the stage need more AI usage than planned? Note it for the week budget.

## Weekly rhythm (15-20 h)
Plan 1 h, build 10-14 h, review diffs + run gates 3 h, update open items 1 h.
