# Subscription Management

> Solution Architect | Depth: standard | Generated: 2026-06-09

> **Note on this run**: This was produced non-interactively. Where the skill would normally ask the user 3-4 rounds of clarifying questions, reasonable assumptions were made and are flagged in **Open Questions**. The librarian skill was unavailable (see **Existing Knowledge** for what to retrieve), and research topics are flagged for the researcher skill rather than researched here.

## Existing Knowledge

The librarian skill was **not available** during this run, so no existing artifacts could be loaded. Before building on this breakdown, an agent with librarian access should search for prior work to avoid duplication:

- **Category `researches`** — keywords: "SaaS pricing models", "subscription proration", "payment retry / dunning", "monthly vs annual billing". These would inform plan definition, proration logic, and the retry policy.
- **Category `specs`** — keywords: "billing", "subscription", "invoicing", "payment gateway". A prior billing spec would refine scope boundaries and the dependency map.
- **Category `docs`** — keywords: "payment gateway integration", "tax handling", "accounting reconciliation". These would clarify which existing systems this must integrate with.

## Problem Statement

- **Business problem**: The business needs reliable, predictable recurring revenue. Without subscription management, it cannot bill customers on a cadence, capture revenue from plan upgrades, recover failed payments, or produce the invoices needed for accounting and compliance. Every uncollected charge and every cancelled-but-uncharged customer is lost revenue.
- **User problem**: Customers want to pick a plan that fits their needs and budget, pay on a cycle that suits them (monthly or yearly), and change their commitment as their usage grows or shrinks — without friction, surprise charges, or losing access unexpectedly when a card declines. They also want clear records (invoices) of what they paid for.
- **Success criteria**:
  - Recurring revenue is collected on time for at least 95% of active subscriptions.
  - Involuntary churn from failed payments (after retries) stays below 3% of revenue.
  - Users can upgrade, downgrade, or cancel self-service in under 30 seconds without contacting support.
  - Every successful charge produces a correct, tax-inclusive invoice available to the user within minutes.
  - Proration on mid-cycle changes is accurate to the cent and explainable to the customer.

## Scope

- **In scope**: Plan catalog and selection; signup and initial payment; recurring billing on **both monthly and yearly** cycles; subscription lifecycle (upgrade, downgrade, cancel, reactivate, expire); proration for mid-cycle plan changes; payment failure handling with retries and dunning; invoice and credit-note generation; payment method management.
- **Out of scope** (assumed — see Open Questions): Usage-based / metered billing; multi-currency; per-jurisdiction tax calculation (assumes a tax rate is supplied or a flat rate is applied); coupons/discount codes as a first-class system (proration credits are in scope, promotional discounts are not); postal dunning letters; credit checks; reseller/partner billing.
- **Existing systems**: User account / identity system; email (and optionally in-app) notification service; external payment gateway (tokenized card storage, charge, refund); accounting/ERP system for revenue reconciliation; admin/support console.

## Capabilities

### CAP-01: Plan catalog & selection

**Trigger**: A new user reaches the plan selection step during signup, or an existing user opens billing settings to change plans.

**Inputs**:
- Plan catalog: available plans with price per billing interval (monthly and yearly), included features, and active/retired status — defined by administrators.
- User account: authenticated user with account state (new vs. existing) — from the user account system.
- Current subscription (existing users): active plan, billing interval, and status — from CAP-03.

**Logic flow**:
1. System retrieves the active plan catalog and presents each plan with its monthly and yearly price (and any implied yearly savings).
2. New users see all active plans; existing users see their current plan highlighted with available upgrade/downgrade paths.
3. User selects a plan **and a billing interval** (monthly or yearly) and confirms.
4. System classifies the action: new subscription, upgrade, downgrade, interval change, or same-plan (no-op).
5. If new subscription or upgrade (higher effective value): route to payment processing (CAP-02), requesting a proration quote from CAP-07 for upgrades.
6. If downgrade or interval reduction: schedule the change for the next billing period end (no immediate charge); record any proration credit via CAP-07.
7. If same plan and interval: inform the user no change is needed.
8. **Error path**: If the catalog is unavailable, show the last-known catalog with a "pricing may be outdated" notice and block final confirmation until refreshed.

**Outputs**:
- Selected-plan intent record: user ID, plan ID, billing interval, action type, timestamp — stored in the subscription system.
- Pricing summary shown to user: plan, interval, amount due now (incl. proration if applicable), and next billing date.
- Routing signal to CAP-02 (payment needed) or to a confirmation page (scheduled change, no charge now).

**Edge cases**:
- Plan retired between page load and confirmation: re-validate active status before accepting.
- Existing user with an outstanding/past-due balance attempts a change: block until balance is cleared.
- User switches interval on the same plan (monthly → yearly): treat as an upgrade-style immediate charge with proration credit for the unused monthly portion.

**Connects to**: CAP-02, CAP-03, CAP-07

---

### CAP-02: Payment processing

**Trigger**: A flow needs money moved — initial signup payment, an immediate upgrade/interval-change charge, or a recurring renewal from CAP-04.

**Inputs**:
- Payment method: card/billing details entered by the user, or a stored tokenized payment method reference for recurring charges.
- Customer info: user ID, email, name — from the user account system.
- Amount to charge: plan price for the chosen interval, or a prorated amount — from CAP-01, CAP-04, or CAP-07.
- Idempotency key: a unique key per charge intent, to prevent duplicate charges.

**Logic flow**:
1. System obtains payment details (new entry) or the stored payment token (recurring).
2. System assembles the charge: amount, currency, description, customer reference, idempotency key.
3. System submits the charge to the payment gateway and receives the result.
4. If approved: record a successful transaction with the gateway reference; signal CAP-03 to activate/continue the subscription and CAP-05 to generate an invoice.
5. If declined: record the failure with the decline reason; signal CAP-06 (retry/dunning).
6. On first successful charge for a payment method, store the returned reusable token for future recurring charges (CAP-08).
7. **Error path**: If the gateway is unreachable, retry a small number of times with short delays; if still failing, mark the charge as a transient error and hand to CAP-06.

**Outputs**:
- Transaction record: user ID, amount, interval, gateway reference, status, timestamp — in the transaction log.
- Payment confirmation or failure notice to the user.
- Activation signal to CAP-03; invoice trigger to CAP-05; retry trigger to CAP-06 on failure.

**Edge cases**:
- Approved but confirmation delayed: treat as pending, verify status asynchronously, never double-charge.
- Duplicate submissions: deduplicate via idempotency key.
- Zero-amount charge (e.g., fully credited upgrade or free trial): skip the gateway, treat as success.
- Card flagged lost/stolen: treat as a decline, flag for review.

**Connects to**: CAP-01, CAP-03, CAP-04, CAP-05, CAP-06, CAP-07, CAP-08

---

### CAP-03: Subscription lifecycle

**Trigger**: A confirmed selection + payment (CAP-01/CAP-02), a user-initiated change, an admin action, or a scheduled change taking effect at period end.

**Inputs**:
- Lifecycle action: activate, upgrade, downgrade, change-interval, cancel, reactivate, expire — from CAP-01, CAP-02, or the scheduler.
- Current subscription state: plan, interval, status (active, past-due, paused, cancelled, expired), current period start/end — from the subscription system.
- Billing/period context: current period dates and grace-period status — from CAP-04.

**Logic flow**:
1. Receive a lifecycle action and validate it against the current state.
2. **Activate**: set status active, set period start, schedule first renewal at interval end (1 month or 1 year).
3. **Upgrade**: apply the new plan immediately; request a proration charge from CAP-07 and route it to CAP-02.
4. **Downgrade / interval reduction**: record as a pending change effective at period end; do not bill now; record any proration credit via CAP-07.
5. **Cancel**: set cancel-at-period-end and schedule deactivation for the period end date (user retains access until then).
6. **Immediate cancel (admin)**: deactivate now and compute any refund/credit via CAP-07.
7. **Reactivate**: restore active status; if within the same period, preserve the original period end, otherwise start a fresh period.
8. **Expire**: set status expired and tell CAP-04 to stop billing.
9. **Error path**: Reject actions that conflict with state (e.g., upgrading a cancelled subscription) with a clear explanation.

**Outputs**:
- Updated subscription state — in the subscription system.
- Lifecycle notifications to the notification service.
- Billing-adjustment signals to CAP-04; proration requests to CAP-07; invoice/credit-note triggers to CAP-05.

**Edge cases**:
- Cancel then reactivate within the same period: preserve original period end.
- Cancel requested while a downgrade is pending: drop the pending downgrade, process the cancellation.
- "Upgrade" to a cheaper plan: validate effective value and re-route as a downgrade.
- Pending downgrade + an upgrade requested before it applies: supersede the pending change.

**Connects to**: CAP-01, CAP-02, CAP-04, CAP-05, CAP-07

---

### CAP-04: Recurring billing cycle

**Trigger**: A scheduler runs (at least daily) to find subscriptions due for renewal — covering both monthly and yearly cycles.

**Inputs**:
- Due-subscriptions list: active subscriptions whose current period ends today or is past due — from the subscription system.
- Grace-period configuration: days after the billing date before suspension — from administrators.
- Pending scheduled changes: downgrades/interval changes set to apply at this period end — from CAP-03.

**Logic flow**:
1. Scheduler runs the due-check.
2. Query active subscriptions where period end ≤ today.
3. For each, first apply any pending scheduled change (downgrade/interval change) so the new price takes effect this cycle.
4. Compute the renewal amount from the (possibly updated) plan and interval.
5. Signal CAP-02 to charge the stored payment method.
6. On success: extend the period by one interval (1 month or 1 year), update period end, trigger CAP-05 invoice.
7. On failure: start the grace-period counter, flag the subscription past-due, hand to CAP-06.
8. If grace period expires without recovery: signal CAP-03 to suspend/expire.
9. **Error path**: If the scheduler misses a day, the next run picks up everything that became due in the interim (idempotent per-day billing guard prevents double-billing).

**Outputs**:
- Renewal charge requests to CAP-02.
- Period extensions and past-due flags in the subscription system.
- Suspension signals to CAP-03; invoice triggers to CAP-05.

**Edge cases**:
- Yearly anniversary on Feb 29 in a non-leap year: bill on Feb 28.
- Already billed earlier the same day: per-subscription billing guard prevents a second charge.
- End-of-month / end-of-year spikes (many renewals same day): process sequentially; order is irrelevant.
- Pending downgrade present at renewal: apply it before computing the charge.

**Connects to**: CAP-02, CAP-03, CAP-05, CAP-07

---

### CAP-05: Invoice & credit-note generation

**Trigger**: A successful charge (CAP-02), a lifecycle change with financial impact (CAP-03), a renewal (CAP-04), or a refund/credit event (CAP-07).

**Inputs**:
- Invoice event: type (initial, renewal, upgrade-proration, refund/credit) and related transaction ID — from CAP-02/03/04/07.
- Transaction record: amount, date, gateway reference — from CAP-02.
- Customer details: name, email, billing address — from the user account system.
- Subscription details: plan name, interval, period start/end, line items including proration — from CAP-03/CAP-07.
- Tax inputs: applicable tax rate/amount (assumed supplied; see scope).

**Logic flow**:
1. Receive the invoice/credit event and gather transaction, customer, and subscription data.
2. Assemble line items: base plan charge, prorated charges/credits, subtotal, tax, total.
3. Assign a sequential invoice (or credit-note) number per the configured numbering scheme.
4. Render a printable invoice/credit-note document.
5. Store it against the user and transaction; expose it in the billing portal.
6. Send it to the user by email (attachment or link).
7. **Error path**: If the transaction record is missing, generate the invoice marked "payment pending verification" and reconcile later.

**Outputs**:
- Invoice or credit-note document — stored and sent to the user.
- Invoice metadata (number, user, transaction, amount, status) — for reconciliation.
- Email notification to the user.

**Edge cases**:
- Refund after invoicing: issue a credit note linked to the original invoice rather than editing it.
- Failed transaction: no invoice generated.
- Multiple same-day transactions (upgrade proration + renewal): separate documents per transaction.
- Fiscal-year number reset: support configurable sequences.

**Connects to**: CAP-02, CAP-03, CAP-04, CAP-07

---

### CAP-06: Payment failure handling & dunning

**Trigger**: A charge fails (CAP-02 returns a decline or transient error).

**Inputs**:
- Failed-transaction record: user ID, amount, decline reason, gateway reference — from CAP-02.
- Retry/dunning configuration: max attempts and retry schedule — from administrators.
- Customer contact info and notification preferences — from the user account system.

**Logic flow**:
1. Receive the failed-charge details and read the current retry count for this subscription.
2. If retries remain, schedule the next attempt per the dunning schedule (e.g., +3d, +7d, +14d) and notify the user with the reason and next retry date.
3. On the scheduled date, signal CAP-02 to retry against the stored payment method.
4. On success: send a payment-recovered notice, clear past-due, restore the subscription via CAP-03.
5. On failure: increment the count and schedule the next attempt.
6. If attempts are exhausted: send a final notice and signal CAP-03 to suspend/expire.
7. If the user updates their payment method (CAP-08) during dunning: reset retries and attempt immediately.
8. **Error path**: If the gateway is down at a scheduled retry, reschedule (e.g., +24h) without consuming a retry attempt.

**Outputs**:
- Retry schedule and status records.
- Dunning notifications at each failure and at exhaustion; recovery notification on success.
- Suspension signal to CAP-03; updated retry count.

**Edge cases**:
- Replacement card also fails: schedule continues; count behavior is configurable.
- Support-initiated manual retry: an authorized admin can trigger an immediate retry and reset the counter.
- Subscription cancelled during dunning: cancel remaining retries.

**Connects to**: CAP-02, CAP-03, CAP-08

---

### CAP-07: Proration & credit calculation

**Trigger**: A mid-cycle change with financial impact — upgrade, downgrade, interval change, or immediate (admin) cancellation/refund — requested by CAP-01 or CAP-03.

**Inputs**:
- Change context: current plan/interval and price, new plan/interval and price, current period start/end, and the change date.
- Proration policy: how unused time is valued and whether credits are refunded or applied to the next cycle — from administrators (see Open Questions).

**Logic flow**:
1. Compute the unused portion of the current period (time remaining ÷ period length) and the credit for the old plan over that portion.
2. Compute the cost of the new plan over the same remaining portion.
3. **Upgrade / interval increase**: charge = new-plan remaining cost − old-plan unused credit; if positive, return an immediate charge amount to CAP-02.
4. **Downgrade / interval decrease**: typically no immediate charge; compute a credit for the difference and, per policy, either bank it toward the next invoice or queue a refund.
5. **Immediate cancellation**: compute the unused credit and, per policy, queue a refund or write it off.
6. Round consistently and produce an itemized breakdown (old-plan credit, new-plan charge, net).
7. **Error path**: If period dates are inconsistent or the change date is outside the current period, reject and surface for review.

**Outputs**:
- Proration quote / net amount — to CAP-01 (display) and CAP-02 (charge) or to the credit ledger.
- Itemized proration line items — to CAP-05 for the invoice/credit note.
- Credit balance updates on the account where applicable.

**Edge cases**:
- Change on the first or last day of the period (near-zero or near-full proration).
- Monthly → yearly switch: credit the unused monthly remainder against the new yearly charge.
- Multiple changes within one period: each prorates against the then-current state.
- Credit larger than the new charge (downgrade): results in account credit or refund, never a negative invoice.

**Connects to**: CAP-01, CAP-02, CAP-03, CAP-05

---

### CAP-08: Payment method management

**Trigger**: A user adds, updates, or removes a payment method in the billing portal; or the system needs a default method for a recurring charge.

**Inputs**:
- Payment details entered by the user (tokenized at capture).
- User account and existing stored methods.

**Logic flow**:
1. User submits a new or updated payment method; the system validates it with the gateway (e.g., a zero/low auth) and stores a reusable token.
2. User can mark a method as default for recurring charges.
3. On removal, the system checks whether it is the only/default method on an active subscription; if so, warn that recurring billing will fail without a replacement.
4. When a method is added/updated during dunning, signal CAP-06 to reset retries and attempt payment immediately.
5. **Error path**: If validation fails, do not store the method and explain why.

**Outputs**:
- Stored tokenized payment-method reference (default flag) — used by CAP-02 for recurring charges.
- Trigger to CAP-06 when a method changes during an active dunning cycle.
- Confirmation notification to the user.

**Edge cases**:
- Removing the last valid method on an active subscription: block or strongly warn.
- Expired card detected before renewal: proactively notify the user to update it.
- Multiple methods stored: clear default selection and fallback behavior.

**Connects to**: CAP-02, CAP-06

## Dependency Map

| Capability | Depends on | Feeds into |
|-----------|-----------|------------|
| CAP-01 Plan selection | CAP-07 (quotes) | CAP-02, CAP-03 |
| CAP-02 Payment processing | CAP-01, CAP-04, CAP-07, CAP-08 | CAP-03, CAP-05, CAP-06 |
| CAP-03 Subscription lifecycle | CAP-01, CAP-02, CAP-07 | CAP-04, CAP-05 |
| CAP-04 Recurring billing cycle | CAP-03 | CAP-02, CAP-05, CAP-07 |
| CAP-05 Invoice generation | CAP-02, CAP-03, CAP-04, CAP-07 | — |
| CAP-06 Payment failure / dunning | CAP-02, CAP-08 | CAP-02, CAP-03 |
| CAP-07 Proration & credits | CAP-01, CAP-03, CAP-04 | CAP-02, CAP-05 |
| CAP-08 Payment method mgmt | — | CAP-02, CAP-06 |

## Open Questions

These are assumptions made for this non-interactive run; confirm with stakeholders.

- **Proration credit handling**: On downgrade, are credits banked toward the next invoice or refunded immediately? (Assumed: banked toward next invoice.)
- **Yearly cancellation/refunds**: Are mid-term yearly cancellations refunded pro-rata, or is the annual term non-refundable? This materially changes CAP-03 and CAP-07.
- **Tax**: Is per-jurisdiction tax in scope, or is a single rate supplied externally? (Assumed: rate supplied; full tax engine out of scope.)
- **Trials**: Are free trials offered, and do they require a card up front? (Not modeled; would add a trial state to CAP-03 and a zero-amount path in CAP-02.)
- **Discounts/coupons**: Are promotional discount codes needed? (Assumed out of scope; proration credits are in scope.)
- **Minimum commitment**: Is there a minimum period before cancellation, especially for yearly plans?
- **Multiple subscriptions per user**: Can one account hold more than one active subscription (e.g., multiple products)?
- **Dunning schedule specifics**: Exact retry intervals and max attempts (assumed 3 attempts at +3d/+7d/+14d).

## Research Suggestions

Flagged for the researcher skill (not researched in this run):

- **Proration strategies for monthly↔yearly and plan changes** — Need the fairest, most explainable model for crediting unused time and switching intervals. Suggested query: "Best practices for prorating SaaS subscription charges and credits on upgrades, downgrades, and monthly-to-yearly interval changes."
- **Dunning and payment retry policy** — Optimal retry intervals, attempt counts, and email sequencing to maximize recovery while minimizing gateway costs and annoyance. Suggested query: "Payment retry and dunning best practices for SaaS — optimal retry schedule, max attempts, and recovery email cadence."
- **Refund policy for annual subscriptions** — Legal/commercial norms and customer-expectation trade-offs for mid-term yearly cancellations. Suggested query: "SaaS annual subscription refund and cancellation policy norms — pro-rata vs non-refundable."
- **Invoicing & revenue recognition compliance** — Invoice timing, credit notes, and deferred revenue for monthly vs yearly billing. Suggested query: "Revenue recognition (ASC 606) for monthly and annual SaaS subscriptions — invoice timing, proration, and credit-note handling."
- **Tax handling approach** — Whether to integrate a tax engine for multi-jurisdiction sales tax/VAT. Suggested query: "SaaS subscription tax handling — when to adopt a tax automation service for sales tax and VAT across jurisdictions."

## Next Steps

1. Resolve the Open Questions with stakeholders — especially proration credit handling, yearly refund policy, and trial support — as these change CAP-03 and CAP-07.
2. Define the concrete plan catalog: tiers, monthly and yearly prices, included features, and any yearly discount.
3. Confirm the dunning schedule (intervals + max attempts) and the grace-period length.
4. Specify the billing portal flows: plan/interval change, payment method management, invoice and credit-note access.
5. Have an agent with librarian access run the searches listed under **Existing Knowledge**, then reconcile this breakdown with any prior research or specs.
6. Use the librarian skill to save this document as a spec artifact.

---
*Capability breakdown produced by solution-architect skill. Use the librarian skill to persist this artifact.*
