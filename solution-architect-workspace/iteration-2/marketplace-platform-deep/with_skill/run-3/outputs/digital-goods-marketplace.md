# Digital Goods Marketplace

> Solution Architect | Depth: deep | Generated: 2026-06-09

> **Note on this run**: This breakdown was produced non-interactively. Where the skill
> would normally ask the user 2-4 questions per round, I have made reasonable, explicitly
> stated assumptions and recorded the most consequential ones in **Open Questions**. The
> librarian skill was not available, so existing knowledge could not be loaded — see the
> note below. The researcher skill was not available either, so research topics are flagged
> in **Research Suggestions** rather than investigated.

## Existing Knowledge

The librarian skill is **not available** in this run, so I could not search for or load
prior research, specs, or notes. Before this breakdown is treated as authoritative, an agent
with librarian access should check for existing artifacts to avoid duplicating work:

- **Category `researches`** — keywords: "digital goods marketplace", "two-sided marketplace
  trust and safety", "digital product licensing", "marketplace fraud / chargebacks", "VAT on
  digital goods". Would inform CAP-04, CAP-05, CAP-08, CAP-09, CAP-11.
- **Category `specs`** — keywords: "seller onboarding", "payout / KYC", "checkout flow",
  "license / entitlement model". Would set baseline scope for CAP-01, CAP-06, CAP-07, CAP-10.
- **Category `docs`** — keywords: "payment gateway integration", "tax engine", "content
  moderation policy", "notification event catalog". Would inform CAP-04, CAP-09, CAP-11, CAP-13.

If any of these exist, fold their findings in before implementation planning.

## Problem Statement

- **Business problem**: The business wants to operate a two-sided marketplace where independent
  sellers list and sell **digital goods** (e.g., templates, ebooks, design assets, audio,
  software, courses) and buyers discover and purchase them. The platform earns revenue by taking
  a commission on each sale. To be viable it must attract supply (sellers who trust they will be
  paid and protected from piracy/fraud) and demand (buyers who can find quality goods, pay
  securely, and reliably receive what they bought) simultaneously, while keeping fraud, chargebacks,
  piracy, and prohibited content low enough to stay solvent and compliant.
- **User problem**:
  - *Buyers* need to discover relevant, trustworthy digital goods, understand exactly what they
    are getting (license terms, format, compatibility), pay securely, and receive immediate,
    reliable access/download — with recourse if the product is broken, misrepresented, or never
    delivered.
  - *Sellers* need to list and price products, upload and update the underlying digital files,
    manage limited or licensed inventory (keys, seats, editions), get discovered, and receive
    timely, predictable payouts — while being protected from piracy, fraudulent buyers, and
    unjust chargebacks.
- **Success criteria**:
  - Checkout-to-delivery success rate ≥ 99% (buyer receives access within seconds of payment).
  - Catalog → purchase conversion and time-to-first-download tracked; median time from "buy" to
    "downloaded" under 60 seconds.
  - Dispute + chargeback rate below 1% of completed orders (digital goods are chargeback-prone).
  - Seller payout on-time rate ≥ 99%; seller satisfaction with payout reliability ≥ 90%.
  - < 0.5% of GMV attributable to fraud or prohibited/infringing content after moderation.
  - Reach a target of N completed orders/month and M active sellers within the first 6 months
    (specific targets to be set with stakeholders — see Open Questions).

## Scope

- **In scope**: Seller account/onboarding with payout + tax/KYC capture; product listing and
  digital file management; inventory/license management (unlimited, limited-quantity, and
  key/seat-based goods); catalog search and discovery; product detail and preview; cart and
  checkout; payment capture with platform commission; **digital delivery and entitlement**
  (download links, license keys, access grants); refunds and chargeback handling; reviews and
  ratings; buyer order history and re-download; seller dashboard (sales, earnings, balance);
  seller payouts; content moderation and takedown (DMCA / prohibited content); notifications;
  buyer and seller dashboards/analytics; platform admin oversight.
- **Out of scope (MVP)**: Physical goods or shipping logistics; subscriptions / recurring
  digital products (one-time purchases only for MVP); affiliate / referral program; native mobile
  apps (web-only); multi-currency seller payouts beyond the platform's base set (assume a small
  supported set); buyer-to-buyer resale of digital goods; in-platform editing tools for the goods
  themselves; tax *filing* on behalf of sellers (the platform may collect/remit marketplace VAT
  but does not file sellers' income taxes); white-label / enterprise tenancy.
- **Existing systems (assumed available, integrated not built here)**: User account &
  authentication system (handles login, sessions, roles); payment gateway (card + wallet
  processing, refunds, chargeback webhooks); object/file storage with secure time-limited URLs;
  email delivery service; a tax-rate / VAT determination service; a malware/AV scanning service
  for uploaded files. (These are assumptions for a non-interactive run; confirm with stakeholders.)

## Capabilities

### CAP-01: Seller onboarding and account setup

**Trigger**: A registered user opts to "Become a Seller," or an existing seller edits their
seller profile / payout settings.

**Inputs**:
- User identity: authenticated user ID and account status, from the user account system.
- Seller profile data: store/display name, bio, logo/banner, support contact, store URL slug,
  entered by the user via a form.
- Payout details: payout method (bank account / PayPal / supported provider) and currency,
  entered by the seller.
- Tax / identity data: legal name, country, tax residency / VAT ID, and any KYC information
  required to pay out (e.g., government ID for higher payout tiers), entered by the seller.

**Logic flow**:
1. System confirms the user's base account is active and verified (email verified).
2. System presents the seller onboarding form (profile, payout, tax/KYC).
3. Seller enters store profile; system validates the store slug for uniqueness and allowed characters.
4. Seller enters payout method; system validates format and (where supported) verifies the account
   via the payment gateway's onboarding flow.
5. Seller provides tax/identity info; system records tax residency and VAT/tax ID for later
   tax determination (CAP-09) and reporting.
6. System sets the seller's status: `active` (can list and sell) or `pending verification`
   (can list as draft but cannot publish / cannot be paid out) depending on whether required
   KYC/payout steps are complete.
7. System stores the seller record and grants the seller role/permissions.
8. **Error path**: If payout verification fails, the seller account is created but flagged
   "payouts blocked," and the seller is told what to fix; listing remains possible but payouts hold.

**Outputs**:
- Seller record: seller ID, store profile, payout method (tokenized/reference only), tax info,
  status, timestamps, stored in the seller account system.
- Role grant: seller permissions added to the user.
- Onboarding status notification to the seller (CAP-13).

**Edge cases**:
- Seller in an unsupported payout country: allow listing but block payouts and clearly state the limitation.
- Duplicate store slug: system suggests an available alternative.
- Seller later changes payout currency/country: re-trigger payout verification; in-flight payouts
  use the prior method (see CAP-08).
- User already a buyer with open disputes: onboarding allowed, but flagged for review.

**Connects to**: CAP-02, CAP-08, CAP-09, CAP-11, CAP-12, CAP-13

---

### CAP-02: Product listing and digital file management

**Trigger**: An active seller creates a new product, or edits/updates an existing product
(including uploading a new version of the underlying file).

**Inputs**:
- Seller identity: authenticated seller ID and status, from CAP-01.
- Listing metadata: title, description, category/tags, price (and currency), license terms
  (personal / commercial / extended), supported formats and compatibility notes, cover image and
  preview/sample assets, entered via a form.
- Digital file(s): the deliverable file(s) or archive the buyer receives, uploaded by the seller
  to secure storage.
- Inventory configuration: stock model (see CAP-03) — unlimited, limited quantity, or
  key/seat-based — entered by the seller.

**Logic flow**:
1. System verifies the seller is active and within their allowed product count.
2. Seller enters listing metadata and uploads the deliverable file(s) and preview assets.
3. Each uploaded file is sent to malware/AV scanning; files failing the scan are rejected.
4. System validates file type/size against limits and records file metadata (size, format, version).
5. Seller sets price, license terms, and inventory model (hands off inventory specifics to CAP-03).
6. System auto-generates a unique product slug from the title.
7. Seller chooses Save Draft or Publish; on Publish, system checks required fields (title,
   description, category, price, at least one deliverable file, at least one preview/cover) are present.
8. On Publish, the listing is queued for moderation if it matches risk heuristics (CAP-11);
   otherwise it is published and indexed for search (CAP-04).
9. Updating a file creates a new version; existing buyers may be offered the updated version
   (see CAP-07 re-download / entitlements).
10. **Error path**: If a slug conflicts, append a numeric suffix; if AV scan is pending, keep the
    listing in "processing" and publish only after the scan passes.

**Outputs**:
- Product record: product ID, seller ID, metadata, license terms, price, file references &
  versions, status (draft/processing/published/under-review/suspended), timestamps.
- Search index update for published products (CAP-04).
- Seller notification of save/publish/rejection (CAP-13).

**Edge cases**:
- Deliverable file exceeds size limit: reject with guidance (e.g., split or use allowed archive).
- AV scan flags the file: block publish, notify seller, log for moderation.
- Seller deletes a product that has been purchased: listing is unpublished but the product record
  and files are retained so prior buyers keep access (CAP-07); not hard-deleted.
- Seller edits price while items are in buyers' carts: price at checkout is locked when the buyer
  begins payment (CAP-06).

**Connects to**: CAP-03, CAP-04, CAP-05, CAP-06, CAP-07, CAP-11, CAP-12

---

### CAP-03: Inventory and license/entitlement management

**Trigger**: A seller configures stock for a product (CAP-02), or an order consumes inventory
(CAP-06), or stock is replenished/adjusted by the seller.

**Inputs**:
- Stock model: `unlimited` (infinite copies of a downloadable file), `limited quantity`
  (a finite number of sellable units, e.g., limited edition), or `key/seat-based` (a pool of unique
  license keys or activation seats), set by the seller.
- Key/seat pool (for key-based goods): a list of unique license keys or a generation rule,
  provided/uploaded by the seller.
- Consumption events: confirmed orders that decrement available stock, from CAP-06.
- Adjustment events: manual stock add/remove by the seller.

**Logic flow**:
1. System records the stock model for the product.
2. For `limited quantity`: system maintains an available count and decrements it on each confirmed sale.
3. For `key/seat-based`: system maintains a pool of unallocated keys; on sale it reserves and then
   allocates one key to the order at delivery time (CAP-07).
4. For `unlimited`: no decrement; the same file is delivered to every buyer.
5. When available stock for a limited/keyed product reaches zero, the product is marked
   "sold out" and hidden from purchase (still visible as out-of-stock per seller preference).
6. At checkout, system reserves stock for the duration of the payment attempt to prevent overselling.
7. If payment fails or is abandoned, the reserved stock/key is released back to the pool.
8. Seller can replenish keys or increase quantity, which reactivates the product for sale.
9. **Error path**: If two checkouts race for the last unit, the first to confirm payment wins; the
   second is told the item just sold out and (for refundable cases) is not charged or is auto-refunded.

**Outputs**:
- Inventory state: per-product available count and/or key pool status (allocated/unallocated).
- Reservation records tied to in-progress orders (with expiry).
- Allocated entitlement reference handed to CAP-07 at delivery.
- Low-stock / sold-out notifications to the seller (CAP-13).

**Edge cases**:
- Key pool exhausted while orders are pending: pending orders without an allocated key are held
  and either fulfilled on replenishment or refunded after a timeout.
- Seller uploads duplicate keys: system de-duplicates and warns the seller.
- Limited-quantity product refunded after sale (CAP-08): the unit is returned to stock only if the
  seller's policy allows; keys are generally not returned to the pool (treated as burned).

**Connects to**: CAP-02, CAP-06, CAP-07, CAP-08, CAP-12

---

### CAP-04: Catalog search and discovery

**Trigger**: A buyer visits the marketplace, enters a search query, applies filters, or browses
a category / curated collection.

**Inputs**:
- Search query: free-text keywords, from the search bar.
- Filter/sort parameters: category, price range, format/compatibility, license type, minimum
  rating, sort order (relevance, price, rating, newest, best-selling).
- Buyer context: locale/currency, prior views/purchases (for relevance/recommendations).
- Listing index: all published products with metadata, ratings, and sales signals, from CAP-02 and CAP-10.

**Logic flow**:
1. Buyer searches or browses a category/collection.
2. System parses the query into keywords, categories, and attributes.
3. System matches against product titles, descriptions, tags, and seller/store names.
4. System applies active filters and computes relevance using keyword match, rating, sales
   velocity, and listing completeness.
5. System sorts per the selected order (default: relevance) and returns paginated result summaries
   (title, price in buyer's currency, rating, cover, seller).
6. Prices are displayed in the buyer's locale currency using the platform's display conversion.
7. On zero results, system suggests related categories or broader terms.
8. System logs query, filters, results, and click-throughs for analytics (CAP-12).
9. **Error path**: If the search index is degraded, fall back to a cached snapshot with reduced
   filtering and a "results may be incomplete" notice.

**Outputs**:
- Paginated search results / category pages shown to the buyer.
- Search analytics events (CAP-12).
- "No results" suggestions.

**Edge cases**:
- Misspelled query: apply fuzzy matching / spell correction.
- Contradictory filters (min price > max): ignore the invalid filter and notify.
- Suspended/under-review products: excluded from results immediately.
- Region-restricted products (if a seller restricts sale by geography): hidden or marked
  unavailable for buyers in excluded regions.

**Connects to**: CAP-02, CAP-05, CAP-06, CAP-10, CAP-12

---

### CAP-05: Product detail, preview, and reviews display

**Trigger**: A buyer opens a product detail page from search, a collection, a store page, or a direct link.

**Inputs**:
- Product reference: product ID, from the link/result.
- Product data: full metadata, license terms, formats, version, price, preview/sample assets, from CAP-02.
- Social proof: rating, review count and review content, from CAP-10; seller reputation, from CAP-01/CAP-10.
- Inventory state: in-stock / sold-out, from CAP-03.

**Logic flow**:
1. System loads the published product and its current version metadata.
2. System renders title, full description, license terms, formats/compatibility, price in buyer's
   currency, cover, and previews/samples (watermarked or partial so the buyer can evaluate without
   getting the full deliverable).
3. System shows aggregate rating, individual reviews, and seller info/store link.
4. System shows availability from CAP-03 (Buy / Add to cart, or Sold out).
5. System exposes "report this listing" for prohibited/infringing content (feeds CAP-11).
6. **Error path**: If the product is unpublished/suspended after the link was shared, show a
   "no longer available" state and suggest similar products (CAP-04).

**Outputs**:
- Rendered product detail page to the buyer.
- "Add to cart" / "Buy now" action feeding CAP-06.
- Report event feeding CAP-11.
- View analytics event (CAP-12).

**Edge cases**:
- Preview asset missing: show metadata-only with a notice; never expose the actual deliverable as a preview.
- Buyer already owns the product: show "You own this — download" linking to CAP-07 instead of Buy.
- Region-restricted for the buyer: show unavailable state.

**Connects to**: CAP-02, CAP-04, CAP-06, CAP-07, CAP-10, CAP-11, CAP-12

---

### CAP-06: Cart, checkout, and payment

**Trigger**: A buyer clicks "Buy now" or proceeds to checkout from the cart.

**Inputs**:
- Cart contents: one or more products with their locked prices and license terms, from CAP-05.
- Buyer identity: authenticated buyer ID and billing/location info (country for tax), from the
  user account system; guest checkout may capture email + country.
- Payment method: card or wallet, entered or selected from saved methods.
- Tax determination: applicable VAT/sales tax for the buyer's location and product type, from the
  tax service (CAP-09).
- Commission config: platform commission % and any fixed fees, set by admins.

**Logic flow**:
1. System assembles the cart and re-validates each item: still published, in stock (reserve via CAP-03),
   and locks the current price.
2. System determines tax for the buyer's location/product type (CAP-09) and computes the order total:
   item prices + tax (+ any platform-borne fees disclosed appropriately).
3. System shows the buyer a full breakdown: per-item price, tax, total, and license terms acceptance.
4. Buyer authorizes payment; system processes the charge through the payment gateway.
5. On success, system creates a confirmed order, splits the amount conceptually into platform
   commission and seller proceeds (seller proceeds credited to the seller's pending balance — see CAP-08),
   and finalizes the stock decrement / key allocation via CAP-03.
6. System immediately triggers digital delivery / entitlement creation (CAP-07).
7. System emits notifications to buyer (receipt) and seller (new sale) via CAP-13.
8. On payment failure, system releases reserved stock (CAP-03), keeps the cart, and offers retry.
9. **Error path**: If the gateway confirms the charge but the system fails before recording the order,
   a reconciliation process detects the orphaned charge and either completes the order (delivering the
   goods) or auto-refunds, ensuring the buyer is never charged without delivery.

**Outputs**:
- Order record: order ID, buyer ID, line items (product, seller, price, license), tax, total,
  commission split, status (paid/failed/refunded/disputed), timestamps, stored in the order system.
- Payment confirmation / receipt to the buyer (CAP-13).
- Seller pending-balance credit (CAP-08).
- Delivery trigger to CAP-07.
- Stock consumption to CAP-03.

**Edge cases**:
- Multi-seller cart: a single payment is split across multiple sellers' proceeds; if one item is
  out of stock at checkout, that line is removed and the buyer is notified before charging.
- Price changed between add-to-cart and checkout: the price locked at checkout start is honored.
- Buyer's payment flagged as high fraud risk: order held for review (CAP-11) before delivery, or
  declined.
- Buyer in a tax jurisdiction the platform cannot determine: fall back to a default rule and flag
  for finance review.

**Connects to**: CAP-03, CAP-05, CAP-07, CAP-08, CAP-09, CAP-11, CAP-13

---

### CAP-07: Digital delivery, entitlements, and re-download

**Trigger**: An order is paid (CAP-06), or a buyer returns to access a previously purchased product,
or a seller publishes a new version of a purchased product.

**Inputs**:
- Confirmed order: order ID, buyer ID, purchased product(s) and versions, license terms, from CAP-06.
- Deliverable reference: file reference/version and any allocated license key/seat, from CAP-02 and CAP-03.
- Buyer access request: authenticated buyer requesting a download or access link, from the buyer's library.

**Logic flow**:
1. On order paid, system creates an **entitlement** record linking the buyer to the product, version,
   license terms, and any allocated key/seat (from CAP-03).
2. System generates secure, time-limited download links (and/or reveals the license key / grants access).
3. System delivers access: shows it in the buyer's library/order page and includes it in the receipt
   (CAP-13).
4. Buyer can re-download from their library at any time while the entitlement is valid; each request
   generates a fresh time-limited link.
5. System enforces reasonable download limits/throttling per entitlement to deter sharing/piracy
   (e.g., N downloads per day) without harming legitimate re-downloads.
6. If the seller publishes a new file version, system flags the entitlement so the buyer can fetch the
   updated version (per the platform's update policy).
7. If an order is refunded or charged back (CAP-08) or removed for infringement (CAP-11), the
   entitlement is revoked and links stop working.
8. **Error path**: If link generation fails or storage is unavailable, system retries and shows the
   buyer a "preparing your download" state; the entitlement remains valid so no purchase is lost.

**Outputs**:
- Entitlement record: buyer ID, product/version, license terms, allocated key/seat, status
  (active/revoked), download counters, stored in the entitlements system.
- Secure download links / revealed keys / access grants to the buyer.
- Delivery confirmation event (feeds CAP-13 and CAP-12).

**Edge cases**:
- Buyer loses the deliverable and re-downloads after the seller updated the file: serve the version
  the buyer is entitled to (latest by default, with access to the purchased version if policy requires).
- Excessive download attempts (possible credential sharing): throttle and flag for review (CAP-11).
- Key-based product but no key was available at payment (CAP-03 exhaustion): hold delivery, notify
  buyer, fulfill on replenishment or auto-refund after timeout.
- Entitlement revoked due to chargeback: links die immediately; buyer notified.

**Connects to**: CAP-02, CAP-03, CAP-06, CAP-08, CAP-11, CAP-12, CAP-13

---

### CAP-08: Refunds, chargebacks, and dispute handling

**Trigger**: A buyer requests a refund; or the payment gateway sends a chargeback notification; or a
seller approves/initiates a refund; or a dispute is escalated to platform mediation.

**Inputs**:
- Refund request: order ID, line item(s), reason (not as described, broken file, didn't receive,
  duplicate purchase), from the buyer.
- Order & delivery context: order record (CAP-06), entitlement/download history (CAP-07), and any
  messages/evidence.
- Chargeback notice: gateway webhook with order reference, amount, and reason code.
- Refund policy: platform + seller refund rules (digital-goods policy, windows, eligibility), set by
  admins/sellers.

**Logic flow**:
1. Buyer submits a refund request from their order; system checks eligibility against the refund
   policy and whether the goods were downloaded/accessed (key signal for digital goods).
2. For clear-cut cases (e.g., never downloaded within window, duplicate charge), system can auto-approve
   and refund from the seller's proceeds / platform balance, and revoke the entitlement (CAP-07).
3. For contested cases, system notifies the seller, who may approve, partially refund, or contest with
   evidence within a response window.
4. If buyer and seller disagree, the case escalates to a platform mediator, who reviews delivery logs,
   download history, previews, and messages, then issues a binding decision (full/partial/no refund).
5. On a refund, system reverses the payment (full or partial) through the gateway, debits the seller's
   balance accordingly, adjusts platform commission, revokes/limits the entitlement, and (per CAP-03
   policy) handles inventory/key return.
6. On a **chargeback**, system freezes the corresponding seller proceeds, revokes the entitlement,
   gathers delivery evidence, and (where the seller wishes) submits representment to the gateway;
   outcome updates balances accordingly.
7. System tracks per-buyer and per-seller refund/chargeback rates to feed fraud signals (CAP-11).
8. **Error path**: If a refund to the original method fails (expired card), system records a credit owed
   and notifies finance for manual handling.

**Outputs**:
- Refund/dispute record: case ID, order, reason, status (open/seller-responded/escalated/resolved),
  outcome, stored in the dispute system.
- Payment reversal / representment instruction to the gateway.
- Balance adjustments to the seller (CAP-08↔CAP-up: seller balance) and commission adjustments.
- Entitlement revocation (CAP-07) and inventory handling (CAP-03).
- Notifications to both parties (CAP-13); fraud signals to CAP-11.

**Edge cases**:
- Buyer downloaded then requests refund claiming non-receipt: download logs (CAP-07) are decisive evidence.
- Chargeback on an order already refunded: reconcile to avoid double reversal.
- Serial refunder buyer: pattern flagged (CAP-11); future purchases may require review.
- Refund requested after seller already paid out (CAP-08 payout): recover from future proceeds or
  flag negative balance for collection.

**Connects to**: CAP-03, CAP-06, CAP-07, CAP-09 (seller balance/payout), CAP-11, CAP-13

---

### CAP-09: Tax determination and marketplace tax handling

**Trigger**: A buyer reaches checkout (CAP-06); or a payout/period close requires tax reporting data.

**Inputs**:
- Transaction context: buyer location/country, product type (digital good), seller tax residency,
  amount, from CAP-06 and CAP-01.
- Tax rules: VAT/GST/sales-tax rates and digital-goods rules by jurisdiction, from the tax service.
- Platform tax role config: where the platform acts as marketplace facilitator (collect & remit) vs.
  where the seller is responsible, set by admins.

**Logic flow**:
1. At checkout, system sends buyer location and product type to the tax service to determine the
   applicable tax rate and treatment for digital goods.
2. System computes tax, adds it to the order total, and records the tax breakdown on the order (CAP-06).
3. System records whether the platform is collecting/remitting (marketplace facilitator) or the
   seller bears the obligation, per jurisdiction config.
4. System accumulates collected tax and transaction records for reporting periods.
5. At period close, system produces tax summaries for the platform's remittance and per-seller tax
   reports/statements (income for payouts is reported separately).
6. **Error path**: If the tax service is unavailable, system applies a conservative default rate, flags
   the order for finance reconciliation, and never blocks the sale.

**Outputs**:
- Per-order tax breakdown stored on the order.
- Collected-tax ledger for platform remittance.
- Per-seller tax/earnings statements (feeds CAP-12 dashboards and CAP-08 records).

**Edge cases**:
- Buyer provides a valid business VAT ID (reverse charge): tax handled per B2B rules.
- Jurisdiction with thresholds the platform hasn't crossed: config determines collection on/off.
- Buyer's stated country conflicts with payment/location signals: flag potential location fraud (CAP-11).

**Connects to**: CAP-01, CAP-06, CAP-08, CAP-12

---

### CAP-10: Reviews and ratings

**Trigger**: A buyer who has a completed purchase (paid, delivered, past any immediate refund window)
chooses to review a product; or a review is edited/reported.

**Inputs**:
- Purchase proof: entitlement/order linking the reviewer to the product, from CAP-06/CAP-07.
- Review content: star rating (1-5), optional text, optional attribute ratings (quality, value,
  accuracy of description), from the buyer.
- Review policy: eligibility window and content rules, set by admins.

**Logic flow**:
1. System verifies the reviewer actually purchased the product (verified-purchase reviews only).
2. Buyer submits a rating and optional text.
3. System scans content for prohibited material (PII, hate speech) and either publishes or holds for
   moderation (CAP-11).
4. System publishes the review, associates it with the product and seller, and recalculates the
   product's average rating, review count, and the seller's aggregate reputation.
5. Seller may post a single public response per review.
6. Buyer may edit within a short window (e.g., 48h) with edit history retained.
7. **Error path**: Content flagged by moderation is held until reviewed; rating is not counted until published.

**Outputs**:
- Review record: review ID, order/entitlement ref, product, seller, rating, text, status, timestamps.
- Updated product rating and seller reputation (feeds CAP-04 ranking, CAP-05 display).
- Review notification to the seller (CAP-13).

**Edge cases**:
- Review without verified purchase: rejected.
- Coordinated fake positive reviews (review bombing/inflation): pattern detection flags for review (CAP-11).
- Retaliatory review after a refund dispute: allowed but flagged; mediator can remove if policy violated.
- Self-review (seller buying own product): blocked via identity/payment-link checks.

**Connects to**: CAP-04, CAP-05, CAP-06, CAP-07, CAP-11, CAP-12, CAP-13

---

### CAP-11: Content moderation, trust, and fraud prevention

**Trigger**: A listing is published or flagged by heuristics (CAP-02); a user reports a listing/review
(CAP-05/CAP-10); a takedown/DMCA notice is received; or fraud signals fire from orders/refunds
(CAP-06/CAP-08).

**Inputs**:
- Moderation queue items: listings, reviews, files, or accounts flagged by heuristics, reports, or
  AV scan results.
- Reports: reporter identity, target, reason (infringement, prohibited content, scam), evidence.
- Takedown notices: complainant info, claimed work, target listing (DMCA-style).
- Fraud signals: chargeback/refund rates, location mismatches, velocity anomalies, download-abuse
  patterns, from CAP-06/CAP-07/CAP-08/CAP-09.

**Logic flow**:
1. System aggregates flagged items into a moderation queue with severity scoring.
2. Automated checks run first (AV results, banned-term matches, known-bad hashes); high-confidence
   violations can auto-suspend a listing pending review.
3. A moderator reviews queued items and decides: approve, request changes, suspend listing, remove
   content, warn/suspend/ban account, or revoke entitlements (coordinating with CAP-07/CAP-08).
4. For takedown notices, system suspends the listing, notifies the seller, and supports a counter-notice
   workflow; repeat infringers are escalated to account suspension.
5. Fraud signals can trigger order holds (before delivery in CAP-06), step-up verification, or payout
   holds (CAP-08).
6. All actions are logged with reason for auditability and appeals.
7. **Error path**: If automated scanning is unavailable, new listings requiring scanning stay in
   "processing" rather than publishing unscanned.

**Outputs**:
- Moderation decisions: status changes to listings/reviews/accounts, with logged reasons.
- Suspension / takedown / ban actions feeding CAP-02, CAP-04, CAP-07, CAP-08.
- Notifications to affected parties and complainants (CAP-13).
- Audit log for compliance.

**Edge cases**:
- False/abusive reports to harm a competitor seller: reporter reputation tracked; abusive reporting penalized.
- Counter-notice to a takedown: listing may be reinstated per policy/timeline.
- Borderline content needing legal review: escalated rather than auto-decided.
- Seller's whole catalog implicated: bulk suspend with single notice and appeal path.

**Connects to**: CAP-02, CAP-04, CAP-05, CAP-06, CAP-07, CAP-08, CAP-10, CAP-13

---

### CAP-12: Seller and buyer dashboards and analytics

**Trigger**: A seller or buyer opens their dashboard; or a scheduled report runs.

**Inputs**:
- User identity and role, from the user account system.
- View + time-range selection, from the user.
- Source data: orders (CAP-06), entitlements/downloads (CAP-07), payouts/balance (CAP-08),
  refunds/disputes (CAP-08), reviews (CAP-10), tax/earnings (CAP-09), listings/inventory (CAP-02/CAP-03).

**Logic flow**:
1. System tailors the dashboard to the role.
2. **Seller view**: sales count and GMV, net earnings after commission/refunds, pending vs. available
   vs. paid-out balance, best-selling products, conversion from views, ratings, inventory/low-stock,
   open disputes, and downloadable earnings/tax statements.
3. **Buyer view**: purchase history / library with re-download links (CAP-07), spend over time, open
   refund/dispute cases, pending reviews to leave.
4. System aggregates over the selected period and computes period-over-period changes.
5. System supports CSV/PDF export and optional scheduled email reports (CAP-13).
6. **Error path**: If a source is unavailable, show cached values with a "may be stale" indicator.

**Outputs**:
- Rendered dashboards and visualizations.
- On-demand exports and scheduled reports (via CAP-13).

**Edge cases**:
- New seller/buyer with no data: empty-state guidance (list a product / browse catalog).
- Clear separation of pending (in dispute window/escrow-like hold), available, and paid-out balances.
- Large data volume: load summaries first, details async.

**Connects to**: CAP-02, CAP-03, CAP-06, CAP-07, CAP-08, CAP-09, CAP-10, CAP-13

---

### CAP-13: Notification system

**Trigger**: Any capability emits an event needing to reach a buyer, seller, or admin (sale,
delivery, payout, refund/chargeback, dispute, review, moderation action, low stock, onboarding status).

**Inputs**:
- Notification event: type, target user, and payload, from any capability.
- User preferences: opted-in channels (email, in-app, push) and frequency (immediate/digest), from
  account settings.
- Contact info: email / device tokens, from the user account system.

**Logic flow**:
1. System receives an event and looks up the target's preferences for that event type.
2. In-app: create an inbox record. Email: render the template and queue delivery. Push: send to devices.
3. Deduplicate across channels and batch into digests where the user prefers.
4. Log delivery for analytics/monitoring.
5. **Error path**: On email bounce, flag the address and fall back to in-app only.

**Outputs**:
- In-app notification records, emails, push messages.
- Delivery logs (feeds CAP-12 monitoring).

**Edge cases**:
- User opted out of a category: suppress non-critical; **never** suppress critical transactional or
  legal notices (receipts, payout failures, chargebacks, takedowns) regardless of preference.
- Unverified email: suppress email, use in-app/push until verified.
- Burst of events: collapse into a digest where allowed.

**Connects to**: CAP-01, CAP-02, CAP-03, CAP-06, CAP-07, CAP-08, CAP-09, CAP-10, CAP-11, CAP-12

---

## Dependency Map

| Capability | Depends on | Feeds into |
|-----------|-----------|------------|
| CAP-01 Seller onboarding | — | CAP-02, CAP-08, CAP-09, CAP-13 |
| CAP-02 Listing & files | CAP-01 | CAP-03, CAP-04, CAP-05, CAP-06, CAP-07, CAP-11, CAP-13 |
| CAP-03 Inventory/license | CAP-02 | CAP-06, CAP-07, CAP-08 |
| CAP-04 Search & discovery | CAP-02, CAP-10 | CAP-05, CAP-06 |
| CAP-05 Product detail/preview | CAP-02, CAP-04, CAP-10 | CAP-06, CAP-07, CAP-11 |
| CAP-06 Cart/checkout/payment | CAP-02, CAP-03, CAP-05, CAP-09 | CAP-07, CAP-08, CAP-10, CAP-11, CAP-13 |
| CAP-07 Delivery/entitlement | CAP-02, CAP-03, CAP-06 | CAP-08, CAP-10, CAP-11, CAP-12, CAP-13 |
| CAP-08 Refunds/chargebacks/payouts | CAP-01, CAP-03, CAP-06, CAP-07, CAP-09 | CAP-03, CAP-07, CAP-11, CAP-12, CAP-13 |
| CAP-09 Tax | CAP-01, CAP-06 | CAP-06, CAP-08, CAP-12 |
| CAP-10 Reviews | CAP-06, CAP-07 | CAP-04, CAP-05, CAP-11, CAP-12, CAP-13 |
| CAP-11 Moderation/fraud | CAP-02, CAP-05, CAP-06, CAP-07, CAP-08, CAP-10 | CAP-02, CAP-04, CAP-07, CAP-08, CAP-13 |
| CAP-12 Dashboards/analytics | CAP-02, CAP-03, CAP-06, CAP-07, CAP-08, CAP-09, CAP-10 | CAP-13 |
| CAP-13 Notifications | (all event-emitting CAPs) | — |

> Note: CAP-08 combines refunds, chargebacks, and payouts because for digital goods these share the
> seller-balance ledger and entitlement-revocation logic. If stakeholders prefer, payouts can be split
> into a separate capability (see Open Questions).

## Open Questions

- **Payout model & timing**: For digital goods there is no "service completion." Should seller proceeds
  become available immediately on payment, after a fixed hold (e.g., 7-14 days) to cover refunds/chargebacks,
  or on a rolling reserve? This materially affects CAP-08 and seller cash flow. (Assumed: a fixed hold
  window before funds move from pending to available.)
- **Should payouts be split out from CAP-08** into their own capability (as in the service-marketplace
  example), or stay combined given the shared ledger? (Assumed: combined for this draft.)
- **Refund policy for downloaded goods**: Are refunds allowed after the buyer has downloaded? Under what
  conditions (broken file, not as described only)? This drives CAP-08 eligibility logic.
- **Recurring / subscription digital products**: Out of scope for MVP here — confirm one-time-purchase only.
- **Marketplace tax facilitator status**: In which jurisdictions does the platform collect and remit vs.
  leave to sellers? Drives CAP-09 configuration.
- **File update policy**: When a seller updates a product file, do existing buyers automatically get the
  new version, only on request, or only if they purchased an "updates included" license?
- **Multi-currency**: Display-only conversion vs. charging/paying out in multiple currencies. (Assumed:
  charge in a base/display currency set; payouts in a small supported set.)
- **Success-metric targets**: Concrete monthly orders / active-seller targets need stakeholder input.
- **Guest checkout**: Allowed, or account required to hold entitlements? (Assumed: account required so
  buyers retain a re-downloadable library; guest may be added later.)

## Research Suggestions

Topics flagged for the **researcher skill** (not researched here, as the researcher skill is unavailable):

- **Chargeback & fraud mitigation for digital goods** — Digital goods are uniquely chargeback- and
  fraud-prone (instant, irreversible delivery). Suggested researcher query: "Chargeback and fraud
  prevention best practices for instant-delivery digital goods marketplaces — 3DS/step-up auth, risk
  scoring, delivery-evidence representment, and seller reserve models."
- **Seller payout timing vs. refund risk** — Balancing fast seller payouts against refund/chargeback
  exposure with no service-completion signal. Suggested query: "Payout hold periods and rolling reserves
  for digital marketplaces — how platforms balance seller cash flow against chargeback risk."
- **Marketplace VAT/sales-tax obligations for digital goods** — Cross-border digital-goods tax
  (EU VAT MOSS/OSS, US economic nexus, marketplace facilitator laws). Suggested query: "Marketplace
  facilitator tax obligations for cross-border digital goods — VAT/GST/sales-tax collection and remittance
  rules and thresholds."
- **Anti-piracy / entitlement protection** — Limiting unauthorized redistribution of delivered files
  (watermarking, signed time-limited links, license keys, download throttling). Suggested query:
  "Anti-piracy techniques for digital-goods marketplaces — invisible watermarking, signed expiring URLs,
  license-key models, and download-abuse detection."
- **Review integrity** — Preventing fake/inflated reviews and review bombing in a verified-purchase model.
  Suggested query: "Review system integrity for digital marketplaces — verified-purchase enforcement,
  rating-inflation and review-bombing detection."
- **Commission / fee structures for digital marketplaces** — What take rate sustains the platform while
  attracting sellers. Suggested query: "Commission and fee structures for digital-goods marketplaces by
  product category and price point."

## Next Steps

1. Resolve the **payout timing / hold model** and **refund-after-download policy** with stakeholders —
   these are the highest-leverage decisions and gate CAP-06, CAP-07, and CAP-08.
2. Confirm scope assumptions (one-time purchases only, account-required checkout, supported currencies,
   tax-facilitator jurisdictions) and update CAP-06/CAP-09 accordingly.
3. Have an agent with **librarian** access search for prior research/specs (see Existing Knowledge) and
   fold in anything found.
4. Hand the flagged topics to the **researcher** skill (see Research Suggestions), prioritizing
   chargeback/fraud mitigation and digital-goods tax.
5. Define the MVP product categories, license-type taxonomy, and the inventory models to support first
   (start with unlimited + limited-quantity; add key/seat-based if demand exists).
6. Draft platform policies referenced throughout: refund policy, prohibited-content / DMCA policy, and
   the notification event catalog (which events go to which channels).

---
*Capability breakdown produced by solution-architect skill. Use the librarian skill to persist this artifact.*
