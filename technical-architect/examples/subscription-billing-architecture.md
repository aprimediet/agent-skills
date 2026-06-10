# Subscription Billing System — Technical Architecture

> Technical Architect | Depth: standard | Generated: 2026-06-10

## Source Breakdown

This architecture builds on a capability breakdown provided inline (the librarian skill was not available to retrieve it). It covers six capabilities: plan selection, payment processing, subscription lifecycle, the recurring billing cycle, invoice generation, and payment retry.

- [Subscription Billing System](./subscription-billing.md) — Solution-architect breakdown defining CAP-01 through CAP-06 for recurring SaaS billing, with a flat tax rate, monthly cycle, and existing user/email/payment-gateway/ERP systems.

> Note: the librarian skill was unavailable, so this architecture was produced from the breakdown pasted by the caller rather than retrieved. An agent with librarian access should retrieve the source breakdown under `specs` matching "subscription billing capabilities" to keep the mapping authoritative.

## Constraints & Assumptions

- **Scale & load**: A few thousand customers in year one **[stated]**. This is modest — billing throughput is dominated by one daily batch run over a few thousand active subscriptions, not by request concurrency. Designing for tens of thousands is prudent headroom; designing for millions would be over-engineering **[assumed]**.
- **Team**: 4-person team comfortable with TypeScript **[stated]**. Favors a single-language stack (TypeScript end-to-end) to minimize context-switching and let four people own the whole system **[assumed]**.
- **Hosting**: No hosting preference stated. Assume a managed PaaS with a managed Postgres rather than self-managed Kubernetes — a 4-person team should not be running its own control plane for a few thousand customers **[assumed]**.
- **Hard constraints**: Payments must go through a gateway/provider; no raw card data stored (PCI scope minimization) **[stated]**. Flat tax rate, monthly billing only, single currency, per the breakdown's out-of-scope list **[stated]**. GDPR-grade handling of customer PII is assumed since this is customer billing data **[assumed]**.
- **Existing systems**: User account management system, email notification service, a payment gateway, and an accounting/ERP system for reconciliation **[stated]**. This architecture integrates with these rather than replacing them.

## Architecture Overview

- **Style**: **Modular monolith** — a single deployable TypeScript service with strong internal module boundaries (one module per capability), plus a separate scheduled worker process for the daily billing cycle and a queue-backed worker for retries and webhooks. Rationale: at a few thousand customers a 4-person team gets far more leverage from one codebase, one deploy, and in-process transactions across billing records than from the operational tax of microservices. The module boundaries leave a clean seam to extract services later if scale demands it.
- **Shape**: A web frontend (billing portal + plan selection) talks to an API in the monolith. The API holds six modules mirroring CAP-01..CAP-06, all sharing one Postgres database so subscription state, transactions, and invoices stay transactionally consistent. Two things run outside the request path: (1) a **scheduler** that fires the daily billing cycle (CAP-04) and due retries (CAP-06), and (2) a **queue + worker** that processes asynchronous work — payment-gateway webhooks, retry attempts, invoice PDF generation, and email dispatch — so user-facing flows never block on gateway latency or PDF rendering. The payment gateway (Stripe) is the only place card data lives; the system stores tokens, never PANs.

## Tech Stack

### Frontend
- **Recommendation**: React with TypeScript via **Next.js (App Router)**, using the gateway's hosted/embedded payment elements (Stripe Elements) for the card form. Plan catalog and billing portal rendered as standard pages; sensitive card input delegated entirely to the provider's iframe-based components.
- **Why**: CAP-01 (plan selection) and the billing portal (payment-method update in CAP-06, invoice viewing in CAP-05) are conventional CRUD-style screens — React/Next is the mainstream TypeScript choice the team will know. Critically, using Stripe Elements means card data is captured directly by the provider's iframe and never touches our frontend or backend, keeping PCI scope at SAQ A.
- **Alternatives**: Plain Vite + React SPA — prefer if you don't want SSR or a Node rendering tier and are happy serving a static bundle against the API. Remix — comparable to Next; prefer if the team already favors its data-loading model.

### Backend / API
- **Recommendation**: **Node.js + TypeScript with NestJS**, exposing a REST/JSON API. One NestJS module per capability (PlanSelection, Payments, Subscriptions, BillingCycle, Invoicing, Retry). Use a typed data layer (Prisma) for Postgres access.
- **Why**: NestJS gives the modular-monolith structure for free — its module system enforces the capability boundaries (CAP-01..CAP-06) and its dependency injection keeps the seams clean for later extraction. TypeScript end-to-end matches the team. REST is sufficient; the API surface is small and mostly resource-oriented (plans, subscriptions, invoices, payment methods).
- **Alternatives**: Express/Fastify with a hand-rolled module layout — prefer if the team finds NestJS too opinionated and wants minimal framework. tRPC — prefer if the frontend and backend stay in one repo and you want end-to-end type safety without a REST contract; less ideal if the ERP or other consumers need a conventional HTTP API.

### Data storage
- **Primary database — Recommendation**: **PostgreSQL** (managed), accessed via Prisma. Core tables: `plans`, `subscriptions`, `transactions`, `invoices`, `retry_schedules`, `webhook_events`.
- **Why**: Billing is inherently relational and transactional — CAP-02 must record a transaction and signal CAP-03 to activate a subscription atomically; CAP-04 must extend a period and write an invoice consistently; CAP-05 needs gapless sequential invoice numbers. Postgres gives ACID transactions, strong constraints (unique idempotency keys for CAP-02 dedupe, sequences for invoice numbers in CAP-05), and `SELECT ... FOR UPDATE` to serialize per-subscription billing safely. At this scale a single primary instance is ample.
  - **Alternatives**: MySQL — equivalent fit; prefer only if the team or host standardizes on it. DynamoDB — avoid here; the access patterns are relational and need multi-row transactions and sequences, which fight a key-value store.
- **Object storage — Recommendation**: **S3-compatible blob store** for generated invoice PDFs (CAP-05), served via signed URLs.
- **Why**: Invoice documents are immutable artifacts that must be retrievable from the billing portal; the DB stores invoice metadata, the blob store holds the rendered PDF. Keeps large binaries out of Postgres.
  - **Alternatives**: Store PDFs in Postgres as bytea — acceptable at very low volume; prefer object storage as invoice count grows.
- **Cache / search / analytics**: **Not needed at this scale.** Plan catalogs and subscription lookups are tiny and fully served by Postgres with indexes; there is no search requirement and no analytics workload in the breakdown. Reconciliation data goes to the existing ERP, not a separate warehouse. Add a Redis cache only if the plan-catalog read path (CAP-01) ever becomes hot, which a few thousand users will not cause.

### Async / messaging
- **Recommendation**: A **job/queue system backed by Postgres or Redis** — concretely **BullMQ (Redis)** if a managed Redis is easy on the chosen host, otherwise **pg-boss (Postgres-backed)** to avoid adding infrastructure. Plus a **cron-style scheduler** (the host's scheduled job, or a leader-elected in-process cron) to trigger the daily billing run.
- **Why**: Several capabilities are explicitly asynchronous and must not block user requests:
  - CAP-04 (billing cycle) is a daily scheduled batch — a scheduled job enqueues one billing task per due subscription.
  - CAP-02 webhook reconciliation ("approved but confirmation delayed" edge case) consumes gateway webhooks off a queue.
  - CAP-06 (payment retry) schedules future retry attempts (3/7/14 days) — durable delayed jobs are exactly this.
  - CAP-05 invoice PDF rendering and all email dispatch run as jobs so the request path stays fast.
  Queue jobs give retry-with-backoff, idempotency, and durability for free. A full event-streaming platform (Kafka) is unjustified at this scale.
- **Alternatives**: pg-boss — prefer when you want zero new infrastructure (reuses Postgres) and throughput is low, which it is here. Cloud-native queue (SQS) + scheduler (EventBridge) — prefer if you commit to AWS and want fully managed primitives.

### Authentication & authorization
- **Recommendation**: **Delegate end-user identity to the existing user account management system** (the breakdown names it as an existing system). The billing service validates the incoming session/JWT issued by that system and maps it to a customer record. Add a small **role check** for the admin-only actions called out in the breakdown (immediate cancellation in CAP-03, manual retry in CAP-06).
- **Why**: The breakdown's inputs for CAP-01/02/05 say user identity and customer info are "provided by the user account system" — re-implementing auth would duplicate an existing capability (and is solution-architect territory). Billing only needs to (a) trust that system's tokens and (b) enforce the two privileged operations. Internal service-to-service calls (scheduler/worker → API, or ERP integration) use a separate service credential.
- **Alternatives**: Stand up a dedicated IdP (Auth0/Clerk/Keycloak) — only if the user account system cannot issue verifiable tokens; otherwise it adds a redundant identity tier.

### Infrastructure & hosting
- **Recommendation**: **Managed container PaaS** (Render, Railway, Fly.io, or AWS App Runner / ECS Fargate) running three process types from one codebase: the **web/API service**, the **worker** (queue consumer), and the **scheduler** (cron). **Managed Postgres** (e.g. RDS / Neon / the PaaS's Postgres) and **managed Redis** if BullMQ is chosen. One staging environment + one production environment.
- **Why**: A 4-person team should spend its time on billing correctness, not on operating Kubernetes. A managed PaaS gives push-to-deploy, managed TLS, and managed datastores with backups. Three process types (api/worker/scheduler) cleanly separate the request path, async work, and the daily batch while sharing one image and codebase — the modular-monolith deployment model.
- **Alternatives**: AWS ECS Fargate + RDS + ElastiCache + EventBridge — prefer if the org is already an AWS shop and wants everything in one cloud account for the ERP/reconciliation integration. Kubernetes (EKS/GKE) — avoid at this team size and scale; the operational overhead isn't justified.

### CI/CD & developer tooling
- **Recommendation**: **GitHub Actions** pipeline: lint (ESLint) + typecheck (`tsc`) + unit/integration tests (Vitest/Jest, with Postgres in a service container) on every PR; build a single Docker image; deploy to staging on merge to main, promote to production on a tagged release or manual approval. **Prisma Migrate** for schema migrations run as a release step. Infrastructure defined in the PaaS's config-as-code (e.g. `render.yaml`) or Terraform if on AWS.
- **Why**: Billing logic must be heavily tested — proration (CAP-03), grace periods and double-billing prevention (CAP-04), idempotent charges (CAP-02), and retry counting (CAP-06) are exactly the kind of money-touching logic that needs an integration test suite gating every deploy. Migrations as a controlled release step prevent schema drift against the live billing tables.
- **Alternatives**: GitLab CI / CircleCI — equivalent; pick whatever hosts the repo. Manual deploys — unacceptable for a money system; automate from day one.

### Observability
- **Recommendation**: **Structured JSON logging** (pino) shipped to a managed log platform; **metrics + alerting** via the host's built-in monitoring or a managed APM (Sentry for errors, plus a metrics backend such as Grafana Cloud / Datadog at the cheapest tier); **distributed tracing optional** via OpenTelemetry if request latency becomes an issue.
- **Why**: The highest-stakes failure modes are silent: the daily billing run (CAP-04) not running, charges silently failing, or retries (CAP-06) not firing on schedule. Concretely, alert on: billing-job success/failure counts and last-run timestamp, payment decline rate (CAP-02), webhook processing lag, and queue depth/age. Error tracking (Sentry) catches exceptions in proration and invoice generation. This is the minimum to trust an autonomous money system.
- **Alternatives**: Full Datadog/New Relic suite — prefer once scale or team grows; overkill now. Logs-only with no metrics — insufficient, because the batch and retry schedulers need active "did it run?" alerting.

### Third-party services & integrations
- **Recommendation**:
  - **Payment gateway: Stripe** — for CAP-02 (charges via PaymentIntents with idempotency keys), stored payment methods as tokens (recurring charges in CAP-02/CAP-04), and webhooks for asynchronous confirmation. **[Flagged for research — see Research Suggestions.]**
  - **Email: the existing email notification service** — for CAP-05 invoice delivery and CAP-06 failure/recovery notifications. Integrate, don't replace.
  - **Accounting/ERP: the existing ERP system** — push invoice and transaction records (CAP-05) for reconciliation via its API or a nightly export.
  - **Invoice PDF rendering**: a server-side HTML-to-PDF library (e.g. a headless-Chromium renderer or a templating + PDF lib) run inside the worker.
- **Why**: Using a gateway with tokenization and Elements keeps raw card data out of the system entirely (PCI SAQ A), satisfying the hard constraint. Stripe natively provides idempotency keys (CAP-02 duplicate-charge edge case), stored-method tokens (recurring CAP-04 charges), and webhooks (CAP-02 delayed-confirmation edge case), which map directly onto the breakdown. Email and ERP already exist per the breakdown, so we integrate.
- **Alternatives**: Braintree / Adyen as the gateway — prefer Adyen if you later need broad international/multi-currency coverage (out of scope now), Braintree if PayPal is a required method. Note: this is a high-stakes, hard-to-reverse choice — see Research Suggestions.

### Security
- **Recommendation**: PCI scope minimization via gateway tokenization (no PAN/CVV ever stored or logged). **Secrets** (gateway API keys, DB creds, webhook signing secrets) in the host's secret manager / env injection, never in the repo. **TLS everywhere** (managed certs). **Encryption at rest** on Postgres and the blob store (managed-provider default). **Verify webhook signatures** from the gateway before acting on them. **Idempotency keys** on all charge requests (CAP-02). **Audit log** of privileged actions — admin immediate-cancel (CAP-03) and manual retry (CAP-06). PII (name, email, billing address) treated as GDPR-relevant: access-controlled and deletable.
- **Why**: This is a money-and-PII system; the threat model is fraudulent charges, leaked card/PII data, and unauthorized admin actions. Tokenization removes the largest risk class (card data) entirely. Webhook signature verification prevents forged "payment succeeded" events. Idempotency keys are the breakdown's own defense against double-charging. Audit logging makes the admin overrides traceable.
- **Alternatives**: Storing cards yourself behind your own vault — explicitly rejected; it pulls you into PCI SAQ D and is unjustifiable for this team and scale.

## Capability → Tech Mapping

| Capability | Implemented by | Notes |
|-----------|----------------|-------|
| CAP-01 Plan selection | Next.js plan/billing pages → NestJS `PlanSelection` module → Postgres `plans`/`subscriptions` | Reads plan catalog from Postgres; records selection + action type; routes upgrades to CAP-02, downgrades to a scheduled change. Cached-catalog edge case handled in the read path. |
| CAP-02 Payment processing | NestJS `Payments` module → Stripe PaymentIntents + tokens → Postgres `transactions`; webhooks via queue/worker | Idempotency keys for dedupe; stored tokens for recurring charges; webhook consumer handles delayed confirmation; failures enqueue CAP-06. |
| CAP-03 Subscription lifecycle | NestJS `Subscriptions` module → Postgres `subscriptions` (transactional state machine) | Activate/upgrade/downgrade/cancel/reactivate/expire as state transitions; proration computed in-module and charged via CAP-02; emits invoice and notification events. Admin immediate-cancel is role-gated + audited. |
| CAP-04 Billing cycle | Scheduler (cron) → enqueues per-subscription billing jobs → worker → `Payments`/`Subscriptions` | Daily run queries due subscriptions; `FOR UPDATE` + last-billing-date check prevents double-billing; missed-day catch-up is inherent (queries all past-due). Successful renewals extend period + trigger CAP-05. |
| CAP-05 Invoice generation | NestJS `Invoicing` module → Postgres invoice metadata + sequence → worker renders PDF → blob store → existing email service + ERP | Gapless invoice numbers via Postgres sequence; PDF rendered async; credit notes for refunds; pushed to ERP for reconciliation. |
| CAP-06 Payment retry | NestJS `Retry` module → delayed queue jobs (BullMQ/pg-boss) → `Payments` → notifications | Durable delayed jobs implement 3/7/14-day schedule; retry count in `retry_schedules`; payment-method update resets + immediate retry; exhaustion signals CAP-03 suspend. Manual admin retry is role-gated + audited. |

## Key Architecture Decisions

### AD-01: Modular monolith over microservices

- **Decision**: Build CAP-01..CAP-06 as modules in one TypeScript service (with separate worker and scheduler processes from the same codebase), not as independent services.
- **Context**: 4-person team, a few thousand customers, six tightly-coupled capabilities that share data and need cross-capability transactions (charge + activate, renew + invoice).
- **Rationale**: One deploy and one database let four people move fast and keep billing state transactionally consistent. Microservices would impose network boundaries, distributed transactions, and operational overhead with no scale justification. NestJS modules preserve clean seams for later extraction.
- **Tradeoffs**: All capabilities scale and deploy together; a bug in one module can affect the whole service. Acceptable at this scale and mitigated by strong module boundaries and tests.

### AD-02: Payment gateway with tokenization; never store card data

- **Decision**: Use Stripe (gateway) with Elements for capture and tokens for recurring charges; store only tokens and transaction references.
- **Context**: Hard constraint that payments use a provider and no raw card data is stored; CAP-02 needs recurring charges, idempotency, and async confirmation.
- **Rationale**: Keeps PCI scope at SAQ A, removes the single largest security liability, and the gateway natively provides the idempotency keys, stored methods, and webhooks the breakdown's edge cases require.
- **Tradeoffs**: Vendor lock-in to the gateway's API and fee structure; some flows (proration math, dunning) are split between our code and the provider's features.

### AD-03: Postgres as the single transactional store

- **Decision**: One managed Postgres instance holds plans, subscriptions, transactions, invoices, and retry schedules.
- **Context**: Billing is relational and money-critical: atomic charge-and-activate, gapless invoice numbers, double-billing prevention.
- **Rationale**: ACID transactions, unique/idempotency constraints, sequences, and row locking directly implement the breakdown's correctness requirements. Scale is small enough that a single primary suffices.
- **Tradeoffs**: A single primary is a scaling and availability bottleneck eventually; mitigated by managed backups/failover and the fact that this scale is far from the limit.

### AD-04: Scheduler + durable queue for batch and retries

- **Decision**: A cron scheduler triggers the daily billing run and due retries; a durable queue (BullMQ or pg-boss) runs charges, webhook handling, PDF rendering, and email off the request path.
- **Context**: CAP-04 is a daily batch, CAP-06 needs delayed retries over days, and several CAP-02/CAP-05 steps must not block users.
- **Rationale**: Durable delayed jobs with retry/backoff and idempotency are the natural fit; missed runs self-heal by querying all past-due work. Avoids a heavyweight streaming platform.
- **Tradeoffs**: Adds a Redis dependency if BullMQ is chosen (pg-boss avoids it but shares the DB); requires care to make jobs idempotent so a retried job never double-charges.

## Risks & Tradeoffs

- **Double-charging is the worst failure.** Mitigation: gateway idempotency keys per charge, a last-billing-date guard plus `SELECT ... FOR UPDATE` in CAP-04, and idempotent queue jobs. Test this path hardest.
- **The daily billing job silently not running** would stall all revenue. Mitigation: alert on last-successful-run timestamp and job success counts; the catch-up query design means a missed day recovers automatically on the next run.
- **Proration correctness (CAP-03)** is subtle and money-visible; getting it wrong erodes trust. Mitigation: dedicated integration tests; the strategy itself is flagged for research (see below and the source breakdown's own open question).
- **Single Postgres primary** is an availability/scaling ceiling. Acceptable now; revisit read replicas / connection pooling well before tens of thousands of active subscriptions.
- **Gateway lock-in.** Switching providers later is costly because tokens and webhook semantics are provider-specific. Accepted as a deliberate tradeoff for PCI scope reduction; isolate gateway calls behind a single `Payments` adapter to ease a future swap.
- **Invoice numbering and refunds** touch revenue-recognition rules; getting timing or credit-note handling wrong has accounting consequences. Flagged for research below.

## Research Suggestions

High-stakes or uncertain choices to validate with the researcher skill (the researcher skill was not available in this session):

- **Payment gateway selection** — Stripe is the recommended default, but the choice is hard to reverse (tokens, webhooks, and fees are provider-specific) and depends on regional availability, payout terms, and roadmap (the breakdown lists multi-currency as future scope). Suggested researcher query: "Stripe vs Braintree vs Adyen for a SaaS recurring-billing system — tokenization, recurring-charge and dunning features, idempotency, webhook reliability, fees, and international/multi-currency roadmap for a small team."
- **Proration strategy for mid-cycle changes** — How to compute and present prorated charges/credits on upgrade and downgrade (mirrors the source breakdown's open question). Suggested researcher query: "Best practices for prorating subscription charges and credits on mid-cycle SaaS plan upgrades and downgrades, and how leading billing platforms implement it."
- **Payment retry / dunning schedule** — Optimal retry intervals and max attempts to maximize recovery without excess gateway cost. Suggested researcher query: "Optimal payment retry intervals, maximum attempts, and dunning email sequencing for SaaS subscription recovery."
- **Queue technology: BullMQ (Redis) vs pg-boss (Postgres)** — Whether the extra Redis dependency is worth it at this scale, or whether reusing Postgres is sufficient. Suggested researcher query: "BullMQ vs pg-boss for delayed/scheduled jobs in a small Node.js billing service — durability, delayed-job support, operational overhead, and throughput limits."

## Open Questions

- Does the existing user account management system issue verifiable tokens (JWT or introspectable sessions) that the billing service can trust, or will an integration shim be required? (Drives the auth approach in AD/auth section.)
- What integration contract does the ERP/accounting system expose for pushing invoices and transactions — real-time API, or batch export? (Affects CAP-05 reconciliation wiring.)
- Is a managed Redis readily available on the chosen host (favoring BullMQ), or should we stay Postgres-only with pg-boss?
- Are there data-residency requirements for customer PII that constrain the hosting region?
- These are *technical* open questions. Functional open questions (minimum subscription period, proration-credit policy, multiple subscriptions per user) belong to the source breakdown and should be resolved with solution-architect, not here.

## Next Steps

1. Confirm the auth contract with the user account system and the integration contract with the ERP (resolves the two highest-impact open questions).
2. Stand up the repo skeleton: NestJS modules for CAP-01..CAP-06, Prisma schema for the core tables, and the three process types (api/worker/scheduler) deployable to the chosen PaaS.
3. Spike the Stripe integration end-to-end on test mode: PaymentIntent with idempotency key, stored-token recurring charge, and signed webhook handling (de-risks CAP-02 and AD-02).
4. Build the integration test harness against a real Postgres for the money-critical paths: idempotent charge, daily billing catch-up + double-billing guard, proration, and retry counting.
5. Wire observability for the billing job (last-run + success/failure alerts) before the first real charge.
6. Run the four research queries above (gateway choice, proration, retry schedule, queue tech) before locking those decisions.

---
*Technical architecture produced by technical-architect skill. Use the librarian skill to persist this artifact.*
