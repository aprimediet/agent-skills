# Notification System

> Solution Architect | Depth: standard | Generated: 2026-06-09

> **Note on knowledge check (Step 0):** The librarian skill is not available in this run, so existing artifacts could not be loaded. Before building on this breakdown, an agent with librarian access should search for prior work to avoid duplication:
> - **researches** — keywords: "notification system", "transactional email deliverability", "user notification preferences", "notification batching/digest"
> - **specs** — keywords: "notification center", "email templates", "messaging/events"
> - **docs** — any existing event catalog, email-provider setup, or in-app notification UI notes
>
> Because no artifacts could be confirmed, the *Existing Knowledge* section below is omitted.

> **Note on assumptions (non-interactive run):** The opening question (channels) is documented in `opening-question.md`. It was answered with a stated assumption: a **multi-channel notification system for a typical web SaaS**, launching with **in-app notifications** and **email** (transactional + digest), SMS and mobile push deferred to a later version. All such assumptions are recorded under Open Questions.

## Problem Statement

- **Business problem**: The product generates events users care about (mentions, status changes, account/billing activity), but has no reliable way to surface them. Without a notification system, users miss time-sensitive events, engagement and retention drop, and support load rises from "I didn't know that happened." The business needs a consistent, controllable channel to drive users back into the product and to deliver mandatory transactional messages (e.g., security and billing) dependably.
- **User problem**: Users want to be told about things relevant to them — promptly, through a channel they prefer, and without being overwhelmed by noise. They need a single place to catch up on what happened (in-app), assurance that important messages reach them (email), and control over what they receive.
- **Success criteria**:
  - Transactional notifications (security, billing) are delivered to at least 99% of intended recipients within 1 minute of the triggering event.
  - In-app notifications appear in the recipient's notification center within seconds of the event.
  - Users can change their notification preferences and have changes take effect immediately, with a measurable reduction in opt-outs/unsubscribes after preference controls ship.
  - No user receives a notification on a channel they have opted out of (excluding mandatory transactional messages).

## Scope

- **In scope**: Event intake from the application, recipient resolution, per-user notification preferences, in-app notification delivery and read-state, transactional and digest email delivery, message templating/personalization, delivery tracking and retry for email, and notification history.
- **Out of scope (v1)**: SMS and mobile/web push (design leaves room to add them), marketing campaign management and segmentation, real-time chat/messaging between users, localization beyond a single language, A/B testing of notification copy, and an analytics dashboard (basic delivery logging only).
- **Existing systems**: User account/identity system (recipient records, contact details, roles), the application services that emit events, an email delivery provider, and the product's web frontend (which renders the in-app notification center).

## Capabilities

### CAP-01: Event intake and normalization

**Trigger**: An application service reports that a notification-worthy event has occurred (e.g., "user was mentioned", "invoice paid", "password changed").

**Inputs**:
- Event signal: an event type identifier plus a payload of event-specific data (actor, subject, related entity, timestamp), provided by the emitting application service.
- Event catalog: the set of recognized event types and the data each is expected to carry, defined by system administrators.

**Logic flow**:
1. System receives an incoming event signal.
2. System validates that the event type is recognized and that the payload contains the required fields for that type.
3. System normalizes the event into a standard internal notification request: event type, originating actor, intended subject/recipient hints, and contextual data.
4. System determines the notification category (transactional vs. informational) from the event catalog — this affects whether recipient opt-out applies later.
5. System hands the normalized request to recipient resolution (CAP-02).
6. **Error path**: If the event type is unknown or required fields are missing, system rejects the event, logs the rejection with the reason, and does not produce a notification.

**Outputs**:
- Normalized notification request: a standardized record describing what happened and its category, passed to CAP-02.
- Rejection log entry: for invalid or unrecognized events, stored for troubleshooting.

**Edge cases**:
- A duplicate event arrives (same event re-reported): system deduplicates using an event identity so the user is not notified twice.
- An event references an entity that no longer exists (e.g., a deleted comment): system records the event but flags it so downstream steps can decide whether the notification is still meaningful.
- A burst of identical events for the same recipient in a short window (e.g., 50 mentions): system marks them as candidates for grouping by the batching capability (CAP-06).

**Connects to**: CAP-02, CAP-06

---

### CAP-02: Recipient resolution and preference check

**Trigger**: A normalized notification request is produced by event intake (CAP-01).

**Inputs**:
- Normalized notification request: the event and its category, provided by CAP-01.
- Recipient records: user accounts, their contact details (email), and account status, provided by the user account system.
- Notification preferences: each user's per-event-type and per-channel opt-in/opt-out settings and digest preferences, provided by the preference management capability (CAP-03).

**Logic flow**:
1. System resolves the event into one or more concrete recipients (e.g., the mentioned user, the account owner, all members of a workspace).
2. For each recipient, system looks up their notification preferences for this event type.
3. System determines the eligible channels per recipient: for transactional/mandatory categories, channels cannot be fully suppressed; for informational categories, opted-out channels are excluded.
4. System checks recipient status — suspended, deactivated, or unverified-email recipients are filtered or restricted accordingly.
5. System produces a per-recipient, per-channel delivery plan (e.g., "User A: in-app now + email immediately"; "User B: in-app now + email rolled into daily digest").
6. If a recipient has opted into digest delivery for this event type, system routes the email portion to the batching capability (CAP-06) instead of immediate send.
7. **Error path**: If a recipient has no valid channel (e.g., opted out of all informational channels), system records that no notification was sent and why.

**Outputs**:
- Delivery plan: a set of per-recipient, per-channel send instructions, passed to in-app delivery (CAP-04), email delivery (CAP-05), or batching (CAP-06).
- Suppression log: records of recipients deliberately not notified and the reason (opt-out, ineligible status).

**Edge cases**:
- The event has a very large recipient set (e.g., workspace-wide announcement): system handles fan-out without dropping recipients.
- A recipient's email is unverified: in-app is still delivered, but email is held until verification.
- A recipient is both directly mentioned and a member of a notified group: system collapses to a single notification rather than two.

**Connects to**: CAP-01, CAP-03, CAP-04, CAP-05, CAP-06

---

### CAP-03: Notification preference management

**Trigger**: A user opens their notification settings, or the system needs default preferences for a newly created account.

**Inputs**:
- Preference change request: the user's desired settings per event type and per channel (in-app on/off, email immediate/digest/off), provided by the user via a settings interface.
- Default preference policy: the out-of-the-box defaults for each event type and channel, defined by system administrators.
- Event catalog: the list of event types that can be configured, provided by CAP-01's catalog.

**Logic flow**:
1. On account creation, system seeds the user's preferences from the default policy.
2. When the user opens settings, system displays each configurable event type grouped by category, with current per-channel settings.
3. System makes clear which categories are mandatory (transactional) and cannot be fully disabled, allowing only channel choice within them where applicable.
4. User changes one or more settings and saves.
5. System validates the change (e.g., the user cannot disable a legally/operationally required transactional message) and persists the updated preferences.
6. System makes updated preferences immediately effective for subsequent notifications.
7. System honors a global unsubscribe action from an email footer link by setting all informational email channels to off.
8. **Error path**: If a save fails, system retains the prior settings and informs the user the change did not apply.

**Outputs**:
- Updated preference record: per-user, per-event-type, per-channel settings, stored in the preference store and read by CAP-02.
- Confirmation: a message to the user that preferences were saved.

**Edge cases**:
- A new event type is introduced after the user set their preferences: system applies the default for that type until the user customizes it.
- The user disables everything: mandatory transactional messages still send; system communicates this clearly.
- Conflicting rapid changes (user toggles repeatedly): system applies the last saved state.

**Connects to**: CAP-02

---

### CAP-04: In-app notification delivery

**Trigger**: A delivery plan from recipient resolution (CAP-02) includes an in-app channel instruction for a recipient.

**Inputs**:
- In-app send instruction: recipient ID, rendered notification content reference, event metadata, provided by CAP-02 and templating (CAP-07).
- Recipient session/connection state: whether the recipient is currently active in the product, provided by the web frontend.

**Logic flow**:
1. System creates an in-app notification record for the recipient with content, source event, timestamp, and unread status.
2. System makes the notification available in the recipient's notification center (bell icon), updating the unread count.
3. If the recipient is currently active, system surfaces the notification promptly (e.g., a live indicator/toast) without requiring a page reload.
4. When the recipient views the notification center, system marks displayed notifications as seen; when the recipient opens a specific notification, system marks it read and updates the unread count.
5. System supports a "mark all as read" action and removal/dismissal of individual notifications.
6. **Error path**: If the notification content reference cannot be resolved, system stores a minimal fallback ("An update occurred") so the recipient is still informed.

**Outputs**:
- In-app notification record: stored per recipient with read-state, surfaced in the notification center.
- Unread count update: reflected in the UI.
- Read-state updates: persisted when the recipient interacts.

**Edge cases**:
- The referenced entity is deleted before the user opens the notification: system shows the notification but indicates the target is no longer available.
- The recipient has thousands of unread notifications: system caps the displayed list and the count display (e.g., "99+") and supports pagination/history (CAP-08).
- The same logical event would create near-duplicate in-app entries: system collapses them (see CAP-06 grouping).

**Connects to**: CAP-02, CAP-06, CAP-07, CAP-08

---

### CAP-05: Email notification delivery

**Trigger**: A delivery plan from recipient resolution (CAP-02) includes an immediate email instruction, or the batching capability (CAP-06) releases a digest email.

**Inputs**:
- Email send instruction: recipient email address, subject, rendered email body, event metadata, provided by CAP-02/CAP-06 and templating (CAP-07).
- Sender configuration: from-address, reply-to, and footer/unsubscribe link policy, defined by system administrators.

**Logic flow**:
1. System assembles the email message from the rendered content and sender configuration, including a one-click unsubscribe link for informational emails.
2. System submits the message to the email delivery provider.
3. System records the send attempt with a unique reference and an initial status of "submitted".
4. System listens for delivery outcome signals (delivered, bounced, deferred, complaint) and updates the message status accordingly via delivery tracking (CAP-09).
5. If a soft failure (temporary/deferred) occurs, system schedules a retry per the retry policy; if a hard bounce occurs, system marks the address as undeliverable and stops retrying.
6. On repeated hard bounces or a spam complaint, system flags the recipient's email channel as suppressed and notifies preference management (CAP-03) to reflect the suppression.
7. **Error path**: If the email provider is unreachable, system queues the message and retries with backoff rather than dropping it.

**Outputs**:
- Outbound email: delivered to the recipient via the email provider.
- Send record: status-tracked message log, passed to CAP-09.
- Suppression signal: when an address is undeliverable or complains, communicated to CAP-03.

**Edge cases**:
- Recipient email is invalid/malformed: system fails fast and logs without attempting send.
- Provider accepts the message but it later bounces: status is updated asynchronously via CAP-09, not assumed delivered at submission.
- A transactional email must send even though the user opted out of informational email: system still sends it (mandatory category) and omits the unsubscribe link.

**Connects to**: CAP-02, CAP-03, CAP-06, CAP-07, CAP-09

---

### CAP-06: Batching and digest

**Trigger**: Recipient resolution (CAP-02) routes a notification to digest, or a scheduled digest window (e.g., hourly/daily) is reached, or event intake (CAP-01) flags a burst of similar events for grouping.

**Inputs**:
- Digest-bound notifications: individual notification items queued for a recipient, provided by CAP-02.
- Digest schedule and grouping rules: digest frequency per recipient and rules for collapsing similar events, defined by preferences (CAP-03) and administrators.

**Logic flow**:
1. System accumulates digest-bound notification items per recipient in a pending collection.
2. System groups similar items (e.g., "5 people mentioned you") to reduce noise, per grouping rules.
3. When the recipient's digest window arrives, system checks whether any pending items exist.
4. If items exist, system composes a single digest payload summarizing them and routes it to email delivery (CAP-05) and/or in-app (CAP-04) as a grouped entry.
5. If no items are pending at the window, system sends nothing (no empty digests).
6. After sending, system clears the pending collection for that recipient and window.
7. **Error path**: If composition fails, system retains the pending items for the next window rather than discarding them.

**Outputs**:
- Digest message: a single grouped notification, passed to CAP-04 and/or CAP-05.
- Grouped in-app entry: a collapsed notification record where applicable.
- Cleared pending state: after successful send.

**Edge cases**:
- An urgent transactional event arrives for a user on digest: it bypasses batching and sends immediately (transactional is never digested).
- A user changes digest frequency mid-window: system applies the change to the next window and does not lose pending items.
- A pending item's underlying entity is deleted before the digest sends: system omits or annotates it.

**Connects to**: CAP-01, CAP-02, CAP-04, CAP-05

---

### CAP-07: Templating and personalization

**Trigger**: A notification needs rendered content for a specific channel before delivery (invoked by CAP-02/CAP-04/CAP-05/CAP-06).

**Inputs**:
- Template definition: per-event-type, per-channel content templates with placeholders, defined by system administrators.
- Notification data: the event payload and recipient details needed to fill placeholders, provided by CAP-01 and the user account system.

**Logic flow**:
1. System selects the template matching the event type and target channel (in-app short form vs. email long form).
2. System fills placeholders with personalized data (recipient name, actor, entity title, links).
3. System produces channel-appropriate rendered content (a structured in-app payload, an email subject + body).
4. System applies safe handling of user-supplied content within templates to avoid malformed or unsafe output.
5. System returns the rendered content to the requesting delivery capability.
6. **Error path**: If a template is missing or a required placeholder has no data, system falls back to a generic safe template and logs the gap.

**Outputs**:
- Rendered notification content: per channel, returned to CAP-04/CAP-05/CAP-06.
- Template gap log: records of missing templates or data for administrators to fix.

**Edge cases**:
- A template references a field absent from a particular event instance: system shows a sensible default rather than a blank or broken placeholder.
- Recipient's display name is empty: system uses a neutral fallback ("there").
- The same event renders differently per channel: system maintains separate templates and keeps them consistent in meaning.

**Connects to**: CAP-02, CAP-04, CAP-05, CAP-06

---

### CAP-08: Notification history and read-state

**Trigger**: A recipient opens their notification center or requests their notification history; or the system performs scheduled retention housekeeping.

**Inputs**:
- Notification records: the recipient's in-app notifications with status and timestamps, provided by CAP-04.
- Retention policy: how long notifications are kept before archival/removal, defined by administrators.

**Logic flow**:
1. System retrieves the recipient's notifications ordered most-recent-first, separating unread from read.
2. System supports paging through older notifications and filtering (e.g., by category).
3. System reflects read/unread state changes performed in CAP-04.
4. On a schedule, system archives or removes notifications older than the retention window.
5. **Error path**: If history retrieval fails, system still shows the most recent unread items so the user is not left blind.

**Outputs**:
- Notification history view: a paginated, filterable list for the recipient.
- Retention actions: archived/removed older notifications per policy.

**Edge cases**:
- A user with a very long history: system pages efficiently and never loads everything at once.
- Retention removes a notification the user had bookmarked mentally: system communicates the retention policy so expectations are set.
- Read-state must stay consistent across multiple open sessions/devices: system reflects the latest state.

**Connects to**: CAP-04

---

### CAP-09: Delivery tracking and retry

**Trigger**: Email delivery (CAP-05) submits a message, or the email provider reports an asynchronous delivery outcome (delivered, bounced, deferred, complaint).

**Inputs**:
- Send records: submitted email messages with their references, provided by CAP-05.
- Provider outcome signals: delivery/bounce/complaint notifications, provided by the email delivery provider.
- Retry policy: max attempts and intervals for soft failures, defined by administrators.

**Logic flow**:
1. System records each message's lifecycle status from submission onward.
2. On a "delivered" signal, system marks the message delivered.
3. On a "deferred/soft-fail" signal, system schedules a retry per policy until success or max attempts.
4. On a "hard bounce" signal, system marks the address undeliverable, stops retries, and signals CAP-05/CAP-03 to suppress the channel for that recipient.
5. On a "complaint" (spam) signal, system suppresses the recipient's informational email and records the complaint.
6. System exposes delivery status so support/admins can answer "did this notification reach the user?".
7. **Error path**: If outcome signals are delayed or lost, messages remain in "submitted/unknown" status with a timeout that triggers a status reconciliation check.

**Outputs**:
- Delivery status log: per-message status history, available to administrators/support.
- Retry schedule: pending retries for soft failures.
- Suppression signals: undeliverable/complaint outcomes communicated to CAP-05 and CAP-03.

**Edge cases**:
- A retry succeeds after several soft failures: status reflects eventual delivery.
- Provider sends a duplicate outcome signal: system deduplicates so status isn't toggled incorrectly.
- A transactional message hard-bounces (e.g., the only email on file is dead): system raises an operational alert because the user cannot be reached.

**Connects to**: CAP-03, CAP-05

## Dependency Map

| Capability | Depends on | Feeds into |
|-----------|-----------|------------|
| CAP-01 Event intake | — | CAP-02, CAP-06 |
| CAP-02 Recipient resolution | CAP-01, CAP-03 | CAP-04, CAP-05, CAP-06 |
| CAP-03 Preference management | — | CAP-02 |
| CAP-04 In-app delivery | CAP-02, CAP-07 | CAP-06, CAP-08 |
| CAP-05 Email delivery | CAP-02, CAP-07 | CAP-03, CAP-09 |
| CAP-06 Batching/digest | CAP-01, CAP-02 | CAP-04, CAP-05 |
| CAP-07 Templating | CAP-01 | CAP-04, CAP-05, CAP-06 |
| CAP-08 History/read-state | CAP-04 | — |
| CAP-09 Delivery tracking/retry | CAP-05 | CAP-03, CAP-05 |

## Open Questions

These include the assumptions made for this non-interactive run, which should be confirmed with the user before building.

- **Channels (assumed):** This breakdown assumes **in-app + email** for v1, with SMS and mobile/web push deferred. Confirm the actual channel set; adding push/SMS introduces device/token management and new delivery + tracking capabilities.
- **Audience (assumed):** Notifications target **end users of the SaaS product**, driven by application events. Confirm whether internal/admin/operational alerting is also in scope.
- **Mandatory vs. optional categories:** Which event types are legally/operationally mandatory (cannot be opted out of)? The transactional-vs-informational split drives CAP-02 and CAP-03 behavior.
- **Digest cadence:** What digest frequencies should be offered (hourly, daily, weekly), and what is the default?
- **Retention window:** How long are in-app notifications retained before archival/removal (CAP-08)?
- **Recipient fan-out scale:** What is the largest expected recipient set for a single event (affects CAP-02)? This determines whether high-volume fan-out is a first-class concern.
- **Real-time expectation:** Is "appears within seconds" for in-app a hard requirement, or is near-real-time acceptable? Affects whether live delivery (CAP-04 step 3) is in v1.

## Research Suggestions

The researcher skill is not available in this run; these topics are flagged for it rather than researched here.

- **Transactional email deliverability** — To meet the 99% delivery target, the team needs current best practices on sender reputation, authentication (SPF/DKIM/DMARC), bounce/complaint handling, and suppression lists. Suggested researcher query: "Transactional email deliverability best practices 2026 — sender authentication, bounce and complaint handling, suppression lists, and inbox placement for SaaS."
- **Notification preference UX patterns** — CAP-03 hinges on a preference model users actually understand. Suggested researcher query: "Effective notification preference center UX — per-event vs. per-channel granularity, defaults, digest options, and unsubscribe compliance."
- **Digest and batching strategies** — CAP-06 needs proven approaches to grouping and cadence that cut noise without burying urgent items. Suggested researcher query: "Notification batching and digest design — grouping similar events, choosing cadence, and when to bypass batching for urgent messages."
- **Anti-noise / notification fatigue** — Across CAP-02/CAP-06, how to prevent over-notification and opt-out churn. Suggested researcher query: "Reducing notification fatigue in SaaS products — frequency capping, smart bundling, and engagement-based throttling."
- **Compliance for messaging** — Unsubscribe and consent obligations (CAP-03/CAP-05). Suggested researcher query: "Email notification compliance — CAN-SPAM, GDPR, and one-click unsubscribe requirements for transactional vs. marketing/informational messages."

## Next Steps

1. Confirm the v1 channel set and audience (resolve the two assumed Open Questions) before any further design.
2. Define the event catalog: enumerate notification-worthy event types, their payloads, and their category (transactional vs. informational) — this is the backbone for CAP-01, CAP-03, and CAP-07.
3. Specify the notification preference model and defaults, including which categories are mandatory.
4. Design the in-app notification center UX (list, read-state, unread count, grouping) and the email template set.
5. Flag the listed Research Suggestions to the researcher skill, prioritizing email deliverability and preference UX.
6. Once confirmed, use the librarian skill to persist this document as a **spec** artifact.

---
*Capability breakdown produced by solution-architect skill. Use the librarian skill to persist this artifact.*
