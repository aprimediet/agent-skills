# Subscription Billing System — Technical Architecture

> Technical Architect | Depth: standard | Generated: 2026-06-10

## Source Breakdown

This architecture builds on a solution-architect capability breakdown provided inline in the prompt (the librarian skill was not available to retrieve a stored artifact). It covers six capabilities: plan selection (CAP-01), payment processing (CAP-02), subscription lifecycle (CAP-03), billing cycle (CAP-04), invoice generation (CAP-05), and payment retry/dunning (CAP-06). Every technical choice below is anchored to one or more of these — no new functional capabilities are introduced.

- **Subscription Billing System (CAP-01..CAP-06)** — provided inline by the caller; defines plan selection, payment processing, subscription lifecycle, recurring billing cycle, invoice generation, and payment retry/dunning for a SaaS subscription product.

> Note: the librarian skill was unavailable, so this was produced from the inline breakdown rather than a retrieved spec. An agent with librarian access should retrieve the authoritative breakdown under `specs` matching "subscription billing capabilities" to keep the capability mapping in sync, and persist this architecture document.

## Constraints & Assumptions

- **Scale & load**: A few thousand customers in year one **[stated]**. This is modest: billing throughput is dominated by a single recurring batch run over a few thousand active subscriptions, not by request concurrency. Designing with headroom for tens of thousands of subscriptions is prudent; designing for millions would be over-engineering for a 4-person team **[assumed]**.
- **Team**: 4 people, comfortable with TypeScript **[stated]**. This strongly favors a single-language, end-to-end TypeScript stack so all four can own the whole system without context-switching, and favors managed services over self-operated infrastructure **[assumed]**.
- **Hosting**: No hosting preference stated **[assumed]**. Recommending a managed container PaaS plus managed Postgres rather than self-managed Kubernetes — a 4-person team should not run its own cluster control plane at this scale **[assumed]**.
- **Hard constraints**: Payments must go through a gateway/provider; no raw card data (PAN/CVV) is ever stored — PCI scope minimization to SAQ A **[stated]**. Customer billing data is PII, so GDPR-grade access control and deletion are assumed **[assumed]**.
- **Existing systems**: None named in the prompt **[stated/absent]**. Unlike a larger breakdown, this one does not reference an existing identity provider, email service, or ERP, so this architecture provisions authentication, transactional email, and (optionally) accounting export as part of its own scope, and flags them as open questions if such systems already exist **[assumed]**.

## Architecture Overview

- **Style**: **Modular monolith** — one deployable TypeScript service with strong internal module boundaries (one module per capability), plus two additional process types from the same codebase: a **scheduler** (cron) for the recurring billing run and a **worker** (queue consumer) for retries, webhooks, PDF rendering, and email. Rationale: at a few thousand customers, a 4-person team gets far more leverage from one codebase, one deploy, and in-process transactions across billing records than from the operational tax of microservices. Module boundaries leave clean seams to extract services later if scale ever demands it.
- **Shape**: A web frontend (plan selection + customer billing portal) calls a REST API in the monolith. The API contains six modules mirroring CAP-01..CAP-06, all backed by one PostgreSQL database so subscription state, transactions, and invoices stay transactionally consistent. Two things run outside the request path: (1) a **scheduler** that fires the recurring billing cycle (CAP-04) and due payment retries (CAP-06), and (2) a **queue + worker** that handles asynchronous work — payment-gateway webhooks, retry attempts, invoice PDF generation, and email dispatch — so user-facing flows never block on gateway latency or PDF rendering. The payment gateway (Stripe) is the only place card data ever lives; the system stores provider tokens and references, never card numbers.

## Tech Stack

### Frontend
- **Recommendation**: **Next.js (App Router) with React and TypeScript**, using the gateway's embedded payment components (**Stripe Elements / Payment Element**) for all card capture. Plan catalog, checkout, and the billing portal (payment-method updates, invoice history) are standard pages; sensitive card input is delegated entirely to the provider's iframe.
- **Why**: CAP-01 (plan selection) and the billing portal (payment-method update tied to CAP-06, invoice viewing tied to CAP-05) are conventional CRUD-style screens — Next.js is the mainstream TypeScript choice the team already knows. Crucially, capturing cards via Stripe Elements means card data is entered directly into the provider's iframe and never touches our frontend or backend, holding PCI scope at SAQ A (the stated hard constraint).
- **Alternatives**: Vite + React SPA — prefer if you don't want a Node SSR tier and are happy serving a static bundle against the API. Remix — comparable to Next; prefer if the team favors its nested data-loading model.

### Backend / API
- **Recommendation**: **Node.js + TypeScript with NestJS**, exposing a REST/JSON API, with one module per capability (`PlanSelection`, `Payments`, `Subscriptions`, `BillingCycle`, `Invoicing`, `Retry`). Use **Prisma** as the typed data-access layer.
- **Why**: NestJS gives the modular-monolith structure for free — its module system enforces the CAP-01..CAP-06 boundaries and its dependency injection keeps the seams clean for later extraction. TypeScript end-to-end matches the team's strength. REST is sufficient: the API surface is small and resource-oriented (plans, subscriptions, invoices, payment methods, webhooks).
- **Alternatives**: Express or Fastify with a hand-rolled module layout — prefer if NestJS feels too opinionated and you want a minimal framework. tRPC — prefer if frontend and backend live in one repo and you want end-to-end type safety without a REST contract; less ideal if external consumers (e.g. an accounting system) need conventional HTTP.

### Data storage
- **Primary database — Recommendation**: **PostgreSQL** (managed), via Prisma. Core tables: `plans`, `subscriptions`, `transactions`, `invoices`, `retry_schedules`, `webhook_events`, plus an `audit_log`.
- **Why**: Billing is inherently relational and money-critical. CAP-02 must record a transaction and signal CAP-03 to activate a subscription atomically; CAP-04 must extend a billing period and write an invoice consistently; CAP-05 needs gapless sequential invoice numbers. Postgres provides ACID transactions, unique constraints (idempotency keys for CAP-02 deduplication), sequences (invoice numbering for CAP-05), and `SELECT ... FOR UPDATE` row locking to serialize per-subscription billing safely (CAP-04). A single primary instance is ample at this scale.
  - **Alternatives**: MySQL — equivalent fit; prefer only if the team or host standardizes on it. DynamoDB — avoid here; access patterns are relational and need multi-row transactions and sequences, which fight a key-value store.
- **Object storage — Recommendation**: **S3-compatible blob store** for generated invoice PDFs (CAP-05), served to the billing portal via short-lived signed URLs.
- **Why**: Invoices are immutable artifacts that must be retrievable later. Store invoice metadata in Postgres and the rendered PDF in object storage; keep large binaries out of the relational DB.
  - **Alternatives**: Postgres `bytea` — acceptable at very low volume; switch to object storage as invoice count grows.
- **Cache / search / analytics — Not needed at this scale.** Plan catalogs and subscription lookups are tiny and fully served by Postgres with indexes; there is no search or analytics requirement in the breakdown. Add Redis caching only if the plan-catalog read path (CAP-01) ever becomes hot, which a few thousand users will not cause.

### Async / messaging
- **Recommendation**: A **durable job/queue system** — **BullMQ (Redis-backed)** if managed Redis is convenient on the chosen host, otherwise **pg-boss (Postgres-backed)** to avoid adding infrastructure — plus a **cron scheduler** (the host's scheduled job, or a leader-elected in-process cron) to trigger the recurring billing run.
- **Why**: Several capabilities are explicitly asynchronous and must not block user requests:
  - CAP-04 (billing cycle) is a scheduled batch — the scheduler enqueues one billing job per due subscription.
  - CAP-02 webhook reconciliation (delayed/asynchronous gateway confirmation) consumes webhooks off a queue.
  - CAP-06 (payment retry/dunning) schedules future retry attempts over days — durable delayed jobs are exactly this.
  - CAP-05 invoice PDF rendering and all email dispatch run as jobs so the request path stays fast.
  Queue jobs provide retry-with-backoff, idempotency, and durability for free. A streaming platform (Kafka) is unjustified at this scale.
- **Alternatives**: pg-boss — prefer when you want zero new infrastructure (reuses Postgres) and throughput is low, which it is here. Cloud-native SQS + EventBridge — prefer if you commit to AWS and want fully managed primitives.

### Authentication & authorization
- **Recommendation**: **A managed auth provider for customer identity** — **Clerk or Auth0** (or Supabase Auth) issuing JWTs the billing API validates — combined with a small in-app **role check** for the admin-only actions in the breakdown (e.g. immediate cancellation in CAP-03, manual retry trigger in CAP-06). Internal scheduler/worker → API calls use a separate service credential, not a user token.
- **Why**: Unlike a breakdown that names an existing identity system, this one does not, so identity must be provisioned. A managed provider lets a 4-person team avoid building and securing password storage, MFA, and session management themselves — high-risk work that is not the product. The billing service only needs to trust verified tokens, map them to a customer record, and gate the two privileged operations.
- **Alternatives**: Self-hosted Keycloak — prefer only if data-residency or licensing rules out SaaS auth; it adds an operational burden this team should avoid. If an existing user/identity system actually exists (see Open Questions), delegate to it and skip the managed provider entirely.

### Infrastructure & hosting
- **Recommendation**: **Managed container PaaS** (Render, Railway, Fly.io, or AWS App Runner / ECS Fargate) running three process types from one codebase image: the **web/API service**, the **worker** (queue consumer), and the **scheduler** (cron). **Managed Postgres** (RDS / Neon / the PaaS's own) and **managed Redis** if BullMQ is chosen. One staging environment plus one production environment.
- **Why**: A 4-person team should spend its time on billing correctness, not on operating Kubernetes. A managed PaaS gives push-to-deploy, managed TLS, and managed datastores with automated backups. Three process types (api/worker/scheduler) cleanly separate the request path, async work, and the recurring batch while sharing one image and codebase — the modular-monolith deployment model.
- **Alternatives**: AWS ECS Fargate + RDS + ElastiCache + EventBridge — prefer if the org is already an AWS shop. Kubernetes (EKS/GKE) — avoid at this team size and scale; the operational overhead isn't justified.

### CI/CD & developer tooling
- **Recommendation**: **GitHub Actions** pipeline — lint (ESLint) + typecheck (`tsc`) + unit/integration tests (Vitest, with Postgres in a service container) on every PR; build a single Docker image; auto-deploy to staging on merge to `main`; promote to production on a tagged release or manual approval. **Prisma Migrate** runs schema migrations as a controlled release step. Infrastructure as config-as-code (`render.yaml` / Terraform if on AWS).
- **Why**: Billing logic is money-touching and must be heavily tested — idempotent charges (CAP-02), double-billing prevention and catch-up (CAP-04), proration on plan changes (CAP-03), gapless invoice numbering (CAP-05), and retry counting (CAP-06) are exactly the paths an integration suite must gate on every deploy. Migrations as a controlled release step prevent schema drift against live billing tables.
- **Alternatives**: GitLab CI / CircleCI — equivalent; pick whatever hosts the repo. Manual deploys — unacceptable for a money system; automate from day one.

### Observability
- **Recommendation**: **Structured JSON logging** (pino) shipped to a managed log platform; **error tracking** via Sentry; **metrics + alerting** via the host's monitoring or a low-tier managed APM (Grafana Cloud / Datadog); **distributed tracing optional** via OpenTelemetry if latency becomes an issue.
- **Why**: The highest-stakes failures here are silent: the recurring billing run (CAP-04) not firing, charges silently failing, or retries (CAP-06) not running on schedule. Concretely, alert on: billing-job success/failure counts and last-successful-run timestamp, payment decline rate (CAP-02), webhook processing lag, and queue depth/age. Sentry catches exceptions in proration and invoice generation. This is the minimum needed to trust an autonomous money system.
- **Alternatives**: Full Datadog/New Relic suite — prefer once scale or team grows; overkill now. Logs-only with no metrics — insufficient, because the batch and retry schedulers need active "did it run?" alerting.

### Third-party services & integrations
- **Recommendation**:
  - **Payment gateway: Stripe** — for CAP-02 (charges via PaymentIntents with idempotency keys), stored payment methods as tokens (recurring charges in CAP-02/CAP-04), and webhooks for asynchronous confirmation. **[Flagged for research — see Research Suggestions.]** Stripe Billing's native subscription/dunning features may also offload parts of CAP-03/CAP-04/CAP-06 — evaluate build-vs-buy.
  - **Transactional email: a managed provider** (Postmark, Resend, or SendGrid) — for CAP-05 invoice delivery and CAP-06 dunning/failure/recovery notifications.
  - **Invoice PDF rendering**: a server-side HTML-to-PDF renderer (headless-Chromium or a templating + PDF library) run inside the worker (CAP-05).
  - **Accounting export (optional)**: push invoice/transaction records to an accounting system if one exists — flagged as an open question since none was named.
- **Why**: A gateway with tokenization and Elements keeps raw card data out of the system entirely (PCI SAQ A), satisfying the hard constraint. Stripe natively provides idempotency keys (CAP-02 duplicate-charge defense), stored-method tokens (recurring CAP-04 charges), and signed webhooks (CAP-02 delayed-confirmation), mapping directly onto the breakdown. Email must be provisioned since no existing service was named.
- **Alternatives**: Braintree / Adyen as the gateway — prefer Adyen for broad international/multi-currency coverage, Braintree if PayPal is a required method. This is a high-stakes, hard-to-reverse choice — see Research Suggestions.

### Security
- **Recommendation**: PCI scope minimization via gateway tokenization (no PAN/CVV ever stored or logged). **Secrets** (gateway API keys, DB creds, webhook signing secrets) in the host's secret manager / injected env, never in the repo. **TLS everywhere** (managed certs). **Encryption at rest** on Postgres and the blob store (managed-provider default). **Verify webhook signatures** from the gateway before acting on events. **Idempotency keys** on all charge requests (CAP-02). **Audit log** of privileged actions — admin immediate-cancel (CAP-03) and manual retry (CAP-06). Treat customer PII (name, email, billing address) as GDPR-relevant: access-controlled and deletable.
- **Why**: This is a money-and-PII system; the threat model is fraudulent charges, leaked card/PII data, and unauthorized admin actions. Tokenization removes the largest risk class (card data) entirely. Webhook signature verification prevents forged "payment succeeded" events. Idempotency keys are the breakdown's own defense against double-charging. Audit logging makes admin overrides traceable.
- **Alternatives**: Storing cards yourself behind your own vault — explicitly rejected; it pulls you into PCI SAQ D, unjustifiable for this team and scale.

## Capability → Tech Mapping

| Capability | Implemented by | Notes |
|-----------|----------------|-------|
| CAP-01 Plan selection | Next.js plan/checkout pages → NestJS `PlanSelection` module → Postgres `plans`/`subscriptions` | Reads plan catalog from Postgres; records selection + action type; routes new/upgrade purchases to CAP-02, downgrades to a scheduled change. |
| CAP-02 Payment processing | NestJS `Payments` module → Stripe PaymentIntents + tokens → Postgres `transactions`; webhooks via queue/worker | Idempotency keys for dedupe; stored tokens for recurring charges; webhook consumer handles delayed confirmation; failures enqueue CAP-06. Card capture via Stripe Elements (SAQ A). |
| CAP-03 Subscription lifecycle | NestJS `Subscriptions` module → Postgres `subscriptions` (transactional state machine) | Activate/upgrade/downgrade/cancel/reactivate/expire as state transitions; proration computed in-module and charged via CAP-02; emits invoice + notification events. Admin immediate-cancel is role-gated + audited. |
| CAP-04 Billing cycle | Scheduler (cron) → enqueues per-subscription billing jobs → worker → `Payments`/`Subscriptions` | Recurring run queries due subscriptions; `FOR UPDATE` + last-billing-date guard prevents double-billing; missed-run catch-up is inherent (queries all past-due). Successful renewals extend the period and trigger CAP-05. |
| CAP-05 Invoice generation | NestJS `Invoicing` module → Postgres invoice metadata + sequence → worker renders PDF → blob store → email provider | Gapless invoice numbers via Postgres sequence; PDF rendered async; credit notes for refunds; delivered via the transactional email provider; optional accounting export. |
| CAP-06 Payment retry/dunning | NestJS `Retry` module → delayed queue jobs (BullMQ/pg-boss) → `Payments` → email notifications | Durable delayed jobs implement the retry schedule; retry count in `retry_schedules`; payment-method update resets + immediate retry; exhaustion signals CAP-03 to suspend. Manual admin retry is role-gated + audited. |

## Key Architecture Decisions

### AD-01: Modular monolith over microservices

- **Decision**: Build CAP-01..CAP-06 as modules in one TypeScript service (with separate worker and scheduler processes from the same codebase), not as independent services.
- **Context**: 4-person team, a few thousand customers, six tightly-coupled capabilities that share data and need cross-capability transactions (charge + activate, renew + invoice).
- **Rationale**: One deploy and one database let four people move fast and keep billing state transactionally consistent. Microservices would impose network boundaries, distributed transactions, and operational overhead with no scale justification. NestJS modules preserve clean seams for later extraction.
- **Tradeoffs**: All capabilities scale and deploy together; a bug in one module can affect the whole service. Acceptable at this scale, mitigated by strong module boundaries and tests.

### AD-02: Payment gateway with tokenization; never store card data

- **Decision**: Use Stripe with Elements for capture and tokens for recurring charges; store only tokens and transaction references.
- **Context**: Hard constraint that payments use a provider and no raw card data is stored; CAP-02 needs recurring charges, idempotency, and async confirmation.
- **Rationale**: Keeps PCI scope at SAQ A, removes the single largest security liability, and the gateway natively provides the idempotency keys, stored methods, and webhooks the breakdown's edge cases require.
- **Tradeoffs**: Vendor lock-in to the gateway's API and fee structure; flows like proration and dunning are split between our code and the provider's features. Isolate gateway calls behind one `Payments` adapter to ease a future swap.

### AD-03: Postgres as the single transactional store

- **Decision**: One managed Postgres instance holds plans, subscriptions, transactions, invoices, and retry schedules.
- **Context**: Billing is relational and money-critical: atomic charge-and-activate, gapless invoice numbers, double-billing prevention.
- **Rationale**: ACID transactions, unique/idempotency constraints, sequences, and row locking directly implement the breakdown's correctness requirements. Scale is small enough that a single primary suffices.
- **Tradeoffs**: A single primary is an eventual scaling/availability ceiling; mitigated by managed backups/failover and the fact that this scale is far from the limit.

### AD-04: Scheduler + durable queue for batch and retries

- **Decision**: A cron scheduler triggers the recurring billing run and due retries; a durable queue (BullMQ or pg-boss) runs charges, webhook handling, PDF rendering, and email off the request path.
- **Context**: CAP-04 is a recurring batch, CAP-06 needs delayed retries over days, and several CAP-02/CAP-05 steps must not block users.
- **Rationale**: Durable delayed jobs with retry/backoff and idempotency are the natural fit; missed runs self-heal by querying all past-due work. Avoids a heavyweight streaming platform.
- **Tradeoffs**: Adds a Redis dependency if BullMQ is chosen (pg-boss avoids it but shares the DB); requires care to keep jobs idempotent so a retried job never double-charges.

### AD-05: Managed auth provider for customer identity

- **Decision**: Use a managed auth provider (Clerk/Auth0/Supabase Auth) for customer identity and sessions, with in-app role checks for admin actions.
- **Context**: No existing identity system was named in the breakdown, yet the billing portal and admin actions require authenticated, authorized users.
- **Rationale**: A 4-person team should not build and secure password storage, MFA, and session management — high-risk, non-differentiating work. A managed provider issues verifiable tokens the API simply validates.
- **Tradeoffs**: Another vendor dependency and per-MAU cost; if an existing identity system turns out to exist, this is redundant and should be replaced by delegation (see Open Questions).

## Risks & Tradeoffs

- **Double-charging is the worst failure.** Mitigation: gateway idempotency keys per charge, a last-billing-date guard plus `SELECT ... FOR UPDATE` in CAP-04, and idempotent queue jobs. Test this path hardest.
- **The recurring billing job silently not running** would stall all revenue. Mitigation: alert on last-successful-run timestamp and job success counts; the catch-up query design means a missed run recovers automatically on the next run.
- **Proration correctness (CAP-03)** is subtle and money-visible; getting it wrong erodes trust. Mitigation: dedicated integration tests; the strategy itself is flagged for research below.
- **Single Postgres primary** is an availability/scaling ceiling. Acceptable now; revisit read replicas and connection pooling well before tens of thousands of active subscriptions.
- **Gateway lock-in.** Switching providers later is costly because tokens and webhook semantics are provider-specific. Accepted as a deliberate tradeoff for PCI scope reduction; isolate gateway calls behind a single adapter.
- **Build-vs-buy on subscription logic.** Stripe Billing can natively handle parts of CAP-03/CAP-04/CAP-06; building it ourselves gives control but adds money-critical code to maintain. Decide deliberately rather than by default.

## Research Suggestions

High-stakes or uncertain choices to validate with the researcher skill (the researcher skill was not available in this session):

- **Payment gateway selection** — Stripe is the recommended default, but the choice is hard to reverse (tokens, webhooks, and fees are provider-specific) and depends on regional availability, payout terms, and roadmap. Suggested researcher query: "Stripe vs Braintree vs Adyen for a SaaS recurring-billing system — tokenization, recurring-charge and dunning features, idempotency, webhook reliability, fees, and international/multi-currency support for a small team."
- **Build vs buy subscription/dunning logic** — Whether to use Stripe Billing's native subscriptions and Smart Retries or build CAP-03/CAP-04/CAP-06 in-house. Suggested researcher query: "Stripe Billing native subscriptions and dunning vs building subscription lifecycle, recurring billing, and retry logic in-house for a small SaaS — control, maintenance burden, and feature coverage."
- **Proration strategy for mid-cycle changes** — How to compute and present prorated charges/credits on upgrade and downgrade. Suggested researcher query: "Best practices for prorating subscription charges and credits on mid-cycle SaaS plan upgrades and downgrades, and how leading billing platforms implement it."
- **Payment retry / dunning schedule** — Optimal retry intervals and max attempts to maximize recovery without excess gateway cost. Suggested researcher query: "Optimal payment retry intervals, maximum attempts, and dunning email sequencing for SaaS subscription recovery."
- **Queue technology: BullMQ (Redis) vs pg-boss (Postgres)** — Whether the extra Redis dependency is worth it at this scale. Suggested researcher query: "BullMQ vs pg-boss for delayed/scheduled jobs in a small Node.js billing service — durability, delayed-job support, operational overhead, and throughput limits."

## Open Questions

- Does an existing user/identity system exist that the billing service should delegate to, or should it provision its own auth (AD-05 assumes the latter)?
- Is there an existing transactional email service to integrate with for CAP-05/CAP-06, or should one be provisioned?
- Is there an accounting/ERP system that invoice and transaction records (CAP-05) must be reconciled against, and via what contract (real-time API or batch export)?
- Is a managed Redis readily available on the chosen host (favoring BullMQ), or should the system stay Postgres-only with pg-boss?
- Are there data-residency requirements for customer PII that constrain the hosting region?
- *Functional* questions — minimum subscription period, proration-credit policy, billing frequency, multiple subscriptions per customer, currencies — belong to the source breakdown and should be resolved with solution-architect, not here.

## Next Steps

1. Resolve the existing-systems open questions (identity, email, accounting) — they determine whether AD-05 and the email/export integrations stand or are replaced by delegation.
2. Stand up the repo skeleton: NestJS modules for CAP-01..CAP-06, a Prisma schema for the core tables, and the three process types (api/worker/scheduler) deployable to the chosen PaaS.
3. Spike the Stripe integration end-to-end in test mode: PaymentIntent with idempotency key, stored-token recurring charge, and signed webhook handling (de-risks CAP-02 and AD-02).
4. Build the integration test harness against a real Postgres for the money-critical paths: idempotent charge, recurring-billing catch-up + double-billing guard, proration, and retry counting.
5. Wire observability for the billing job (last-run + success/failure alerts) before the first real charge.
6. Run the research queries above (gateway choice, build-vs-buy, proration, retry schedule, queue tech) before locking those decisions.

---
*Technical architecture produced by technical-architect skill. Use the librarian skill to persist this artifact.*
