# 05 - Context map

Source of truth: `qa/contexts.toml` (checked against `src/deepaira/*` and `.importlinter`).

```mermaid
flowchart TD
  subgraph L1[Layer 1]
    admin
    privacy
  end
  capture[Layer 2: capture]
  subgraph L3[Layer 3: categories]
    calendar_bookings
    bills_renewals
    invoices_approvals
    returns_warranty
    moving_life_events
    home_projects
    custom_categories
  end
  items[Layer 4: items]
  extraction[Layer 5: extraction - only LLM caller]
  billing[Layer 6: billing]
  subgraph L7[Layer 7]
    metering
    identity
  end
  audit[Layer 8: audit]
  engine[Layer 9: engine - pure Python]
  L1 --> capture --> L3 --> items --> extraction --> billing --> L7 --> audit --> engine
```

A higher layer may import a lower one. Siblings on one layer never import each other. Skipping layers is allowed (for example `items` may use `engine` directly).

| Context | Owns | Table prefix |
|---|---|---|
| admin | support tools, metrics views | adm |
| privacy | export, deletion, consent | prv |
| capture | inbound email, paste, upload | cap |
| calendar_bookings ... custom_categories | category rules and views | cal, bil, inv, ret, mov, hom, cus |
| items | the tracked item, reminders, approvals | itm |
| extraction | LLM provider interface, prompts, output validation | ext |
| billing | plans, entitlements | bll |
| metering | usage ledger and cost | met |
| identity | accounts and sessions | idn |
| audit | append-only action history | aud |
| engine | dates, time zones, recurrence, conflicts | eng |

Open question: may Django foreign keys cross contexts? Until decided, reference other contexts by plain ID.
