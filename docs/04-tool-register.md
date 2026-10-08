# 04 - Tool register and vetting policy

"Open source" for this project means **reliable and secure**, not just free. A tool must pass every item below before its entry in `qa/tool-register.toml` may change from `pending-vetting` to `approved`.

## Vetting checklist
1. **License** - OSI-approved; recorded in the entry.
2. **Maintenance** - recent releases, active maintainers, issues answered.
3. **Adoption** - used widely enough that problems are found by others first.
4. **Security record** - past advisories handled promptly; check the project's security policy.
5. **Supply chain** - published from a source repo, signed or provenance-attested where available; few transitive dependencies.
6. **Telemetry** - no hidden data collection; note defaults and how to disable.
7. **Exit plan** - what replaces it if it goes bad.
8. Record `license`, `vetted_on` (date) and `telemetry` in the entry. Verification must be done on the day with current sources; training knowledge is not enough.

## Supply-chain controls
Lockfiles committed (`uv.lock`, `package-lock.json`); CI actions pinned to full commit SHAs; `pip-audit`, `bandit`, and `gitleaks` in CI; new dependencies fail governance until registered.

## Tiers (initial judgment, **unverified** - confirm during vetting)
| Tier | Meaning | Tools |
|---|---|---|
| established | Long track record | Django, PostgreSQL, pytest, Hypothesis, Playwright, React, TypeScript, Vite, Vitest, mypy, bandit, pip-audit, Docker |
| reputable-verify | Good reputation; check the list above | ruff, uv, Semgrep, gitleaks, import-linter, mutmut, time-machine, Schemathesis, Django Ninja, oasdiff, Spectral, openapi-typescript, vite-plugin-pwa, DeepEval |
| watch | Use cautiously; ownership or maturity risk | Promptfoo (reported pending acquisition by OpenAI; repo stays MIT) [VERIFY], Langfuse cloud (synthetic data only) |
| defer / drop | Not now | Langfuse self-host, garak / PyRIT, Sentry (license [VERIFY]), brand-new eval libraries |

## Process
Add the tool as `pending-vetting` -> run the checklist -> founder approves -> mark `approved`. `governance.py release-gate` refuses to pass while any used tool is pending.
