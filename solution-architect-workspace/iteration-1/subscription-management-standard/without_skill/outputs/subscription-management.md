# Subscription Management — Capability Breakdown

## 1. Overview

This document decomposes the **Subscription Management** area of a SaaS product into the discrete capabilities required to operate it. The area covers the full lifecycle of a paid customer relationship: choosing a plan, recurring billing on monthly or yearly cycles, changing plans (upgrade / downgrade / cancel), and the financial machinery behind it — payment processing, failure recovery, proration, and invoicing.

The breakdown is organized into capability domains. Each capability lists what it does, the key behaviors it must support, important edge cases, and its main data concerns. The intent is to make the scope explicit enough to estimate, design, and build against.

### 1.1 Actors

- **Subscriber / Account owner** — the paying customer who selects, changes, and pays for a plan.
- **End users** — additional seats under an account (if the product supports seats).
- **Billing system / scheduler** — automated processes that run renewals, retries, and reconciliation.
- **Payment provider** — external gateway (e.g., Stripe, Braintree, Adyen) that charges cards and reports outcomes.
- **Support / billing admin** — internal staff who issue refunds, credits, comps, and resolve disputes.
- **Finance / accounting** — consumers of revenue, tax, and reconciliation data.

### 1.2 Core domain objects

- **Plan / Price** — a sellable offering with an amount, currency, and billing interval (monthly / yearly).
- **Subscription** — the binding between an account and a plan, with a status and a current billing period.
- **Invoice** — an itemized statement for a billing period, with line items, taxes, discounts, and a total.
- **Payment / Charge** — an attempt to collect money against an invoice.
- **Payment method** — a stored card / bank mandate / wallet used to charge the customer.
- **Customer / Billing account** — the entity that owns subscriptions, payment methods, and billing identity.

---

## 2. Capability Domains

## 2.1 Plan & Catalog Management

Defines what customers can buy.

| Capability | Description |
|---|---|
| Plan definition | Create plans with name, description, feature entitlements, and visibility (public/private). |
| Price points | Each plan has one or more prices: amount, currency, and interval (monthly, yearly). A plan typically has both a monthly and a discounted yearly price. |
| Multi-currency pricing | Offer per-currency prices rather than FX-converting at charge time. |
| Tiered / seat-based pricing | Flat, per-seat, tiered (volume/graduated), or usage-based pricing models. |
| Add-ons | Optional purchasable extras attached to a base subscription. |
| Trials | Free trial length, whether a card is required upfront, and trial-to-paid conversion behavior. |
| Plan versioning | Change prices/features over time without retroactively breaking existing subscribers (grandfathering). |
| Entitlements mapping | Translate "what plan you're on" into "what features/limits you get" — the link between billing and product access. |

**Edge cases:** deprecating a plan while subscribers remain on it; introducing a price increase and how/when existing customers are migrated; region-specific catalogs.

---

## 2.2 Signup & Subscription Creation

Turning a prospect into an active subscriber.

| Capability | Description |
|---|---|
| Plan selection | Choose plan + interval (monthly/yearly), seat count, and add-ons. |
| Checkout | Collect billing details and a payment method; create the customer in the payment provider. |
| Trial start | Begin a trial without an immediate charge (or with a deferred first charge). |
| First charge | Charge immediately for paid signups, or schedule the first charge at trial end. |
| Subscription activation | On successful payment, mark subscription active and grant entitlements. |
| Coupons / promo codes | Apply discounts at signup (percentage, fixed amount, first-period vs recurring, duration). |
| Tax & address collection | Capture billing address and tax IDs (e.g., VAT) needed for compliant invoicing. |

**Edge cases:** card declined at signup (no subscription created vs pending state); duplicate signup attempts; signing up while a prior canceled subscription exists.

---

## 2.3 Billing Cycle & Recurring Charges

The recurring engine — the heart of the system.

| Capability | Description |
|---|---|
| Billing period tracking | Each subscription has a current period start/end and an anchor date. |
| Renewal scheduling | At period end, generate the next invoice and attempt payment automatically. |
| Monthly vs yearly cycles | Support both intervals; yearly renews once every 12 months at the discounted rate. |
| Billing anchor | Determine the day-of-month/year on which billing recurs; handle month-length mismatches (e.g., billed on the 31st). |
| Idempotent renewals | Ensure a single renewal run never double-charges, even on retry or scheduler overlap. |
| Time-zone & cutoff handling | Define when "end of period" occurs consistently. |
| Dunning window | The period during which a renewal payment may still be retried before the subscription lapses. |

**Edge cases:** clock/timezone drift; leap years for yearly plans; the 29th/30th/31st billing anchor on short months; renewals during an in-flight plan change.

---

## 2.4 Plan Changes — Upgrade / Downgrade / Cancel

Mutating an active subscription.

### Upgrade
- Switch to a higher-priced plan or add seats/add-ons.
- Typically takes effect **immediately**, with **proration**: charge the prorated difference for the remaining period now.
- Entitlements upgrade immediately.

### Downgrade
- Switch to a lower-priced plan or remove seats/add-ons.
- Two common policies: **immediate** (with prorated credit) or **at end of current period** (most common — avoids refunds and keeps paid-for access until period end).
- Entitlements may need to step down at period boundary; enforce new limits at downgrade time (e.g., over-seat or over-quota handling).

### Interval switch (monthly ↔ yearly)
- Switching monthly→yearly is an upgrade-like change (often immediate, prorated).
- Yearly→monthly is usually scheduled for the next renewal.

### Cancel
| Capability | Description |
|---|---|
| Cancel at period end | Subscription stays active until the paid period ends, then lapses (default, customer-friendly). |
| Immediate cancel | Ends access now; may issue a prorated refund/credit per policy. |
| Reactivation / undo cancel | Reverse a pending cancellation before it takes effect. |
| Cancellation reasons | Capture reason codes for churn analytics. |
| Win-back / pause | Optionally pause instead of cancel; resume later. |

**Edge cases:** changing plan and interval at the same time; multiple changes within one period; downgrade scheduled then upgrade requested before it applies; cancel during dunning; proration when a coupon is active.

---

## 2.5 Proration

Calculating fair partial-period amounts when changes occur mid-cycle.

| Capability | Description |
|---|---|
| Proration on upgrade | Credit unused time on the old plan; charge for remaining time on the new plan; bill the net difference. |
| Proration on downgrade | Issue a credit for the price difference, applied to future invoices or as an immediate refund per policy. |
| Proration on seat changes | Add/remove seats mid-cycle with per-seat proration. |
| Credit handling | Track credit balance and apply it to subsequent invoices. |
| Proration policy config | Toggle proration on/off per change type; choose "charge now" vs "next invoice." |
| Rounding & precision | Define rounding rules and minimum charge thresholds to avoid 1-cent invoices. |

**Edge cases:** proration combined with discounts/coupons; proration across a currency; proration when the period anchor also changes; negative invoice (credit exceeds charge) handling.

---

## 2.6 Payment Processing

Moving money, via a provider.

| Capability | Description |
|---|---|
| Payment method storage | Tokenize and store cards/bank mandates with the provider; never store raw PAN (PCI scope reduction). |
| Charge execution | Charge an invoice against the default payment method. |
| Multiple payment methods | Support cards, ACH/SEPA direct debit, wallets (Apple/Google Pay), and per-customer default selection. |
| 3-D Secure / SCA | Handle Strong Customer Authentication challenges (especially EU/PSD2) for both interactive and off-session charges. |
| Off-session charges | Charge stored methods during automated renewals without the customer present. |
| Webhook ingestion | Consume async provider events (payment succeeded/failed, dispute opened) reliably and idempotently. |
| Provider abstraction | Optional anti-corruption layer to limit lock-in to a single gateway. |

**Edge cases:** SCA required on an off-session renewal (must notify customer to authenticate); webhook delivered out of order or duplicated; provider timeout leaving charge state ambiguous (reconcile before re-charging).

---

## 2.7 Payment Failure Handling & Dunning

Recovering revenue when charges fail.

| Capability | Description |
|---|---|
| Failure classification | Distinguish hard declines (lost/stolen, closed account) from soft declines (insufficient funds, temporary) to choose retry strategy. |
| Retry / dunning schedule | Automatically retry failed renewals on a configurable schedule (e.g., day 1, 3, 5, 7) with backoff. |
| Smart retries | Optionally use provider-side intelligent retry timing. |
| Dunning notifications | Email/in-app prompts asking the customer to update their card, with deep links. |
| Grace period | Keep service active for a window after first failure before suspending. |
| Suspension / downgrade on failure | Restrict access after the dunning window expires. |
| Final lapse / involuntary churn | Cancel the subscription after all retries fail; record as involuntary churn. |
| Card updater | Use account-updater services to refresh expiring/replaced cards automatically. |
| Recovery on update | Immediately retry the open invoice when a customer adds a working card. |

**Edge cases:** card expires between renewals; partial recovery (some invoices paid, others not); customer fixes payment after suspension but during the same period; disputes/chargebacks triggered during dunning.

---

## 2.8 Invoicing

Producing the financial record.

| Capability | Description |
|---|---|
| Invoice generation | Create an invoice per billing event (renewal, plan change, add-on) with itemized line items. |
| Line items | Base plan, seats, add-ons, proration credits/charges, discounts, taxes, and credit balance applied. |
| Tax calculation | Compute sales tax / VAT / GST based on customer location and product taxability (often via a tax engine). |
| Invoice numbering | Sequential, gap-free, jurisdiction-compliant numbering. |
| Invoice states | Draft → open → paid → void / uncollectible; track transitions and timestamps. |
| Documents (PDF) | Render downloadable invoices and receipts with legally required fields. |
| Credit notes / refunds | Issue credit notes for refunds and adjustments. |
| Invoice delivery | Email invoices/receipts and expose them in a billing portal. |
| Manual / offline invoicing | Support invoice-then-pay (NET terms) for enterprise customers, not just auto-charge. |

**Edge cases:** retroactive corrections after an invoice is finalized (use credit notes, not edits); tax rate changes mid-period; zero-amount and negative invoices; multi-currency rounding on totals.

---

## 2.9 Customer Billing Portal & Self-Service

What the subscriber can do without contacting support.

| Capability | Description |
|---|---|
| View current plan & status | Show plan, interval, next billing date, and amount. |
| Update payment method | Add/replace/delete cards and set default. |
| Change plan | Self-serve upgrade/downgrade/cancel with clear proration preview. |
| Billing history | List and download past invoices and receipts. |
| Update billing details | Address, tax ID, billing email. |
| Manage seats / add-ons | Adjust quantities with cost preview. |
| Cancellation flow | Self-serve cancel with retention offers and reason capture. |

**Edge cases:** showing accurate "what you'll be charged" previews including proration, taxes, and discounts before confirmation.

---

## 2.10 Admin & Support Operations

Internal control plane.

| Capability | Description |
|---|---|
| Manual adjustments | Apply credits, discounts, comps, and one-off charges. |
| Refunds | Full/partial refunds with reason and audit trail. |
| Override actions | Force cancel, extend trial, change next billing date, skip dunning. |
| Dispute / chargeback handling | Track disputes, submit evidence, and adjust subscription state on loss. |
| Impersonation / lookup | Find a customer's billing state for support. |
| Comp / internal accounts | Free or discounted accounts for staff/partners. |

---

## 2.11 Notifications & Communications

Triggered messages across the lifecycle.

- Welcome / subscription confirmation; trial start and **trial-ending** reminders.
- Upcoming renewal notice (especially required for yearly plans in some jurisdictions).
- Payment receipt; payment failed; dunning reminders; final suspension notice.
- Plan change confirmation; cancellation confirmation; card-expiring warning.
- Price-change advance notice.

**Concern:** preferences, localization, and deliverability; these are billing-critical emails, not marketing.

---

## 2.12 Reporting, Analytics & Reconciliation

Making the money legible.

| Capability | Description |
|---|---|
| Revenue metrics | MRR/ARR, expansion/contraction, churn (voluntary vs involuntary), ARPU, LTV. |
| Recognized vs deferred revenue | For yearly plans, recognize revenue over the period (rev-rec / ASC 606). |
| Dunning effectiveness | Recovery rate, failed-payment volume, retry success. |
| Reconciliation | Match internal invoice/charge records against the payment provider's settlement reports and the bank. |
| Tax reporting | Per-jurisdiction tax collected for filing. |
| Cohort & retention analysis | Subscription survival by signup cohort and plan. |
| Audit log | Immutable history of every billing-affecting action. |

---

## 3. Cross-Cutting Concerns

| Concern | Why it matters |
|---|---|
| **Idempotency** | Renewals, retries, and webhooks must be safe to repeat without double-charging. Use idempotency keys end-to-end. |
| **Consistency between billing and access** | Entitlements (what the user can do) must stay in sync with subscription status, including during dunning grace periods. |
| **State machine clarity** | Subscription status (trialing, active, past_due, canceled, paused, unpaid) should be a well-defined state machine with explicit transitions. |
| **Money correctness** | Use integer minor units, defined rounding, and a single source of truth for amounts; never float. |
| **PCI compliance** | Keep raw card data out of scope by tokenizing with the provider; SAQ-A where possible. |
| **Tax/legal compliance** | VAT/GST/sales tax, invoice format requirements, advance renewal notices, refund and cancellation-rights laws vary by region. |
| **Auditability** | Every charge, credit, refund, and plan change needs a tamper-evident trail for finance and disputes. |
| **Provider resilience** | Handle gateway downtime, timeouts, and ambiguous states via reconciliation rather than blind retries. |
| **Webhook reliability** | Verify signatures, deduplicate, process asynchronously, and tolerate out-of-order/late delivery. |
| **Data privacy** | Billing data is PII; handle access, retention, and deletion appropriately. |

---

## 4. Subscription State Model (reference)

A typical status set and key transitions:

- `trialing` → `active` (trial converts / first charge succeeds)
- `trialing` → `canceled` (trial canceled or conversion charge fails with no retry)
- `active` → `past_due` (renewal charge fails; dunning begins)
- `past_due` → `active` (recovery — card updated / retry succeeds)
- `past_due` → `unpaid` / `canceled` (dunning exhausted — involuntary churn)
- `active` → `canceled` (voluntary cancel; immediate or at period end)
- `active` → `paused` → `active` (pause/resume)
- `canceled` → `active` (reactivation, where supported)

Plan changes (upgrade/downgrade/interval switch) occur within `active`/`trialing` and trigger proration and invoicing rather than status changes.

---

## 5. Build vs Buy Note

Much of this — recurring billing, proration math, dunning, tax, SCA, invoice PDFs, and a customer portal — is provided out of the box by billing platforms (Stripe Billing, Chargebee, Recurly, Paddle). The decision is largely **how much of the billing engine to delegate** vs build in-house. Even when delegating, the product still owns: entitlement mapping, plan/interval UX, the access-vs-billing consistency layer, reconciliation into internal finance systems, and product-specific change policies. The capabilities above remain the scope to reason about regardless of build/buy — the question is who implements each.

---

## 6. Capability Checklist (summary)

- [ ] Plan & price catalog (monthly/yearly, multi-currency, add-ons, trials, versioning)
- [ ] Entitlements mapping (billing ↔ product access)
- [ ] Signup & checkout with coupons, tax, and trials
- [ ] Recurring billing engine (anchors, idempotent renewals, both intervals)
- [ ] Upgrade / downgrade / interval-switch / cancel / pause / reactivate
- [ ] Proration engine (charges, credits, policies, rounding)
- [ ] Payment processing (tokenization, SCA, off-session, webhooks)
- [ ] Payment-failure handling & dunning (classification, retries, grace, recovery)
- [ ] Invoicing (line items, tax, numbering, states, PDFs, credit notes)
- [ ] Customer billing portal (self-service changes with previews)
- [ ] Admin/support operations (refunds, credits, overrides, disputes)
- [ ] Lifecycle notifications
- [ ] Reporting, analytics, rev-rec, and reconciliation
- [ ] Cross-cutting: idempotency, consistency, state machine, money correctness, PCI, tax/legal, audit
