# Digital-Goods Marketplace — Technical Architecture

> Technical Architect | Depth: deep | Generated: 2026-06-10

## Source Breakdown

This architecture builds on a solution-architect-style capability breakdown for a two-sided **digital-goods** marketplace (buyers browse and purchase digital goods; sellers list items, manage inventory/licenses, and receive payouts). The breakdown was provided inline in the task prompt — the librarian skill was **not available** to retrieve or persist it. Every technical choice below is anchored to a capability from that breakdown; no new functional capabilities are introduced. Where a functional gap surfaces, it is flagged back to solution-architect rather than invented.

The breakdown names ~15 capabilities across these areas, which I have enumerated as CAP-01..CAP-15 for traceability (IDs assigned here for the mapping; confirm against the canonical breakdown if it carries its own numbering):

- **CAP-01** Seller onboarding (registration, KYC/identity, tax/payout setup, store creation)
- **CAP-02** Listing & asset management (create/edit listings, upload digital assets, metadata, versioning)
- **CAP-03** Inventory & license management (license keys/seats/quotas, stock for finite goods)
- **CAP-04** Search & discovery (full-text, facets, ranking, recommendations entry points)
- **CAP-05** Catalog browse & product detail (categories, listing pages, media)
- **CAP-06** Checkout & cart (cart, tax/VAT calculation, order creation)
- **CAP-07** Payment processing (charge, idempotency, fraud signals)
- **CAP-08** Digital delivery & entitlements (grant access, secure download/stream, license issuance)
- **CAP-09** Refunds & chargebacks (refund flow, dispute/chargeback handling, entitlement revocation)
- **CAP-10** Seller ledger (double-entry accounting, fees, balances, reconciliation)
- **CAP-11** Payouts (scheduled/threshold payouts to sellers, transfers, reporting)
- **CAP-12** Reviews & ratings (buyer reviews, aggregates, verified-purchase gating)
- **CAP-13** Moderation & trust/safety (listing/asset/review moderation, fraud, takedowns)
- **CAP-14** Notifications (transactional + marketing across email/push/in-app)
- **CAP-15** Buyer & seller dashboards / analytics (orders, earnings, downloads, payout history)

> Note: "Catalog browse" (CAP-05) and "search" (CAP-04) are split for clarity; if the breakdown treats them as one capability, merge them — the tech mapping is unaffected.

## Constraints & Assumptions

- **Scale & load**: Design for growth to **millions of users** **[stated]**. This is a read-heavy discovery workload (browse/search) with a transactional money core (checkout, payment, ledger, payouts) and a delivery tier that must serve potentially large binary assets globally and cheaply. Implies: horizontal scale on stateless tiers, a dedicated search engine, a CDN-fronted delivery path that keeps large files off the app tier, and strong consistency on money/entitlement state. **[assumed]** cheap-at-launch-but-no-rewrite-to-millions: the design must run lean early and scale by adding capacity/extracting services, not by re-architecting.
- **Team**: Competent, cloud-agnostic engineering team with no stated language/framework lock-in **[stated]**. **[assumed]** small-to-mid team at launch that values a mainstream, well-staffed ecosystem and developer productivity over exotic technology.
- **Hosting**: **Cloud-agnostic**, no must-use cloud **[stated]**. Bias toward portable, open technologies (containers, open-source data stores, S3-compatible storage, managed-anywhere services) over proprietary lock-in, while allowing a single managed cloud at launch for speed **[assumed]**.
- **Hard constraints**:
  - **PCI DSS** applies to CAP-07 (payment) and CAP-11 (payouts). Assume **SAQ A** posture — the platform never touches raw card data; card capture/storage is delegated to a PCI-compliant gateway **[assumed]**.
  - **GDPR / data-protection**: PII for buyers and sellers, plus seller KYC and bank/tax data (CAP-01, CAP-11). Need data-subject export/erasure and regional-residency optionality **[assumed]**.
  - **Tax compliance**: digital goods trigger destination-based VAT/GST and US sales-tax-on-digital rules (CAP-06). Assume a tax-calculation provider rather than building tax tables in-house **[assumed]**.
  - **Financial correctness** is a hard constraint: fee math, seller balances, refunds, chargebacks, and payouts must be auditable and reconcilable **[stated, inferred from "seller ledger" being a named capability]**.
  - **Anti-piracy / content protection**: digital assets must be delivered without leaking a permanent public URL, and entitlements must be revocable on refund/chargeback (CAP-08, CAP-09) **[assumed]**.
- **Existing systems**: None stated as pre-existing. Treated as build-or-integrate decisions below: identity/auth, payment gateway, email/push providers, object storage, tax provider, KYC provider are all integrations the platform stands up (not legacy systems to preserve).

## Architecture Overview

- **Style**: **Modular monolith at launch with pre-carved seams for later service extraction** — a deliberate hybrid. Rationale: launch volume and a small team don't justify the operational tax of full microservices, but this domain has clear, high-pressure fault lines — **search/discovery**, the **money core** (payment + ledger + payouts + refunds), **digital delivery/entitlements**, **moderation**, and **notifications** — that will need independent scaling and failure isolation at millions of users. Build one (or few) deployable application(s) organized into strict modules, with an event backbone and clean async boundaries so the highest-pressure modules can be extracted into services later without rewriting their callers. Lowest-regret given the scale ramp.
- **Shape**: A stateless API/application tier serves web clients and houses the domain modules (onboarding, listings, inventory/licenses, search-facade, catalog, cart/checkout, payments, delivery/entitlements, refunds, ledger, payouts, reviews, moderation, notifications, dashboards). A **relational database** is the system of record for transactional state — orders, entitlements, the **double-entry seller ledger**, payouts, licenses — fronted by **Redis** for hot reads, cart state, and rate limiting. A dedicated **search engine** (kept in sync from listing/inventory events) powers CAP-04 so discovery never contends with the transactional database. An **event backbone** (Kafka-class) carries domain events — `OrderPaid`, `EntitlementGranted`, `RefundIssued`, `ChargebackReceived`, `PayoutSettled`, `ListingPublished`, `ReviewPublished` — to async consumers: notifications, search indexing, ledger postings, analytics rollups, payout batching, and entitlement revocation. **Object storage + CDN** hold and deliver digital assets, with downloads authorized via **short-lived signed URLs** so the app tier and the assets never sit in the bytes path. The money flows are implemented as an append-only **double-entry ledger** (the platform's source of truth), with an external **payment gateway** as the rail for charges, refunds, and seller payouts.

## Tech Stack

### Frontend
- **Recommendation**: **TypeScript + React, server-rendered via Next.js (App Router)**, as a single web app with role-aware surfaces (buyer storefront, seller studio, admin/moderation console). Headless component system (Radix/shadcn-style) for control over the marketplace UI.
- **Why**: The storefront, catalog (CAP-05), and search results (CAP-04) are SEO- and first-paint-sensitive — server rendering improves crawlability and conversion. Seller listing/asset management (CAP-02), dashboards (CAP-15), and checkout (CAP-06) are interactive and benefit from React's ecosystem. Web-only is sufficient for MVP; React Native is a low-friction future path since the skill set carries over.
- **Alternatives**: **Remix** — prefer for a more web-standards-centric data/forms model and simpler caching mentality. **SvelteKit** — leaner runtime/bundle if the team has Svelte depth, at the cost of a smaller hiring pool. Keep the **admin/moderation console** as a route within the same app early; split it into its own app only when access-control isolation or release cadence demands it.

### Backend / API
- **Recommendation**: **TypeScript on Node.js (NestJS)** for the application tier, exposing a **REST/JSON API** (OpenAPI-documented) with a thin BFF for the Next.js frontend. One language across front and back reduces context-switching for a small team; NestJS modules map cleanly onto the modular-monolith seams.
- **Why**: The workload is I/O-bound orchestration (gateway, search, DB, queue, object storage) rather than CPU-bound — Node's sweet spot. NestJS's module/provider structure enforces the internal boundaries this architecture depends on (no cross-module table access). REST keeps the public surface simple and cacheable; GraphQL's client-shaped-query win is real for the dashboards but not worth the platform-wide complexity tax at this stage.
- **Alternatives**: **Go (Echo/Fiber)** — prefer if the team is Go-native, or specifically for the **delivery/entitlement** and **payment/ledger** services later where throughput, latency, and footprint matter most; costs the shared-language productivity. **Java/Kotlin + Spring Boot** — prefer if the team's center of gravity is JVM and the financial domain wants its mature transactional ecosystem. **GraphQL (Apollo)** for dashboard read paths specifically — a targeted later optimization, not a foundation.

### Data storage

**Primary database (system of record)**
- **Recommendation**: **PostgreSQL** (managed), one logical database with **schema-per-module** discipline, on a primary + read-replica topology.
- **Why**: The core — orders, entitlements/licenses, the double-entry seller ledger, refunds, payouts (CAP-03, CAP-06..CAP-11) — demands ACID transactions, strong consistency, and correctness. Entitlement grants and ledger postings are exactly what relational + transactions are built for. Postgres scales vertically a long way and horizontally via read replicas for read-heavy catalog/dashboard reads; it's open-source and managed on every cloud (supports cloud-agnostic).
- **Alternatives**: **MySQL/MariaDB** — equivalent fit; prefer only with deeper MySQL ops muscle. **CockroachDB / Spanner-class distributed SQL** — prefer only when single-primary write throughput becomes the proven ceiling; defer, as it adds cost/complexity now. Do **not** put the ledger or entitlements in a document store — the consistency guarantees are the whole point.

**Cache**
- **Recommendation**: **Redis** (managed) for hot catalog/listing reads, cart state (CAP-06), session/rate-limit counters, search-result caching of popular queries, signed-URL/download-token short-TTL state, and license-key reservation locks for finite inventory (CAP-03).
- **Why**: Cart is naturally session-scoped, ephemeral, and high-churn — a poor fit for the transactional DB until checkout. Finite-inventory license issuance (e.g., limited seats/keys) needs an atomic reservation primitive (`SET NX` + TTL) to prevent over-issuance under contention. Redis also absorbs the cached-popular-results path for CAP-04.
- **Alternatives**: **Valkey** — drop-in open-source fork; prefer if licensing portability is a concern. **Memcached** — only for pure key/value caching; you lose the atomic/expiry primitives the inventory lock relies on.

**Search engine**
- **Recommendation**: **OpenSearch** (or Elasticsearch) as a dedicated cluster powering CAP-04, fed asynchronously from listing/inventory-change events.
- **Why**: CAP-04 needs full-text relevance ranking, fuzzy/typo tolerance, faceted filters (category, price, rating, format/license type, tags), and synonym handling — none of which Postgres does well at marketplace scale. A separate engine means discovery load never contends with transactional writes, and the index can be rebuilt/reshaped independently (replay from the event log). OpenSearch is Apache-2.0 and managed on every major cloud (cloud-agnostic).
- **Alternatives**: **Typesense / Meilisearch** — prefer at MVP for far simpler operations and excellent typo-tolerance out of the box; revisit if relevance tuning and aggregation needs outgrow them. **Algolia** — prefer if you want fully managed, best-in-class relevance and instant-search UX without running a cluster, at higher cost and vendor lock-in. **Postgres FTS + `pg_trgm`** — a launch-only bridge to defer running a cluster, explicitly not the millions-of-users answer. This is a research flag (below).

**Object / blob storage (digital assets)**
- **Recommendation**: **S3-compatible object storage** with a **private bucket** model. Sellers upload assets via **pre-signed PUT URLs** (bytes never transit the app tier). Buyers download via **short-lived signed GET URLs** issued only after an entitlement check, served through a **CDN** with signed-URL/signed-cookie support. Large or streamable goods (video/audio) use CDN range requests; very large files use multipart upload.
- **Why**: Digital goods are the product — they must be stored durably and delivered globally, cheaply, and **without a permanent public URL** (anti-piracy). Entitlement-gated signed URLs (CAP-08) ensure only paying buyers with a valid, non-revoked entitlement get bytes, and short TTLs limit link sharing. Keeping the app tier out of the bytes path is essential to scale delivery to millions without scaling compute. S3-compatible APIs keep this portable (incl. MinIO on-prem).
- **Alternatives**: Cloud-native equivalents (GCS / Azure Blob) — fine, but standardize on the S3 API for portability. For very-high-volume video, a **managed media/streaming service** (signed HLS/DASH) is the scale path; flagged where relevant.

**Analytics store**
- **Recommendation**: **Defer a dedicated warehouse at launch**; serve CAP-15 dashboards from Postgres read replicas with **pre-aggregated rollup tables / materialized views** updated from events (sales, downloads, earnings, payout history). Introduce a **columnar warehouse (ClickHouse, or BigQuery/Snowflake-class)** when analytical query volume or history depth strains the replicas.
- **Why**: CAP-15 dashboards are bounded, per-user aggregations (earnings, orders, downloads over time windows) that replicas + rollups handle well early. Standing up a warehouse before there's data to justify it is over-engineering; the seam (events already on the backbone) makes adding one later additive, not a rewrite. **ClickHouse** is the opinionated pick when the time comes — strong cost/performance on append-heavy event data, open-source/portable.

### Async / messaging

**Needed** — not optional. Notifications (CAP-14) fan in from most capabilities; payment → entitlement → ledger → payout is a chain of asynchronous, ordered, replayable events; search indexing and analytics are event-fed; refunds/chargebacks must trigger entitlement revocation and ledger reversals asynchronously.

- **Recommendation**: **A durable event log — Apache Kafka (or a Kafka-compatible managed service)** for domain events, plus a lightweight in-process **job runner (BullMQ on Redis)** for background jobs (email rendering, signed-URL housekeeping, report generation, retries) at launch.
- **Why**: Domain events — `OrderPaid`, `EntitlementGranted`, `RefundIssued`, `ChargebackReceived`, `PayoutInitiated`/`PayoutSettled`, `ListingPublished`, `InventoryChanged`, `ReviewPublished` — need durable, replayable, **ordered** delivery (e.g., per-seller ledger ordering, per-order entitlement ordering) to multiple independent consumers: notifications (CAP-14), search indexing (CAP-04), ledger posting (CAP-10), payout batching (CAP-11), entitlement revocation (CAP-09), analytics rollups (CAP-15), and moderation/fraud scoring (CAP-13). A log-based backbone gives per-key ordering, replay (rebuild the index, recompute rollups, re-derive ledger views), and clean fan-out — and is the mechanism that lets modules be extracted into services later without changing producers. The Redis-backed job runner covers simple off-request-path work cheaply.
- **Alternatives**: **RabbitMQ / cloud queues (SQS+SNS, Pub/Sub)** — prefer at MVP if you don't yet need replay/ordering and want lower ops overhead; you give up the replay that makes index/ledger/analytics rebuilds easy. **NATS JetStream** — a lighter-weight log with good ordering if Kafka's footprint is unwelcome. Right-size honestly: launching on a managed queue and adopting Kafka when replay/fan-out volume demands it is defensible — flagged for research below.

### Authentication & authorization
- **Recommendation**: **A managed/self-hostable IdP speaking OIDC/OAuth2** — **Keycloak** (self-hosted, portable) or a managed equivalent (Auth0/Cognito/Clerk). The app tier consumes signed tokens (JWT access tokens; rotating refresh tokens in secure, HTTP-only cookies). **Authorization** lives in the app tier as **role- + relationship-/ownership-based access control**: roles (buyer, seller, moderator/admin) plus ownership and entitlement checks (a seller edits only their own listings; a buyer downloads only goods they hold a valid entitlement for).
- **Why**: No existing identity system is stated, so this is a build/integrate decision — OIDC keeps it standard and swappable. Authorization is domain-specific and must be owned: **entitlement checks gate digital delivery** (CAP-08) and are the anti-piracy frontline; **verified-purchase gating** for reviews (CAP-12), **seller ownership** of listings/assets/inventory (CAP-02/03), and **moderator elevation** (CAP-13) are all relationship checks. Centralize them in a NestJS policy/guard layer so every module enforces consistently. **Seller KYC/identity verification** (CAP-01) is a distinct compliance step layered on top of basic auth, delegated to a KYC provider (below).
- **Alternatives**: Fully-managed IdP (Auth0/Clerk) — prefer for speed at MVP and to offload MFA/social login; revisit cost and lock-in at scale. Keycloak — prefer for portability and no per-MAU pricing, at the cost of operating it.

### Infrastructure & hosting
- **Recommendation**: **Containers (Docker) on Kubernetes** (managed: EKS/GKE/AKS — pick one cloud at launch, stay portable), stateless app tier behind a load balancer and autoscaled horizontally; managed services for Postgres, Redis, OpenSearch, and the event backbone; **CDN** for asset delivery and static assets; object storage for assets.
- **Why**: Cloud-agnostic + growth to millions points to containers on Kubernetes as the portable, horizontally-scalable substrate — the same artifacts run on any cloud or on-prem. Managed data services avoid operating stateful systems yourself while staying on open engines. The stateless app tier scales out trivially; search, cache, delivery, and the event backbone scale independently — the point of the seams. The CDN is load-bearing here: it is the delivery tier for digital goods, not just a static-asset optimization.
- **Alternatives**: **PaaS (Fly.io / Render / cloud App Platform)** — strongly prefer **at MVP** to avoid Kubernetes overhead; the container-first design makes the eventual K8s migration mostly packaging, not rewriting. **Serverless functions** — good for spiky stateless edges (asset post-processing/transcoding on upload, signed-URL minting, scheduled payout/report jobs), but a poor fit for the always-warm transactional core; use selectively, not as the foundation.

### CI/CD & developer tooling
- **Recommendation**: **Trunk-based development with GitHub Actions (or GitLab CI)**; pipeline runs lint → typecheck → unit/integration tests → build container → deploy to staging → promote to prod. **Infrastructure as Code via Terraform** (cloud-agnostic). Database migrations versioned and run in-pipeline (Prisma Migrate / Flyway). Environments dev → staging → prod, with ephemeral preview environments per PR if budget allows. **Architecture fitness checks** (module-boundary / dependency linting) in CI to keep the modular-monolith seams honest.
- **Why**: A modular monolith deploys as one or few artifacts, keeping CI/CD simple — a major saving over microservices. Terraform keeps infra reproducible and not welded to one cloud. Migration discipline is non-negotiable given the financial schema (ledger, payouts, entitlements) where ad-hoc drift is dangerous.
- **Alternatives**: **Pulumi** — prefer if the team would rather express infra in TypeScript; smaller ecosystem than Terraform. **GitOps (Argo CD)** — adopt once on Kubernetes for declarative deploys.

### Observability
- **Recommendation**: **OpenTelemetry** for traces/metrics/logs (vendor-neutral, cloud-agnostic), exported to a backend you self-host or buy: **Prometheus + Grafana** (metrics/dashboards), **Loki** or an OpenSearch/ELK stack (logs), **Tempo/Jaeger** (tracing). Structured logging everywhere; correlation IDs propagated from the API through the event backbone to async consumers.
- **Why**: The hardest things to debug here are the async money/entitlement chains — a payment captured but entitlement not granted (CAP-07→08), a refund issued but entitlement not revoked or ledger not reversed (CAP-09→10), a payout that silently failed (CAP-11), a notification that never fired (CAP-14). Distributed tracing across API → event log → consumers makes these diagnosable. Add **alerting on business/financial invariants**: ledger-vs-gateway balance mismatches, entitlement-without-payment or payment-without-entitlement, dead-letter-queue depth, payout failure rate, search index lag, and download-authorization error rate.
- **Alternatives**: **Datadog / Grafana Cloud / Honeycomb** — prefer managed if the team would rather not run the stack; OTel instrumentation lets you switch backends without re-instrumenting.

### Third-party services & integrations
- **Payment gateway** (CAP-07, CAP-09, CAP-11) — a gateway with **marketplace/split-payment and connected-account payouts** (Stripe Connect-class, or Adyen/Braintree marketplace) handles card capture (keeping the platform at SAQ A), charges, refunds, **chargeback/dispute webhooks**, and seller payouts/transfers. The platform's own **double-entry ledger records the truth**; the gateway moves the money. Webhooks must be signature-verified and replay-protected.
- **Tax calculation** (CAP-06) — a provider (Stripe Tax / Avalara / TaxJar) computes destination-based VAT/GST and US digital-goods sales tax at checkout; the platform stores the computed tax and the evidence for filing.
- **KYC / identity verification** (CAP-01) — a provider (e.g., the gateway's onboarding/KYC, or Persona/Onfido) verifies seller identity and collects tax forms (W-9/W-8/local equivalents) before payouts are enabled.
- **Email & push** (CAP-14) — a transactional email provider (Postmark/SendGrid/SES) and push (web Push API now; FCM/APNs when native apps arrive). Real-time/in-app notifications via a WebSocket gateway or a managed pub/sub-to-client service.
- **Object storage + CDN** (CAP-02 uploads, CAP-08 delivery) — S3-compatible storage + a signed-URL-capable CDN (CloudFront/Fastly/Cloudflare). Optional **media transcoding** (managed transcoder) for streamable goods.
- **Content moderation / anti-malware** (CAP-13) — antivirus/malware scanning on uploaded assets (e.g., ClamAV or a managed scanner) is a hard requirement for executables/archives; text/image moderation (managed moderation API) for listings and reviews. Start with rules/heuristics in-app; managed classification is the scale path — flagged for research.

### Security
- **Secrets management**: a dedicated secrets store (**HashiCorp Vault** for portability, or the chosen cloud's secrets manager) — gateway/KYC/tax API keys, DB credentials, asset signing keys. No secrets in code or images.
- **PCI scope minimization**: card data never touches the platform — use the gateway's hosted fields/tokenization to stay at SAQ A. Store only tokens/references.
- **Content protection (anti-piracy)**: private object storage; **no permanent public asset URLs**; **short-lived signed download URLs/cookies** issued only after an entitlement check; per-download tokens and rate limiting; optional **per-buyer watermarking/stamping** of deliverables and license-key issuance for software goods (CAP-03/08). Entitlements are **revocable** (CAP-09) — a revoked entitlement immediately fails the download-authorization check.
- **Encryption**: TLS everywhere in transit; encryption at rest on Postgres, Redis, object storage, and backups (managed defaults plus enforced policy). **Field-level encryption** for the most sensitive PII — seller bank/payout details and KYC data — above gateway tokenization.
- **GDPR controls**: data-subject export and erasure (profiles, reviews, orders subject to legal/financial retention exceptions); regional residency achievable via per-region Postgres/storage if required.
- **Application security**: input validation at the API boundary; output encoding; Redis-backed rate limiting on auth, search, checkout, and download endpoints; **idempotency keys on all money-moving operations** (charge, refund, payout) and on entitlement grants to make retries safe; signed, replay-protected webhooks from the gateway, tax, and KYC providers; audit logging of moderator/admin actions (CAP-13) and payout/ledger adjustments.

## Capability → Tech Mapping

| Capability | Implemented by | Notes |
|-----------|----------------|-------|
| CAP-01 Seller onboarding | NestJS onboarding module + IdP (OIDC) + Postgres (seller/store records) + KYC provider + payment-gateway connected-account setup; emits `SellerOnboarded` | KYC + tax-form collection gate payout eligibility; connected account created on the gateway up front so CAP-11 can pay out. |
| CAP-02 Listing & asset management | NestJS listing module + Postgres (listing/version metadata) + S3 pre-signed PUT uploads + malware scan on upload + CDN; emits `ListingPublished` | Bytes go direct-to-storage; publish event drives async search indexing; asset versioning tracked in DB, scan must pass before publish. |
| CAP-03 Inventory & license management | NestJS inventory module + Postgres (license keys/seats/quotas, ACID) + Redis (atomic reservation locks for finite stock) | License issuance is transactional; `SET NX`+TTL prevents over-issuance of finite keys/seats under contention; emits `InventoryChanged`. |
| CAP-04 Search & discovery | OpenSearch cluster fed from listing/inventory events + Redis-cached popular queries | Separate engine so discovery never hits the transactional DB; fuzzy/typo tolerance, facets, synonyms; eventual consistency on index. |
| CAP-05 Catalog browse & product detail | Next.js SSR pages + Postgres read replicas + Redis cache + CDN for media | SEO/first-paint via SSR; replica + cache absorb read-heavy browse; media served from CDN. |
| CAP-06 Checkout & cart | NestJS cart/checkout module + Redis (cart state) + Postgres (order creation, ACID) + tax provider | Cart in Redis until checkout; order persisted transactionally; tax computed and stored per line; idempotency key on order submission. |
| CAP-07 Payment processing | NestJS payments module + payment gateway (charge) + Postgres (order/payment state) + idempotency keys; emits `OrderPaid` | Gateway keeps platform at SAQ A; idempotency makes retries safe; `OrderPaid` triggers entitlement + ledger consumers. |
| CAP-08 Digital delivery & entitlements | NestJS delivery module + Postgres (entitlements/licenses) + S3 + signed-URL/CDN + entitlement check in policy layer; consumes `OrderPaid`, emits `EntitlementGranted` | Download authorized only on valid, non-revoked entitlement; short-lived signed URLs; per-download tokens + rate limit; license keys issued from CAP-03. |
| CAP-09 Refunds & chargebacks | NestJS refunds module + payment gateway (refund + chargeback webhooks) + Postgres + Kafka (`RefundIssued`, `ChargebackReceived`) → entitlement revocation + ledger reversal | Signed, replay-protected webhooks; refund/chargeback revokes the entitlement and posts reversing ledger entries; idempotent handling. |
| CAP-10 Seller ledger | NestJS ledger module + Postgres double-entry append-only ledger; consumes `OrderPaid`/`RefundIssued`/`ChargebackReceived`/`PayoutSettled` | Source of truth for fees, balances, reconciliation against the gateway; every balance derivable; reconciliation job + invariant alerts. |
| CAP-11 Payouts | NestJS payouts module + Postgres ledger + gateway transfers/payouts + Kafka consumer (batching) + scheduled jobs; emits `PayoutInitiated`/`PayoutSettled` | Respects schedule/threshold; batches transfers to cut fees; gated on KYC/tax completion; idempotent transfers; failed-payout retries + notifications. |
| CAP-12 Reviews & ratings | NestJS reviews module + Postgres (reviews, rating aggregates) + verified-purchase check (entitlement/order) + moderation hold; emits `ReviewPublished` | Verified-purchase gating uses order/entitlement; rating recompute in transaction; suspect reviews routed to CAP-13. |
| CAP-13 Moderation & trust/safety | NestJS moderation module + admin console + malware scanner + managed text/image moderation + Postgres (moderation queue/decisions, audit log); consumes asset/listing/review/fraud events | Asset scan blocks publish; listing/review moderation queue; takedown revokes entitlements/delists; fraud scoring on orders/payouts; all actions audit-logged. |
| CAP-14 Notifications | NestJS notifications module as Kafka consumer (fan-in) + Postgres (in-app inbox + preferences) + email/push providers + WebSocket gateway | Subscribes to all domain events; per-event preference + opt-out; critical (payment/refund/payout/security) bypass marketing opt-out; dedup/digest batching. |
| CAP-15 Buyer & seller dashboards / analytics | NestJS dashboards module + Postgres read replicas + event-driven rollup tables + CSV/PDF export jobs + scheduled email reports via CAP-14 | Earnings, orders, downloads, payout history from replicas+rollups at launch; ClickHouse warehouse is the documented scale path; exports run as background jobs. |

## Key Architecture Decisions

### AD-01: Modular monolith with pre-carved seams, not microservices (yet)
- **Decision**: Build a single deployable modular monolith (NestJS modules) with strict internal boundaries and an event backbone, designed so search, the money core (payment/ledger/payouts/refunds), delivery/entitlements, moderation, and notifications can be extracted into services later.
- **Context**: Designing for millions of users but launching lean with a small competent team; the domain has clear fault lines.
- **Rationale**: Microservices now would impose distributed-systems tax (network failures, distributed transactions across money and entitlement flows, deployment sprawl) the launch volume can't justify and that would slow the team. A modular monolith keeps money and entitlement flows in-process and transactional while the event boundaries pre-pay the cost of later extraction. Lowest-regret given the scale ramp.
- **Tradeoffs**: Requires discipline to keep boundaries honest (no cross-module table access); a sloppy team turns this into a big ball of mud. Mitigated by enforced module structure, schema-per-module, events as the cross-module contract, and dependency linting in CI.

### AD-02: Postgres as system of record with a double-entry ledger for money
- **Decision**: All transactional state — orders, entitlements/licenses, the seller ledger, refunds, payouts — in PostgreSQL; model fees, balances, refunds, chargebacks, and payouts as an append-only double-entry ledger.
- **Context**: CAP-07/09/10/11 demand auditability, reconciliation, and correctness; "seller ledger" is an explicitly named capability.
- **Rationale**: ACID transactions and relational integrity are exactly suited to money and entitlement state machines. A double-entry ledger makes every seller balance derivable and reconcilable against the gateway, and turns failure modes (charged-but-not-recorded, refunded-but-not-reversed) into detectable, repairable invariants rather than silent loss.
- **Tradeoffs**: A single-primary write ceiling exists far out; deferred to distributed SQL only when proven necessary. Ledger discipline adds modeling effort up front, repaid in audit/dispute/payout confidence.

### AD-03: Entitlement-gated, signed-URL digital delivery via object storage + CDN
- **Decision**: Store assets in private S3-compatible storage; deliver only via short-lived signed URLs/cookies issued after an entitlement check, fronted by a CDN; entitlements are first-class, revocable records in Postgres.
- **Context**: Digital goods are the product (CAP-08); they must be served globally and cheaply, protected from piracy, and revocable on refund/chargeback (CAP-09).
- **Rationale**: Keeping the app tier out of the bytes path is the only way delivery scales to millions without scaling compute. Signed, short-lived, entitlement-checked URLs are the anti-piracy frontline and make revocation effective (a revoked entitlement fails authorization before any URL is minted). Per-download tokens, rate limiting, and optional watermarking/license-key issuance harden it further.
- **Tradeoffs**: Signed-URL plumbing and CDN signing config add complexity; link-sharing within a TTL window is still possible (mitigated by short TTLs, per-download tokens, watermarking). Very large media may need a managed streaming/transcoding tier later.

### AD-04: Event backbone (Kafka-class) as the async + future-extraction spine
- **Decision**: A durable, replayable event log carries domain events to async consumers (notifications, search indexing, ledger posting, payout batching, entitlement revocation, analytics, fraud/moderation).
- **Context**: Notifications (CAP-14) fan in from most capabilities; payment→entitlement→ledger→payout and refund/chargeback→revocation→reversal are async chains; search and analytics are event-fed.
- **Rationale**: Log-based eventing gives per-key ordering (per-seller ledger, per-order entitlement), replay (rebuild index/rollups, re-derive ledger views), and clean multi-consumer fan-out — and is the mechanism that makes later service extraction non-breaking. Right-sizing note: a simpler managed queue is an acceptable MVP substitute if replay isn't yet needed (see research flag).
- **Tradeoffs**: Operational weight and a learning curve; eventual-consistency reasoning required in consumers (a paid order's entitlement/index/notification arrive shortly after, not synchronously). Mitigated by managed Kafka, idempotent/replay-safe consumers, and tracing.

### AD-05: Dedicated search engine (OpenSearch) fed asynchronously from events
- **Decision**: Run search in a separate engine, kept eventually consistent via listing/inventory events, rather than querying Postgres for discovery.
- **Context**: CAP-04 needs relevance ranking, fuzzy matching, facets, and synonyms under read-heavy marketplace traffic; CAP-05 browse is high-volume.
- **Rationale**: Postgres FTS can't meet relevance/facet needs at scale, and discovery traffic would contend with transactional writes. A separate engine isolates that load and can be reshaped/rebuilt independently (replay from the event log).
- **Tradeoffs**: Eventual consistency — a just-published listing may take seconds to appear; acceptable for discovery. Adds a stateful system to operate (use managed).

### AD-06: Cloud-agnostic, container-first infrastructure on open engines
- **Decision**: Docker + Kubernetes (managed) with Terraform, on open-source data/search/event engines available managed on any cloud; PaaS acceptable at MVP; CDN as the delivery tier.
- **Context**: Explicit cloud-agnostic constraint plus growth to millions, with a delivery workload dominated by large binaries.
- **Rationale**: Containers + open engines + Terraform keep the platform portable and horizontally scalable without welding it to one provider. The CDN/object-storage delivery path is what makes serving digital goods to millions affordable. PaaS at launch avoids K8s overhead while container artifacts make the migration low-risk.
- **Tradeoffs**: Operating open engines (even managed) is more work than going all-in on one cloud's proprietary stack — the price of portability. Kubernetes is overkill until volume grows — hence PaaS-first.

### AD-07: Delegate payments, KYC, and tax; own the ledger and entitlements
- **Decision**: Use a marketplace-capable payment gateway (charges, refunds, chargebacks, connected-account payouts), a KYC provider, and a tax-calculation provider; the platform owns the double-entry ledger and the entitlement system as systems of record.
- **Context**: PCI (SAQ A), GDPR, destination-based digital-goods tax, and seller KYC are hard constraints (CAP-01/06/07/09/11); building any of these in-house is high-risk and slow.
- **Rationale**: Delegating card handling keeps the platform out of heavy PCI scope; delegating tax and KYC offloads jurisdiction-by-jurisdiction compliance churn. The platform keeps the parts that are uniquely its domain and must be correct/auditable — the ledger and entitlements — while external providers move money and assert compliance.
- **Tradeoffs**: Vendor coupling and per-transaction fees; gateway feature gaps (e.g., split-payment/payout model) constrain the design — surfaced as open questions below.

## Risks & Tradeoffs

- **Financial correctness under concurrency and failure.** Charges, refunds, chargebacks, fee math, and batched payouts crossing the platform ledger and an external gateway are the highest-stakes paths. *Mitigation*: double-entry ledger as source of truth; idempotency keys on all money operations; a reconciliation job against the gateway; alerting on ledger-vs-gateway and payment-vs-entitlement invariants.
- **Entitlement/delivery integrity (piracy & leakage).** Permanent or over-long-lived URLs, missing revocation on refund/chargeback, or a download path that bypasses the entitlement check would leak paid goods. *Mitigation*: private storage, short-lived signed URLs gated on a non-revoked entitlement, per-download tokens, rate limiting, optional watermarking/license keys, and revocation wired to `RefundIssued`/`ChargebackReceived`.
- **Async consistency gaps.** Paid order but delayed/missing entitlement, refund without revocation, or notification that never fires are the classic event-chain failures. *Mitigation*: durable/ordered event log, idempotent + replay-safe consumers, dead-letter queues with alerting, and end-to-end tracing across API → events → consumers.
- **Search/index consistency lag.** Async indexing means brief windows where a new listing isn't searchable or a taken-down one still appears. *Mitigation*: low-latency pipeline, index-lag monitoring, and a fallback path on a cached snapshot.
- **Modular-monolith boundary erosion.** The later-extraction story collapses if modules share tables or call internals. *Mitigation*: schema-per-module, events as the only cross-module write contract, dependency linting in CI.
- **Real-time notifications at scale.** Long-lived WebSocket connections (in-app notifications) don't fit a purely stateless model and need sticky routing/connection scaling. *Mitigation*: isolate the real-time gateway as a scalable component (an early extraction candidate); fall back to polling if needed.
- **Trust & safety / fraud & malware.** Malicious uploads (malware in software/archives), fake/abusive reviews, listing fraud, and payment fraud are inherent (CAP-13). *Mitigation*: mandatory malware scanning before publish, moderation queues, verified-purchase review gating, fraud scoring on orders/payouts — but detection sophistication is a known gap (research flag).
- **Tax/regulatory correctness.** Digital-goods VAT/GST and US digital-sales-tax rules are complex and jurisdiction-specific. *Mitigation*: delegate to a tax provider, store computed tax + evidence; revisit thresholds (e.g., EU OSS, US economic nexus) with finance/legal.
- **Premature distribution / over-engineering.** Standing up Kafka + Kubernetes + a warehouse on day one for low launch volume would burn runway. *Mitigation*: explicit MVP-vs-scale split — PaaS + managed queue + replica-based analytics at launch, with seams designed so each upgrade is additive.

## Research Suggestions

High-stakes or uncertain choices to validate with the researcher skill before committing:

- **Async backbone: Kafka-class event log vs. managed queue at this scale ramp.** A consequential, hard-to-reverse infrastructure choice (it shapes consumers, ordering, and the extraction story); the right answer depends on real replay/fan-out needs vs. operational budget. Suggested researcher query: *"Event streaming backbone selection for a transactional digital-goods marketplace scaling from thousands to millions of orders: Apache Kafka vs. managed cloud queues (SQS/SNS, Pub/Sub) vs. NATS JetStream — tradeoffs in per-key ordering, replay, exactly-once/idempotency, operational cost, and migration path."*
- **Search technology: managed OpenSearch/Elasticsearch vs. Typesense/Meilisearch vs. Algolia.** Search is core to discovery/conversion (CAP-04) and the relevance/facet/typo requirements are demanding; operational cost, relevance quality, and lock-in differ sharply. Suggested researcher query: *"Search engine selection for a two-sided digital-goods marketplace requiring full-text relevance ranking, fuzzy/typo tolerance, faceted filtering, and synonyms at millions-of-users scale: OpenSearch/Elasticsearch vs. Typesense vs. Meilisearch vs. Algolia — relevance quality, operational burden, cost, and lock-in."*
- **(Secondary) Digital-goods delivery & content protection.** The bytes-path and anti-piracy design is central; signed-URL TTLs, watermarking, license-key issuance, and large-media streaming need validation against real asset types/sizes. Suggested researcher query: *"Secure delivery and anti-piracy for a digital-goods marketplace: signed-URL/signed-cookie CDN delivery, per-download tokens, watermarking, license-key issuance, and managed streaming/transcoding for large media — patterns, tradeoffs, and protection vs. usability."*
- **(Secondary) Payment + tax + KYC provider fit for marketplaces.** Build-vs-buy and provider selection drive PCI scope, payout model, and tax/KYC compliance. Suggested researcher query: *"Marketplace payment platforms with connected-account split payouts plus integrated tax and KYC for cross-border digital goods (Stripe Connect + Stripe Tax vs. Adyen for Platforms vs. others): chargeback handling, payout scheduling, PCI scope, and tax/VAT coverage."*

## Open Questions

- **Payment gateway feature set** — Does the chosen gateway support marketplace **split payments and connected-account payouts**, chargeback webhooks, and scheduled/threshold payouts (Stripe Connect-class)? The ledger/payout design depends on it; if not, more treasury logic moves in-house. *(Needs confirmation; also affects AD-07.)*
- **Identity strategy** — Build on a managed IdP (Auth0/Clerk/Cognito) or self-host (Keycloak)? Affects MFA, social login, per-MAU cost, and portability. Social login expectation for buyers? *(Technical; needs a call.)*
- **Asset types and sizes** — What digital goods are in scope (files, software/keys, large media/video, subscriptions)? Streamable/large media materially changes the delivery tier (transcoding, HLS/DASH, range delivery) and storage cost.
- **License model semantics** — *(Functional, defer to solution-architect)*: how licenses/seats/quotas behave (per-seat, per-device activation, expiry, transfer), and what "inventory" means for infinitely-copyable goods vs. finite keys — these drive CAP-03 modeling but are functional decisions.
- **Refund/chargeback policy & windows** — *(Functional, defer to solution-architect)*: refund eligibility windows, partial refunds, and whether/when entitlements are revoked on refund vs. chargeback. The revocation mechanism is built here; the policy is not.
- **Data residency** — Are there regional data-residency requirements (GDPR/locale) forcing per-region Postgres/storage from the start, or is a single region acceptable at launch?

## Next Steps

1. Stand up the modular-monolith skeleton (NestJS modules + Postgres + Terraform) on a PaaS target, with CI running typecheck/test/migrate and module-boundary linting from day one.
2. Spike the money core: double-entry ledger schema + payment-gateway integration (charge → refund → chargeback webhook → payout) with idempotency keys and a reconciliation job; validate against the gateway sandbox.
3. Spike delivery/entitlements end-to-end: pre-signed upload + malware scan → entitlement grant on `OrderPaid` → short-lived signed-URL download gated on a non-revoked entitlement → revocation on `RefundIssued`/`ChargebackReceived`. Validate signed-URL/CDN config and link-sharing limits.
4. Spike search: index listings from `ListingPublished`/`InventoryChanged` into OpenSearch (or Typesense for the MVP comparison); validate relevance, fuzzy matching, and facets against realistic catalog data; measure the cached-popular path.
5. Resolve the AD-04 (event backbone) and search research flags, then implement the notification fan-in (CAP-14) as the first event consumer end-to-end.
6. Confirm the two key integration assumptions — payment gateway (split payments/connected payouts/chargebacks) and identity strategy — and revise the architecture if either gap exists.
7. Hand this document to the librarian skill to persist as a spec artifact.

---
*Technical architecture produced by technical-architect skill. Use the librarian skill to persist this artifact.*
