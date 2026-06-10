# Notification System

> Solution Architect | Depth: standard | Generated: 2026-06-09

## Existing Knowledge

_No librarian skill was available in this session, so no existing artifacts could be loaded. Before building this system, an agent with librarian access should check for prior work to avoid duplication:_

- **Search category `researches`** for keywords: "notification", "email deliverability", "notification preferences", "digest", "user engagement notifications".
- **Search category `specs`** for keywords: "notification", "messaging", "alerts", "notification center", "email templates".
- **Search category `docs`** for keywords: "event taxonomy", "domain events", "user preferences", "email provider", "unsubscribe / compliance".

The most useful artifacts to retrieve would be: any existing domain-event catalog (what events the app already emits), an existing user-preferences schema, and any prior email-provider or deliverability research.

## Problem Statement

- **Business problem**: The product has no systematic way to re-engage users or keep them informed when something relevant happens. Important events (a teammate comments, an invoice is paid, an account needs attention) go unseen, reducing engagement, slowing collaboration, and increasing support load from users who "didn't know." The business needs a reliable, centralized way to notify users across channels, with measurable delivery and engagement.
- **User problem**: Users want to know when something relevant to them happens, in the channel they prefer, without being spammed. They want to catch up on what they missed (a notification center), control what they receive (preferences), and trust that time-sensitive notifications actually arrive.
- **Success criteria**: At least 99% of generated notifications are delivered to at least one enabled channel within their target latency (near-real-time for in-app, within minutes for transactional email). Users can view and dismiss in-app notifications and change their preferences in under 30 seconds. Email unsubscribe / preference changes are honored on 100% of subsequent sends. Notification-driven engagement (click-through, return visits) is measurable.

## Scope

- **In scope**: Event intake from the application, routing events to recipients and channels, per-user notification preferences, in-app notification center with read/unread state, transactional email delivery, scheduled digest emails, delivery tracking, and compliance with unsubscribe/opt-out for email.
- **Out of scope** (this iteration): SMS, mobile push, Slack/webhook/third-party channels, internal operational/system alerting (e.g. on-call paging), localization of notification content beyond the product's existing language support, and end-user-authored notification rules. These are noted as likely future extensions.
- **Existing systems**: User account / identity system (recipients, contact details, account status), the application's domain events (the things that happen and should trigger notifications), an email delivery provider (external), and the product's web frontend (which renders the notification center).

## Capabilities

### CAP-01: Event intake

**Trigger**: An application or domain event occurs that may warrant notifying one or more users (e.g. "comment_added", "invoice_paid", "mention_created", "account_password_changed"), or a scheduled job emits a digest-trigger event.

**Inputs**:
- Event message: an event type, the actor who caused it, the subject/resource it concerns, a timestamp, and contextual payload data, provided by the application.
- Event taxonomy: the catalog of recognized event types and their required payload fields, defined by system administrators / product.

**Logic flow**:
1. System receives an incoming event from the application.
2. System validates the event against the known event taxonomy — recognized type and required fields present.
3. If the event type is unknown or malformed, system records it as a rejected event and does not proceed.
4. System normalizes the event into a canonical internal form (type, actor, subject, context, timestamp).
5. System deduplicates against recently received events so the same real-world occurrence reported twice produces a single notification flow.
6. System hands the validated, normalized event to routing (CAP-02).
7. **Error path**: If intake is temporarily unable to accept events, the event is held/queued so no event is silently lost.

**Outputs**:
- Normalized event record: canonical event stored for traceability and audit.
- Routing trigger: the validated event passed to CAP-02.
- Rejected-event log: malformed/unknown events recorded for diagnostics.

**Edge cases**:
- Same event delivered multiple times (duplicate) — deduplicated before routing.
- Burst of events from a bulk action (e.g. a user mentions 50 people at once) — accepted without dropping, may be flagged for batching downstream.
- Event references a resource or actor that no longer exists — routing proceeds but recipient resolution (CAP-02) handles the missing reference.

**Connects to**: CAP-02

---

### CAP-02: Recipient resolution & routing

**Trigger**: A validated event is received from event intake (CAP-01).

**Inputs**:
- Normalized event: type, actor, subject, context, provided by CAP-01.
- Recipient rules: which roles/relationships should be notified for a given event type (e.g. "notify the resource owner and anyone subscribed to the thread"), defined by product/admins.
- User directory: candidate recipient accounts, their relationship to the event subject, and account status (active/suspended), provided by the user account system.

**Logic flow**:
1. System looks up the recipient rule for the event type.
2. System resolves the rule into a concrete list of candidate recipient users.
3. System removes invalid recipients — suspended/deleted accounts, and the actor themselves where self-notification is undesirable (e.g. don't notify you of your own comment).
4. For each remaining recipient, system attaches the event for preference evaluation (CAP-03).
5. If, after resolution, there are no eligible recipients, system records the event as "no recipients" and stops.
6. **Error path**: If the user directory is unavailable, the event is held for retry rather than dropped.

**Outputs**:
- Per-recipient notification intents: one pending notification per (recipient, event) pair, passed to CAP-03.
- No-recipient log entry: recorded when an event resolves to zero recipients.

**Edge cases**:
- Recipient list is very large (fan-out / "thundering herd") — system handles many recipients per event without losing any.
- A user appears as a recipient for multiple overlapping rules on one event — deduplicated to a single notification intent.
- Actor and recipient are the same person and self-notify is off — recipient removed.

**Connects to**: CAP-01, CAP-03

---

### CAP-03: Preference & channel selection

**Trigger**: A per-recipient notification intent is produced by routing (CAP-02).

**Inputs**:
- Notification intent: the (recipient, event) pair with context, provided by CAP-02.
- User preferences: the recipient's per-category and per-channel settings (e.g. "comments: in-app yes, email no"; "digest: weekly"), and any global mute / quiet-hours setting, provided by the preference store (managed in CAP-07).
- Channel eligibility: whether the recipient has a usable address for each channel (e.g. a verified email; not unsubscribed), provided by the user account system and the email compliance state.

**Logic flow**:
1. System maps the event type to its notification category (e.g. "comment_added" → "Comments & mentions").
2. System reads the recipient's preferences for that category.
3. If the recipient has muted the category entirely (or all channels for it), system suppresses the notification and records the suppression reason.
4. For each channel enabled in preferences, system checks channel eligibility (valid address, not opted out, not in quiet hours for non-urgent items).
5. System decides per channel whether to send immediately or defer into a digest (e.g. low-priority items batched into a daily/weekly digest per CAP-06).
6. System emits one delivery instruction per selected immediate channel, and/or queues the item for digest inclusion.
7. If no channel qualifies, system records the notification as suppressed-by-preference.
8. **Error path**: If preferences cannot be loaded, system falls back to a safe default preference set (in-app on, email on for transactional/critical categories only) and flags the fallback.

**Outputs**:
- Delivery instructions: per-channel send requests routed to CAP-04 (in-app) and/or CAP-05 (email).
- Digest queue entries: items deferred for batching, routed to CAP-06.
- Suppression records: notifications intentionally not sent, with reason (muted, opted out, quiet hours).

**Edge cases**:
- A category is marked "critical/transactional" (e.g. password change, security alert) — preference mute does not suppress it; it always sends on at least one channel.
- Quiet hours overlap a time-sensitive item — urgent items override quiet hours; non-urgent ones defer.
- User has no preferences set yet (new user) — defaults apply.

**Connects to**: CAP-02, CAP-04, CAP-05, CAP-06, CAP-07

---

### CAP-04: In-app notification delivery & center

**Trigger**: A delivery instruction targeting the in-app channel is received from CAP-03, or a user opens/interacts with their notification center.

**Inputs**:
- Delivery instruction: recipient, rendered notification content (title, body, link to the relevant resource), category, timestamp, provided by CAP-03.
- User interaction: open notification center, mark item read/unread, dismiss item, mark-all-read, provided by the recipient via the frontend.

**Logic flow**:
1. On a delivery instruction, system creates an in-app notification item for the recipient in unread state.
2. System updates the recipient's unread count and makes the item available to the frontend in near-real-time.
3. When the user opens the notification center, system returns their notifications newest-first with read/unread status.
4. When the user opens or clicks an item, system marks it read and decrements the unread count.
5. When the user dismisses an item, system removes it from the active list (retaining it per retention policy).
6. System applies a retention policy — old/read notifications are aged out after a configured period.
7. **Error path**: If real-time delivery fails, the item still persists and appears on the next center load (no loss); the unread count reconciles on next fetch.

**Outputs**:
- In-app notification item: stored per recipient with read/unread state.
- Unread count: surfaced to the frontend (badge).
- Read/dismiss state changes: persisted and reflected in delivery tracking (CAP-08).

**Edge cases**:
- User has hundreds of unread items — center paginates and offers mark-all-read.
- Same notification arrives while the center is open — list updates without duplication.
- Linked resource was deleted after the notification was created — clicking shows a graceful "no longer available" state.

**Connects to**: CAP-03, CAP-08

---

### CAP-05: Email notification delivery

**Trigger**: A delivery instruction targeting the email channel is received from CAP-03, or a rendered digest is received from CAP-06.

**Inputs**:
- Delivery instruction: recipient, email address, notification category, content data, provided by CAP-03 (or CAP-06 for digests).
- Email template: the template for the category, including subject, body layout, and required unsubscribe/footer elements, defined by product/admins.
- Compliance state: the recipient's unsubscribe / opt-out status for the category, provided by CAP-07.

**Logic flow**:
1. System confirms the recipient has not opted out of this category's emails; if opted out, suppress and record reason.
2. System selects the appropriate template and renders it with the notification content, including an unsubscribe link and required footer.
3. System submits the rendered email to the external email provider for delivery.
4. System records the send attempt with a tracking reference.
5. System ingests delivery feedback from the provider (delivered, bounced, complaint/spam-report) and updates the notification's delivery status.
6. On a hard bounce or spam complaint, system updates the recipient's email eligibility/compliance state (CAP-07) so future sends are suppressed appropriately.
7. **Error path**: If the email provider is unreachable or returns a transient error, system retries with backoff up to a configured limit, then marks the notification as failed-delivery and records it.

**Outputs**:
- Outbound email: submitted to the email provider.
- Delivery status updates: delivered / bounced / complained / failed, recorded for tracking (CAP-08).
- Compliance updates: bounce/complaint-driven suppression signals to CAP-07.

**Edge cases**:
- Recipient address is invalid/unverified — do not send; flag for the user to update.
- Repeated hard bounces — address marked undeliverable; channel disabled for that user until corrected.
- Spam complaint — treated as an implicit opt-out for that category.
- Provider reports "delivered" but the item is critical — still surfaced in-app as a backup channel.

**Connects to**: CAP-03, CAP-06, CAP-07, CAP-08

---

### CAP-06: Digest batching & scheduling

**Trigger**: An item is queued for digest inclusion by CAP-03, and a scheduler fires at the configured digest cadence (e.g. daily or weekly per user preference).

**Inputs**:
- Digest queue entries: deferred notification items per recipient, provided by CAP-03.
- Digest schedule: per-user cadence and preferred send time, provided by CAP-07.
- Recipient details: name, email, timezone, provided by the user account system.

**Logic flow**:
1. System accumulates deferred items per recipient between digest runs.
2. At the scheduled time (respecting the user's timezone and chosen cadence), system gathers all pending digest items for the recipient.
3. If there are no pending items, system skips sending a digest for that recipient (no empty digests).
4. System groups items by category and orders them for readability, then composes a single digest payload.
5. System hands the composed digest to email delivery (CAP-05).
6. System clears the delivered items from the digest queue.
7. **Error path**: If a scheduled run is missed (downtime), the next run includes all still-pending items so nothing is dropped; if composition fails for one recipient, others are unaffected.

**Outputs**:
- Composed digest: a single batched notification handed to CAP-05.
- Cleared queue: digest items marked as included/sent.
- Skipped-digest record: recorded when a recipient had nothing to send.

**Edge cases**:
- A high-priority item lands in the digest queue but shouldn't wait — it is promoted to immediate send instead of waiting for the digest.
- User changes cadence mid-window — the new cadence applies to the next run.
- Extremely large digest (hundreds of items) — system caps and summarizes ("and 120 more...").

**Connects to**: CAP-03, CAP-05, CAP-07

---

### CAP-07: Notification preferences management

**Trigger**: A user opens their notification settings and changes a preference, an email unsubscribe link is clicked, or the system updates compliance state from a bounce/complaint (CAP-05).

**Inputs**:
- Preference changes: per-category and per-channel toggles, digest cadence, quiet hours, global mute, provided by the user via settings.
- Unsubscribe action: a one-click unsubscribe from an email footer link, provided by the recipient (no login required).
- Compliance signals: bounce/complaint-driven suppression updates, provided by CAP-05.

**Logic flow**:
1. System presents the user's current preferences grouped by category and channel.
2. When the user changes a setting, system validates it (e.g. at least one channel remains for critical categories, or warns that they may miss important messages) and saves it.
3. When an email unsubscribe link is used, system records the opt-out for the relevant scope (single category or all marketing-class emails) without requiring login.
4. When a compliance signal arrives from CAP-05, system updates the recipient's channel eligibility (e.g. mark email undeliverable).
5. System makes the updated preferences immediately available to CAP-03, CAP-05, and CAP-06 so the next notification honors them.
6. **Error path**: If a save fails, the prior preferences remain in effect and the user is told the change didn't apply.

**Outputs**:
- Updated preference record: stored per user and read by CAP-03/05/06.
- Opt-out / compliance state: recorded for email eligibility.
- Confirmation: feedback to the user that settings were saved (or an unsubscribe confirmation page).

**Edge cases**:
- User tries to disable every channel for a critical/transactional category — system prevents fully muting legally/operationally required messages, or clearly warns.
- Unsubscribe link from a forwarded email — opt-out applies to the original recipient, not the forwarder.
- Conflicting changes from two open sessions — last write wins, with the result shown on next load.

**Connects to**: CAP-03, CAP-05, CAP-06

---

### CAP-08: Delivery tracking & engagement

**Trigger**: Any send attempt, delivery-status update, or user engagement event (in-app read, email open/click) occurs across CAP-04 and CAP-05.

**Inputs**:
- Send/delivery events: created, delivered, bounced, failed, suppressed, provided by CAP-04 and CAP-05.
- Engagement events: in-app read/dismiss, email open/click (where trackable), provided by CAP-04 and CAP-05.

**Logic flow**:
1. System records the lifecycle of each notification: created → routed → delivered/failed/suppressed → engaged.
2. System aggregates per-event-type and per-channel metrics (delivery rate, failure rate, read/click rate, time-to-delivery).
3. System exposes a per-notification status lookup (useful for support: "did the user get this?").
4. System surfaces aggregate metrics for product/ops to evaluate against success criteria.
5. **Error path**: If a tracking event arrives for an unknown notification, system records it as orphaned for diagnostics rather than failing.

**Outputs**:
- Notification audit trail: full lifecycle per notification.
- Aggregate metrics: delivery and engagement rates by channel and category.
- Support lookup: status for an individual notification/recipient.

**Edge cases**:
- Email open/click tracking blocked by the recipient's mail client — counted as "delivered, engagement unknown" rather than "not delivered."
- Late-arriving provider feedback (hours later) — status reconciled retroactively.
- High event volume — metrics computed without slowing delivery.

**Connects to**: CAP-04, CAP-05

## Dependency Map

| Capability | Depends on | Feeds into |
|-----------|-----------|------------|
| CAP-01 Event intake | — | CAP-02 |
| CAP-02 Recipient resolution & routing | CAP-01 | CAP-03 |
| CAP-03 Preference & channel selection | CAP-02, CAP-07 | CAP-04, CAP-05, CAP-06 |
| CAP-04 In-app delivery & center | CAP-03 | CAP-08 |
| CAP-05 Email delivery | CAP-03, CAP-06, CAP-07 | CAP-07, CAP-08 |
| CAP-06 Digest batching & scheduling | CAP-03, CAP-07 | CAP-05 |
| CAP-07 Preferences management | CAP-05 (compliance) | CAP-03, CAP-05, CAP-06 |
| CAP-08 Delivery tracking & engagement | CAP-04, CAP-05 | — |

## Open Questions

_The following were assumed for this non-interactive run and should be confirmed with stakeholders before build:_

- **Channels & audience (the anchor question)**: Assumed multi-channel = **in-app + email**, targeting the product's own end users. SMS, push, Slack/webhook, and internal operational alerting are assumed out of scope this iteration. Confirm before committing.
- **Event source**: Assumed the application already emits (or can emit) domain events that intake (CAP-01) consumes. Is there an existing event taxonomy, or must one be defined?
- **Recipient rules ownership**: Who defines "who gets notified for event type X" — product config, admin UI, or hardcoded per event type?
- **Critical/transactional vs. optional categories**: Which categories may never be muted (security, billing)? This drives the CAP-03/CAP-07 override behavior and any legal requirements.
- **Digest cadence options**: Which cadences are offered (daily, weekly, off)? Is digest opt-in or opt-out by default?
- **Retention policy**: How long are in-app notifications and delivery audit trails retained?
- **Real-time expectation**: Does in-app need live push (badge updates without refresh), or is fetch-on-load acceptable for v1?

## Research Suggestions

_The researcher skill was not available in this session. The following topics are flagged for an agent with researcher access — do not treat the answers as known:_

- **Email deliverability & compliance** — Need to define how bounces, spam complaints, unsubscribe, and required footer/unsubscribe elements are handled to protect sender reputation and meet anti-spam law. Suggested researcher query: "Transactional vs. marketing email deliverability best practices and legal requirements (CAN-SPAM, GDPR, one-click unsubscribe) for a SaaS notification system."
- **Notification preference UX patterns** — Need a preference model that gives control without overwhelming users, and defines which categories cannot be muted. Suggested researcher query: "Notification preference center design patterns for SaaS — category/channel granularity, defaults, quiet hours, and which notifications must remain mandatory."
- **Digest batching & timing strategies** — Need to decide cadence options, send-time optimization, and how to balance immediacy vs. batching. Suggested researcher query: "Notification digest batching strategies — daily vs. weekly cadence, send-time optimization, and immediate-vs-batched decision rules for SaaS products."
- **Event-driven fan-out reliability** — Need to ensure no event/notification is lost under bursts or downtime, with deduplication. Suggested researcher query: "Reliable event fan-out for notification systems — at-least-once delivery, deduplication, and handling large recipient fan-out without loss (conceptual, not implementation)."

## Next Steps

1. Confirm the anchor assumptions in Open Questions (channels = in-app + email, end-user audience, out-of-scope channels) with stakeholders.
2. Inventory the application's existing domain events and define the event taxonomy that CAP-01 will validate against.
3. Define the notification category list and map each event type to a category, marking which categories are critical/non-mutable.
4. Run the flagged research topics (deliverability/compliance, preference UX) via the researcher skill before finalizing CAP-05 and CAP-07 behavior.
5. Use the librarian skill to persist this capability breakdown as a spec artifact.

---
*Capability breakdown produced by solution-architect skill. Use the librarian skill to persist this artifact.*
