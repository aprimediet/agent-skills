# Digital Goods Marketplace

> Solution Architect | Depth: deep | Generated: 2026-06-09

> **Note on this run**: This breakdown was produced non-interactively. Where the skill would normally ask the user 4-5 rounds of clarifying questions, I have made reasonable, explicitly-stated assumptions. All such assumptions are collected in the **Assumptions** and **Open Questions** sections so they can be confirmed or corrected. The librarian skill was unavailable (see **Existing Knowledge**) and the researcher skill was unavailable (topics flagged in **Research Suggestions**).

## Existing Knowledge

The librarian skill is not available in this run, so I could not load or search for prior artifacts. Before building on this breakdown, an agent with librarian access should search for:

- **Category `researches`** — keywords: "digital goods marketplace", "two-sided marketplace trust & safety", "escrow / payout split", "digital delivery fraud", "license/entitlement models". These would inform CAP-06 (Payment), CAP-07 (Delivery & Entitlement), and CAP-13 (Trust, Safety & Fraud).
- **Category `specs`** — keywords: "seller onboarding", "payout / KYC", "checkout flow", "refund policy", "review system". These would establish baseline scope for CAP-01, CAP-03, CAP-09, and CAP-11.
- **Category `docs`** — keywords: "payment gateway integration", "tax / VAT on digital goods", "DMCA / takedown process". These bear on CAP-06, CAP-12, and CAP-13.

If any are found, fold their findings into the relevant capabilities and replace the assumptions noted below.

## Problem Statement

- **Business problem**: The business wants to operate a two-sided marketplace for **digital goods** (e.g., templates, e-books, design assets, audio/video, software, plugins, courses). It must attract sellers with low-friction listing and reliable payouts, attract buyers with trustworthy discovery and instant delivery, and capture revenue via commission on each sale. Without a platform, sellers resort to ad-hoc storefronts with poor discovery and buyers have no protection against bad files, fraud, or non-delivery.
- **User problem**:
  - *Buyers* need to discover quality digital goods, trust they are legitimate (not stolen/malware), purchase securely, and receive their goods instantly with durable access for re-download and updates.
  - *Sellers* need to list and price goods, upload files and manage versions/inventory, understand demand, and receive reliable, transparent payouts net of fees.
- **Success criteria**:
  - Checkout conversion (item view → completed purchase) ≥ 4%.
  - 99%+ of paid orders deliver entitlement within 60 seconds of payment capture.
  - Buyer-initiated dispute/refund rate ≤ 3% of completed orders.
  - Seller payout on-time rate ≥ 99% against the published schedule.
  - Time from seller signup to first published listing under 15 minutes (median).
  - Fraudulent/infringing listing takedown within 24 hours of a valid report.

## Scope

- **In scope**: Seller onboarding & payout setup; listing creation/management with digital file upload, versioning, and inventory limits; catalog search & discovery; cart & checkout; payment with platform commission split; instant digital delivery & durable entitlements (re-download, version updates, license keys); order management for both sides; refunds & disputes; reviews & ratings; seller payouts & ledger; buyer library; notifications; trust/safety/fraud & content moderation; admin/marketplace operations; reporting dashboards for both sides.
- **Out of scope (this iteration)**: Physical goods or shipping; subscriptions/recurring digital memberships (one-time purchases only for MVP); affiliate/referral programs; native mobile apps (web-only); seller-to-seller transactions; in-platform escrow holding beyond the standard refund window; DRM enforcement on downloaded files beyond watermarking/license keys; full tax filing/remittance automation (capture tax data only — see Open Questions).
- **Existing systems (assumed available)**: User account & authentication system; email/notification delivery service; payment gateway with marketplace/split-payment support; cloud object storage for digital files; CDN for delivery.

## Assumptions

These stand in for answers the skill would normally elicit interactively:

1. **Goods are digital only**, delivered as downloadable files and/or license keys; no physical fulfillment or shipping.
2. **One-time purchases only** for MVP (no subscriptions/rentals).
3. **Inventory** can be (a) unlimited (infinite digital copies), or (b) limited — a fixed pool of unique license keys / serialized assets that can sell out. Both are supported.
4. **Commission model**: platform takes a percentage commission per sale; sellers receive net proceeds. Exact rate is a business decision (Open Questions).
5. **Payouts** go to sellers on a schedule after a clearing/refund-hold window; the platform is the merchant of record for buyers and splits funds to sellers.
6. **Web-only** for MVP; single currency at launch with multi-currency flagged for research.
7. **Refund window** is fixed platform-wide (e.g., 14 days) for MVP; per-seller policies are an Open Question.

## Capabilities

### CAP-01: Seller onboarding and payout account setup

**Trigger**: A registered user selects "Become a seller" / "Start selling," or an existing seller opens payout settings.

**Inputs**:
- User identity: authenticated user ID and account status, from the user account system.
- Seller profile data: display/store name, bio, logo/banner, support contact, country of operation, entered by the user.
- Payout & identity data: payout method (bank account, PayPal, or equivalent), tax/identity details required for payouts (KYC), entered by the user and verified by the payment gateway/identity provider.

**Logic flow**:
1. System confirms the user account is active and eligible to sell (not banned/restricted).
2. System collects the seller profile and creates a seller account in "unverified" status.
3. System initiates payout/KYC onboarding with the payment provider; collects identity and bank/payout details.
4. System tracks verification state returned by the provider (pending, verified, rejected, more-info-needed).
5. Until payout verification succeeds, the seller may create draft listings but cannot publish or receive payouts (configurable — see Open Questions).
6. On verification success, system marks the seller "active" and enables publishing and payouts.
7. **Error path**: If KYC is rejected, system records the reason, notifies the seller (CAP-14), and surfaces remediation steps; the seller remains in restricted state.

**Outputs**:
- Seller account record: seller ID, store profile, status (unverified/active/restricted/suspended), linked to the user account.
- Payout account linkage: reference to the verified payout/KYC profile held by the payment provider.
- Status notification to the seller (CAP-14).

**Edge cases**:
- User in a country unsupported for payouts: block seller onboarding with an explanation.
- KYC stuck in "pending" beyond SLA: system periodically re-checks status and notifies the seller.
- Seller changes payout country/entity later: re-verification is required before the next payout.
- Banned user attempts to re-register as a seller under a new email: flag for trust & safety (CAP-13).

**Connects to**: CAP-02, CAP-10, CAP-13, CAP-14

---

### CAP-02: Listing creation, file upload, versioning, and inventory

**Trigger**: An active seller opens "Create listing" or edits an existing listing.

**Inputs**:
- Seller identity: authenticated seller ID and account status, from CAP-01.
- Listing metadata: title, description, category/tags, price, cover image and gallery/preview assets, license terms, entered by the seller.
- Digital deliverables: the actual file(s) to deliver (e.g., ZIP, PDF, audio, video, software), and/or a pool of license keys/serial codes, uploaded by the seller.
- Inventory configuration: unlimited, or a finite quantity / finite key pool, set by the seller.
- Existing listing/version data (for edits): current content and version history, from the listing repository.

**Logic flow**:
1. System validates seller is active and within any active-listing limits.
2. Seller enters metadata and uploads deliverable file(s); system validates type, size, and runs a malware/safety scan (CAP-13).
3. System stores each uploaded deliverable as an immutable **version** with a version label/number; previously published versions are retained for buyers who already own them (CAP-08).
4. Seller sets pricing, license terms, and preview/sample assets (preview is publicly viewable; the full deliverable is gated).
5. Seller configures inventory: unlimited, fixed quantity, or a license-key pool (system counts available keys).
6. Seller saves as draft or publishes; on publish, system checks required fields (title, description, category, price, at least one deliverable that passed scanning) and that inventory > 0 if limited.
7. On publish, system indexes the listing for discovery (CAP-04) and makes it purchasable.
8. Seller may publish a **new version** later; system records it, optionally notifies prior buyers of the update (CAP-08, CAP-14), and serves the new version to future buyers.
9. **Error path**: If a deliverable fails the safety scan, the listing cannot be published; the seller is notified with the reason.

**Outputs**:
- Listing record: listing ID, seller ID, metadata, price, license terms, status (draft/published/suspended/sold-out), current version pointer.
- Versioned deliverable records: each version with its file reference(s) and/or key-pool reference, retained for entitlement fulfillment.
- Inventory state: remaining quantity / available key count.
- Search index update (CAP-04) and seller notification (CAP-14).

**Edge cases**:
- Upload interrupted/oversized: partial upload is discarded; seller retries; listing stays in draft.
- Seller deletes a listing that has existing buyers: deletion is blocked or soft-archived so prior buyers retain access (CAP-08).
- Finite key pool exhausted: listing auto-transitions to "sold out" and is hidden from purchase but kept for owners' re-download.
- Seller edits price while item is in buyers' carts: price at the moment of payment/checkout authorization governs (see CAP-05/CAP-06).
- Copyrighted/infringing upload: flagged by CAP-13; publish blocked pending review.

**Connects to**: CAP-01, CAP-04, CAP-07, CAP-08, CAP-13, CAP-15

---

### CAP-03: Seller storefront and profile

**Trigger**: A buyer visits a seller's public store page, or a seller previews their store.

**Inputs**:
- Seller profile: store name, branding, bio, aggregate rating, from CAP-01 and CAP-11.
- Seller's published listings: from CAP-02.
- Trust signals: total sales count, member-since date, response indicators, from the order and review systems.

**Logic flow**:
1. System retrieves the seller's active store profile and published, non-suspended listings.
2. System displays branding, aggregate rating (CAP-11), and the listing grid with sort/filter within the store.
3. System surfaces trust signals (verified badge, sales volume, ratings).
4. **Error path**: If the seller is suspended, the store shows an "unavailable" state and listings are not purchasable.

**Outputs**:
- Rendered storefront: profile + filtered/sorted listing grid shown to the buyer.
- Storefront view analytics event (CAP-16).

**Edge cases**:
- Seller has no published listings: show an empty/coming-soon state.
- Seller suspended mid-session: purchasing is disabled; existing owners keep library access (CAP-08).

**Connects to**: CAP-01, CAP-02, CAP-04, CAP-11, CAP-16

---

### CAP-04: Catalog search and discovery

**Trigger**: A buyer searches, applies filters, browses a category, or lands on the homepage.

**Inputs**:
- Search query: free-text keywords from the search bar.
- Filters: category/tags, price range, rating minimum, file type/format, license type, sort order (relevance, price, rating, newest, best-selling).
- Buyer context: session, optional purchase/browse history for relevance.
- Listing index: all published, in-stock listings with metadata and relevance signals, from CAP-02.

**Logic flow**:
1. System parses the query into keywords, categories, and attributes.
2. System matches against listing titles, descriptions, tags, and seller names.
3. System applies active filters and excludes suspended/sold-out/unpublished listings.
4. System scores by relevance (keyword strength, rating, sales velocity, completeness) and sorts per the selected order.
5. System returns paginated result summaries (title, seller, price, rating, cover, format).
6. Zero results → system suggests broader terms or related categories.
7. System logs the query and result interactions (CAP-16).
8. **Error path**: If the index is unavailable, fall back to a cached snapshot with reduced filtering.

**Outputs**:
- Paginated search results displayed to the buyer.
- Search analytics events (CAP-16).
- No-result suggestions.

**Edge cases**:
- Misspelled query: fuzzy matching/spell correction.
- Contradictory filters (min price > max): ignore invalid filter and notify.
- Featured/promoted placements (if any) must be clearly distinguished from organic results.
- Surfacing infringing items flagged by CAP-13: excluded once flagged.

**Connects to**: CAP-02, CAP-05, CAP-16

---

### CAP-05: Cart and checkout

**Trigger**: A buyer clicks "Add to cart" / "Buy now," then proceeds to checkout.

**Inputs**:
- Selected items: listing IDs, current versions, prices, license terms, from CAP-02.
- Buyer identity: authenticated buyer ID (or guest, if guest checkout is enabled — Open Questions).
- Cart contents: items, quantities (for finite-inventory keys), running totals.
- Applicable adjustments: discount/coupon codes, taxes (CAP-12), from configuration.

**Logic flow**:
1. Buyer adds items to a cart; system validates each item is still published and in stock.
2. System computes the order summary: per-item price, applicable discounts, tax (CAP-12), and total.
3. System prevents duplicate purchase of an item the buyer already owns (warns and offers re-download via CAP-08) unless re-purchase is explicitly allowed.
4. For finite-inventory/key items, system places a short reservation on the units during checkout to prevent overselling.
5. Buyer confirms and proceeds to payment (CAP-06).
6. Price/terms are locked at checkout authorization; later seller edits do not change this order.
7. **Error path**: If an item sells out or is removed during checkout, system removes it from the cart, notifies the buyer, and recalculates totals before payment.

**Outputs**:
- Cart/order draft: items, versions, prices, discounts, tax, total, reservation holds.
- Hand-off to payment (CAP-06).

**Edge cases**:
- Mixed cart from multiple sellers: system supports a single payment that splits across sellers (CAP-06), or splits into per-seller orders (decision — Open Questions).
- Coupon invalid/expired: reject with explanation; keep cart intact.
- Reservation expires before payment: re-validate stock at payment time.
- Free items (price 0): bypass payment, go straight to entitlement (CAP-07).

**Connects to**: CAP-02, CAP-06, CAP-08, CAP-12, CAP-16

---

### CAP-06: Payment processing and commission split

**Trigger**: A buyer authorizes payment at checkout (CAP-05).

**Inputs**:
- Order draft: items, sellers, amounts, tax, total, from CAP-05.
- Buyer payment method: card or stored method, via the payment form/gateway.
- Commission configuration: platform commission %/fixed fee per sale, by category or globally, set by admins.
- Tax data: computed tax to collect, from CAP-12.

**Logic flow**:
1. System sends the total to the payment gateway and attempts to capture/authorize the charge.
2. On success, system creates an **order** record and, for multi-seller carts, sub-orders per seller.
3. System computes the split per sub-order: gross price − platform commission − applicable fees = seller net proceeds; records the breakdown.
4. System marks the order "paid," consumes/decrements finite inventory or allocates a license key (CAP-02/CAP-07).
5. System triggers digital delivery & entitlement (CAP-07) and sends a receipt to the buyer (CAP-14).
6. Seller proceeds enter a **pending/clearing** balance subject to the refund-hold window before becoming payable (CAP-10).
7. On payment failure, system marks the order "payment failed," releases inventory reservations, and notifies the buyer with retry options.
8. **Error path**: If the gateway charges but the system fails before recording the order, a reconciliation process detects the orphaned charge and either completes the order or auto-refunds.

**Outputs**:
- Order + sub-order records: order ID, buyer, seller(s), items, amounts, commission, seller net, tax, status (paid/failed/refunded).
- Commission/ledger entries (CAP-10).
- Triggers to CAP-07 (delivery) and CAP-14 (receipt).
- Inventory decrement / key allocation (CAP-02).

**Edge cases**:
- Partial gateway success across multi-seller split: roll back to a consistent state or fully refund; never deliver unpaid items.
- Currency mismatch between buyer and seller payout currency: apply platform conversion; record rate used.
- Buyer initiates card chargeback later: freeze related seller proceeds and open dispute handling (CAP-09).
- Commission rate changes mid-transaction: use the rate in effect at order creation.

**Connects to**: CAP-05, CAP-07, CAP-09, CAP-10, CAP-12, CAP-14

---

### CAP-07: Digital delivery and entitlement

**Trigger**: An order is marked paid (CAP-06), or a free item is "purchased" (CAP-05).

**Inputs**:
- Paid order: order/sub-order IDs, buyer ID, listing IDs, purchased versions, from CAP-06.
- Deliverables: the file version(s) and/or an allocated license key, from CAP-02.
- Delivery configuration: download link expiry/limits, license terms, from admin/seller settings.

**Logic flow**:
1. System creates a durable **entitlement** linking the buyer to the purchased listing/version.
2. For file goods: system generates secure, access-controlled download access (expiring/signed links served via CDN); the buyer can re-download from their library (CAP-08) within policy limits.
3. For key goods: system assigns one unique key from the pool to the buyer and marks it consumed.
4. System confirms delivery readiness and notifies the buyer that the goods are available (CAP-14).
5. If a new version is later published (CAP-02), the entitlement grants access to the updated version per the update policy.
6. **Error path**: If file access generation or key allocation fails, the order is held in "paid–delivery pending," the buyer is informed, and the system retries; if unrecoverable (e.g., key pool corrupt), an auto-refund is initiated (CAP-09).

**Outputs**:
- Entitlement record: buyer ID, listing/version, license terms, grant date, status (active/revoked).
- Download access / allocated license key delivered to the buyer.
- Delivery confirmation notification (CAP-14).

**Edge cases**:
- Buyer exceeds download attempt limit: offer re-issuance via library (CAP-08) or support.
- Seller removes/changes a file post-sale: prior entitlement still resolves to the purchased version.
- Refund issued after delivery (CAP-09): entitlement is revoked; download access disabled (note: files already downloaded cannot be retracted — see Open Questions).
- Large file delivery under load: served via CDN; system degrades gracefully with resumable downloads.

**Connects to**: CAP-02, CAP-06, CAP-08, CAP-09, CAP-14

---

### CAP-08: Buyer library and re-download

**Trigger**: A buyer opens "My library" / "Purchases," or requests a re-download or a version update.

**Inputs**:
- Buyer identity: authenticated buyer ID, from the user account system.
- Entitlements: the buyer's active entitlements and purchased versions, from CAP-07.
- Current listing versions: latest available version and update eligibility, from CAP-02.

**Logic flow**:
1. System lists all of the buyer's entitlements with item name, seller, purchase date, license, and current version.
2. Buyer requests a download; system verifies the entitlement is active and within any download/limit policy, then issues secure access (CAP-07).
3. If a newer version is available and the entitlement grants updates, system offers the update and which version to download.
4. Buyer can view/download their license keys and receipts/invoices (CAP-12).
5. **Error path**: If an entitlement was revoked (refund/dispute), the item shows as unavailable with the reason.

**Outputs**:
- Library view: list of owned items with download/update actions, keys, and receipts.
- Re-issued secure download access or key display.

**Edge cases**:
- Listing later removed/seller suspended: owned items remain in the library and downloadable (deliverables retained per CAP-02).
- Buyer wants update but bought a version with no update entitlement: show upgrade/repurchase path if the seller offers one.
- Account deletion: define retention of entitlements/receipts (Open Questions).

**Connects to**: CAP-02, CAP-06, CAP-07, CAP-12

---

### CAP-09: Refunds and disputes

**Trigger**: A buyer requests a refund, opens a dispute, or a card chargeback is received; or a seller proactively issues a refund.

**Inputs**:
- Order context: order/sub-order, buyer, seller, items, amounts, delivery/entitlement state, from CAP-06/CAP-07.
- Request details: reason category (not as described, defective/corrupt file, didn't receive, accidental, fraudulent charge) and description, from the requester.
- Evidence: message history, download/access logs, file metadata, from relevant systems.
- Policy configuration: refund window and eligibility rules, set by admins (platform-wide for MVP).

**Logic flow**:
1. Requester opens a refund/dispute on an eligible order within the refund window.
2. System freezes the related seller proceeds (if still in clearing) so they cannot be paid out (CAP-10).
3. For straightforward cases within policy (e.g., within window, low value), system may auto-approve and refund the buyer, revoking the entitlement (CAP-07).
4. Otherwise system notifies the seller, who has a response window to accept, counter, or contest with evidence.
5. If parties agree (full/partial refund), system applies the outcome: refunds the buyer, reverses/adjusts commission and seller net (CAP-10).
6. If no agreement, the dispute escalates to a platform mediator who makes a binding decision based on evidence.
7. For external card chargebacks, system represents evidence to the gateway and reconciles the financial outcome.
8. System updates order status (refunded/partially refunded/dispute resolved) and notifies both parties (CAP-14).
9. **Error path**: If seller proceeds were already paid out before a chargeback, system records a negative balance/clawback against future earnings (CAP-10).

**Outputs**:
- Dispute/refund record: IDs, reason, status (open/responded/escalated/resolved), outcome.
- Financial adjustments: buyer refund, commission reversal, seller net adjustment (CAP-10).
- Entitlement revocation (CAP-07).
- Notifications to both parties (CAP-14).

**Edge cases**:
- Buyer downloaded the file then requests refund: weigh download/access logs; risk of refund abuse flagged to CAP-13.
- Duplicate disputes on one order: redirect to the existing one.
- Seller unresponsive: mediator decides on available evidence.
- Refund requested after the window: rejected unless fraud/infringement is involved.
- Chargeback fraud pattern across many buyers: escalate to CAP-13.

**Connects to**: CAP-06, CAP-07, CAP-10, CAP-13, CAP-14

---

### CAP-10: Seller ledger, balances, and payouts

**Trigger**: An order is paid (accrues pending proceeds), a clearing window elapses (funds become available), a scheduled payout runs, or a refund/chargeback adjusts balances.

**Inputs**:
- Earning events: paid sub-orders with seller net proceeds and commission, from CAP-06.
- Adjustment events: refunds, partial refunds, chargebacks, clawbacks, from CAP-09.
- Payout configuration: payout schedule (e.g., weekly), minimum payout threshold, clearing/refund-hold window, from seller preference and system defaults.
- Seller payout account: verified payout method, from CAP-01.

**Logic flow**:
1. On each paid sub-order, system records a ledger entry: gross, commission, fees, seller net → added to the seller's **pending** balance.
2. After the clearing/refund-hold window passes with no open dispute, pending proceeds move to **available** balance.
3. Refunds/chargebacks create reversing ledger entries against pending or available balance (or a negative/clawback balance if already paid out).
4. On the payout schedule, if available balance ≥ minimum threshold and the payout account is valid, system initiates a transfer via the payment provider and records a payout transaction.
5. System batches multiple sub-orders into one payout to reduce fees.
6. System notifies the seller of the payout with amount and expected arrival (CAP-14).
7. **Error path**: If the payout method is invalid/expired, funds are held, the seller is prompted to update payout info (CAP-01), and the payout retries on the next cycle.

**Outputs**:
- Ledger entries: append-only earnings, fees, refunds, adjustments per seller.
- Balance state: pending, available, on-hold, negative (clawback).
- Payout transactions: amount, method, provider reference, status (pending/completed/failed).
- Seller notifications (CAP-14) and accounting records for reconciliation/tax (CAP-12, CAP-16).

**Edge cases**:
- Below minimum threshold: accumulate until met.
- Funds frozen by an open dispute (CAP-09): excluded from available balance until resolved.
- Negative balance from post-payout chargeback: offset against future earnings; if persistently negative, escalate to collections/T&S (CAP-13).
- Payout currency differs from earning currency: apply conversion at payout time and record the rate.

**Connects to**: CAP-01, CAP-06, CAP-09, CAP-12, CAP-14, CAP-16

---

### CAP-11: Reviews and ratings

**Trigger**: A buyer completes a purchase and the review window opens, or a buyer submits/edits a review.

**Inputs**:
- Verified purchase: order/entitlement proving the buyer owns the item, from CAP-06/CAP-07.
- Review content: star rating (1–5) and optional text/criteria (quality, value, accuracy), from the buyer.
- Review window/config: how long after purchase reviews are allowed, set by admins.

**Logic flow**:
1. After delivery, system invites the buyer to review (only verified purchasers may review).
2. Buyer submits a rating and optional text; system stores it (pending moderation if flagged).
3. System publishes the review on the listing and seller profile and recalculates aggregate ratings and counts (CAP-03).
4. Seller may post a single public reply per review.
5. System scans for prohibited content; flagged reviews go to moderation (CAP-13) before publishing.
6. **Error path**: If aggregate recalculation fails, system retries; ratings shown remain at last good value.

**Outputs**:
- Review record: review ID, order/entitlement ref, rating, text, status (pending/published/flagged/removed), optional seller reply.
- Updated aggregate rating/count on listing and seller profile (CAP-03).
- Review notifications (CAP-14).

**Edge cases**:
- Non-purchaser tries to review: blocked (verified-purchase-only).
- Refunded order: policy decision whether the review stays or is removed (Open Questions).
- Rating manipulation (fake purchases to post reviews): pattern detection flags to CAP-13.
- Retaliatory or abusive reviews: moderation path.

**Connects to**: CAP-03, CAP-06, CAP-07, CAP-13, CAP-14

---

### CAP-12: Tax and invoicing

**Trigger**: Tax is computed at checkout (CAP-05), or a receipt/invoice is generated after payment (CAP-06).

**Inputs**:
- Order data: items, prices, buyer location/jurisdiction, seller location, from CAP-05/CAP-06.
- Tax configuration: tax/VAT rules for digital goods by jurisdiction, who is merchant of record, set by admins (MVP: capture, with full automation flagged for research).
- Business identity: platform/seller legal details for invoices.

**Logic flow**:
1. At checkout, system determines applicable tax for digital goods based on buyer jurisdiction and rules.
2. System adds tax to the order total and records the tax breakdown.
3. After payment, system generates a receipt/invoice with line items, tax, seller/platform identity, and order reference.
4. System makes invoices available to the buyer (CAP-08) and records tax data for reporting (CAP-16).
5. **Error path**: If jurisdiction can't be determined, apply a default/no-tax rule per policy and flag the order for review.

**Outputs**:
- Tax computation attached to the order.
- Receipt/invoice document available to buyer and seller.
- Tax/accounting records for reporting (CAP-16).

**Edge cases**:
- Buyer provides a business/VAT ID (reverse charge): adjust tax treatment if supported.
- Tax rules change between cart and payment: use the rule in effect at payment.
- Cross-border digital goods VAT thresholds: flagged for research.

**Connects to**: CAP-05, CAP-06, CAP-08, CAP-10, CAP-16

---

### CAP-13: Trust, safety, fraud, and content moderation

**Trigger**: A file is uploaded (CAP-02), a listing/review is published, a user reports content, or fraud signals fire from payments/refunds.

**Inputs**:
- Uploaded deliverables and previews: from CAP-02 (for malware/safety and infringement scanning).
- User reports: takedown/infringement/abuse reports with reason and evidence, from buyers/sellers/third parties.
- Risk signals: chargeback patterns, refund abuse, velocity anomalies, duplicate-account signals, from CAP-06/CAP-09/CAP-10.
- Moderation policy: prohibited content rules, infringement (DMCA-style) process, set by admins.

**Logic flow**:
1. On upload, system scans deliverables for malware and screens for obvious policy/infringement violations; failing items are blocked from publishing (CAP-02).
2. On report, system queues the item for moderation, optionally hiding it pending review for serious claims.
3. A moderator reviews evidence and decides: keep, remove/suspend listing, warn, suspend, or ban the seller; processes counter-notices for infringement.
4. Fraud signals (chargebacks, refund abuse, suspicious payouts) raise risk scores; high-risk sellers may have payouts held (CAP-10) or accounts restricted (CAP-01).
5. System logs all moderation/fraud actions for audit.
6. **Error path**: If automated scanning is unavailable, listings requiring scan stay in draft and are queued for manual review.

**Outputs**:
- Moderation/case records: subject, reason, decision, actor, timestamp (audit log).
- Enforcement actions: listing suspension/removal, seller restriction/ban, payout holds.
- Notifications to affected users (CAP-14).
- Risk scores feeding payouts (CAP-10) and onboarding (CAP-01).

**Edge cases**:
- False/abusive takedown reports: track reporter reliability; penalize abuse.
- Repeat infringer: escalating enforcement up to ban.
- Legitimate seller wrongly flagged: appeal/restore path with audit trail.
- Malware discovered after delivery: revoke entitlements (CAP-07), notify affected buyers, refund (CAP-09).

**Connects to**: CAP-01, CAP-02, CAP-06, CAP-07, CAP-09, CAP-10, CAP-11, CAP-14, CAP-15

---

### CAP-14: Notifications

**Trigger**: An event in any capability requires notifying a buyer, seller, or admin.

**Inputs**:
- Notification event: type (order paid, delivery ready, payout sent, refund/dispute update, review received, listing approved/removed, KYC status, version update available), target user, and payload, from any capability.
- User preferences: opted-in channels (email, in-app) and frequency, from account settings.
- Contact info: email/device references, from the user account system.

**Logic flow**:
1. System receives the event and looks up the target user's preferences for that event type.
2. In-app: create a notification record in the user's inbox.
3. Email: render the appropriate template and queue for delivery.
4. Deduplicate across channels; batch into digests if the user prefers.
5. Log delivery outcomes (CAP-16).
6. **Error path**: On email bounce, flag the address invalid and fall back to in-app only.

**Outputs**:
- In-app notification records; email messages; delivery logs (CAP-16).

**Edge cases**:
- User opted out of a channel for an event type: skip that channel.
- Critical financial/safety notices (payout failure, dispute, refund, security): always sent regardless of marketing opt-outs.
- Unverified email: suppress email, use in-app, until verified.

**Connects to**: CAP-01, CAP-02, CAP-06, CAP-07, CAP-09, CAP-10, CAP-11, CAP-13, CAP-16

---

### CAP-15: Admin and marketplace operations

**Trigger**: A platform administrator manages categories, fees, policies, moderation queues, or user accounts; or operational reports run.

**Inputs**:
- Admin identity: authenticated admin with role/permissions, from the user account system.
- Configuration data: commission rates (global/per category), category taxonomy, refund/dispute policy, payout schedule/threshold defaults, featured placements.
- Operational data: moderation queue (CAP-13), dispute escalations (CAP-09), payout/financial reconciliation (CAP-10), platform-wide metrics (CAP-16).

**Logic flow**:
1. Admin authenticates with appropriate permissions.
2. Admin configures commission, categories, policies, and featured placements; changes apply going forward (existing orders use prior config).
3. Admin works moderation/dispute queues and takes enforcement actions (CAP-13, CAP-09).
4. Admin can suspend/restore listings, sellers, or buyers and view audit logs.
5. Admin views platform-level reporting (CAP-16) and triggers reconciliation.
6. **Error path**: Unauthorized action attempts are blocked and logged.

**Outputs**:
- Configuration changes applied platform-wide (commission, categories, policies, placements).
- Enforcement/decision records and audit logs.
- Operational and financial reports (CAP-16).

**Edge cases**:
- Conflicting config edits by multiple admins: last-write-wins with audit history (or locking — Open Questions).
- Commission change must not retroactively alter settled orders.
- Privileged actions (refunds, bans, payout overrides) require elevated permission and are fully audited.

**Connects to**: CAP-09, CAP-10, CAP-13, CAP-16

---

### CAP-16: Reporting and analytics dashboards

**Trigger**: A seller, buyer, or admin opens a dashboard, or a scheduled report runs.

**Inputs**:
- User identity & role: from the user account system.
- View/time-range selection: dashboard section and period (7/30/90 days, custom), from the user.
- Raw data: orders (CAP-06), entitlements (CAP-07), refunds/disputes (CAP-09), ledger/payouts (CAP-10), reviews (CAP-11), tax (CAP-12), search/traffic events (CAP-04), notifications (CAP-14).

**Logic flow**:
1. System determines the role and tailors the dashboard.
2. *Sellers*: sales, revenue (gross/net/commission), best-selling items, conversion, traffic, ratings, pending vs. available balance, payout history, refund rate.
3. *Buyers*: purchase history, total spent, owned items, pending reviews, receipts.
4. *Admins*: GMV, take rate/commission revenue, active sellers/listings, dispute/refund rates, top categories, fraud metrics.
5. System aggregates over the selected range, computes period-over-period changes, and renders cards/charts/lists.
6. On request, system exports CSV/PDF; scheduled reports are emailed (CAP-14).
7. **Error path**: If a data source is down, show last cached data and mark it stale.

**Outputs**:
- Rendered dashboards; on-demand exports; scheduled emailed reports (CAP-14).

**Edge cases**:
- New account with no data: empty state with onboarding guidance.
- Clearly separate available vs. pending vs. on-hold balances for sellers (ties to CAP-10).
- Large data volumes: load summaries first, details async.
- Custom range including future dates: cap at today.

**Connects to**: CAP-04, CAP-06, CAP-07, CAP-09, CAP-10, CAP-11, CAP-12, CAP-14, CAP-15

## Dependency Map

| Capability | Depends on | Feeds into |
|-----------|-----------|------------|
| CAP-01 Seller onboarding & payout setup | — | CAP-02, CAP-10, CAP-13, CAP-14 |
| CAP-02 Listing, upload, versioning, inventory | CAP-01, CAP-13 | CAP-03, CAP-04, CAP-07, CAP-08 |
| CAP-03 Storefront & profile | CAP-01, CAP-02, CAP-11 | CAP-04, CAP-16 |
| CAP-04 Search & discovery | CAP-02 | CAP-05, CAP-16 |
| CAP-05 Cart & checkout | CAP-02, CAP-04, CAP-12 | CAP-06, CAP-08 |
| CAP-06 Payment & commission split | CAP-05, CAP-12 | CAP-07, CAP-09, CAP-10, CAP-14 |
| CAP-07 Delivery & entitlement | CAP-02, CAP-06 | CAP-08, CAP-09, CAP-14 |
| CAP-08 Buyer library & re-download | CAP-02, CAP-06, CAP-07, CAP-12 | — |
| CAP-09 Refunds & disputes | CAP-06, CAP-07 | CAP-10, CAP-13, CAP-14 |
| CAP-10 Ledger, balances & payouts | CAP-01, CAP-06, CAP-09 | CAP-12, CAP-14, CAP-16 |
| CAP-11 Reviews & ratings | CAP-06, CAP-07 | CAP-03, CAP-13, CAP-14 |
| CAP-12 Tax & invoicing | CAP-05, CAP-06 | CAP-08, CAP-10, CAP-16 |
| CAP-13 Trust, safety, fraud & moderation | CAP-02, CAP-06, CAP-09, CAP-11 | CAP-01, CAP-07, CAP-10, CAP-14, CAP-15 |
| CAP-14 Notifications | CAP-01, CAP-02, CAP-06, CAP-07, CAP-09, CAP-10, CAP-11, CAP-13 | CAP-16 |
| CAP-15 Admin & operations | CAP-09, CAP-10, CAP-13, CAP-16 | CAP-02, CAP-06 (config) |
| CAP-16 Reporting & analytics | CAP-04, CAP-06, CAP-07, CAP-09, CAP-10, CAP-11, CAP-12, CAP-14, CAP-15 | — |

## Open Questions

- **Commission model & rate**: Flat % platform-wide, per-category tiers, or volume-based? What fixed fees (if any) apply? Confirms CAP-06/CAP-10/CAP-15.
- **Refund policy**: Single platform-wide window (assumed 14 days) vs. per-seller policies; and how digital "already downloaded" goods affect refund eligibility. Affects CAP-09.
- **Entitlement revocation realism**: A refund can disable download access but cannot retract files already downloaded. Is watermarking/license-key revocation enough, or is any DRM expected? Affects CAP-07/CAP-09.
- **Multi-seller cart handling**: Single combined payment with split, vs. separate per-seller orders. Affects CAP-05/CAP-06.
- **Guest checkout**: Allowed, or account required (needed for the durable library/re-download)? Affects CAP-05/CAP-08.
- **Payout clearing window**: Length of the refund-hold period before seller proceeds become available (e.g., 7 vs. 14 days). Affects CAP-10.
- **Tax/VAT scope**: Is the platform the merchant of record collecting and remitting tax, or are sellers responsible? MVP assumes capture only. Affects CAP-12.
- **Currency**: Single launch currency vs. multi-currency pricing and payouts. Affects CAP-06/CAP-10/CAP-12.
- **Version update entitlement**: Do buyers automatically get future versions free, or only the version purchased? Affects CAP-02/CAP-07/CAP-08.
- **Reviews after refund**: Keep, hide, or remove reviews when the order is refunded. Affects CAP-11.
- **Inventory model emphasis**: Is finite license-key inventory a launch requirement or a later phase? Affects CAP-02/CAP-06.

## Research Suggestions

Topics that need deeper investigation by the researcher skill (researcher skill is unavailable in this run; these are flagged, not researched):

- **Digital-goods refund & download-abuse policy** — Refunds on instantly-delivered, downloadable goods invite abuse. Suggested researcher query: "Refund policy best practices for marketplaces selling instantly-downloadable digital goods — balancing buyer protection with refund/chargeback abuse, and handling already-downloaded files."
- **Marketplace commission & fee benchmarks (digital goods)** — Rate affects seller supply and buyer pricing. Suggested researcher query: "Commission/take-rate benchmarks for digital goods marketplaces (templates, assets, e-books, software) and impact on seller liquidity."
- **Tax/VAT on cross-border digital goods** — Complex jurisdictional rules and merchant-of-record obligations. Suggested researcher query: "VAT/GST and sales-tax obligations for cross-border digital goods marketplaces, including merchant-of-record models and reverse charge."
- **Marketplace payout, escrow & clawback mechanics** — Clearing windows, negative balances, and chargeback clawbacks. Suggested researcher query: "Split-payment payout architecture for marketplaces — clearing/hold windows, refund reserves, and chargeback clawback handling."
- **Anti-piracy / file protection for digital goods** — How much protection is feasible/expected. Suggested researcher query: "Anti-piracy and license enforcement options for digital goods marketplaces — watermarking, license keys, signed downloads, and their trade-offs."
- **Content moderation & DMCA/takedown workflow** — Infringement is a primary risk for digital goods. Suggested researcher query: "DMCA-style notice-and-takedown and counter-notice workflows for two-sided digital goods marketplaces, including repeat-infringer enforcement."
- **Verified-purchase review integrity** — Preventing fake reviews and manipulation. Suggested researcher query: "Review integrity practices for digital marketplaces — verified-purchase-only reviews, manipulation detection, and seller-reply policies."

## Next Steps

1. Resolve the high-impact Open Questions with stakeholders — commission model, refund policy, payout clearing window, and tax/merchant-of-record stance — since they shape CAP-06, CAP-09, CAP-10, and CAP-12.
2. Run the flagged Research Suggestions (via the researcher skill) on refund abuse, tax/VAT, payout/clawback mechanics, and DMCA workflow; fold findings back in.
3. Have an agent with librarian access search for prior researches/specs/docs (see Existing Knowledge) and reconcile this breakdown with anything found.
4. Define the launch category taxonomy and which inventory model (unlimited vs. finite key pool) is required at launch.
5. Walk the end-to-end money flow (checkout → split → clearing → payout, plus refund/chargeback reversals) with finance to validate the ledger and balance states in CAP-10.
6. Define the notification event catalog (CAP-14) and the moderation/takedown policy (CAP-13) before build.

---
*Capability breakdown produced by solution-architect skill. Use the librarian skill to persist this artifact.*
