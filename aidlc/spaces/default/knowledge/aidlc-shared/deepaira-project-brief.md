# DeepAIRA project brief (for every AI-DLC stage)

DeepAIRA is a working codename. The product is a global-ready life-admin platform: the user forwards a message, tells it, or pastes it; the system extracts what matters and tracks it. No third-party passwords are ever stored.

Six categories (design all, build in thin slices): Calendar and Bookings; Bills, Renewals and Subscriptions; Invoices and Approvals; Returns, Warranty and Price-drop; Moving and Life Events; Home Projects. Tentative first trio: Calendar and Bookings, Bills and Renewals, Invoices and Approvals.

Surfaces: web (React + TypeScript PWA), admin console, mobile later via Expo.

Founder: solo, 15-20 hours a week, personal time and equipment only. Not a deep coder: prefers readable code, small steps, plain explanations. Reviews AI output and learns as the project goes.

Launch scope: English and US content, localization-ready from day one (no hard-coded strings, time zones always explicit). Bootstrapped; LLC before payments or outside users.

Where the facts live (read these, do not guess):
- docs/01-architecture-decisions.md - decisions and the tool for each AI-DLC stage
- docs/02-privacy-and-data-rules.md and qa/data-map.toml - data handling
- docs/03-ai-qe-standards.md - quality rules, datasets, release blockers
- qa/contexts.toml - bounded contexts and layering
- qa/tool-register.toml - the only tools that may be used
- docs/06-open-items.md - unresolved questions; never assume an answer
