# 02 - Privacy and data rules

Privacy-first. These rules are enforced by tests and by `governance.py` where possible.

## Rules
1. **Collect the minimum.** Raw forwarded text is held only long enough to extract (default 7 days, then purged). The extracted item is kept until the user deletes it.
2. **No third-party credentials.** The product never asks for or stores a password to another service.
3. **Classify every field.** Every Django model field is listed in `qa/data-map.toml` with sensitivity (public, internal, personal, sensitive, secret), store, retention, deletion mode and whether it can enter an LLM prompt. Governance fails the build if a model field is missing.
4. **Secrets never reach the LLM.** A `secret` field cannot be marked `in_llm_prompt`.
5. **Sensitive data is not kept forever.** `sensitive` and `secret` fields cannot use indefinite retention.
6. **No sharing.** Data is not sold or shared with third parties. The LLM provider is a processor; its data-use and retention terms must be reviewed before real user data is sent [VERIFY: current Anthropic API retention terms].
7. **User control.** Export and deletion live in the `privacy` context. Deletion is a hard delete unless a legal retention reason is recorded.
8. **Logs and traces.** No raw message text in application logs. Traces use IDs and token counts. Any third-party tracing tool receives synthetic data only until a data processing review is done.
9. **Datasets and prompts.** Golden datasets are synthetic. Emails use example.com/org/net; phones use 555-01xx. The PII scan in governance rejects anything else.
10. **Repo hygiene.** `.env`, keys and secrets are git-ignored; Claude Code settings deny reading them; gitleaks runs in CI once vetted.

## Legal items not yet decided (see 06-open-items.md)
Privacy policy and terms, GDPR/UK/CCPA obligations by launch market, children's data, email-forwarding consent. These need a qualified lawyer; this document is engineering rules, not legal advice.
