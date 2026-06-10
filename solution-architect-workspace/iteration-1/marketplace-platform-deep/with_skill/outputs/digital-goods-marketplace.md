# Digital Goods Marketplace

> Solution Architect | Depth: deep | Generated: 2026-06-09

## Existing Knowledge

The librarian skill is **not available** in this run, so no prior artifacts could be loaded. Before building on this breakdown, an agent with librarian access should search for:

- **Category `researches`** — keywords: "digital goods marketplace", "two-sided marketplace trust & safety", "digital licensing models", "marketplace payouts and escrow". Most useful artifact types: market/competitor research, fraud-pattern research, payout-provider comparisons.
- **Category `specs`** — keywords: "seller onboarding", "checkout / payment flow", "license delivery", "payout schedule". Most useful: any existing functional spec for seller accounts, catalog, or checkout that would constrain scope here.
- **Category `docs`** — keywords: "platform fee policy", "refund policy", "content moderation guidelines", "tax / VAT handling". Most useful: business-policy docs that turn several Open Questions below into settled decisions.

Persisting this document is also a librarian task — see Next Steps.

## Problem Statement

- **Business problem**: The business wants to operate a two-sided marketplace for **digital goods** (downloadable or license-based products such as design assets, templates, e-books, audio, software plugins, stock media, etc.). The platform must attract sellers with a low-friction way to list and monetize digital products, and attract buyers with trustworthy discovery and instant, reliable fulfillment. The platform earns revenue by taking a commission on each sale. Without the platform, these transactions happen on fragmented channels with weak fulfillment guarantees, no fraud protection, and no centralized payout infrastructure.
- **User problem**:
  - *Buyers* need to discover relevant, trustworthy digital products, understand exactly what they're buying (format, license terms, what's included), pay securely, and receive their goods immediately and reliably — with recourse if a product is broken, misrepresented, or fraudulent.
  - *Sellers* need to list products quickly, manage their catalog and any quantity/license limits, set pricing, get discovered, and receive reliable payouts with clear visibility into earnings and fees.
- **Success criteria**:
  - ≥ 95% of paid orders deliver the digital good successfully on first attempt within seconds of payment.
  - Buyer-reported "did not receive / could not access" rate below 1% of orders.
  - Median time from buyer landing on a product page to completed purchase under 3 minutes.
  - Seller payout success rate above 98%; median time from sale to withdrawable funds within the published holding window.
  - Chargeback + refund rate below 2% of gross transaction volume.
  - Platform reaches a target of N completed transactions/month within 6 months of launch (target N to be set with stakeholders — see Open Questions).

## Scope

- **In scope**: Seller onboarding & seller accounts; product (digital good) listing creation & management; digital asset/file management and versioning; license & entitlement definition; inventory/quantity limits for limited-run or license-key products; catalog search & discovery; product detail & preview; cart & checkout; payment processing and platform fee deduction; instant digital fulfillment (secure download links / license-key issuance / entitlement grant); order management & buyer library ("my purchases"); refunds & chargeback handling; ratings & reviews; seller payouts & balance/ledger; content moderation & takedowns; multi-channel notifications; buyer and seller dashboards & analytics.
- **Out of scope (MVP, stated as assumptions)**: Physical goods or any shipping logistics; subscription/recurring-billing products (one-time purchases only for MVP); seller-to-seller transactions; affiliate/referral program; native mobile apps (responsive web only); buyer-to-buyer resale of purchased goods; in-platform messaging/chat between buyers and sellers (handled via support + reviews for MVP); tax remittance/withholding by the platform beyond collecting required tax info; multi-seller bundles.
- **Existing systems (assumed to be provided)**: User identity & authentication; a payment gateway supporting card payments, refunds, and payouts/transfers to sellers; a cloud object/file storage service for hosting digital assets; an email delivery service; a CDN for serving downloads.

### Key Assumptions (non-interactive run)

Because clarifying questions could not be asked, this breakdown assumes:
1. **Digital goods, one-time purchase.** Each product is a downloadable file set and/or a license/entitlement; no recurring billing.
2. **Three fulfillment types** are supported: (a) direct file download, (b) license-key issuance from a key pool, (c) entitlement/access grant (e.g., unlock streamable/hosted content). This covers the common digital-goods cases.
3. **"Inventory"** for digital goods means optional quantity limits — primarily finite license-key pools or intentionally limited editions; un-limited products are the default ("unlimited" stock).
4. **Escrow-lite / holding period** rather than per-transaction manual escrow: funds clear to the seller's withdrawable balance after a refund/chargeback holding window, given the instant-fulfillment nature of digital goods.
5. **Platform-wide refund policy** for MVP (no per-seller policies), with a defined refund window.
6. **Web-only, English MVP**; currency/localization handled by the payment gateway where possible.

These assumptions are surfaced as Open Questions where they materially affect design.

## Capabilities

### CAP-01: Seller onboarding and account setup

**Trigger**: A registered user chooses to "Become a seller" / "Start selling," or an existing seller edits their seller profile or payout details.

**Inputs**:
- User identity: authenticated user ID and account status, from the identity system.
- Seller profile data: display/store name, bio, profile image, contact email, and category specialties, entered by the user.
- Payout setup data: payout method details (bank account, PayPal, or equivalent) and the legal/tax identity required to receive payouts (legal name, country, tax form info), entered by the user.
- Agreement acceptance: acknowledgment of the seller terms, commission schedule, and content policy.

**Logic flow**:
1. System confirms the user's base account is verified (email confirmed) and in good standing.
2. System presents the seller setup flow: store profile, then payout/tax info, then agreement acceptance.
3. Seller enters store profile details; system validates uniqueness of the store name/handle.
4. Seller submits payout and tax identity info; system validates required fields for the seller's country.
5. System verifies the payout method with the payment gateway (e.g., account validation / micro-check) — this may complete asynchronously.
6. Seller accepts the seller agreement and commission schedule (the accepted version is recorded).
7. System activates the seller account, granting access to listing and catalog capabilities (CAP-02).
8. Until payout/tax verification completes, the seller may list and sell, but funds accumulate as **pending** and cannot be withdrawn (ties to CAP-13).
9. **Error path**: If payout verification fails, the seller account is still active for listing, but withdrawals are blocked and the seller is prompted to fix payout details.

**Outputs**:
- Seller account record: seller ID, store profile, payout/tax status, agreement version accepted, status (active/limited/suspended).
- Search-visible storefront profile (feeds CAP-04).
- Notification confirming seller activation or flagging incomplete payout/tax setup (CAP-12).

**Edge cases**:
- User in a country the payout provider does not support: system allows browsing/selling intent but blocks listing publication and explains the limitation.
- Store name collides with an existing or trademarked name: system rejects and requests an alternative.
- User attempts to re-onboard after a prior ban: system detects and blocks based on identity signals.
- Tax info incomplete at first payout time: withdrawal is held until completed.

**Connects to**: CAP-02, CAP-12, CAP-13, CAP-14

---

### CAP-02: Product listing creation and management

**Trigger**: An active seller opens "Create product" or edits/duplicates/unpublishes an existing product.

**Inputs**:
- Seller identity and standing, from CAP-01.
- Product metadata: title, description, category/tags, price (and optional sale price), license type selection (CAP-06), fulfillment type (download / license key / entitlement), preview media, and supported formats, entered by the seller.
- Associated assets: the deliverable file(s) or license-key pool reference, provided via CAP-03.
- Inventory settings: unlimited (default) or a finite quantity / key-pool size (CAP-07).
- Existing product data for edits, from the catalog repository.

**Logic flow**:
1. System verifies the seller account is active and permitted to publish.
2. System presents the product form, pre-filled if editing/duplicating.
3. Seller enters metadata, selects fulfillment type and license type, sets price and inventory mode, and attaches preview media.
4. Seller links the deliverable asset(s) (CAP-03) — required before publishing.
5. System auto-generates a unique product slug from the title.
6. Seller saves as draft or requests publish.
7. On publish, system enforces completeness (title, description, category, price, at least one deliverable asset, license type) and runs automated content checks (CAP-11). If checks pass, status becomes **published**; if flagged, status becomes **pending review**.
8. Published products are indexed for discovery (CAP-04).
9. Editing the deliverable of a live product creates a new asset version (CAP-03) without breaking existing buyers' access.
10. **Error path**: If slug conflicts, system appends a numeric suffix; if asset is missing/invalid, publish is blocked with a clear message.

**Outputs**:
- Product record: product ID, seller ID, metadata, price, fulfillment type, license type, inventory mode, status (draft/pending review/published/unpublished/suspended), version pointers, timestamps.
- Search index update (CAP-04).
- Seller notification of publish/draft/flag status (CAP-12).

**Edge cases**:
- Seller unpublishes a product that has been purchased: existing buyers retain access (via CAP-09); the product simply leaves discovery.
- Seller exceeds an account-tier listing cap: publish blocked with limit message.
- Price set to 0 (free product): allowed if business permits free goods; otherwise blocked (Open Question).
- Seller suspended mid-edit: saving blocked, redirected to account-status page.

**Connects to**: CAP-03, CAP-04, CAP-06, CAP-07, CAP-09, CAP-11

---

### CAP-03: Digital asset management and versioning

**Trigger**: A seller uploads, replaces, or removes a deliverable file/key-pool associated with a product (during CAP-02), or the system needs to serve an asset during fulfillment (CAP-09).

**Inputs**:
- Uploaded files: the actual digital deliverables (archives, documents, media, software), provided by the seller.
- License-key material: a list/pool of keys uploaded or generated, for key-based products.
- Asset metadata: file name, size, type, checksum, version label, provided by the seller or derived by the system.
- Product association: the product ID the asset belongs to, from CAP-02.

**Logic flow**:
1. Seller uploads a deliverable; system validates file type, size limits, and scans for malware/prohibited content.
2. System stores the asset privately (not publicly addressable) and records a checksum and version label.
3. For key-based products, system imports the key pool, deduplicates keys, and records the available count (feeds CAP-07).
4. When a seller replaces a deliverable, system stores it as a **new version** and keeps prior versions so existing entitlements remain valid; the seller chooses whether existing buyers get the update.
5. System links the current version to the product for future fulfillments.
6. On fulfillment requests (CAP-09), system issues a time-limited, access-controlled download URL or releases one license key from the pool — assets are never served via permanent public links.
7. **Error path**: If malware/prohibited content is detected, the asset is quarantined, the product cannot be published, and the seller is notified (escalates to CAP-11).

**Outputs**:
- Asset record(s): asset ID, product ID, version, storage reference, checksum, scan status, size/type.
- Key-pool record with available/consumed counts (feeds CAP-07).
- Secure, expiring fulfillment URLs or issued keys on demand (to CAP-09).

**Edge cases**:
- Upload interrupted/partial: system discards the incomplete upload and prompts retry; product cannot publish without a complete asset.
- Seller replaces an asset with a smaller/incomplete version: previous version retained; buyers are not silently downgraded.
- Key pool exhausted while product still marked available: triggers out-of-stock handling (CAP-07).
- Extremely large files: system enforces a per-file ceiling and advises splitting or external-host approach (Open Question on size limits).

**Connects to**: CAP-02, CAP-07, CAP-09, CAP-11

---

### CAP-04: Catalog search and discovery

**Trigger**: A buyer visits the marketplace, enters a search query, applies filters, browses a category, or views a storefront.

**Inputs**:
- Search query: free-text keywords, from the search bar.
- Filters: category, price range, license type, format/file type, rating minimum, "free/paid," sort order (relevance, price, rating, newest, best-selling), from filter controls.
- Buyer context: locale and (optional) past behavior, from session/identity.
- Product index: all published products with metadata and ranking signals, maintained by CAP-02.

**Logic flow**:
1. Buyer enters a query or selects a category/storefront.
2. System parses query into keywords/categories.
3. System matches against product titles, descriptions, tags, and seller store names.
4. System applies active filters and removes suspended/unpublished/out-of-stock products.
5. System ranks results using keyword relevance, rating, sales velocity, and listing completeness.
6. System returns paginated result summaries (title, seller, price, rating, format, cover/preview).
7. On zero results, system suggests broader terms or related categories.
8. System logs search/click events for analytics (CAP-15).
9. **Error path**: If the search index is unavailable, system falls back to a cached snapshot with reduced filtering and signals degraded results.

**Outputs**:
- Paginated search/browse results to the buyer.
- Search analytics events (CAP-15).
- No-result suggestions.

**Edge cases**:
- Misspelled query: fuzzy matching/spell correction applied.
- Contradictory filters (min price > max): invalid filter ignored with notice.
- Newly published product not yet indexed: appears after a short indexing delay; seller sees it in their own catalog immediately.
- Out-of-stock limited-edition product: shown as "sold out" rather than hidden, if business prefers (Open Question).

**Connects to**: CAP-02, CAP-05, CAP-15

---

### CAP-05: Product detail and preview

**Trigger**: A buyer clicks a product from search/browse, a storefront, a shared link, or a notification.

**Inputs**:
- Product ID and full product record, from CAP-02.
- Preview assets: sample images, watermarked previews, demo clips, or read-only excerpts, from CAP-03/CAP-02.
- Seller storefront summary: store name, rating, total sales, from CAP-01/CAP-14.
- Aggregate review data, from CAP-10.

**Logic flow**:
1. System loads the product record and verifies it is currently purchasable (published, in stock).
2. System renders product details: title, full description, price (and sale price if active), license terms summary (CAP-06), supported formats, what's included, and file size.
3. System renders previews appropriate to the fulfillment type (watermarked images, sample/demo, excerpt) without exposing the full deliverable.
4. System shows seller info and aggregated ratings/reviews (CAP-10).
5. System presents the primary call to action: "Buy now" / "Add to cart" (CAP-08).
6. If out of stock (limited product), the CTA is replaced with a "sold out" state.
7. **Error path**: If the product is unpublished/suspended after the link was shared, system shows a "no longer available" page and suggests similar products.

**Outputs**:
- Rendered product detail page to the buyer.
- Buy/add-to-cart entry point into CAP-08.
- Product view analytics event (CAP-15).

**Edge cases**:
- Preview asset missing: page renders without preview but notes "no preview available."
- Price changed between listing view and detail view: detail page reflects the current price authoritatively.
- Buyer already owns the product: CTA shows "View in your library" (CAP-09) instead of buy.

**Connects to**: CAP-02, CAP-06, CAP-08, CAP-09, CAP-10, CAP-15

---

### CAP-06: License and entitlement definition

**Trigger**: A seller selects/configures a license while creating a product (CAP-02); referenced again at fulfillment and in the buyer's library.

**Inputs**:
- License selection: a license template (e.g., personal use, commercial use, extended/multi-seat) chosen from platform-provided options, or a custom terms text, from the seller.
- Usage parameters: permitted use, seat/usage count, redistribution rules, from the seller within allowed bounds.
- Platform license policy: the set of allowed license templates and any mandatory clauses, from administrators.

**Logic flow**:
1. System presents the platform's standard license templates plus an optional custom-terms field.
2. Seller selects a template and sets any allowed parameters (e.g., number of seats for a commercial license).
3. System validates the chosen license against platform policy (no prohibited terms; required clauses present).
4. The license definition is attached to the product and summarized on the product page (CAP-05).
5. At purchase (CAP-08), the specific license terms in force at purchase time are snapshotted onto the order so the buyer's entitlement is fixed even if the seller later changes the listing.
6. **Error path**: If a custom license violates policy, publish is blocked with an explanation.

**Outputs**:
- License definition attached to the product.
- Per-order license snapshot stored with the buyer's entitlement (feeds CAP-09).
- License summary shown on the product page and in the buyer's library.

**Edge cases**:
- Seller changes license terms after sales exist: only future purchases use new terms; past buyers keep their snapshotted license.
- Buyer needs proof of license (e.g., for an audit): library provides a downloadable license certificate referencing the order.
- Conflicting parameters (e.g., "single seat" + "redistribution allowed"): system blocks the invalid combination.

**Connects to**: CAP-02, CAP-05, CAP-08, CAP-09

---

### CAP-07: Inventory and availability management

**Trigger**: A seller sets inventory mode (CAP-02), a purchase consumes a unit/key (CAP-08), a refund returns a unit, or a key pool runs low/empty (CAP-03).

**Inputs**:
- Inventory mode: unlimited (default) or finite quantity / key-pool-bound, from CAP-02.
- Stock count and key-pool availability, from CAP-03.
- Purchase/refund events that decrement/increment availability, from CAP-08 and CAP-12 (refunds).

**Logic flow**:
1. For unlimited products, availability checks always pass; no decrement occurs.
2. For finite-quantity or key-based products, system tracks remaining count.
3. At checkout (CAP-08), system reserves a unit/key for the duration of payment to prevent overselling.
4. On successful payment, the reservation is consumed and the remaining count decrements (and one key is allocated for key-based products).
5. On failed/abandoned checkout, the reservation is released back to availability.
6. When stock hits zero, the product is marked "sold out" in catalog (CAP-04) and detail (CAP-05).
7. On a refund (CAP-12) for a key-based product, system decides per policy whether to recycle the key back into the pool (default: do not recycle to avoid abuse; configurable).
8. System notifies the seller when stock is low or exhausted (CAP-12).
9. **Error path**: If two checkouts race for the last unit, the reservation step ensures only one succeeds; the loser is told it just sold out and offered alternatives.

**Outputs**:
- Authoritative availability/stock state per product (feeds CAP-04, CAP-05, CAP-08).
- Low-stock / sold-out notifications to the seller (CAP-12).
- Reservation records during checkout.

**Edge cases**:
- Seller increases stock or adds keys after sell-out: product returns to "available" and re-enters discovery.
- Key pool empties mid-checkout despite reservation logic (e.g., corrupted import): purchase is blocked and refunded if already charged; incident flagged.
- Unlimited product mistakenly set to finite 0: treated as sold out until corrected.

**Connects to**: CAP-02, CAP-03, CAP-04, CAP-05, CAP-08, CAP-12

---

### CAP-08: Cart, checkout, and payment

**Trigger**: A buyer clicks "Buy now" or proceeds to checkout from their cart.

**Inputs**:
- Cart contents: one or more product IDs with their current prices and license selections, from CAP-05.
- Buyer identity and billing details: authenticated buyer ID, billing/tax location, from identity and a checkout form.
- Payment method: card or stored payment method, from the buyer / payment gateway.
- Pricing inputs: product prices, any applicable taxes/VAT, platform/seller fee config (for fee accounting), discount/coupon codes if supported.
- Availability reservation: a confirmed reservation for finite/key products, from CAP-07.

**Logic flow**:
1. Buyer reviews the cart; system re-validates each item is still purchasable and re-fetches current prices.
2. System reserves stock/keys for finite products (CAP-07).
3. System computes order totals: item prices, applicable taxes, discounts, and the buyer-facing total; it also computes the per-item platform commission and seller net for accounting.
4. Buyer selects/enters a payment method and authorizes payment.
5. System charges the buyer's payment method via the payment gateway for the full order.
6. On success: system creates the order, snapshots license terms (CAP-06), records the financial split (platform fee vs. seller net) into the seller ledger as **pending** (CAP-13), consumes reservations (CAP-07), and immediately triggers fulfillment (CAP-09).
7. On payment failure: system releases reservations (CAP-07), marks the attempt failed, and offers retry with another method.
8. For multi-seller carts, the order is split into per-seller sub-orders so each seller's ledger and fulfillment are tracked independently.
9. **Error path**: If the charge succeeds but order creation/fulfillment cannot complete, reconciliation detects the orphaned charge and either completes fulfillment or auto-refunds (CAP-12).

**Outputs**:
- Order record(s): order ID, buyer ID, line items, per-seller split, prices, taxes, fees, status (paid/failed/refunded), timestamps.
- Payment receipt to the buyer (CAP-12).
- Pending ledger entries per seller (CAP-13).
- Fulfillment trigger (CAP-09).
- Reservation consumption/release (CAP-07).

**Edge cases**:
- Price changed between cart and checkout: system shows the new price and requires re-confirmation before charging.
- Buyer already owns a product in the cart: system warns and lets them remove it (re-buy allowed only if business permits, e.g., gifting — Open Question).
- Partial multi-item failure: each line item/sub-order succeeds or fails independently where the gateway allows; otherwise the whole order rolls back.
- Duplicate submit / double-click: idempotency prevents double charges for the same checkout attempt.
- Buyer's card later charged back: triggers CAP-12 chargeback handling and ledger reversal (CAP-13).

**Connects to**: CAP-05, CAP-06, CAP-07, CAP-09, CAP-12, CAP-13, CAP-15

---

### CAP-09: Digital fulfillment and buyer library

**Trigger**: An order is successfully paid (CAP-08); or a buyer later returns to access a previously purchased item ("my purchases").

**Inputs**:
- Paid order: order ID, buyer ID, line items, fulfillment types, license snapshots, from CAP-08/CAP-06.
- Deliverable references: current asset versions and/or key pool, from CAP-03.
- Buyer identity for access control, from the identity system.

**Logic flow**:
1. On a paid order, for each line item system determines the fulfillment type:
   - **Download**: generates a secure, time-limited, access-controlled download link bound to the buyer's entitlement.
   - **License key**: allocates one key from the pool (CAP-07/CAP-03) and assigns it to the order.
   - **Entitlement/access**: grants the buyer access to the hosted/streamable content.
2. System records an **entitlement** linking the buyer, product, order, license snapshot, and the granted asset version.
3. System delivers fulfillment immediately: shows the download/key/access on the post-purchase screen and via notification (CAP-12).
4. System adds the item to the buyer's permanent **library** ("my purchases"), where they can re-download (subject to fair-use limits), retrieve their key, view license terms, and download a receipt/license certificate.
5. Re-download requests re-validate the entitlement and re-issue a fresh expiring link; system enforces any reasonable per-period download-count limits to deter abuse.
6. If a seller publishes a new asset version and opted to share updates, library items reflect the new version (CAP-03).
7. If an entitlement is revoked due to refund/chargeback (CAP-12), access and re-download are disabled.
8. **Error path**: If fulfillment fails (asset missing, key pool empty), system retries; if still failing, it auto-refunds the line item (CAP-12) and alerts the seller and support.

**Outputs**:
- Entitlement record(s): buyer ID, product ID, order ID, license snapshot, asset version, status (active/revoked).
- Delivered download links / issued keys / access grants.
- Buyer library state ("my purchases").
- Fulfillment confirmation notification (CAP-12).

**Edge cases**:
- Buyer loses the link/email: library always provides re-access while the entitlement is active.
- Excessive re-downloads (potential sharing/abuse): system rate-limits and may flag the entitlement (CAP-11).
- Product removed from sale after purchase: buyer keeps access; the product just isn't re-purchasable.
- Key-based product, buyer's allocated key is later reported invalid: support can re-issue from the pool or escalate (CAP-12).

**Connects to**: CAP-03, CAP-06, CAP-07, CAP-08, CAP-10, CAP-11, CAP-12

---

### CAP-10: Ratings and reviews

**Trigger**: A buyer who has a fulfilled entitlement opts to review a product; or a review is edited/reported.

**Inputs**:
- Reviewer identity and proof of purchase (an active/past entitlement), from CAP-09.
- Review content: star rating (1–5), optional text, optional structured aspects (quality, accuracy of description, value), from a review form.
- Review policy config: eligibility window, edit window, from administrators.

**Logic flow**:
1. System verifies the reviewer purchased the product (verified-purchase only) and the review window is open.
2. Reviewer submits rating and optional text.
3. System runs automated content checks (CAP-11) on review text; clean reviews publish immediately, flagged ones go to moderation.
4. Published reviews attach to the product and to the seller's aggregate rating.
5. System recomputes the product's and seller's average rating and review counts (feeds CAP-04/CAP-05/CAP-14).
6. The seller may post one public response per review.
7. Reviewer may edit within the edit window; an edit history is retained.
8. **Error path**: Reviews flagged for prohibited content are withheld pending moderation.

**Outputs**:
- Review record: review ID, product ID, reviewer ID, order/entitlement ref, rating, text, aspects, status (published/flagged/removed), timestamps.
- Updated product and seller aggregate ratings.
- Review notification to the seller (CAP-12).

**Edge cases**:
- Reviewer refunded the product: review may be marked "refunded purchase" or removed per policy (Open Question).
- Rating manipulation (review rings, self-purchase to review own product): system detects unusual patterns and flags (CAP-11).
- Retaliatory/abusive review: seller can report; moderation adjudicates.
- No-text 1-star review: published; system encourages but does not require explanation.

**Connects to**: CAP-04, CAP-05, CAP-09, CAP-11, CAP-12, CAP-14

---

### CAP-11: Content moderation and trust & safety

**Trigger**: A product is published/edited (CAP-02), an asset is uploaded (CAP-03), a review is submitted (CAP-10), a user reports content, or automated risk signals fire.

**Inputs**:
- Submitted content: product metadata, deliverable assets, previews, reviews, store profiles.
- Automated signals: malware scan results, prohibited-content detection, plagiarism/duplicate-asset detection, abnormal sales/download/refund patterns, from CAP-03/CAP-08/CAP-09.
- User reports: reporter ID, target (product/seller/review), reason, evidence, from any user.
- Policy ruleset: prohibited content, IP/copyright rules, from administrators.

**Logic flow**:
1. On publish/upload/review, system runs automated checks (malware, prohibited content, obvious duplicates/IP signatures).
2. Clean items proceed; risky items are set to "pending review" or quarantined and queued for a moderator.
3. User reports create a moderation case with the gathered evidence.
4. A moderator reviews the case and decides: approve, request changes, unpublish/remove, suspend the seller, or escalate (e.g., copyright/DMCA process).
5. For removals, system unpublishes the product and may revoke fulfillment access depending on severity (coordinating with CAP-09).
6. Repeat or severe violations escalate to seller suspension/ban (affects CAP-01) and may freeze payouts (CAP-13).
7. System logs all moderation actions for audit and notifies affected parties (CAP-12).
8. **Error path**: If automated checks are unavailable, new publishes default to "pending review" rather than auto-publishing risky content.

**Outputs**:
- Moderation case records and decisions (audit log).
- Content state changes (published/pending/removed/quarantined).
- Seller account actions (warn/limit/suspend/ban) feeding CAP-01 and CAP-13.
- Notifications to reporters and affected sellers/buyers (CAP-12).

**Edge cases**:
- Legitimate product wrongly flagged: appeal path restores it; false-positive feedback tunes future checks.
- Copyright counter-notice: system follows a defined notice/counter-notice workflow before restoring.
- Mass-report abuse against a competitor: system weights reports and detects coordinated reporting.
- Removed product with existing buyers: entitlements handled per policy (keep access vs. revoke for severe IP/malware cases).

**Connects to**: CAP-01, CAP-02, CAP-03, CAP-09, CAP-10, CAP-12, CAP-13

---

### CAP-12: Refunds, chargebacks, and order support

**Trigger**: A buyer requests a refund within the refund window; a fulfillment failure auto-refunds (CAP-09); a card-issuer chargeback is received; or support intervenes on an order.

**Inputs**:
- Order/entitlement context: order ID, line items, amounts, fees, fulfillment status, from CAP-08/CAP-09/CAP-13.
- Refund request: reason category (not as described, broken/corrupt file, accidental purchase, fraud), description, from the buyer.
- Refund policy config: refund window, eligibility rules (e.g., download status), platform fee handling on refunds, from administrators.
- Chargeback notice: from the payment gateway.

**Logic flow**:
1. Buyer submits a refund request from their library/order; system checks eligibility (within window, policy conditions such as whether the file was downloaded).
2. For auto-approved cases (e.g., fulfillment failure, within a no-questions window), system refunds the buyer via the gateway immediately.
3. For discretionary cases, the request is routed to the seller and/or support for a decision within a response window; default outcome on non-response is defined by policy.
4. On approved refund: system reverses the buyer charge, revokes the entitlement (CAP-09), and reverses the corresponding ledger entries — clawing back the seller net and platform fee per policy (CAP-13). For key products, the key is not recycled by default (CAP-07).
5. On chargeback: system records the dispute, may freeze the disputed amount in the seller ledger (CAP-13), gathers evidence (order, fulfillment proof, download logs) and submits a representment via the gateway; outcome updates the order and ledger accordingly.
6. System notifies buyer and seller at each state change.
7. **Error path**: If a gateway refund fails, system retries and flags for manual finance handling; the buyer is kept informed.

**Outputs**:
- Refund/chargeback records: amount, reason, status (requested/approved/denied/refunded/won/lost), evidence bundle.
- Entitlement revocation (CAP-09).
- Ledger reversals/holds (CAP-13).
- Notifications to both parties (CAP-12 via CAP... see notifications below).
- Updated order status.

**Edge cases**:
- Buyer downloaded the full asset then requests refund: policy-dependent; flagged for abuse if a buyer repeatedly does this ("serial refunder").
- Chargeback on an already-refunded order: system reconciles to avoid double refund.
- Refund after payout already withdrawn: results in a negative seller balance handled by CAP-13 (recovered from future sales or via reverse transfer).
- Partial refund (multi-item order): only affected line items are reversed.

**Connects to**: CAP-07, CAP-08, CAP-09, CAP-11, CAP-13, CAP-14

---

### CAP-13: Seller ledger, balances, and fees

**Trigger**: A sale completes (CAP-08), a refund/chargeback occurs (CAP-12), a payout runs (CAP-14), the holding period elapses, or fee config changes.

**Inputs**:
- Sale split: gross amount, platform commission, taxes collected, seller net, from CAP-08.
- Reversals/holds: refund and chargeback adjustments, from CAP-12.
- Fee schedule: commission percentage and any fixed fees, holding-period length, from administrators/seller agreement (snapshotted at sale time).
- Payout events that debit the available balance, from CAP-14.

**Logic flow**:
1. On a completed sale, system posts a **pending** credit to the seller's ledger equal to the seller net (gross minus commission and taxes), using the fee schedule snapshotted at sale time.
2. Funds remain **pending** until the holding period (refund/chargeback risk window) elapses, then move to **available**.
3. Refunds/chargebacks post debits, reversing the corresponding pending or available amounts; if available funds are insufficient, the balance can go **negative** and is recovered from future earnings or via a reverse charge.
4. System maintains a running balance with three buckets: pending, available, and (during disputes) on-hold.
5. Moderation actions (CAP-11) can place a hold on the entire balance.
6. The ledger exposes a full, itemized transaction history per seller (feeds CAP-14 dashboards and statements).
7. **Error path**: Any discrepancy between gateway settlement reports and the internal ledger is surfaced to a reconciliation process for finance review.

**Outputs**:
- Ledger entries: per-transaction credits/debits with type, amount, fee breakdown, status, timestamps.
- Balance state: pending / available / on-hold per seller.
- Available-funds signal to CAP-14 when payout conditions are met.
- Earnings/statement data for CAP-15.

**Edge cases**:
- Fee schedule changes after a sale: the snapshotted fee at sale time governs that transaction.
- Currency mismatch between sale and payout currency: conversion handled and recorded at the relevant step.
- Negative balance at account closure: outstanding amount handled per the recovery policy.
- Tax-collected amounts: tracked separately and never paid out to the seller.

**Connects to**: CAP-01, CAP-08, CAP-11, CAP-12, CAP-14, CAP-15

---

### CAP-14: Seller payouts and withdrawals

**Trigger**: Available balance meets payout conditions (scheduled date reached or threshold met), or a seller manually requests a withdrawal.

**Inputs**:
- Available balance and payout currency, from CAP-13.
- Payout method and verified payout/tax status, from CAP-01.
- Payout configuration: schedule (automatic daily/weekly/monthly or manual), minimum threshold, from seller preference and platform default.

**Logic flow**:
1. System confirms the seller's payout method is verified and the account is not on hold (CAP-01/CAP-11).
2. System checks the available balance against the payout schedule and minimum threshold.
3. When conditions are met, system initiates a transfer of the available balance to the seller's payout method via the gateway, batching where it reduces fees.
4. System debits the available balance (CAP-13) and records a payout transaction with a gateway reference.
5. System notifies the seller with the amount and expected arrival time (CAP-12).
6. On failure (invalid account, gateway rejection), system holds funds, marks the payout failed, and prompts the seller to fix payout details.
7. System generates downloadable payout statements/receipts for the seller's records.
8. **Error path**: If payout/tax verification lapsed, withdrawals are blocked and the seller is repeatedly prompted to re-verify.

**Outputs**:
- Payout transaction record: seller ID, amount, method, gateway reference, status (pending/completed/failed), timestamp.
- Available-balance debit (CAP-13).
- Payout notification/statement to the seller (CAP-12, CAP-15).

**Edge cases**:
- No payout method set: funds accumulate; seller is periodically reminded.
- Below minimum threshold: funds accumulate until threshold is met.
- Seller changes payout method mid-payout: in-flight payout uses the original method; future payouts use the new one.
- Account suspended with positive balance: payout held pending resolution of the moderation/compliance case.

**Connects to**: CAP-01, CAP-11, CAP-12, CAP-13, CAP-15

---

### CAP-15: Notifications, dashboards, and analytics

**Trigger**: Any capability emits a notification-worthy event; or a buyer/seller opens their dashboard; or a scheduled report runs.

**Inputs**:
- Notification events: event type (purchase confirmed, fulfillment delivered, new sale, review received, refund/chargeback update, payout completed, low stock, moderation action, etc.), target user, payload, from any capability.
- User notification preferences and contact info, from the identity/account settings.
- Aggregatable data: orders (CAP-08), entitlements/library (CAP-09), reviews (CAP-10), ledger/payouts (CAP-13/CAP-14), catalog (CAP-02), search/views (CAP-04/CAP-05).
- Dashboard view + time-range filter, from the user's navigation.

**Logic flow**:
1. **Notifications**: on each event, system looks up the user's per-event-type preferences and delivers via in-app inbox and/or email; critical financial/compliance notices are always sent regardless of marketing opt-outs; duplicate channels are deduplicated; bounced emails fall back to in-app.
2. **Buyer dashboard**: shows the library/"my purchases," order history, active refund requests, and total spend.
3. **Seller dashboard**: shows sales (current/past periods), gross vs. net earnings, pending/available/on-hold balances, payout history, best-selling products, conversion (views→sales from CAP-04/CAP-05), ratings, low-stock alerts, and active moderation/dispute items.
4. System applies the selected time range and computes totals, averages, and period-over-period changes.
5. On export request, system generates a CSV/PDF of the current view (e.g., earnings statement, sales report).
6. Scheduled reports (e.g., weekly seller earnings summary) run on schedule and are emailed.
7. **Error path**: If a data source is temporarily unavailable, dashboards show last-known cached values and flag the data as possibly stale.

**Outputs**:
- In-app notifications, emails, and a delivery log.
- Rendered buyer/seller dashboards.
- On-demand and scheduled exported reports/statements.

**Edge cases**:
- New account with no data: dashboards show empty states with guided next steps (browse / create first product).
- User opts out of all channels for an event type: only non-critical notifications are suppressed.
- Rapid burst of events: optionally batched into a digest per the user's preference.
- Future-dated range requested: clamped to today.

**Connects to**: CAP-01, CAP-02, CAP-04, CAP-05, CAP-08, CAP-09, CAP-10, CAP-11, CAP-12, CAP-13, CAP-14

## Dependency Map

| Capability | Depends on | Feeds into |
|-----------|-----------|------------|
| CAP-01 Seller onboarding | — | CAP-02, CAP-13, CAP-14, CAP-15 |
| CAP-02 Product listing | CAP-01, CAP-03, CAP-06, CAP-07 | CAP-04, CAP-05, CAP-11, CAP-15 |
| CAP-03 Asset management | CAP-02 | CAP-02, CAP-07, CAP-09, CAP-11 |
| CAP-04 Search & discovery | CAP-02 | CAP-05, CAP-15 |
| CAP-05 Product detail/preview | CAP-02, CAP-03, CAP-06, CAP-10 | CAP-08, CAP-09, CAP-15 |
| CAP-06 License definition | CAP-02 | CAP-05, CAP-08, CAP-09 |
| CAP-07 Inventory | CAP-02, CAP-03 | CAP-04, CAP-05, CAP-08 |
| CAP-08 Checkout & payment | CAP-05, CAP-06, CAP-07 | CAP-09, CAP-12, CAP-13, CAP-15 |
| CAP-09 Fulfillment & library | CAP-03, CAP-06, CAP-07, CAP-08 | CAP-10, CAP-11, CAP-12, CAP-15 |
| CAP-10 Reviews | CAP-09 | CAP-04, CAP-05, CAP-11, CAP-14, CAP-15 |
| CAP-11 Moderation / T&S | CAP-02, CAP-03, CAP-09, CAP-10 | CAP-01, CAP-09, CAP-12, CAP-13, CAP-15 |
| CAP-12 Refunds & chargebacks | CAP-08, CAP-09, CAP-13 | CAP-07, CAP-09, CAP-13, CAP-15 |
| CAP-13 Ledger, balances, fees | CAP-08, CAP-11, CAP-12 | CAP-14, CAP-15 |
| CAP-14 Payouts | CAP-01, CAP-11, CAP-13 | CAP-12, CAP-15 |
| CAP-15 Notifications/dashboards | CAP-01, CAP-02, CAP-04, CAP-05, CAP-08, CAP-09, CAP-10, CAP-11, CAP-12, CAP-13, CAP-14 | — |

## Open Questions

These are decisions deferred because this was a non-interactive run; each materially affects design and should be confirmed with stakeholders.

- **Recurring vs. one-time.** Assumed one-time purchases only. Will the platform need subscriptions or recurring licenses (changes CAP-06, CAP-08, CAP-13)?
- **Fulfillment types in MVP.** Are all three (download, license key, hosted entitlement) needed at launch, or can MVP ship with downloads only (simplifies CAP-03, CAP-07, CAP-09)?
- **Refund policy for instant digital goods.** What is the refund window, and is a product refundable after it has been downloaded? This drives CAP-12 eligibility and abuse handling.
- **Holding period before payout.** How long do funds stay "pending" before becoming withdrawable (e.g., 7/14/30 days)? Balances chargeback risk vs. seller cash flow (CAP-13/CAP-14).
- **Commission structure.** Flat % across all categories, tiered by seller volume, or per-category? (CAP-13.)
- **Tax/VAT responsibility.** Does the platform act as merchant of record and remit taxes, or only collect seller tax info? Significant scope impact (CAP-08, CAP-13, CAP-01).
- **Free products.** Are $0 products allowed (affects CAP-02, CAP-08 fulfillment path with no payment)?
- **Multi-seller carts.** Supported at launch, or one seller per order for MVP (affects CAP-08 order splitting)?
- **Key recycling on refund.** Should refunded license keys return to the pool? Default assumed "no" (CAP-07/CAP-12).
- **Entitlement on takedown.** When a product is removed for IP/malware reasons, do existing buyers keep access? (CAP-09/CAP-11.)
- **Buyer↔seller messaging.** Assumed out of scope for MVP; confirm whether pre-sale questions need a contact channel.
- **Launch volume target (N).** The success-criteria transaction target needs a stakeholder-set number.

## Research Suggestions

Flagged for the **researcher skill** (this run did not conduct research):

- **Digital goods refund & abuse policies** — Refunds for instantly-downloadable goods invite "download-then-refund" abuse. Suggested researcher query: "Refund policies for digital download marketplaces — handling instant fulfillment, download-status gating, and serial-refunder abuse detection."
- **Payout holding periods and chargeback risk** — The pending→available window trades seller cash flow against fraud/chargeback exposure. Suggested researcher query: "Optimal payout holding periods for digital marketplaces — chargeback timing windows and seller cash-flow expectations."
- **License model design for digital assets** — Standard license templates (personal/commercial/extended/multi-seat) and enforceability. Suggested researcher query: "Common license tiers for digital asset marketplaces (templates, stock media, software) and how platforms present and enforce them."
- **Marketplace fraud for digital goods** — Stolen-card purchases, asset/IP theft, fake listings, review manipulation, key reselling. Suggested researcher query: "Fraud and trust-and-safety patterns for digital goods marketplaces — payment fraud, IP/copyright infringement, key resale, and detection strategies."
- **Commission/fee benchmarks** — What take rates are competitive for digital-goods categories. Suggested researcher query: "Commission/take-rate benchmarks for digital goods marketplaces by category (design assets, e-books, audio, software plugins)."
- **Merchant-of-record & tax/VAT obligations** — Whether the platform should be merchant of record for global digital sales (e.g., EU VAT/MOSS, US sales tax). Suggested researcher query: "Merchant-of-record vs. marketplace facilitator obligations for cross-border digital goods sales (VAT/sales tax)."
- **Secure digital delivery** — Best practices for expiring links, download-abuse prevention, and license-key distribution. Suggested researcher query: "Secure delivery patterns for paid digital downloads — expiring URLs, download rate-limiting, and license-key issuance."

## Next Steps

1. Resolve the high-impact Open Questions with stakeholders first: fulfillment types in MVP, refund policy, holding period, and tax/merchant-of-record stance — these reshape CAP-08, CAP-09, CAP-12, CAP-13.
2. Define the platform license-template catalog and content/IP policy (inputs to CAP-06 and CAP-11).
3. Specify the fee schedule and ledger states (pending/available/on-hold) end to end, including refund/chargeback reversal and negative-balance recovery (CAP-13).
4. Prototype the core happy path with one seller and one buyer: list → publish → buy → instant fulfillment → review → payout, to validate the fulfillment and ledger flows.
5. Define the notification event catalog and which events are in-app vs. email vs. critical-always (CAP-15).
6. Commission the flagged research topics via the researcher skill before finalizing refund, payout-timing, tax, and fraud-handling decisions.
7. **Persist this artifact**: the librarian skill was unavailable here. An agent with librarian access should save this document as a **spec** artifact (suggested keywords/tags: "digital goods marketplace", "two-sided marketplace", "capability breakdown", "seller payouts", "digital fulfillment") so it can be discovered and built upon.

---
*Capability breakdown produced by solution-architect skill. Use the librarian skill to persist this artifact.*
