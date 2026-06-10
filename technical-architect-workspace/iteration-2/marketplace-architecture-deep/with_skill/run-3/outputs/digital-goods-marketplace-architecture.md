# Digital-Goods Marketplace — Technical Architecture

> Technical Architect | Depth: deep | Generated: 2026-06-10

## Source Breakdown

This architecture builds on a capability breakdown for a two-sided **digital-goods** marketplace (buyers browse and purchase digital goods; sellers list items, manage inventory/licenses, and receive payouts). The breakdown was **provided inline in the task** — the librarian skill was not available to retrieve a stored solution-architect spec, so the capabilities below are an inline enumeration of the stated areas, not invented scope. Every technical choice is anchored to one of these capabilities; where a functional gap surfaces it is flagged back to solution-architect rather than designed in.

Capabilities (inline, derived strictly from the stated areas — no new functional scope introduced):

- **CAP-01 Seller onboarding** — register as seller, KYC/identity & tax verification, connect a payout account, accept terms.
- **CAP-02 Listing & catalog management** — create/edit/publish/unpublish listings, pricing, metadata, categories, listing versioning.
- **CAP-03 Digital asset & inventory/license management** — upload/store digital assets and license keys/codes; manage finite inventory (e.g., license-key pools) and unlimited (re-deliverable) goods.
- **CAP-04 Search & discovery** — full-text search, facets/filters, sorting, browse-by-category, relevance ranking.
- **CAP-05 Cart & checkout** — cart, order creation, tax computation, order state machine.
- **CAP-06 Payment processing** — charge buyer via PCI-compliant gateway, capture, store tokens/references, handle declines.
- **CAP-07 Digital delivery & entitlements** — on successful payment, grant the buyer an entitlement and deliver the asset (secure/expiring download links and/or license-key issuance), buyer library/re-download.
- **CAP-08 Refunds & chargebacks** — process refunds, handle gateway chargeback/dispute webhooks, revoke entitlements where applicable, adjust seller balances.
- **CAP-09 Seller ledger** — auditable per-seller account of sales, fees, refunds, chargebacks, adjustments, and current balance.
- **CAP-10 Payouts** — schedule/threshold-driven disbursement of seller balances to connected payout accounts, with retries and reconciliation.
- **CAP-11 Reviews & ratings** — buyers rate/review purchased goods; rating aggregation; verified-purchase gating.
- **CAP-12 Moderation & trust/safety** — review listings, assets, and reviews for prohibited/infringing content; takedown/suspension actions; abuse/fraud signals.
- **CAP-13 Notifications** — transactional and lifecycle notifications across email/in-app/push (purchase receipts, delivery, payout, moderation actions).

> Note: a formal CAP breakdown from the solution-architect skill would sharpen this (especially entitlement-revocation policy, license-pool semantics, and chargeback liability rules). Running solution-architect first is recommended; the inline list above is the honest basis for the mapping.

## Constraints & Assumptions

- **Scale & load**: Design for growth to **millions of users** **[stated]**. Implies horizontal scalability, a read-heavy browse/search path, transactional integrity on money and entitlement flows, durable high-volume asset delivery, and headroom for spikes (launch sales, featured drops, limited license-key pools selling out fast). No explicit launch volume was given, so assume **cheap-at-launch but no-rewrite-to-millions** as the design objective **[assumed]**.
- **Team**: Competent, cloud-agnostic engineering team **[stated]**; no stated language/framework lock-in **[stated]**. Assume small-to-mid team at launch that values a mainstream, well-staffed ecosystem over exotic tech **[assumed]**.
- **Hosting**: **Cloud-agnostic, no must-use cloud** **[stated]**. Bias toward portable, open technologies (containers, open-source data stores, S3-compatible storage, managed-anywhere engines) over proprietary lock-in, while allowing a single managed cloud at launch for speed **[assumed]**.
- **Hard constraints**:
  - **PCI DSS** applies to CAP-06 (payment) and CAP-10 (payouts). Assume **SAQ A** posture — never touch raw card data; delegate card capture/storage to a PCI-compliant gateway **[assumed]**.
  - **Financial correctness** is a hard constraint: sales, fees, refunds, chargebacks, ledger balances, and payouts must be auditable and reconcilable against the gateway (CAP-08/09/10) **[assumed, strongly implied]**.
  - **Digital-goods entitlement integrity** is a distinguishing hard constraint: an entitlement must be granted **exactly once** per paid order, delivery links/keys must be **non-leakable and revocable**, and finite license-key inventory must never be **double-sold** under concurrency (CAP-03/07/08) **[assumed, intrinsic to digital goods]**.
  - **GDPR / data-protection** obligations apply (buyer & seller PII, KYC/tax data, reviews) — need data-subject export/erasure (with financial/tax legal-retention carve-outs) and regional residency optionality **[assumed]**.
  - **KYC / AML / tax** obligations attach to seller onboarding and payouts (CAP-01/10) — identity verification, tax-form collection (e.g., W-9/W-8/DAC7-class reporting), sanctions screening **[assumed]**.
- **Existing systems**: None stated as must-integrate. Treat **payment/payout gateway**, **email/notification provider**, **object storage + CDN**, and **identity provider** as selectable third parties rather than pre-existing systems **[assumed]**.

## Architecture Overview

- **Style**: **Modular monolith at launch with pre-carved seams for service extraction** — a pragmatic hybrid. Rationale: a small competent team and an unstated (likely modest) launch volume don't justify the operational tax of full microservices, but this domain has sharp fault lines — **the money/ledger core, the entitlement/delivery core, search, and notifications** — where independent scaling and failure isolation are required at millions of users. Build one well-factored deployable, organized into strict modules with an event backbone, and design the money, entitlement, and async boundaries so the highest-pressure modules can be split out later without rewriting callers. Lowest-regret path on the stated scale ramp.
- **Shape**: A stateless API/application tier serves the web client and hosts the domain modules (onboarding, catalog, assets, search-facade, checkout, payments, entitlements/delivery, refunds, ledger, payouts, reviews, moderation, notifications). A **relational database is the system of record** for transactional state (orders, entitlements, license-key inventory, the double-entry ledger, payouts), fronted by **Redis** for hot reads and atomic inventory reservation. A dedicated **search engine** (kept in sync from catalog events) powers CAP-04 so browse/search load never contends with transactional writes. An **event backbone** carries domain events (`OrderPaid`, `EntitlementGranted`, `RefundIssued`, `ChargebackOpened`, `PayoutSettled`, `ListingPublished`) to async consumers — entitlement granting, search indexing, notifications, ledger postings, payout batching, analytics. **Object storage + a CDN with signed/expiring URLs** hold and deliver digital assets; delivery is never proxied through the app tier. Money flows are an append-only **double-entry ledger** for auditability, with the external gateway as the rail (charges, refunds, chargebacks, connected-account payouts).

## Tech Stack

### Frontend
- **Recommendation**: **TypeScript + React, server-rendered via Next.js** (App Router) as a single web app with role-aware surfaces (buyer storefront, seller dashboard, moderation/admin console). Headless component system (Radix/shadcn-style).
- **Why**: The storefront and listing/search pages (CAP-02/04) are SEO- and first-paint-sensitive — server rendering improves discovery and conversion. The seller dashboard (CAP-01/02/03/09/10), buyer library/re-download (CAP-07), and moderation console (CAP-12) are interactive React surfaces. Web-only is sufficient for the stated scope; React Native is a low-friction later path since the skill set carries over.
- **Alternatives**: **Remix** — prefer for a more web-standards data/forms model and simpler caching mentality. **Astro + islands** — prefer if the storefront is overwhelmingly content/SEO with light interactivity, pushing the dashboard into a separate SPA.

### Backend / API
- **Recommendation**: **TypeScript on Node.js (NestJS)** for the application tier, exposing a **REST/JSON API** (OpenAPI-documented) with a thin BFF for the Next.js frontend. One language across front and back; NestJS modules map cleanly onto the modular-monolith seams.
- **Why**: The workload is I/O-bound orchestration (gateway calls, search, DB, queue, storage) rather than CPU-bound — Node's strength. NestJS module/provider structure enforces the internal boundaries the architecture depends on. REST keeps the public surface cacheable and simple; GraphQL's main win (client-shaped queries) is real for the dashboards but not worth the cross-API complexity tax now.
- **Alternatives**: **Go (Echo/Fiber)** — prefer if the team is Go-native, or for later extraction of the highest-throughput services (entitlement/delivery, ledger); costs the shared-language productivity. **Java/Kotlin + Spring Boot** — prefer if the team's center of gravity is JVM and the financial domain wants its mature transactional ecosystem. **GraphQL (Apollo)** for dashboard read paths specifically — a targeted later optimization, not a foundation.

### Data storage

**Primary database (system of record)**
- **Recommendation**: **PostgreSQL** (managed), one logical database with schema-per-module discipline, primary + read-replica topology.
- **Why**: Orders, entitlements, **finite license-key inventory**, the **double-entry ledger**, refunds/chargeback adjustments, and payouts (CAP-03/05/06/07/08/09/10) demand ACID transactions and strong consistency. Two correctness properties are textbook relational concerns: (1) **exactly-once entitlement grant** per paid order — enforced with a unique constraint on `(order_id)` in the entitlements table inside the payment-confirmation transaction; (2) **no double-sale of a license key** — enforced by atomically claiming a key row (`SELECT ... FOR UPDATE SKIP LOCKED` or a status CAS) within the order transaction. Postgres scales vertically far and horizontally via replicas for the read-heavy library/dashboard reads; open-source and managed on every cloud (cloud-agnostic).
- **Alternatives**: **MySQL/MariaDB** — equivalent fit; prefer only with deeper MySQL operational muscle. **CockroachDB / Spanner-class distributed SQL** — prefer only when single-primary write throughput genuinely becomes the ceiling at very large scale; defer until proven. Do **not** put the ledger or entitlements in a document store — losing the consistency guarantees here is exactly the wrong trade.

**Cache**
- **Recommendation**: **Redis** (managed) for hot reads (listing detail, catalog pages), session/rate-limit counters, cached popular-search results, and **atomic short-TTL reservations of finite license-key inventory** during checkout (CAP-05) to prevent oversell under contention.
- **Why**: A limited license-key pool selling out during a drop is a contention hotspot; a Redis atomic reservation (e.g., decrement-with-floor / `SET NX` hold) holds stock for the checkout window, with the **authoritative claim still committed in the Postgres transaction** at payment confirmation (Redis is the fast gate, Postgres is the truth). Redis also serves the cached-popular-results path for CAP-04 and rate-limits abuse-prone endpoints (CAP-12).
- **Alternatives**: **Valkey** — drop-in open-source fork; prefer for licensing-portability peace of mind. **Memcached** — only for pure key/value caching; you lose the atomic/expiry primitives the inventory reservation relies on.

**Search engine**
- **Recommendation**: **OpenSearch** (or Elasticsearch) as a dedicated cluster powering CAP-04, fed asynchronously from catalog-change events.
- **Why**: CAP-04 needs full-text relevance, fuzzy/typo tolerance, faceted filters (category, price range, rating, format/license type), and sorting at marketplace scale — none of which Postgres does well as traffic grows. A separate engine means browse/search load never contends with transactional writes, and the index can be rebuilt/reshaped independently (replay from the event log). OpenSearch is Apache-2.0 and managed on every major cloud (cloud-agnostic).
- **Alternatives**: **Typesense / Meilisearch** — prefer at launch for far simpler ops and excellent typo-tolerance out of the box; revisit if relevance tuning and aggregation needs outgrow them. **Postgres full-text + `pg_trgm`** — viable *only* at launch volume to defer a search cluster; explicitly a bridge, not the millions-of-users answer. (Research flag below.)

**Object / blob storage + delivery**
- **Recommendation**: **S3-compatible object storage** for digital assets, with **direct-to-storage uploads via pre-signed URLs** (seller side, CAP-03) and **delivery via short-lived signed CDN URLs** (buyer side, CAP-07). Assets stored in a **private bucket**; the app tier mints time-boxed, single-purpose signed URLs and never proxies the bytes.
- **Why**: Digital goods can be large (software, media, design files) and must be (a) cheap and durable to store, (b) fast to deliver globally, and (c) **non-leakable and revocable**. Signed, expiring CDN URLs satisfy entitlement integrity (a link is useless after expiry and is only minted for a valid entitlement), keep the API tier out of the bytes path (critical for scale and cost), and give global performance. S3-compatible APIs keep this portable across clouds and to MinIO on-prem.
- **Alternatives**: Cloud-native equivalents (GCS/Azure Blob with signed URLs) — fine; standardize on the S3 API to stay portable. For the highest piracy-sensitivity goods, **per-buyer watermarking/transformation** at delivery time is a later additive step (research/solution-architect territory, not invented here).

**License-key / secret material storage**
- **Recommendation**: Store license keys/codes in **Postgres with column-level (application-layer) encryption**, keyed via the secrets/KMS layer; keys are claimed transactionally and revealed to the buyer only post-payment.
- **Why**: License keys are bearer secrets with finite inventory — they need transactional claim semantics (Postgres) plus encryption at rest beyond disk-level so a DB read alone doesn't leak sellable inventory (CAP-03/07).
- **Alternatives**: A dedicated secrets vault per key is overkill at key-pool volumes; envelope encryption in Postgres is the right granularity.

**Analytics store**
- **Recommendation**: **Defer a dedicated warehouse at launch**; serve seller dashboard analytics (sales/earnings over time) from Postgres read replicas with event-driven pre-aggregated rollup tables/materialized views. Introduce a **columnar warehouse (ClickHouse, or BigQuery/Snowflake-class)** when analytical volume/history depth strains the replicas.
- **Why**: Early dashboard analytics are bounded per-seller aggregations that replicas + rollups handle well. The events already on the backbone make adding a warehouse later additive, not a rewrite. **ClickHouse** is the opinionated pick when the time comes (cost/performance on append-heavy data; open-source/portable).

### Async / messaging

**Needed** — entitlement granting after payment, search indexing, notification fan-out (CAP-13 fans in from most capabilities), ledger postings, payout batching, and chargeback handling are all off-the-request-path work. Async eventing is core, not optional.

- **Recommendation**: **A durable, replayable event log — Apache Kafka (or a Kafka-compatible managed service)** for domain events, plus a lightweight job runner (**BullMQ on Redis**) for in-process background jobs (email rendering, report generation, retries) at launch.
- **Why**: Domain events — `OrderPaid`, `EntitlementGranted`, `RefundIssued`, `ChargebackOpened`, `PayoutSettled`, `ListingPublished` — need durable, ordered (per-key), replayable delivery to multiple independent consumers (entitlement/delivery, search indexing CAP-04, notifications CAP-13, ledger postings CAP-09, payout batching CAP-10, analytics). Ordering per `order_id` / per `seller_id` keeps ledger postings correct; replay lets the search index and analytics rollups be rebuilt; the log is also the mechanism that makes later service extraction non-breaking. BullMQ covers the cheap "do this off the request path" jobs.
- **Alternatives**: **RabbitMQ / cloud queues (SQS+SNS, Pub/Sub)** — prefer at launch if you don't yet need replay/ordering and want lower ops overhead; you give up the event-log replay that makes index/analytics/ledger rebuilds easy. **NATS JetStream** — a lighter-weight log with good ordering if Kafka's footprint is unwelcome. It is defensible to **launch on a managed queue and adopt Kafka when replay/fan-out volume demands it** — flagged for research.

### Authentication & authorization
- **Recommendation**: **A managed OIDC/OAuth2 identity provider** — self-hosted **Keycloak** for portability, or managed **Auth0/Cognito-class** for speed — issuing JWT access tokens + rotating refresh tokens (secure HTTP-only cookies). **Authorization** lives in the app tier as **role- + relationship-based access control**: roles (buyer, seller, moderator/admin) plus relationship checks (you may download only goods you hold an **entitlement** for; you may edit only your own listings; only moderators take down content).
- **Why**: No existing identity system was stated, so identity is in-scope; an OIDC IdP avoids hand-rolling password/MFA/social-login security. The marketplace-specific authorization is *not* something an IdP provides — entitlement-gated downloads (CAP-07), seller-owns-listing (CAP-02/03), verified-purchase-gated reviews (CAP-11), and moderator privileges (CAP-12) are relationship checks the platform must own. Centralize them as a NestJS policy/guard layer so every module enforces consistently. Seller onboarding KYC (CAP-01) augments identity with verification state but does not replace authentication.
- **Alternatives**: **Cloud-native managed IdP (Cognito/Identity Platform)** — prefer for fastest launch on a chosen cloud; weigh portability. **Keycloak** — prefer for cloud-agnostic self-hosting and full control; costs you operating it.

### Infrastructure & hosting
- **Recommendation**: **Containers (Docker) on managed Kubernetes** (EKS/GKE/AKS — pick one cloud at launch, stay portable), stateless app tier behind a load balancer and autoscaled horizontally; managed Postgres, Redis, OpenSearch, and event backbone; **CDN in front of object storage** for asset delivery and static assets.
- **Why**: Cloud-agnostic + growth to millions points to containers on Kubernetes as the portable, horizontally-scalable substrate — same artifacts on any cloud or on-prem. Managed data services avoid operating stateful systems while staying on open engines. The stateless app tier scales out trivially; search, cache, delivery, and the event backbone scale independently — the point of the seams.
- **Alternatives**: **PaaS (Fly.io / Render / cloud App Platform)** — strongly prefer *at launch* to skip Kubernetes overhead; the container-first design makes the eventual K8s migration mostly packaging. **Serverless functions** — good for spiky stateless edges (asset post-processing on upload, scheduled payout/rollup jobs, signed-URL minting at very high fan-out), used selectively — not as the always-warm transactional foundation.

### CI/CD & developer tooling
- **Recommendation**: **Trunk-based development with GitHub Actions (or GitLab CI)**; pipeline: lint → typecheck → unit/integration tests → build container → deploy to staging → promote to prod. **Infrastructure as Code via Terraform** (cloud-agnostic). Database migrations versioned and run in-pipeline (Prisma Migrate / Flyway). Environments dev → staging → prod, with ephemeral PR preview environments if budget allows. **Architecture fitness checks** (module-boundary/dependency linting) in CI to protect the monolith seams.
- **Why**: A modular monolith deploys as one or few artifacts — CI/CD stays simple, a major saving over microservices. Terraform keeps infra reproducible and not welded to one cloud. Migration discipline is non-negotiable given the financial and entitlement schema (ledger, entitlements, license inventory) where ad-hoc drift would be dangerous.
- **Alternatives**: **Pulumi** — prefer if the team would rather express infra in TypeScript (one language); slightly smaller ecosystem than Terraform. **GitOps (Argo CD)** — adopt once on Kubernetes for declarative deploys.

### Observability
- **Recommendation**: **OpenTelemetry** instrumentation (traces/metrics/logs, vendor-neutral) exported to a self-host-or-buy backend: **Prometheus + Grafana** (metrics), **Loki** or ELK/OpenSearch (logs), **Tempo/Jaeger** (tracing). Structured logging with correlation IDs propagated from the API through events to async consumers.
- **Why**: The hardest-to-debug paths are the async money/entitlement flows — a payment captured but entitlement not granted (CAP-06/07 error path), a refund that didn't revoke (CAP-08), a payout that silently failed (CAP-10), a notification that never fired (CAP-13). Distributed tracing across API → event log → consumers makes these diagnosable; OTel keeps the backend non-locked-in. Add **alerting on business invariants**: orders-paid-without-entitlement count, ledger-vs-gateway balance drift, payout failure rate, license-key oversell attempts, search index lag, dead-letter queue depth.
- **Alternatives**: **Datadog / Grafana Cloud / Honeycomb** — prefer managed if the team would rather not run the stack; OTel means switching backends without re-instrumenting.

### Third-party services & integrations
- **Payment & payout gateway** — implements card capture, charging, refunds, chargeback/dispute webhooks, and **connected-account payouts** for CAP-06/08/10. A gateway with marketplace/split-payment and connected-account support (**Stripe Connect-class**, or Adyen/Braintree MarketPay) keeps the platform out of direct PCI scope and provides payout rails plus chargeback webhooks. The platform's **own double-entry ledger records the truth**; the gateway moves the money.
- **KYC / identity & tax verification** — for seller onboarding (CAP-01): identity verification, sanctions screening, and tax-form collection. Often provided by the same connected-accounts gateway (Stripe Connect KYC) or a dedicated KYC vendor; **flag build-vs-buy back to the team** rather than assume.
- **Email / transactional messaging** — renders and sends receipts, delivery, payout, and moderation notices for CAP-13 (e.g., a transactional email provider).
- **Object storage + CDN** — asset storage and signed-URL delivery (CAP-03/07).
- **Push notifications** — web push (Push API) now; FCM/APNs when native apps arrive (CAP-13 push channel).
- **Content moderation / abuse detection** — listing/asset/review scanning and infringement signals (CAP-12). Start with rules/heuristics + human moderation queue; a managed moderation/classification API is the scale path — flagged for research.

### Security
- **Secrets management**: a dedicated secrets store (**HashiCorp Vault** for portability, or the chosen cloud's secrets manager / KMS) for gateway API keys, DB credentials, signing keys, and the envelope-encryption keys protecting license-key inventory. No secrets in code or images.
- **PCI scope minimization**: card data never touches the platform — use the gateway's hosted fields/tokenization to stay at SAQ A; store only tokens/references (CAP-06/10).
- **Entitlement & delivery integrity** (the digital-goods-specific control): private asset bucket; **short-lived, single-purpose signed CDN URLs minted only against a valid entitlement**; entitlements revocable on refund/chargeback (CAP-08); download attempts authorized by the relationship/policy layer and rate-limited; optional per-buyer watermarking for high-risk goods as a later step.
- **Encryption**: TLS everywhere in transit; encryption at rest on Postgres, Redis, object storage, backups; **application-layer (envelope) encryption** for the most sensitive data — license keys, KYC/tax/PII, payout bank details — above the storage defaults.
- **GDPR controls**: data-subject export and erasure (profile, reviews, KYC where legally erasable) with **financial/tax legal-retention carve-outs** on ledger/order records; regional residency achievable via per-region Postgres/storage if required.
- **Application security**: input validation at the API boundary; output encoding; **idempotency keys on all money- and entitlement-moving operations** (charge, refund, entitlement grant, payout) to make retries safe; **signed gateway webhooks with replay protection** for payment/refund/chargeback events; rate limiting (Redis-backed) on auth, search, download, and checkout; audit logging of moderator/admin actions (CAP-12) and ledger adjustments.
- **AV/malware scanning of uploaded assets** (CAP-03): scan seller-uploaded files asynchronously before they become deliverable, since buyers download executable/openable content.

## Capability → Tech Mapping

| Capability | Implemented by | Notes |
|-----------|----------------|-------|
| CAP-01 Seller onboarding | NestJS onboarding module + IdP (OIDC) + KYC/connected-account provider + Postgres (seller, verification state) | Authentication via IdP; KYC/tax/payout-account setup via gateway/KYC vendor; onboarding state gates listing/payout eligibility. Build-vs-buy KYC flagged. |
| CAP-02 Listing & catalog management | NestJS catalog module + Postgres (listings, pricing, versions); emits `ListingPublished`/update events to Kafka | Seller-owns-listing enforced in policy layer; publish event drives async search indexing (no synchronous coupling to search). |
| CAP-03 Digital asset & inventory/license mgmt | NestJS assets module + S3 pre-signed uploads + async AV scan + Postgres (asset metadata, encrypted license-key pool) | Keys envelope-encrypted; finite inventory rows claimed transactionally; assets private until scanned & published. |
| CAP-04 Search & discovery | OpenSearch cluster fed from catalog events + Redis-cached popular results | Separate engine so browse/search never hits transactional DB; facets (category/price/rating/format), fuzzy matching, relevance ranking. |
| CAP-05 Cart & checkout | NestJS checkout module + Postgres (orders, ACID) + Redis (atomic finite-inventory reservation, TTL) | Reservation in Redis holds limited license stock during checkout window; authoritative claim committed in the order transaction; order state machine in Postgres. |
| CAP-06 Payment processing | NestJS payments module + payment gateway (charge/capture) + Postgres + Kafka (`OrderPaid`); idempotency keys + signed webhooks | Gateway tokenizes cards (SAQ A); idempotency keys make retries safe; `OrderPaid` triggers entitlement grant + ledger posting + notification. |
| CAP-07 Digital delivery & entitlements | NestJS entitlements module (Kafka consumer of `OrderPaid`) + Postgres (entitlements, unique on order_id) + signed CDN URLs / license-key reveal + buyer library | Exactly-once grant via unique constraint inside payment txn; delivery via short-lived signed URLs / decrypted key; library re-download re-mints signed URLs. |
| CAP-08 Refunds & chargebacks | NestJS refunds module + gateway refund API + chargeback webhook consumer + Postgres ledger entries + entitlement revocation; emits `RefundIssued`/`ChargebackOpened` | Refund/chargeback writes reversing ledger entries and (per policy) revokes the entitlement (signed URLs stop minting); idempotent; reconciliation against gateway. |
| CAP-09 Seller ledger | NestJS ledger module as Kafka consumer (postings) + Postgres double-entry ledger (append-only) | Every sale/fee/refund/chargeback/adjustment is a balanced posting keyed per seller; balance derivable and reconcilable against the gateway. |
| CAP-10 Payouts | NestJS payouts module + Postgres ledger + gateway connected-account transfers + Kafka consumer (batching) + scheduled jobs | Schedule/threshold-driven; batches transfers to cut fees; idempotent transfers; failed-payout retries + seller notification; respects KYC/onboarding completion. |
| CAP-11 Reviews & ratings | NestJS reviews module + Postgres (reviews, rating aggregates) + verified-purchase check (entitlement) + moderation hold | Only entitlement-holders review (verified purchase); rating recalculation in transaction; review content flows to moderation scanning. |
| CAP-12 Moderation & trust/safety | NestJS moderation module + admin console (Next.js) + moderation/classification API + AV scan signals + Postgres (cases, actions, audit log) | Human review queue + automated signals; takedown unpublishes listing/asset and (per policy) affects entitlements; all moderator actions audit-logged. |
| CAP-13 Notifications | NestJS notifications module as Kafka consumer (fan-in) + Postgres (in-app inbox) + email provider + web push | Subscribes to domain events; per-event preference lookup; dedup/digest batching; critical notices (receipt, chargeback, payout failure, moderation action) bypass opt-out. |

## Key Architecture Decisions

### AD-01: Modular monolith with pre-carved seams, not microservices (yet)
- **Decision**: Build a single deployable modular monolith (NestJS modules) with strict internal boundaries and an event backbone, designed so entitlement/delivery, payments/ledger, search, and notifications can be extracted into services later.
- **Context**: Designing for millions of users with a small competent team and (unstated, likely modest) launch volume; the domain has clear fault lines.
- **Rationale**: Microservices now would impose distributed-systems tax (network failures, distributed transactions across the money/entitlement flows, deployment overhead) that the launch volume can't justify and that would slow the team. A modular monolith keeps money and entitlement grants in-process and transactional (the exactly-once and no-oversell invariants are far easier within one DB transaction) while events pre-pay the cost of later extraction. Lowest-regret on the scale ramp.
- **Tradeoffs**: Requires discipline to keep boundaries honest (no cross-module table access); a sloppy team turns it into a big ball of mud. Mitigated by schema-per-module, events as the cross-module write contract, and dependency linting in CI.

### AD-02: Postgres as system of record with a double-entry ledger for money
- **Decision**: All transactional state in PostgreSQL; model sales, fees, refunds, chargebacks, adjustments, and payouts as an append-only double-entry ledger.
- **Context**: CAP-06/08/09/10 demand auditability, reconciliation, and correctness; chargebacks arrive asynchronously and must reverse prior postings.
- **Rationale**: ACID transactions and relational integrity suit money state machines. A double-entry ledger makes every seller balance derivable and reconcilable against the gateway, and turns "charged but not posted" or "refunded but balance wrong" into detectable, repairable invariants rather than silent loss. Chargebacks become reversing postings, not destructive edits.
- **Tradeoffs**: Single-primary write ceiling exists far out; deferred to distributed SQL only when proven. Ledger discipline adds modeling effort up front, repaid in audit/dispute confidence.

### AD-03: Entitlement is the authoritative grant; delivery is via short-lived signed CDN URLs
- **Decision**: On `OrderPaid`, grant a single entitlement (unique on `order_id`) inside the payment-confirmation transaction; deliver assets/keys only by minting short-lived, single-purpose signed CDN URLs (or decrypting the claimed license key) against a valid, non-revoked entitlement. The app tier never proxies asset bytes.
- **Context**: Digital goods must be granted exactly once, delivered without leaking, revocable on refund/chargeback, and delivered at scale/global low latency (CAP-07/08).
- **Rationale**: Separating the durable *entitlement* (in Postgres, the truth) from ephemeral *delivery* (signed URLs from the CDN) gives exactly-once semantics, revocability (stop minting URLs / rotate), non-leakability (links expire), and scale (bytes never touch the API tier). A unique constraint makes duplicate webhooks/retries harmless.
- **Tradeoffs**: Already-downloaded bytes can't be un-downloaded — revocation prevents *future* access, not retroactive recovery; high-piracy goods may need watermarking (a later additive step, not invented here). Signed-URL minting must be cheap and is itself an extraction candidate at extreme fan-out.

### AD-04: Finite license-key inventory protected by Redis reservation + Postgres authoritative claim
- **Decision**: Hold limited license-key stock with an atomic Redis reservation during the checkout window; commit the authoritative key claim (`FOR UPDATE SKIP LOCKED` / status CAS) inside the order transaction at payment confirmation.
- **Context**: Limited license-key pools can sell out under high concurrency (drops/sales) and must never be double-sold (CAP-03/05).
- **Rationale**: Redis gives a fast, expiring gate that prevents most oversell and protects the DB from a thundering herd; Postgres gives the authoritative, transactional claim that is the actual correctness guarantee. The two layers are complementary (speed vs. truth).
- **Tradeoffs**: A reservation that expires before payment frees stock back, which is correct but can frustrate slow buyers; tune the TTL. Two systems to reason about — mitigated by treating Redis as advisory and Postgres as authoritative.

### AD-05: Dedicated search engine (OpenSearch) fed asynchronously from events
- **Decision**: Run search in a separate engine, kept eventually consistent via `ListingPublished`/update events, rather than querying Postgres for browse/search.
- **Context**: CAP-04 needs relevance ranking, fuzzy matching, and faceted filters under read-heavy traffic.
- **Rationale**: Postgres full-text can't meet relevance/facet needs as traffic grows, and browse traffic would contend with transactional writes. A separate engine isolates that load and is rebuildable from the event log.
- **Tradeoffs**: Eventual consistency — a just-published listing may take seconds to appear; acceptable for discovery. Adds a stateful system to operate (use managed).

### AD-06: Event backbone (Kafka-class) as the async + future-extraction spine
- **Decision**: A durable, replayable event log carries domain events to async consumers (entitlement granting, indexing, ledger postings, notifications, payout batching, analytics).
- **Context**: Entitlement granting, notification fan-in (CAP-13), ledger postings, and chargeback handling must run off the request path and be ordered/replayable.
- **Rationale**: Log-based eventing gives per-key ordering (per order/per seller, keeping ledger postings correct), replay (rebuild index/rollups), clean fan-out, and is the mechanism that makes later extraction non-breaking. Right-sizing note: a simpler managed queue is an acceptable launch substitute if replay isn't yet needed (research flag).
- **Tradeoffs**: Operational weight and a learning curve; eventual-consistency reasoning in consumers. Mitigated by managed Kafka and idempotent, replay-safe consumers.

### AD-07: Cloud-agnostic, container-first infrastructure on open engines
- **Decision**: Docker + managed Kubernetes with Terraform, on open-source data/search/event engines available managed on any cloud; PaaS acceptable at launch.
- **Context**: Explicit cloud-agnostic constraint plus growth to millions.
- **Rationale**: Containers + open engines + Terraform keep the platform portable and horizontally scalable without welding it to one provider's proprietary services. PaaS at launch avoids K8s overhead while container artifacts make the eventual migration low-risk.
- **Tradeoffs**: Operating open engines (even managed) is more work than going all-in on one cloud's proprietary stack — the price of portability. Kubernetes is overkill until volume grows — hence PaaS-first.

## Risks & Tradeoffs

- **Entitlement/payment consistency under failure.** A captured payment whose entitlement grant or ledger posting fails (or a duplicate webhook double-granting) is the highest-stakes digital-goods path. *Mitigation*: grant inside the payment-confirmation transaction with a unique constraint on `order_id`; idempotency keys; signed webhooks with replay protection; a reconciliation job that finds paid-but-ungranted orders and ledger-vs-gateway drift, with alerting.
- **Asset/link leakage and post-refund piracy.** Signed URLs limit exposure but already-downloaded bytes can't be recalled; revocation only stops future access. *Mitigation*: short TTLs, single-purpose URLs, download rate-limiting, private buckets; per-buyer watermarking for high-risk goods as a later step (flag to solution-architect for policy).
- **License-key oversell under contention.** Concurrency on a limited pool during a drop can double-sell without care. *Mitigation*: Redis reservation gate + Postgres authoritative claim (`SKIP LOCKED`/CAS); oversell-attempt alerting.
- **Chargeback liability and timing.** Chargebacks arrive days/weeks later, after payout may already have occurred, creating negative seller balances and platform liability. *Mitigation*: ledger models negative balances and clawbacks; payout holds/reserves policy; reconciliation — but the **liability/clawback policy itself is a functional decision for solution-architect** (flagged below), not invented here.
- **Modular-monolith boundary erosion.** The extraction story collapses if modules share tables or call internals. *Mitigation*: schema-per-module, events as the only cross-module write contract, dependency linting in CI.
- **Malware in uploaded assets.** Buyers download seller-supplied files. *Mitigation*: async AV/malware scan before an asset becomes deliverable; quarantine on failure.
- **Premature distribution / over-engineering.** Kafka + Kubernetes + warehouse on day one for a modest launch burns runway. *Mitigation*: explicit launch-vs-scale split — PaaS + managed queue + replica analytics at launch, seams designed so each upgrade is additive.
- **Trust & safety / fraud.** Stolen-card purchases of instantly-deliverable goods, fake reviews, infringing listings. *Mitigation*: relationship/verified-purchase checks, moderation scanning, velocity/anomaly signals — but detection sophistication is a known gap (research flag).

## Research Suggestions

High-stakes or uncertain choices to validate with the researcher skill before committing:

- **Marketplace payment/payout gateway with connected accounts, KYC, and chargeback handling (build-vs-buy and vendor selection).** This is the most consequential, hard-to-reverse integration — it shapes PCI scope, payout rails, KYC/tax compliance, and chargeback flow, and the ledger/payout design depends on its exact capabilities. Suggested researcher query: *"Payment platform selection for a two-sided digital-goods marketplace needing connected-account payouts, seller KYC/AML and tax-form (W-9/W-8/DAC7) handling, refunds, and chargeback/dispute webhooks while keeping the platform at PCI SAQ A: Stripe Connect vs. Adyen for Platforms/MarketPay vs. Braintree/PayPal Commerce Platform — capabilities, payout reserve/negative-balance handling, fees, data portability, and integration effort."*
- **Async backbone: Kafka-class event log vs. managed queue at this scale ramp.** A consequential infrastructure choice (it shapes consumers, ordering, ledger-posting correctness, and the extraction story); the right answer depends on real replay/fan-out needs vs. operational budget. Suggested researcher query: *"Event streaming backbone selection for a transactional digital-goods marketplace scaling from launch to millions of users: Apache Kafka vs. managed cloud queues (SQS/SNS, Pub/Sub) vs. NATS JetStream — ordering guarantees, replay, idempotency/exactly-once, operational cost, and migration path from a simple queue to a log."*
- **(Secondary) Search technology: managed OpenSearch/Elasticsearch vs. Typesense/Meilisearch vs. Postgres FTS bridge.** Search drives CAP-04 conversion; relevance, facets, and operational cost differ sharply. Suggested researcher query: *"Search engine selection for a digital-goods marketplace catalog requiring full-text relevance, typo tolerance, faceted filtering, and sorting at scale: OpenSearch/Elasticsearch vs. Typesense vs. Meilisearch vs. Postgres full-text+pg_trgm — relevance quality, operational burden, and cost."*
- **(Secondary) Digital-asset protection / anti-piracy and content moderation tooling.** Build-vs-buy for watermarking, infringement detection, and content/abuse moderation. Suggested researcher query: *"Build-vs-buy digital-goods anti-piracy (per-buyer watermarking, signed-URL/DRM strategies) and content moderation/infringement detection for a marketplace's listings, assets, and reviews — accuracy, latency, integration, and cost."*

## Open Questions

- **Entitlement-revocation policy on refund/chargeback** — Does a refund or chargeback revoke the buyer's entitlement and library access, or only adjust balances? This affects CAP-07/08 design and is a **functional decision for solution-architect**, not invented here.
- **Chargeback liability & seller clawback policy** — Who bears a chargeback after payout (platform vs. seller), and does the platform hold reserves or allow negative seller balances with clawback? Shapes the ledger and payout logic (CAP-08/09/10); functional decision for solution-architect.
- **License-pool semantics** — Are finite license keys the dominant model, or mostly unlimited re-deliverable goods? Determines how central the reservation/claim machinery (AD-04) is. Functional clarification.
- **KYC/tax scope & geography** — Which jurisdictions, tax-reporting regimes, and sanctions screening apply to sellers (CAP-01/10)? Drives the KYC vendor/build decision and data-retention design.
- **Identity provider choice** — Self-hosted Keycloak (portability) vs. a managed IdP (speed)? Needs a team call given the cloud-agnostic constraint.
- **Data residency** — Are there regional data-residency requirements forcing per-region Postgres/storage from the start, or is a single region acceptable at launch?

## Next Steps

1. Stand up the modular-monolith skeleton (NestJS modules + Postgres + Terraform) on a PaaS target, with CI running typecheck/test/migrate and module-boundary linting from day one.
2. Spike the money + entitlement core together: order state machine, double-entry ledger schema, payment-gateway charge → `OrderPaid` → exactly-once entitlement grant (unique on order_id) → ledger posting, with idempotency keys, signed webhooks, and a reconciliation job; validate against the gateway sandbox including a refund and a simulated chargeback.
3. Spike delivery: private S3 bucket + signed CDN URLs + buyer re-download; spike the finite-license reservation (Redis gate + Postgres `SKIP LOCKED` claim) under concurrency to prove no oversell.
4. Spike search: index listings from `ListingPublished` events into OpenSearch (or Typesense for the launch comparison) and validate relevance, facets, and typo tolerance on realistic catalog data.
5. Resolve the high-stakes integration choice with the AD/research flag — select the marketplace payment/payout/KYC platform — and confirm its connected-account, chargeback, and reserve/negative-balance capabilities, since the ledger and payout design depend on it.
6. Send the open functional questions (entitlement revocation, chargeback liability/clawback, license-pool semantics, KYC scope) to solution-architect before build.
7. Hand this document to the librarian skill to persist as a spec artifact.

---
*Technical architecture produced by technical-architect skill. Use the librarian skill to persist this artifact.*
