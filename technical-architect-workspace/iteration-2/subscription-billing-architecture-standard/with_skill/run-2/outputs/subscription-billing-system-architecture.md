# Subscription Billing System — Technical Architecture

> Technical Architect | Depth: standard | Generated: 2026-06-10

## Source Breakdown

This architecture builds on a capability breakdown provided **inline by the caller** — the librarian skill was not available to retrieve a stored spec. It covers six capabilities: plan selection (CAP-01), payment processing (CAP-02), subscription lifecycle (CAP-03), billing cycle (CAP-04), invoice generation (CAP-05), and payment retry/dunning (CAP-06).

- Subscription Billing System (inline) — solution-architect capability breakdown defining CAP-01 through CAP-06 for a SaaS subscription billing system.

> Note: the librarian skill was unavailable, so this architecture was produced from the capability list given in the prompt rather than retrieved. An agent with librarian access should retrieve the authoritative source breakdown under `specs` matching "subscription billing capabilities" / "SaaS billing CAP-01 CAP-06" to confirm the mapping below stays faithful to the functional design. No capabilities were invented here — everything anchors to CAP-01..CAP-06 as stated.

## Constraints & Assumptions

- **Scale & load**: A few thousand customers in year one **[stated]**. This is modest. Billing throughput is dominated by one recurring batch run over a few thousand active subscriptions, not by request concurrency — even at 5,000 subscriptions a daily run is a few thousand charges spread over minutes, not a high-QPS workload. Designing for tens of thousands of subscriptions is sensible headroom; designing for millions would be over-engineering for this team **[assumed]**.
- **Team**: 4-person team comfortable with TypeScript **[stated]**. This strongly favors a single-language, end-to-end TypeScript stack so four people can own the whole system without context-switching between runtimes **[assumed]**.
- **Hosting**: No hosting preference stated **[assumed]**. A 4-person team should not run its own Kubernetes control plane for a few thousand customers, so the recommendation assumes a **managed container PaaS plus managed Postgres** rather than self-managed infrastructure.
- **Hard constraints**: Payments go through a **third-party gateway; no raw card data (PAN/CVV) is ever stored**, minimizing PCI scope **[stated]**. Customer billing data is PII, so GDPR-grade handling (access control, deletability) is assumed even though no specific regulation was named **[assumed]**. No budget, data-residency, or must-use-cloud constraint was stated **[assumed none]**.
- **Existing systems**: None were stated **[assumed]**. The prompt does not name an existing auth system, email service, or accounting/ERP, so this design provides those layers itself and flags them as open questions in case they already exist and should be integrated instead.

## Architecture Overview

- **Style**: **Modular monolith** — a single deployable TypeScript service with strong internal module boundaries (one module per capability), plus a separate **scheduled worker** for the recurring billing run and a **queue-backed worker** for retries, webhooks, PDF rendering, and email. Rationale: at a few thousand customers a 4-person team gets far more leverage from one codebase, one deploy, and in-process transactions across billing records than from the operational tax of microservices. The module boundaries leave a clean seam to extract a service later if scale ever demands it.
- **Shape**: A web frontend (plan selection + billing portal) calls a REST API in the monolith. The API holds six modules mirroring CAP-01..CAP-06, all sharing one Postgres database so subscription state, transactions, and invoices stay transactionally consistent. Two things run outside the request path: (1) a **scheduler** that fires the recurring billing cycle (CAP-04) and due retries (CAP-06), and (2) a **queue + worker** that processes asynchronous work — payment-gateway webhooks (CAP-02), retry attempts (CAP-06), invoice PDF rendering (CAP-05), and email dispatch — so user-facing flows never block on gateway latency or PDF rendering. The payment gateway is the only place card data lives; the system stores provider tokens and transaction references, never card numbers.

## Tech Stack

### Frontend
- **Recommendation**: **React + TypeScript via Next.js (App Router)**, using the gateway's hosted/embedded payment elements (e.g. Stripe Elements) for any card-detail capture. Plan catalog, checkout, and billing portal (invoice viewing, payment-method update) rendered as standard pages; card input delegated entirely to the provider's iframe-based components.
- **Why**: CAP-01 (plan selection) and the billing portal (CAP-05 invoice viewing, CAP-06 payment-method update) are conventional CRUD-style screens — React/Next is the mainstream TypeScript choice the team already knows. Using provider Elements means card data is captured directly by the gateway's iframe and never touches our frontend or backend, keeping PCI scope at the lowest tier (SAQ A) — directly serving the no-card-storage constraint.
- **Alternatives**: Vite + React SPA — prefer if you don't want an SSR/Node rendering tier and are happy serving a static bundle against the API. Remix — comparable to Next; prefer if the team favors its data-loading model.

### Backend / API
- **Recommendation**: **Node.js + TypeScript with NestJS**, exposing a REST/JSON API, one module per capability (`PlanSelection`, `Payments`, `Subscriptions`, `BillingCycle`, `Invoicing`, `Retry`). Typed data access via **Prisma**.
- **Why**: NestJS gives the modular-monolith structure for free — its module system enforces the CAP-01..CAP-06 boundaries and its dependency injection keeps seams clean for later extraction. TypeScript end-to-end matches the team. REST is sufficient: the API surface is small and resource-oriented (plans, subscriptions, invoices, payment methods).
- **Alternatives**: Express/Fastify with a hand-rolled module layout — prefer if the team finds NestJS too opinionated and wants a minimal framework. tRPC — prefer if frontend and backend share one repo and you want end-to-end type safety without a REST contract; less ideal if external consumers (e.g. an accounting system) ever need a conventional HTTP API.

### Data storage
- **Primary database — Recommendation**: **PostgreSQL** (managed), accessed via Prisma. Core tables: `plans`, `subscriptions`, `transactions`, `invoices`, `retry_schedules`, `webhook_events`.
- **Why**: Billing is inherently relational and transactional — CAP-02 must record a transaction and signal CAP-03 to activate a subscription atomically; CAP-04 must extend a period and write an invoice consistently; CAP-05 needs gapless sequential invoice numbers. Postgres gives ACID transactions, strong constraints (unique idempotency keys for CAP-02 dedupe, sequences for invoice numbers in CAP-05), and `SELECT ... FOR UPDATE` to serialize per-subscription billing safely. At this scale a single primary instance is ample.
  - **Alternatives**: MySQL — equivalent fit; prefer only if the team or host standardizes on it. DynamoDB — avoid here; the access patterns are relational and need multi-row transactions and sequences, which fight a key-value store.
- **Object storage — Recommendation**: **S3-compatible blob store** for generated invoice PDFs (CAP-05), served via signed URLs.
- **Why**: Invoice documents are immutable artifacts retrievable from the billing portal; the DB holds invoice metadata, the blob store holds the rendered PDF. Keeps large binaries out of Postgres.
  - **Alternatives**: Store PDFs in Postgres as `bytea` — acceptable at very low volume; prefer object storage as invoice count grows.
- **Cache / search / analytics**: **Not needed at this scale.** Plan catalogs and subscription lookups are tiny and fully served by Postgres with indexes; there is no search requirement and no analytics workload in the breakdown. Add a Redis cache only if the plan-catalog read path (CAP-01) ever becomes hot — a few thousand users will not cause that. (If BullMQ is chosen for queuing, Redis will already be present and can double as a cache later.)

### Async / messaging
- **Recommendation**: A **durable job/queue system** — **BullMQ (Redis)** if a managed Redis is easy on the chosen host, otherwise **pg-boss (Postgres-backed)** to avoid adding infrastructure. Plus a **cron-style scheduler** (the host's scheduled job, or a leader-elected in-process cron) to trigger the recurring billing run.
- **Why**: Several capabilities are explicitly asynchronous and must not block user requests:
  - CAP-04 (billing cycle) is a recurring scheduled batch — the scheduler enqueues one billing task per due subscription.
  - CAP-02 webhook reconciliation (gateway "payment confirmed" callbacks, including delayed confirmations) consumes webhooks off a queue.
  - CAP-06 (payment retry / dunning) schedules future retry attempts as **durable delayed jobs** — exactly what dunning needs.
  - CAP-05 invoice PDF rendering and all email dispatch run as jobs so the request path stays fast.
  Queue jobs give retry-with-backoff, idempotency, and durability for free. A full event-streaming platform (Kafka) is unjustified at this scale.
- **Alternatives**: pg-boss — prefer when you want zero new infrastructure (reuses Postgres) and throughput is low, which it is here. Cloud-native queue (SQS) + scheduler (EventBridge) — prefer if you commit to AWS and want fully managed primitives.

### Authentication & authorization
- **Recommendation**: If an existing user-account system is present, **delegate end-user identity to it** (validate its session/JWT, map to a customer record). If none exists, use a **managed auth provider (Clerk or Auth0)** rather than rolling your own. Add **role-based checks** for the admin-only actions implied by CAP-03 (e.g. immediate cancellation/refund) and CAP-06 (manual retry). Internal service-to-service calls (scheduler/worker → API) use a separate service credential.
- **Why**: No auth system was stated, but standing up custom auth for a money system is unnecessary risk for a 4-person team. A managed provider gives secure session handling, MFA, and password reset out of the box, leaving the team to focus on billing correctness. Billing itself only needs to (a) trust a verified identity and (b) gate the few privileged operations.
- **Alternatives**: Self-hosted Keycloak — prefer only with a hard data-residency or no-third-party-IdP constraint; adds an identity tier to operate. Hand-rolled email/password auth — avoid for a billing system.

### Infrastructure & hosting
- **Recommendation**: **Managed container PaaS** (Render, Railway, Fly.io, or AWS App Runner / ECS Fargate) running three process types from one codebase: the **web/API service**, the **worker** (queue consumer), and the **scheduler** (cron). **Managed Postgres** (RDS / Neon / the PaaS's Postgres) and **managed Redis** if BullMQ is chosen. One staging environment + one production environment.
- **Why**: A 4-person team should spend its time on billing correctness, not on operating Kubernetes. A managed PaaS gives push-to-deploy, managed TLS, and managed datastores with automated backups. Three process types (api/worker/scheduler) cleanly separate the request path, async work, and the recurring batch while sharing one image and codebase — the modular-monolith deployment model.
- **Alternatives**: AWS ECS Fargate + RDS + ElastiCache + EventBridge — prefer if the org is already an AWS shop and wants everything in one cloud account. Kubernetes (EKS/GKE) — avoid at this team size and scale; the operational overhead isn't justified.

### CI/CD & developer tooling
- **Recommendation**: **GitHub Actions** pipeline — lint (ESLint) + typecheck (`tsc`) + unit/integration tests (Vitest or Jest, with Postgres in a service container) on every PR; build a single Docker image; deploy to staging on merge to main, promote to production on a tagged release or manual approval. **Prisma Migrate** for schema migrations run as a controlled release step. Infrastructure as config-as-code (e.g. `render.yaml`) or Terraform if on AWS.
- **Why**: Billing logic must be heavily tested — proration (CAP-03), grace periods and double-billing prevention (CAP-04), idempotent charges (CAP-02), and retry counting (CAP-06) are exactly the money-touching logic that needs an integration suite gating every deploy. Migrations as a controlled release step prevent schema drift against live billing tables.
- **Alternatives**: GitLab CI / CircleCI — equivalent; pick whatever hosts the repo. Manual deploys — unacceptable for a money system; automate from day one.

### Observability
- **Recommendation**: **Structured JSON logging** (pino) shipped to a managed log platform; **error tracking** via Sentry; **metrics + alerting** via the host's built-in monitoring or a cheap managed tier (Grafana Cloud / Datadog). **Distributed tracing optional** via OpenTelemetry if request latency becomes an issue later.
- **Why**: The highest-stakes failure modes here are silent: the recurring billing run (CAP-04) not firing, charges silently failing, or retries (CAP-06) not running on schedule. Concretely, alert on: billing-job success/failure counts and last-successful-run timestamp, payment decline rate (CAP-02), webhook processing lag, and queue depth/age. Sentry catches exceptions in proration and invoice generation. This is the minimum needed to trust an autonomous money system.
- **Alternatives**: Full Datadog/New Relic suite — prefer once scale or team grows; overkill now. Logs-only with no metrics — insufficient, because the batch and retry schedulers need active "did it run?" alerting.

### Third-party services & integrations
- **Recommendation**:
  - **Payment gateway: Stripe** — for CAP-02 (charges via PaymentIntents with idempotency keys), stored payment methods as tokens (recurring charges in CAP-02/CAP-04), and webhooks for asynchronous confirmation. **[Flagged for research — see Research Suggestions.]**
  - **Email: a transactional email provider** (Postmark, Resend, or SES) — for CAP-05 invoice delivery and CAP-06 dunning/recovery notifications. If an internal email service already exists, integrate with it instead.
  - **Invoice PDF rendering**: a server-side HTML-to-PDF library (a headless-Chromium renderer, or a templating + PDF lib) run inside the worker (CAP-05).
- **Why**: Using a gateway with tokenization and Elements keeps raw card data out of the system entirely (PCI SAQ A), satisfying the hard constraint. Stripe natively provides idempotency keys (CAP-02 duplicate-charge defense), stored-method tokens (recurring CAP-04 charges), and signed webhooks (CAP-02 delayed-confirmation handling) — all of which map directly onto the capability list. A dedicated transactional email provider is more reliable for invoice/dunning delivery than self-hosted SMTP.
- **Alternatives**: Braintree / Adyen as the gateway — prefer Adyen if you later need broad international/multi-currency coverage, Braintree if PayPal is a required method. Note: gateway choice is high-stakes and hard to reverse — see Research Suggestions.

### Security
- **Recommendation**: PCI scope minimization via gateway tokenization (no PAN/CVV ever stored or logged). **Secrets** (gateway API keys, DB creds, webhook signing secrets) in the host's secret manager / injected env, never in the repo. **TLS everywhere** (managed certs). **Encryption at rest** on Postgres and the blob store (managed-provider default). **Verify webhook signatures** from the gateway before acting on them. **Idempotency keys** on all charge requests (CAP-02). **Audit log** of privileged actions — admin cancel/refund (CAP-03) and manual retry (CAP-06). Treat PII (name, email, billing address) as GDPR-relevant: access-controlled and deletable.
- **Why**: This is a money-and-PII system; the threat model is fraudulent charges, leaked card/PII data, and unauthorized admin actions. Tokenization removes the largest risk class (card data) entirely. Webhook signature verification prevents forged "payment succeeded" events. Idempotency keys are the primary defense against double-charging. Audit logging makes admin overrides traceable.
- **Alternatives**: Building your own card vault — explicitly rejected; it pulls you into PCI SAQ D and is unjustifiable for this team and scale.

## Capability → Tech Mapping

| Capability | Implemented by | Notes |
|-----------|----------------|-------|
| CAP-01 Plan selection | Next.js plan/checkout pages → NestJS `PlanSelection` module → Postgres `plans`/`subscriptions` | Reads plan catalog from Postgres; records selection; routes paid signups to CAP-02 and state changes to CAP-03. |
| CAP-02 Payment processing | NestJS `Payments` module → Stripe PaymentIntents + tokens → Postgres `transactions`; webhooks via queue/worker | Idempotency keys for dedupe; stored tokens for recurring charges; webhook consumer handles async/delayed confirmation; failures enqueue CAP-06. |
| CAP-03 Subscription lifecycle | NestJS `Subscriptions` module → Postgres `subscriptions` (transactional state machine) | Activate / upgrade / downgrade / cancel / reactivate / expire as state transitions; proration computed in-module and charged via CAP-02; emits invoice + notification events. Admin cancel/refund role-gated + audited. |
| CAP-04 Billing cycle | Scheduler (cron) → enqueues per-subscription billing jobs → worker → `Payments`/`Subscriptions` | Recurring run queries due subscriptions; `FOR UPDATE` + last-billing-date guard prevents double-billing; missed-run catch-up is inherent (queries all past-due). Successful renewals extend the period and trigger CAP-05. |
| CAP-05 Invoice generation | NestJS `Invoicing` module → Postgres invoice metadata + sequence → worker renders PDF → blob store → email provider | Gapless invoice numbers via a Postgres sequence; PDF rendered asynchronously; credit notes for refunds; delivered via the transactional email provider. |
| CAP-06 Payment retry / dunning | NestJS `Retry` module → delayed queue jobs (BullMQ/pg-boss) → `Payments` → email notifications | Durable delayed jobs implement the retry schedule; retry count tracked in `retry_schedules`; payment-method update resets + triggers immediate retry; exhaustion signals CAP-03 to suspend. Manual admin retry role-gated + audited. |

## Key Architecture Decisions

### AD-01: Modular monolith over microservices

- **Decision**: Build CAP-01..CAP-06 as modules in one TypeScript service (with separate worker and scheduler processes from the same codebase), not as independent services.
- **Context**: 4-person team, a few thousand customers, six tightly-coupled capabilities that share data and need cross-capability transactions (charge + activate, renew + invoice).
- **Rationale**: One deploy and one database let four people move fast and keep billing state transactionally consistent. Microservices would impose network boundaries, distributed transactions, and operational overhead with no scale justification. NestJS modules preserve clean seams for later extraction.
- **Tradeoffs**: All capabilities scale and deploy together; a bug in one module can affect the whole service. Acceptable at this scale and mitigated by strong module boundaries and tests.

### AD-02: Payment gateway with tokenization; never store card data

- **Decision**: Use a gateway (Stripe) with Elements for capture and tokens for recurring charges; store only tokens and transaction references.
- **Context**: Hard constraint that payments use a provider and no raw card data is stored; CAP-02 needs recurring charges, idempotency, and async confirmation.
- **Rationale**: Keeps PCI scope at SAQ A, removes the single largest security liability, and the gateway natively provides the idempotency keys, stored methods, and webhooks that CAP-02 and CAP-06 require.
- **Tradeoffs**: Vendor lock-in to the gateway's API and fee structure; some flows (proration math, dunning logic) are split between our code and the provider's features. Mitigate by isolating gateway calls behind a single `Payments` adapter.

### AD-03: Postgres as the single transactional store

- **Decision**: One managed Postgres instance holds plans, subscriptions, transactions, invoices, and retry schedules.
- **Context**: Billing is relational and money-critical: atomic charge-and-activate, gapless invoice numbers, double-billing prevention.
- **Rationale**: ACID transactions, unique/idempotency constraints, sequences, and row locking directly implement the correctness requirements. Scale is small enough that a single primary suffices.
- **Tradeoffs**: A single primary is eventually a scaling/availability ceiling; mitigated by managed backups/failover and the fact that this scale is far from the limit. Revisit read replicas / pooling well before tens of thousands of active subscriptions.

### AD-04: Scheduler + durable queue for batch and retries

- **Decision**: A cron scheduler triggers the recurring billing run and due retries; a durable queue (BullMQ or pg-boss) runs charges, webhook handling, PDF rendering, and email off the request path.
- **Context**: CAP-04 is a recurring batch, CAP-06 needs delayed retries over days, and several CAP-02/CAP-05 steps must not block users.
- **Rationale**: Durable delayed jobs with retry/backoff and idempotency are the natural fit; missed runs self-heal by querying all past-due work. Avoids a heavyweight streaming platform.
- **Tradeoffs**: Adds a Redis dependency if BullMQ is chosen (pg-boss avoids it but shares the DB); requires care to make jobs idempotent so a retried job never double-charges.

## Risks & Tradeoffs

- **Double-charging is the worst failure.** Mitigation: gateway idempotency keys per charge, a last-billing-date guard plus `SELECT ... FOR UPDATE` in CAP-04, and idempotent queue jobs. Test this path hardest.
- **The recurring billing job silently not running** would stall all revenue. Mitigation: alert on last-successful-run timestamp and job success counts; the catch-up query design means a missed run recovers automatically on the next pass.
- **Proration correctness (CAP-03)** is subtle and money-visible; getting it wrong erodes trust. Mitigation: dedicated integration tests; the strategy itself is flagged for research below.
- **Single Postgres primary** is an availability/scaling ceiling. Acceptable now; revisit read replicas / connection pooling before tens of thousands of active subscriptions.
- **Gateway lock-in.** Switching providers later is costly because tokens and webhook semantics are provider-specific. Accepted as a deliberate tradeoff for PCI scope reduction; isolate gateway calls behind a single `Payments` adapter to ease a future swap.
- **Dunning recovery vs. churn.** Retry cadence and dunning emails (CAP-06) directly affect involuntary churn and gateway fees; a poorly tuned schedule loses revenue or annoys customers. Flagged for research below.
- **Auth assumption risk.** This design assumes no existing identity system and recommends a managed provider. If an internal user system already exists, integrate with it instead of adding a redundant tier (see Open Questions).

## Research Suggestions

High-stakes or uncertain choices to validate with the researcher skill (the researcher skill was not available in this session):

- **Payment gateway selection** — Stripe is the recommended default, but the choice is hard to reverse (tokens, webhooks, and fees are provider-specific) and depends on regional availability, payout terms, and roadmap (e.g. future multi-currency). Suggested researcher query: "Stripe vs Braintree vs Adyen for a SaaS recurring-billing system — tokenization, recurring-charge and dunning features, idempotency, webhook reliability, fees, and international/multi-currency roadmap for a small team."
- **Proration strategy for mid-cycle changes** — How to compute and present prorated charges/credits on upgrade and downgrade. Suggested researcher query: "Best practices for prorating subscription charges and credits on mid-cycle SaaS plan upgrades and downgrades, and how leading billing platforms implement it."
- **Payment retry / dunning schedule (CAP-06)** — Optimal retry intervals, max attempts, and dunning email sequencing to maximize recovery without excess gateway cost or churn. Suggested researcher query: "Optimal payment retry intervals, maximum attempts, and dunning email sequencing for SaaS subscription recovery."
- **Queue technology: BullMQ (Redis) vs pg-boss (Postgres)** — Whether the extra Redis dependency is worth it at this scale, or whether reusing Postgres is sufficient. Suggested researcher query: "BullMQ vs pg-boss for delayed/scheduled jobs in a small Node.js billing service — durability, delayed-job support, operational overhead, and throughput limits."

## Open Questions

- Is there an existing user-account / identity system to integrate with (favoring token delegation), or should we stand up a managed auth provider as recommended? (Drives the auth section.)
- Is there an existing internal email service for invoice/dunning delivery, or should we adopt a transactional email provider? (Affects CAP-05/CAP-06 integration.)
- Is an accounting/ERP system in play that needs invoice/transaction reconciliation feeds (real-time API or batch export)? (Would add a CAP-05 reconciliation integration.)
- Is a managed Redis readily available on the chosen host (favoring BullMQ), or should we stay Postgres-only with pg-boss?
- Are there data-residency requirements for customer PII that constrain the hosting region?
- These are *technical* open questions. Functional questions — billing cadence (monthly/annual), currency support, proration-credit policy, minimum subscription term, multiple subscriptions per customer — belong to the source breakdown and should be resolved with the solution-architect skill, not here.

## Next Steps

1. Confirm the surrounding-systems questions (auth, email, ERP) — they decide whether to integrate or build those layers (resolves the highest-impact open questions).
2. Stand up the repo skeleton: NestJS modules for CAP-01..CAP-06, Prisma schema for the core tables, and the three process types (api/worker/scheduler) deployable to the chosen PaaS.
3. Spike the Stripe integration end-to-end in test mode: PaymentIntent with idempotency key, stored-token recurring charge, and signed webhook handling (de-risks CAP-02 and AD-02).
4. Build the integration test harness against a real Postgres for the money-critical paths: idempotent charge, billing catch-up + double-billing guard, proration, and retry counting.
5. Wire observability for the billing job (last-run + success/failure alerts) before the first real charge.
6. Run the four research queries above (gateway choice, proration, dunning schedule, queue tech) before locking those decisions.

---
*Technical architecture produced by technical-architect skill. Use the librarian skill to persist this artifact.*
