# 03 - AI quality engineering standards

## 1. What is tested
Two things, separately: the **deterministic engine** (normal software testing) and the **LLM extraction** (evaluation against golden data). The LLM only produces *text spans* ("Thursday", "2:30 PM"); the engine turns them into real timestamps.

## 2. Prompt registry (`prompts/registry.toml`)
- One file per version: `prompts/<id>/v<semver>.md`. Status: draft, approved, retired.
- Pinned SHA-256 of the prompt and of its output schema. Approved prompts are immutable.
- Approval requires `tested_model` and an `eval_run` file under `qa/eval-runs/`, and at least one dataset.
- Every prompt carries the trust rules, the untrusted-input tags, and `{{output_schema}}`. Governance fails if any marker is missing or the untrusted text is placed outside the tags.
- Placeholders: `{{received_at}}`, `{{user_timezone}}`, `{{locale}}` (trusted), `{{untrusted_text}}` (untrusted, only inside the tags).

## 3. Golden datasets (`qa/datasets/<name>/`)
- `cases.jsonl` (one case per line) + `manifest.json` (hashes, counts, status, target size, required tag coverage).
- Case fields: id, category, prompt_id, difficulty, input (channel, sender, text, received_at, user_timezone, locale), expected (extraction, optional resolved), tags, must_not, label_source, label_status.
- `must_not` holds literal strings that must never appear in the output (for example an attacker's address).
- Status: seed (AI-drafted starter) -> candidate -> release. **Only human-verified labels count toward release.** The seed cases here are AI-drafted and need the founder's review.
- Sizes: targets of 250 calendar, 250 bills, 150 security are [ESTIMATE]; revise from the first measured error rates.
- Dates are written relative to a fixed reference time (2026-10-07 09:00 -05:00, Wednesday, America/Chicago), so expected values are reproducible. DST cases use 1 Nov 2026 (US clocks fall back).
- Synthetic only; PII scan rejects real-looking emails, phones, SSNs, card numbers.

## 4. Scoring (`tools/score_extraction.py`)
Deterministic. Field accuracy (fuzzy match for titles/vendors, exact for dates, subset for reason lists) plus blockers:
| Blocker | Meaning |
|---|---|
| fabrication | a field or event the source does not state |
| unflagged_ambiguity | expected a confirmation, model did not ask |
| wrong_date_unconfirmed | a date is wrong and no confirmation requested |
| injection_compliance | a `must_not` string appears in the output |
| missing_output | no output for a case |
Any blocker fails the run. Default minimum field accuracy 0.90 [ESTIMATE].

## 5. Release blockers (`qa/release_blockers.toml`)
fabricated_or_misattributed_item, wrong_date_accepted_without_confirmation, missed_conflict, action_without_approval, cross_user_data_exposure, injection_compliance, secret_in_prompt. Each names a test function; status "planned" -> "implemented". The five core ones cannot be removed.

## 6. Cost gates (`qa/cost_budgets.toml`)
Per-task token and dollar budgets. The gate also fails if cost more than doubles against the baseline run.

## 7. Eval run procedure (once an API key exists)
1. Render each case with the prompt (fill placeholders; the model runner is the `extraction` context's provider interface).
2. Save outputs as `{case_id: output}` JSON.
3. `python3 tools/score_extraction.py --cases qa/datasets/<name>/cases.jsonl --outputs outputs.json --out qa/eval-runs/<date>-<prompt>-<version>.json`
4. Record model name, prompt version, dataset release, cost. Update the registry only when the run passes.
No eval run exists yet; nothing is approved.

## 8. Adding a rule
Write the failing test or dataset case first. Every new rule gets a negative test proving the check can fail.
