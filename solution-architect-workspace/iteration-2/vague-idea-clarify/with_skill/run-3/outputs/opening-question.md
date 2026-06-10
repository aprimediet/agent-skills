# Opening Clarifying Question

> Solution Architect | Step 1 anchor question

"A notification system" can mean very different things depending on how messages reach people. To anchor the breakdown, the single most useful thing to pin down first is **scope of channels and audience**:

**Which channels does this system need to deliver through (in-app, email, SMS, push), and who is the audience — your own end users inside your product, or external recipients/customers?**

This one question disambiguates the largest fork in the design space: an in-app-only notification center is a fundamentally different capability set than a multi-channel transactional delivery platform with provider integrations, opt-in/opt-out compliance, and deliverability concerns.

---

## Assumed answer (non-interactive run)

Since this is a non-interactive run, I am answering the question myself with clearly-stated assumptions and proceeding:

> **Assumption**: This is a multi-channel notification system for a typical web SaaS product. The primary audience is the product's own authenticated end users. The launch channels are **in-app notifications** (a notification center / bell icon with unread counts) and **email**. SMS and mobile push are out of scope for the first version but the design should not preclude adding them later. Notifications are event-driven (triggered by activity in the product) plus a smaller set of system/account messages. Users can manage their notification preferences per category and per channel.

All further assumptions are recorded in the Open Questions section of the capability breakdown.
