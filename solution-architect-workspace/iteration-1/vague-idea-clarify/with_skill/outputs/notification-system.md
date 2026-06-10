# Notification System

> Solution Architect | Depth: standard | Generated: 2026-06-09

> **Note on assumptions**: The original prompt ("I want to build a notification system") was vague. The opening clarifying question — about delivery channels and product type — was self-answered for this non-interactive run with the following stated assumptions:
> - **Product context**: a typical multi-tenant web SaaS application with existing user accounts.
> - **Channels**: in-app notifications (notification center / bell icon) and transactional email, as the two launch channels. SMS and mobile/web push are treated as out of scope for now but the model is designed to accommodate them later.
> - **Primary purpose**: delivering event-driven, transactional, and informational notifications to end users (e.g., "your report is ready", "you were mentioned", "your invoice failed").
> These assumptions are flagged again in Open Questions and should be confirmed with the user before this breakdown is treated as final.

## Existing Knowledge

The librarian skill is **not available** in this run, so no existing artifacts could be loaded. Before treating this breakdown as final, an agent with librarian access should check for prior work to avoid duplication. Suggested searches:

- **Category `researches`** — keywords: "notification system", "notification channels", "email deliverability", "user notification preferences", "fan-out delivery".
- **Category `specs`** — keywords: "notifications", "messaging", "alerts", "in-app inbox", "notification preferences".
- **Category `docs`** — keywords: "event bus", "user events", "email provider", "templating", existing channel integrations already in use by the product.

The most useful artifacts to retrieve would be: any existing event/domain model (to know what events can trigger notifications), any prior decision on an email provider, and any existing user-preferences or settings model.

## Problem Statement

- **Business problem**: The product currently has no consistent way to reach users when something relevant happens. Important events (failures, completions, mentions, security alerts) go unnoticed, which drives support load, reduces engagement and retention, and creates risk when time-sensitive events (e.g., billing failures, security events) are missed. The business needs a single, reliable, reusable system that any part of the product can use to notify users — instead of each feature building its own ad-hoc emails.
- **User problem**: Users want to be kept informed about things that matter to them — without being overwhelmed by noise. They want timely alerts for important events, a place to see what they've missed (an in-app inbox), and control over what they receive and through which channel.
- **Success criteria**:
  - A new product feature can send a notification through the system without building new delivery infrastructure (reuse, not reinvention).
  - At least 99% of generated notifications are delivered to at least one channel (or recorded as a deliberate suppression based on user preference).
  - Users can view and manage their notification preferences, and preference changes take effect on the next notification.
  - In-app notifications appear in the user's notification center in near-real-time; email notifications are delivered within minutes.
  - Unsubscribe / opt-out requests are honored and auditable (compliance requirement for email).

## Scope

- **In scope**: Accepting notification-worthy events from the product; deciding who should be notified and through which channels; respecting user notification preferences and opt-outs; rendering notification content from templates; delivering via in-app and email channels; maintaining an in-app notification center (read/unread, history); recording delivery outcomes; basic batching/deduplication to control noise.
- **Out of scope** (for this iteration): SMS and push (mobile/web) channels; marketing/campaign notifications and segmentation (this system is for transactional/event-driven notifications, not marketing blasts); in-system authoring UI for non-engineers to create new templates; analytics dashboards on notification performance; localization/translation of content beyond accepting pre-translated templates; cross-org/admin broadcast tooling.
- **Existing systems**: User account/identity system (source of recipients, contact details, locale); the product's domain features that emit events (the triggers); an email delivery provider (external); the product's web frontend (renders the in-app notification center); a user settings/preferences area (hosts the preference UI).

## Capabilities

### CAP-01: Event ingestion

**Trigger**: A product feature reports that something notification-worthy has happened (a system event, e.g., "report.completed", "comment.mention", "invoice.payment_failed"). May also be triggered by a scheduled job that emits time-based events (e.g., "trial.expiring_in_3_days").

**Inputs**:
- Notification event: an event type identifier, the subject/actor, references to the affected entities, and a payload of context data, submitted by the originating product feature
- Recipient hint (optional): explicit recipient(s) the event is about, if the originating feature already knows them
- Idempotency key: a unique identifier for the event occurrence, supplied by the originating feature to prevent duplicate processing

**Logic flow**:
1. System receives a notification event from a product feature
2. System validates that the event type is a known/registered type and that required context fields are present
3. System checks the idempotency key — if this event occurrence has already been ingested, it is acknowledged and discarded as a duplicate
4. System records the event as accepted and queues it for recipient resolution (CAP-02)
5. **Error path**: If the event type is unknown or required fields are missing, the system rejects the event with a descriptive error and records the rejection for later debugging (does not silently drop it)

**Outputs**:
- Accepted event record: stored event with type, payload, timestamp, and processing status
- Resolution trigger: a signal to CAP-02 to determine recipients
- Rejection record (error path): a logged invalid-event entry for diagnostics

**Edge cases**:
- A burst of identical events arrives (e.g., a bulk operation fires 10,000 events): system relies on idempotency and downstream batching (CAP-06) to avoid flooding recipients
- An event references an entity that no longer exists (deleted between firing and processing): system marks the event as un-routable and skips it gracefully
- An event arrives for a recipient who has since been deactivated: handled in recipient resolution (CAP-02)

**Connects to**: CAP-02

---

### CAP-02: Recipient resolution

**Trigger**: An event has been accepted (CAP-01) and needs its target audience determined.

**Inputs**:
- Accepted event: event type and context payload, provided by CAP-01
- Audience rules: per-event-type rules defining who should be notified (e.g., "the entity owner", "all collaborators", "the billing admin"), defined by system configuration
- User directory: account records including active/inactive status, role, and relationships to entities, provided by the user account system

**Logic flow**:
1. System looks up the audience rule for the event type
2. System resolves the rule against the current state to produce a concrete list of recipient user IDs (e.g., expand "all collaborators on document X" into actual users)
3. System filters out recipients who are deactivated, deleted, or otherwise ineligible
4. System filters out the actor themselves when the rule says "don't notify the person who caused the event" (e.g., don't notify you that you commented)
5. System produces a per-recipient notification intent — one logical notification per recipient — and passes each to preference evaluation (CAP-03)
6. **Error path**: If the audience resolves to zero recipients, the system records the event as "no recipients" and completes without error

**Outputs**:
- Recipient list: resolved, eligible user IDs for the event
- Per-recipient notification intents: passed to CAP-03 for preference evaluation
- No-recipient record (edge): a benign completion record when nobody needs notifying

**Edge cases**:
- An audience rule is very large (e.g., notify 50,000 members of an org): resolution must produce intents that can be processed in bulk without timing out
- A recipient appears multiple times via overlapping rules: system deduplicates to one intent per recipient per event
- The actor and a legitimate recipient are the same person but via different roles: defined by the audience rule whether to include or suppress

**Connects to**: CAP-01, CAP-03

---

### CAP-03: Preference evaluation

**Trigger**: A per-recipient notification intent is produced (CAP-02).

**Inputs**:
- Notification intent: the recipient, the event type, and the context, provided by CAP-02
- User notification preferences: the recipient's per-category and per-channel settings (e.g., "mentions: in-app yes, email no"), and any global opt-out / "do not disturb" settings, provided by the preference store (CAP-07)
- Channel eligibility data: whether the recipient has the contact details required for each channel (e.g., a verified email address), provided by the user account system

**Logic flow**:
1. System maps the event type to a notification category (e.g., "mentions", "billing", "security")
2. System retrieves the recipient's preferences for that category
3. System determines, per channel, whether the recipient wants this notification on that channel
4. **Mandatory override**: For categories flagged as critical/transactional (e.g., security alerts, payment failures), the system ignores opt-outs for at least one channel so the user cannot miss legally or operationally essential messages
5. System checks channel eligibility — e.g., suppress email if the user has no verified email address
6. System produces a set of (recipient, channel) delivery decisions: which channels to actually send on
7. If no channels remain after filtering, system records a deliberate suppression (with reason) and stops — this still counts as a successful, intentional outcome
8. **Error path**: If preferences cannot be loaded, system falls back to safe defaults (deliver critical categories, suppress optional ones) and flags the failure

**Outputs**:
- Per-channel delivery decisions: the approved (recipient, channel) pairs, passed to content rendering (CAP-04)
- Suppression record: an auditable entry when a notification is intentionally not sent, with the reason (opted out / no eligible channel)

**Edge cases**:
- A user has opted out of everything but an essential security notification fires: critical-override ensures it is still delivered on at least one channel
- A user is in a "do not disturb" / snooze window: optional notifications are deferred or batched (handed to CAP-06); critical ones still go through
- Preference exists for a channel the system no longer supports: ignored safely

**Connects to**: CAP-02, CAP-04, CAP-06, CAP-07

---

### CAP-04: Content rendering

**Trigger**: A delivery decision (CAP-03) requires the notification content to be produced for one or more channels.

**Inputs**:
- Delivery decision: recipient, channel(s), event type, and context payload, provided by CAP-03
- Notification templates: per-event-type, per-channel content templates with placeholders (e.g., email subject/body, in-app message), provided by the template store
- Recipient personalization data: name, locale/timezone, and any per-user formatting needs, provided by the user account system

**Logic flow**:
1. System selects the template matching the event type, channel, and recipient locale
2. System merges the event context and personalization data into the template placeholders
3. System formats channel-appropriate output (e.g., an email needs subject + HTML/text body and an unsubscribe link; an in-app notification needs a short title, body, and a link/action target)
4. System validates that no required placeholder is left unfilled
5. System hands the rendered content to the appropriate delivery capability (CAP-05 for delivery dispatch)
6. **Error path**: If a template is missing for the channel/locale, system falls back to a default-locale template, then to a generic template; if none exists, it records a rendering failure and does not send malformed content

**Outputs**:
- Rendered notification content: channel-specific, fully populated message ready for delivery
- Rendering failure record (error path): a logged entry identifying the missing or broken template

**Edge cases**:
- Context contains user-supplied text (e.g., a comment body) that must be safely escaped to avoid broken layouts or injection in email/in-app
- A placeholder references data not present in the payload: caught by validation in step 4
- Very long content (e.g., a huge comment): system truncates with a "view more" link rather than sending oversized messages

**Connects to**: CAP-03, CAP-05

---

### CAP-05: Delivery dispatch

**Trigger**: Rendered content is ready for a specific channel (CAP-04), or a deferred/batched notification reaches its send time (CAP-06).

**Inputs**:
- Rendered notification: recipient, channel, and channel-specific content, provided by CAP-04 or CAP-06
- Channel configuration: the active delivery destination per channel (the in-app inbox for in-app; the email provider for email), defined by system configuration
- Recipient contact details: verified email address for email; user ID for in-app, provided by the user account system

**Logic flow**:
1. System routes the rendered notification to the handler for its channel
2. For **in-app**: system creates a notification record in the recipient's notification center as unread (feeds CAP-08)
3. For **email**: system submits the message to the email delivery provider and captures the provider's accept/reject response
4. System records the delivery attempt and its immediate outcome (queued / accepted / rejected)
5. For email, system listens for asynchronous delivery status (delivered, bounced, complaint) and updates the record when it arrives
6. If a delivery attempt fails transiently (e.g., provider temporarily unavailable), system retries a bounded number of times with increasing delays
7. If a hard failure occurs (e.g., a permanent bounce / invalid address), system records the failure and flags the recipient's email as needing re-verification (feeds back to CAP-07)
8. **Error path**: If all retries are exhausted on a non-critical notification, system records final failure; for a critical notification that fails on all channels, system raises an internal alert for operator attention

**Outputs**:
- In-app notification record: a new unread entry in the recipient's notification center (to CAP-08)
- Email send request: a message handed to the external email provider
- Delivery status record: per-attempt and final delivery outcome, stored in the delivery log
- Bounce/complaint signal: feedback to CAP-07 to update the recipient's channel eligibility

**Edge cases**:
- The email provider accepts the message but it later bounces: status record is updated asynchronously; the user's email may be marked invalid after repeated hard bounces
- The in-app channel write succeeds but the user is offline: notification waits in the inbox and is shown on next visit (no loss)
- A spam complaint is received: the recipient is auto-opted-out of that category and the event is logged for compliance
- Provider rate limits the system during a spike: dispatch defers and retries rather than dropping (coordinates with CAP-06)

**Connects to**: CAP-04, CAP-06, CAP-07, CAP-08

---

### CAP-06: Batching and deduplication

**Trigger**: Preference evaluation defers a notification (CAP-03), or multiple notifications of the same type accumulate for a recipient within a short window, or a recipient has opted into digest delivery.

**Inputs**:
- Deferred/poolable notification intents: notifications eligible to be grouped, provided by CAP-03
- Batching rules: per-category windows and digest schedules (e.g., "group mentions over 5 minutes", "daily digest at 8am local"), defined by system configuration
- Recipient timezone and digest preference: provided by CAP-07

**Logic flow**:
1. System holds eligible notifications in a per-recipient, per-category collection window
2. System deduplicates near-identical notifications within the window (e.g., 12 likes on the same post become "12 people liked your post")
3. When the window closes (or the scheduled digest time arrives in the recipient's timezone), system assembles the grouped content and hands it to rendering/dispatch (CAP-04 → CAP-05)
4. Critical/transactional notifications bypass batching entirely and are dispatched immediately
5. **Error path**: If the scheduler that closes windows fails, the next run flushes all overdue windows so nothing is held indefinitely

**Outputs**:
- Grouped/digest notification: a single consolidated notification representing many events, passed to CAP-04/CAP-05
- Deduplication record: which raw notifications were collapsed into the group

**Edge cases**:
- Only one notification arrives in a window: sent as a normal single notification, not a "digest of 1"
- A user changes their digest preference mid-window: the new preference applies to the next window, not the one in flight
- A grouped notification's underlying events are partially revoked (e.g., comments deleted) before send: the group is recomputed at send time to reflect current state

**Connects to**: CAP-03, CAP-04, CAP-05

---

### CAP-07: Preference and channel management

**Trigger**: A user opens their notification settings and changes a preference, clicks an unsubscribe link, or a delivery outcome (CAP-05) reports a bounce/complaint that changes channel eligibility.

**Inputs**:
- Preference change: the recipient, the category/channel, and the new setting (on/off, digest/immediate, do-not-disturb window), provided by the user via the settings UI or an unsubscribe link
- Channel eligibility update: bounce/complaint signals, provided by CAP-05
- Contact verification status: whether the user's email is verified, provided by the user account system

**Logic flow**:
1. System presents the user's current preferences organized by category and channel, with critical categories marked as non-disableable (or limited to channel choice only)
2. System records preference changes and timestamps them for audit
3. For one-click email unsubscribe, system records the opt-out without requiring login (compliance requirement) and confirms it
4. When CAP-05 reports a hard bounce or spam complaint, system updates the recipient's channel eligibility (e.g., marks email as undeliverable or auto-opts-out the category)
5. System makes the current preferences available to CAP-03 for evaluation on the next notification
6. **Error path**: If a preference write fails, the user is shown an error and the prior preference remains in effect (no silent partial update)

**Outputs**:
- Updated preference record: the recipient's current per-category, per-channel settings, stored in the preference store
- Audit entry: who changed what and when (important for unsubscribe/compliance)
- Channel eligibility update: the recipient's deliverable channels, read by CAP-03

**Edge cases**:
- A user unsubscribes from all email but the system later needs to send a critical security email: the critical-override in CAP-03 still applies (and this should be disclosed in the preferences UI)
- A user re-verifies a previously bounced email: eligibility is restored
- Conflicting preferences set from two devices nearly simultaneously: last-write-wins with the audit trail preserving both attempts

**Connects to**: CAP-03, CAP-05

---

### CAP-08: In-app notification center

**Trigger**: A user opens the in-app notification center / bell icon, or a new in-app notification is created (CAP-05), or the user marks notifications as read/dismissed.

**Inputs**:
- In-app notification records: the recipient's notifications with read/unread state, content, link target, and timestamp, provided by CAP-05 and the notification store
- User actions: open center, mark read, mark all read, dismiss, click through, performed by the user

**Logic flow**:
1. When a new in-app notification is created (CAP-05), system increments the recipient's unread count and makes it available to the frontend in near-real-time
2. When the user opens the center, system returns the most recent notifications (paginated, newest first) with their read/unread state
3. When the user clicks a notification, system marks it read and navigates to the linked entity
4. When the user marks one/all as read or dismisses, system updates the corresponding records and recalculates the unread count
5. System retains notification history for a defined retention period and then archives or purges older entries
6. **Error path**: If the notification store is briefly unavailable, the frontend shows the last-known state and retries rather than showing an error or zero

**Outputs**:
- Notification feed: the paginated list of the user's notifications with state
- Unread count: the badge number shown on the bell icon
- Updated read/dismiss state: persisted changes to notification records

**Edge cases**:
- A notification links to an entity the user can no longer access (permissions revoked): clicking shows a graceful "no longer available" message instead of an error
- A user has thousands of unread notifications: unread count is capped for display (e.g., "99+") and the feed paginates
- The same logical event produced both an email and an in-app notification: the in-app entry stands on its own; reading one does not auto-clear the other channel

**Connects to**: CAP-05

## Dependency Map

| Capability | Depends on | Feeds into |
|-----------|-----------|------------|
| CAP-01 Event ingestion | — | CAP-02 |
| CAP-02 Recipient resolution | CAP-01 | CAP-03 |
| CAP-03 Preference evaluation | CAP-02, CAP-07 | CAP-04, CAP-06 |
| CAP-04 Content rendering | CAP-03 | CAP-05 |
| CAP-05 Delivery dispatch | CAP-04, CAP-06 | CAP-07, CAP-08 |
| CAP-06 Batching and deduplication | CAP-03 | CAP-04, CAP-05 |
| CAP-07 Preference and channel management | CAP-05 | CAP-03 |
| CAP-08 In-app notification center | CAP-05 | — |

## Open Questions

- **Channel scope (assumption to confirm)**: This breakdown assumes in-app + email at launch, with SMS and push deferred. Is that the right starting set, or is one of SMS/push required for the first release?
- **Product context (assumption to confirm)**: Assumed a multi-tenant web SaaS with existing user accounts and an existing settings area. If the product is mobile-first or has no existing accounts/preferences area, several capabilities shift.
- **Critical-override categories**: Which notification categories must bypass opt-out (security, billing, legal)? This needs an explicit, agreed list — over-using the override erodes user trust and may breach anti-spam rules.
- **Retention policy**: How long are in-app notifications and delivery logs kept? Affects CAP-08 and compliance.
- **Template ownership**: Who authors and maintains templates — engineering only, or do non-engineers need an authoring path later? (Authoring UI is currently out of scope.)
- **Real-time expectation**: How "real-time" must in-app notifications be (instant push to an open page vs. visible on next page load)? This materially changes CAP-08.
- **Cross-channel coordination**: If a user reads an in-app notification, should the corresponding email be suppressed if not yet sent? Currently treated as independent per channel.

## Research Suggestions

Topics flagged for the **researcher skill** (no research was conducted in this run):

- **Notification preference and opt-out models** — Need a proven model for per-category/per-channel preferences plus a defensible critical-override policy. Suggested researcher query: "How do mature SaaS products structure user notification preferences across categories and channels, and which transactional categories legitimately bypass opt-out?"
- **Email deliverability and compliance** — Bounce/complaint handling, one-click unsubscribe, and anti-spam obligations directly shape CAP-05 and CAP-07. Suggested researcher query: "Email notification deliverability best practices and legal compliance (CAN-SPAM, GDPR, one-click unsubscribe, bounce/complaint handling) for transactional SaaS email."
- **Batching and digest strategies** — Need guidance on collapse windows and digest scheduling that reduce noise without delaying important notifications. Suggested researcher query: "Best practices for notification batching, deduplication, and digest scheduling to reduce notification fatigue in SaaS products."
- **Real-time in-app delivery patterns** — To set the right expectation for CAP-08. Suggested researcher query: "Approaches to delivering near-real-time in-app notifications to web clients and the tradeoffs between them (latency, complexity, scale)."

## Next Steps

1. Confirm the channel set and product-context assumptions above with the user before finalizing.
2. Agree on the notification **category taxonomy** and the explicit list of critical/override categories.
3. Catalog the initial set of **event types** the product needs to notify on, with their audience rules (this feeds CAP-01 and CAP-02).
4. Define the **preferences UI** structure and the email unsubscribe flow (CAP-07).
5. Hand the four research topics above to the researcher skill, then revisit CAP-03, CAP-05, and CAP-06 with the findings.

---
*Capability breakdown produced by solution-architect skill. The librarian skill was unavailable in this run — use the librarian skill to save this as a spec artifact (suggested category: specs; keywords: notification system, in-app notifications, email, preferences).*
