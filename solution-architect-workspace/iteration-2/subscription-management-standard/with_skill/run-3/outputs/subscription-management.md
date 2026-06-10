# Subscription Management

> Solution Architect | Depth: standard | Generated: 2026-06-09

## Existing Knowledge

> The librarian skill is not available in this run, so existing artifacts could not be loaded. Before building on this breakdown, an agent with librarian access should check for prior work to avoid duplication:
> - **researches** — search keywords: "SaaS subscription billing", "proration strategies", "dunning / payment retry", "subscription pricing models"
> - **specs** — search keywords: "subscription management", "billing", "plan lifecycle", "invoicing"
> - **docs** — search keywords: "payment gateway integration", "invoice / tax rules"
> Most useful artifact types: any prior pricing/plan research, an existing payment gateway integration spec, and any tax/invoicing compliance notes.

## Problem Statement

- **Business problem**: The business needs reliable, predictable recurring revenue. Without subscription management it cannot bill customers on a repeating cycle, monetize plan changes, recover failed payments, or produce the invoices required for accounting and customer records. Involuntary churn (failed payments) and friction in plan changes directly erode revenue.
- **User problem**: Customers want to pick a plan that fits their needs, pay on a cadence they choose (monthly or yearly), change plans as their usage grows or shrinks, cancel cleanly, and trust that billing is accurate, fairly prorated, and well documented with invoices.
- **Success criteria**:
  - Recurring revenue is collected on time for at least 95% of active subscriptions.
  - Involuntary churn from failed payments stays below 3% of revenue after retries.
  - Users can upgrade, downgrade, or cancel self-service in under 30 seconds without contacting support.
  - Every successful charge produces an accurate, accessible invoice within minutes.

## Scope

- **In scope**: Plan catalog and selection; signup and initial payment; recurring billing on monthly and yearly cycles; subscription lifecycle (upgrade, downgrade, cancel, reactivate); proration of mid-cycle changes; payment failure handling with retries and dunning; invoice generation and delivery.
- **Out of scope**: Usage-based / metered billing; multi-currency; detailed tax determination by jurisdiction (this breakdown assumes a tax rate is supplied and applied, not calculated here); credit checks; postal dunning; coupon/discount engine (flagged as an Open Question); revenue-recognition accounting beyond invoice issuance.
- **Existing systems**: User account/identity system; payment gateway (card processing, tokenized payment methods); email/notification service; accounting/ERP system for reconciliation; billing/self-service portal UI.

> **Assumptions made for this non-interactive run** (would normally be confirmed with the user; see Open Questions):
> 1. Both monthly and yearly billing intervals are supported per plan; yearly is typically discounted.
> 2. Upgrades apply immediately with a prorated charge; downgrades take effect at the end of the current period (no immediate refund), with prorated credit applied to future invoices.
> 3. Cancellation is "cancel at period end" by default; the user retains access until the paid period expires.
> 4. Payment methods are stored as gateway tokens; the system does not hold raw card data.
> 5. Tax is applied as a supplied rate; jurisdiction-specific tax calculation is external.

## Capabilities

### CAP-01: Plan catalog and selection

**Trigger**: A new user reaches the plan selection step during signup, or an existing user opens billing settings to change plans.

**Inputs**:
- User account: authenticated user record with status (new vs. existing), from the account system.
- Plan catalog: available plans with pricing per billing interval (monthly/yearly), included features, and active status, defined by administrators.
- Current subscription (existing users): active plan, billing interval, and status, from CAP-03.

**Logic flow**:
1. System retrieves the plan catalog and displays active plans with monthly and yearly prices side by side, showing the yearly savings.
2. New users see all active plans; existing users see their current plan highlighted with available upgrade/downgrade and interval-switch options.
3. User selects a plan and billing interval and confirms.
4. System classifies the action: new subscription, upgrade, downgrade, interval change, or same-plan.
5. System records the selection (plan ID + interval) against the account.
6. If payment is required now (new subscription or upgrade), route to CAP-02 with the amount (prorated where applicable, computed by CAP-07).
7. If it is a downgrade or a yearly→monthly style change that reduces value, schedule the change for period end via CAP-03.
8. If same plan + interval, inform the user no change is needed.
9. **Error path**: If the catalog is unavailable, show a cached copy with a "pricing may be outdated" notice and block final confirmation until refreshed.

**Outputs**:
- Selection record: user ID, plan ID, billing interval, action type, timestamp, stored in the subscription system.
- Pricing summary: selected plan, interval, amount due now, and next billing date, shown to the user.
- Routing signal: to CAP-02 (payment) or to a confirmation page.

**Edge cases**:
- Plan retired but cached as active — re-check active status before accepting.
- Existing user with an outstanding/past-due balance — block plan changes until cleared.
- User switches monthly→yearly mid-cycle — treat as an upgrade-style change requiring proration (CAP-07).

**Connects to**: CAP-02, CAP-03, CAP-07

---

### CAP-02: Payment processing

**Trigger**: A selection (CAP-01) needs payment, an upgrade needs an immediate prorated charge (CAP-03/CAP-07), or a recurring cycle is due (CAP-04).

**Inputs**:
- Payment method: new card details from a payment form, or a stored gateway token for recurring/known users.
- Customer info: user ID, email, name, billing address, from the account system.
- Amount to charge: plan price for the chosen interval, or a prorated amount from CAP-07, including applicable tax.

**Logic flow**:
1. System obtains the payment method (new entry or stored token).
2. System assembles the charge: amount, currency, tax, description, customer reference, and an idempotency key.
3. System submits the charge to the payment gateway and stores the returned payment-method token for future cycles.
4. On approval: record a successful transaction with the gateway transaction ID; signal CAP-03 to activate/continue and CAP-05 to invoice.
5. On decline: record the failure with the decline reason; trigger CAP-06 (retry/dunning).
6. **Error path**: If the gateway is unreachable, retry up to 3 times with short delays, then report a temporary failure and queue for re-attempt; never double-charge thanks to the idempotency key.

**Outputs**:
- Transaction record: user ID, amount, tax, currency, gateway ID, status, timestamp, in the transaction log.
- Payment confirmation or failure notification to the user.
- Activation signal to CAP-03; invoice trigger to CAP-05; retry trigger to CAP-06 on failure.

**Edge cases**:
- Approval with delayed confirmation — treat as pending and verify asynchronously.
- Duplicate rapid submissions — deduplicated via idempotency key.
- Zero-amount charge (free trial / fully credited downgrade) — skip the gateway, record a zero-value transaction.
- Card flagged lost/stolen — handle as a normal decline, flag for review.

**Connects to**: CAP-01, CAP-03, CAP-04, CAP-05, CAP-06, CAP-07

---

### CAP-03: Subscription lifecycle

**Trigger**: A confirmed selection + payment (CAP-01/CAP-02), a user-initiated change, or a scheduled change taking effect at period end.

**Inputs**:
- Lifecycle action: activate, upgrade, downgrade, switch interval, cancel, reactivate, expire — from CAP-01, CAP-02, or the scheduler.
- Current subscription state: plan, interval, status (active/past-due/cancelled/expired), period start/end, from the subscription system.
- Billing context: current period dates and grace-period status, from CAP-04.

**Logic flow**:
1. Receive the lifecycle action.
2. **Activate**: set status active, set period start, schedule first cycle end based on interval (monthly/yearly).
3. **Upgrade**: apply the new plan immediately, request a prorated charge for the remainder of the period (CAP-07 computes, CAP-02 charges).
4. **Downgrade**: record as pending; apply at period end. Compute prorated credit (CAP-07) to apply to future invoices.
5. **Interval change** (e.g., monthly→yearly): treat value increases as upgrades (immediate, prorated); value decreases as period-end changes.
6. **Cancel**: set to cancel-at-period-end; user keeps access until period end; schedule deactivation.
7. **Immediate cancel (admin)**: deactivate now; compute any refund/credit due via CAP-07.
8. **Reactivate**: if within the paid period, restore active and keep the original period end; if after expiry, treat like a new activation.
9. **Expire**: set status expired; signal CAP-04 to stop billing.
10. **Error path**: Reject actions that conflict with current state (e.g., upgrading a cancelled subscription) with a clear explanation.

**Outputs**:
- Updated subscription state (status, plan, interval, period dates) in the subscription system.
- Lifecycle notifications to the notification service.
- Billing adjustment signal to CAP-04; invoice/credit trigger to CAP-05.

**Edge cases**:
- Cancel then reactivate within the same period — preserve original period end.
- "Upgrade" to a cheaper plan — validate price direction and reclassify as downgrade.
- Cancellation requested while a downgrade is pending — drop the pending downgrade, process cancellation.
- Pending downgrade plus a new upgrade — supersede the pending downgrade with the upgrade.

**Connects to**: CAP-01, CAP-02, CAP-04, CAP-05, CAP-07

---

### CAP-04: Billing cycle (recurring renewals)

**Trigger**: A scheduler runs daily to find subscriptions due for renewal (monthly or yearly).

**Inputs**:
- Due subscriptions: active subscriptions whose current period end is today or past due, from a scheduler query.
- Plan pricing: current price for the subscription's plan and interval.
- Grace-period configuration: days a past-due subscription stays active before suspension, from administrators.

**Logic flow**:
1. Scheduler runs the daily check.
2. Query all active subscriptions due today or earlier (covering both monthly and yearly cycles).
3. For each, apply any pending period-end change first (e.g., scheduled downgrade or interval switch from CAP-03), then compute the renewal amount.
4. Signal CAP-02 to charge the renewal amount.
5. On success: extend the period by one interval, update the period end, trigger CAP-05 to invoice.
6. On failure: flag past-due, start the grace-period counter, trigger CAP-06 (retry/dunning), keep access during grace.
7. If grace expires without payment: signal CAP-03 to suspend.
8. **Error path**: If the scheduler misses a day, the next run picks up everything that became due in the interim; the last-billed date guards against double-billing.

**Outputs**:
- Renewal charge requests to CAP-02.
- Updated period end dates for successful renewals.
- Past-due flags with grace-expiry dates; suspension signals to CAP-03.
- Invoice triggers to CAP-05.

**Edge cases**:
- Billing date is Feb 29 in a non-leap year — bill on Feb 28; month-end dates (e.g., the 31st) anchor to the last valid day of shorter months.
- Already billed earlier same day — check last-billed date to prevent duplicates.
- Yearly anniversary handling — yearly subscriptions renew on the same calendar date one year later.
- End-of-month spike — process sequentially; order does not matter.

**Connects to**: CAP-02, CAP-03, CAP-05, CAP-07

---

### CAP-05: Invoice generation and delivery

**Trigger**: A successful payment (CAP-02), a lifecycle change with a financial effect (CAP-03), or a completed renewal (CAP-04).

**Inputs**:
- Invoice event: trigger type (initial, renewal, upgrade, downgrade credit, reactivation) and transaction/credit reference.
- Transaction record: amount, tax, date, gateway reference, from CAP-02.
- Proration detail: prorated charge or credit line items, from CAP-07.
- Customer details: name, email, billing address, from the account system.
- Subscription details: plan name, interval, period start/end, from CAP-03.

**Logic flow**:
1. Receive the invoice event and gather transaction, proration, customer, and subscription data.
2. Assemble the invoice: sequential invoice number, customer info, plan/interval description, billing period, itemized line items (base charge, prorated adjustments, credits), tax line, and total.
3. Confirm the computed total matches the transaction amount (or that a credit note carries no charge).
4. Render a printable invoice document.
5. Store the invoice, associating it with the user and transaction.
6. Email the invoice to the user and publish it to the billing portal.
7. **Error path**: If the transaction record is missing, issue the invoice marked "payment pending verification" and reconcile later.

**Outputs**:
- Invoice document (number, dates, customer info, line items, tax, total) stored and sent to the user.
- Invoice metadata record for reconciliation.
- Credit note for downgrade credits or refunds.
- Email notification with the invoice/link.

**Edge cases**:
- Refund after invoicing — issue a credit note linked to the original invoice.
- Failed transaction — no invoice generated.
- Multiple same-day transactions (upgrade + renewal) — separate invoices per transaction.
- Fiscal-year numbering reset — support configurable numbering patterns.

**Connects to**: CAP-02, CAP-03, CAP-04, CAP-07

---

### CAP-06: Payment failure handling and dunning

**Trigger**: A charge fails in CAP-02 (decline or error), typically during a renewal (CAP-04).

**Inputs**:
- Failed transaction: user ID, amount, decline reason, gateway reference, from CAP-02.
- Retry configuration: max attempts and retry schedule (e.g., day 1, 3, 5, 7), from administrators.
- Customer contact info and notification preferences, from the account system.

**Logic flow**:
1. Receive the failed transaction.
2. Check the current retry count for this billing attempt.
3. If below max, schedule the next retry per the configured schedule and send a payment-failed/dunning notice with the next attempt date and a link to update the payment method.
4. On the scheduled date, signal CAP-02 to re-attempt with the stored method.
5. On retry success: send a recovery notice, clear past-due, restore active status via CAP-03, trigger invoice (CAP-05).
6. On retry failure: increment the count, schedule the next attempt.
7. When attempts are exhausted: send a final notice and signal CAP-03 to suspend.
8. If the user updates their payment method during the window: reset retries and attempt immediately.
9. **Error path**: If the stored method is removed mid-window, cancel pending retries and prompt the user to add a new method.

**Outputs**:
- Retry schedule records (dates, statuses).
- Dunning notifications at each failure and at exhaustion; recovery notification on success.
- Suspension signal to CAP-03 when exhausted; reactivation signal on recovery.
- Updated retry counter.

**Edge cases**:
- Updated card also fails — schedule continues; counter resets only if configured.
- Gateway down during a scheduled retry — reschedule ~24h later.
- Admin-triggered manual retry — allowed, resets the counter.
- Subscription cancelled during the window — cancel remaining retries.

**Connects to**: CAP-02, CAP-03, CAP-04, CAP-05

---

### CAP-07: Proration and credit calculation

**Trigger**: A mid-cycle plan or interval change (CAP-01/CAP-03), an immediate admin cancellation with refund, or any change that alters the amount owed within an active period.

**Inputs**:
- Change context: old plan/interval/price, new plan/interval/price, change date, current period start/end, from CAP-03.
- Proration policy: how unused time is valued and whether credits are refunded or carried forward, from administrators.
- Tax rate applicable to the adjustment.

**Logic flow**:
1. Determine unused time remaining in the current period as of the change date.
2. Compute the unused-value credit for the old plan and the cost of the new plan for the remaining period.
3. For an upgrade: charge the difference (new prorated cost minus old prorated credit) immediately via CAP-02; produce charge line items for CAP-05.
4. For a downgrade: compute the credit; per policy, carry it forward to reduce the next invoice (default) or refund it.
5. For an interval switch to yearly: apply the credit for the unused monthly remainder against the new yearly charge.
6. For immediate admin cancellation: compute the refundable unused portion, if policy allows.
7. Apply tax to net adjustments.
8. **Error path**: If the change date or period boundaries are inconsistent, default to next-period-boundary handling (no immediate proration) and flag for review.

**Outputs**:
- Proration result: net charge or credit amount with itemized line items, sent to CAP-02 (charge) and CAP-05 (invoice/credit note).
- Credit balance updates carried forward to future billing where applicable.

**Edge cases**:
- Multiple changes within one period — proration is computed against the most recent effective state, not cumulatively double-counted.
- Change on the first or last day of a period — minimal/zero proration.
- Downgrade credit exceeds the next invoice — carry remaining credit forward to subsequent periods.
- Rounding differences — apply a consistent rounding rule and absorb sub-cent remainders.

**Connects to**: CAP-01, CAP-02, CAP-03, CAP-04, CAP-05

## Dependency Map

| Capability | Depends on | Feeds into |
|-----------|-----------|------------|
| CAP-01 | — | CAP-02, CAP-03, CAP-07 |
| CAP-02 | CAP-01 | CAP-03, CAP-04, CAP-05, CAP-06, CAP-07 |
| CAP-03 | CAP-01, CAP-02 | CAP-04, CAP-05, CAP-07 |
| CAP-04 | CAP-03 | CAP-02, CAP-03, CAP-05, CAP-07 |
| CAP-05 | CAP-02, CAP-03, CAP-04, CAP-07 | — |
| CAP-06 | CAP-02 | CAP-02, CAP-03, CAP-04, CAP-05 |
| CAP-07 | CAP-01, CAP-03 | CAP-02, CAP-05 |

## Open Questions

- **Downgrade credits**: carry forward to the next invoice (assumed default) or refund immediately? Affects CAP-07 and CAP-05.
- **Cancellation policy**: cancel-at-period-end (assumed) vs. immediate cancel with prorated refund for self-service users? Any minimum commitment for yearly plans?
- **Yearly discount mechanics**: is the yearly price a fixed catalog price or a percentage discount off 12 monthly charges? Affects catalog display (CAP-01) and proration (CAP-07).
- **Discounts/coupons**: is a promo/coupon engine in scope? Currently excluded — would add inputs to CAP-01, CAP-02, CAP-07.
- **Multiple subscriptions per user**: can one account hold more than one active subscription (e.g., multiple products)?
- **Trials**: are free trials offered, and do they convert automatically to paid (affecting CAP-02 zero-amount and CAP-03 activation)?
- **Tax determination**: confirmed external — who supplies the rate, and does the invoice need tax IDs / reverse-charge handling?

## Research Suggestions

Topics flagged for the **researcher skill** (not researched here):

- **Proration strategies for plan and interval changes** — Need the fairest, clearest model for crediting unused time on upgrades, downgrades, and monthly↔yearly switches. Suggested query: "Best practices for prorating SaaS subscription charges and credits on mid-cycle upgrades, downgrades, and billing-interval changes."
- **Dunning and payment retry scheduling** — Need an optimal retry cadence and max attempts that maximize recovery without excess gateway fees or annoying customers. Suggested query: "Payment retry and dunning best practices for SaaS — optimal retry intervals, max attempts, and recovery email sequencing."
- **Monthly vs. yearly pricing and discount structure** — Inform yearly discount mechanics and their effect on proration. Suggested query: "How SaaS companies structure annual vs. monthly pricing and discounts, and the billing implications for proration and refunds."
- **Invoice and revenue-recognition compliance** — Invoicing must align with accounting standards, especially with yearly billing recognized over time. Suggested query: "Invoice requirements and ASC 606 revenue recognition for SaaS subscriptions with monthly and annual billing."

## Next Steps

1. Resolve the Open Questions, especially downgrade-credit and cancellation policies, to finalize CAP-07.
2. Define the plan catalog with concrete monthly and yearly prices, features, and any trial terms.
3. Design the billing-portal flows for plan/interval changes, payment-method updates, invoice access, and dunning recovery.
4. Establish the payment gateway integration contract (authorize, capture, tokenize, refund) and the tax-rate source.
5. Hand the flagged topics to the researcher skill, then revisit proration and dunning specifics.

---
*Capability breakdown produced by solution-architect skill. Use the librarian skill to persist this artifact.*
