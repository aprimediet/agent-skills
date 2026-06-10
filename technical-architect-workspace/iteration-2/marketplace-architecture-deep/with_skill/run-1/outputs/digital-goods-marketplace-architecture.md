# Digital-Goods Marketplace — Technical Architecture

> Technical Architect | Depth: deep | Generated: 2026-06-10

## Source Breakdown

No solution-architect capability breakdown was retrievable — the librarian skill is unavailable in this run, so the capability list below is an **inline breakdown derived directly from the task statement**, not invented. Each capability maps to one of the ~15 areas named in the task (seller onboarding, listing/asset management, search, checkout, payment, digital delivery/entitlements, refunds/chargebacks, seller ledger, payouts, reviews, moderation, notifications). It is captured here so the technical mapping stays honest; **running the solution-architect skill first would produce a stronger, validated breakdown** (cancellation/refund policy, entitlement model, fee schedule, and payout rules in particular).

Inline capability list (CAP-NN):

- **CAP-01 Seller onboarding & KYC** — seller signup, identity/business verification, tax/banking details capture for payouts, seller account states (pending/active/suspended).
- **CAP-02 Listing management** — create/edit/version listings for digital goods (title, description, pricing, media, categories), draft/publish lifecycle.
- **CAP-03 Asset & inventory/license management** — upload and store the sellable digital asset(s); manage license keys/seats/quantity for license-limited goods; asset versioning.
- **CAP-04 Search & discovery** — full-text search, faceted filtering (category, price, rating, format), relevance ranking, browse.
- **CAP-05 Checkout** — cart, order creation, price/tax computation, idempotent order placement.
- **CAP-06 Payment** — charge the buyer via gateway, capture, store payment references (no raw card data).
- **CAP-07 Digital delivery & entitlements** — on successful payment, grant the buyer an entitlement and deliver the asset (secure download link / license key issuance) and re-download access.
- **CAP-08 Refunds & chargebacks** — buyer-initiated refunds, gateway chargeback/dispute handling, entitlement revocation, ledger reversal.
- **CAP-09 Seller ledger** — append-only double-entry record of seller earnings, platform fees, refunds, chargebacks, adjustments; reconcilable against the gateway.
- **CAP-10 Payouts** — scheduled/threshold-based payout of seller balance to bank accounts via gateway transfers; payout states and retries.
- **CAP-11 Reviews & ratings** — buyers who own an entitlement rate/review goods; aggregate rating per listing/seller.
- **CAP-12 Moderation** — review listings, assets, and review content for prohibited/IP-infringing/malicious material; takedown/suspend actions; admin queue.
- **CAP-13 Notifications** — transactional and lifecycle notifications (order receipt, delivery, payout sent, refund processed, moderation action) across email/in-app/push.
- **CAP-14 Buyer storefront & purchase library** — browse/listing detail pages and a buyer's "my purchases" library with re-download/entitlement view.
- **CAP-15 Seller dashboard & analytics** — seller-facing earnings, sales, payout, and listing-performance views.

> CAP-14 and CAP-15 are surfacing the two implicit user-facing surfaces the task describes ("buyers browse and purchase"; "sellers list items, manage inventory, receive payouts"). They are presentation/aggregation of capabilities above, not new business logic. If the breakdown owner considers them out of scope, drop them — no architecture below depends on their being separate.

## Constraints & Assumptions

- **Scale & load**: Design for growth to **millions of users** **[stated]**. Implies horizontal scalability, read-heavy search/storefront, transactional integrity on money flows (orders, ledger, payouts), large-binary asset storage/delivery at CDN scale, and headroom for spikes (launches, sales). Start cheap, avoid a rewrite to reach millions **[assumed]**.
- **Team**: Competent, cloud-agnostic team, no language/framework lock-in **[stated]**. Assume a small-to-mid team that values a mainstream, well-staffed ecosystem and productivity over exotic tech **[assumed]**.
- **Hosting**: **Cloud-agnostic**, no must-use cloud **[stated]**. Bias toward portable, open technologies (containers, open-source data stores, S3-compatible storage, managed-anywhere services) over proprietary lock-in; a single managed cloud at launch is acceptable for speed **[assumed]**.
- **Hard constraints**:
  - **PCI DSS** applies to CAP-06 (payment) and CAP-10 (payout). Assume **SAQ A** posture — never touch raw card data; delegate card capture/storage to a PCI-compliant gateway, store only tokens/references **[assumed]**.
  - **GDPR / data-protection** obligations (buyer & seller PII, reviews, payout banking details) — need data-subject export/erasure and regional residency optionality **[assumed]**.
  - **Financial correctness** is a hard constraint: order totals, platform fees, refunds, chargebacks, seller ledger, and payouts must be auditable and reconcilable **[assumed, strongly implied by the seller-ledger/payout/refund/chargeback capabilities]**.
  - **KYC/AML & tax** obligations for seller onboarding/payouts (CAP-01, CAP-10) — identity/business verification and tax reporting are required for marketplaces that pay out funds **[assumed]**.
  - **Asset protection / anti-piracy** — sold assets are the seller's IP; delivery must prevent trivial leakage (no public URLs, signed/expiring access, entitlement gating) **[assumed]**.
- **Existing systems**: None stated — treat identity, payment gateway, email, and object storage as **services to select** rather than pre-existing integrations (this differs from a typical brownfield breakdown) **[assumed]**.

## Architecture Overview

- **Style**: **Modular monolith at launch, with a small set of pre-carved seams for extraction into services** — a pragmatic hybrid. Rationale: the team and launch volume don't justify the operational tax of full microservices, but the domain has *natural fault lines* — search, payments/ledger, asset delivery, moderation, notifications — where independent scaling and failure isolation will be required at millions of users. Build one deployable app organized into strict modules, with money and async boundaries designed so the highest-pressure modules can be split out later without rewriting callers. Lowest-regret path: avoids premature distribution while pre-paying the design cost of the seams that scale demands.
- **Shape**: A stateless API/application tier serves the buyer storefront and seller dashboard and houses the domain modules (onboarding, listings, assets/entitlements, search-facade, checkout, payments, delivery, refunds, ledger, payouts, reviews, moderation, notifications). A **relational database** is the system of record for transactional state (orders, entitlements, ledger, payouts, disputes), fronted by a **cache** for hot reads and idempotency/rate-limit state. A dedicated **search engine** (kept in sync from listing-change events) powers CAP-04 so discovery never contends with the transactional database. An **event backbone** carries domain events (`OrderPaid`, `EntitlementGranted`, `RefundProcessed`, `ChargebackReceived`, `PayoutSent`, `ListingPublished`, `ReviewPublished`) to async consumers — notifications, search indexing, analytics, payout batching, ledger postings. **Object storage holds the sellable digital assets and listing media**, and **digital delivery is gated**: buyers never get a public URL — they get short-lived signed download links (or issued license keys) only after an entitlement is verified, served through a CDN. The money flows (fees, refunds, chargebacks, payouts) are an append-only **double-entry ledger** for auditability, with the external payment gateway as the rail.

## Tech Stack

### Frontend
- **Recommendation**: **TypeScript + React, server-rendered via Next.js** (App Router), as a single web app with role-aware surfaces — public/buyer storefront (CAP-04, CAP-14), buyer purchase library (CAP-14), and seller dashboard (CAP-02, CAP-03, CAP-15) — plus an internal moderation console (CAP-12). Headless component system (Radix/shadcn-style).
- **Why**: Storefront and listing-detail pages (CAP-04/CAP-14) are SEO- and first-paint-sensitive — SSR/ISR improves discovery and conversion. Dashboards and checkout are interactive and benefit from React's ecosystem. Web-first; React Native is a low-friction future path since the skill set carries over.
- **Alternatives**: **Remix** — prefer for a more web-standards-centric data/forms model and simpler caching mentality. **SvelteKit** — leaner runtime/bundle if the team has Svelte depth; smaller hiring pool at marketplace scale.

### Backend / API
- **Recommendation**: **TypeScript on Node.js (NestJS)** for the application tier, exposing a **REST/JSON API** (OpenAPI-documented) with a thin BFF for the Next.js frontend. One language across front/back reduces context-switching; NestJS modules map cleanly onto the modular-monolith seams.
- **Why**: The workload is I/O-bound orchestration (gateway, search, DB, queue, object storage) where Node excels. NestJS's module/provider structure enforces the internal boundaries the architecture depends on. REST keeps the public surface simple and cacheable; GraphQL's client-shaped-query win is real for the seller dashboard but not worth the platform-wide complexity tax now.
- **Alternatives**: **Go (Echo/Fiber)** — prefer if the team is Go-native or if the payments/ledger/payout and delivery-signing paths later need very high throughput and tight latency/footprint; costs the shared-language productivity. **Java/Kotlin + Spring Boot** — prefer if the team's center of gravity is JVM and the financial domain wants its mature transactional ecosystem. **GraphQL (Apollo) for the seller-dashboard read paths specifically** — a targeted later optimization, not a foundation.

### Data storage

**Primary database (system of record)**
- **Recommendation**: **PostgreSQL** (managed), one logical database with schema-per-module discipline, primary + read-replica topology.
- **Why**: Orders, entitlements, the seller ledger, refunds/chargebacks, and payouts (CAP-05–CAP-10) demand ACID transactions, strong consistency, and correctness. Entitlement grants and ledger postings are exactly what relational + transactions are built for. Postgres scales vertically a long way and horizontally via read replicas for read-heavy storefront/library/dashboard reads; open-source and managed on every cloud (cloud-agnostic).
- **Alternatives**: **MySQL/MariaDB** — equivalent fit; prefer only with deeper MySQL operational muscle. **CockroachDB / Spanner-class distributed SQL** — prefer only when single-primary write throughput becomes the genuine ceiling; defer until proven. Do **not** put the ledger or entitlements in a document store — the consistency guarantees are the whole point.

**Cache**
- **Recommendation**: **Redis** (managed) for hot reads (listing/storefront), session/rate-limit counters, idempotency-key storage for money operations, and short-TTL signed-URL/download-token bookkeeping.
- **Why**: Idempotent checkout/payment/refund/payout operations need a fast atomic store for idempotency keys; rate limiting on auth, search, checkout, and download endpoints protects the platform; cached popular listings/search results keep storefront latency low.
- **Alternatives**: **Valkey** — drop-in open-source fork; prefer for licensing portability. **Memcached** — only for pure key/value caching; loses the atomic primitives idempotency/rate-limiting rely on.

**Search engine**
- **Recommendation**: **OpenSearch** (or Elasticsearch) as a dedicated cluster powering CAP-04, fed asynchronously from listing-change events.
- **Why**: CAP-04 needs full-text relevance scoring, fuzzy/typo tolerance, faceted filters (category, price range, rating, format), and fast popular-result reads — none of which Postgres does well at marketplace scale. A separate engine means discovery load never contends with transactional writes, and the index can be rebuilt/reshaped independently (replay from the event log). OpenSearch is Apache-2.0 and managed on every major cloud.
- **Alternatives**: **Typesense / Meilisearch** — prefer at MVP for far simpler ops and excellent typo-tolerance out of the box; revisit when relevance tuning/aggregation needs grow. **Postgres full-text + `pg_trgm`** — viable *only* at launch volume to defer a search cluster; explicitly a bridge, not the millions-of-users answer. Research flag below.

**Object / blob storage (the sellable assets + media)**
- **Recommendation**: **S3-compatible object storage**, with **private buckets** for sold assets (CAP-03) and CDN-fronted delivery only via short-lived signed URLs (CAP-07); listing media (CAP-02) in a separate public-read-via-CDN path. Seller uploads go direct-to-storage via pre-signed PUT URLs.
- **Why**: Digital assets are the product — large binaries that must never be in the DB and must never be publicly addressable. Pre-signed direct uploads keep the API out of the bytes path; private buckets + per-entitlement signed GETs enforce that only paying owners can download (anti-piracy). A CDN serves media globally and accelerates large authorized downloads. S3-compatible APIs keep this portable (GCS/Azure Blob/MinIO).
- **Alternatives**: Cloud-native equivalents (GCS/Azure Blob) — fine, but standardize on the S3 API for portability. For very large assets, consider **multipart upload + resumable** flows.

**Analytics store**
- **Recommendation**: **Defer a dedicated warehouse at launch**; serve CAP-15 seller dashboards from Postgres read replicas with pre-aggregated rollup tables/materialized views updated from events. Introduce a **columnar warehouse (ClickHouse, or BigQuery/Snowflake-class)** when analytical query volume or history depth strains the replicas.
- **Why**: CAP-15 dashboards are bounded, per-seller aggregations (earnings, sales, payouts, listing performance over time windows) that replicas + rollups handle well early. Standing up a warehouse before there's data to justify it is over-engineering; the events already on the backbone make adding one later additive, not a rewrite. **ClickHouse** is the opinionated pick when the time comes (cost/performance on append-heavy analytical data, open-source/portable).

### Async / messaging

**Needed** — CAP-13 (notifications) fans in from most capabilities; CAP-06/07/08/10 trigger downstream money, delivery, and notification flows; CAP-04 indexing and CAP-15 analytics are event-driven. Async eventing is core, not optional.

- **Recommendation**: **A durable, replayable event log — Apache Kafka (or a Kafka-compatible managed service)** for domain events, plus a lightweight job runner (**BullMQ on Redis**) for in-process background jobs (email rendering, signed-URL minting at scale, report generation, retries) at launch.
- **Why**: Domain events — `OrderPaid`, `EntitlementGranted`, `RefundProcessed`, `ChargebackReceived`, `PayoutSent`, `ListingPublished`, `ReviewPublished` — need durable, replayable, ordered delivery to multiple independent consumers (notifications CAP-13, search indexing CAP-04, analytics rollups CAP-15, payout batching CAP-10, ledger postings CAP-09). A log-based backbone gives ordering per key (per order / per seller ledger), replay (rebuild search index or rollups), and clean fan-out — and is the mechanism that lets modules be extracted into services later without changing producers. BullMQ covers the simpler off-request-path work cheaply.
- **Alternatives**: **RabbitMQ / cloud queues (SQS+SNS, Pub/Sub)** — prefer at MVP if replay/ordering isn't yet needed and you want lower operational overhead; you give up event-log replay that makes index/analytics rebuilds easy. **NATS JetStream** — lighter-weight log with good ordering if Kafka's footprint is unwelcome. It is defensible to **launch on a managed cloud queue and adopt Kafka when replay/fan-out demands it** — research flag below.

### Authentication & authorization
- **Recommendation**: **A managed/portable identity provider via OIDC/OAuth2** — **Keycloak** (self-hosted, portable) as the cloud-agnostic default, or a managed IdP (Auth0/Cognito) for speed. The app tier consumes signed tokens (JWT access tokens, rotating refresh tokens in secure HTTP-only cookies). **Authorization** lives in the app tier as **role- + relationship-based access control**: roles (buyer, seller, moderator/admin) plus relationship checks — e.g., you can download/re-download (CAP-07/CAP-14) only an asset you hold an entitlement for; you can review (CAP-11) only a good you've purchased; you can edit a listing only as its owning seller.
- **Why**: No identity system is stated, so one must be selected; OIDC keeps it portable and lets the storefront, dashboard, and moderation console share one identity. The high-value authorization is domain-specific — **entitlement checks are the linchpin of anti-piracy and review integrity** — and must be owned in-app as a uniform policy/guard layer so every download, license-key reveal, and review write is gated consistently.
- **Alternatives**: If a buyer-friction-free experience matters, add **social login** via the IdP. For fine-grained relationship authz at scale, a policy engine (**OpenFGA / OPA**) is the documented path; start with in-app guards and adopt a policy engine if rules proliferate.

### Infrastructure & hosting
- **Recommendation**: **Containers (Docker) on Kubernetes** (managed: EKS/GKE/AKS — pick one cloud at launch, stay portable), stateless app tier behind a load balancer and autoscaled horizontally; managed services for Postgres, Redis, OpenSearch, and the event backbone; **CDN in front of object storage** for both media and authorized large-asset delivery.
- **Why**: Cloud-agnostic + millions-of-users growth points to containers on Kubernetes as the portable, horizontally-scalable substrate — the same artifacts run on any cloud or on-prem. Managed data services avoid operating stateful systems yourself while staying on open engines. The stateless app tier scales out trivially; search, cache, delivery, and the event backbone scale independently — the point of the seams. A CDN is non-negotiable for digital-goods delivery (large downloads, global buyers, origin offload).
- **Alternatives**: **PaaS (Fly.io / Render / cloud App Platform)** — strongly prefer *at MVP* to avoid Kubernetes overhead at low volume; the container-first design makes the K8s migration mostly packaging, not rewriting. **Serverless functions** — good for spiky, stateless edges (asset post-processing/scanning on upload, signed-URL minting, scheduled payout/report jobs); a poor fit for the always-warm transactional core, so use selectively.

### CI/CD & developer tooling
- **Recommendation**: **Trunk-based development with GitHub Actions (or GitLab CI)**; pipeline runs lint → typecheck → unit/integration tests → build container → deploy to staging → promote to prod. **Infrastructure as Code via Terraform** (cloud-agnostic). Database migrations versioned and run in-pipeline (Prisma Migrate / Flyway). Environments dev → staging → prod, with ephemeral preview environments per PR if budget allows. **Module-boundary linting** (dependency-cruiser/Nx-style) enforced in CI to keep the monolith's seams honest.
- **Why**: A modular monolith deploys as one or few artifacts, so CI/CD stays simple — a major saving over microservices. Terraform keeps infra reproducible and not welded to one cloud. Migration discipline is non-negotiable given the financial schema (ledger, entitlements, payouts) where schema drift would be dangerous.
- **Alternatives**: **Pulumi** — prefer if the team would rather express infra in TypeScript; smaller ecosystem than Terraform. **GitOps (Argo CD)** — adopt once on Kubernetes for declarative deploys.

### Observability
- **Recommendation**: **OpenTelemetry** instrumentation (traces/metrics/logs, vendor-neutral) exported to a backend you can self-host or buy: **Prometheus + Grafana** (metrics/dashboards), **Loki** or an OpenSearch/ELK stack (logs), **Tempo/Jaeger** (tracing). Structured logging with correlation IDs propagated from the API through events to async consumers.
- **Why**: Money flows and async fan-out are the hardest things to debug — a payment captured but entitlement not granted (CAP-06→CAP-07), a payout that silently failed (CAP-10), a chargeback that didn't reverse the ledger (CAP-08), a notification that never fired (CAP-13). Distributed tracing across API → event backbone → consumers makes those diagnosable. OTel keeps the observability vendor swappable. Add **alerting on financial and delivery invariants**: ledger-vs-gateway balance mismatch, paid-orders-without-entitlement, dead-letter-queue depth, payout failure rate, search index lag, signed-URL error rate.
- **Alternatives**: **Datadog / Grafana Cloud / Honeycomb** — prefer managed if the team would rather not run the stack; OTel instrumentation lets you switch backends without re-instrumenting.

### Third-party services & integrations
- **Payment gateway** — card capture, charge/capture, refunds, chargeback/dispute webhooks, connected-account payouts and transfers for CAP-06/08/10. A gateway with **marketplace/split-payment and connected-account support** (Stripe Connect-class, or Adyen/Braintree MarketPay) is what keeps the platform out of direct PCI scope and provides payout rails. The platform's **own ledger records truth**; the gateway moves money and is the source of chargeback events.
- **KYC/AML & tax** — seller identity/business verification and tax-form collection for CAP-01/CAP-10. Stripe Connect (or a dedicated KYC provider + tax service like Stripe Tax/Avalara) handles verification and tax calculation/reporting; the platform stores verification status and tax references, not raw documents where avoidable.
- **Email delivery** — transactional email (order receipts, delivery links, payout/refund notices, moderation actions) for CAP-13, plus scheduled seller reports (CAP-15). A provider like SES/SendGrid/Postmark.
- **Object storage / CDN** — sold assets + media (CAP-02/03/07/14).
- **Push notifications** — web push (Push API) now; FCM/APNs when native apps arrive — CAP-13 push channel.
- **Malware/AV scanning of uploaded assets** — sold assets are executable/openable files distributed to many buyers; **scan on upload before an asset is deliverable** (CAP-03→CAP-07). A scanning engine (ClamAV self-hosted, or a managed scanning API) as an async consumer of the upload event.
- **Content moderation** — CAP-12 (prohibited/IP-infringing listings/assets, abusive reviews). Start with rules/heuristics + admin queue; a managed moderation/classification API is the scale path — research flag.

### Security
- **Secrets management**: a dedicated secrets store (**HashiCorp Vault** for portability, or the chosen cloud's secrets manager) — gateway API keys, DB credentials, asset-signing keys, IdP secrets. No secrets in code or images.
- **PCI scope minimization**: card data never touches the platform — use the gateway's hosted fields/tokenization to stay at the lightest PCI posture (SAQ A). Store only tokens/references.
- **Digital-asset protection (the differentiating control)**: sold assets live in **private object storage**, never publicly addressable; downloads are authorized per-entitlement and served via **short-lived signed URLs** (and/or issued license keys) through the CDN; optionally watermark/stamp downloads with the buyer's order ID for leak tracing; rate-limit and log every download. **Malware-scan assets on upload**; an asset is not deliverable until it passes.
- **Encryption**: TLS everywhere in transit; encryption at rest on Postgres, Redis, object storage, and backups (managed defaults + enforced policy). Field-level encryption for the most sensitive PII (seller payout banking details, KYC references) above gateway tokenization.
- **GDPR controls**: data-subject export and erasure (profile, reviews, purchase history, messaging — subject to legal/financial retention exceptions for ledger/tax); regional residency achievable via per-region Postgres/storage if required.
- **Application security**: input validation at the API boundary, output encoding, Redis-backed rate limiting on auth/search/checkout/download endpoints; **idempotency keys on all money-moving and entitlement-granting operations** (payment, refund, payout, grant) so retries are safe; **signed gateway webhooks with replay protection** (the trigger for entitlement grant on `OrderPaid` and reversal on `ChargebackReceived`).
- **Authorization enforcement**: the role/relationship/entitlement policy layer applied uniformly; moderator/admin actions (CAP-12) audit-logged.

## Capability → Tech Mapping

| Capability | Implemented by | Notes |
|-----------|----------------|-------|
| CAP-01 Seller onboarding & KYC | NestJS onboarding module + Postgres (seller accounts/status) + gateway connected-account + KYC/tax provider; emits `SellerActivated` | Verification delegated to gateway/KYC provider; platform stores status + references, not raw docs; seller can't be paid out until verified. |
| CAP-02 Listing management | NestJS listing module + Postgres (listing records, draft/publish state) + S3 pre-signed media upload + CDN; emits `ListingPublished` | Publish event drives async search indexing — no synchronous coupling to search; media in public-CDN path, distinct from sold assets. |
| CAP-03 Asset & inventory/license management | NestJS assets module + Postgres (asset metadata, license/seat inventory, versions) + **private S3** + pre-signed PUT upload + AV-scan consumer | License/seat counts decremented transactionally at entitlement grant; asset deliverable only after malware scan passes; versioning supports re-download of purchased version. |
| CAP-04 Search & discovery | OpenSearch cluster fed from listing events; Redis-cached popular results | Separate engine so discovery never hits the transactional DB; fuzzy matching = OpenSearch typo tolerance; facets on category/price/rating/format. |
| CAP-05 Checkout | NestJS checkout module + Postgres (cart, orders, ACID) + Redis (idempotency keys) + tax service | Idempotent order placement; price/tax computed at order creation; order is the unit the ledger and entitlement hang off. |
| CAP-06 Payment | NestJS payments module + payment gateway (charge/capture) + Postgres (payment refs) + signed gateway webhooks; emits `OrderPaid` | No raw card data (SAQ A); `OrderPaid` webhook (idempotent) is the trigger for entitlement + ledger + notification. |
| CAP-07 Digital delivery & entitlements | NestJS entitlements/delivery module + Postgres (entitlements) + private S3 + short-lived signed URLs / license-key issuance via CDN; consumes `OrderPaid`, emits `EntitlementGranted` | Entitlement is the authorization for every download/re-download; signed URL minted per-request after entitlement check; "paid but no entitlement" is a monitored invariant. |
| CAP-08 Refunds & chargebacks | NestJS refunds module + payment gateway (refund/dispute webhooks) + Postgres (entitlement revocation) + double-entry ledger reversal; consumes `ChargebackReceived`, emits `RefundProcessed` | Refund/chargeback revokes entitlement and posts reversing ledger entries; idempotent; chargeback path is gateway-driven webhook. |
| CAP-09 Seller ledger | NestJS ledger module + Postgres append-only double-entry ledger; consumes `OrderPaid`/`RefundProcessed`/`ChargebackReceived`/`PayoutSent` | System of record for seller balance, platform fees, reversals, adjustments; reconciliation job vs. gateway; balance derivable, not stored mutable. |
| CAP-10 Payouts | NestJS payouts module + Postgres ledger + gateway transfers + Kafka consumer (batching) + scheduled jobs; emits `PayoutSent` | Respects schedule/threshold + KYC-verified gate; batches transfers to cut fees; idempotent transfers; failed-payout retries + seller notification. |
| CAP-11 Reviews & ratings | NestJS reviews module + Postgres (reviews, rating aggregates) + entitlement check + moderation hold; emits `ReviewPublished` | Only entitlement holders can review (anti-fake-review); rating recalculation in transaction; abusive content flagged to moderation. |
| CAP-12 Moderation | NestJS moderation module + Postgres (queue, actions, audit log) + moderation/classification API + admin console | Listings/assets/reviews scanned (rules + managed API); takedown suspends listing and can revoke deliverability; all actions audit-logged. |
| CAP-13 Notifications | NestJS notifications module as Kafka consumer (fan-in) + Postgres (in-app inbox) + email provider + web push | Subscribes to all domain events; per-event preference lookup; critical notices (payment/refund/payout/moderation) bypass opt-out; dedup/digest batching. |
| CAP-14 Buyer storefront & purchase library | Next.js (SSR/ISR storefront) + NestJS read APIs + Postgres read replicas + Redis cache + entitlements (library); delivery via CAP-07 | SEO-sensitive storefront server-rendered; "my purchases" library lists entitlements with re-download via signed URLs; cached popular pages. |
| CAP-15 Seller dashboard & analytics | Next.js dashboard + NestJS read APIs + Postgres read replicas + event-driven rollup tables + CSV/PDF export jobs + scheduled email reports | Replicas + rollups at launch; ClickHouse warehouse is the documented scale path; exports/reports run as background jobs. |

## Key Architecture Decisions

### AD-01: Modular monolith with pre-carved seams, not microservices (yet)
- **Decision**: Build a single deployable modular monolith (NestJS modules) with strict internal boundaries and an event backbone, designed so search, payments/ledger, asset-delivery, moderation, and notifications can be extracted into services later.
- **Context**: Designing for millions of users but launching at low volume with a small competent team; the domain has clear fault lines.
- **Rationale**: Microservices now impose distributed-systems tax (network failures, distributed transactions across money/entitlement flows, deployment complexity) the launch volume can't justify and that would slow the team. A modular monolith keeps money + entitlement flows in-process and transactional while event boundaries pre-pay the cost of later extraction. Lowest-regret given the scale ramp.
- **Tradeoffs**: Requires discipline to keep boundaries honest (no reaching across modules' tables); a sloppy team turns this into a big ball of mud. Mitigated by enforced module structure, schema-per-module, events as the cross-module contract, and CI boundary-linting.

### AD-02: Postgres as system of record with a double-entry ledger for money
- **Decision**: All transactional state in PostgreSQL; model platform fees, earnings, refunds, chargebacks, and payouts as an append-only double-entry ledger.
- **Context**: CAP-08/09/10 demand auditability, reconciliation, and correctness across earnings, reversals, and payouts; chargebacks arrive asynchronously from the gateway and must reverse cleanly.
- **Rationale**: ACID transactions and relational integrity suit money state machines. A double-entry ledger makes every seller balance derivable and reconcilable against the gateway, and turns "charged but not recorded" / "chargeback not reversed" into detectable, repairable invariants rather than silent loss.
- **Tradeoffs**: Single-primary write ceiling exists far out; deferred to distributed SQL only when proven. Ledger discipline adds modeling effort up front, repaid in audit/dispute/payout confidence.

### AD-03: Entitlement-gated, signed-URL delivery from private object storage
- **Decision**: Sold assets live in private S3-compatible storage; delivery (CAP-07) is authorized per-entitlement and served only via short-lived signed URLs (or issued license keys) through a CDN; assets are malware-scanned on upload before becoming deliverable.
- **Context**: The product *is* the digital file; the platform must prevent piracy/leakage and must not ship malware to buyers, while serving large downloads to millions globally.
- **Rationale**: Entitlement is the single authorization point for every download and re-download, which makes anti-piracy and review-integrity (CAP-11) enforceable in one place; private buckets + expiring signed URLs prevent URL sharing; CDN offloads origin and accelerates global delivery; scan-on-upload prevents distributing malicious assets.
- **Tradeoffs**: Signed-URL minting and entitlement checks add per-download work (mitigated by short-lived caching of the authorization, not the asset); determined sharing of an in-flight signed URL is still possible (mitigated by short TTLs and optional per-buyer watermarking). License-key goods need a separate inventory/seat model.

### AD-04: Dedicated search engine (OpenSearch) fed asynchronously from events
- **Decision**: Run search in a separate engine, kept eventually consistent via `ListingPublished`/update events, rather than querying Postgres for discovery.
- **Context**: CAP-04 needs relevance ranking, fuzzy matching, and faceted filters under read-heavy storefront traffic.
- **Rationale**: Postgres full-text can't meet relevance/facet needs at scale, and discovery traffic would contend with transactional writes. A separate engine isolates that load and can be reshaped/rebuilt independently (replay from the event log).
- **Tradeoffs**: Eventual consistency — a just-published or just-taken-down listing may lag seconds in search; acceptable for discovery, and a moderation takedown additionally blocks delivery at the entitlement layer regardless of index state. Adds a stateful system to operate (use managed).

### AD-05: Event backbone (Kafka-class) as the async + future-extraction spine
- **Decision**: A durable, replayable event log carries domain events to async consumers (notifications, indexing, analytics, payout batching, ledger postings).
- **Context**: CAP-13 fans in from most capabilities; money/delivery/notification flows must not block user-facing requests; search and analytics must be (re)buildable.
- **Rationale**: Log-based eventing gives per-key ordering (per order / per seller ledger), replay (rebuild index/rollups), and clean multi-consumer fan-out, and is the mechanism that makes later service extraction non-breaking. Right-sizing note: a simpler managed queue is an acceptable MVP substitute if replay isn't yet needed (research flag).
- **Tradeoffs**: Operational weight and a learning curve; eventual-consistency reasoning required in consumers. Mitigated by managed Kafka and idempotent, replay-safe consumers.

### AD-06: Select a portable OIDC identity provider; own entitlement/role/relationship authz
- **Decision**: Authenticate via a portable OIDC IdP (Keycloak default, managed acceptable); implement marketplace-specific authorization (roles + ownership + entitlement checks) in the app tier.
- **Context**: No identity system is stated, so one must be chosen; download/re-download and review rights are entitlement/ownership-specific and not provided externally.
- **Rationale**: OIDC keeps identity portable and shared across storefront/dashboard/console; the high-value authz (entitlement-gated delivery, owner-only listing edits, purchaser-only reviews) must be owned in-app and enforced uniformly via a policy/guard layer.
- **Tradeoffs**: Operating an IdP (if self-hosted) is work; a managed IdP trades portability for speed. Fine-grained relationship authz may later warrant a policy engine (OpenFGA/OPA).

### AD-07: PCI/KYC scope delegated to a marketplace-capable gateway
- **Decision**: Delegate card capture, payouts, connected accounts, KYC/AML, and chargeback handling to a Stripe-Connect-class gateway; the platform holds only the ledger and references.
- **Context**: Payments, refunds, chargebacks, and payouts (CAP-06/08/10) plus seller KYC (CAP-01) are heavily regulated; building them in-house is high-risk and slow.
- **Rationale**: Keeps the platform at SAQ A, offloads KYC/AML and tax-form burden, and provides payout rails and chargeback webhooks — letting the team focus on the ledger and entitlement logic that are genuinely the platform's own.
- **Tradeoffs**: Gateway lock-in and fee economics; abstract the gateway behind an internal port so a second provider (Adyen/Braintree) can be added if needed.

## Risks & Tradeoffs

- **Financial correctness under concurrency and failure.** Payments, refunds, asynchronous chargebacks, and batched payouts crossing the platform ledger and an external gateway are the highest-stakes paths. *Mitigation*: double-entry ledger as source of truth, idempotency keys on all money operations and entitlement grants, a reconciliation job against the gateway, and alerting on ledger-vs-gateway and paid-but-no-entitlement invariants.
- **Digital-asset leakage / piracy.** Once a buyer downloads, the file can be redistributed — the architecture limits *acquisition* (entitlement-gated, expiring signed URLs, scan-on-upload) but cannot prevent post-download sharing. *Mitigation*: short-lived signed URLs, per-buyer watermarking/stamping for leak tracing, download rate-limiting and logging; accept that DRM-grade protection is out of scope unless explicitly required (would be a new capability — flag to solution-architect).
- **Malware distribution.** Sellers upload files delivered to many buyers; a malicious asset is a platform-level incident. *Mitigation*: mandatory async malware scan before an asset is deliverable; quarantine on failure; re-scan on signature updates.
- **Chargeback abuse & fraud.** Digital goods are high-chargeback-risk (instant delivery, no physical return). *Mitigation*: gateway fraud tooling, entitlement revocation on chargeback, velocity/anomaly checks at checkout, seller-balance holds for disputed amounts — detection sophistication is a known gap (research flag).
- **Search/index consistency lag.** Async indexing means brief windows where a published listing isn't searchable or a taken-down one still appears. *Mitigation*: low-latency event pipeline, index-lag monitoring, and entitlement-layer enforcement so a takedown blocks delivery regardless of index state.
- **Modular-monolith boundary erosion.** The later-extraction story collapses if modules share tables or call internals. *Mitigation*: schema-per-module, events as the only cross-module write contract, dependency-linting in CI.
- **Premature distribution / over-engineering.** Standing up Kafka + Kubernetes + a warehouse on day one for low volume burns runway. *Mitigation*: explicit MVP-vs-scale split — PaaS + managed queue + replica-based analytics at launch, with seams designed so each upgrade is additive.
- **Tax & multi-currency.** Marketplace payouts and global sales bring tax calculation/reporting and FX. *Mitigation*: delegate tax to the gateway/tax service; record FX rate + timestamp on each ledger entry; resolve fee-attribution policy (open question) before build.

## Research Suggestions

High-stakes or uncertain choices to validate with the researcher skill before committing:

- **Async backbone: Kafka-class event log vs. managed queue at this scale ramp.** A consequential, hard-to-reverse infrastructure choice that shapes consumers, ordering, and the extraction story; the right answer depends on real replay/fan-out needs vs. operational budget. Suggested researcher query: *"Event streaming backbone selection for a transactional digital-goods marketplace scaling from thousands to millions of orders: Apache Kafka vs. managed cloud queues (SQS/SNS, Pub/Sub) vs. NATS JetStream — tradeoffs in ordering, replay, exactly-once/idempotency, operational cost, and migration path."*
- **Digital-goods delivery & anti-piracy approach.** Delivery is the product and the highest-stakes platform-specific control; signed-URL gating, watermarking, license-key issuance, and optional DRM differ sharply in protection, cost, and buyer friction. Suggested researcher query: *"Secure digital-goods delivery and anti-piracy for a marketplace at scale: short-lived signed URLs from private object storage vs. license-key issuance vs. watermarking/forensic stamping vs. DRM — protection strength, buyer friction, CDN/cost implications, and leak-tracing effectiveness."*
- **(Secondary) Marketplace trust & safety: moderation, chargeback/fraud, and fake-review detection — build vs. buy.** Digital-goods marketplaces face IP-infringement, malware, high chargeback rates, and fake reviews. Suggested researcher query: *"Build-vs-buy content moderation, fraud/chargeback detection, and fake-review prevention for a digital-goods marketplace — managed APIs vs. in-house heuristics, accuracy, latency, and cost."*

## Open Questions

- **Entitlement & license model** — Are goods single-purchase perpetual downloads, license-key/seat-limited, subscription, or a mix? This shapes the CAP-03/CAP-07 inventory and entitlement schema. (Functional — confirm in solution-architect.)
- **Refund/chargeback policy** — Refund window, partial refunds, and whether entitlement is revoked on refund vs. retained; chargeback liability split between platform and seller (affects ledger holds). (Functional — solution-architect.)
- **Payment gateway feature set** — Does the chosen gateway support marketplace split payments, connected-account payouts, KYC/AML, tax, and chargeback webhooks (Stripe-Connect-class)? The payout/ledger design depends on it; if not, more treasury/KYC logic moves in-house.
- **Anti-piracy strength required** — Are signed-URL gating + watermarking sufficient, or is true DRM a requirement? DRM would be a significant new capability and cost. (Flag to solution-architect, don't assume.)
- **Data residency** — Any regional residency requirements (GDPR/locale) forcing per-region Postgres/storage from the start, or is a single region acceptable at launch?
- **Identity** — Confirm the IdP choice (self-hosted Keycloak vs. managed) and whether social login / SSO for sellers is required.

## Next Steps

1. Stand up the modular-monolith skeleton (NestJS modules + Postgres + Terraform) on a PaaS target, with CI running typecheck/test/migrate and module-boundary linting from day one.
2. Spike the money + entitlement core: order → payment-gateway charge → `OrderPaid` webhook → entitlement grant → double-entry ledger posting, with idempotency keys and a reconciliation job; validate against the gateway sandbox, including the refund and chargeback-reversal paths.
3. Spike secure delivery: private S3 + entitlement-checked short-lived signed URLs via CDN, plus async malware scan-on-upload gating deliverability; measure authorized large-download performance and verify URL sharing is bounded by TTL.
4. Spike search: index listings from `ListingPublished` events into OpenSearch (or Typesense for the MVP comparison) and validate relevance, fuzzy matching, and facets against realistic listing data.
5. Resolve the AD-05 async-backbone research flag, then implement the notification fan-in (CAP-13) as the first end-to-end event consumer.
6. Confirm the key integration assumptions with stakeholders — gateway (split payments / connected payouts / KYC / chargeback webhooks) and the entitlement/license + refund policy — and revise the architecture if gaps exist.
7. Hand this document to the librarian skill to persist as a spec artifact.

---
*Technical architecture produced by technical-architect skill. Use the librarian skill to persist this artifact.*
