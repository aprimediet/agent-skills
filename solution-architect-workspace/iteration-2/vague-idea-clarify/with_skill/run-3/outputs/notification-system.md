# Notification System

> Solution Architect | Depth: standard | Generated: 2026-06-09

> **Note on existing knowledge**: The librarian skill is not available in this run, so no prior artifacts could be loaded. Before building this further, an agent with librarian access should search for: researches on "notification systems / messaging delivery", specs related to "notification preferences" or "notification center", and any docs mentioning "email delivery", "transactional email", or "in-app notifications". This avoids duplicating prior work. (No `Existing Knowledge` section is included below because nothing was retrieved.)

## Problem Statement

- **Business problem**: The product has activity worth surfacing — collaboration events, account changes, deadlines, system alerts — but no consistent mechanism to tell users about it. Without notifications, users miss time-sensitive events, re-engagement drops, support tickets rise ("I didn't know that happened"), and the business loses a key retention and activation lever.
- **User problem**: Users cannot keep track of what is happening in the product without manually checking. They want to be informed of relevant events promptly, in a channel that suits the urgency, without being spammed, and with the ability to control what they hear about and how.
- **Success criteria**: A new product event can be wired to a user-facing notification without bespoke per-feature plumbing. In-app notifications appear within seconds of the triggering event; emails are delivered for at least 98% of valid addresses. Users can mute or re-route any notification category from a preferences screen, and those preferences are always honored. Notification volume per user stays within configured limits (no duplicate or runaway sends).

## Scope

- **In scope**: Event ingestion from the product, mapping events to notification types, per-user preference resolution, rendering notifications from templates, delivery via two channels (in-app notification center and email), read/unread and dismissal state for in-app notifications, a user-facing preferences/settings capability, delivery tracking and retry for failed sends, and basic rate limiting / deduplication.
- **Out of scope (v1)**: SMS and mobile push channels (design should remain channel-extensible), digest/batched email rollups, marketing/campaign notifications (this covers transactional/activity notifications only), localization/translation of templates, in-app real-time presence, and an admin analytics dashboard. These are candidate follow-ups, not v1 capabilities.
- **Existing systems**: User account/identity system (source of user IDs, email addresses, and account status), the product's domain features (sources of events), an email delivery provider (external sending infrastructure), and the product's web front-end (host of the in-app notification center UI).

## Capabilities

### CAP-01: Event ingestion

**Trigger**: A domain event occurs anywhere in the product (e.g., "comment added", "task assigned", "invoice paid", "password changed") and is emitted to the notification system.

**Inputs**:
- Event record: an event type identifier, the acting actor (who/what caused it), the affected resource, one or more target user IDs (intended recipients), a timestamp, and a payload of contextual data, provided by the emitting product feature.
- Event type registry: the set of recognized event types and whether each is notification-eligible, defined by system administrators / product configuration.

**Logic flow**:
1. System receives an inbound event from a product feature.
2. System validates that the event has a recognized type, a timestamp, and at least one target user.
3. System looks up whether this event type is notification-eligible; if not, it acknowledges and discards the event.
4. System normalizes the event into a standard internal shape and records that it was received (for deduplication and auditing).
5. System hands the normalized event to notification-type mapping (CAP-02).
6. **Error path**: If the event is malformed or references an unknown event type, system records it as rejected with a reason and does not propagate it; the emitter is acknowledged so it does not block.

**Outputs**:
- Normalized event: a validated, standard-shaped event with type, actor, recipients, and payload, passed to CAP-02.
- Ingestion log entry: a record that the event was received, accepted, or rejected, stored for auditing and deduplication.

**Edge cases**:
- The same event is emitted twice (e.g., a retry by the source feature): system uses an event identifier / idempotency key to recognize and drop the duplicate.
- An event targets a user ID that no longer exists: system drops that recipient and continues with any valid recipients.
- A burst of events arrives at once: system accepts them all and lets downstream rate limiting (CAP-06) govern actual sends.

**Connects to**: CAP-02

---

### CAP-02: Notification-type mapping

**Trigger**: A normalized event is received from event ingestion (CAP-01).

**Inputs**:
- Normalized event: from CAP-01.
- Notification type catalog: the mapping from event types to one or more notification types, each notification type carrying a category (e.g., "mentions", "billing", "security"), a default channel set, and a default urgency, defined by product configuration.

**Logic flow**:
1. System receives the normalized event.
2. System looks up which notification type(s) the event maps to. One event may produce more than one notification type, or none.
3. For each resulting notification type and each target recipient, system creates a candidate notification carrying the recipient, category, default channels, urgency, and the event payload needed to render content.
4. System passes each candidate notification to preference resolution (CAP-03).
5. **Error path**: If an event type has no mapping configured, system records a "no mapping" warning and drops the event without producing a notification.

**Outputs**:
- Candidate notifications: one per (recipient × notification type), each tagged with category, default channels, urgency, and render context, passed to CAP-03.
- Mapping warnings: records of unmapped event types, surfaced for configuration review.

**Edge cases**:
- An event maps to multiple notification types that would be redundant for the user: dedup is handled downstream (CAP-06), but mapping should avoid obviously overlapping types.
- A recipient is also the actor who caused the event (e.g., you commented on your own item): mapping flags self-originated candidates so preference resolution can suppress "notify me about my own actions" by default.

**Connects to**: CAP-01, CAP-03

---

### CAP-03: Preference resolution

**Trigger**: A candidate notification is produced by mapping (CAP-02).

**Inputs**:
- Candidate notification: recipient, category, default channels, urgency, from CAP-02.
- User notification preferences: per-recipient settings indicating, per category, which channels are enabled or disabled and whether the category is muted entirely, provided by the preferences capability (CAP-07).
- Recipient account status: whether the user is active, and whether their email is verified, provided by the user account system.

**Logic flow**:
1. System receives the candidate notification.
2. System loads the recipient's preferences for the notification's category (falling back to system defaults if the user has set none).
3. If the category is fully muted, system drops the candidate and records the suppression reason.
4. System computes the effective channel set: the intersection of the notification type's eligible channels and the channels the user has enabled for that category.
5. System removes channels that are unavailable for this recipient (e.g., email channel removed if the user's email is unverified or the account is deactivated).
6. If self-originated suppression applies (from CAP-02) and the user has not opted in to self-notifications, system drops the candidate.
7. If at least one channel remains, system produces a deliverable notification per remaining channel and passes them to content rendering (CAP-04). If no channel remains, system records "suppressed by preferences" and stops.
8. **Error path**: If preferences cannot be loaded, system falls back to safe system defaults (typically in-app on, email on only for high-urgency/security categories) and flags the fallback.

**Outputs**:
- Channel-resolved notifications: deliverable notification intents, one per surviving channel, passed to CAP-04.
- Suppression records: reasons a candidate was dropped (muted, no enabled channel, self-originated, unverified email), stored for auditing and user-facing "why didn't I get this" support.

**Edge cases**:
- Security/account-critical notifications (e.g., password changed, new login): system treats these as non-suppressible on at least one channel regardless of user mutes, to avoid silent account compromise.
- User has disabled all channels for a category: only the non-suppressible categories still deliver; all others are correctly dropped.
- Preference data is stale relative to a just-changed setting: system reads preferences at resolution time so the latest setting wins.

**Connects to**: CAP-02, CAP-04, CAP-07

---

### CAP-04: Content rendering

**Trigger**: A channel-resolved notification is received from preference resolution (CAP-03).

**Inputs**:
- Channel-resolved notification: recipient, channel, category, urgency, and render context (event payload), from CAP-03.
- Template catalog: per notification-type, per-channel templates with placeholders for dynamic content (actor name, resource title, action, links), defined by product configuration.
- Recipient display context: the user's name and any display preferences, from the user account system.

**Logic flow**:
1. System selects the template matching the notification type and the target channel (e.g., a compact in-app template vs. a full email template).
2. System fills the template placeholders with values from the render context and recipient display context.
3. System produces the channel-appropriate rendered payload: for in-app, a short title/body plus a link and icon; for email, a subject line and full body.
4. System attaches metadata needed for delivery and tracking (recipient address/handle, category, urgency, a unique notification ID).
5. System passes the rendered notification to the matching delivery capability — in-app delivery (CAP-05) or email delivery (CAP-06's sibling email path; see CAP-05/CAP-06 split below).
6. **Error path**: If a template is missing for a notification-type/channel pair, system falls back to a generic template and flags the gap; if even the fallback cannot render (missing required data), it records a render failure and drops that channel's send.

**Outputs**:
- Rendered notification: a fully-formed, channel-specific message with subject/title, body, links, and delivery metadata, passed to delivery (CAP-05).
- Render failure / fallback records: logged for template-coverage review.

**Edge cases**:
- Render context references a resource that was deleted between event time and render time: system renders with a graceful placeholder ("a deleted item") rather than failing.
- Template contains a link to a resource the recipient can no longer access: link is still rendered but the product enforces access at click time (out of scope for this system).
- Extremely long dynamic values (e.g., a 5,000-character comment): system truncates to a configured length with an ellipsis.

**Connects to**: CAP-03, CAP-05

---

### CAP-05: Delivery and channel dispatch

**Trigger**: A rendered notification is received from content rendering (CAP-04). (This capability handles both the in-app and email channels via a shared dispatch flow; channel-specific steps are noted.)

**Inputs**:
- Rendered notification: channel, recipient address/handle, message payload, urgency, notification ID, from CAP-04.
- Rate-limit / dedup decision: an allow/hold/drop signal for this send, provided by CAP-06.
- Channel availability state: whether the in-app store and the email provider are currently healthy, observed by the system.

**Logic flow**:
1. System consults rate limiting and deduplication (CAP-06) before sending; if the decision is "drop" (duplicate) or "hold" (rate cap reached), system defers or discards accordingly.
2. **In-app channel**: system writes the notification into the recipient's notification center store with state "unread", a timestamp, and a link; the front-end surfaces it (badge count, list entry). No external provider is involved.
3. **Email channel**: system submits the rendered email to the external email delivery provider and records the submission with the notification ID.
4. System records a delivery attempt with status (delivered/queued/failed) and the channel.
5. For email, system listens for provider delivery/bounce/complaint signals and updates the delivery record accordingly.
6. If a send fails transiently (provider unreachable, timeout), system enqueues it for retry with a backoff schedule, up to a configured maximum, then marks it permanently failed.
7. **Error path**: A hard failure (e.g., invalid email address, hard bounce) is recorded as permanently failed with a reason and is not retried; for the email channel a hard bounce also flags the address for the account system to prompt re-verification.

**Outputs**:
- In-app notification entry: a stored, unread notification in the recipient's notification center, available to CAP-08 for read/dismiss state.
- Email submission: a message handed to the email provider for delivery.
- Delivery records: per-attempt status (queued, delivered, bounced, complained, failed) with the notification ID and channel, stored for tracking and the "why didn't I get this" audit trail.
- Retry queue entries: deferred sends awaiting another attempt.
- Bounce/complaint flags: signals to the user account system for hard-bounced or complained addresses.

**Edge cases**:
- Email provider is fully down: email sends accumulate in the retry queue; in-app delivery is unaffected and continues.
- Recipient has no in-app session open: the in-app notification still persists and is shown next time they load the product.
- Repeated hard bounces for a user: system stops attempting email to that address and relies on in-app until the address is re-verified.
- A complaint (spam report): system suppresses future non-critical email to that recipient and records it.

**Connects to**: CAP-04, CAP-06, CAP-08

---

### CAP-06: Rate limiting and deduplication

**Trigger**: A notification is about to be dispatched (consulted by CAP-05 before each send), and also evaluated as notifications are produced.

**Inputs**:
- Pending/recent notification history: what has recently been sent to this recipient in this category and channel, maintained by the system.
- Rate-limit and dedup configuration: per-category and per-channel caps (e.g., max N emails per hour), a dedup window, and collapsing rules (e.g., "5 new comments" instead of 5 separate notifications), defined by administrators.

**Logic flow**:
1. System receives a send request (or a freshly produced notification) with recipient, category, channel, and a content/dedup key.
2. System checks whether an identical or near-identical notification (same dedup key) was already sent or is pending within the dedup window; if so, it returns "drop" (or collapses it into an existing pending notification).
3. System checks the recipient's recent send count for this category/channel against the configured cap.
4. If under the cap, system returns "allow". If at or over the cap, system returns "hold" and schedules the notification for later, or collapses multiple held notifications into a single summarized one where collapsing rules apply.
5. System records the decision so subsequent checks reflect it.
6. **Error path**: If the history/config cannot be read, system fails open for critical categories (always allow security alerts) and fails conservative for the rest (allow a single send, skip collapsing).

**Outputs**:
- Send decision: allow / hold / drop (with collapse target when applicable), returned to CAP-05.
- Updated send history: incremented counters and recorded dedup keys, stored for future decisions.
- Collapsed notification: a single summarized notification replacing several held ones, fed back into rendering/delivery.

**Edge cases**:
- A genuine burst of distinct, important events hits the cap: collapsing produces a digest-style single notification rather than silently dropping events.
- Security category exceeds the cap: caps are not applied to non-suppressible critical categories.
- Clock skew or a held notification that is no longer relevant (resource deleted): system discards stale held notifications at release time.

**Connects to**: CAP-05

---

### CAP-07: Notification preferences management

**Trigger**: A user opens their notification settings, or the system provisions default preferences for a newly created account.

**Inputs**:
- User identity: the authenticated user, from the account system.
- Current preferences: the user's existing per-category, per-channel settings, stored by this capability (empty for new users).
- Category and channel catalog: the set of notification categories and available channels the user is allowed to configure, defined by product configuration.

**Logic flow**:
1. On account creation, system seeds the user with default preferences (sensible defaults: in-app on for everything, email on for important categories, critical/security categories locked on).
2. When the user opens settings, system displays each category with its current per-channel toggles and indicates which are locked (non-suppressible).
3. User changes a toggle (enable/disable a channel for a category, or mute a category entirely).
4. System validates the change (cannot disable a locked critical channel) and persists the new preference.
5. System makes the updated preferences immediately available to preference resolution (CAP-03) for subsequent notifications.
6. **Error path**: If a save fails, system reports the failure to the user and leaves the prior preference intact (no partial update).

**Outputs**:
- Stored preferences: the user's current per-category, per-channel settings, read by CAP-03.
- Default preference set: created at account provisioning time.
- Confirmation to the user: visible state reflecting the saved change.

**Edge cases**:
- User attempts to disable a critical/security notification: system prevents it and explains why it is mandatory.
- New notification category is added after a user already set preferences: the new category appears with system defaults until the user customizes it.
- User disables all channels for an optional category: honored fully; that category goes silent for them.

**Connects to**: CAP-03

---

### CAP-08: In-app notification state (read / unread / dismiss)

**Trigger**: A user views their notification center, opens a notification, or dismisses one; or a new in-app notification is delivered (CAP-05).

**Inputs**:
- In-app notification entries: the recipient's stored notifications with current state, from CAP-05's store.
- User action: open the center, click a notification, mark-all-read, or dismiss/delete a notification, from the front-end.

**Logic flow**:
1. When a new in-app notification is delivered, system increments the recipient's unread count and surfaces it (badge / list).
2. When the user opens the notification center, system returns their notifications ordered most-recent-first with unread ones distinguished.
3. When the user opens or clicks a specific notification, system marks it read and decrements the unread count, then routes the user to the linked resource.
4. When the user marks all as read, system clears the unread count for all currently-unread notifications.
5. When the user dismisses/deletes a notification, system removes it from the active list (retaining a record for audit if configured).
6. **Error path**: If a state update fails, the front-end shows the last known good state and retries the update; counts reconcile on next load.

**Outputs**:
- Updated notification state: read/unread/dismissed flags and an accurate unread count, stored and reflected in the UI.
- Navigation signal: directs the user to the resource referenced by the notification when clicked.

**Edge cases**:
- The same notification is read on two devices/sessions: state converges to "read"; unread count never goes negative.
- A notification links to a resource the user can no longer access: system shows an "no longer available" message instead of a broken destination.
- Very old notifications accumulate: system applies a retention/auto-archive policy after a configured age (policy value is an open question).

**Connects to**: CAP-05

## Dependency Map

| Capability | Depends on | Feeds into |
|-----------|-----------|------------|
| CAP-01 Event ingestion | — | CAP-02 |
| CAP-02 Notification-type mapping | CAP-01 | CAP-03 |
| CAP-03 Preference resolution | CAP-02, CAP-07 | CAP-04 |
| CAP-04 Content rendering | CAP-03 | CAP-05 |
| CAP-05 Delivery and channel dispatch | CAP-04, CAP-06 | CAP-08 |
| CAP-06 Rate limiting and deduplication | — | CAP-05 |
| CAP-07 Notification preferences management | — | CAP-03 |
| CAP-08 In-app notification state | CAP-05 | — |

## Open Questions

These include the assumptions made for this non-interactive run (flagged), which should be confirmed with the user.

- **[Assumption — confirm]** Channels for v1 are in-app + email only; SMS and push are deferred. Is that the correct launch scope?
- **[Assumption — confirm]** Audience is the product's own authenticated end users (not external/anonymous recipients). Correct?
- **[Assumption — confirm]** These are transactional/activity notifications, not marketing campaigns. Are marketing/broadcast sends needed?
- Which categories should be treated as non-suppressible/critical (security and account changes assumed)? The exact list needs product sign-off.
- Should v1 include digest/batched email (e.g., a daily roundup), or is collapsing within rate limits sufficient for launch?
- What is the retention/auto-archive policy for in-app notifications (age threshold, hard delete vs. archive)?
- What are the concrete rate-limit caps per category/channel, and the dedup/collapse window durations?
- Is real-time in-app delivery (live badge update without refresh) required for v1, or is on-next-load acceptable?

## Research Suggestions

The researcher skill is not available in this run, so these topics are flagged rather than researched. Each is a ready-to-use researcher query.

- **Transactional email deliverability** — The email channel's success depends on sender reputation, authentication, bounce/complaint handling, and suppression lists; getting this wrong silently drops legitimate notifications. Suggested researcher query: "Best practices for transactional email deliverability — SPF/DKIM/DMARC, bounce and complaint handling, and suppression list management."
- **Notification rate limiting and digest strategies** — Need to define caps, collapsing, and digest behavior that prevent fatigue without dropping important events. Suggested researcher query: "How do SaaS products design notification rate limiting, deduplication, and digest batching to reduce notification fatigue while preserving important alerts?"
- **Notification preference UX patterns** — The preferences screen drives whether users stay opted in; the per-category/per-channel model needs validation. Suggested researcher query: "Proven UX patterns for notification preference centers — category vs. channel granularity, mandatory categories, and opt-out flows."
- **Channel extensibility for SMS/push** — Although deferred, v1 should not preclude adding SMS and push later. Suggested researcher query: "Architectural patterns for channel-agnostic notification systems that allow adding SMS and mobile push without reworking event ingestion and preferences."

## Next Steps

1. Confirm the flagged assumptions in Open Questions with the user (channels, audience, transactional-vs-marketing scope).
2. Define the concrete notification category list and which categories are non-suppressible/critical.
3. Define the event-type → notification-type → template mapping for the first set of product events to support at launch.
4. Set rate-limit caps, dedup windows, and the in-app retention policy.
5. Once scope is confirmed, dispatch the flagged research topics to the researcher skill, then use the librarian skill to persist this breakdown as a spec artifact.

---
*Capability breakdown produced by solution-architect skill. Use the librarian skill to persist this artifact.*
