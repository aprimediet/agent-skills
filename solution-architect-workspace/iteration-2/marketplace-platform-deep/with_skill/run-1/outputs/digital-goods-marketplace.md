# Digital Goods Marketplace

> Solution Architect | Depth: deep | Generated: 2026-06-09

> **Note on this run**: This breakdown was produced non-interactively. Where the skill would normally ask the user clarifying questions (problem framing, scope boundaries, edge-case decisions), reasonable assumptions were made and are flagged in **Open Questions** and inline. The librarian skill was unavailable, so existing-knowledge retrieval is delegated below rather than performed.

## Existing Knowledge

The librarian skill is **not available** in this run, so no prior artifacts could be loaded. Before building on this breakdown, an agent with librarian access should check for existing work to avoid duplication. Suggested searches:

- **Category `researches`** — keywords: "digital goods marketplace", "two-sided marketplace trust", "digital product delivery", "marketplace payouts", "chargeback fraud digital goods". Prior research on trust/safety, escrow, or fraud would inform CAP-06, CAP-09, and CAP-11.
- **Category `specs`** — keywords: "marketplace", "seller onboarding", "payout", "licensing". An existing seller-onboarding or payment spec would provide baseline scope for CAP-01, CAP-07, and CAP-10.
- **Category `docs`** — keywords: "payment gateway integration", "tax/VAT digital goods", "DMCA takedown". Operational docs would inform CAP-09 and the compliance open questions.

If any of those artifacts exist, re-run this breakdown incorporating them.

## Problem Statement

- **Business problem**: The business wants to operate a two-sided marketplace that connects sellers of digital goods (e-books, templates, software, audio, art, courses, design assets, etc.) with buyers, and earns revenue by taking a commission on each sale. The platform must attract and retain sellers (supply), attract buyers (demand), and facilitate trustworthy transactions — discovery, purchase, instant delivery, and reliable payouts — while protecting against fraud, piracy, and chargebacks. Without a structured platform, sellers lack reach and payment infrastructure, and buyers lack a trusted place to discover and safely purchase digital goods.
- **User problem**:
  - *Buyers* need to discover relevant digital goods, evaluate quality before buying (previews, ratings, reviews), purchase securely, and receive immediate, reliable access to what they paid for — with recourse if the product is misrepresented or broken.
  - *Sellers* need to list and merchandise their products, manage availability and versions, set pricing, get paid reliably and transparently, and build a reputation that drives more sales — without handling payment infrastructure, fraud, or delivery logistics themselves.
- **Success criteria** (assumed targets — confirm with stakeholders):
  - Buyer purchase completion rate (checkout start → successful delivery) above 90%.
  - Median time from purchase to successful product access under 30 seconds (instant digital delivery).
  - Seller payout reliability above 99% (initiated payouts that land successfully), with transparent balance visibility.
  - Refund/dispute rate below 3% of completed transactions; fraud/chargeback losses below an agreed threshold of gross merchandise value.
  - Reach a minimum of 1,000 published listings and a target monthly GMV within the first 6 months of launch.

## Scope

- **In scope**: Seller onboarding and identity/payout setup; listing creation and lifecycle management; digital asset upload, versioning, and storage; inventory/availability and licensing model (unlimited vs. limited-quantity/license-key); catalog search and discovery; product detail with previews; cart and checkout; payment processing and platform commission; instant digital delivery and secure download/license access; order history and buyer library; ratings and reviews; refunds, disputes, and chargeback handling; seller earnings ledger and payouts; content moderation and takedown; multi-channel notifications; buyer and seller dashboards with analytics.
- **Out of scope** (assumed for MVP — confirm): physical goods or hybrid physical+digital bundles; subscription/recurring-access products (one-time purchases only for MVP); marketplace-funded affiliate/referral program; in-platform messaging/chat between buyer and seller (handled via support and reviews for MVP); seller-to-seller transactions; native mobile apps (web-only for MVP); automated tax filing/remittance to authorities (the platform collects tax data but does not file on sellers' behalf); white-label/multi-tenant marketplace.
- **Existing systems** (assumed available): user account and authentication system; email/notification delivery service; a payment gateway with payout/transfer support (e.g., a Stripe-Connect-style capability); cloud object storage for large digital assets; an identity/KYC verification provider for seller onboarding. *(Named as capabilities the platform integrates with, not as implementation choices.)*

## Capabilities

### CAP-01: Seller onboarding and payout setup

**Trigger**: A registered user chooses to "Become a Seller" / "Start Selling," or an existing seller updates their seller profile or payout details.

**Inputs**:
- User identity: authenticated user ID and account status, from the user account system.
- Seller profile data: display/store name, bio, profile image, public contact/support info, entered by the user.
- Identity & tax data: legal name, business/individual classification, country, and tax identifiers required for payouts and reporting, entered by the user and verified by the identity/KYC provider.
- Payout method: bank account, connected wallet, or other supported payout destination, entered by the user and validated by the payment gateway.

**Logic flow**:
1. System confirms the user's account is active and eligible to become a seller (e.g., email verified, not banned).
2. System collects the public seller profile (store name, bio, image) and checks store-name uniqueness, appending guidance if taken.
3. System collects identity and tax information and submits it to the identity/KYC verification process; seller status is set to "pending verification."
4. System collects and validates a payout method with the payment gateway.
5. If verification passes and a valid payout method exists, system marks the seller as "verified — can publish and receive payouts."
6. If verification is incomplete, the seller may still create draft listings but **cannot publish or receive payouts** until verification clears.
7. System creates a seller earnings ledger (zero balance) tied to the seller account (feeds CAP-10).
8. **Error path**: If KYC fails or is flagged, system holds seller activation, notifies the user with the reason, and routes the case for manual review.

**Outputs**:
- Seller account record: seller ID, public profile, verification status, payout method reference, stored in the seller/account system.
- Verification result: pass/fail/pending status from the identity provider.
- Earnings ledger initialized for the seller (used by CAP-08 and CAP-10).
- Seller notification: onboarding status and any required next steps (CAP-09).

**Edge cases**:
- User is in a country the platform cannot pay out to: system blocks seller activation and explains supported regions.
- KYC verification is delayed: seller can prepare draft listings but sees a clear "verification pending — cannot publish" state.
- Payout method later becomes invalid: future payouts are held (see CAP-08); seller is prompted to update.
- User already has a seller account: system routes to profile editing rather than re-onboarding.

**Connects to**: CAP-02, CAP-08, CAP-09, CAP-10, CAP-11

---

### CAP-02: Listing creation and lifecycle management

**Trigger**: A verified (or draft-eligible) seller opens "Create Listing," edits an existing listing, or changes a listing's status (publish, unpublish, archive).

**Inputs**:
- Seller identity: authenticated seller ID, verification status, from CAP-01.
- Listing metadata: title, description, category/subcategory, tags, price, currency, license terms, preview media (thumbnail, sample images, demo/preview file), entered by the seller.
- Digital asset reference: the uploaded deliverable file(s) and version, from CAP-03.
- Inventory/availability settings: unlimited vs. limited quantity / number of license keys, from CAP-04.
- Existing listing data (for edits): current listing content, from the listing repository.

**Logic flow**:
1. System verifies the seller is allowed to create/edit listings (active, not suspended).
2. System presents the listing form, pre-populated if editing.
3. Seller enters metadata, sets price and license terms, attaches preview media, and links the uploaded deliverable (CAP-03) and inventory model (CAP-04).
4. System auto-generates a unique listing slug from the title; on conflict, appends a numeric suffix.
5. Seller chooses to save as draft or publish.
6. On publish, system validates required fields (title, description, category, price, at least one deliverable asset, a thumbnail/preview) **and** that the seller is verified; if not verified, publishing is blocked with guidance.
7. On publish, system submits the listing to content moderation (CAP-11) per policy; depending on moderation mode, the listing is published immediately with post-hoc review, or held pending approval.
8. System indexes published listings for search and discovery (CAP-05).
9. Status changes (unpublish/archive) remove the listing from discovery but preserve it for existing buyers' library access (CAP-08) and order history.
10. **Error path**: If the linked deliverable asset is missing or failed virus/format checks (CAP-03), publishing is blocked until a valid asset is attached.

**Outputs**:
- Listing record: listing ID, seller ID, metadata, price, license terms, asset/version references, inventory model, status (draft/pending/published/unpublished/archived/suspended), timestamps.
- Search index update: published listings indexed/de-indexed in CAP-05.
- Moderation submission: listing queued/checked by CAP-11.
- Seller notification: save/publish/moderation outcome (CAP-09).

**Edge cases**:
- Seller edits price or deliverable of a listing with existing buyers: existing buyers retain access to the version they purchased; new price/version applies to future buyers only.
- Seller archives a listing mid-checkout for another buyer: in-progress checkouts already holding the item complete; new checkouts are blocked.
- Listing exceeds platform limits (e.g., max listings for unverified sellers): publishing blocked with limit message.
- Duplicate/plagiarized listing detected by moderation: listing held or removed (CAP-11).

**Connects to**: CAP-01, CAP-03, CAP-04, CAP-05, CAP-06, CAP-08, CAP-11, CAP-12

---

### CAP-03: Digital asset upload, versioning, and storage

**Trigger**: A seller uploads or replaces a deliverable file (or preview/demo file) for a listing.

**Inputs**:
- Seller identity and target listing: from CAP-01/CAP-02.
- Asset file(s): the digital deliverable and any preview/demo files, with file type, size, and intended role (deliverable vs. preview), uploaded by the seller.
- Version intent: new asset vs. new version of an existing asset, indicated by the seller.

**Logic flow**:
1. System accepts the upload and validates file type, size limits, and (where applicable) format integrity against the allowed-type policy.
2. System scans the file for malware/prohibited content; files failing the scan are quarantined and rejected.
3. System stores the validated asset in secure storage and records a version number, checksum, and upload timestamp.
4. If the upload is a new version of an existing deliverable, system retains prior versions so existing buyers keep access to the version they purchased while new buyers receive the latest.
5. System generates derived preview artifacts where applicable (e.g., watermarked sample, truncated demo) for display on the product page (CAP-06) without exposing the full deliverable.
6. System links the stored asset/version to the listing (CAP-02).
7. **Error path**: If the upload is interrupted or the scan fails, system discards the partial/failed file, keeps any previously valid version intact, and notifies the seller.

**Outputs**:
- Asset record: asset ID, listing ID, version, file reference, checksum, type, size, scan status, stored in the asset/storage system.
- Preview artifact: watermarked/truncated sample for public display.
- Version history: ordered list of versions per deliverable.
- Seller notification: upload success/failure and scan result (CAP-09).

**Edge cases**:
- Very large asset upload: system supports resumable/chunked upload and reports progress; partial failures do not corrupt the prior version.
- Seller uploads a deliverable that matches a known-pirated fingerprint: flagged to moderation (CAP-11) and held.
- Preview generation fails for an unsupported format: listing can still publish using a seller-provided thumbnail; auto-preview is skipped.
- Buyer-owned version is later removed by the seller: buyers retain a retrievable copy of the version they purchased (see Open Questions on retention policy).

**Connects to**: CAP-02, CAP-06, CAP-08, CAP-11

---

### CAP-04: Inventory, availability, and licensing model

**Trigger**: A seller configures how a listing is sold (unlimited downloads vs. limited quantity / limited license keys), or the system decrements availability when a sale completes.

**Inputs**:
- Listing reference: from CAP-02.
- Availability model: "unlimited" (digital good sold to any number of buyers) or "limited" (finite quantity, finite license-key pool, or finite seats), set by the seller.
- License-key pool (if limited-key): a set of pre-generated or seller-supplied keys, provided by the seller or generated by the platform.
- Sale event: a completed order for the listing, from CAP-07.

**Logic flow**:
1. Seller selects the availability model when creating/editing the listing (CAP-02).
2. For unlimited goods, no stock tracking is needed; the item is always purchasable while published.
3. For limited quantity, system tracks remaining count; for limited-key, system tracks the remaining key pool.
4. During checkout (CAP-07), system places a short hold (reservation) on a unit/key to prevent overselling while payment is in progress.
5. On successful payment, system permanently decrements the count or assigns a specific license key to the order (feeds delivery in CAP-08).
6. When availability reaches zero, system marks the listing "sold out," removes it from purchase flows, and (per seller setting) keeps it visible-but-unavailable or auto-unpublishes it.
7. If a payment is abandoned or fails, the held unit/key is released back to the pool.
8. **Error path**: If two checkouts race for the last unit/key, only one succeeds; the other is informed it is sold out and the reservation is released.

**Outputs**:
- Availability state: remaining quantity / remaining key count / sold-out flag per listing.
- License-key assignment: the specific key bound to a completed order (used by CAP-08).
- Reservation/hold record: temporary lock during checkout, released on completion or timeout.
- Seller notification: low-stock and sold-out alerts (CAP-09).

**Edge cases**:
- Seller reduces quantity below the number already sold: system rejects the change; sold units cannot be un-sold.
- License-key pool exhausted but listing still marked available: system blocks new purchases and alerts the seller to add keys.
- Reservation timeout during slow payment: hold expires and unit/key returns to the pool; if the buyer then completes payment, system re-checks availability and refunds if truly sold out (see CAP-07 error path).
- Seller switches a sold listing from limited to unlimited: allowed going forward; previously assigned keys remain valid.

**Connects to**: CAP-02, CAP-07, CAP-08, CAP-09

---

### CAP-05: Catalog search and discovery

**Trigger**: A buyer visits the marketplace, enters a search query, applies filters, browses a category, or views curated/recommended collections.

**Inputs**:
- Search query: free-text keywords, from the search bar.
- Filter/sort parameters: category, price range, license type, format/file type, minimum rating, sort order (relevance, price, rating, newest, best-selling), from filter controls.
- Buyer context: locale/currency, optional purchase/browse history for relevance, from the user/session.
- Listing index: published listings with metadata, rating, and sales signals, maintained by CAP-02 and CAP-06.

**Logic flow**:
1. Buyer searches or browses a category/collection.
2. System parses the query into keywords, categories, and attributes.
3. System matches against indexed listing titles, descriptions, tags, and categories.
4. System applies active filters (category, price, license, format, rating).
5. System scores results by relevance, blending keyword match strength with quality signals (rating, sales volume, listing completeness).
6. System sorts per the selected order (default: relevance) and paginates results.
7. System returns listing summaries (title, seller, price in buyer currency, rating, thumbnail, sold-out flag).
8. On zero results, system suggests broader terms or related categories.
9. System logs queries, filters, and click-through for analytics (CAP-12).
10. **Error path**: If the search index is degraded, system falls back to a cached catalog snapshot with reduced filtering and flags results as possibly stale.

**Outputs**:
- Search results: paginated listing summaries displayed to the buyer.
- Recommendations/collections: curated or personalized listing sets.
- Search analytics events: queries, filter usage, result counts, click-through (CAP-12).

**Edge cases**:
- Misspelled query: system applies fuzzy matching / spell correction.
- Contradictory filters (min price > max price): system ignores the invalid filter and notifies the buyer.
- Currency display: prices shown in buyer's locale currency for browsing; the charge currency and conversion are confirmed at checkout (CAP-07).
- Sold-out limited items: shown with a clear "sold out" badge and optionally a "notify me / similar items" affordance.

**Connects to**: CAP-02, CAP-06, CAP-07, CAP-12

---

### CAP-06: Product detail and preview

**Trigger**: A buyer opens a listing's detail page from search, a collection, a link, or their wishlist.

**Inputs**:
- Listing reference: listing ID, from CAP-05 or a direct link.
- Listing content: metadata, price, license terms, seller profile snapshot, from CAP-02.
- Preview artifacts: watermarked samples / demo files, from CAP-03.
- Social proof: rating summary and reviews, from CAP-09.
- Availability state: in stock / sold out, from CAP-04.

**Logic flow**:
1. System loads the listing's full public content, seller profile snapshot, and current availability.
2. System renders previews (images, watermarked samples, demo playback) without exposing the full deliverable.
3. System displays price in the buyer's currency, license terms, format/size details, rating, and review highlights.
4. System shows a purchase action — "Buy now," "Add to cart," or "Sold out" depending on availability and whether the buyer already owns the item.
5. If the buyer already owns the listing, system shows "In your library" with a link to access it (CAP-08) instead of a buy action.
6. System records the product view for analytics and recommendations (CAP-12).
7. **Error path**: If a preview artifact fails to load, system degrades gracefully to the thumbnail and remaining available previews.

**Outputs**:
- Product detail view: full listing presentation with previews and purchase affordance, displayed to the buyer.
- Ownership state: whether the buyer already owns the item.
- View analytics event (CAP-12).

**Edge cases**:
- Listing was unpublished/archived after the buyer arrived via an old link: system shows an "unavailable" state and suggests similar items (existing owners still reach it via their library).
- Buyer attempts to access the full deliverable from the preview: system only ever serves watermarked/truncated previews here; the full file is delivered only post-purchase (CAP-08).
- Region-restricted listing: if the seller or policy restricts sale regions, system shows a "not available in your region" state.

**Connects to**: CAP-02, CAP-03, CAP-04, CAP-05, CAP-07, CAP-08, CAP-09, CAP-12

---

### CAP-07: Cart, checkout, and payment

**Trigger**: A buyer clicks "Buy now" or proceeds to checkout from the cart.

**Inputs**:
- Cart contents: one or more listings with quantities (typically 1 per digital good), price, currency, license terms, from CAP-06.
- Buyer identity: authenticated buyer ID and account status; guest-checkout email if guest checkout is allowed (see Open Questions).
- Payment method: card or stored/wallet payment method, from the buyer via the payment form or saved methods.
- Pricing/fee configuration: platform commission and any buyer-facing fees/taxes (VAT/sales tax) by jurisdiction, defined by administrators.
- Availability/holds: reservation state for limited items, from CAP-04.

**Logic flow**:
1. System assembles the cart, validating each listing is still published, available, and not already owned by the buyer.
2. For limited items, system places availability holds (CAP-04) for the checkout window.
3. System computes the order total: item prices + applicable tax − any discounts, displayed with a clear breakdown; system also computes the platform commission and the seller net per item (recorded but the buyer sees the gross).
4. System confirms the charge currency and applies any conversion if buyer and listing currencies differ, disclosing the rate.
5. Buyer selects/enters a payment method and authorizes payment.
6. System processes the charge through the payment gateway.
7. On success, system creates the order record (status "paid"), captures per-item commission/seller-net splits, and triggers delivery (CAP-08) and seller earnings accrual (CAP-10).
8. On success, system permanently decrements limited availability / binds license keys (CAP-04).
9. On payment failure, system releases availability holds, sets the order "payment failed," and offers retry.
10. **Error path**: If the charge succeeds but order creation fails (system crash), reconciliation detects the orphaned charge and either completes the order or refunds the buyer; if a held unit was sold out in the interim, the buyer is automatically refunded with an explanation.

**Outputs**:
- Order record: order ID, buyer ID, line items (listing, seller, version, license key if any), gross amount, tax, platform commission, seller net, currency, status (paid/payment failed/refunded), timestamps.
- Payment receipt: emailed/displayed receipt with order reference and tax breakdown (CAP-09).
- Delivery trigger: signal to CAP-08 to grant access/deliver the asset.
- Earnings accrual trigger: signal to CAP-10 to credit the seller's pending balance.
- Availability update: decrement/key-binding to CAP-04.

**Edge cases**:
- Buyer already owns the item: system blocks re-purchase (or warns) and links to the existing library entry.
- Multi-seller cart: a single buyer payment is split across sellers' earnings; each seller is credited their respective net (CAP-10).
- Tax jurisdiction cannot be determined: system uses the buyer's account/billing country; if still ambiguous, applies a conservative default and flags for review.
- Discount/coupon abuse (if coupons exist): system enforces per-buyer and per-coupon usage limits.
- Chargeback initiated by the buyer's card issuer after purchase: triggers chargeback handling within CAP-09 and freezes related seller earnings (CAP-10).

**Connects to**: CAP-04, CAP-06, CAP-08, CAP-09, CAP-10, CAP-12

---

### CAP-08: Digital delivery and buyer library

**Trigger**: An order reaches "paid" status (CAP-07), or a buyer returns to access a previously purchased item.

**Inputs**:
- Completed order: order ID, buyer ID, line items with asset/version references and any assigned license keys, from CAP-07.
- Asset reference: the specific deliverable version purchased, from CAP-03.
- Access policy: download limits, link expiry, and license terms, defined by administrators and the listing.

**Logic flow**:
1. On a paid order, system grants the buyer entitlement to each purchased item, binding the specific asset version (and license key, if any) to the buyer's account.
2. System generates secure, time-limited and/or count-limited access (download links and/or license-key reveal) for the buyer.
3. System adds the purchased items to the buyer's permanent **library**, accessible any time from the buyer's account.
4. When the buyer downloads or accesses an item, system validates the entitlement, serves the correct purchased version, and logs the access against any limits.
5. If the seller releases a new version (CAP-03), the buyer continues to own the purchased version; whether they get free upgrades is governed by the listing's license terms (see Open Questions).
6. System sends a delivery confirmation with access instructions (CAP-09).
7. **Error path**: If link generation fails, system retries and, on persistent failure, surfaces an in-library "retry access" action and alerts support; the entitlement itself is never lost.

**Outputs**:
- Entitlement record: buyer ID, order ID, listing/asset/version, license key (if any), access limits, status (active/revoked), stored in the entitlement system.
- Secure access link / license reveal: time/count-limited download or key, served to the buyer.
- Library entry: persistent buyer-facing record of owned items.
- Delivery confirmation notification (CAP-09).
- Access log: downloads/accesses for abuse detection and limits.

**Edge cases**:
- Buyer hits the download-count or link-expiry limit: system allows re-generating access from the library per policy (digital goods generally remain accessible to legitimate owners).
- Order is later refunded (CAP-09): entitlement is revoked, access links invalidated, and the library entry marked "refunded — access removed."
- Seller account is removed/asset deleted after purchase: platform retains the purchased version for the buyer per the retention policy (Open Questions).
- Suspected credential sharing / mass downloading from one entitlement: system flags for abuse review (CAP-11) and may throttle access.

**Connects to**: CAP-03, CAP-04, CAP-07, CAP-09, CAP-10, CAP-11, CAP-12

---

### CAP-09: Reviews, refunds, disputes, and chargebacks

**Trigger**: A buyer submits a review after purchase; or a buyer requests a refund/opens a dispute; or the payment gateway notifies of a chargeback.

**Inputs**:
- Purchase/entitlement context: order ID, buyer ID, seller ID, listing, purchase date, access/download activity, from CAP-07/CAP-08.
- Review content: star rating (1–5) and optional text, from the buyer (verified purchase required).
- Refund/dispute request: reason category (not as described, broken/corrupt file, duplicate purchase, accidental, never delivered) and description, from the buyer.
- Chargeback notice: dispute reason and amount, from the payment gateway.
- Policy configuration: review window, refund eligibility rules, dispute SLAs, from administrators.

**Logic flow**:
1. **Reviews**: After a buyer's order is delivered, system opens a review invitation; only verified purchasers may review. Submitted reviews are published, associated with the listing/seller, and the seller's aggregate rating is recalculated (feeds CAP-05, CAP-06).
2. **Refund request**: Buyer requests a refund from order history; system checks eligibility (within refund window, access/download activity, reason category). Per policy, low-risk requests may be auto-approved; others route to the seller and/or platform support.
3. On refund approval, system reverses the charge (full or partial) to the buyer, revokes the entitlement (CAP-08), and reverses or claws back the seller's earnings (CAP-10).
4. **Dispute escalation**: If buyer and seller disagree, the case escalates to platform support, who reviews evidence (order, access logs, previews vs. delivered, messages/notes) and makes a binding decision (refund, partial refund, or deny).
5. **Chargeback**: On a gateway chargeback notice, system immediately freezes the related seller earnings (CAP-10), compiles evidence (delivery and access logs, license terms, reviews), and submits a representment; the outcome (won/lost) determines whether the seller is debited or made whole.
6. System notifies all parties at each step (CAP-09 events feed CAP-13).
7. **Error path**: If a refund cannot be issued to the original payment method (expired card), system issues store credit or an alternate method per policy and flags for support.

**Outputs**:
- Review record: review ID, order/listing/seller, rating, text, verified-purchase flag, status (published/flagged/removed).
- Rating rollup: recalculated seller/listing rating (to CAP-05, CAP-06).
- Refund/dispute record: case ID, order, reason, status (open/approved/denied/escalated/resolved), resolution amount.
- Chargeback record: gateway reference, amount, status (received/contested/won/lost), evidence package.
- Financial reversal instructions: to the payment system and to CAP-10 (earnings clawback/freeze).
- Notifications to buyer and seller at each transition (CAP-13).

**Edge cases**:
- Buyer downloaded the full deliverable then requests a refund: flagged as higher-risk; routed to manual review rather than auto-approval (digital goods are non-returnable once consumed, per policy).
- Retaliatory or fake reviews: system detects patterns (no verified purchase, burst activity) and flags for moderation (CAP-11).
- Seller's balance is insufficient to cover a clawback: the negative balance is carried and recovered from future earnings or the seller's payout method per policy.
- Buyer opens both a platform dispute and a card chargeback: system links them and the chargeback outcome supersedes.
- Review submitted for a refunded order: review is removed or marked, as ownership was reversed.

**Connects to**: CAP-05, CAP-06, CAP-07, CAP-08, CAP-10, CAP-11, CAP-13

---

### CAP-10: Seller earnings ledger and commission

**Trigger**: A sale completes (CAP-07), a refund/chargeback occurs (CAP-09), or a payout is initiated (CAP-11) — any event that changes a seller's balance.

**Inputs**:
- Sale event: order line item with gross amount, platform commission, computed seller net, currency, from CAP-07.
- Commission configuration: platform commission rate(s) (flat %, per-category, or tiered) and any fixed fees, from administrators.
- Reversal events: refund/clawback/chargeback amounts, from CAP-09.
- Hold policy: clearing period during which new earnings are "pending" before becoming "available" (buyer-protection window), from administrators.

**Logic flow**:
1. On a completed sale, system computes the split: gross − platform commission − applicable processing/tax handling = seller net (the commission rate in effect at purchase time is locked to the order).
2. System credits the seller net to a **pending** balance and starts the clearing period (buyer-protection/refund window).
3. When the clearing period elapses with no open refund/dispute/chargeback, system moves the amount from **pending** to **available** balance (eligible for payout in CAP-11).
4. On a refund or lost chargeback, system reverses the corresponding seller net from pending (or claws back from available/future earnings if already cleared), per CAP-09.
5. System maintains a complete, auditable ledger of every credit, debit, fee, and adjustment per seller.
6. System exposes balances (pending, available, lifetime earnings, fees paid) to the seller dashboard (CAP-12).
7. **Error path**: If a split cannot be computed (missing commission config), system records the gross, flags the line for finance review, and withholds it from available balance until resolved.

**Outputs**:
- Ledger entries: dated credits/debits with type (sale, commission, refund, chargeback, payout, adjustment), amount, currency, related order/case.
- Balance state: pending, available, and lifetime totals per seller.
- Payout-eligibility signal: available balance amounts usable by CAP-11.
- Accounting/reporting records for reconciliation and tax (feeds CAP-12 and seller tax documents).

**Edge cases**:
- Multi-currency earnings: system tracks balances per currency or converts to a settlement currency per policy, disclosing the rate.
- Commission rate changes after a sale: the rate at purchase time governs that order.
- Negative available balance after clawback: carried forward and recovered from subsequent sales or, per policy, debited from the payout method.
- High-value sale during a fraud review: amount held in pending beyond the standard window until cleared (CAP-11).

**Connects to**: CAP-01, CAP-07, CAP-09, CAP-11, CAP-12

---

### CAP-11: Seller payouts

**Trigger**: A seller's available balance becomes payable per their payout schedule (automatic), the seller requests a manual withdrawal, or a scheduled payout run executes.

**Inputs**:
- Available balance: payable amount per seller, from CAP-10.
- Payout method: the seller's validated payout destination, from CAP-01.
- Payout schedule/threshold: automatic (daily/weekly/monthly) or manual/threshold-based, from seller preference and system default.
- Risk/hold signals: any open disputes, chargeback exposure, or fraud review flags, from CAP-09/CAP-12.

**Logic flow**:
1. System determines payable amount from the seller's **available** balance (excluding pending and held amounts).
2. System checks risk/hold signals; if the seller is under fraud or dispute review, payout is held and the seller is informed.
3. System validates the payout method is active and valid with the payment gateway.
4. Per the schedule/threshold, system initiates a transfer of the payable amount to the seller's payout method.
5. System records the payout transaction (amount, destination, gateway reference, status) and debits the available balance in the ledger (CAP-10).
6. System notifies the seller with the amount and expected arrival (CAP-13).
7. On payout failure (invalid account, gateway rejection), system reverses the debit, returns funds to available balance, and prompts the seller to fix their payout method.
8. **Error path**: If the payout method is invalid/expired, system holds funds and sends repeated prompts to update payout details; no funds are lost.

**Outputs**:
- Payout transaction record: seller ID, amount, method, gateway reference, status (pending/completed/failed), timestamp.
- Ledger debit: available balance reduced by the paid-out amount (CAP-10).
- Seller notification: payout confirmation or failure with resolution steps (CAP-13).
- Reconciliation/accounting record.

**Edge cases**:
- Payable below the minimum payout threshold: funds accumulate until the threshold is met.
- Seller has no/invalid payout method: all funds held; periodic prompts to register a method.
- Multiple sellers/payouts in one run: system batches transfers to minimize fees while keeping per-seller records distinct.
- Cross-currency payout: conversion applied at payout time with the rate disclosed.
- Payout requested while a large chargeback is pending: the at-risk amount is excluded (kept in pending/hold) and only the safe portion is paid.

**Connects to**: CAP-01, CAP-09, CAP-10, CAP-13

---

### CAP-12: Content moderation, trust, and safety

**Trigger**: A listing or asset is submitted/updated (CAP-02/CAP-03), content is reported by a user, a copyright/DMCA takedown is filed, or automated risk signals fire.

**Inputs**:
- Submitted content: listing metadata, deliverable/preview assets, seller profile, from CAP-02/CAP-03.
- Reports/takedowns: user report or rights-holder takedown notice with the targeted listing and reason.
- Automated signals: malware scan results (CAP-03), piracy/duplicate fingerprints, fake-review patterns (CAP-09), abusive download/access patterns (CAP-08).
- Policy configuration: prohibited content categories, moderation mode (pre- vs. post-publication), and enforcement actions, from administrators.

**Logic flow**:
1. On submission, system runs automated checks (malware, prohibited content, plagiarism/duplicate fingerprinting); clear items proceed, suspicious items are queued for human review.
2. Per moderation mode, listings either publish immediately with post-hoc review or are held pending approval.
3. On a user report or DMCA/takedown, system records the case, can temporarily unpublish the listing pending review, and notifies the seller.
4. A moderator reviews evidence and takes action: approve, request changes, remove listing, suspend seller, or restore.
5. Confirmed copyright/DMCA takedowns remove the listing and may revoke access for fraudulently sold items (coordinated with CAP-08/CAP-09).
6. Repeat or severe violations trigger seller suspension or ban, which blocks publishing and payouts (CAP-11) per policy.
7. System maintains an audit trail of all moderation decisions.
8. **Error path**: If automated checks are unavailable, system falls back to manual review for new listings and flags a backlog risk.

**Outputs**:
- Moderation case record: case ID, target listing/seller, reason, evidence, decision, status, timestamps.
- Enforcement actions: listing hold/removal, seller suspension/ban, access revocation signals (to CAP-02, CAP-08, CAP-11).
- Notifications to affected sellers and reporting parties (CAP-13).
- Audit trail for compliance.

**Edge cases**:
- False/abusive takedown notices: system supports a counter-notice/appeal process before permanent removal.
- Seller suspended with an available balance and pending payouts: balance handling follows policy (held during investigation; released or withheld per outcome).
- Borderline content needing legal review: escalated beyond standard moderation.
- Mass-report brigading against a legitimate listing: system de-weights coordinated reports and requires moderator judgment.

**Connects to**: CAP-02, CAP-03, CAP-08, CAP-09, CAP-11, CAP-13

---

### CAP-13: Notifications

**Trigger**: An event in any other capability requires notifying a buyer, seller, or administrator.

**Inputs**:
- Notification event: event type (seller verified, listing approved/removed, purchase receipt, delivery ready, new review, refund/dispute update, chargeback, payout completed/failed, low stock, moderation action, etc.), target user ID, and payload, from any capability.
- User preferences: opted-in channels (email, in-app, push) and frequency (immediate vs. digest), from account settings.
- Contact info: email address and device tokens, from the user account system.

**Logic flow**:
1. System receives an event with type, target user, and payload.
2. System looks up the user's preferences for that event type.
3. In-app: creates a notification record in the user's inbox.
4. Email: renders the appropriate template and queues for delivery.
5. Push: constructs and sends the payload to registered devices.
6. System deduplicates per channel and batches into digests where the user prefers.
7. System logs deliveries for monitoring/analytics (CAP-12 dashboards).
8. **Error path**: On email bounce, system flags the address invalid and falls back to in-app only.

**Outputs**:
- In-app notification record (inbox item with action link, read state).
- Email message via the delivery service.
- Push notification to registered devices.
- Delivery log for monitoring.

**Edge cases**:
- User opted out of a channel for an event type: that channel is skipped.
- Critical notifications (payment failure, chargeback, payout failure, account/moderation actions): delivered regardless of marketing opt-out.
- Email unverified: email suppressed; in-app/push used until verified.
- Burst of events: batched into a digest if the user prefers.

**Connects to**: CAP-01, CAP-02, CAP-04, CAP-07, CAP-08, CAP-09, CAP-10, CAP-11, CAP-12, CAP-14

---

### CAP-14: Buyer and seller dashboards and analytics

**Trigger**: A buyer or seller opens their dashboard, or a scheduled report runs.

**Inputs**:
- User identity and role: from the account system.
- View/time-range selection: dashboard section and period (7/30/90 days, custom), from the user.
- Raw data sources: orders (CAP-07), entitlements/library (CAP-08), reviews (CAP-09), earnings ledger and payouts (CAP-10, CAP-11), listings (CAP-02), search/view analytics (CAP-05, CAP-06), moderation status (CAP-12).

**Logic flow**:
1. System determines the user's role and tailors the dashboard.
2. **Seller view**: active/draft listings, views and conversion per listing, units sold, gross sales, commissions paid, pending vs. available balance, payout history, ratings/reviews, low-stock alerts, and tax/earnings summaries.
3. **Buyer view**: purchased library with access links, order history and receipts, pending reviews, refund/dispute status.
4. System applies the time-range filter and computes totals, averages, and period-over-period changes.
5. System renders metrics as cards, charts, and lists; supports CSV/PDF export of the current view.
6. Scheduled reports run on the configured cadence and deliver via email (CAP-13).
7. **Error path**: If a data source is down, system shows last-cached data and marks it potentially stale.

**Outputs**:
- Dashboard display: role-tailored metrics and visualizations.
- Exported report: on-demand CSV/PDF.
- Scheduled report: recurring email delivery (CAP-13).
- Tax/earnings summary documents for sellers.

**Edge cases**:
- New account with no data: empty state with onboarding guidance (sellers: create a listing; buyers: browse the catalog).
- Earnings clearly separated into available, pending (clearing), and held (under review) so sellers understand payout timing.
- Large data volume: summary loads first, detailed breakdowns load asynchronously.
- Custom date range including future dates: capped at today.

**Connects to**: CAP-02, CAP-05, CAP-06, CAP-07, CAP-08, CAP-09, CAP-10, CAP-11, CAP-12, CAP-13

## Dependency Map

| Capability | Depends on | Feeds into |
|-----------|-----------|------------|
| CAP-01 Seller onboarding & payout setup | — | CAP-02, CAP-08, CAP-10, CAP-11, CAP-13 |
| CAP-02 Listing creation & lifecycle | CAP-01, CAP-03, CAP-04 | CAP-05, CAP-06, CAP-11(via moderation), CAP-12, CAP-14 |
| CAP-03 Asset upload, versioning, storage | CAP-02 | CAP-02, CAP-06, CAP-08, CAP-12 |
| CAP-04 Inventory, availability, licensing | CAP-02 | CAP-06, CAP-07, CAP-08, CAP-13 |
| CAP-05 Search & discovery | CAP-02, CAP-06 | CAP-06, CAP-07, CAP-14 |
| CAP-06 Product detail & preview | CAP-02, CAP-03, CAP-04, CAP-09 | CAP-05, CAP-07, CAP-08, CAP-14 |
| CAP-07 Cart, checkout, payment | CAP-04, CAP-06 | CAP-08, CAP-09, CAP-10, CAP-13, CAP-14 |
| CAP-08 Delivery & buyer library | CAP-03, CAP-04, CAP-07 | CAP-09, CAP-10, CAP-12, CAP-14 |
| CAP-09 Reviews, refunds, disputes, chargebacks | CAP-07, CAP-08 | CAP-05, CAP-06, CAP-10, CAP-11(holds), CAP-12, CAP-13, CAP-14 |
| CAP-10 Earnings ledger & commission | CAP-01, CAP-07, CAP-09 | CAP-11, CAP-14 |
| CAP-11 Seller payouts | CAP-01, CAP-09, CAP-10, CAP-12 | CAP-13, CAP-14 |
| CAP-12 Moderation, trust & safety | CAP-02, CAP-03, CAP-08, CAP-09 | CAP-02, CAP-08, CAP-11, CAP-13, CAP-14 |
| CAP-13 Notifications | CAP-01, CAP-02, CAP-04, CAP-07, CAP-08, CAP-09, CAP-10, CAP-11, CAP-12, CAP-14 | — |
| CAP-14 Dashboards & analytics | CAP-02, CAP-05, CAP-06, CAP-07, CAP-08, CAP-09, CAP-10, CAP-11, CAP-12 | CAP-13 |

## Open Questions

These reflect decisions a real interactive session would resolve with the user. Assumptions made for this run are noted.

- **One-time vs. subscription products** — Assumed one-time purchases only for MVP. Should recurring-access / subscription digital products be in scope?
- **Refund policy for consumed digital goods** — Assumed digital goods are non-returnable once the full deliverable is downloaded, with manual review for download-then-refund cases. What is the exact refund window and auto-approval threshold?
- **Earnings clearing/hold period** — Assumed a buyer-protection clearing window before pending earnings become available. How long (e.g., 7, 14, 30 days), and does it vary by seller risk tier?
- **License upgrade entitlement** — When a seller publishes a new version, do existing buyers get free upgrades, or only the version they purchased? Assumed: buyers keep the purchased version; upgrades governed by per-listing license terms.
- **Asset retention after seller/listing removal** — How long must the platform retain a purchased version so buyers keep access if the seller leaves? Assumed: retained per a defined retention policy.
- **Commission model** — Flat %, per-category, or tiered by volume? Assumed a configurable flat % with admin override. Are there listing or transaction fees in addition to commission?
- **Guest checkout** — Assumed buyers must have an account to maintain a library/entitlements. Is anonymous guest checkout required?
- **Tax handling (VAT/sales tax)** — Assumed the platform calculates and collects tax but does not remit/file on sellers' behalf. Who is the merchant of record, and what jurisdictions must be supported at launch?
- **Moderation mode** — Pre-publication approval (slower, safer) vs. post-publication review (faster supply growth)? Assumed configurable, defaulting to automated checks + post-hoc human review.
- **Region/geo restrictions** — Are sales region-restricted (per seller or platform policy), and is region-based pricing needed?

## Research Suggestions

The researcher skill is **not available** in this run. The following topics are flagged for it; do not research them here.

- **Chargeback and fraud mitigation for digital goods** — Digital goods are high-risk for "item not received" / "not as described" chargebacks since there is no shipment proof. Suggested researcher query: "Chargeback prevention and representment strategies for digital goods marketplaces — evidence types (delivery/access logs, license terms), friendly-fraud patterns, and seller liability models." (Informs CAP-07, CAP-09, CAP-10, CAP-11.)
- **Merchant-of-record and tax/VAT obligations** — Tax collection and merchant-of-record status materially affect checkout and payouts across jurisdictions. Suggested researcher query: "Merchant-of-record vs. marketplace facilitator models for global digital-goods sales — VAT/sales-tax collection and remittance obligations." (Informs CAP-07, CAP-10, CAP-14.)
- **Earnings hold / payout-timing benchmarks** — The clearing window balances buyer protection against seller cash flow and is a key trust lever. Suggested researcher query: "Payout clearing/hold periods on digital marketplaces — typical windows, risk-tiered holds, and seller-satisfaction trade-offs." (Informs CAP-10, CAP-11.)
- **Anti-piracy / content fingerprinting for digital assets** — Detecting plagiarized or pirated uploads protects rights holders and platform reputation. Suggested researcher query: "Content fingerprinting and duplicate-detection techniques for digital-asset marketplaces (images, audio, code, documents)." (Informs CAP-03, CAP-12.)
- **Commission/fee benchmarks for digital marketplaces** — Commission rate affects seller acquisition and GMV. Suggested researcher query: "Commission and fee structures across major digital-goods marketplaces by product category, and impact on seller supply and liquidity." (Informs CAP-10.)
- **Review-system integrity** — Preventing fake/retaliatory reviews and rating inflation for verified-purchase reviews. Suggested researcher query: "Verified-purchase review integrity for marketplaces — fake-review detection, retaliation prevention, and rating-inflation mitigation." (Informs CAP-09.)

## Next Steps

1. Resolve the high-impact Open Questions with stakeholders — especially refund policy, earnings clearing window, commission model, and merchant-of-record/tax stance — as these shape CAP-07, CAP-09, CAP-10, and CAP-11.
2. Have an agent with **librarian** access run the searches in "Existing Knowledge" to confirm whether prior research/specs exist, and incorporate them.
3. Commission the **researcher** skill on the flagged topics (chargeback/fraud, tax/MoR, payout timing) before finalizing payment and payout capabilities.
4. Define the launch listing categories, license types, and allowed file formats with stakeholders.
5. Prototype the core happy path end to end — list → publish → discover → buy → instant delivery → earnings accrual → payout — with one seller and one buyer to validate entitlement and ledger flows.
6. Draft platform policies (refunds, prohibited content, DMCA/takedown, seller agreement) that the dispute, moderation, and payout capabilities depend on.

---
*Capability breakdown produced by solution-architect skill. Use the librarian skill to persist this artifact.*
