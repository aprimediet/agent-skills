# Digital-Goods Marketplace — Technical Architecture

> Technical Architect | Depth: deep | Generated: 2026-06-10

## Source Breakdown

No capability breakdown was supplied as a separate artifact and the **librarian skill is unavailable**, so the capabilities below are an **inline breakdown derived directly from the task statement** — the ~15 capabilities the user enumerated, normalized into a CAP-NN list. No new functional capabilities are invented; where the task is silent on a functional rule, it is flagged back to solution-architect rather than decided here. Running the **solution-architect skill first would produce a stronger, fuller breakdown** (edge cases, error paths, business rules), and this architecture should be re-validated against it once it exists.

Inline capability list (the foundation every technical choice maps to):

- **CAP-01 Seller onboarding & verification** — seller signup, KYC/identity, tax/bank details, payout-account connection, approval to sell.
- **CAP-02 Listing management** — sellers create/edit/publish/unpublish digital-good listings (metadata, pricing, media, variants).
- **CAP-03 Digital asset & inventory/license management** — upload and store the deliverable assets; manage license keys / limited-quantity inventory / license terms per listing.
- **CAP-04 Search & discovery** — buyers browse, full-text search, filter/facet, sort, category browse.
- **CAP-05 Checkout** — cart, order creation, price/tax/discount calculation, order placement.
- **CAP-06 Payment** — charge the buyer via a payment gateway; capture, idempotent processing.
- **CAP-07 Digital delivery & entitlements** — grant the buyer access to purchased goods (downloads, license keys, entitlement records) post-payment.
- **CAP-08 Refunds & chargebacks** — buyer refunds and gateway-initiated chargebacks; revoke/adjust entitlements; reverse ledger entries.
- **CAP-09 Seller ledger** — per-seller accounting of sales, fees, refunds, chargebacks, adjustments; reconcilable balances.
- **CAP-10 Payouts** — pay sellers their available balance on a schedule/threshold; track payout status.
- **CAP-11 Reviews & ratings** — buyers review purchased goods; aggregate ratings.
- **CAP-12 Moderation** — review/approve/flag listings, assets, and review content; handle prohibited content and takedowns.
- **CAP-13 Notifications** — transactional and event-driven notifications across channels (email, in-app, push) to buyers and sellers.
- **CAP-14 Buyer account & library** — buyer-facing view of purchased goods / entitlements (the "my purchases" library and re-download).
- **CAP-15 Admin / platform operations** — operational console for moderation queues, dispute/chargeback handling, payout oversight, ledger reconciliation views.

> CAP-14 and CAP-15 are implied by the enumerated areas (digital delivery/entitlements implies a buyer library; moderation + chargebacks + payouts imply an admin surface). They are called out explicitly so coverage is honest; if they are *not* in scope, drop them — they are not load-bearing for the rest of the design.

## Constraints & Assumptions

- **Scale & load**: Design for growth to **millions of users** **[stated]**. Implies horizontal scalability, a read-heavy browse/search path, strict transactional integrity on money + entitlement flows, and headroom for spikes (launch/sale campaigns, large-asset download bursts). No launch-volume target was given, so assume **cheap at launch, no rewrite to reach millions** **[assumed]**.
- **Team**: **Competent, cloud-agnostic team**, no stated language/framework lock-in **[stated]**. Assume a small-to-mid team that values a mainstream, well-staffed ecosystem over exotic tech **[assumed]**.
- **Hosting**: **Cloud-agnostic, no must-use cloud** **[stated]**. Bias toward portable, open technologies (containers, open-source engines, S3-compatible storage, managed-anywhere services) over proprietary lock-in; a single managed cloud at launch for speed is acceptable **[assumed]**.
- **Hard constraints**:
  - **PCI DSS** scope applies to CAP-06 (payment) and CAP-10 (payout). Assume **SAQ A** posture — never touch raw card data; delegate card capture/storage to a PCI-compliant gateway **[assumed]**.
  - **GDPR / data-protection** obligations apply (buyer/seller PII, KYC data, reviews) — need data-subject export/erasure and regional residency optionality **[assumed]**.
  - **Tax** on digital goods (VAT/MOSS, US sales tax, marketplace-facilitator rules) is a real obligation for CAP-05 — assume a **tax-calculation provider** rather than building tax logic in-house **[assumed]**.
  - **Financial correctness** is a hard constraint: sales, fees, refunds, chargebacks, seller balances, and payouts must be auditable and reconcilable **[assumed, but inherent to the named capabilities]**.
  - **Anti-piracy / asset protection**: digital deliverables must not be served by unauthenticated, shareable URLs — delivery must be entitlement-gated **[assumed, inherent to CAP-07]**.
- **Existing systems**: None stated. Unlike the service-marketplace example, **no existing identity or payment system is given**, so identity and the payment gateway are **selected here** (not assumed pre-existing) and called out as such.

## Architecture Overview

- **Style**: **Modular monolith at launch with pre-carved seams for extraction into services** — a pragmatic hybrid. Rationale: a small competent team at launch can't absorb the operational tax of full microservices, but the domain has clear fault lines — **money/ledger, search, digital delivery, and notifications** — where independent scaling and failure isolation become mandatory at millions of users. Build one (or few) deployable apps organized into strict modules, with an event backbone and clean async boundaries so the highest-pressure modules can be split out later without rewriting callers. Lowest-regret path on the stated scale ramp.
- **Shape**: A stateless API/application tier serves web clients and houses the domain modules (onboarding, listings, assets/licenses, search-facade, checkout, payments, entitlements/delivery, refunds, ledger, payouts, reviews, moderation, notifications, buyer library, admin). A **relational database** is the system of record for transactional state (orders, entitlements, ledger, payouts), fronted by **Redis** for hot reads and idempotency/rate-limit primitives. A **dedicated search engine** (kept in sync from listing events) powers CAP-04 so browse/search never contends with transactional writes. An **event backbone** carries domain events (`OrderPaid`, `EntitlementGranted`, `RefundIssued`, `ChargebackReceived`, `PayoutSent`, `ListingPublished`, `ReviewPublished`) to async consumers — entitlement granting, search indexing, notifications, ledger postings, payout batching, analytics. **Object storage + CDN** hold listing media and the digital deliverables; deliverables are served only through **short-lived, entitlement-gated signed URLs**. Money flows are an append-only **double-entry ledger** for auditability, with an external **payment gateway** as the rail and a **tax provider** for calculation.

## Tech Stack

### Frontend
- **Recommendation**: **TypeScript + React, server-rendered via Next.js** (App Router) — one web app with role-aware surfaces: buyer storefront, seller dashboard, and admin console (CAP-15). Headless component system (Radix/shadcn-style) for control over storefront UI.
- **Why**: The storefront and listing pages (CAP-02, CAP-04, CAP-14) are SEO- and first-paint-sensitive — SSR/ISR improves discovery and conversion. Seller dashboards (CAP-09/10) and checkout (CAP-05) are interactive and benefit from React's ecosystem. Web-first; React Native is a low-friction later path since the skill set carries over.
- **Alternatives**: **Remix** — prefer for a more web-standards-centric data/forms model. **SvelteKit** — leaner runtime if the team has Svelte depth; weaker hiring pool/ecosystem at scale. Admin (CAP-15) can be a separate internal app (e.g., Refine/React-admin) to keep the storefront lean.

### Backend / API
- **Recommendation**: **TypeScript on Node.js (NestJS)** for the application tier, exposing a **REST/JSON API** (OpenAPI-documented) with a thin BFF for Next.js. NestJS modules map cleanly onto the modular-monolith seams; one language front-to-back reduces context switching for a small team.
- **Why**: The workload is I/O-bound orchestration (gateway, tax provider, search, DB, queue, object storage) where Node excels. NestJS's module/provider structure enforces the internal boundaries the architecture depends on. REST keeps the public surface simple and cacheable.
- **Alternatives**: **Go (Echo/Fiber)** — prefer if the team is Go-native or if the ledger/payout/delivery hot paths later need very high throughput and tight latency/footprint; costs shared-language productivity. **Java/Kotlin + Spring Boot** — prefer if the team's center of gravity is JVM and the financial domain wants its mature transactional ecosystem. **GraphQL** for the dashboard read paths specifically — a targeted later optimization, not a foundation.

### Data storage

**Primary database (system of record)**
- **Recommendation**: **PostgreSQL** (managed), one logical database with schema-per-module discipline, primary + read-replica topology.
- **Why**: Orders, entitlements, the seller ledger, refunds/chargebacks, and payouts (CAP-05–CAP-10) demand ACID transactions, strong consistency, and correctness. Granting an entitlement and recording the sale must be atomic; ledger math must be exact. Postgres scales vertically far and horizontally via replicas for read-heavy browse/library/dashboard paths; open-source and managed on every cloud (cloud-agnostic).
- **Alternatives**: **MySQL/MariaDB** — equivalent fit; prefer only with deeper MySQL operational muscle. **CockroachDB / Spanner-class distributed SQL** — only when single-primary write throughput becomes the proven ceiling; defer (cost/complexity now). Do **not** put the ledger or entitlements in a document store.

**Cache**
- **Recommendation**: **Redis** (managed) for hot reads (listing/category pages, popular search results), session/rate-limit counters, **idempotency keys** on money operations, and short-lived license-key reservation locks (atomic `SET NX` + TTL) where inventory is limited (CAP-03).
- **Why**: Limited-quantity goods / unique license keys need atomic, expiring reservations to prevent over-selling under contention — a textbook Redis use case. Idempotency-key storage makes payment/refund/payout retries safe. Caches the cached-popular path for CAP-04.
- **Alternatives**: **Valkey** — drop-in open-source fork; prefer if licensing portability is a concern. **Memcached** — pure key/value caching only; loses the atomic/expiry primitives the inventory hold relies on.

**Search engine**
- **Recommendation**: **OpenSearch** (or Elasticsearch) as a dedicated cluster powering CAP-04, fed asynchronously from listing-change events.
- **Why**: CAP-04 needs full-text relevance, fuzzy/typo tolerance, faceted filters (category, price, rating, tags), and sort — none of which Postgres does well at marketplace scale, and discovery load must never contend with transactional writes. The index is rebuildable/reshapeable independently by replaying the event log. OpenSearch is Apache-2.0 and managed on every major cloud.
- **Alternatives**: **Typesense / Meilisearch** — prefer at MVP for far simpler ops and excellent typo-tolerance out of the box; revisit if relevance tuning and aggregation needs outgrow them. **Postgres FTS + `pg_trgm`** — viable only at launch volume to defer a search cluster; explicitly a bridge, not the millions-of-users answer (research flag below).

**Object / blob storage (listing media + digital deliverables)**
- **Recommendation**: **S3-compatible object storage** with a **CDN** in front. Two distinct buckets/prefixes with different policies: (1) **public media** (listing images/previews) served via CDN; (2) **protected deliverables** (the actual digital goods, CAP-03/CAP-07) in a **private** bucket, served only via **short-lived signed URLs minted after an entitlement check**, ideally through signed-CDN-URL delivery so large downloads don't hit the origin. Seller uploads go **direct-to-storage via pre-signed PUT** so the API tier stays out of the bytes path.
- **Why**: Deliverables are the product and the piracy surface — they must never be reachable by a guessable or shareable static URL. Entitlement-gated, expiring signed URLs (optionally watermarked/per-buyer tokens for high-value goods) are the standard control. Public previews and protected goods need different access policies, hence the split. S3-compatible APIs keep this portable (MinIO on-prem). CDN offloads large-file egress globally.
- **Alternatives**: GCS / Azure Blob — fine; standardize on the S3 API to stay portable. For very large deliverables, consider resumable/multipart upload and download.

**Analytics store**
- **Recommendation**: **Defer a dedicated warehouse at launch**; serve seller-dashboard and admin metrics (CAP-09/15) from read replicas + pre-aggregated rollup tables/materialized views fed by events. Introduce a **columnar warehouse (ClickHouse, or BigQuery/Snowflake-class)** when analytical query volume or history depth strains replicas.
- **Why**: Early dashboards are bounded per-seller aggregations (sales, fees, balance over windows) that replicas + rollups handle well. Standing up a warehouse before there's data is over-engineering; the event backbone makes adding one later additive, not a rewrite. **ClickHouse** is the opinionated pick when the time comes (cost/perf on append-heavy data, open-source/portable).

### Async / messaging

**Needed** — entitlement granting, search indexing, notification fan-out, ledger postings, payout batching, and chargeback handling are all naturally asynchronous and fan out from a handful of money/lifecycle events. CAP-13 alone fans in from most other capabilities.

- **Recommendation**: **A durable event log — Apache Kafka (or a Kafka-compatible managed service)** for domain events, plus a lightweight **job runner (BullMQ on Redis)** for in-process background work (email rendering, report/export generation, retries) at launch.
- **Why**: Events — `OrderPaid`, `EntitlementGranted`, `RefundIssued`, `ChargebackReceived`, `PayoutSent`, `ListingPublished`, `ReviewPublished`, `ModerationDecided` — need durable, replayable, ordered (per-key) delivery to multiple independent consumers (entitlements CAP-07, indexing CAP-04, notifications CAP-13, ledger CAP-09, payout batching CAP-10, analytics). A log gives ordering per key (per-order, per-seller-ledger), replay (rebuild the index or recompute rollups), and clean fan-out — and is the mechanism that lets modules be extracted into services later without changing producers. The Redis-backed runner covers simple off-request-path work cheaply.
- **Alternatives**: **RabbitMQ / cloud queues (SQS+SNS, Pub/Sub)** — prefer at MVP if replay/ordering isn't yet needed and you want lower operational overhead; you lose the event-log replay that makes index/ledger rebuilds easy. **NATS JetStream** — a lighter-weight log with good ordering if Kafka's footprint is unwelcome. It is defensible to **launch on a managed queue and adopt Kafka when replay/fan-out volume demands it** — flagged for research below.

### Authentication & authorization
- **Recommendation**: **A managed/self-hosted IdP via OIDC/OAuth2** — **Keycloak** (self-hosted, portable) as the opinionated cloud-agnostic pick, or a managed IdP (Auth0/Cognito) if the team prefers not to run it. The app tier consumes signed tokens (JWT access tokens, rotating refresh tokens in secure HTTP-only cookies). **Authorization** lives in the app tier as **role- + relationship-based access control**: roles (buyer, seller, moderator, admin) plus relationship/ownership checks (a seller edits only their own listings; a buyer downloads only goods they have an entitlement for; only a verified+approved seller can publish or be paid out).
- **Why**: Unlike the service-marketplace example, **no existing identity system is given**, so one must be chosen — OIDC keeps it standards-based and swappable, and Keycloak keeps it portable. Authorization is domain-specific and must be owned: entitlement-gated download (CAP-07/14), seller-approval gating (CAP-01 → CAP-02/CAP-10), and moderator/admin elevation (CAP-12/15) are all platform-owned policy. Centralize as a NestJS policy/guard layer so every module enforces consistently.
- **Alternatives**: Fully managed IdP (Auth0/Cognito/Clerk) — faster to launch, less to operate, at the cost of some portability and per-MAU pricing at scale. For fine-grained, relationship-heavy authorization that grows complex, a policy engine (**OpenFGA / Oso / OPA**) is a later option; start with code-level guards.

### Infrastructure & hosting
- **Recommendation**: **Containers (Docker) on Kubernetes** (managed: EKS/GKE/AKS — pick one cloud at launch, stay portable), stateless app tier behind a load balancer and autoscaled horizontally; managed services for Postgres, Redis, OpenSearch, and the event backbone; CDN for media and signed-URL deliverable downloads.
- **Why**: Cloud-agnostic + growth to millions points to containers on Kubernetes as the portable, horizontally-scalable substrate — same artifacts on any cloud or on-prem. Managed data services avoid operating stateful systems yourself while staying on open engines. The stateless app tier scales out trivially; search, cache, and the event backbone scale independently — the point of the seams.
- **Alternatives**: **PaaS (Fly.io / Render / cloud App Platform)** — strongly prefer *at MVP* to avoid Kubernetes overhead; the container-first design makes the eventual K8s migration mostly packaging, not rewriting. **Serverless functions** — good for spiky stateless edges (image/preview processing on upload, signed-URL minting, scheduled payout/report jobs), but a poor fit for the always-warm transactional core; use selectively, not as the foundation.

### CI/CD & developer tooling
- **Recommendation**: **Trunk-based development with GitHub Actions (or GitLab CI)**; pipeline runs lint → typecheck → unit/integration tests → build container → deploy to staging → promote to prod. **Infrastructure as Code via Terraform** (cloud-agnostic). Database migrations versioned and run in-pipeline (Prisma Migrate / Flyway). Environments dev → staging → prod, with ephemeral preview environments per PR if budget allows. **Module-boundary / dependency linting in CI** to keep the monolith modular.
- **Why**: A modular monolith deploys as one/few artifacts, keeping CI/CD simple — a major saving over microservices. Terraform keeps infra reproducible and not welded to one cloud. Migration discipline is non-negotiable given the financial + entitlement schema where ad-hoc drift would be dangerous.
- **Alternatives**: **Pulumi** — prefer if the team would rather express infra in TypeScript; smaller ecosystem than Terraform. **GitOps (Argo CD)** — adopt once on Kubernetes for declarative deploys.

### Observability
- **Recommendation**: **OpenTelemetry** for traces/metrics/logs (vendor-neutral, cloud-agnostic), exported to a self-host-or-buy backend: **Prometheus + Grafana** (metrics), **Loki** or ELK/OpenSearch (logs), **Tempo/Jaeger** (tracing). Structured logging with correlation IDs propagated from API through events to async consumers.
- **Why**: Money + entitlement + async fan-out are the hardest things to debug — a payment captured but entitlement not granted (CAP-06→CAP-07), a chargeback that didn't revoke access (CAP-08), a payout that silently failed (CAP-10), a notification that never fired (CAP-13). Distributed tracing across API → event log → consumers makes these diagnosable. OTel avoids vendor lock-in. **Alert on business invariants**: payments-without-entitlements, ledger-vs-gateway balance mismatch, dead-letter depth, payout failure rate, search index lag, signed-URL mint error rate.
- **Alternatives**: **Datadog / Grafana Cloud / Honeycomb** — prefer managed if the team would rather not run the stack; OTel instrumentation means switching backends without re-instrumenting.

### Third-party services & integrations
- **Payment gateway** — card capture, charging, idempotent processing, refunds, chargeback/webhook events, and **connected-account payouts** for CAP-06, CAP-08, CAP-10. A gateway with marketplace/split-payment + connected-account + payout support (Stripe Connect-class, or Adyen/Braintree-MarketPay) keeps the platform out of direct PCI scope and provides the payout rails. The platform's **ledger records the truth**; the gateway moves the money.
- **Tax calculation** — a tax provider (Stripe Tax / Avalara / TaxJar-class) for CAP-05 to compute VAT/sales tax on digital goods and support marketplace-facilitator reporting. Building tax logic in-house is a trap at this scope.
- **KYC / identity verification** — for CAP-01 seller verification; often provided by the same connected-accounts payment provider (Stripe Connect onboarding/KYC), else a dedicated KYC vendor. Avoids storing raw identity documents yourself.
- **Email delivery** — transactional email provider (SES/SendGrid/Postmark-class) for CAP-13 and scheduled reports.
- **Push notifications** — web push (Push API), FCM/APNs when native apps arrive, for CAP-13.
- **Content moderation** — CAP-12 listing/asset/review scanning: start with rules/heuristics in-app plus malware/AV scanning on uploaded assets; a managed moderation/classification API or model is the scale path (research flag).
- **Anti-malware scanning of seller assets** — uploaded deliverables (CAP-03) should be AV/malware-scanned before they can be sold/delivered (a clamav-style scanner or a managed scanning service running as an async consumer on upload).

### Security
- **Secrets management**: dedicated secrets store (**HashiCorp Vault** for portability, or the cloud's secrets manager) — gateway/tax/KYC API keys, DB credentials, URL-signing keys. No secrets in code or images.
- **PCI scope minimization**: card data never touches the platform — gateway hosted fields/tokenization keep the platform at SAQ A; store only tokens/references.
- **Deliverable protection (anti-piracy)**: protected goods live in a private bucket; access only via **entitlement-checked, short-TTL signed URLs** (ideally signed-CDN URLs); consider per-buyer watermarking/tokenization for high-value goods; rate-limit and log download requests; revoke on refund/chargeback (CAP-08).
- **Encryption**: TLS everywhere in transit; encryption at rest on Postgres, Redis, object storage, and backups (managed defaults + enforced policy). Field-level encryption for the most sensitive PII (payout bank details, KYC references) above gateway tokenization.
- **GDPR controls**: data-subject export and erasure (profile, reviews, purchase history subject to legal-retention exceptions on financial records); regional residency via per-region Postgres/storage if required.
- **Application security**: input validation at the API boundary, output encoding, **rate limiting** (Redis-backed) on auth, search, checkout, and download endpoints; **idempotency keys** on all money-moving operations (payment, refund, payout) to make retries safe; **signed gateway webhooks with replay protection** (the chargeback/payment event source must be verified). Moderator/admin actions (CAP-12/15) audit-logged.

## Capability → Tech Mapping

| Capability | Implemented by | Notes |
|-----------|----------------|-------|
| CAP-01 Seller onboarding & verification | NestJS onboarding module + Postgres (seller records, status) + IdP (account) + payment-gateway connected-account onboarding/KYC | Approval gate flips the flag that lets CAP-02 publish and CAP-10 pay out; raw ID docs stay with the KYC/gateway provider. |
| CAP-02 Listing management | NestJS listing module + Postgres (listing records) + S3 pre-signed media uploads + CDN; emits `ListingPublished`/update events to Kafka | Publish gated on approved-seller status; events drive async search indexing (no synchronous coupling to search). |
| CAP-03 Asset & inventory/license mgmt | NestJS assets module + **private** S3 bucket (deliverables) + Postgres (license keys, inventory counts, terms) + Redis (atomic key reservation, TTL) + async AV/malware scan consumer | Deliverables never public; limited inventory/unique keys reserved atomically to prevent over-sell; assets scanned before becoming sellable. |
| CAP-04 Search & discovery | OpenSearch cluster fed from listing events; Redis-cached popular results | Separate engine so browse load never hits the transactional DB; fuzzy matching + facets from the index; cached-popular path for low latency. |
| CAP-05 Checkout | NestJS checkout module + Postgres (cart/order, ACID) + tax provider (tax calc) + Redis (inventory holds) | Order placement computes price/tax/discount; reserves limited inventory; creates the order before payment, then drives CAP-06. |
| CAP-06 Payment | NestJS payments module + payment gateway (charge) + Postgres (order/payment state) + Redis (idempotency keys) + emits `OrderPaid` | Idempotent capture; signed webhook reconciliation handles the "charged but not recorded" path; `OrderPaid` triggers entitlement + ledger. |
| CAP-07 Digital delivery & entitlements | NestJS entitlements module (Kafka consumer of `OrderPaid`) + Postgres (entitlement records) + signed-URL/CDN delivery from private bucket | Entitlement granted atomically with the sale; download served only via short-TTL entitlement-checked signed URLs; emits `EntitlementGranted`. |
| CAP-08 Refunds & chargebacks | NestJS refunds module + payment gateway (refund + chargeback webhooks) + Postgres double-entry ledger (reversal) + entitlement revocation; emits `RefundIssued`/`ChargebackReceived` | Chargeback webhook is the trigger for revoke + ledger reversal + seller-balance debit; idempotent; admin (CAP-15) handles disputes/representment. |
| CAP-09 Seller ledger | NestJS ledger module (Kafka consumer) + Postgres append-only double-entry ledger | Posts entries on `OrderPaid` (sale − fee), `RefundIssued`, `ChargebackReceived`, adjustments; balances derivable and reconcilable vs. the gateway. |
| CAP-10 Payouts | NestJS payouts module + Postgres ledger (available balance) + payment-gateway transfers + Kafka consumer (batching) + scheduled jobs | Respects schedule/threshold + seller-approval/KYC status; batches transfers to cut fees; idempotent; failed-payout retries + seller notification. |
| CAP-11 Reviews & ratings | NestJS reviews module + Postgres (reviews, rating aggregates) + entitlement check (only buyers who own the good may review) + moderation hold; emits `ReviewPublished` | Verified-purchase gate via entitlement; rating recompute in transaction; flagged content routed to CAP-12. |
| CAP-12 Moderation | NestJS moderation module + Postgres (queues, decisions) + content-scanning/AV + admin UI (CAP-15); emits `ModerationDecided` | Listing/asset/review review; takedown unpublishes (drives a search-index update); decisions audit-logged. |
| CAP-13 Notifications | NestJS notifications module as Kafka consumer (fan-in) + Postgres (in-app inbox) + email provider + web push | Subscribes to all domain events; per-user preference lookup; critical money/security notifications bypass opt-out; dedup/digest batching. |
| CAP-14 Buyer account & library | NestJS library module + Postgres (entitlements) + signed-URL re-download + Postgres read replicas | "My purchases" = entitlement list; re-download re-mints a fresh signed URL after re-checking the entitlement (revoked on refund/chargeback). |
| CAP-15 Admin / platform ops | Separate admin app (React-admin/Refine) + NestJS admin module + Postgres (read replicas) + audit log | Moderation queues, chargeback/dispute handling, payout oversight, ledger-vs-gateway reconciliation views; elevated role, all actions audited. |

## Key Architecture Decisions

### AD-01: Modular monolith with pre-carved seams, not microservices (yet)
- **Decision**: Build a single deployable modular monolith (NestJS modules) with strict internal boundaries and an event backbone, designed so search, payments/ledger, digital delivery, and notifications can be extracted into services later.
- **Context**: Designing for millions of users with a small competent team; clear domain fault lines; no stated launch volume but a need to be cheap early.
- **Rationale**: Microservices now impose distributed-systems tax (network failures, distributed transactions across money/entitlement flows, deployment complexity) the early stage can't justify and that slows the team. A modular monolith keeps the *grant-entitlement-with-the-sale* transaction in-process and ACID while event boundaries pre-pay later extraction. Lowest-regret on the scale ramp.
- **Tradeoffs**: Requires discipline (no cross-module table reach); a sloppy team turns it into a big ball of mud. Mitigated by schema-per-module, events as the cross-module write contract, and dependency linting in CI.

### AD-02: Postgres as system of record with a double-entry ledger for money
- **Decision**: All transactional state in PostgreSQL; model sales, fees, refunds, chargebacks, adjustments, and payouts as an append-only double-entry ledger.
- **Context**: CAP-06/08/09/10 demand auditability, reconciliation, and exactness across sales, reversals, balances, and payouts.
- **Rationale**: ACID + relational integrity are exactly suited to money state machines. A double-entry ledger makes every seller balance derivable and reconcilable against the gateway, and turns "charged but not recorded" / "refunded but balance not debited" into detectable, repairable invariants rather than silent loss.
- **Tradeoffs**: Single-primary write ceiling exists far out; defer distributed SQL until proven necessary. Ledger discipline adds modeling effort up front, repaid in audit/reconciliation confidence.

### AD-03: Entitlement-gated delivery from a private bucket via short-lived signed URLs
- **Decision**: Store digital deliverables in a private S3-compatible bucket; serve them only through short-TTL, entitlement-checked signed (CDN) URLs; revoke access on refund/chargeback.
- **Context**: The deliverables *are* the product and the piracy surface; CAP-07/14 must gate access and CAP-08 must revoke it; CAP-03 separates public previews from protected goods.
- **Rationale**: A static or public URL would leak the product permanently. Minting a fresh expiring URL only after an entitlement check (and re-checking on every re-download) ties access to a live, revocable grant — the standard, scalable anti-piracy control — while the CDN absorbs large-file egress.
- **Tradeoffs**: URL-signing keys become security-critical secrets (Vault); determined sharing of a live URL within its TTL is still possible (mitigate with short TTLs, per-buyer tokens/watermarking for high-value goods, and download rate limits). Adds a mint-on-access step rather than a static link.

### AD-04: Dedicated search engine (OpenSearch) fed asynchronously from events
- **Decision**: Run search in a separate engine, kept eventually consistent via `ListingPublished`/update/takedown events, rather than querying Postgres for discovery.
- **Context**: CAP-04 needs relevance ranking, fuzzy matching, and faceted filters under read-heavy browse traffic; CAP-12 takedowns must remove items from results.
- **Rationale**: Postgres FTS can't meet relevance/facet needs at scale and discovery would contend with transactional writes. A separate engine isolates that load and is rebuildable/reshapeable by replaying the event log.
- **Tradeoffs**: Eventual consistency — a just-published or just-taken-down listing may lag by seconds in search. Acceptable for discovery; mitigate takedown lag with a synchronous index-delete on moderation action for safety-critical removals. Adds a stateful system to operate (use managed).

### AD-05: Event backbone (Kafka-class) as the async + future-extraction spine
- **Decision**: A durable, replayable event log carries domain events to async consumers (entitlements, indexing, ledger, notifications, payout batching, analytics).
- **Context**: Entitlement granting, ledger postings, notification fan-out (CAP-13 fans in from most capabilities), and payout batching are async; search/ledger/analytics must be (re)buildable.
- **Rationale**: Log-based eventing gives per-key ordering (per-order, per-seller), replay (rebuild index/rollups, recompute ledger views), and clean multi-consumer fan-out, and makes later service extraction non-breaking. A simpler managed queue is an acceptable MVP substitute if replay isn't yet needed (research flag).
- **Tradeoffs**: Operational weight and eventual-consistency reasoning in consumers. Mitigated by managed Kafka and idempotent, replay-safe consumers. Critically: the *grant-entitlement* step should remain transactional with the sale (or be made idempotent + reconciled) so a consumer hiccup never leaves a paid buyer without their goods.

### AD-06: Cloud-agnostic, container-first infrastructure on open engines
- **Decision**: Docker + Kubernetes (managed) with Terraform, on open-source data/search/event engines available managed on any cloud; PaaS acceptable at MVP.
- **Context**: Explicit cloud-agnostic constraint plus growth to millions.
- **Rationale**: Containers + open engines + Terraform keep the platform portable and horizontally scalable without welding to one provider's proprietary services. PaaS at launch avoids K8s overhead while container artifacts make eventual migration low-risk.
- **Tradeoffs**: Operating open engines (even managed) is more work than going all-in on one cloud's proprietary stack — the price of portability. Kubernetes is overkill until volume grows, hence PaaS-first.

### AD-07: Buy identity, tax, and KYC rather than building them
- **Decision**: Use an OIDC IdP (Keycloak/managed) for auth, a tax provider for CAP-05, and the connected-accounts gateway (or a KYC vendor) for CAP-01 verification.
- **Context**: No existing identity/payment/tax systems were stated; tax, KYC, and PCI are high-liability, non-differentiating domains.
- **Rationale**: These are correctness- and compliance-critical areas where vendor solutions are mature and cheap relative to the legal risk of getting them wrong. Owning them would burn runway and create liability with no product advantage.
- **Tradeoffs**: Vendor dependency and per-transaction/per-MAU pricing; mitigated by keeping the platform ledger as source of truth and using standards (OIDC) so identity is swappable.

## Risks & Tradeoffs

- **Payment-to-entitlement atomicity.** The single most important invariant: a buyer who paid must always get their goods, and a buyer who didn't (or was refunded/charged-back) must not. *Mitigation*: grant the entitlement in the same transaction as recording the paid order where possible, or make the `OrderPaid`→grant consumer idempotent with a reconciliation job that alerts on paid-without-entitlement; revoke on `ChargebackReceived`/`RefundIssued`.
- **Financial correctness under concurrency and failure.** Sales, fees, refunds, chargebacks, and batched payouts across the ledger and an external gateway are high-stakes. *Mitigation*: double-entry ledger as source of truth, idempotency keys on all money operations, signed-webhook verification, and a reconciliation job + alerts on ledger-vs-gateway mismatch.
- **Digital-goods piracy / leakage.** Entitlement-gated signed URLs reduce but don't eliminate sharing within a URL's lifetime. *Mitigation*: short TTLs, per-buyer tokens/watermarking for high-value goods, download rate limiting + anomaly detection, immediate revoke on refund/chargeback.
- **Over-selling limited inventory / license keys.** Limited-quantity goods can be double-sold under contention. *Mitigation*: atomic Redis reservation (TTL) at checkout plus a DB uniqueness/transaction guard at fulfillment — defense in depth.
- **Refund/chargeback abuse on instantly-delivered goods.** Digital goods are delivered immediately, so chargebacks after download are a real fraud/loss vector. *Mitigation*: fraud signals at checkout, gateway risk tooling, entitlement revocation, and ledger reversal — but the *policy* (what's refundable, dispute handling) is a solution-architect question, flagged below.
- **Search/index consistency lag, esp. takedowns.** A moderated-down listing lingering in results is a trust/legal risk. *Mitigation*: synchronous index-delete on takedown; index-lag monitoring; cached-snapshot fallback for the read path.
- **Modular-monolith boundary erosion.** The extraction story collapses if modules share tables/internals. *Mitigation*: schema-per-module, events as the only cross-module write contract, dependency linting in CI.
- **Premature distribution / over-engineering.** Kafka + Kubernetes + a warehouse on day one would burn runway. *Mitigation*: explicit MVP-vs-scale split — PaaS + managed queue + replica-based analytics at launch, every upgrade additive.

## Research Suggestions

High-stakes or uncertain choices to validate with the researcher skill before committing:

- **Async backbone: Kafka-class event log vs. managed queue at this scale ramp.** Consequential, hard-to-reverse infrastructure that shapes consumers, ordering, and the extraction story; the right answer depends on real replay/fan-out needs vs. operational budget. Suggested researcher query: *"Event streaming backbone selection for a transactional digital-goods marketplace scaling from launch to millions of users: Apache Kafka vs. managed cloud queues (SQS/SNS, Pub/Sub) vs. NATS JetStream — tradeoffs in per-key ordering, replay, idempotency/exactly-once, operational cost, and migration path, with emphasis on payment→entitlement and ledger-posting consumers."*
- **Digital-goods delivery & anti-piracy architecture.** Delivery is the core differentiator and the main loss vector; signed-URL design, watermarking, CDN signing, and license-key models differ sharply in security and cost. Suggested researcher query: *"Secure delivery architecture for paid digital goods at scale: entitlement-gated short-lived signed URLs vs. signed-CDN URLs vs. tokenized/watermarked downloads vs. DRM — anti-piracy effectiveness, CDN integration, large-file/resumable download support, revocation on refund/chargeback, and cost."*
- **(Secondary) Payment + tax + connected-account provider selection for a digital-goods marketplace.** PCI scope, marketplace-facilitator tax obligations, connected-account payouts, and KYC are tightly coupled and vendor-specific. Suggested researcher query: *"Payment and tax provider selection for a global digital-goods marketplace: Stripe Connect + Stripe Tax vs. Adyen MarketPay vs. Braintree + Avalara/TaxJar — connected-account payouts, KYC onboarding, marketplace-facilitator VAT/sales-tax handling, chargeback tooling, and PCI SAQ-A scope."*

## Open Questions

- **Refund / chargeback policy for instantly-delivered goods** — What is refundable after download, and how are disputes/representment handled? This is a functional rule (solution-architect's territory) that the refund/ledger/entitlement design depends on — flagged, not invented here.
- **License model specifics** — Are deliverables single-download, perpetual re-download, per-seat license keys, subscription, or limited-quantity? CAP-03/07/14 implementations differ; needs the functional definition.
- **Tax/regulatory footprint** — Which jurisdictions at launch (EU VAT/MOSS, US marketplace-facilitator, others)? Determines tax-provider configuration and possible data-residency needs.
- **Seller payout model** — Is the platform merchant-of-record (collects, then pays sellers from its ledger) or a facilitator using connected accounts (gateway splits at sale)? This materially changes the ledger, payout, and tax design and should be settled with solution-architect/finance before build.
- **KYC depth** — How much identity verification is required to sell / be paid out, and in which regions? Determines KYC vendor and onboarding flow.
- **Native mobile** — Web-only assumed; if native apps are near-term, it affects auth (token storage), push (FCM/APNs), and possibly delivery (in-app downloads).

## Next Steps

1. Run the **solution-architect skill** to produce a proper capability breakdown (edge cases, error paths, business rules) and re-validate this architecture against it — especially the refund/license/payout-model open questions.
2. Stand up the modular-monolith skeleton (NestJS modules + Postgres + Terraform) on a PaaS target, with CI running typecheck/test/migrate and module-boundary linting from day one.
3. Spike the money + entitlement core: order → gateway charge (idempotent) → `OrderPaid` → grant entitlement (atomic/reconciled) → double-entry ledger posting → signed-URL delivery; validate the paid-without-entitlement reconciliation and chargeback-revoke paths against the gateway sandbox.
4. Spike secure delivery: private bucket + entitlement-checked short-TTL signed (CDN) URLs + revocation, per the AD-03 / delivery research flag; validate large-file download and re-download from the buyer library (CAP-14).
5. Spike search: index listings from `ListingPublished`/takedown events into OpenSearch (or Typesense for the MVP comparison); validate relevance, facets, and synchronous takedown removal.
6. Confirm the key vendor decisions — payment/tax/KYC provider (AD-07) and the payout/merchant-of-record model — and revise the ledger/payout design accordingly.
7. Hand this document to the librarian skill to persist as a spec artifact.

---
*Technical architecture produced by technical-architect skill. Use the librarian skill to persist this artifact.*
