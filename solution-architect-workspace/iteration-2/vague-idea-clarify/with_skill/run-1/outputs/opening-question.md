# Opening Clarifying Question

> Solution Architect | Step 1 anchor question

"A notification system" is broad, so before breaking it down I need one anchor on scope. The single question I would ask first:

**Which delivery channels does this notification system need to support, and is it primarily for notifying your own end users inside your product, or also for internal/operational alerts?**

(For example: in-app notifications only, in-app + email, or also SMS, push, and webhooks? And who is the audience — your app's end users, your internal team, or both?)

## Why this question first

Channels and audience are the single biggest fork in a notification system's capability breakdown. They determine:

- How many delivery-capability variants exist (each channel has its own send, formatting, and failure behavior)
- Whether user-facing preference management and consent/compliance (e.g. email unsubscribe, SMS opt-out) are in scope
- Whether an in-app notification center / read-state tracking is needed
- The complexity of routing, fan-out, and deduplication logic

Anchoring on channels + audience lets every downstream capability trace cleanly back to a concrete problem instead of guessing.

## Assumed answer for this non-interactive run

Since this run is non-interactive, I answer the question myself with a clearly-stated, reasonable assumption and proceed:

**Assumption:** This is a multi-channel notification system for a typical web SaaS product, targeting the product's own end users. The in-scope channels are **in-app** (a notification center with read/unread state) and **email**. SMS, mobile push, Slack/webhook, and internal operational alerting are treated as out of scope for this iteration but noted as likely future extensions. Notifications are triggered by application/domain events (e.g. "comment added", "invoice paid", "weekly digest") plus scheduled digests. Users can manage per-category notification preferences.

These assumptions are recorded in the Open Questions section of the capability breakdown so they can be confirmed later.
