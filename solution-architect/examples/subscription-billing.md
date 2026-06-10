# Subscription Billing System

> Solution Architect | Depth: standard | Generated: 2026-06-09

## Existing Knowledge

- [SaaS Pricing Research](../researches/2026_05_28__saas-pricing-models/index.md) — Covers tiered pricing models, competitor analysis, and willingness-to-pay data. Informs the plan definition and plan selection capabilities.

## Problem Statement

- **Business problem**: The business needs a recurring revenue stream. Without a subscription billing system, customers pay once and churn — there is no mechanism to charge periodically, manage plan changes, or handle failed payments.
- **User problem**: Customers want predictable pricing, the ability to upgrade or downgrade their plan as their needs change, and confidence that their payment information is handled securely and reliably.
- **Success criteria**: Monthly recurring revenue is collected on time for at least 95% of active subscriptions. Involuntary churn from failed payments stays below 3% of total revenue. Users can change their plan in under 30 seconds without contacting support.

## Scope

- **In scope**: Plan definition and selection, one-time payment collection at signup, recurring billing on a monthly cycle, subscription lifecycle management (upgrade, downgrade, cancel, reactivate), invoice generation, payment failure handling with retry logic
- **Out of scope**: Usage-based billing, metered billing, annual billing with discounts, multi-currency support, tax calculation (assumes flat tax rate applied uniformly), dunning letters via postal mail, credit checks
- **Existing systems**: User account management system, email notification service, payment gateway, accounting/ERP system for reconciliation

## Capabilities

### CAP-01: Plan selection

**Trigger**: A new user signs up and reaches the plan selection page, or an existing user navigates to the billing settings to change their plan.

**Inputs**:
- User account: authenticated user record with account type (new vs. existing), provided by the user account system
- Plan catalog: list of available plans with pricing, features, and billing frequency, defined by system administrators
- Current subscription (for existing users): the user's active plan and its status, provided by the subscription lifecycle system (CAP-03)

**Logic flow**:
1. System retrieves the plan catalog and displays available plans with their prices and included features
2. For new users, system shows all active plans from lowest to highest price
3. For existing users, system highlights their current plan and shows upgrade/downgrade paths to adjacent plans
4. User selects a plan and confirms their choice
5. System records the selected plan ID against the user account
6. System determines the action type: new subscription, upgrade, downgrade, or same-plan renewal
7. If the selection is an upgrade (higher price tier), system proceeds directly to payment processing (CAP-02)
8. If the selection is a downgrade (lower price tier), system schedules the change to take effect at the next billing cycle end
9. If the selection is the same plan, system notifies the user they are already on this plan
10. **Error path**: If the plan catalog is unavailable, system shows a cached copy with a notice that pricing may be outdated

**Outputs**:
- Selected plan record: user ID, plan ID, action type (new/upgrade/downgrade/same), selection timestamp, stored in the subscription management system
- Pricing summary: a confirmation display showing the selected plan, the amount to be charged, and the next billing date, shown to the user
- Flow routing signal: directs the user to payment processing (CAP-02) if payment is needed, or to a confirmation page if not

**Edge cases**:
- A plan is retired but still visible in cached data: the system should check plan active status before accepting selection
- User selects a plan that requires annual commitment but the system only supports monthly: reject and explain the limitation
- Existing user selects a downgrade but has outstanding invoices: prevent downgrade until outstanding balance is cleared

**Connects to**: CAP-02, CAP-03

---

### CAP-02: Payment processing

**Trigger**: A plan selection (CAP-01) requires payment — either an initial payment for a new subscription, an immediate charge for an upgrade, or a recurring billing cycle payment (CAP-04).

**Inputs**:
- Payment details: credit card number, expiry date, CVV, billing address, provided by the user via a payment form
- Customer information: user ID, email, name, provided by the user account system
- Amount to charge: the price of the selected plan (or prorated amount for upgrades), provided by the plan selection (CAP-01) or billing cycle (CAP-04)
- Payment gateway token (for recurring charges): a stored payment method reference token, provided by a previous successful payment in this capability

**Logic flow**:
1. System receives payment details from the user or retrieves a stored payment method reference for recurring charges
2. System prepares the charge: amount, currency, description, customer information
3. System sends the charge request to the payment gateway
4. System receives the gateway response
5. If the charge is approved, system records the transaction as successful with the gateway transaction ID
6. If the charge is declined, system records the failure with the decline reason code from the gateway
7. For successful payments, system signals the subscription lifecycle (CAP-03) to activate or continue the subscription
8. For failed payments, system triggers the payment retry capability (CAP-06)
9. **Error path**: If the payment gateway is unreachable, system retries up to 3 times with 30-second delays, then reports a temporary failure

**Outputs**:
- Transaction record: user ID, amount, currency, gateway transaction ID, status (success/declined/error), timestamp, stored in the transaction log
- Payment confirmation: success notification to the user with a receipt reference, or failure notification with the reason and next steps
- Subscription activation signal: a trigger to CAP-03 to activate the subscription upon successful payment
- Retry trigger: a signal to CAP-06 when payment fails

**Edge cases**:
- Payment is approved but the gateway confirmation is delayed: system treats the payment as pending and verifies status asynchronously
- User submits payment details for a card that is reported lost or stolen: gateway declines, system treats as a regular decline and flags for manual review
- Duplicate payment requests from the same user in rapid succession: system deduplicates based on a idempotency key to prevent double charges
- Amount to charge is zero (e.g., free trial with no payment needed): system skips payment processing entirely

**Connects to**: CAP-01, CAP-03, CAP-04, CAP-06

---

### CAP-03: Subscription lifecycle

**Trigger**: A plan selection is confirmed (CAP-01) and initial payment is processed (CAP-02), or an existing user initiates a change to their subscription, or a scheduled change takes effect at the end of a billing cycle.

**Inputs**:
- Subscription action: the type of lifecycle event (activate, upgrade, downgrade, cancel, reactivate, expire), provided by CAP-01, CAP-02, or system scheduler
- Current subscription state: the user's current plan, status (active, paused, cancelled, expired), current period start and end dates, provided by the subscription management system
- Billing cycle information: the current billing period dates and whether the subscription is in the grace period, provided by the billing cycle capability (CAP-04)

**Logic flow**:
1. System receives a lifecycle action signal
2. For activation: system sets the subscription status to active, sets the current period start date, and schedules the first billing cycle end
3. For upgrade: system immediately activates the new plan, calculates the prorated charge for the remainder of the billing period, and signals CAP-02 to process the additional charge
4. For downgrade: system notes the pending change and does not apply it until the current billing period ends
5. For cancel: system records the cancellation request, sets the subscription to cancel-at-period-end, and schedules the actual deactivation for the last day of the current billing period
6. For immediate cancellation (admin only): system deactivates the subscription immediately and calculates any refund due
7. For reactivation: system restores the subscription to active status and resets the billing cycle from the reactivation date
8. For expiration: system sets the subscription status to expired and signals the billing cycle (CAP-04) to stop billing
9. **Error path**: If a subscription action conflicts with the current state (e.g., attempting to upgrade a cancelled subscription), system rejects the action with an explanation

**Outputs**:
- Updated subscription state: the new status and period dates for the user's subscription, stored in the subscription management system
- Lifecycle notification: an event sent to the notification service (e.g., "Your plan has been upgraded to Professional")
- Billing signal: an event to CAP-04 to adjust the billing schedule or amount
- Invoice trigger: an event to CAP-05 to generate a prorated invoice for mid-cycle changes

**Edge cases**:
- User cancels and then reactivates within the same billing period: system treats this as a reactivation and preserves the original billing cycle end date
- User upgrades to a plan that costs less than their current plan (should be a downgrade): system validates that the new plan price is higher before processing an upgrade
- Admin force-cancels a user with an outstanding balance: system blocks cancellation until balance is cleared
- User requests cancellation while a downgrade is pending: system cancels the downgrade and processes the cancellation instead

**Connects to**: CAP-01, CAP-02, CAP-04, CAP-05

---

### CAP-04: Billing cycle

**Trigger**: A system scheduler runs daily to check for subscriptions that need billing.

**Inputs**:
- Due subscriptions list: all active subscriptions whose billing period end date is today or past due, generated by the scheduler querying the subscription management system
- Grace period configuration: number of days after the billing date before the subscription is suspended, defined by system administrators

**Logic flow**:
1. System scheduler runs the daily billing check
2. System queries for all active subscriptions where the current period end date is today or earlier
3. For each due subscription, system calculates the next billing amount based on the current plan price
4. System signals CAP-02 to process the recurring payment
5. If payment succeeds, system extends the subscription period by one billing cycle and updates the period end date
6. If payment fails, system starts the grace period counter — the subscription remains active but is flagged as past due
7. If the grace period expires without successful payment, system signals CAP-03 to suspend the subscription
8. **Error path**: If the scheduler fails to run (downtime on the scheduled day), the next run picks up all subscriptions that became due in the interim

**Outputs**:
- Billing request: a set of charges to process, sent to CAP-02
- Period extension: updated period end dates for successful renewals, stored in the subscription management system
- Past-due flags: subscription status updated to past-due with a grace period expiry date
- Suspension signals: notifications to CAP-03 when grace period expires
- Invoice trigger: events to CAP-05 to generate invoices for successful renewals

**Edge cases**:
- Multiple subscriptions become due on a weekend or holiday: the scheduler runs regardless; no special handling needed
- A subscription was already billed earlier in the same day (duplicate): system checks the last billing date before processing to prevent double-billing
- All subscriptions are due on the same day (end-of-month spike): the scheduler processes them sequentially; order does not matter
- A subscription's billing date falls on February 29 in a non-leap year: system uses February 28 as the billing date

**Connects to**: CAP-02, CAP-03, CAP-05

---

### CAP-05: Invoice generation

**Trigger**: A payment is successfully processed (CAP-02), a subscription lifecycle change occurs (CAP-03), or a billing cycle completes (CAP-04).

**Inputs**:
- Invoice event: the trigger type (renewal, upgrade, downgrade, initial purchase) and associated transaction ID, provided by CAP-02, CAP-03, or CAP-04
- Transaction record: the payment amount, date, and gateway reference, provided by CAP-02
- Customer details: user name, email, billing address, provided by the user account system
- Subscription details: plan name, period start and end dates, provided by CAP-03

**Logic flow**:
1. System receives an invoice generation event with the trigger type and associated data
2. System retrieves the transaction record, customer details, and subscription details
3. System assembles the invoice: invoice number (sequentially generated), customer information, plan description, billing period, itemized charges including any prorated amounts or credits
4. System calculates the total due (which should match the transaction amount) and confirms that tax has been applied
5. System generates the invoice document in a printable format
6. System stores the invoice and associates it with the user account and the transaction
7. System sends the invoice to the user via email and makes it available in the billing portal
8. **Error path**: If the transaction record cannot be found, system generates the invoice with a note that payment details are pending verification

**Outputs**:
- Invoice document: a structured invoice with number, dates, customer info, line items, total, and tax, stored in the invoice repository and sent to the user
- Invoice record: metadata about the invoice (number, user ID, transaction ID, amount, status), stored for reconciliation purposes
- Email notification: a message to the user with the invoice attached or a link to view it

**Edge cases**:
- A transaction is refunded after an invoice was generated: system issues a credit note linked to the original invoice
- User needs an invoice for a transaction that failed: no invoice is generated for failed transactions
- Multiple transactions occur in a single day for the same user (upgrade + recurring): system generates separate invoices for each transaction
- Invoice number sequence resets at the start of a fiscal year: system supports configurable numbering patterns

**Connects to**: CAP-02, CAP-03, CAP-04

---

### CAP-06: Payment retry

**Trigger**: A payment attempt fails (CAP-02 returns a decline or error response).

**Inputs**:
- Failed transaction record: user ID, amount, decline reason code, gateway transaction ID (if available), provided by CAP-02
- Retry configuration: maximum retry attempts, retry schedule (intervals between retries), provided by system administrators
- Customer contact information: user email and notification preferences, provided by the user account system

**Logic flow**:
1. System receives the failed transaction details from CAP-02
2. System checks the retry count for this subscription — how many times has this payment been retried?
3. If the retry count is below the maximum, system schedules the next retry attempt according to the retry schedule (e.g., 3 days, 7 days, 14 days)
4. System sends a payment-failed notification to the user informing them of the issue and the next retry date
5. On the scheduled retry date, system signals CAP-02 to attempt payment again using the stored payment method
6. If the retry succeeds, system sends a payment-recovered notification and updates the subscription status back to active
7. If the retry fails, system increments the retry count and schedules the next attempt
8. If all retry attempts are exhausted, system sends a final notification to the user and signals CAP-03 to suspend the subscription
9. If the user updates their payment method during the retry period (via a billing portal action), system resets the retry count and attempts payment immediately
10. **Error path**: If the stored payment method is removed by the user during the retry period, system cancels all pending retries and notifies the user to add a new payment method

**Outputs**:
- Retry schedule: a record of scheduled retry attempts with dates and status, stored in the retry management system
- Failure notifications: email alerts sent to the user at each retry failure and at exhaustion
- Recovery notification: an email alert when a retry succeeds
- Subscription suspension signal: a trigger to CAP-03 when all retries are exhausted
- Updated retry count: the incremented retry attempt counter stored against the subscription

**Edge cases**:
- User updates their payment method to a card that also fails: the existing retry schedule continues; the retry count does not reset unless explicitly configured
- Payment gateway is down during a scheduled retry: the retry is rescheduled for 24 hours later
- User contacts support and asks for a manual retry: the system allows an authorized admin to trigger an immediate retry, resetting the retry counter
- The subscription is cancelled during the retry window: remaining retries are cancelled

**Connects to**: CAP-02, CAP-03

## Dependency Map

| Capability | Depends on | Feeds into |
|-----------|-----------|------------|
| CAP-01 | — | CAP-02, CAP-03 |
| CAP-02 | CAP-01 | CAP-03, CAP-04, CAP-05, CAP-06 |
| CAP-03 | CAP-01, CAP-02 | CAP-04, CAP-05 |
| CAP-04 | CAP-03 | CAP-02, CAP-05 |
| CAP-05 | CAP-02, CAP-03, CAP-04 | — |
| CAP-06 | CAP-02 | CAP-02, CAP-03 |

## Open Questions

- Should there be a minimum subscription period before a user can cancel? (Proposed: no minimum, but consider for annual plans)
- How should prorated credits be handled on downgrade — applied as a credit to the next billing cycle or refunded immediately?
- Should the system support multiple active subscriptions per user (e.g., a user with two separate products)?

## Research Suggestions

- **Proration strategies for subscription changes** — Need to determine the fairest and most understandable approach for prorating charges and credits on mid-cycle upgrades/downgrades. Suggested researcher query: "Best practices for prorating subscription charges on plan upgrades and downgrades — how SaaS companies handle mid-cycle billing changes."
- **Payment retry scheduling** — Need to determine the optimal retry schedule and maximum attempts to maximize recovery without excessive gateway costs. Suggested researcher query: "Payment retry best practices for SaaS subscriptions — optimal retry intervals, maximum attempts, and dunning email sequencing."
- **Revenue recognition compliance** — The invoice generation capability must comply with accounting standards. Suggested researcher query: "Revenue recognition rules for SaaS subscription billing under ASC 606 — how invoice timing and refund policies affect compliance."

## Next Steps

1. Define the plan catalog with specific pricing, features, and trial periods per tier
2. Design the billing portal user flow for plan changes, payment method updates, and invoice viewing
3. Establish the payment gateway integration contract and test the authorization, capture, and refund flows
4. Determine the tax application rules (flat rate vs. location-based) and how tax appears on invoices

---
*Capability breakdown produced by solution-architect skill. Use the librarian skill to persist this artifact.*
