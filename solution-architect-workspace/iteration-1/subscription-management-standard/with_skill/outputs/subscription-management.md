# Subscription Management

> Solution Architect | Depth: standard | Generated: 2026-06-09

## Existing Knowledge

_No librarian skill is available in this run, so no existing artifacts could be loaded or verified. Before building on this breakdown, an agent with librarian access should search for prior work to avoid duplication:_

- **Category `researches`** — keywords: "SaaS pricing models", "subscription proration", "payment retry / dunning", "involuntary churn". Useful to anchor plan definitions and the proration/retry policies flagged below.
- **Category `specs`** — keywords: "subscription billing", "billing lifecycle", "invoice generation". A prior billing spec would supersede or refine several capabilities here.
- **Category `docs`** — keywords: "payment gateway integration", "tax / invoicing requirements", "plan catalog". Integration contracts and tax rules directly affect CAP-02 and CAP-06.

## Problem Statement

- **Business problem**: The business needs reliable recurring revenue and the flexibility to monetize at different commitment levels (monthly vs. yearly). Without managed subscriptions, it cannot bill periodically, capture revenue from plan changes, or recover revenue lost to failed payments — directly limiting MRR/ARR and inflating involuntary churn.
- **User problem**: Customers want to choose a plan and billing cadence that fits their budget, change that plan as their needs evolve (upgrade/downgrade/cancel), and trust that billing is fair, transparent, and predictable — with clear invoices and graceful handling when a payment fails.
- **Success criteria**:
  - At least 95% of due subscriptions are billed successfully on time each cycle.
  - Involuntary churn from failed payments stays below 3% of recurring revenue (measured after the retry/dunning window).
  - Users can change plan or billing cadence in under 30 seconds without contacting support.
  - Every successful charge produces a correct, itemized invoice with proration reflected accurately.

## Scope

- **In scope**: Plan and cadence selection (monthly/yearly), initial payment at signup, recurring billing on both monthly and yearly cycles, subscription lifecycle (upgrade, downgrade, cancel, reactivate), proration on mid-cycle changes, invoice and credit-note generation, payment-failure handling with retry/dunning.
- **Out of scope** _(assumptions — see Open Questions)_: usage-based/metered billing, multi-currency, jurisdiction-specific tax calculation (assumes a single configurable tax rule applied uniformly), discount codes/coupons and promotional pricing, postal dunning, credit checks, and multiple concurrent subscriptions per user (assumed one active subscription per user).
- **Existing systems**: User account/identity system, email notification service, external payment gateway (stores tokenized payment methods), and an accounting/ERP system for reconciliation.

## Assumptions made (non-interactive run)

Because this run cannot ask clarifying questions, the breakdown proceeds on these stated assumptions; each is also surfaced in Open Questions where it materially affects design:

1. One active subscription per user; not a multi-product catalog per account.
2. A single configurable tax rule (flat) is applied; full tax-engine integration is out of scope.
3. Proration applies to both upgrades (immediate prorated charge) and the monthly↔yearly cadence switch; downgrades take effect at period end (credit-by-default, no immediate cash refund).
4. Payment methods are tokenized and stored by the gateway; the system never stores raw card data.
5. Free trials may exist but are treated as a property of plan selection, not a separate capability.

## Capabilities

### CAP-01: Plan and cadence selection

**Trigger**: A new user reaches the plan selection step at signup, or an existing user opens billing settings to change plan or switch billing cadence (monthly ↔ yearly).

**Inputs**:
- User account: authenticated user with account type (new vs. existing), from the user account system.
- Plan catalog: available plans with per-cadence pricing (monthly price, yearly price), included features, and any trial terms, defined by administrators.
- Current subscription (existing users): active plan, cadence, status, and current period dates, from CAP-03.

**Logic flow**:
1. System retrieves the plan catalog and displays each plan with both its monthly and yearly price (and the effective saving on yearly).
2. New users see all active plans; existing users see their current plan/cadence highlighted with available upgrade, downgrade, and cadence-switch paths.
3. User selects a plan and a billing cadence and confirms.
4. System classifies the action: new subscription, upgrade, downgrade, cadence change, or same selection.
5. System computes the change effect: upgrades and monthly→yearly switches are treated as immediate (prorated, routes to CAP-02); downgrades and yearly→monthly switches are scheduled for the next period boundary.
6. If the selection is identical to the current plan and cadence, system informs the user no change is needed.
7. **Error path**: If the catalog is unavailable, system shows a cached copy with a "pricing may be outdated" notice and revalidates plan status before accepting any selection.

**Outputs**:
- Selection record: user ID, plan ID, cadence, action type, timestamp — stored in the subscription management system.
- Pricing summary: chosen plan, cadence, amount due now (including proration), and next billing date — shown to the user.
- Routing signal: to CAP-02 when an immediate charge is required, otherwise to a confirmation view.

**Edge cases**:
- A retired plan still appears in cached data — verify active status before accepting.
- Existing user attempts a change while holding an outstanding/past-due balance — block until cleared (see CAP-06).
- User switches cadence and plan tier in one action — system resolves to a single net proration and one effective date.

**Connects to**: CAP-02, CAP-03

---

### CAP-02: Payment processing

**Trigger**: A selection (CAP-01) requires payment, an immediate upgrade/cadence-switch proration is due (CAP-03), or a recurring billing run is initiated (CAP-04).

**Inputs**:
- Payment method: a new payment entry from the user, or a stored tokenized payment method reference for recurring charges, held by the gateway.
- Customer information: user ID, email, name, from the user account system.
- Amount to charge: full plan price for the chosen cadence, or a prorated amount for mid-cycle changes, from CAP-01/CAP-03/CAP-04.
- Idempotency key: a unique key per logical charge to prevent duplicates.

**Logic flow**:
1. System assembles the charge (amount, currency, description, customer, idempotency key).
2. System submits the charge to the payment gateway and receives a response.
3. If approved, system records a successful transaction with the gateway transaction ID and stores/refreshes the payment-method token.
4. If declined, system records the failure with the decline reason code.
5. On success, system signals CAP-03 to activate/continue the subscription and CAP-05 to generate an invoice.
6. On failure, system triggers CAP-06 (retry/dunning).
7. **Error path**: If the gateway is unreachable, system retries the request up to a small fixed number of times with short delays, then reports a transient failure (distinct from a hard decline, which goes to dunning).

**Outputs**:
- Transaction record: user ID, amount, cadence context, gateway transaction ID, status, timestamp — stored in the transaction log.
- Payment confirmation or failure notice to the user, with receipt reference or reason and next steps.
- Activation signal to CAP-03; invoice trigger to CAP-05; retry trigger to CAP-06 on failure.

**Edge cases**:
- Charge approved but confirmation delayed — treat as pending and reconcile asynchronously; do not double-charge.
- Duplicate submissions in rapid succession — deduplicate via idempotency key.
- Zero-amount charge (e.g., free trial start, or proration nets to zero) — skip the gateway and record a zero-value transaction for the audit trail.
- Card flagged lost/stolen — gateway declines; treat as a decline and flag for review.

**Connects to**: CAP-01, CAP-03, CAP-04, CAP-05, CAP-06

---

### CAP-03: Subscription lifecycle

**Trigger**: A confirmed selection with successful initial payment (CAP-01/CAP-02), a user-initiated change, or a scheduled change taking effect at a period boundary.

**Inputs**:
- Lifecycle action: activate, upgrade, downgrade, switch cadence, cancel, reactivate, or expire — from CAP-01, CAP-02, CAP-06, or the scheduler.
- Current subscription state: plan, cadence, status (active, past-due, paused, cancelled, expired), current period start/end — from the subscription management system.
- Billing context: current period dates and grace/dunning state, from CAP-04/CAP-06.

**Logic flow**:
1. **Activate**: set status active, set period start, and set period end based on cadence (monthly = +1 month, yearly = +1 year).
2. **Upgrade**: apply the new plan immediately, compute the prorated charge for the remainder of the current period, and signal CAP-02 for the additional charge.
3. **Cadence switch (monthly→yearly)**: apply immediately, prorate the unused remainder of the monthly period as a credit against the yearly charge, and signal CAP-02.
4. **Downgrade / cadence switch (yearly→monthly)**: record as a pending change effective at the next period boundary; do not charge or refund now (credit-by-default per assumption).
5. **Cancel**: set cancel-at-period-end and schedule deactivation for the period boundary; access continues until then.
6. **Reactivate**: if within the active/grace window, restore to active and preserve the original period end; if after expiry, treat as a new activation.
7. **Expire**: set status expired and signal CAP-04 to stop billing.
8. **Error path**: reject actions that conflict with current state (e.g., upgrading a cancelled subscription) with a clear explanation.

**Outputs**:
- Updated subscription state (status, plan, cadence, period dates) — stored in the subscription management system.
- Lifecycle notification to the user via the notification service.
- Billing signal to CAP-04 (adjust schedule/amount) and invoice/credit-note trigger to CAP-05 for mid-cycle changes.

**Edge cases**:
- Cancel then reactivate within the same period — preserve the original period end; no new charge.
- A "downgrade" priced higher than current plan — validate direction and reclassify as an upgrade.
- Cancellation requested while a downgrade or cadence switch is pending — cancel the pending change and process the cancellation.
- Outstanding balance at cancel time — block until cleared.

**Connects to**: CAP-01, CAP-02, CAP-04, CAP-05

---

### CAP-04: Recurring billing cycle

**Trigger**: A scheduler runs daily to find subscriptions due for renewal (both monthly and yearly cadences).

**Inputs**:
- Due subscriptions: active subscriptions whose current period end is today or past, queried by the scheduler.
- Pending changes: any downgrades or yearly→monthly switches scheduled to take effect this boundary, from CAP-03.
- Grace/dunning configuration: days of grace and the retry policy, from administrators.

**Logic flow**:
1. Scheduler runs the daily due-check.
2. System collects all subscriptions whose period end is today or earlier.
3. For each, system first applies any pending plan/cadence change scheduled for this boundary (so the renewal charges the correct new amount).
4. System computes the renewal amount from the (possibly updated) plan and cadence.
5. System signals CAP-02 to charge the stored payment method.
6. On success, system extends the period by one cadence unit (+1 month or +1 year) and signals CAP-05 for an invoice.
7. On failure, system flags the subscription past-due, starts the grace window, and hands off to CAP-06.
8. If grace expires without recovery, system signals CAP-03 to suspend/expire.
9. **Error path**: if the scheduler misses a day (downtime), the next run picks up everything that became due in the interim.

**Outputs**:
- Billing requests to CAP-02.
- Period extensions for successful renewals — stored in the subscription management system.
- Past-due flags with grace expiry dates; suspension signals to CAP-03.
- Invoice triggers to CAP-05 for successful renewals.

**Edge cases**:
- Yearly billing date is Feb 29 in a non-leap year — bill on Feb 28.
- Month-end anchor (e.g., the 31st) in a short month — use the last day of that month.
- Already billed earlier the same day — check last billing date to prevent double-billing.
- End-of-month/year spike of many due subscriptions — process sequentially; order is irrelevant.

**Connects to**: CAP-02, CAP-03, CAP-05

---

### CAP-05: Invoice and credit-note generation

**Trigger**: A successful charge (CAP-02), a mid-cycle lifecycle change with a proration (CAP-03), a successful renewal (CAP-04), or a refund/credit event.

**Inputs**:
- Invoice event: type (initial, renewal, upgrade-proration, cadence-switch, credit/refund) and associated transaction ID — from CAP-02/CAP-03/CAP-04.
- Transaction record: amount, date, gateway reference — from CAP-02.
- Customer details: name, email, billing address — from the user account system.
- Subscription details: plan name, cadence, period start/end — from CAP-03.

**Logic flow**:
1. System receives the invoice event and gathers transaction, customer, and subscription data.
2. System assembles an itemized document: sequential invoice number, customer info, plan/cadence, billing period, line items (base charge, prorated charges, credits), tax line, and total.
3. System confirms the computed total matches the transaction amount; if it does not, it flags for review rather than emitting a mismatched invoice.
4. For credits/refunds, system issues a credit note linked to the original invoice instead of a new charge invoice.
5. System stores the document, links it to the user and transaction, emails it to the user, and exposes it in the billing portal.
6. **Error path**: if the transaction record is missing, generate the invoice marked "payment pending verification" and reconcile later.

**Outputs**:
- Invoice or credit-note document — stored in the invoice repository and delivered to the user.
- Invoice metadata (number, user ID, transaction ID, amount, status) — stored for reconciliation with the accounting/ERP system.
- Email notification to the user.

**Edge cases**:
- Refund after an invoice was issued — emit a linked credit note; never alter the original.
- Failed transaction — no invoice generated.
- Multiple same-day transactions (e.g., upgrade proration + renewal) — separate invoices per transaction.
- Invoice numbering reset at fiscal-year boundary — support configurable numbering patterns.

**Connects to**: CAP-02, CAP-03, CAP-04

---

### CAP-06: Payment failure handling (retry / dunning)

**Trigger**: A charge fails with a hard decline (CAP-02), or a renewal charge fails (CAP-04).

**Inputs**:
- Failed transaction: user ID, amount, decline reason code, gateway reference — from CAP-02.
- Retry/dunning configuration: max attempts and retry schedule — from administrators.
- Customer contact and notification preferences — from the user account system.

**Logic flow**:
1. System records the failure and reads the current retry count for the subscription.
2. If below the maximum, system schedules the next retry per the configured schedule (e.g., day 3, 7, 14) and emails the user a payment-failed notice with the next retry date and a link to update their payment method.
3. On each scheduled date, system signals CAP-02 to re-attempt using the stored payment method.
4. On success, system sends a payment-recovered notice and signals CAP-03 to clear the past-due flag and return to active.
5. On failure, system increments the retry count and schedules the next attempt.
6. If the user updates their payment method mid-window, system resets the retry count and attempts immediately.
7. If all attempts are exhausted, system sends a final notice and signals CAP-03 to suspend/expire the subscription.
8. **Error path**: if the stored payment method is removed during the window, cancel pending retries and prompt the user to add a new method.

**Outputs**:
- Retry schedule records (dates, status) — stored in the retry/dunning system.
- Failure, recovery, and final notices to the user.
- Subscription suspension signal to CAP-03 on exhaustion; past-due clear signal on recovery.
- Updated retry count stored against the subscription.

**Edge cases**:
- Gateway down at a scheduled retry — reschedule (e.g., +24h) without consuming an attempt.
- Replacement card also declines — schedule continues; count behavior per configuration.
- Subscription cancelled during the window — cancel remaining retries.
- Support-initiated manual retry — an authorized admin can trigger an immediate attempt and reset the counter.

**Connects to**: CAP-02, CAP-03

---

## Dependency Map

| Capability | Depends on | Feeds into |
|-----------|-----------|------------|
| CAP-01 Plan and cadence selection | — | CAP-02, CAP-03 |
| CAP-02 Payment processing | CAP-01 | CAP-03, CAP-05, CAP-06 |
| CAP-03 Subscription lifecycle | CAP-01, CAP-02 | CAP-02, CAP-04, CAP-05 |
| CAP-04 Recurring billing cycle | CAP-03 | CAP-02, CAP-03, CAP-05 |
| CAP-05 Invoice / credit-note generation | CAP-02, CAP-03, CAP-04 | — |
| CAP-06 Payment failure handling | CAP-02, CAP-04 | CAP-02, CAP-03 |

## Open Questions

- **Multiple subscriptions per user**: This breakdown assumes one active subscription per account. Is that correct, or must a user hold several products at once? (Affects CAP-01 and CAP-03 modeling.)
- **Downgrade economics**: On downgrade or yearly→monthly switch, should unused value become an account credit (assumed default) or a cash refund? Cash refunds add tax/refund complexity to CAP-02 and CAP-05.
- **Yearly proration on upgrade**: When a yearly subscriber upgrades mid-term, how is the large prorated balance handled — single immediate charge, or amortized? (Affects CAP-02/CAP-03.)
- **Trials**: Are free trials in scope, and do they require a payment method up front? (Currently treated as a plan property in CAP-01.)
- **Tax**: Assumed a single flat configurable rule. If jurisdiction-based tax is required, CAP-05 needs a tax-engine dependency.
- **Cancellation policy**: Is there a minimum commitment (especially for yearly plans), and does cancel always mean cancel-at-period-end (assumed) or allow immediate cancellation with refund?

## Research Suggestions

_Delegate these to the researcher skill; no research was conducted in this run._

- **Proration for plan and cadence changes** — Define a fair, transparent proration model, especially for monthly↔yearly switches and mid-term yearly upgrades. Suggested researcher query: "How SaaS companies prorate subscription charges on plan upgrades, downgrades, and monthly-to-annual switches — credit vs. refund and customer-perceived fairness."
- **Retry / dunning schedule optimization** — Determine retry intervals and max attempts that maximize recovery while limiting gateway cost and churn. Suggested researcher query: "Optimal payment retry intervals and dunning email cadence for SaaS subscriptions to minimize involuntary churn."
- **Revenue recognition for annual vs. monthly billing** — Yearly upfront billing recognized over 12 months has compliance implications. Suggested researcher query: "Revenue recognition under ASC 606 for annual upfront SaaS billing — deferred revenue, proration, and refunds."

## Next Steps

1. Resolve the Open Questions, prioritizing multiple-subscriptions, downgrade credit-vs-refund, and yearly-upgrade proration — they reshape CAP-01/CAP-02/CAP-03.
2. Define the plan catalog with explicit monthly and yearly prices, features, trial terms, and the yearly saving displayed to users.
3. Specify the proration formula precisely (per-day vs. per-second, rounding rules) for upgrades and cadence switches.
4. Establish the payment gateway integration contract (authorize/capture/refund, tokenization, idempotency) and the tax application rule.
5. Design the billing-portal flows for plan/cadence changes, payment-method updates, invoice/credit-note viewing, and dunning recovery.
6. Once approved, persist this document via the librarian skill as a `specs` artifact (e.g., keyword "subscription management").

---
*Capability breakdown produced by solution-architect skill. Use the librarian skill to persist this artifact.*
