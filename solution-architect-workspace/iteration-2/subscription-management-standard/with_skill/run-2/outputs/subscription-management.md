# Subscription Management

> Solution Architect | Depth: standard | Generated: 2026-06-09

## Existing Knowledge

The librarian skill is not available in this run, so existing artifacts could not be loaded. Before building on this breakdown, an agent with librarian access should search for prior work:

- **Category `researches`** — keywords: "SaaS pricing models", "subscription billing", "dunning", "proration". Prior pricing or willingness-to-pay research would inform the plan catalog and plan-change rules.
- **Category `specs`** — keywords: "subscription management", "billing", "invoicing". A prior billing spec would tell us which capabilities already exist and which are net-new.
- **Category `docs`** — keywords: "payment gateway integration", "invoice format", "tax rules". Operational docs that constrain how invoices and payments behave.

Retrieving these avoids duplicating decisions already made.

## Problem Statement

- **Business problem**: The business needs predictable recurring revenue. Without subscription management, the product cannot bill customers on a repeating cycle, capture revenue from plan changes, or recover revenue lost to failed payments — directly capping growth and inflating involuntary churn.
- **User problem**: Customers want to choose a plan that fits their needs and budget (monthly for flexibility, yearly for savings), change that plan as their usage grows or shrinks, cancel without friction, and trust that billing is accurate, transparent, and well-documented with invoices.
- **Success criteria**: Recurring revenue is collected on time for at least 95% of active subscriptions. Involuntary churn from failed payments stays below 3% of revenue. Users can upgrade, downgrade, or cancel self-service in under 60 seconds. Every successful charge produces a correct, itemized invoice with proration reflected accurately.

## Scope

- **In scope**: Plan catalog and selection; signup and initial payment; recurring billing on monthly and yearly cycles; subscription lifecycle (upgrade, downgrade, cancel, reactivate, expire); proration on mid-cycle plan and cycle changes; payment failure handling with retries and dunning; invoice and credit-note generation.
- **Out of scope** (assumed — see Open Questions): usage-based/metered billing; multi-currency; full tax-jurisdiction calculation (a flat or externally-supplied tax rate is assumed); add-ons and seat-based quantity billing; coupons/discount codes; trials beyond a simple free-trial-then-charge flow; postal dunning.
- **Existing systems**: User account/identity system; email/notification service; payment gateway (stores tokenized payment methods); accounting/ERP system for reconciliation.

## Capabilities

### CAP-01: Plan catalog and selection

**Trigger**: A new user reaches the plan selection step during signup, or an existing user opens billing settings to change plan or billing cycle.

**Inputs**:
- Plan catalog: available plans with prices for both monthly and yearly cycles, included features, and active/retired status, defined by administrators.
- User account: authenticated user record with account type (new vs. existing), from the account system.
- Current subscription (existing users): active plan, billing cycle, and status, from CAP-03.

**Logic flow**:
1. System retrieves the active plan catalog and displays each plan with its monthly and yearly price (yearly typically shown with the implied discount).
2. New users see all active plans; existing users see their current plan highlighted with available upgrade/downgrade and cycle-switch options.
3. User selects a plan and a billing cycle (monthly or yearly) and confirms.
4. System classifies the action: new subscription, upgrade, downgrade, cycle switch (monthly↔yearly), or same-plan/same-cycle (no-op).
5. If the change increases the amount owed now (upgrade, or monthly→yearly taken immediately), route to payment processing (CAP-02) with a prorated amount from CAP-03.
6. If the change decreases value (downgrade, or yearly→monthly), schedule it to take effect at the end of the current paid period.
7. If it is a no-op, inform the user they are already on this plan and cycle.
8. **Error path**: If the catalog is unavailable, show a cached copy with a "pricing may be outdated" notice and block final confirmation until live pricing is confirmed.

**Outputs**:
- Selection record: user ID, plan ID, chosen cycle, action type, timestamp, stored in the subscription system.
- Pricing summary: selected plan, cycle, amount due now, and next billing date, shown to the user.
- Routing signal: to CAP-02 if payment is needed now, otherwise to a confirmation page.

**Edge cases**:
- A plan is retired but still cached: re-check active status before accepting selection.
- User switches cycle and plan in one action: treat as a combined change and compute a single prorated amount.
- Existing user with outstanding/past-due balance attempts a change: block until balance is cleared.

**Connects to**: CAP-02, CAP-03

---

### CAP-02: Payment processing

**Trigger**: A selection (CAP-01) needs payment now, a recurring cycle is due (CAP-04), a prorated upgrade charge is required (CAP-03), or a retry is scheduled (CAP-06).

**Inputs**:
- Payment method: card/bank details entered at signup, or a stored tokenized payment-method reference for recurring/retry charges, from the payment gateway.
- Customer info: user ID, email, name, from the account system.
- Amount to charge: full plan price for the chosen cycle, or a prorated amount, from CAP-01 / CAP-03 / CAP-04, including an idempotency key.

**Logic flow**:
1. System collects payment details (new) or retrieves the stored payment-method token (recurring/retry).
2. System prepares the charge: amount, currency, description, customer reference, idempotency key.
3. System submits the charge to the payment gateway and receives the response.
4. If approved, record a successful transaction with the gateway transaction ID and signal CAP-03 to activate/continue and CAP-05 to invoice.
5. If declined, record the failure with the decline reason and trigger CAP-06 (retry/dunning).
6. **Error path**: If the gateway is unreachable, retry the request up to 3 times with short delays; if still unreachable, mark the charge pending and reconcile asynchronously rather than declining.

**Outputs**:
- Transaction record: user ID, amount, currency, gateway ID, status, timestamp, stored in the transaction log.
- Payment confirmation or failure notification to the user.
- Activation signal to CAP-03; invoice trigger to CAP-05; retry trigger to CAP-06 on failure.

**Edge cases**:
- Approved but confirmation delayed: treat as pending and verify status asynchronously.
- Duplicate submissions: idempotency key prevents double charges.
- Zero-amount charge (e.g., free trial, or downgrade credit fully covers the period): skip the gateway call and proceed as success.
- Card flagged lost/stolen: treat as a normal decline, flag for review.

**Connects to**: CAP-01, CAP-03, CAP-04, CAP-05, CAP-06

---

### CAP-03: Subscription lifecycle and proration

**Trigger**: A confirmed selection + payment (CAP-01/CAP-02), a user-initiated change, an admin action, or a scheduled change taking effect at period end.

**Inputs**:
- Lifecycle action: activate, upgrade, downgrade, switch cycle, cancel, reactivate, expire — from CAP-01, CAP-02, admin tools, or the scheduler.
- Current subscription state: plan, cycle, status (active/past-due/paused/cancelled/expired), current period start/end, from the subscription system.
- Plan pricing: monthly and yearly prices for source and target plans, from the catalog.

**Logic flow**:
1. Receive the lifecycle action and validate it against current state.
2. **Activate**: set status active, set period start, schedule the first cycle end based on chosen cycle (monthly/yearly).
3. **Upgrade**: apply the new plan immediately; compute proration — credit the unused portion of the current plan for the remaining days in the period and charge the prorated cost of the new plan for those days; signal CAP-02 for the net charge.
4. **Downgrade**: record as a pending change effective at period end; the user keeps current features until then; no immediate charge (assumed — no immediate refund; see Open Questions).
5. **Switch cycle**: monthly→yearly applies immediately with proration (credit remaining monthly value against the yearly price); yearly→monthly is scheduled for the end of the paid yearly term.
6. **Cancel**: record cancel-at-period-end; schedule deactivation for the last day of the paid period so the user retains access they paid for.
7. **Immediate cancel (admin)**: deactivate now and compute any refund due.
8. **Reactivate**: if within the paid period, restore active and preserve the original period end; if after expiry, treat as a new activation.
9. **Expire**: set status expired and signal CAP-04 to stop billing.
10. **Error path**: If the action conflicts with state (e.g., upgrading a cancelled subscription), reject with an explanation.

**Outputs**:
- Updated subscription state stored in the subscription system.
- Proration computation: credit and charge line items, passed to CAP-02 (charge) and CAP-05 (invoice line items).
- Lifecycle notification to the notification service.
- Billing-schedule signal to CAP-04; invoice trigger to CAP-05 for mid-cycle changes.

**Edge cases**:
- Cancel then reactivate within the same period: preserve original period end, no re-charge.
- "Upgrade" to a cheaper plan: validate target price is actually higher, else handle as a downgrade.
- Cancellation requested while a downgrade is pending: cancel the pending downgrade and process the cancellation.
- Leap-year / month-length anchor dates: a yearly subscription started Feb 29 renews Feb 28 in non-leap years; monthly anchored to the 31st bills on the last day of shorter months.

**Connects to**: CAP-01, CAP-02, CAP-04, CAP-05

---

### CAP-04: Recurring billing cycle

**Trigger**: A scheduler runs daily to find subscriptions due for renewal.

**Inputs**:
- Due subscriptions: active subscriptions whose period end is today or past, from the subscription system.
- Plan pricing and cycle: amount and cycle (monthly/yearly) for each due subscription.
- Grace-period configuration: days past due before suspension, from administrators.

**Logic flow**:
1. Scheduler runs the daily billing check.
2. Query active subscriptions with period end ≤ today, excluding any already billed today (duplicate guard).
3. For each, compute the next amount from the current plan and cycle, applying any scheduled change (pending downgrade or cycle switch) that takes effect at this renewal.
4. Signal CAP-02 to charge the stored payment method.
5. On success: extend the period by one cycle (one month or one year), update the period end, and trigger CAP-05 to invoice.
6. On failure: flag the subscription past-due, start the grace-period counter, and let CAP-06 manage retries/dunning.
7. If grace period expires without success, signal CAP-03 to suspend/expire.
8. **Error path**: If the scheduler misses a day (downtime), the next run picks up everything that became due in the gap.

**Outputs**:
- Billing requests to CAP-02.
- Period extensions stored in the subscription system.
- Past-due flags with grace-period expiry dates.
- Suspension signals to CAP-03; invoice triggers to CAP-05.

**Edge cases**:
- Many renewals on the same day (month/year-end spike): processed sequentially; order is irrelevant.
- Pending change due at this renewal: apply it before computing the amount.
- Already billed earlier today: skip via the duplicate guard.

**Connects to**: CAP-02, CAP-03, CAP-05

---

### CAP-05: Invoice and credit-note generation

**Trigger**: A successful payment (CAP-02), a mid-cycle lifecycle change (CAP-03), a completed renewal (CAP-04), or a refund/credit event.

**Inputs**:
- Invoice event: trigger type (initial, renewal, upgrade, downgrade-credit, refund) and transaction ID, from CAP-02/CAP-03/CAP-04.
- Transaction record: amount, date, gateway reference, from CAP-02.
- Customer details: name, email, billing address, from the account system.
- Subscription and proration details: plan, cycle, period dates, prorated line items, from CAP-03.

**Logic flow**:
1. Receive the event and gather transaction, customer, subscription, and proration data.
2. Assemble the invoice: sequential invoice number, customer info, itemized line items (base charge, prorated credits/charges), subtotal, tax, total.
3. Verify the total matches the transaction amount; confirm tax was applied per the configured rate.
4. Render the invoice in a printable format, store it, and associate it with the user and transaction.
5. Email the invoice to the user and publish it to the billing portal.
6. For refunds/credits, generate a credit note linked to the original invoice instead of a charge invoice.
7. **Error path**: If the transaction record is missing, generate the invoice marked "payment pending verification" and reconcile later.

**Outputs**:
- Invoice document (number, dates, line items, tax, total) stored in the invoice repository and sent to the user.
- Credit notes for refunds/downgrade credits.
- Invoice metadata record for reconciliation.
- Email notification with the invoice or a link.

**Edge cases**:
- Refund after invoicing: issue a credit note, do not alter the original invoice.
- Failed transaction: no invoice generated.
- Multiple transactions in one day for one user (upgrade + renewal): separate invoice per transaction.
- Fiscal-year numbering reset: support configurable numbering sequences.

**Connects to**: CAP-02, CAP-03, CAP-04

---

### CAP-06: Payment retry and dunning

**Trigger**: A payment fails (CAP-02 returns a decline or error).

**Inputs**:
- Failed transaction: user ID, amount, decline reason, gateway reference, from CAP-02.
- Retry configuration: max attempts and retry schedule, from administrators.
- Customer contact info and notification preferences, from the account system.

**Logic flow**:
1. Receive the failed-transaction details and check the current retry count for the subscription.
2. If below the max, schedule the next retry per the configured schedule (e.g., 3, 7, 14 days) and send a payment-failed notification stating the issue and next retry date.
3. On the retry date, signal CAP-02 to charge the stored method again.
4. On success: send a payment-recovered notice and return the subscription to active.
5. On failure: increment the retry count and schedule the next attempt; escalate dunning messaging.
6. On exhaustion: send a final notice and signal CAP-03 to suspend/expire.
7. If the user updates their payment method during the window, reset the retry count and attempt immediately.
8. **Error path**: If the user removes their stored payment method, cancel pending retries and prompt them to add a new one.

**Outputs**:
- Retry schedule records (dates, statuses) in the retry/dunning system.
- Dunning notifications at each failure and at exhaustion; recovery notification on success.
- Suspension signal to CAP-03 on exhaustion.
- Updated retry count on the subscription.

**Edge cases**:
- New card also fails: schedule continues; count does not reset unless configured to.
- Gateway down at retry time: reschedule ~24 hours later.
- Admin-triggered manual retry: allowed, resets the counter.
- Subscription cancelled during the retry window: cancel remaining retries.

**Connects to**: CAP-02, CAP-03

---

### CAP-07: Self-service billing portal

**Trigger**: An authenticated user opens the billing/account area.

**Inputs**:
- User identity and current subscription state, from the account system and CAP-03.
- Invoice history, from CAP-05.
- Stored payment methods, from the payment gateway.

**Logic flow**:
1. Display current plan, billing cycle, status, next billing date, and amount.
2. Offer actions: change plan/cycle (→ CAP-01), update or remove payment method, cancel or reactivate (→ CAP-03), retry a failed payment (→ CAP-06).
3. Show invoice and credit-note history with download links (from CAP-05).
4. Surface any past-due or dunning state with a clear call to action to fix payment.
5. Persist payment-method changes via the gateway and, if a payment is currently failing, trigger an immediate retry (CAP-06).
6. **Error path**: If the gateway tokenization fails when saving a new method, keep the old method and show an error.

**Outputs**:
- Action signals routed to CAP-01, CAP-03, CAP-06.
- Updated payment-method token stored via the gateway.
- A consolidated view of subscription, billing, and invoices for the user.

**Edge cases**:
- User removes their only payment method while subscribed: warn that billing will fail and require adding another before next renewal.
- Concurrent changes (two browser tabs): apply last-write-wins with a confirmation re-check of current state.
- User downloads an invoice mid-refund: show the original invoice plus the linked credit note.

**Connects to**: CAP-01, CAP-03, CAP-05, CAP-06

## Dependency Map

| Capability | Depends on | Feeds into |
|-----------|-----------|------------|
| CAP-01 | CAP-03 (current state) | CAP-02, CAP-03 |
| CAP-02 | CAP-01 | CAP-03, CAP-04, CAP-05, CAP-06 |
| CAP-03 | CAP-01, CAP-02 | CAP-02, CAP-04, CAP-05 |
| CAP-04 | CAP-03 | CAP-02, CAP-03, CAP-05 |
| CAP-05 | CAP-02, CAP-03, CAP-04 | CAP-07 |
| CAP-06 | CAP-02 | CAP-02, CAP-03 |
| CAP-07 | CAP-03, CAP-05 | CAP-01, CAP-03, CAP-06 |

## Open Questions

Several of these reflect assumptions made because this was a non-interactive run; confirm them with the user.

- **Proration on downgrade**: Assumed downgrades take effect at period end with no immediate refund. Alternative: prorate immediately and issue account credit. Which model fits the business?
- **Yearly→monthly switches**: Assumed scheduled for end of the paid annual term (no mid-term refund). Confirm.
- **Tax handling**: Assumed a flat or externally-supplied tax rate, not full jurisdiction calculation. Is location-based tax required?
- **Trials**: Is there a free-trial period before the first charge, and does it require a payment method up front?
- **Discounts/coupons**: Assumed out of scope. Are promo codes or annual discounts (beyond plan price difference) needed?
- **Multiple subscriptions per user**: Can one account hold more than one active subscription (e.g., separate products/seats)?
- **Minimum commitment**: Is there a minimum term (especially for yearly) before cancellation is allowed?
- **Grace period and retry schedule values**: Specific days/attempts are placeholders pending the research below.

## Research Suggestions

The researcher skill is not available in this run; these are flagged for it.

- **Proration strategies for plan and cycle changes** — Need a fair, understandable model for mid-cycle upgrades, downgrades, and monthly↔yearly switches. Suggested researcher query: "Best practices for prorating SaaS subscription charges on plan upgrades, downgrades, and billing-cycle switches — how leading SaaS companies compute credits and charges."
- **Payment retry and dunning scheduling** — Need optimal retry intervals, max attempts, and dunning email cadence to maximize recovery without excess gateway cost or annoyance. Suggested researcher query: "Optimal payment retry and dunning schedules for SaaS subscriptions — intervals, max attempts, and email sequencing for failed-payment recovery."
- **Revenue recognition and invoice compliance** — Yearly billing especially raises deferred-revenue and recognition questions. Suggested researcher query: "Revenue recognition for monthly and annual SaaS subscriptions under ASC 606 — invoice timing, deferred revenue, refunds, and credit notes."
- **Tax handling for SaaS subscriptions** — Determine whether jurisdiction-based tax (VAT/GST/US sales tax) is required. Suggested researcher query: "Tax calculation requirements for SaaS subscription billing across US, EU, and other jurisdictions, and common integration approaches."

## Next Steps

1. Resolve the Open Questions (proration model, tax, trials, discounts, multi-subscription, minimum term) with the user.
2. Define the concrete plan catalog: tiers, features, and both monthly and yearly prices with the intended discount.
3. Commission the flagged researcher topics (proration, dunning, revenue recognition, tax).
4. Design the billing-portal flows for plan/cycle change, payment-method update, cancellation, and invoice access.
5. Use the librarian skill to save this document as a spec artifact.

---
*Capability breakdown produced by solution-architect skill. Use the librarian skill to persist this artifact.*
