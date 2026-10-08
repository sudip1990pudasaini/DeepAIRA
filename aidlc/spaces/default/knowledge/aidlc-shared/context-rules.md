# Bounded contexts and layering (source of truth: qa/contexts.toml)

Layers, top to bottom. A context may import only from layers below it, never above, never a sibling on its own layer.
1 admin, privacy | 2 capture | 3 calendar_bookings, bills_renewals, invoices_approvals, returns_warranty, moving_life_events, home_projects, custom_categories | 4 items | 5 extraction | 6 billing | 7 metering, identity | 8 audit | 9 engine.

Rules:
- Import another context only through its package `__init__` (public interface). No reaching into its models.
- Only `extraction` may import the LLM SDK (`anthropic`). Everything else calls extraction.
- `engine` imports no Django, no network, no LLM. It is plain, fully testable Python.
- Every Django model field is classified in qa/data-map.toml in the same change that adds it.
- Adding a context: edit qa/contexts.toml, run `python3 tools/governance.py gen-importlinter`, update .importlinter, create the package. The governance check fails if the three disagree.
- Whether foreign keys may cross contexts is an open decision (docs/06-open-items.md). Until decided, use plain ID references, not ForeignKey, across contexts.
