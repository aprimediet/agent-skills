# Marketplace Platform

> Solution Architect | Depth: deep | Generated: 2026-06-09

## Existing Knowledge

- [Two-Sided Marketplace Research](../researches/2026_05_15__marketplace-trust-safety/index.md) — Covers trust-building mechanisms, escrow patterns, and dispute resolution workflows for online marketplaces. Directly informs CAP-05 (Payment & Escrow) and CAP-08 (Dispute Resolution).
- [Freelance Platform Spec](../specs/freelance-platform-requirements.md) — Defines user roles, service categories, and the booking workflow. Provides baseline scope for CAP-01, CAP-03, and CAP-04.

## Problem Statement

- **Business problem**: The business needs to launch a two-sided marketplace connecting service providers with clients. The platform must facilitate discovery, booking, payment, and post-service interactions while building trust between strangers transacting online. Without a structured platform, these transactions happen through informal channels with no guarantees for either party.
- **User problem**: Clients need to find qualified providers, understand what they offer, book their services, and pay securely with confidence that they'll get what they paid for. Providers need to showcase their work, manage bookings, get paid reliably, and build a reputation that attracts more clients.
- **Success criteria**: 70% of booked services result in a completed transaction. Average time from search to booking is under 5 minutes. Dispute rate stays below 5% of completed transactions. Provider payout satisfaction rate is above 90%. Platform achieves a minimum of 1,000 completed transactions per month within 6 months of launch.

## Scope

- **In scope**: Provider listing creation and management, search and discovery with filtering, booking and scheduling, payment processing with escrow hold, messaging between parties, review and rating system, dispute resolution, provider payouts, multi-channel notifications, user dashboards with analytics
- **Out of scope**: Background checks or credential verification of providers, insurance or guarantee products, in-person service fulfillment logistics, tax withholding and reporting, third-party calendar integrations, mobile apps (web-only for MVP), white-label marketplace for enterprise clients
- **Existing systems**: User account and authentication system, email notification service, payment gateway, cloud file storage service (for listing images and attachments)

## Capabilities

### CAP-01: Listing creation and management

**Trigger**: A registered provider navigates to the "Create Listing" page or selects "Edit" on an existing listing.

**Inputs**:
- Provider identity: authenticated provider user ID, account status, and verification level, provided by the user account system
- Listing data: title, description, category, pricing (fixed price or hourly rate with estimated duration), location (service area), available time slots, images (up to 10), and optional video URL, all provided by the provider through a form
- Existing listing data (for edits): the current published or draft listing content, provided by the listing repository

**Logic flow**:
1. System validates the provider's account is active and in good standing
2. System presents the listing form, pre-populated with existing data if editing
3. Provider enters or updates listing details — title, description, category, pricing model, location, availability, and media
4. For each image uploaded, system invokes file validation (file type, size, dimensions suitable for display)
5. System auto-generates a listing slug from the title and checks for uniqueness
6. Provider chooses to save as draft or publish
7. If published, system checks that required fields are complete (title, description, category, price, at least one image): if incomplete, system prompts the provider to fill in missing fields before publishing
8. System stores the listing with the chosen status (draft or published) and timestamps
9. For published listings, system indexes the listing for search and discovery (CAP-02)
10. **Error path**: If the slug conflicts with an existing listing, system appends a numeric suffix to ensure uniqueness

**Outputs**:
- Listing record: structured listing data with unique ID, provider ID, title, description, category, pricing, location, images, status (draft/published/suspended), and timestamps, stored in the listing repository
- Search index update: new or updated listing indexed for discovery in CAP-02
- Provider notification: confirmation that the listing was saved or published

**Edge cases**:
- Provider tries to publish more than the maximum allowed active listings: system blocks publishing and shows the limit message
- Provider account is suspended during listing editing: system prevents saving and redirects to account status page
- Listing image upload fails partway: the system saves the listing without the failed image and flags it as having incomplete media
- Provider deletes a listing that has active bookings: system prevents deletion and directs provider to cancel or complete all bookings first

**Connects to**: CAP-02, CAP-07, CAP-10

---

### CAP-02: Search and discovery

**Trigger**: A client visits the marketplace homepage, enters a search query, applies filters, or browses a category.

**Inputs**:
- Search query: free-text keywords entered by the client, provided through the search bar
- Filter parameters: category, price range (min/max), location, availability date/time, provider rating minimum, sort order (relevance, price, rating, newest), provided through filter controls
- Client context: client location (for geo-filtering), past search history (for relevance), provided by the user account system and client session
- Listing index: all published listings with their metadata and relevance scores, maintained by CAP-01

**Logic flow**:
1. Client enters a search query or navigates to a category
2. System parses the query and identifies keywords, categories, and location terms
3. System queries the listing index matching the keywords against listing titles, descriptions, and category tags
4. System applies active filters — category, price range, location proximity, availability, minimum rating
5. System calculates relevance scores for matching listings based on keyword match strength, provider rating, and listing completeness
6. System sorts results according to the selected sort order (default: relevance)
7. System returns the top results (default: 20 per page) with listing title, provider name, price, rating, location, and cover image
8. If the query returns zero results, system suggests alternative searches based on related categories or broader terms
9. System logs the search query and results for analytics
10. **Error path**: If the search index is unavailable, system falls back to a keyword match on a cached listing snapshot with reduced filter functionality

**Outputs**:
- Search results: a paginated list of listing summaries (title, provider, price, rating, location, image), displayed to the client
- Search analytics event: query terms, filter usage, result counts, and click-through data, logged for analysis
- Suggestions: alternative search terms or category recommendations when no results are found

**Edge cases**:
- Client searches for a misspelled term: system applies fuzzy matching or spell correction to find relevant results
- Client applies filters that contradict each other (e.g., price range where min > max): system ignores the invalid filter and notifies the client
- Location search with no listings within range: system expands the search radius progressively and notifies the client
- High-traffic period causes slow search response: system returns cached popular results within 200ms and loads full results asynchronously

**Connects to**: CAP-01, CAP-03

---

### CAP-03: Booking flow

**Trigger**: A client views a listing detail page and clicks "Book Now" or "Request Booking."

**Inputs**:
- Selected listing: the listing ID, provider ID, pricing model, and available time slots, provided by CAP-01
- Client identity: authenticated client user ID and account status, provided by the user account system
- Booking details: selected service date and time, duration (if hourly), any custom requirements or messages from the client, provided through a booking form
- Provider availability: the provider's current booked and blocked time slots, provided by the scheduling system

**Logic flow**:
1. Client views the listing detail page and clicks the booking action
2. System checks the provider's current availability for the requested date and time
3. If the time slot is available, system presents the booking confirmation form with a price summary
4. Client enters any special requirements and confirms the booking
5. System calculates the total price: fixed price or hourly rate × estimated duration
6. System places a temporary hold on the time slot (15-minute reservation) to prevent double-booking during checkout
7. System records a pending booking with the details and price
8. System notifies the provider that a booking request is pending their confirmation
9. If the provider confirms within the response window (default: 24 hours), the booking status changes to confirmed and CAP-04 (Payment & Escrow) is triggered
10. If the provider declines or doesn't respond, the booking expires, the time slot is released, and the client is notified
11. **Error path**: If the time slot is already booked during the confirmation flow (race condition), system informs the client and suggests adjacent available slots

**Outputs**:
- Booking record: booking ID, client ID, provider ID, listing ID, date/time, duration, price, status (pending/confirmed/declined/cancelled/completed), stored in the booking system
- Provider notification: booking request with client details and requirements, sent to the provider
- Client confirmation: booking request submitted confirmation with expected provider response timeline, shown to the client
- Time slot reservation: temporary hold on the provider's schedule, released after provider response or expiry

**Edge cases**:
- Client requests a booking for a date/time in the past: system rejects and asks for a future date
- Provider has set their availability to "not accepting new clients": the booking button is hidden and a "currently unavailable" message is shown
- Client creates multiple pending booking requests with different providers for the same time: system allows it but warns the client about scheduling conflicts
- Provider's account is suspended between booking request and confirmation: system auto-declines the booking and notifies the client

**Connects to**: CAP-01, CAP-02, CAP-04, CAP-06, CAP-09

---

### CAP-04: Payment and escrow

**Trigger**: A booking is confirmed by the provider (CAP-03), requiring the client to make payment.

**Inputs**:
- Booking confirmation: confirmed booking ID, client ID, provider ID, total price, service date, provided by CAP-03
- Payment method: client-selected payment method (card or stored payment method), provided by the client through a payment form or from their saved payment methods
- Platform fee configuration: platform commission percentage and any fixed service fees, defined by system administrators
- Escrow terms: standard release conditions (service completed, mutual confirmation or dispute window expired), defined by system administrators

**Logic flow**:
1. System receives the confirmed booking and calculates the total amount due: service price plus any platform fees
2. System prompts the client to pay: shows the full breakdown including the service price, platform fee, and total
3. Client selects or enters a payment method and authorizes the payment
4. System processes the payment through the payment gateway
5. Upon successful payment, system places the funds in escrow — the provider can see the funds are held but cannot withdraw them yet
6. System records the escrow transaction: total amount held, platform fee amount, provider payout amount (total minus fees)
7. System updates the booking status to "paid" and notifies both parties
8. If payment fails, system updates the booking status to "payment failed" and notifies the client with retry options
9. After the service is marked complete (CAP-07) and the review/ dispute window expires (default: 48 hours), system releases funds from escrow to the provider's available balance
10. **Error path**: If the payment gateway processes the charge but the system crashes before recording the escrow, the reconciliation process identifies the orphaned transaction and creates the escrow record

**Outputs**:
- Escrow transaction: records the held funds with booking ID, total amount, fees, provider payout amount, and release status (held/released/refunded), stored in the financial transactions system
- Payment confirmation: receipt sent to the client showing the amount paid and booking reference
- Held funds notification: notification to the provider that funds are held in escrow for the upcoming service
- Fund release trigger: signal to CAP-09 (Payout) when escrow conditions are met
- Booking status update: booking status changed to "paid" or "payment failed"

**Edge cases**:
- Client pays with a currency different from the provider's payout currency: system applies the platform's exchange rate and holds the converted amount
- Payment succeeds but the booking is later cancelled by the client: system initiates a refund from escrow back to the client's payment method
- Client disputes the charge with their card issuer after payment: system places the escrow on hold and triggers the dispute resolution process (CAP-08)
- Platform fee percentage changes mid-transaction: the fee structure at the time of booking is used

**Connects to**: CAP-03, CAP-05, CAP-07, CAP-08, CAP-09

---

### CAP-05: Messaging

**Trigger**: A client or provider navigates to a conversation thread, sends a message, or a system event generates an automated message.

**Inputs**:
- Sender identity: authenticated user ID and role (client or provider), provided by the user account system
- Conversation context: booking ID or listing ID that the conversation relates to, automatically associated or manually selected by the sender
- Message content: text (required), optional file attachments (images, documents), provided by the sender through a message input
- Participant list: the users participating in the conversation, derived from the booking participants or manually added

**Logic flow**:
1. System verifies the sender has permission to message the recipient — they must have an active booking, a pending booking request, or the recipient must have enabled direct messaging
2. System creates or retrieves the conversation thread between the participants
3. System saves the message with sender ID, timestamp, content, and any attachments
4. System delivers the message to the recipient — if they are currently viewing the conversation, the message appears in real time; otherwise, a notification is queued (CAP-10)
5. System updates the conversation metadata: last message timestamp, unread count for the recipient
6. System scans message content for prohibited content (contact information to bypass the platform, offensive language) and flags or blocks as appropriate
7. **Error path**: If an attachment upload fails, the message is sent without the attachment and the sender is notified of the failure

**Outputs**:
- Message record: message ID, conversation ID, sender ID, content, attachments, timestamp, stored in the messaging system
- Real-time delivery: message pushed to the recipient's active session if they are viewing the thread
- Notification event: a signal to CAP-10 to notify the recipient of a new message if they are offline
- Conversation metadata update: updated last message preview and unread count for the conversation list

**Edge cases**:
- Sender sends a message to a user they have no relationship with (no booking, no shared listing): system blocks the message with a permission error
- Recipient has blocked the sender: the message is rejected and the sender is not informed that they are blocked
- Message contains an attachment exceeding the file size limit: the message goes through but the attachment is rejected with an explanation
- Both parties send messages simultaneously: both messages are saved with their respective timestamps; ordering is determined server-side
- A provider sends a message after a booking is completed: messaging remains open for 30 days post-completion for follow-up, then becomes read-only

**Connects to**: CAP-03, CAP-07, CAP-08, CAP-10

---

### CAP-06: Review system

**Trigger**: A booking is marked as completed (manually by both parties, or automatically after a no-response window).

**Inputs**:
- Completed booking: booking ID, client ID, provider ID, service date, and completion timestamp, provided by CAP-03 or CAP-07
- Reviewer identity: authenticated user ID and role (client or provider), provided by the user account system
- Review content: star rating (1-5), written review text (optional), and category ratings (communication, quality, punctuality - optional), provided through a review form
- Review window configuration: number of days after completion that reviews can be submitted, defined by system administrators

**Logic flow**:
1. System detects a booking has been completed and starts the review window (default: 14 days)
2. System sends review invitations to both the client and the provider — each reviews the other
3. Reviewer submits their rating and optional written review
4. System stores the review and marks it as pending until both parties have submitted or the review window expires
5. If both parties submit, both reviews are published simultaneously
6. If only one party submits within the window, that review is published alone when the window expires
7. If neither party submits within the window, no reviews are published and the booking is closed
8. Published reviews are associated with the recipient's profile and affect their overall rating
9. System recalculates the recipient's average rating and total review count
10. **Error path**: If a review contains prohibited content (hate speech, personal information), system flags it for manual moderation and holds publication until reviewed

**Outputs**:
- Review record: review ID, booking ID, reviewer ID, recipient ID, rating, text, category ratings, status (pending/published/flagged/removed), stored in the review system
- Rating update: recalculated average rating and total review count for the recipient's profile, updated in the user profile system
- Review notification: notification to the recipient when a new review is published (CAP-10)
- Profile display update: updated star rating and review count shown on listing and provider profile

**Edge cases**:
- Reviewer submits a 1-star rating with no text: the review is published; the system encourages but does not require a written explanation
- Recipient claims a review is fake (booking was not completed by the reviewer): system investigates and can remove the review if the booking is found to be fraudulent
- Reviewer wants to edit or retract a review: system allows edits within 48 hours but keeps an edit history; retractions are not allowed after publication
- A user receives many reviews in a short period to artificially inflate their rating: system detects unusual patterns and flags for review
- The client and provider are the same person (self-dealing): system prevents reviews on bookings where both parties share the same verified identity

**Connects to**: CAP-03, CAP-07, CAP-10

---

### CAP-07: Dispute resolution

**Trigger**: A client or provider opens a dispute from a booking that is in "paid," "in progress," or "completed" status.

**Inputs**:
- Dispute initiator: user ID and role of the party opening the dispute, provided by the user account system
- Booking context: booking ID, parties involved, service date, price, current status, provided by CAP-03
- Dispute reason: category (service not delivered, service not as described, no-show, quality issues, refund request) and detailed description, provided by the initiator through a dispute form
- Evidence: message history (from CAP-05), booking details, payment records, any files uploaded as evidence, compiled from relevant systems

**Logic flow**:
1. Initiator opens a dispute from the booking page, selects a reason category, and provides a description
2. System immediately places the escrow funds on hold — no release or payout can occur until the dispute is resolved
3. System notifies the other party that a dispute has been opened and shares the details and evidence
4. The other party has 72 hours to respond with their perspective and any evidence
5. If both parties reach an agreement (e.g., partial refund, or full release): system applies the agreed outcome — refunds the agreed amount to the client and releases the remainder to the provider
6. If no agreement is reached within the response window, the dispute escalates to manual review by a platform mediator
7. During manual review, the mediator reviews all evidence from both sides and makes a binding decision: full refund to client, full release to provider, or partial refund with proportional release
8. The mediator's decision is applied: escrow funds are distributed accordingly, and the booking status is updated to "dispute resolved"
9. Both parties are notified of the outcome with an explanation
10. **Error path**: If the mediator does not respond within the service level agreement (48 hours), the dispute is automatically escalated to a senior mediator

**Outputs**:
- Dispute record: dispute ID, booking ID, initiator, reason, description, status (open/responded/escalated/resolved), stored in the dispute management system
- Escrow hold: the funds in escrow are frozen and cannot be released by CAP-04 or CAP-09 until resolution
- Notification to both parties: dispute opened, other party's response, mediator decision (CAP-10)
- Resolution outcome: refund and/or release instructions sent to the financial transactions system
- Booking status update: booking status updated to "dispute resolved" with the resolution summary

**Edge cases**:
- A party opens a dispute on a booking that was already refunded: system rejects the dispute as the booking is already resolved
- A party opens multiple disputes for the same booking: system detects the duplicate and redirects to the existing open dispute
- The initiating party does not respond to follow-up questions from the mediator: the mediator can make a decision based on available evidence
- The dispute involves an amount below the platform's minimum dispute threshold: system offers an automated resolution based on the evidence pattern
- One party threatens the other during the dispute process via messaging: system flags the messages and alerts the mediator

**Connects to**: CAP-03, CAP-04, CAP-05, CAP-09, CAP-10

---

### CAP-08: Provider payout

**Trigger**: Escrow funds are released (CAP-04) — either after a successful no-dispute completion, or as a result of a dispute resolution (CAP-07).

**Inputs**:
- Fund release signal: booking ID, provider ID, release amount (escrowed amount minus fees), release type (standard completion or dispute resolution), provided by CAP-04 or CAP-07
- Provider payout method: the provider's registered payout method (bank account, PayPal, or other), retrieved from the provider's account settings
- Payout schedule configuration: payout frequency (automatic daily, weekly, or manual threshold-based), defined by the provider's preference and system default

**Logic flow**:
1. System receives a fund release signal indicating funds are available for payout
2. System retrieves the provider's registered payout method and validates that it is still active and valid
3. System checks the provider's accumulated available balance (this release plus any other completed bookings awaiting payout)
4. System applies the provider's preferred payout schedule: if the schedule is automatic weekly and the payout day has not arrived, the funds remain in the available balance until the next scheduled payout
5. If the schedule is threshold-based (e.g., payout when balance exceeds $100), system checks whether the accumulated balance meets the threshold
6. If payout conditions are met, system initiates a transfer to the provider's payout method via the payment gateway
7. System records the payout transaction with amount, destination, gateway reference, and status
8. System notifies the provider of the payout with expected arrival time
9. If the payout fails (invalid account details, gateway rejection), system flags the issue and notifies the provider to update their payout method
10. **Error path**: If the payout method is invalid or expired, system holds the funds and sends repeated notifications to the provider to update their payout information

**Outputs**:
- Payout transaction: provider ID, amount, payout method, gateway reference, status (pending/completed/failed), timestamp, stored in the financial transactions system
- Available balance update: the provider's available balance is reduced by the payout amount
- Provider notification: payout confirmation with amount and expected arrival, or failure notification with resolution steps
- Accounting record: transaction logged for reconciliation and tax reporting purposes

**Edge cases**:
- Provider has not set up a payout method: system holds all funds and periodically prompts the provider to register a payout method
- Payout amount is below the minimum payout threshold (e.g., $1): system accumulates until the threshold is met
- Provider changes their payout method while a payout is in progress: the in-progress payout uses the original method; future payouts use the new method
- Payout is attempted to a bank account in a country that uses a different currency: system applies the conversion rate at the time of payout
- Multiple bookings complete and release funds simultaneously: system batches payouts to minimize transaction fees

**Connects to**: CAP-04, CAP-07

---

### CAP-09: Notification system

**Trigger**: An event occurs in any other capability that requires notifying a user (client or provider).

**Inputs**:
- Notification event: event type (booking request, payment confirmation, new message, review received, dispute opened, payout completed, etc.), target user ID, and event-specific payload, provided by any capability
- User notification preferences: channels opted in (email, in-app, push), frequency preferences (immediate or digest), provided by the user's account settings
- User contact information: email address, device tokens, retrieved from the user account system

**Logic flow**:
1. System receives a notification event with the event type, target user, and payload
2. System looks up the user's notification preferences for the given event type
3. For in-app notifications: system creates a notification record stored in the user's notification inbox, visible when the user opens the notification panel
4. For email notifications: system renders the appropriate email template with the event-specific content and queues it for delivery
5. For push notifications: system constructs the push payload and sends it to the user's registered devices
6. System deduplicates notifications: if the same event triggers multiple channels, they are sent once per channel
7. System logs the notification delivery for analytics
8. **Error path**: If an email delivery bounces, system flags the email address as invalid and falls back to in-app notification only

**Outputs**:
- In-app notification record: notification ID, user ID, type, title, body, action link, read status, timestamp, stored in the notifications system
- Email message: rendered email sent via the email delivery service
- Push notification: push payload sent to the user's registered mobile or browser devices
- Delivery log: record of which channels were used and whether delivery succeeded, logged for monitoring

**Edge cases**:
- User has opted out of all notification channels for a specific event type: no notification is sent
- User has not verified their email address: in-app and push notifications are sent; email notifications are suppressed until the email is verified
- Multiple notifications are generated in rapid succession (e.g., booking confirmed + payment processed): system batches them into a single digest if the user prefers digest mode
- User unsubscribes from all transactional emails: system should not suppress critical notifications (payment issues, dispute updates) regardless of preference

**Connects to**: CAP-01, CAP-03, CAP-04, CAP-05, CAP-06, CAP-07, CAP-08, CAP-10

---

### CAP-10: Dashboard and analytics

**Trigger**: A user (client or provider) navigates to their dashboard page, or an automated report schedule triggers.

**Inputs**:
- User identity: authenticated user ID and role (client or provider), provided by the user account system
- Dashboard view preference: the specific dashboard section the user wants to view (overview, earnings, bookings, listings, reviews), provided by the user's navigation choice
- Time range filter: predefined periods (7 days, 30 days, 90 days, custom range), provided by the user through filter controls
- Raw data sources: booking records (CAP-03), transaction records (CAP-04, CAP-08), review data (CAP-06), listing data (CAP-01), all queried from their respective systems

**Logic flow**:
1. User navigates to their dashboard and selects a view
2. System determines the user's role and tailors the dashboard accordingly
3. For providers: system queries their active listings count, pending bookings, upcoming services, available balance, total earnings (current and past periods), average rating, and recent reviews
4. For clients: system queries their active bookings, past bookings, total spent, and pending review invitations
5. System applies the user's time range filter to aggregate historical data
6. System computes summary metrics: totals, averages, percentage changes from previous periods
7. System renders the dashboard view with the aggregated data in visual format (summary cards, charts, lists)
8. If the user requests an export, system generates a CSV or PDF report of the current view
9. For automated scheduled reports: system runs on the configured schedule (weekly, monthly) and sends the report to the user's email (via CAP-09)
10. **Error path**: If a data source is unavailable (e.g., the transaction system is down), system shows cached data from the last successful load and indicates that data may be stale

**Outputs**:
- Dashboard display: aggregated metrics and data visualizations shown to the user in the browser
- Exported report: CSV or PDF file generated on demand and downloaded by the user
- Scheduled report: automated report delivered via email on a recurring schedule

**Edge cases**:
- User has no data (new account): dashboard shows empty state with guidance on next steps (create a listing, browse services)
- Provider's earnings data includes pending payouts and escrowed amounts: system clearly distinguishes between available balance, pending (escrowed), and total earned
- Data takes too long to load due to large volume: system loads summary data first, then loads detailed breakdowns asynchronously
- User requests a custom date range that includes future dates: system limits the range to today at the latest
- Multiple providers share the same account (agency model): not supported for MVP; each provider has their own dashboard

**Connects to**: CAP-01, CAP-03, CAP-04, CAP-06, CAP-08, CAP-09

## Dependency Map

| Capability | Depends on | Feeds into |
|-----------|-----------|------------|
| CAP-01 | — | CAP-02, CAP-07, CAP-10 |
| CAP-02 | CAP-01 | CAP-03 |
| CAP-03 | CAP-01, CAP-02 | CAP-04, CAP-06, CAP-09, CAP-10 |
| CAP-04 | CAP-03 | CAP-05, CAP-07, CAP-08, CAP-09, CAP-10 |
| CAP-05 | CAP-03 | CAP-07, CAP-09 |
| CAP-06 | CAP-03, CAP-07 | CAP-09, CAP-10 |
| CAP-07 | CAP-03, CAP-04, CAP-05 | CAP-04, CAP-08, CAP-09 |
| CAP-08 | CAP-04, CAP-07 | CAP-09, CAP-10 |
| CAP-09 | CAP-01, CAP-03, CAP-04, CAP-05, CAP-06, CAP-07, CAP-08, CAP-10 | — |
| CAP-10 | CAP-01, CAP-03, CAP-04, CAP-06, CAP-08 | CAP-09 |

## Open Questions

- Should the platform support hourly bookings with automatic overtime billing, or only fixed-price services for the MVP?
- What is the appropriate escrow release window after service completion — 48 hours, 72 hours, or 7 days?
- Should providers be able to set their own cancellation policy (flexible, moderate, strict), or is a single platform-wide policy better for trust and simplicity?
- How should the platform handle currency conversion fees — absorbed by the platform, passed to the client, or passed to the provider?
- What is the threshold for automated dispute resolution vs. mandatory manual review?

## Research Suggestions

- **Escrow release timing and trust** — The release window after service completion affects both client confidence and provider cash flow. Suggested researcher query: "Optimal escrow release periods for service marketplaces — balancing buyer protection with seller cash flow timing."
- **Marketplace fraud detection patterns** — Self-dealing, fake reviews, and payment fraud are common marketplace risks. Suggested researcher query: "Fraud detection patterns for two-sided online marketplaces — common attack vectors and mitigation strategies for booking, payments, and reviews."
- **Two-sided marketplace pricing and fee structures** — Platform commission rates affect liquidity, provider earnings, and client willingness to pay. Suggested researcher query: "Commission fee structures for two-sided service marketplaces — what % works for different service categories and average transaction values."
- **Review system design for fairness** — How to prevent rating inflation, retaliation reviews, and other common review system problems. Suggested researcher query: "Best practices for marketplace review systems — simultaneous disclosure, verified-purchase-only reviews, and rating inflation prevention."

## Next Steps

1. Define the MVP listing categories and service types with stakeholders to prioritize the first set of listings
2. Design the escrow and payout flows end-to-end, including the fund release timing and fee structure
3. Prototype the booking flow with a single provider-client pair to validate the time slot availability and booking confirmation workflow
4. Draft the platform terms of service covering dispute resolution, cancellation policy, and refund rules
5. Define the notification event catalog and agree on which events are in-app only vs. email vs. push for MVP

---
*Capability breakdown produced by solution-architect skill. Use the librarian skill to persist this artifact.*
