---
title: Subscription Billing PRD
type: prd
status: draft
created: 2026-06-10T00:00:00Z
updated: 2026-06-10T00:00:00Z
tags: [prd, billing, subscriptions, saas]
sources:
  - researches/2026_06_08_saas-billing-models
  - specs/solution
  - specs/technical
---

# Subscription Billing — PRD

## 1. Summary
A subscription billing system for our SaaS: plans, metered usage, proration,
dunning, and invoicing, built on a payment provider rather than from scratch.
For the monetization team launching paid tiers in Q3. Compiled from billing
research, the capability breakdown, and the technical architecture.

## 2. Background & Problem
*Compiled from research (researches/2026_06_08_saas-billing-models).*
We currently run a single free tier. The research compared build-vs-buy and
recurring-billing providers, concluding that a provider-backed model (Stripe
Billing class) wins on time-to-market and PCI scope, with metered usage as the
main integration risk. Customers have repeatedly asked for usage-based pricing;
sales is blocked on enterprise deals without seat management.

## 3. Goals & Non-Goals
- **Goals**
  - Launch three paid plans (Starter, Pro, Enterprise) with monthly/annual terms.
  - Support metered usage billing for API calls.
  - Automated dunning to recover failed payments.
- **Non-Goals**
  - In-house payment processing or storing raw card data (provider handles it).
  - Multi-currency at launch (USD only this round).
  - Marketplace/partner revenue sharing.

## 4. Success Metrics
- ≥ 8% free-to-paid conversion within 90 days of launch.
- Involuntary churn (failed-payment) < 1.5% monthly after dunning.
- Invoice accuracy ≥ 99.9% (disputes / total invoices).
- Time-to-launch a new plan < 1 day (config, not code).

## 5. Users & Personas
- **Self-serve customer** — picks a plan, upgrades/downgrades, expects proration.
- **Enterprise buyer** — needs seat management, annual invoicing, PO terms.
- **Finance ops** — needs accurate invoices, revenue reporting, refund handling.
- **Support agent** — needs to see subscription state to resolve billing tickets.

## 6. Requirements

### 6.1 Functional Requirements
*Compiled from the solution spec's capabilities.*

| ID | Requirement | Source capability | Priority |
|----|-------------|-------------------|----------|
| FR-1 | Create/cancel subscriptions across three plans, monthly & annual | CAP-01 | Must |
| FR-2 | Prorate on mid-cycle plan changes | CAP-02 | Must |
| FR-3 | Meter and bill API usage above plan quota | CAP-03 | Must |
| FR-4 | Automated dunning with retries and customer notifications | CAP-04 | Must |
| FR-5 | Seat management for Enterprise | CAP-05 | Should |
| FR-6 | Self-serve plan upgrade/downgrade in-app | CAP-06 | Should |
| FR-7 | Generate and email invoices/receipts | CAP-07 | Must |

### 6.2 Non-Functional Requirements
*Compiled from the technical spec.*

| ID | Requirement | Source |
|----|-------------|--------|
| NFR-1 | PCI scope minimized — no raw card data touches our systems (SAQ-A) | technical spec |
| NFR-2 | Webhook processing idempotent; provider is source of truth for payment state | technical spec |
| NFR-3 | Billing events reconciled daily; discrepancies alert finance | technical spec |
| NFR-4 | Usage metering durable and exactly-once per billable event | technical spec |

## 7. Key User Flows
*From the solution spec's logic flows.*
1. **Subscribe** — customer picks plan → provider checkout → webhook confirms →
   subscription activated → welcome + receipt emailed.
2. **Upgrade mid-cycle** — customer changes plan → proration computed →
   immediate charge or credit → confirmation.
3. **Metered billing** — usage events accumulate → at cycle close, overage
   computed → added to next invoice.
4. **Failed payment** — charge fails → dunning sequence (retry + notify) →
   recovered, or subscription paused after final attempt.

## 8. Technical Considerations
*Summary — see specs/technical for the full architecture.* Provider-backed
billing (Stripe Billing class) is the system of record for payment state; our
service stores subscription metadata and usage counters, and reacts to provider
webhooks idempotently. Metering runs through a durable event pipeline to meet
exactly-once billing (NFR-4). Daily reconciliation job guards invoice accuracy.
This keeps PCI scope at SAQ-A (NFR-1) and the build small, at the cost of a hard
dependency on the provider's API and webhook reliability (see Risks).

## 9. Milestones / Release Plan
- **M1 — Core subscriptions** (FR-1, FR-2, FR-7): plans, proration, invoicing.
  Closed beta.
- **M2 — Resilience & metering** (FR-3, FR-4): usage billing + dunning. GA for
  self-serve.
- **M3 — Enterprise** (FR-5, FR-6): seat management + self-serve plan changes.

## 10. Risks & Open Questions
- **Provider dependency** — webhook downtime delays subscription state; need a
  reconciliation fallback (partially covered by NFR-3).
- **Metering correctness** — under/over-billing erodes trust; exactly-once
  (NFR-4) is the highest-risk integration.
- **Multi-currency** — deferred, but enterprise EU deals may force it sooner.
- Open: dunning retry schedule — provider defaults vs. custom? (finance to decide)
- Open: annual-plan refund policy on downgrade?

## 11. Sources
- Research: researches/2026_06_08_saas-billing-models
- Solution spec: specs/solution
- Technical spec: specs/technical
