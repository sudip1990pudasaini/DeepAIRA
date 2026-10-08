# 00 - Project brief

**Working name:** DeepAIRA (codename only; no domain, trademark or LLC exists under it yet).
**Founder:** Sudip, Minnesota (Central time). Solo. 15-20 hours a week. Builds on personal time and equipment, outside any employer hours.

## What it is
A global-ready life-admin platform: *forward it, tell it, track it.* The user forwards a message, types it, or pastes it. The system extracts the facts (a date, an amount, a renewal), asks the user to confirm anything uncertain, and tracks it with reminders. It never stores third-party passwords and never acts without approval.

## Six categories
| # | Category | Typical input |
|---|---|---|
| 1 | Calendar and Bookings | appointment emails, invites, "dentist Thursday 2:30" |
| 2 | Bills, Renewals, Subscriptions | statements, renewal notices, receipts |
| 3 | Invoices and Approvals | invoices a freelancer sends or approves |
| 4 | Returns, Warranty, Price-drop | receipts with return windows |
| 5 | Moving and Life Events | move checklists, address changes |
| 6 | Home Projects | quotes, change orders |

All six are designed up front. They are built in thin slices. Tentative first trio for the Standard plan: 1, 2, 3 (to be decided).

## Surfaces
Web app (React + TypeScript PWA), admin console, mobile later via Expo. iPhone web push works only after Add to Home Screen, so email is the reliable reminder channel.

## Business shape
Bootstrapped. Form an LLC before taking payments or outside users. Venture capital is not planned; revisit later.

## Success for the first release (to be confirmed in Inception)
- A user can forward a message in any of the first-trio categories and see a correct, confirmed item.
- No release blocker in qa/release_blockers.toml fails.
- Cost per extraction stays inside qa/cost_budgets.toml.

## Not in scope yet
Native app store releases, localization beyond English/US content, any feature that logs into a user's third-party accounts.
