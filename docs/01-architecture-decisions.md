# 01 - Architecture decisions and the tool map for every AI-DLC phase

Status key: **Decided** = founder confirmed. **Proposed** = my recommendation, needs the founder's yes. **Open** = unresolved, see 06-open-items.md. Every code dependency named here is in `qa/tool-register.toml` and none is "approved" until vetted (docs/04). Process tools (VS Code, git, GitHub, Claude Code, Figma, Locust/k6) are not code dependencies; vet them before relying on them.

## Part A - Decisions

| ID | Decision | Status | Why / exit plan |
|---|---|---|---|
| ADR-01 | Method: AI-DLC (awslabs/aidlc-workflows v2.10.0, MIT-0) run through Claude Code in VS Code | Decided | Gives stages, approval gates and an audit trail. Exit: the artifacts are plain markdown in the repo. |
| ADR-02 | Backend: Django + PostgreSQL | Decided | Python is the founder's strongest language; mature, secure defaults. |
| ADR-03 | API-first with Django Ninja, OpenAPI as the contract | Decided | One contract feeds the web app, the mobile app and the contract tests. Exit: DRF. |
| ADR-04 | Web: React + TypeScript (Vite) PWA | Decided | Same code base reaches mobile via Expo later. Chosen over htmx because mobile and PWA were requirements. |
| ADR-05 | Mobile: PWA first, Expo later | Decided | iPhone web push needs Add to Home Screen; email is the reliable channel. Expo Go is free for testing; TestFlight needs the $99 Apple account [VERIFY current price]. |
| ADR-06 | Modular monolith with bounded contexts enforced by import-linter | Decided (tool Proposed) | Solo founder: one deployable, hard internal borders. Exit: pytestarch or a custom AST test. |
| ADR-07 | Deterministic engine separate from the LLM | Decided | Dates, time zones, recurrence and conflicts are computed by code and fully testable. |
| ADR-08 | LLM behind a provider interface, only in the `extraction` context | Decided | Swap vendors; enforced by an import contract. |
| ADR-09 | Prompts are versioned files with a registry and pinned hashes | Proposed | Reviewable in git; changes force an eval run. |
| ADR-10 | Golden datasets as JSONL + manifest, human-verified labels, synthetic only | Proposed | Own the data; no vendor lock-in. |
| ADR-11 | Deterministic scoring, no judge model for pass/fail | Proposed | Repeatable, free, explainable. A judge model may be added later for tone only. |
| ADR-12 | Own usage ledger in Postgres first; optional Langfuse cloud hobby tier with synthetic data only | Proposed | Cost and utilization tracking without sending user data to a third party. This answers the "no login, how do we track cost" question: accounts are passwordless but still identified. |
| ADR-13 | Tool vetting policy and tiers | Decided | docs/04. "Open source" means reliable and secure. |
| ADR-14 | Supply-chain controls: lockfiles, actions pinned to SHAs, pip-audit, bandit, gitleaks | Proposed | Enforced by `governance.py release-gate`. |
| ADR-15 | English + US content at launch, localization-ready | Decided | No hard-coded strings; time zones always explicit. |
| ADR-16 | Business: bootstrap; LLC before payments or outside users | Decided | |
| ADR-17 | Tracing of agent work: AI-DLC audit trail (`aidlc-state.md` + audit log) | Decided | Part of the method. |
| ADR-18 | Foreign keys across contexts | **Open** | Interim rule: plain IDs. |
| ADR-19 | Hosting, email-ingest provider, payment provider | **Open** | Decide in Inception (2.8/3.4). Each sits behind an interface. |
| ADR-20 | Final product name | **Open** | DeepAIRA is a codename. |

## Part B - Tool map by AI-DLC phase and stage

AI-DLC v2.10.0 has 5 phases and 33 stages. The **MVP profile** runs 23 and skips 1.2, 1.5, 1.7 and all of Operation; we start there and add Operation stages when there are outside users. Overrides we use: `--depth comprehensive --test-strategy comprehensive`. AI-QE activity appears in every stage, because quality is the founder's area.

Legend: **Run** = executes in the MVP profile. **Skip** = skipped in MVP (revisit trigger given). Tools marked (*) are not yet installed and sit in the register as pending-vetting.

### Phase 0 - Initialization
| Stage | MVP | What happens | Tools | AI-QE activity / gate |
|---|---|---|---|---|
| 0.1-0.3 | Run | Install AI-DLC, configure the space, create the intent folder | Claude Code, VS Code, git, GitHub, `config/claude-settings.snippet.json`, `aidlc/spaces/default/knowledge/` | `governance.py check` passes on the empty pack; permissions deny reading secrets |

### Phase 1 - Ideation
| Stage | MVP | What happens | Tools | AI-QE activity / gate |
|---|---|---|---|---|
| 1.1 Intent Capture | Run | State the product intent | docs/00-project-brief.md, AI-DLC prompts | Intent has measurable success criteria |
| 1.2 Market Research | Skip | Competitor scan | WebSearch (Claude) | Revisit before pricing |
| 1.3 Feasibility | Run | Technical, legal, cost feasibility | docs/06-open-items.md; Optum disclosure check (founder) | Open items recorded, none hidden |
| 1.4 Scope Definition | Run | Pick first slice and trio | Product backlog in markdown | Scope list ties to the six categories |
| 1.5 Team Formation | Skip | Solo founder | - | - |
| 1.6 Rough Mockups | Run | Sketch screens | Claude Design or paper; Figma optional | Each mockup names its states: empty, error, confirm-date |
| 1.7 Approval & Handoff | Skip | Single approver | - | Founder approves in chat |

### Phase 2 - Inception
| Stage | MVP | What happens | Tools | AI-QE activity / gate |
|---|---|---|---|---|
| 2.1 Reverse Engineering | Skip | No existing code | - | Revisit when importing code |
| 2.2 Practices Discovery | Run | Record engineering practices | CLAUDE.md, knowledge files, `qa/tool-register.toml` | Practices are enforceable by a check, not just prose |
| 2.3 Requirements Analysis | Run | Functional and non-functional requirements | AI-DLC requirements template | Each requirement testable; release blockers mapped (`qa/release_blockers.toml`) |
| 2.4 User Stories | Run | Stories with acceptance criteria | Markdown, Given/When/Then | Every story gets at least one golden-dataset case or a test name |
| 2.5 Refined Mockups | Run | Clickable detail | Figma optional | Accessibility notes per screen |
| 2.6 Domain Design | Run | Bounded contexts, data map | `qa/contexts.toml`, `.importlinter`, import-linter, Mermaid (docs/05) | `governance.py check --only contexts datamap` |
| 2.7 Units Generation | Run | Split into buildable units | AI-DLC units | Each unit lists its tests up front |
| 2.8 Contract Design | Run | API contract first | Django Ninja (OpenAPI), Spectral*, oasdiff*, openapi-typescript* | OpenAPI lint clean; breaking-change check wired |
| 2.9 Delivery Planning | Run | Order units, weekly budget | AI-DLC plan, 15-20 h/week budget | Plan includes eval-run and review time |

### Phase 3 - Construction
| Stage | MVP | What happens | Tools | AI-QE activity / gate |
|---|---|---|---|---|
| 3.1 Functional Design | Run | Detailed behaviour per unit | Markdown, Hypothesis property list | Properties written before code (for example "resolved start is always timezone-aware") |
| 3.2 NFR Requirements | Run | Performance, security, privacy, cost targets | `qa/cost_budgets.toml`, `qa/data-map.toml` | Budgets numeric; [ESTIMATE] flagged until measured |
| 3.3 NFR Design | Run | How to meet them | Django security settings, rate limits | Threat list for prompt injection and cross-user access |
| 3.4 Infrastructure Design | Run | Local and cloud shape | Docker, PostgreSQL, uv; hosting provider (Open, ADR-19) | Secrets plan; backup and restore test planned |
| 3.5 Code Generation | Run | Claude Code writes code | Claude Code, Django, Django Ninja, psycopg, anthropic (extraction only), React, TypeScript, Vite, vite-plugin-pwa*, pre-commit | Test-first: failing test, then code. Pre-commit runs governance + ruff. Founder reviews diffs |
| 3.6 Build and Test | Run | Run the whole test pyramid | pytest, pytest-cov, Hypothesis, time-machine*, mutmut* (engine), Schemathesis*, Vitest, pytest-playwright, `tools/score_extraction.py`, Promptfoo (watch) or own runner | See Part C |
| 3.7 CI Pipeline | Run | Automate gates | GitHub Actions (pinned SHAs), ruff, mypy, bandit, pip-audit, Semgrep*, gitleaks*, `lint-imports`, `governance.py` | PR cannot merge unless all gates are green |

### Phase 4 - Operation (Skip in MVP; start before the first outside user)
| Stage | What happens | Tools | AI-QE activity / gate |
|---|---|---|---|
| 4.1 Deployment Pipeline | Automated deploys | GitHub Actions, Docker | Deploy only from a green main |
| 4.2 Environment Provisioning | Staging and production | Hosting provider (Open), PostgreSQL | Staging uses synthetic data only |
| 4.3 Deployment Execution | Roll out | Docker, migrations | Smoke test; rollback rehearsed |
| 4.4 Observability Setup | Logs, metrics, LLM tracing | Own usage ledger (metering), Langfuse cloud hobby tier (watch, synthetic only) | No raw text in logs; cost dashboard |
| 4.5 Incident Response | Runbooks | Markdown runbooks, audit context | Data-exposure drill |
| 4.6 Performance Validation | Load and cost at scale | Locust or k6 (not yet in register) | Cost-per-extraction vs budget |
| 4.7 Feedback & Optimization | Learn from use | Eval runs on real-failure cases added to datasets (after consent) | New failures become new golden cases |

## Part C - The test pyramid and where each tool sits

| Layer | What it proves | Tools | Runs |
|---|---|---|---|
| Static | Style, types, security smells, secrets, license/CVE | ruff, mypy, bandit, Semgrep*, gitleaks*, pip-audit | pre-commit + CI |
| Architecture | Context borders, no LLM outside extraction, pure engine | import-linter (`.importlinter`) | CI |
| Governance | Registry, datasets, data map, tool register, blockers, links | `tools/governance.py` | pre-commit + CI |
| Unit / property | Engine correctness | pytest, Hypothesis, time-machine*, mutmut* | CI |
| Contract | API matches OpenAPI; no breaking change | Schemathesis*, oasdiff*, Spectral* | CI |
| Prompt eval | Extraction quality and safety on golden data | `tools/score_extraction.py`, datasets, registry | on prompt/model change, nightly later |
| End-to-end | Real browser flows (forward, confirm date, approve) | pytest-playwright | CI on main |
| Frontend | Components | Vitest | CI |
| Release gate | Everything above plus approved prompts, release datasets, vetted tools, pinned actions | `governance.py release-gate` | before any outside user |

## Part D - How the non-drifting binding works
Each rule has a machine check so AI cannot silently drift:
1. **Instructions** - `CLAUDE.md` and the AI-DLC knowledge files are loaded every stage.
2. **Prompts** - registry hashes + required untrusted-input markers (`governance.py check`).
3. **Datasets** - schema, manifest hashes, PII scan, time-zone offset sanity, expected output validated against the prompt's output schema.
4. **Context rules** - `qa/contexts.toml` = `src/deepaira/*` = `.importlinter`, plus the two forbidden-import contracts.
5. **Data rules** - model fields = `qa/data-map.toml`.
6. **Tools** - dependencies = `qa/tool-register.toml`.
7. **Blockers** - `qa/release_blockers.toml` names a real test function for each.
8. **Cost** - `qa/cost_budgets.toml` and `governance.py cost-gate`.
