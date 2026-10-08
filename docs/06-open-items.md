# 06 - Open items

## Founder to-dos
- [ ] **Optum HR/Compliance disclosure check** - confirm in writing that outside work is allowed and what must be disclosed. I could not verify employment terms; nothing here is legal advice.
- [ ] **Final product name** - DeepAIRA is a codename. Check domain, trademark (USPTO TESS) and app-store conflicts before committing. Not done.
- [ ] **Review seed dataset labels** - 31 AI-drafted cases await human verification.
- [ ] Apple developer account ($99/yr [VERIFY]) only when a TestFlight build is needed.
- [ ] Anthropic API key (kept in `.env`, never in the repo) before the first eval run.

## Decisions pending
| # | Item | When |
|---|---|---|
| ADR-18 | Foreign keys across contexts | Inception 2.6 |
| ADR-19 | Hosting, email ingestion, payment provider | Inception 2.8 / 3.4 |
| ADR-20 | Final name | before domain purchase |
| - | Standard-plan trio (tentative: Calendar, Bills, Invoices) | Inception 1.4 |
| - | Lawyer review: privacy policy, terms, forwarding consent, GDPR/CCPA | before outside users |
| - | LLC formation | before payments |

## [VERIFY] list
- AI-DLC install steps: README says `aidlc config --harness claude` / `aidlc doctor`; getting-started says manual copy and `/aidlc --doctor`. Follow the doc matching the installed version.
- AI-DLC default routing may use Bedrock and `.claude/settings.json` pre-approves broad tools. Check both after install and merge `config/claude-settings.snippet.json`.
- Claude Code permission rule syntax in the snippet.
- All [ESTIMATE] thresholds: accuracy 0.90, dataset sizes, token budgets, tag minimums.
- Tool tiers and licenses (docs/04).
- Anthropic API data retention terms.
- Import-linter contracts were written but **not executed** (the build sandbox had no PyPI access). Run `lint-imports` first thing.
