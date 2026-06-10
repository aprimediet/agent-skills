# Marketplace Platform — Technical Architecture

> Technical Architect | Depth: deep | Generated: 2026-06-10

## Source Breakdown

This architecture builds on the solution-architect capability breakdown for a two-sided service marketplace. It was provided inline as the source breakdown (the librarian skill was not available to retrieve it), and every technical choice below is anchored to a capability defined there. No new functional capabilities are introduced — where a gap surfaces, it is flagged back rather than invented.

- [Marketplace Platform (capability breakdown)](../../solution-architect/examples/marketplace-platform.md) — Two-sided marketplace: listing management, search/discovery, booking, payment & escrow, messaging, reviews, dispute resolution, provider payouts, notifications, and dashboards/analytics (CAP-01 through CAP-10).

## Constraints & Assumptions

- **Scale & load**: Design for growth to **millions of users** **[stated]**. Implies horizontal scalability, read-heavy search/discovery, transactional integrity on money flows, and headroom for traffic spikes (search during campaigns, payout batches). MVP launch target from the breakdown is 1,000 completed transactions/month within 6 months **[stated]**, so the architecture must be *cheap at launch but not require a rewrite to reach millions* **[assumed]**.
- **Team**: Competent engineering team, no stated language/framework lock-in **[stated]**. Assume a small-to-mid team at launch that values productivity and a mainstream, well-staffed ecosystem over exotic tech **[assumed]**.
- **Hosting**: **Cloud-agnostic**, no must-use cloud **[stated]**. Bias toward portable, open technologies (containers, open-source data stores, managed-anywhere services) over proprietary lock-in, while still allowing a single managed cloud at launch for speed **[assumed]**.
- **Hard constraints**:
  - **PCI DSS** scope applies to CAP-04 (payment) and CAP-08 (payout). Assume **SAQ A** posture — never touch raw card data; delegate card capture and storage to a PCI-compliant gateway **[assumed]**.
  - **GDPR / data-protection** obligations apply (PII for clients and providers, messaging content, reviews) — need data-subject export/erasure and regional residency optionality **[assumed]**.
  - **Financial correctness** is a hard constraint: escrow holds, fee math, refunds, and payouts must be auditable and reconcilable (the breakdown explicitly calls out reconciliation in CAP-04 and CAP-08) **[stated]**.
- **Existing systems** (from the breakdown, treated as integration points, not things to rebuild): user account & authentication system, email notification service, payment gateway, cloud file/object storage. The architecture integrates with these rather than reimplementing them.

## Architecture Overview

- **Style**: **Modular monolith at launch, with a small set of pre-carved seams for extraction into services** — a pragmatic hybrid. Rationale: the team and launch volume don't justify the operational tax of full microservices, but the domain has *natural fault lines* (money, search, messaging, notifications) where independent scaling and failure isolation will be required at millions of users. Build one deployable app organized into strict modules, and design the money and async boundaries so the highest-pressure modules (search, payments/ledger, messaging, notifications) can be split out later without rewriting callers. This is the lowest-regret path: it avoids premature distribution while pre-paying the design cost of the seams that scale demands.
- **Shape**: A stateless API/application tier serves web clients and houses the domain modules (listings, search-facade, booking, payments/escrow/ledger, messaging, reviews, disputes, payouts, notifications, dashboards). A relational database is the system of record for transactional state (bookings, escrow, ledger, disputes), fronted by a cache for hot reads. A dedicated **search engine** (kept in sync from the listing module) powers CAP-02 so discovery never contends with the transactional database. An **event backbone** carries domain events (booking confirmed, payment captured, dispute opened, funds released) to asynchronous consumers — notifications, search indexing, analytics, payout batching — so user-facing flows aren't blocked on slow or fan-out work. A **real-time channel** delivers live messages and in-app notifications. Object storage holds listing media and message/dispute attachments. The money flows (escrow, fees, payouts) are implemented as an append-only **double-entry ledger** for auditability, with the external payment gateway as the rail.

## Tech Stack

### Frontend
- **Recommendation**: **TypeScript + React, server-rendered via Next.js** (App Router), as a single web app with role-aware views (client vs. provider dashboards). Component library: a headless system (Radix/shadcn-style) for control over the marketplace UI.
- **Why**: Search/discovery (CAP-02) and listing detail pages (CAP-01) are SEO- and first-paint-sensitive — server rendering improves both. Dashboards (CAP-10) and booking (CAP-03) are interactive and benefit from React's ecosystem. The breakdown is web-only for MVP, so no native mobile is needed yet; React Native is a low-friction future path because the skill set carries over.
- **Alternatives**: **Remix** — prefer if the team wants a more web-standards-centric data/forms model and simpler caching mentality. **SvelteKit** — prefer for a smaller bundle and leaner runtime if the team has Svelte experience; weaker hiring pool and ecosystem at marketplace scale.

### Backend / API
- **Recommendation**: **TypeScript on Node.js (NestJS)** for the application tier, exposing a **REST/JSON API** (OpenAPI-documented) with a thin BFF layer for the Next.js frontend. One language across front and back reduces context-switching for a small team; NestJS gives module boundaries that map cleanly onto the modular-monolith seams.
- **Why**: The workload is I/O-bound orchestration (calling the gateway, search, DB, queue) rather than CPU-bound, where Node excels. NestJS's module/provider structure enforces the internal boundaries the architecture depends on. REST keeps the public surface simple and cacheable; GraphQL's main win (client-shaped queries over many entities) is real for the dashboards but not worth the complexity tax across the whole API at this stage.
- **Alternatives**: **Go (with a framework like Echo/Fiber)** — prefer if the team is Go-native or if the money/ledger and payout services later need very high throughput and tight latency/footprint; costs you the shared-language productivity. **Java/Kotlin + Spring Boot** — prefer if the team's center of gravity is JVM and the financial domain wants its mature transactional and library ecosystem. **GraphQL (Apollo)** for the dashboard read paths specifically — flag as a targeted, later optimization rather than a foundation.

### Data storage

**Primary database (system of record)**
- **Recommendation**: **PostgreSQL** (managed), one logical database with schema-per-module discipline, on a primary + read-replica topology.
- **Why**: The core of this system — bookings, escrow holds, the financial ledger, disputes, payouts — demands ACID transactions, strong consistency, and correctness (CAP-03, CAP-04, CAP-07, CAP-08). Money math and escrow state transitions are exactly what relational + transactions are built for. Postgres scales vertically a long way and horizontally via read replicas for the read-heavy dashboard and listing reads; it's open-source and available managed on every cloud (supports the cloud-agnostic constraint).
- **Alternatives**: **MySQL/MariaDB** — equivalent fit; prefer only if the team has deeper MySQL operational muscle. **CockroachDB / Spanner-class distributed SQL** — prefer only when single-primary write throughput genuinely becomes the ceiling at very large scale; defer until proven, as it adds cost and operational complexity now. Do **not** put the ledger in a document store — the consistency guarantees aren't worth trading away.

**Cache**
- **Recommendation**: **Redis** (managed) for hot reads, session/rate-limit counters, search-result and listing caching, and the 15-minute booking time-slot holds (CAP-03 step 6) via short-TTL keys with atomic operations.
- **Why**: Booking holds need an atomic, expiring reservation to prevent double-booking under contention — a textbook Redis use case (e.g., `SET NX` with TTL). It also absorbs the cached-popular-results path that CAP-02's edge case requires (sub-200ms popular results) and the stale-data fallback for dashboards (CAP-10 error path).
- **Alternatives**: **Valkey** — drop-in open-source fork, prefer if licensing portability is a concern. **Memcached** — only if usage stays pure key/value caching, but you lose the atomic/expiry primitives the booking hold relies on.

**Search engine**
- **Recommendation**: **OpenSearch** (or Elasticsearch) as a dedicated search cluster powering CAP-02, fed asynchronously from listing-change events.
- **Why**: CAP-02 needs full-text relevance scoring, fuzzy matching/spell-correction, faceted filters (category, price range, rating, availability), geo-proximity filtering, and sub-200ms popular results — none of which Postgres does well at marketplace scale. Keeping search in a separate engine means discovery load never contends with transactional writes, and the index can be rebuilt/reshaped independently. OpenSearch is Apache-2.0 and managed on every major cloud (cloud-agnostic).
- **Alternatives**: **Typesense / Meilisearch** — prefer at MVP for far simpler operations and great typo-tolerance out of the box; revisit if relevance tuning, geo, and aggregation needs outgrow them. **Postgres full-text + `pg_trgm` + PostGIS** — viable *only* at launch volume to defer running a search cluster; explicitly a bridge, not the millions-of-users answer. This is a research flag (below).

**Object / blob storage**
- **Recommendation**: **S3-compatible object storage** (the existing cloud file storage system named in the breakdown), with browser uploads via pre-signed URLs and a CDN in front for delivery.
- **Why**: Listing images (up to 10 per listing, CAP-01), message attachments (CAP-05), and dispute evidence (CAP-07) are large binaries that don't belong in the database. Pre-signed direct-to-storage uploads keep the API tier out of the bytes path; a CDN serves images globally for discovery performance. S3-compatible APIs keep this portable across clouds and MinIO on-prem.
- **Alternatives**: Cloud-native equivalents (GCS/Azure Blob) — fine, but standardize on the S3 API to stay portable.

**Analytics store**
- **Recommendation**: **Defer a dedicated warehouse at launch**; serve CAP-10 dashboards from Postgres read replicas with pre-aggregated summary tables/materialized views updated from events. Introduce a **columnar warehouse (ClickHouse, or BigQuery/Snowflake-class)** when analytical query volume or history depth strains the replicas.
- **Why**: CAP-10's dashboards are bounded, per-user aggregations (earnings, bookings, ratings over time windows) that replicas + rollups handle well early. Standing up a warehouse before there's data to justify it is over-engineering; but the seam (events already flowing on the backbone) means adding one later is additive, not a rewrite. **ClickHouse** is the opinionated pick when the time comes for its cost/performance on append-heavy analytical data, and it's open-source/portable.

### Async / messaging

**Needed** — the dependency map (CAP-09 fans in from eight capabilities; CAP-04/07/08 trigger downstream money and notification flows) makes async eventing core, not optional.

- **Recommendation**: **A managed event/stream backbone — Apache Kafka (or a Kafka-compatible managed service)** as the durable event log for domain events, plus a lightweight job runner (**BullMQ on Redis**) for in-process background jobs (email rendering, report generation, retries) at launch.
- **Why**: Domain events — `BookingConfirmed`, `PaymentCaptured`, `FundsReleased`, `DisputeOpened`, `ReviewPublished`, `ListingPublished` — need durable, replayable, ordered delivery to multiple independent consumers (notifications CAP-09, search indexing CAP-02, analytics rollups CAP-10, payout batching CAP-08). A log-based backbone gives ordering per key (e.g., per booking/per provider ledger), replay for rebuilding the search index or analytics, and clean fan-out. This is also the mechanism that lets modules be extracted into services later without changing producers. The Redis-backed job runner covers the simpler "do this work off the request path" cases cheaply.
- **Alternatives**: **RabbitMQ / cloud queues (SQS+SNS, Pub/Sub)** — prefer at MVP if you don't need replay/ordering and want lower operational overhead; you give up the event-log replay that makes index/analytics rebuilds easy. **NATS JetStream** — prefer for a lighter-weight log with good ordering if Kafka's footprint is unwelcome. Right-size honestly: it is defensible to **launch on a managed cloud queue and adopt Kafka when replay/fan-out volume demands it** — flagged for research below.

### Authentication & authorization
- **Recommendation**: **Integrate the existing user account & authentication system** (named in the breakdown) as the identity provider via **OIDC/OAuth2**; the app tier consumes signed tokens (JWT access tokens, rotating refresh tokens in secure HTTP-only cookies). **Authorization** lives in the app tier as **role- + relationship-based access control**: roles (client, provider, mediator/admin) plus relationship checks (you may message/dispute only on bookings you are a party to).
- **Why**: Authentication is explicitly an existing system — reuse it, don't rebuild (the skill's "how not what" discipline). Authorization, however, is domain-specific and not provided externally: CAP-05 (messaging permission requires an active/pending booking relationship), CAP-07 (only booking parties open disputes; mediators have elevated rights), and CAP-06 (self-dealing prevention) are all *relationship* checks the platform must own. Centralize these as a policy/guard layer in NestJS so every module enforces them consistently.
- **Alternatives**: If the existing system is weak, a managed IdP (**Keycloak** self-hosted for portability, or **Auth0/Cognito** managed) — but the breakdown says identity already exists, so treat replacement as out of scope and flag it back rather than assume it.

### Infrastructure & hosting
- **Recommendation**: **Containers (Docker) on Kubernetes** (managed: EKS/GKE/AKS — pick one cloud at launch, stay portable), with the stateless app tier behind a load balancer and autoscaled horizontally; managed services for Postgres, Redis, OpenSearch, and the event backbone; CDN for media and static assets.
- **Why**: Cloud-agnostic + millions-of-users growth points to containers on Kubernetes as the portable, horizontally-scalable substrate — the same artifacts run on any cloud or on-prem. Managed data services avoid the operational burden of running stateful systems yourself while staying on open engines. The stateless app tier scales out trivially; search, cache, and the event backbone scale independently — which is the whole point of the seams.
- **Alternatives**: **PaaS (Fly.io / Render / cloud App Platform)** — strongly prefer *at MVP* to avoid Kubernetes overhead for 1,000 txns/month; the container-first design means the K8s migration is mostly packaging, not rewriting. **Serverless functions** — good for spiky, stateless edges (image processing on upload, scheduled report jobs), but a poor fit for the long-lived real-time messaging connections and the always-warm transactional core, so use it selectively, not as the foundation.

### CI/CD & developer tooling
- **Recommendation**: **Trunk-based development with GitHub Actions (or GitLab CI)**; pipeline runs lint → typecheck → unit/integration tests → build container → deploy to staging → promote to prod. **Infrastructure as Code via Terraform** (cloud-agnostic, matches the portability constraint). Database migrations versioned and run in-pipeline (Prisma Migrate / Flyway). Environments: dev → staging → prod, with ephemeral preview environments per pull request if budget allows.
- **Why**: A modular monolith deploys as one or few artifacts, so CI/CD stays simple — a major operational saving over microservices. Terraform keeps infra reproducible and not welded to one cloud. Migration discipline is non-negotiable given the financial schema (ledger, escrow) where ad-hoc schema drift would be dangerous.
- **Alternatives**: **Pulumi** — prefer if the team would rather express infra in TypeScript (one language, again); slightly smaller ecosystem than Terraform. **GitOps (Argo CD)** — adopt once on Kubernetes for declarative deploys.

### Observability
- **Recommendation**: **OpenTelemetry** for traces/metrics/logs instrumentation (vendor-neutral, cloud-agnostic), exported to a backend you can self-host or buy: **Prometheus + Grafana** (metrics/dashboards), **Loki** or an ELK/OpenSearch stack (logs), **Tempo/Jaeger** (tracing). Structured logging everywhere; correlation IDs propagated from the API through events to async consumers.
- **Why**: Money flows and async fan-out are the hardest things to debug — a payment captured but escrow not recorded (CAP-04 error path), a payout that silently failed (CAP-08), a notification that never fired (CAP-09). Distributed tracing across the API → event backbone → consumers is what makes those diagnosable. OpenTelemetry keeps you portable so the observability vendor isn't a lock-in. Add **alerting** on financial invariants: escrow-vs-ledger balance mismatches, dead-letter queue depth, payout failure rate, search index lag.
- **Alternatives**: **Datadog / Grafana Cloud / Honeycomb** — prefer managed if the team would rather not run the observability stack; OTel instrumentation means you can switch backends without re-instrumenting.

### Third-party services & integrations
- **Payment gateway (existing system)** — implements card capture, charging, escrow-style holds, transfers, and payouts for CAP-04 and CAP-08. A gateway with marketplace/split-payment and connected-account support (Stripe Connect-class, or Adyen/Braintree) is what keeps the platform out of direct PCI scope and provides the payout rails. The platform's own ledger records the truth; the gateway moves the money.
- **Email delivery (existing system)** — renders and sends transactional email for CAP-09 (and scheduled reports from CAP-10).
- **Object storage / CDN (existing system)** — listing/message/dispute media (CAP-01, CAP-05, CAP-07).
- **Push notifications** — a provider (web push via the Push API; FCM/APNs when native apps arrive) for CAP-09 push channel.
- **Content moderation** — CAP-05 (prohibited content / contact-info leakage) and CAP-06 (review content moderation) need text scanning. Start with rules/heuristics in-app; a managed moderation/classification API or model is the scale path — flagged for research.

### Security
- **Secrets management**: a dedicated secrets store (**HashiCorp Vault** for portability, or the chosen cloud's secrets manager) — gateway API keys, DB credentials, signing keys. No secrets in code or images.
- **PCI scope minimization**: card data never touches the platform — use the gateway's hosted fields/tokenization so the platform stays at the lightest PCI posture (SAQ A). The platform stores only tokens and references.
- **Encryption**: TLS everywhere in transit; encryption at rest on Postgres, Redis, object storage, and backups (managed-service defaults plus enforced policy). Field-level encryption for the most sensitive PII (payout bank details) above the gateway tokenization.
- **GDPR controls**: data-subject export and erasure flows (messaging, reviews, profile, financial records subject to legal-retention exceptions); regional data residency achievable via per-region Postgres/storage if required.
- **Application security**: input validation at the API boundary, output encoding, rate limiting (Redis-backed) on auth, search, and booking endpoints; idempotency keys on all money-moving operations (payment, refund, payout) to make retries safe; signed webhooks from the payment gateway with replay protection.
- **Authorization enforcement**: the relationship/role policy layer (above) applied uniformly; mediator/admin actions (CAP-07) audit-logged.

## Capability → Tech Mapping

| Capability | Implemented by | Notes |
|-----------|----------------|-------|
| CAP-01 Listing creation & management | NestJS listing module + Postgres (listing records) + S3 pre-signed uploads + CDN; emits `ListingPublished` to Kafka | Media direct-to-object-storage; publish event drives async search indexing (no synchronous coupling to search). |
| CAP-02 Search & discovery | OpenSearch cluster fed from listing events; Redis-cached popular results; PostGIS/geo in the index | Separate engine so discovery load never hits the transactional DB; cached popular results satisfy the sub-200ms edge case; fuzzy matching = OpenSearch typo tolerance. |
| CAP-03 Booking flow | NestJS booking module + Postgres (booking records, ACID) + Redis (atomic 15-min slot holds, TTL) | Slot hold = Redis `SET NX` + TTL prevents double-booking; race condition on confirm resolved by the DB transaction; emits `BookingConfirmed`. |
| CAP-04 Payment & escrow | NestJS payments module + payment gateway (charge/hold) + Postgres double-entry ledger + Kafka (`PaymentCaptured`, `FundsReleased`) | Ledger is system of record for escrow/fees; gateway moves money; idempotency keys + reconciliation job handle the "charged but not recorded" error path. |
| CAP-05 Messaging | NestJS messaging module + Postgres (threads/messages) + real-time channel (WebSocket gateway) + S3 (attachments) + moderation scan | Relationship-based send permission enforced in policy layer; real-time delivery to active sessions, else notification event to CAP-09; 30-day post-completion read-only window is a status flag. |
| CAP-06 Review system | NestJS reviews module + Postgres (reviews, rating aggregates) + moderation hold; emits `ReviewPublished` | Simultaneous-disclosure logic in module; rating recalculation in transaction; self-dealing prevented via identity/relationship check; anomaly flags surface to moderation. |
| CAP-07 Dispute resolution | NestJS disputes module + Postgres (dispute records, escrow hold flag) + evidence from messaging/ledger/object storage + mediator admin UI | Opening a dispute sets an escrow-hold flag the payments/payout modules must honor; SLA auto-escalation via scheduled job; outcome writes refund/release entries to the ledger. |
| CAP-08 Provider payout | NestJS payouts module + Postgres ledger + payment gateway transfers + Kafka consumer (batching) + scheduled jobs | Consumes `FundsReleased`; respects schedule/threshold config; batches transfers to cut fees; idempotent transfers; failed-payout retries + provider notifications. |
| CAP-09 Notification system | NestJS notifications module as Kafka consumer (fan-in) + Postgres (in-app inbox) + email service + web push + real-time channel | Subscribes to all domain events; per-event preference lookup; dedup + digest batching; critical notifications (payment/dispute) bypass opt-out per the breakdown's rule. |
| CAP-10 Dashboard & analytics | NestJS dashboards module + Postgres read replicas + pre-aggregated rollup tables (event-driven) + CSV/PDF export jobs + scheduled email reports via CAP-09 | Replicas + rollups at launch; ClickHouse warehouse is the documented scale path; stale-data fallback served from cache; export/report generation runs as background jobs. |

## Key Architecture Decisions

### AD-01: Modular monolith with pre-carved seams, not microservices (yet)
- **Decision**: Build a single deployable modular monolith (NestJS modules) with strict internal boundaries and an event backbone, designed so search, payments/ledger, messaging, and notifications can be extracted into services later.
- **Context**: Designing for millions of users but launching at ~1,000 txns/month with a small competent team; the domain has clear fault lines.
- **Rationale**: Microservices now would impose distributed-systems tax (network failures, distributed transactions across money flows, deployment complexity) that the launch volume can't justify and that would slow the team. A modular monolith keeps money flows in-process and transactional while the event boundaries pre-pay the cost of later extraction. Lowest-regret given the scale ramp.
- **Tradeoffs**: Requires discipline to keep module boundaries honest (no reaching across modules' tables); a sloppy team turns this into a big ball of mud. Mitigated by enforced module structure, schema-per-module, and events as the cross-module contract.

### AD-02: Postgres as system of record with a double-entry ledger for money
- **Decision**: All transactional state in PostgreSQL; model escrow, fees, refunds, and payouts as an append-only double-entry ledger.
- **Context**: CAP-04/07/08 demand auditability, reconciliation, and correctness across escrow holds, disputes, and payouts; the breakdown explicitly mentions reconciliation and accounting records.
- **Rationale**: ACID transactions and relational integrity are exactly suited to money state machines. A double-entry ledger makes every balance derivable and reconcilable against the gateway, and turns the "charged but not recorded" failure mode into a detectable, repairable invariant rather than silent loss.
- **Tradeoffs**: Single-primary write ceiling exists far out; deferred to distributed SQL only when proven necessary. Ledger discipline adds modeling effort up front, paid back in audit/dispute confidence.

### AD-03: Dedicated search engine (OpenSearch) fed asynchronously from events
- **Decision**: Run search in a separate engine, kept eventually consistent via `ListingPublished`/update events, rather than querying Postgres for discovery.
- **Context**: CAP-02 needs relevance ranking, fuzzy matching, faceted + geo filters, and sub-200ms popular results, under read-heavy marketplace traffic.
- **Rationale**: Postgres full-text can't meet relevance/geo/facet needs at scale, and discovery traffic would contend with transactional writes. A separate engine isolates that load and can be reshaped/rebuilt independently (replay from the event log).
- **Tradeoffs**: Eventual consistency — a just-published listing may take seconds to appear in search; acceptable for discovery and explicitly anticipated by CAP-01's async indexing step. Adds a stateful system to operate (use managed).

### AD-04: Event backbone (Kafka-class) as the async + future-extraction spine
- **Decision**: A durable, replayable event log carries domain events to async consumers (notifications, indexing, analytics, payout batching).
- **Context**: CAP-09 fans in from eight capabilities; money/notification flows must not block user-facing requests; search and analytics need to be (re)buildable.
- **Rationale**: Log-based eventing gives ordering per key, replay (rebuild the index/rollups), and clean multi-consumer fan-out, and is the mechanism that makes later service extraction non-breaking. Right-sizing note: a simpler managed queue is an acceptable MVP substitute if replay isn't yet needed (see research flag).
- **Tradeoffs**: Operational weight and a learning curve; eventual-consistency reasoning required in consumers. Mitigated by managed Kafka and idempotent, repl-safe consumers.

### AD-05: Cloud-agnostic, container-first infrastructure on open engines
- **Decision**: Docker + Kubernetes (managed) with Terraform, on open-source data/search/event engines available managed on any cloud; PaaS acceptable at MVP.
- **Context**: Explicit cloud-agnostic constraint plus growth to millions.
- **Rationale**: Containers + open engines + Terraform keep the platform portable and horizontally scalable without welding it to one provider's proprietary services. PaaS at launch avoids K8s overhead while the container artifacts make the eventual migration low-risk.
- **Tradeoffs**: Managing/operating open engines (even managed) is more work than going all-in on one cloud's proprietary stack; the price of portability. Kubernetes is overkill until volume grows — hence PaaS-first.

### AD-06: Reuse existing identity; own only relationship/role authorization
- **Decision**: Authenticate via the existing user/auth system over OIDC; implement marketplace-specific authorization (roles + booking-relationship checks) in the app tier.
- **Context**: Identity is an existing system; messaging/dispute/review permissions are relationship-specific and not provided externally.
- **Rationale**: Don't rebuild what exists; do own the domain authorization the platform uniquely needs (CAP-05/06/07). Centralizing it as a policy/guard layer guarantees consistent enforcement.
- **Tradeoffs**: Coupling to the existing auth system's capabilities; if it's weak (no OIDC, weak MFA), that becomes an open question (below), not an assumption to paper over.

## Risks & Tradeoffs

- **Financial correctness under concurrency and failure.** Escrow holds, dispute-driven splits, refunds, and batched payouts crossing the platform ledger and an external gateway are the highest-stakes paths. *Mitigation*: double-entry ledger as source of truth, idempotency keys on all money operations, a reconciliation job against the gateway (covers CAP-04's orphaned-transaction path), and alerting on ledger-vs-gateway and escrow-balance invariants.
- **Search/index consistency lag.** Async indexing means brief windows where a published listing isn't searchable, or a suspended one still appears. *Mitigation*: low-latency event pipeline, index-lag monitoring, and a fallback keyword path (CAP-02 error path) on a cached snapshot.
- **Modular-monolith boundary erosion.** The whole later-extraction story collapses if modules start sharing tables and calling each other's internals. *Mitigation*: schema-per-module, events as the only cross-module write contract, and architecture fitness checks (dependency linting) in CI.
- **Real-time messaging at scale.** Long-lived WebSocket connections (CAP-05) don't fit a purely stateless/serverless model and need sticky routing and connection scaling. *Mitigation*: isolate the real-time gateway as its own scalable component (an early extraction candidate); fall back to polling for in-app notifications if needed.
- **Premature distribution / over-engineering.** Standing up Kafka + Kubernetes + a warehouse on day one for 1,000 txns/month would burn the runway. *Mitigation*: explicit MVP-vs-scale split — PaaS + managed queue + replica-based analytics at launch, with the seams designed so each upgrade is additive.
- **Trust & safety / fraud.** Self-dealing, fake reviews, contact-info leakage, retaliation, and payment fraud are inherent marketplace risks the breakdown calls out. *Mitigation*: relationship checks, moderation scanning, anomaly flags — but the detection sophistication is a known gap (research flag).
- **Currency conversion.** CAP-04/08 touch multi-currency holds and payouts; FX timing and fee attribution affect ledger correctness. *Mitigation*: record FX rate and timestamp on the ledger entry; resolve the fee-attribution policy (an open question in the source breakdown) before build.

## Research Suggestions

High-stakes or uncertain choices to validate with the researcher skill before committing:

- **Async backbone: Kafka-class event log vs. managed queue at this scale ramp.** This is a consequential, hard-to-reverse infrastructure choice (it shapes consumers, ordering, and the extraction story) and the right answer depends on real replay/fan-out needs vs. operational budget. Suggested researcher query: *"Event streaming backbone selection for a transactional marketplace scaling from thousands to millions of transactions: Apache Kafka vs. managed cloud queues (SQS/SNS, Pub/Sub) vs. NATS JetStream — tradeoffs in ordering, replay, exactly-once/idempotency, operational cost, and migration path."*
- **Search technology: managed OpenSearch/Elasticsearch vs. Typesense/Meilisearch vs. Postgres FTS bridge.** Search is core to CAP-02 conversion and the relevance/geo/facet requirements are demanding; the operational cost and relevance-tuning effort differ sharply across options. Suggested researcher query: *"Search engine selection for a two-sided service marketplace requiring full-text relevance, fuzzy/typo tolerance, faceted filtering, and geo-proximity at scale: OpenSearch/Elasticsearch vs. Typesense vs. Meilisearch vs. Postgres full-text+pg_trgm+PostGIS — relevance quality, geo support, operational burden, and cost."*
- **(Secondary) Marketplace trust & safety / fraud detection tooling.** The breakdown already flags fraud patterns; the technical question is build-vs-buy for moderation and anomaly detection. Suggested researcher query: *"Build-vs-buy content moderation and fraud/anomaly detection for marketplace messaging, reviews, and payments — managed APIs vs. in-house heuristics, accuracy, latency, and cost."*

## Open Questions

- **Existing auth system capabilities** — Does the existing user/auth system speak OIDC/OAuth2 and support MFA, refresh-token rotation, and the client/provider/mediator roles? If not, an IdP introduction (Keycloak/managed) becomes in-scope. (Technical; needs confirmation from the platform owners.)
- **Payment gateway feature set** — Does the existing/chosen gateway support marketplace split payments, connected-account payouts, and escrow-style holds (Stripe Connect-class)? The escrow/payout design depends on it; if not, more ledger/treasury logic moves in-house.
- **Real-time delivery expectations** — Is true real-time messaging (WebSockets) required for MVP, or is near-real-time (short polling) acceptable until volume justifies the real-time gateway?
- **Data residency** — Are there regional data-residency requirements (GDPR/locale) that force per-region Postgres/storage from the start, or is a single region acceptable at launch?
- **Functional items deferred to solution-architect** (flagged, not invented here): the escrow release window, cancellation-policy model, currency-fee attribution, and the automated-vs-manual dispute threshold are all open in the source breakdown and affect the money/ledger design — resolve there before build.

## Next Steps

1. Stand up the modular-monolith skeleton (NestJS modules + Postgres + Terraform) on a PaaS target, with CI running typecheck/test/migrate and module-boundary linting from day one.
2. Spike the money core: double-entry ledger schema + payment-gateway integration (charge → escrow hold → release → payout) with idempotency keys and a reconciliation job; validate against the gateway's sandbox.
3. Spike search: index listings from `ListingPublished` events into OpenSearch (or Typesense for the MVP comparison) and validate relevance, fuzzy matching, facets, and geo against realistic listing data; measure the sub-200ms cached-popular path.
4. Prove the event backbone choice with the AD-04 research flag, then implement the notification fan-in (CAP-09) as the first event consumer end-to-end.
5. Confirm the two key integration assumptions with platform owners — existing auth (OIDC/roles/MFA) and gateway (split payments/connected payouts) — and revise the architecture if either gap exists.
6. Hand this document to the librarian skill to persist as a spec artifact.

---
*Technical architecture produced by technical-architect skill. Use the librarian skill to persist this artifact.*
