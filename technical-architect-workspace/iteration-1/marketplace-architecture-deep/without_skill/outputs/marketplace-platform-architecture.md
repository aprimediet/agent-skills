# Digital-Goods Marketplace — Technical Architecture & Tech Stack

**Document type:** Platform technical architecture
**Scope:** Two-sided digital-goods marketplace (buyers + sellers)
**Target scale:** Millions of users, designed for horizontal growth
**Status:** Reference architecture (greenfield)

---

## 1. Overview & Goals

### 1.1 What we are building

A two-sided marketplace for **digital goods** — non-physical items delivered as files, license keys, or access entitlements (e.g., software, templates, ebooks, audio/video, game assets, fonts, plugins). The two sides:

- **Buyers** — discover, browse, search, purchase, and receive digital goods; manage their library/entitlements; leave reviews; request refunds.
- **Sellers** — onboard (KYC + payout setup), list items, upload and version assets, manage inventory/licenses, see a ledger of earnings, request/receive payouts, respond to reviews.

Because the goods are digital, the platform has properties that differ sharply from physical-goods marketplaces:

- **No shipping/logistics**, but **delivery = entitlement + secure download/license issuance**, which must be idempotent, fraud-resistant, and instantaneous.
- **Inventory** is often unlimited (a file can be sold infinitely) or constrained (finite license-key pools, time-limited licenses, seat-based licenses).
- **Refund/chargeback risk is high** because goods can be consumed instantly and are non-returnable; entitlement revocation and abuse controls are core, not afterthoughts.
- **Money movement** (split payments, marketplace fees, seller payouts, tax) is the regulatory heart of the system.

### 1.2 Architectural goals (and non-goals)

| Goal | Why it matters here |
|------|---------------------|
| **Correctness of money & entitlements** | A buyer paying once must get exactly one entitlement; a seller must be paid exactly what they earned. These are the invariants we never violate. |
| **Scale to millions of users** | Read-heavy browse/search, spiky checkout traffic, large asset egress. |
| **Independent deployability of capabilities** | ~15 capabilities owned by different teams shipping at different cadences. |
| **Strong audit trail & compliance** | PCI scope minimization, KYC/AML, tax, GDPR/CCPA, financial reconciliation. |
| **Fast, relevant discovery** | Search & recommendations drive GMV. |
| **Abuse resistance** | Fraud, piracy, fake reviews, malicious uploads. |

**Non-goals:** physical fulfillment, complex multi-warehouse logistics, in-person payments. We also avoid premature microservice sprawl — we start with a **modular monolith + a few hard-carved services** and extract along proven seams (see §4.1).

---

## 2. Capability Map (the ~15 capabilities)

These are the bounded contexts that drive the service decomposition. Each is owned by one team and has its own data store(s).

| # | Capability | Core responsibility | Primary data store |
|---|------------|---------------------|---------------------|
| 1 | **Identity & Accounts** | AuthN/AuthZ, buyer & seller accounts, sessions, MFA | PostgreSQL + Redis |
| 2 | **Seller Onboarding** | Application, KYC/KYB, payout account linking, agreements | PostgreSQL |
| 3 | **Catalog / Listing** | Listings, categories, attributes, pricing, publish workflow | PostgreSQL |
| 4 | **Asset Management** | File upload, versioning, virus scan, transcoding, license-key pools | S3 + PostgreSQL |
| 5 | **Search & Discovery** | Full-text + faceted search, recommendations, trending | OpenSearch + vector store |
| 6 | **Cart & Checkout** | Cart, pricing/tax calc, order creation, idempotent order intent | PostgreSQL + Redis |
| 7 | **Payments** | PSP integration, authorization/capture, split, refunds, chargebacks | PostgreSQL (payments ledger) |
| 8 | **Digital Delivery / Entitlements** | Grant entitlement, issue licenses, signed download URLs | PostgreSQL + Redis |
| 9 | **Refunds & Disputes** | Refund requests, chargeback handling, revocation policy | PostgreSQL |
| 10 | **Seller Ledger** | Double-entry accounting of earnings, fees, reserves, balances | PostgreSQL (ledger, append-only) |
| 11 | **Payouts** | Scheduling, batching, disbursement via PSP, reconciliation | PostgreSQL |
| 12 | **Reviews & Ratings** | Verified-purchase reviews, aggregates, seller responses | PostgreSQL |
| 13 | **Trust & Safety / Moderation** | Content/listing/review moderation, fraud signals, takedowns | PostgreSQL + ML services |
| 14 | **Notifications** | Email, push, SMS, in-app, webhooks to sellers | PostgreSQL + queue |
| 15 | **Analytics & Reporting** | Seller dashboards, platform BI, financial reports | Warehouse (BigQuery/Snowflake) |

Cross-cutting (not a single team, but platform concerns): **API Gateway/BFF**, **Eventing backbone**, **Media/CDN**, **Observability**, **Secrets/Config**, **Tax & Compliance**.

---

## 3. High-Level Architecture

### 3.1 Logical view (text diagram)

```
                          ┌───────────────────────────────────────────┐
                          │                Clients                     │
                          │  Web (Next.js)   Mobile (RN)   Seller Web   │
                          └───────────────┬───────────────────────────┘
                                          │ HTTPS / TLS1.3
                                  ┌───────▼────────┐
                                  │   CDN / WAF    │  (CloudFront/Cloudflare)
                                  │  edge cache    │
                                  └───────┬────────┘
                                          │
                                  ┌───────▼────────┐
                                  │  API Gateway   │  authN, rate-limit, routing
                                  │   + BFF layer  │  (Kong/Envoy + GraphQL BFF)
                                  └───┬───────┬────┘
              ┌───────────────────────┼───────┼──────────────────────────────┐
              │                       │       │                              │
       ┌──────▼─────┐       ┌─────────▼──┐ ┌──▼─────────┐         ┌──────────▼──────┐
       │ Identity   │       │  Catalog   │ │  Search    │   ...   │  Payments       │
       │ service    │       │  service   │ │  service   │         │  service        │
       └──────┬─────┘       └────┬───────┘ └────┬───────┘         └──────┬──────────┘
              │                  │              │                        │
       ┌──────▼──────────────────▼──────────────▼────────────────────────▼────────┐
       │                    Event Backbone (Kafka)                                 │
       │   topics: order.*, payment.*, entitlement.*, listing.*, ledger.*, ...     │
       └──────┬──────────────────┬──────────────┬────────────────────────┬────────┘
              │                  │              │                        │
       ┌──────▼─────┐     ┌──────▼─────┐  ┌─────▼──────┐          ┌───────▼────────┐
       │ Delivery / │     │  Ledger    │  │  Payouts   │          │ Notifications  │
       │Entitlements│     │ (dbl-entry)│  │            │          │                │
       └────────────┘     └────────────┘  └────────────┘          └────────────────┘

  Data plane: PostgreSQL (per-service)  •  Redis  •  S3/object store  •  OpenSearch
  Analytics:  CDC (Debezium) → Kafka → Lake/Warehouse (BigQuery/Snowflake) → BI
```

### 3.2 Style & key decisions

- **Modular-monolith-first, then targeted services.** Start with a well-modularized application (clear bounded-context modules, separate schemas) and extract the highest-divergence/highest-scale contexts into independent services from day one: **Payments**, **Ledger**, **Search**, **Delivery/Entitlements**, **Media processing**. This avoids distributed-systems tax on contexts that don't need it yet, while protecting the money/scale-critical seams.
- **Async-first via an event backbone.** Order → payment → entitlement → ledger → payout → notification is naturally a saga. We use events for cross-context workflows and keep synchronous calls only for read paths and the critical user-facing checkout path.
- **Database-per-service** for the carved-out services; **schema-per-module** within the monolith. No cross-service DB access — only APIs and events.
- **CQRS where read/write asymmetry is large** (catalog, search, seller dashboards): writes go to the system of record (Postgres), reads are served from projections (OpenSearch, Redis, read replicas, materialized views).
- **Outbox pattern + CDC** for reliable event publication (no dual-write bugs between DB and Kafka).

---

## 4. Service Decomposition & Boundaries

### 4.1 Decomposition rationale

We carve services along **rate-of-change**, **scaling profile**, and **compliance blast radius**:

- **Payments + Ledger + Payouts** form the *financial core*. Isolated for PCI scope minimization, independent audit, and strict change control. Money correctness is enforced here with double-entry bookkeeping and idempotency.
- **Search/Discovery** scales independently (read-heavy, different storage engine, ML workloads).
- **Delivery/Entitlements** is latency- and security-sensitive (signed URLs, license issuance) and must remain available even during partial outages of catalog/search.
- **Media processing** (transcode, virus scan, thumbnailing) is bursty, CPU/GPU-heavy, and best run as async workers.
- Everything else (catalog, cart/checkout, reviews, onboarding, notifications) starts inside the modular monolith and is extracted only when a team/scale reason emerges.

### 4.2 Synchronous vs. asynchronous boundaries

| Interaction | Sync or Async | Mechanism |
|-------------|---------------|-----------|
| Browse / search / product page | Sync (read) | BFF → read projections / caches |
| Add to cart, price quote | Sync | Cart service + Tax service |
| Place order | Sync create + async fulfill | Order created synchronously; fulfillment saga runs async |
| Payment authorize/capture | Sync to PSP, async confirm | PSP call sync; webhooks reconcile async |
| Entitlement grant after payment | Async (event-driven) | `payment.captured` → Delivery consumer |
| Ledger postings | Async | `payment.captured` / `refund.completed` → Ledger consumer |
| Payouts | Async/batch | Scheduled job + PSP transfers |
| Notifications | Async | events → Notification consumers |
| Search index updates | Async | `listing.published` → indexer |
| Analytics | Async | CDC → Kafka → warehouse |

---

## 5. Tech Stack

The stack favors boring, proven, hire-able technologies, with specialized engines only where justified.

### 5.1 Languages & runtimes

- **Primary backend:** **Go** for the financial core and high-throughput, latency-sensitive services (Payments, Ledger, Payouts, Delivery/Entitlements, Gateway-adjacent services). Strong concurrency, low memory footprint, predictable latency.
- **Application backend (modular monolith + most business services):** **TypeScript on Node.js (NestJS)** *or* **Kotlin/Java (Spring Boot)** — pick one org-wide. Recommendation: **NestJS/TypeScript** for velocity and shared types with the frontend, with the option to use Kotlin/Spring for heavy transactional services if the team's strength is JVM. (This doc assumes **NestJS + Go** as the canonical pairing.)
- **Media/ML workers:** **Python** (FastAPI for service endpoints; workers for transcoding/scanning/ML scoring).
- **Search relevance & data jobs:** Python + SQL.

### 5.2 Frontend

- **Web (buyer + seller):** **Next.js (React)** with server-side rendering / ISR for SEO-critical browse and listing pages (discovery drives organic GMV), client components for dashboards.
- **Mobile:** **React Native** (shared logic with web) — buyer-focused; seller flows can stay web-first initially.
- **State/data:** TanStack Query + typed GraphQL/REST clients; design system in a shared component library (Storybook).

### 5.3 API layer

- **API Gateway:** **Kong** or **Envoy-based gateway** for TLS termination, authN (JWT validation/introspection), global rate limiting, routing, and request/response transformation.
- **BFF:** **GraphQL (Apollo) BFF** for the web/mobile apps to aggregate across services and avoid chatty clients; internal service-to-service uses **gRPC** (typed, fast) for synchronous calls and REST for external/partner-facing webhooks.
- **API contracts:** OpenAPI for REST, Protobuf for gRPC, schema registry for Kafka (Avro/Protobuf).

### 5.4 Data stores

| Store | Technology | Used for |
|-------|------------|----------|
| OLTP relational | **PostgreSQL 16** (Aurora PostgreSQL or Cloud SQL/AlloyDB) | System of record for all transactional contexts |
| Cache / ephemeral | **Redis** (ElastiCache/MemoryStore) | Sessions, cart, rate limits, hot reads, locks, signed-URL nonces |
| Search | **OpenSearch / Elasticsearch** | Full-text + faceted search projections |
| Vector | **pgvector** (start) → **dedicated vector DB** (scale) | Semantic search & recommendations |
| Object store | **S3** (or GCS) | Asset originals, derivatives, invoices, exports |
| Event log | **Apache Kafka** (MSK/Confluent) | Event backbone, CDC sink, async workflows |
| Warehouse | **BigQuery / Snowflake** | Analytics, BI, financial reporting |
| Time-series/metrics | **Prometheus** + **Thanos** | Observability metrics |

**Why Postgres as the default OLTP:** transactional integrity (critical for money/entitlements), rich features (JSONB, partial indexes, partitioning, `SELECT ... FOR UPDATE`, advisory locks, logical replication for CDC), and a clean path to per-service isolation.

### 5.5 Infrastructure & platform

- **Cloud:** AWS (reference); the design is portable to GCP. Multi-AZ from day one; multi-region as a later phase for DR and latency.
- **Compute:** **Kubernetes (EKS)** for services + workers; **Karpenter** for autoscaling; **KEDA** for event/queue-driven scaling of workers.
- **IaC:** **Terraform** (infra) + **Helm/Argo CD** (GitOps deploys).
- **CI/CD:** GitHub Actions → build/test/scan → Argo CD progressive delivery (canary via Argo Rollouts).
- **Secrets:** AWS Secrets Manager / Vault; KMS for envelope encryption.
- **CDN:** CloudFront (or Cloudflare) for static assets, media egress, and edge caching of public catalog pages.

---

## 6. Capability Deep-Dives

### 6.1 Identity & Accounts

- **AuthN:** OIDC/OAuth2. Use a managed IdP (**Auth0/Cognito/Keycloak**) for social login, MFA, passwordless. Issue short-lived JWT access tokens + rotating refresh tokens; sessions tracked in Redis for revocation.
- **AuthZ:** Role-based at coarse level (buyer, seller, admin, moderator) plus resource-level checks (seller can only mutate own listings). Centralize policy with an **OPA/Cedar**-style policy engine for moderation/admin scopes.
- **Account model:** A user can be both buyer and seller; seller capability is gated behind onboarding completion. Sensitive PII encrypted at rest (column-level via KMS).

### 6.2 Seller Onboarding

- Workflow engine (state machine) drives: application → identity/business verification (**KYC/KYB via Stripe Identity / Persona**) → payout account linking (**Stripe Connect** express/custom accounts) → tax forms (W-9/W-8/local equivalents) → agreement acceptance → activation.
- Risk-tiered: low-risk sellers fast-tracked; high-risk flagged for manual review (feeds Trust & Safety).
- Stores verification status and capability flags; emits `seller.activated` to unlock listing creation.

### 6.3 Catalog / Listing

- Listing aggregate: title, description, category, attributes (EAV-ish via JSONB), pricing (incl. multi-currency, tiered/volume, license types), media references, status (draft/in-review/published/suspended).
- **Publish workflow:** draft → submitted → moderation (auto + manual) → published. Publishing emits `listing.published` consumed by Search indexer and cache invalidation.
- **Pricing model** supports: one-time purchase, multiple license tiers (personal/commercial/extended), bundles, and discounts/coupons.
- Read path served from cache + read replicas; product pages SSR'd and edge-cached with cache-tag invalidation on update.

### 6.4 Asset Management

This is digital-goods-specific and security-critical.

- **Upload:** Direct-to-S3 via **pre-signed multipart upload** (browser/CLI → S3, not through app servers). Upload metadata recorded; object lands in a quarantine bucket.
- **Processing pipeline (async workers, KEDA-scaled):**
  1. **Virus/malware scan** (ClamAV + a commercial scanner for breadth) — block on failure.
  2. **Content validation** (file type/magic-byte check, size limits, optional DRM/watermark embedding).
  3. **Derivative generation:** previews/thumbnails, transcodes (video → HLS, audio → multiple bitrates), redacted/preview versions.
  4. On success, promote from quarantine to the protected origin bucket; emit `asset.ready`.
- **Versioning:** assets are immutable, content-addressed (hash) with version pointers per listing, so existing entitlements can pin to the purchased version while new buyers get the latest.
- **License-key inventory:** for goods sold as keys (software/games), maintain a **license-key pool** with atomic claim (`SELECT ... FOR UPDATE SKIP LOCKED`) to prevent double-issuance; track key state (available/reserved/issued/revoked).

### 6.5 Search & Discovery

- **Engine:** OpenSearch for lexical + faceted search (filters: category, price, license type, rating, format), with **vector search (pgvector → dedicated)** for semantic/"find similar."
- **Indexing:** event-driven (`listing.published`, `listing.updated`, review-aggregate changes, price changes) via an indexer consumer; full-reindex capability for mapping changes.
- **Ranking:** hybrid (BM25 + vector) with learning-to-rank features (sales velocity, conversion, recency, rating, seller trust score). Personalization layer from user behavior events.
- **Recommendations:** "you may also like," trending, and homepage rails computed in batch (warehouse/feature store) + served from a low-latency store; cold-start via category/content embeddings.

### 6.6 Cart & Checkout

- **Cart** stored in Redis (guest) and persisted to Postgres on login; supports multi-seller carts.
- **Checkout** is a critical, idempotent flow:
  1. Compute final price (line items, discounts, **tax via Stripe Tax / Avalara / TaxJar** based on buyer location and digital-goods tax rules — VAT/GST/sales tax differ by jurisdiction).
  2. Create an **Order** with a client-supplied **idempotency key** (dedupes retries). Order starts in `pending`.
  3. Initiate payment (see §6.7). Order state machine: `pending → paid → fulfilled` (or `payment_failed`, `canceled`).
- **Multi-seller orders** create one order with per-seller sub-orders so fees/ledger/payouts are computed per seller.

### 6.7 Payments

The financial core, kept in a PCI-minimized service in **Go**.

- **PSP:** **Stripe** (primary) with **Stripe Connect** for marketplace split payments and seller payouts; **Adyen** as a second processor for redundancy and better international coverage (provider-abstracted behind an internal interface).
- **PCI scope:** card data never touches our servers — **tokenized client-side** (Stripe Elements / Payment Element). We store only tokens and PSP references → keeps us at **SAQ A**.
- **Flow:** authorize → capture (separate for fraud hold scenarios) → on capture, emit `payment.captured`. Split: marketplace fee retained, seller portion tracked for payout.
- **Idempotency:** every PSP call uses idempotency keys; our payment intents are uniquely keyed to orders to guarantee exactly-once charge semantics.
- **Webhooks:** Stripe/Adyen webhooks are the source of truth for async state (captures, disputes, payout status); verified by signature, deduped, and processed idempotently.
- **3DS/SCA, multi-currency, alternative payment methods** (wallets, local methods) supported via the PSP.

### 6.8 Digital Delivery / Entitlements

- **Entitlement = the durable right** of a buyer to access a purchased good (and its license terms). Created on `payment.captured` (consumer is idempotent on `order_id + line_item_id`).
- **Delivery mechanisms:**
  - **Files:** time-limited **signed download URLs** (S3 pre-signed / CloudFront signed URLs) issued per request; download attempts logged and optionally rate/count-limited per license terms.
  - **License keys:** atomically claimed from the pool and bound to the entitlement.
  - **Streamed media:** signed HLS playback with token-gated manifests.
  - **API/SaaS access:** issue scoped API keys or activate seats.
- **Library:** buyer's "My Purchases" lists entitlements with re-download, version pinning, and license details.
- **Anti-piracy:** watermarking (where applicable), download limits, anomaly detection on access patterns (feeds Trust & Safety).
- **Revocation:** entitlements can be revoked (refund/chargeback/fraud) — revocation flips state and invalidates outstanding signed URLs/keys.

### 6.9 Refunds & Disputes

- **Refund requests** (buyer-initiated) flow through a policy engine (eligibility window, license-type rules, prior-download checks). Approved refunds call PSP refund, emit `refund.completed` → Ledger reversal + entitlement revocation.
- **Chargebacks:** PSP dispute webhook → open dispute case → gather evidence (delivery proof, download logs, IP, license terms) → auto-submit representment package. On loss, reverse ledger and (per policy) debit seller balance/reserve.
- **Seller protection vs. abuse:** track buyer refund/chargeback rates for fraud scoring; track seller dispute rates for trust scoring and reserve adjustments.

### 6.10 Seller Ledger (double-entry)

The accounting backbone — **append-only, double-entry**, in its own Postgres database, in Go.

- Every money event produces balanced journal entries across accounts: `platform_revenue`, `seller_payable`, `seller_reserve`, `processing_fees`, `tax_payable`, `refunds`, etc.
- **Sources of postings (all idempotent on event id):** sale (`payment.captured`), platform fee, processing fee, refund, chargeback, payout, adjustment.
- **Balances are derived** by summing entries (with periodic snapshots/materialized balances for performance). This gives a provable audit trail and exact reconciliation against PSP statements.
- **Reserves/holds:** configurable rolling reserve for risky sellers; funds become payable only after the refund/chargeback risk window.
- **Reconciliation job** compares ledger to PSP settlement reports daily; discrepancies raise alerts.

### 6.11 Payouts

- **Scheduling:** per-seller cadence (daily/weekly/threshold-based) honoring reserves and minimum payout amounts.
- **Execution:** batch job computes payable balance per seller from the ledger, creates a payout, disburses via **Stripe Connect transfers/payouts** (or Adyen), and records the payout as a ledger posting. Idempotent per `payout_id`.
- **Failure handling:** retries with backoff; failed payouts (bad bank details) move funds back to payable and notify the seller.
- **Tax & reporting:** generate 1099-K/local statements; year-end exports.

### 6.12 Reviews & Ratings

- **Verified purchase** enforced — only buyers with a fulfilled entitlement for the listing can review (one review per entitlement).
- Aggregates (avg rating, count, distribution) maintained via async projection; changes feed Search ranking.
- **Seller responses**, helpful votes, and moderation (spam/fake-review detection in Trust & Safety).

### 6.13 Trust & Safety / Moderation

- **Listing/asset moderation:** automated classifiers (malware, prohibited content, IP/DMCA matching via perceptual hashing for images/audio/video) + manual review queue for flagged/high-risk items.
- **Fraud:** real-time scoring at checkout and onboarding using features (velocity, device fingerprint, payment risk from PSP, account age, refund/chargeback history). Integrate a fraud platform (**Sift/Stripe Radar**) plus in-house rules.
- **Review/abuse moderation:** fake-review detection, harassment filtering.
- **Enforcement:** takedowns, listing suspension, account holds, payout freezes — all audited and reversible, with appeals workflow.
- **DMCA/IP:** notice-and-takedown workflow with counter-notice handling.

### 6.14 Notifications

- **Channels:** email (**SES/SendGrid**), push (FCM/APNs), SMS (Twilio/SNS), in-app, and **seller webhooks** (signed, retried with backoff, dead-lettered).
- Event-driven: consumers subscribe to domain events and render templated messages; user preferences and quiet-hours respected; transactional vs. marketing separated (CAN-SPAM/GDPR consent).
- Idempotent send with dedupe keys to avoid double-notifying on event redelivery.

### 6.15 Analytics & Reporting

- **CDC (Debezium)** streams Postgres changes to Kafka → lake (S3/Parquet) → warehouse (**BigQuery/Snowflake**), transformed with **dbt**.
- Powers seller dashboards (sales, conversion, traffic), platform BI/finance, search relevance features, and ML feature store.
- Near-real-time seller dashboard metrics via a serving layer (pre-aggregated rollups in Redis/ClickHouse) for low latency.

---

## 7. Data Architecture

### 7.1 Ownership & isolation

- Each bounded context owns its schema; **no shared tables, no cross-service joins**. Integration is via APIs (sync) and events (async).
- The financial contexts (Payments, Ledger, Payouts) live in a **separately-secured database cluster** with tighter access control and audit logging.

### 7.2 Consistency model

- **Strong consistency** within a context (single Postgres transaction) — used for order creation, ledger postings, license claims, entitlement grants.
- **Eventual consistency across contexts**, coordinated by **sagas** with the **outbox pattern**:
  - The fulfillment saga: `OrderPaid → GrantEntitlement → PostLedger → ScheduleNotification`. Each step is idempotent and emits a completion event; compensations exist for failures (e.g., payment captured but entitlement grant fails → retry, then alert; refund as compensation if unrecoverable).
- **Idempotency everywhere money or entitlements move**: idempotency keys on API writes, event-id dedupe on consumers, unique constraints as the last line of defense.

### 7.3 Reliable eventing (no dual-write bug)

- Services write domain changes and an **outbox row in the same DB transaction**; a CDC/relay publishes the outbox to Kafka. This guarantees the event is published iff the state change committed.
- Kafka topics keyed for ordering where it matters (e.g., per `order_id`, per `seller_id`); schema registry enforces contracts; consumers are idempotent and use DLQs.

### 7.4 Scaling the data tier

- **Read scaling:** read replicas + caching (Redis) + CQRS projections (OpenSearch for search, materialized views/rollups for dashboards).
- **Write scaling:** partition/shard the highest-volume tables. Candidates:
  - **Orders/Payments/Ledger** partitioned by time (range) and, at extreme scale, sharded by `seller_id` or `tenant`/hash.
  - **Entitlements & download logs** partitioned by time; hot/cold tiering of old logs to the lake.
- **Object store** scales effectively infinitely; CDN absorbs egress.
- Search and event backbone scale horizontally by design (shards/partitions).

---

## 8. Cross-Cutting Concerns

### 8.1 Security & compliance

- **PCI DSS:** SAQ A via tokenization (no PAN on our systems). Quarterly scans, segmented financial network.
- **PII protection:** encryption at rest (KMS), column-level encryption for sensitive fields, TLS 1.3 in transit, field-level access auditing.
- **KYC/AML:** during onboarding and ongoing monitoring for high-volume sellers; sanctions screening.
- **GDPR/CCPA:** data inventory, DSR (export/delete) workflows, consent management, regional data residency option (EU data in EU region).
- **Tax:** automated calculation and remittance support (VAT MOSS/OSS for EU digital goods, US sales tax nexus, GST).
- **AuthZ:** least privilege, signed internal service identities (mTLS / SPIFFE), short-lived credentials.
- **Supply chain:** SBOM, dependency scanning, signed images, admission control.

### 8.2 Observability

- **Tracing:** OpenTelemetry end-to-end (gateway → services → workers → DB), distributed trace IDs propagated through events.
- **Metrics:** Prometheus + Grafana; RED/USE dashboards; business SLOs (checkout success rate, time-to-entitlement, payout success).
- **Logs:** structured JSON → Loki/ELK; audit logs for money/entitlement actions retained per compliance.
- **Alerting:** SLO-based, with runbooks; financial reconciliation alerts are P1.

### 8.3 Reliability & resilience

- **SLO targets (illustrative):** browse/search 99.95%, checkout 99.95%, delivery 99.99% (buyers must always be able to get what they paid for), payouts 99.9%.
- **Patterns:** timeouts, retries with jitter, circuit breakers, bulkheads, graceful degradation (e.g., search down → fall back to category browse; recommendations down → static rails).
- **DR:** multi-AZ standard; cross-region async replication for the financial DB and object store; documented RPO/RTO; regular game days.
- **Backpressure:** queue-based load leveling for spikes (flash sales, new drops); KEDA scales workers on lag.

### 8.4 Performance

- Edge-cache public pages and media; cache catalog/search reads aggressively with tag-based invalidation.
- Keep the synchronous checkout path lean; push everything non-essential (entitlement, ledger, notifications) async so "place order" returns fast.
- Pre-signed direct-to-S3 uploads/downloads keep large media off the app tier.

---

## 9. Key End-to-End Flows

### 9.1 Purchase → delivery (happy path)

```
Buyer checkout
  → Cart/Checkout: compute price+tax, create Order(pending) [idempotency key]
  → Payments: create PaymentIntent, client confirms (tokenized), capture
  → Payments emits payment.captured (via outbox→Kafka)
       ├→ Delivery: grant Entitlement (idempotent), claim license key if applicable
       │     → issues signed download URL / key; emits entitlement.granted
       ├→ Ledger: post double-entry journal (sale, fees, seller_payable)
       └→ Notifications: email buyer receipt, notify seller of sale
  → Order transitions paid → fulfilled
```

### 9.2 Refund / chargeback

```
Refund: buyer request → policy check → Payments.refund → refund.completed
   → Ledger reversal (debit seller_payable/reserve) → Entitlement revoked → notify

Chargeback: PSP dispute webhook → dispute case opened → auto-collect evidence
   (download logs, delivery proof) → submit representment
   → on loss: ledger reversal + reserve/balance debit; on win: close, no change
```

### 9.3 Seller payout

```
Scheduler → compute payable from Ledger (minus reserve) per seller
   → create Payout(idempotent) → PSP transfer/payout
   → on success: ledger posting (seller_payable → paid_out) + notify
   → on failure: revert to payable, alert seller, retry
```

### 9.4 Seller lists a digital good

```
Seller creates Listing(draft) → uploads asset (pre-signed multipart → S3 quarantine)
   → async pipeline: virus scan → validate → generate previews/transcodes → promote
   → asset.ready → Listing submitted → moderation (auto+manual) → published
   → listing.published → Search index update + cache invalidation
```

---

## 10. Phased Roadmap (scaling over time)

**Phase 1 — MVP / product-market fit**
- Modular monolith (NestJS) + carved financial core (Go) + Search service.
- Postgres (single primary + replica), Redis, S3 + CloudFront, OpenSearch.
- Stripe Connect for payments/payouts; Stripe Tax/Identity. Single region, multi-AZ.
- Kafka (or start with a managed lighter queue like SQS/SNS) for the fulfillment saga + notifications.
- Core capabilities: identity, onboarding, listing, asset mgmt, search, checkout, payments, delivery/entitlements, ledger, payouts, reviews, basic moderation, notifications.

**Phase 2 — growth / hundreds of thousands of users**
- Extract Delivery/Entitlements and Media processing into dedicated services/workers.
- Introduce CDC → warehouse; dbt; seller analytics dashboards.
- Add second PSP (Adyen) abstraction; fraud platform integration; richer moderation ML.
- Read replicas + caching tiers; OpenSearch scaled; hybrid (vector) search.
- Progressive delivery, full OTel observability, SLOs.

**Phase 3 — scale / millions of users**
- Partition/shard high-volume tables (orders, ledger, entitlements, download logs).
- Multi-region (active-passive financial core; active-active for read/browse/delivery).
- Feature store + ranking ML for search/recommendations; ClickHouse for real-time analytics serving.
- Reserves/risk modeling matured; automated reconciliation; regional data residency.

---

## 11. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Double-charge / double-entitlement | Idempotency keys, unique constraints, exactly-once via outbox + idempotent consumers |
| Money discrepancies | Double-entry ledger, daily PSP reconciliation, immutable audit log |
| Piracy / asset leakage | Short-lived signed URLs, download limits, watermarking, anomaly detection |
| Fraud & chargebacks | Risk scoring at onboarding/checkout, reserves, evidence automation, refund-rate monitoring |
| Malicious uploads | Mandatory scan + quarantine before promotion, type/magic-byte validation |
| Search/recs outage hurts GMV | Graceful degradation to browse + static rails; independent scaling |
| Distributed-systems complexity | Monolith-first, extract only proven seams; keep sync surface minimal |
| Compliance gaps (tax/PCI/GDPR) | Tokenization (SAQ A), automated tax engine, DSR workflows, regional residency |

---

## 12. Summary

This architecture centers on the two things that make a **digital-goods** marketplace different and risky: **instant entitlement/delivery** and **money movement**. It isolates the financial core (Payments, double-entry Ledger, Payouts) in a hardened, idempotent, audit-first service tier; treats **delivery/entitlements** as a first-class, highly-available, anti-piracy-aware capability; and uses an **event-driven saga** backbone to keep the user-facing checkout fast while reliably fanning out fulfillment, accounting, and notifications.

The stack is deliberately pragmatic — **PostgreSQL** systems of record, **Go** for the money/latency core, **NestJS/TypeScript** for application services, **Next.js/React Native** clients, **OpenSearch + vector** for discovery, **Kafka** for the backbone, **Stripe Connect (+ Adyen)** for payments/payouts, on **Kubernetes/Terraform/Argo CD** — and it scales from a monolith-first MVP to a sharded, multi-region, ML-ranked platform serving millions, by extracting services only along proven seams.
