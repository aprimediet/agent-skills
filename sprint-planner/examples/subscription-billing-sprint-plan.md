---
title: Subscription Billing Sprint Plan
type: sprint-plan
created: 2026-06-10T00:00:00Z
updated: 2026-06-10T00:00:00Z
source: prd
---

# Subscription Billing — Sprint Plan

## Overview
Schedules the subscription billing PRD into three sprints: core subscriptions
first, then resilience and metering, then enterprise features. Compiled from the
project PRD (FR-1..FR-7 / CAP-01..07). Multi-currency stays out of scope per the
PRD's non-goals.

## Backlog (prioritized)

| Story | As a… I want… so that… | Source | Priority | Points |
|-------|------------------------|--------|----------|--------|
| US-001 | As a customer, I want to subscribe to a plan, so that I can use paid features | FR-1 / CAP-01 | Must | 8 |
| US-002 | As finance ops, I want invoices and receipts generated, so that billing is auditable | FR-7 / CAP-07 | Must | 5 |
| US-003 | As a customer, I want proration on mid-cycle changes, so that I'm billed fairly | FR-2 / CAP-02 | Must | 5 |
| US-004 | As a customer, I want failed payments retried with notice, so that I don't lose access by accident | FR-4 / CAP-04 | Must | 8 |
| US-005 | As a customer, I want API usage billed above quota, so that I pay for what I use | FR-3 / CAP-03 | Must | 13 |
| US-006 | As a customer, I want to upgrade/downgrade in-app, so that I control my plan | FR-6 / CAP-06 | Should | 5 |
| US-007 | As an enterprise buyer, I want seat management, so that I can administer my team | FR-5 / CAP-05 | Should | 8 |

Deferred: none this round; multi-currency excluded per PRD non-goals.

## Dependencies
- US-003 (proration) and US-006 (plan change) depend on US-001 (subscriptions exist).
- US-005 (metering) depends on US-001 and is the highest-risk integration (NFR: exactly-once).

## Schedule

### Sprint 1 — Core subscriptions  (points: 18)

- **US-001** — As a customer, I want to subscribe to a plan · `Must` · 8 pts
  - [ ] task: Integrate provider checkout for the three plans
  - [ ] task: Handle the activation webhook idempotently
  - [ ] task: Store subscription metadata and state
  - [ ] task: Send welcome + receipt email on activation
- **US-002** — As finance ops, I want invoices and receipts · `Must` · 5 pts
  - [ ] task: Generate invoices from subscription events
  - [ ] task: Email invoices/receipts to the customer
- **US-003** — As a customer, I want proration on changes · `Must` · 5 pts
  - [ ] task: Compute proration on mid-cycle plan change
  - [ ] task: Apply immediate charge or credit and confirm

### Sprint 2 — Resilience & metering  (points: 21)
> Flagged: US-005 is 13 pts — consider splitting metering capture vs. billing
> before this sprint starts.

- **US-004** — As a customer, I want failed payments retried with notice · `Must` · 8 pts
- **US-005** — As a customer, I want API usage billed above quota · `Must` · 13 pts

### Sprint 3 — Enterprise  (points: 13)

- **US-006** — As a customer, I want to upgrade/downgrade in-app · `Should` · 5 pts
- **US-007** — As an enterprise buyer, I want seat management · `Should` · 8 pts

## Risks & Open Questions
- US-005 (metering, 13 pts) is oversized and the riskiest story (exactly-once
  billing) — recommend splitting into "capture usage events" and "bill overage"
  before Sprint 2.
- Sprint 2 is the heaviest at 21 pts; rebalancing US-006 forward is an option if
  velocity proves lower than expected.
- Dunning retry schedule is an open PRD question (finance to decide) — affects
  US-004 tasks.

## Librarian handoff
```
sprint create --name 1 --title "Sprint 1" --goal "Core subscriptions"
sprint create --name 2 --title "Sprint 2" --goal "Resilience & metering"
sprint create --name 3 --title "Sprint 3" --goal "Enterprise"
story create 1 1 --title "Subscribe to a plan" --description "As a customer, I want to subscribe to a plan, so that I can use paid features" --points 8 --priority Must
story create 1 2 --title "Invoices and receipts" --description "As finance ops, I want invoices and receipts generated, so that billing is auditable" --points 5 --priority Must
story create 1 3 --title "Proration on mid-cycle changes" --description "As a customer, I want proration on mid-cycle changes, so that I'm billed fairly" --points 5 --priority Must
story create 2 4 --title "Failed payment retried with notice" --description "As a customer, I want failed payments retried with notice, so that I don't lose access by accident" --points 8 --priority Must
story create 2 5 --title "Usage billed above quota" --description "As a customer, I want API usage billed above quota, so that I pay for what I use" --points 13 --priority Must
story create 3 6 --title "Upgrade/downgrade in-app" --description "As a customer, I want to upgrade/downgrade in-app, so that I control my plan" --points 5 --priority Should
story create 3 7 --title "Seat management" --description "As an enterprise buyer, I want seat management, so that I can administer my team" --points 8 --priority Should
task write 1 1 1 --title "Integrate provider checkout for three plans" --status todo
task write 1 1 2 --title "Handle activation webhook idempotently" --status todo
task write 1 1 3 --title "Store subscription metadata and state" --status todo
task write 1 1 4 --title "Send welcome + receipt email" --status todo
task write 1 2 1 --title "Generate invoices from subscription events" --status todo
task write 1 2 2 --title "Email invoices/receipts" --status todo
task write 1 3 1 --title "Compute proration on plan change" --status todo
task write 1 3 2 --title "Apply charge/credit and confirm" --status todo
```
