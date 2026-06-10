# Subscription Billing System — Technical Architecture

> Technical Architect | Depth: standard | Generated: 2026-06-10

## Source Breakdown

This architecture builds on a solution-architect capability breakdown provided inline (the librarian skill was not available to retrieve it). The breakdown defines six capabilities for a SaaS subscription billing system:

- **CAP-01 Plan selection** — choosing and changing subscription plans.
- **CAP-02 Payment processing** — charging customers through a payment gateway.
- **CAP-03 Subscription lifecycle** — activating, changing, cancelling, and expiring subscriptions.
- **CAP-04 Billing cycle** — the recurring (daily-evaluated) renewal/charge run.
- **CAP-05 Invoice generation** — producing and delivering invoices.
- **CAP-06 Payment retry / dunning** — retrying failed payments and notifying customers.

> Note: the librarian skill was unavailable, so this architecture was produced from the inline breakdown rather than retrieved. An agent with librarian access should retrieve the authoritative source breakdown under the `specs` category matching "subscription billing capabilities / SaaS billing CAP-01..CAP-06" so the capability mapping below stays anchored to the canonical version. No new capabilities were invented here — every technical choice traces back to CAP-01..CAP-06.

## Constraints & Assumptions

- **Scale & load**: A few thousand customers in year one **[stated]**. Load is dominated by a periodic billing run over a few thousand active subscriptions, not by request concurrency — interactive traffic (plan selection, portal views) is light. Designing for low tens of thousands gives sensible headroom; designing for millions would be over-engineering for this team **[assumed]**.
- **Team**: 4-person team comfortable with TypeScript **[stated]**. This strongly favors a single-language, TypeScript-end-to-end stack so four people can own the whole system without context-switching between runtimes **[assumed]**.
- **Hosting**: No hosting preference stated **[assumed]**. Assume a managed container PaaS plus managed Postgres rather than self-managed Kubernetes — a 4-person team should not operate its own cluster control plane at this scale **[assumed]**.
- **Hard constraints**: Payments go through a payment gateway; no raw card data (PAN/CVV) is ever stored, keeping PCI scope minimal (SAQ A) **[stated]**. Customer billing data is PII and is assumed to need GDPR-grade handling (access control, deletion) **[assumed]**.
- **Existing systems**: None were named in the inline breakdown **[stated: absent]**. This architecture therefore includes auth and email as in-scope concerns but is designed so they can be swapped for an existing identity provider or email service if one exists — flagged as an open question.

## Architecture Overview

- **Style**: **Modular monolith** — one deployable TypeScript service with strong internal module boundaries (one module per capability), plus a queue-backed **worker** process and a **scheduler** process built from the same codebase. Rationale: with a few thousand customers and a 4-person team, one codebase, one deploy, and in-process transactions across billing records deliver far more leverage than the operational tax of microservices. Module boundaries leave clean seams to extract a service later if scale ever demands it.
- **Shape**: A web frontend (plan selection + customer billing portal) calls the monolith's HTTP API. The API contains six modules mirroring CAP-01..CAP-06, all backed by a single Postgres database so subscription state, transactions, and invoices stay transactionally consistent. Two things run outside the request path: (1) a **scheduler** that fires the recurring billing run (CAP-04) and due retries (CAP-06); and (2) a **queue + worker** that handles asynchronous work — payment-gateway webhooks, retry attempts, invoice PDF rendering, and email dispatch — so user-facing flows never block on gateway latency or PDF generation. The payment gateway is the only place card data exists; the system stores tokens and references, never card numbers.

## Tech Stack

### Frontend
- **Recommendation**: **React + TypeScript via Next.js (App Router)**, with the payment gateway's hosted/embedded card elements (e.g. Stripe Elements) for any card entry. Plan catalog and billing portal are conventional pages; sensitive card input is delegated entirely to the provider's iframe components.
- **Why**: CAP-01 (plan selection) and the billing portal (payment-method update for CAP-06, invoice viewing for CAP-05) are standard CRUD-style screens — Next.js is the mainstream TypeScript choice the team already knows. Using the gateway's Elements means card data is captured directly by the provider and never touches our frontend or backend, keeping PCI scope at SAQ A (the stated hard constraint).
- **Alternatives**: Vite + React SPA — prefer if you don't want SSR or a Node rendering tier and are happy serving a static bundle against the API. Remix — comparable to Next.js; prefer if the team favors its data-loading model.

### Backend / API
- **Recommendation**: **Node.js + TypeScript with NestJS**, exposing a REST/JSON API. One module per capability (PlanSelection, Payments, Subscriptions, BillingCycle, Invoicing, Dunning). Typed data access via **Prisma**.
- **Why**: NestJS provides the modular-monolith structure out of the box — its module system enforces the CAP-01..CAP-06 boundaries and its dependency injection keeps the seams clean for later extraction. TypeScript end-to-end matches the team's stated comfort. REST is sufficient: the API surface is small and resource-oriented (plans, subscriptions, invoices, payment methods).
- **Alternatives**: Fastify/Express with a hand-rolled module layout — prefer if the team finds NestJS too opinionated and wants a thinner framework. tRPC — prefer if frontend and backend live in one repo and you want end-to-end type safety without a REST contract; less ideal if external consumers ever need a conventional HTTP API.

### Data storage
- **Primary database — Recommendation**: **PostgreSQL** (managed), accessed via Prisma. Core tables: `plans`, `subscriptions`, `transactions`, `invoices`, `retry_schedules`, `webhook_events`.
- **Why**: Billing is inherently relational and transactional. CAP-02 must record a transaction and signal CAP-03 to activate a subscription atomically; CAP-04 must extend a period and write an invoice consistently; CAP-05 needs gapless sequential invoice numbers. Postgres gives ACID transactions, unique constraints (idempotency keys for CAP-02 dedupe), sequences (invoice numbers for CAP-05), and `SELECT ... FOR UPDATE` to serialize per-subscription billing safely. A single primary instance is ample at this scale.
  - **Alternatives**: MySQL — equivalent fit; prefer only if the team or host standardizes on it. DynamoDB — avoid here; the access patterns are relational and need multi-row transactions and sequences, which fight a key-value store.
- **Object storage — Recommendation**: **S3-compatible blob store** for generated invoice PDFs (CAP-05), served via signed URLs.
- **Why**: Invoices are immutable artifacts that must be retrievable from the portal; Postgres holds invoice metadata, the blob store holds the rendered PDF, keeping large binaries out of the DB.
  - **Alternatives**: Postgres `bytea` — acceptable at very low volume; move to object storage as invoice count grows.
- **Cache / search / analytics**: **Not needed at this scale.** Plan catalogs and subscription lookups are tiny and fully served by indexed Postgres; there is no search or analytics requirement in the breakdown. Add a Redis cache only if the plan-catalog read path (CAP-01) ever becomes hot, which a few thousand users will not cause.

### Async / messaging
- **Recommendation**: A **durable job/queue system** — **BullMQ (Redis)** if managed Redis is easy on the chosen host, otherwise **pg-boss (Postgres-backed)** to avoid adding infrastructure — plus a **cron-style scheduler** (the host's scheduled job, or a leader-elected in-process cron) to trigger the recurring billing run.
- **Why**: Several capabilities are explicitly asynchronous and must not block user requests:
  - CAP-04 (billing cycle) is a scheduled batch — the scheduler enqueues one billing job per due subscription.
  - CAP-02 webhook reconciliation (delayed gateway confirmation) consumes webhooks off a queue.
  - CAP-06 (payment retry / dunning) schedules future retry attempts — durable delayed jobs are exactly this.
  - CAP-05 PDF rendering and all email dispatch run as jobs so the request path stays fast.
  Queue jobs provide retry-with-backoff, idempotency, and durability for free. A full event-streaming platform (Kafka) is unjustified at this scale.
- **Alternatives**: pg-boss — prefer when you want zero new infrastructure (reuses Postgres) and throughput is low, which it is here. Cloud-native queue (SQS) + scheduler (EventBridge) — prefer if you commit to AWS and want fully managed primitives.

### Authentication & authorization
- **Recommendation**: Since no existing identity system was named, **use a managed auth provider** (e.g. Clerk, Auth0, or Supabase Auth) that issues verifiable JWTs the billing API validates and maps to a customer record. Add a small **role check** for admin-only actions (e.g. immediate cancellation in CAP-03, manual retry in CAP-06). Internal scheduler/worker → API calls use a separate service credential.
- **Why**: A 4-person team should not hand-roll identity, password storage, and session management for a money system — a managed provider removes that liability and integrates cleanly with the Next.js frontend. Billing only needs to (a) trust verifiable tokens and (b) enforce the few privileged operations.
- **Alternatives**: **Delegate to an existing user-account system** — strongly prefer this if one already exists (flagged as an open question); re-implementing auth would duplicate an existing capability. Self-hosted Keycloak — only if there's a data-residency or cost reason to avoid a SaaS IdP.

### Infrastructure & hosting
- **Recommendation**: **Managed container PaaS** (Render, Railway, Fly.io, or AWS App Runner / ECS Fargate) running three process types from one codebase — the **web/API service**, the **worker** (queue consumer), and the **scheduler** (cron) — plus **managed Postgres** (RDS / Neon / the PaaS's Postgres) and **managed Redis** if BullMQ is chosen. One staging + one production environment.
- **Why**: A 4-person team should spend its time on billing correctness, not on operating Kubernetes. A managed PaaS gives push-to-deploy, managed TLS, and managed datastores with backups. Three process types (api/worker/scheduler) cleanly separate the request path, async work, and the recurring batch while sharing one image — the modular-monolith deployment model.
- **Alternatives**: AWS ECS Fargate + RDS + ElastiCache + EventBridge — prefer if the org is already an AWS shop and wants everything in one account. Kubernetes (EKS/GKE) — avoid at this team size and scale; the operational overhead isn't justified.

### CI/CD & developer tooling
- **Recommendation**: **GitHub Actions** pipeline: lint (ESLint) + typecheck (`tsc`) + unit/integration tests (Vitest or Jest, with Postgres in a service container) on every PR; build a single Docker image; deploy to staging on merge to main; promote to production on a tagged release or manual approval. **Prisma Migrate** for schema migrations run as a controlled release step. Infrastructure as config-as-code (e.g. `render.yaml`) or Terraform if on AWS.
- **Why**: Billing logic must be heavily tested — proration (CAP-03), grace periods and double-billing prevention (CAP-04), idempotent charges (CAP-02), and retry counting (CAP-06) are exactly the money-touching logic that needs an integration suite gating every deploy. Migrations as a controlled release step prevent schema drift against live billing tables.
- **Alternatives**: GitLab CI / CircleCI — equivalent; pick whatever hosts the repo. Manual deploys — unacceptable for a money system; automate from day one.

### Observability
- **Recommendation**: **Structured JSON logging** (pino) shipped to a managed log platform; **error tracking** via Sentry; **metrics + alerting** via the host's monitoring or a cheap managed tier (Grafana Cloud / Datadog); **distributed tracing optional** via OpenTelemetry if latency becomes an issue.
- **Why**: The highest-stakes failures are silent: the recurring billing run (CAP-04) not firing, charges silently failing, or retries (CAP-06) not running on schedule. Alert on: billing-job success/failure counts and last-run timestamp, payment decline rate (CAP-02), webhook processing lag, and queue depth/age. Sentry catches exceptions in proration and invoice generation. This is the minimum to trust an autonomous money system.
- **Alternatives**: Full Datadog/New Relic suite — prefer once scale or team grows; overkill now. Logs-only with no metrics — insufficient, because the batch and retry schedulers need active "did it run?" alerting.

### Third-party services & integrations
- **Recommendation**:
  - **Payment gateway: Stripe** — for CAP-02 (charges via PaymentIntents with idempotency keys), stored payment methods as tokens (recurring charges for CAP-02/CAP-04), and webhooks for asynchronous confirmation. **[Flagged for research — see Research Suggestions.]**
  - **Transactional email: a managed email API** (e.g. Resend, Postmark, or SES) — for CAP-05 invoice delivery and CAP-06 failure/recovery (dunning) notifications. **Swap for an existing email service if one exists.**
  - **Invoice PDF rendering**: a server-side HTML-to-PDF renderer (headless-Chromium or a templating + PDF library) run inside the worker (CAP-05).
- **Why**: A gateway with tokenization and Elements keeps raw card data out of the system entirely (PCI SAQ A), satisfying the hard constraint. Stripe natively provides idempotency keys (CAP-02 duplicate-charge defense), stored-method tokens (recurring CAP-04 charges), and webhooks (CAP-02 delayed-confirmation), which map directly onto the breakdown.
- **Alternatives**: Braintree / Adyen as the gateway — prefer Adyen if you later need broad international/multi-currency coverage, Braintree if PayPal is a required method. This is a high-stakes, hard-to-reverse choice — see Research Suggestions.

### Security
- **Recommendation**: PCI scope minimization via gateway tokenization (no PAN/CVV ever stored or logged). **Secrets** (gateway API keys, DB creds, webhook signing secrets) in the host's secret manager / injected env, never in the repo. **TLS everywhere** (managed certs). **Encryption at rest** on Postgres and the blob store (managed-provider default). **Verify webhook signatures** from the gateway before acting on them. **Idempotency keys** on all charge requests (CAP-02). **Audit log** of privileged actions — admin immediate-cancel (CAP-03) and manual retry (CAP-06). PII (name, email, billing address) treated as GDPR-relevant: access-controlled and deletable.
- **Why**: This is a money-and-PII system; the threat model is fraudulent charges, leaked card/PII data, and unauthorized admin actions. Tokenization removes the largest risk class (card data) entirely. Webhook signature verification prevents forged "payment succeeded" events. Idempotency keys defend against double-charging. Audit logging makes admin overrides traceable.
- **Alternatives**: Storing cards yourself behind your own vault — explicitly rejected; it pulls you into PCI SAQ D and is unjustifiable for this team and scale.

## Capability → Tech Mapping

| Capability | Implemented by | Notes |
|-----------|----------------|-------|
| CAP-01 Plan selection | Next.js plan/portal pages → NestJS `PlanSelection` module → Postgres `plans`/`subscriptions` | Reads plan catalog from Postgres; records selection + change type; routes upgrades to CAP-02, downgrades to a scheduled change handled by CAP-03. |
| CAP-02 Payment processing | NestJS `Payments` module → Stripe PaymentIntents + tokens → Postgres `transactions`; webhooks via queue/worker | Idempotency keys for dedupe; stored tokens for recurring charges; webhook consumer handles delayed confirmation; failures enqueue CAP-06. |
| CAP-03 Subscription lifecycle | NestJS `Subscriptions` module → Postgres `subscriptions` (transactional state machine) | Activate/upgrade/downgrade/cancel/reactivate/expire as state transitions; proration computed in-module and charged via CAP-02. Admin immediate-cancel is role-gated + audited. |
| CAP-04 Billing cycle | Scheduler (cron) → enqueues per-subscription billing jobs → worker → `Payments`/`Subscriptions` | Recurring run queries due subscriptions; `FOR UPDATE` + last-billing-date guard prevents double-billing; missed runs self-heal (query all past-due). Successful renewals extend the period and trigger CAP-05. |
| CAP-05 Invoice generation | NestJS `Invoicing` module → Postgres invoice metadata + sequence → worker renders PDF → blob store → email API | Gapless invoice numbers via Postgres sequence; PDF rendered async; delivered via the email service and retrievable from the portal via signed URL. |
| CAP-06 Payment retry / dunning | NestJS `Dunning` module → delayed queue jobs (BullMQ/pg-boss) → `Payments` → email notifications | Durable delayed jobs implement the retry schedule; retry count tracked in `retry_schedules`; payment-method update triggers immediate retry; exhaustion signals CAP-03 to suspend. Manual admin retry is role-gated + audited. |

## Key Architecture Decisions

### AD-01: Modular monolith over microservices

- **Decision**: Build CAP-01..CAP-06 as modules in one TypeScript service (with separate worker and scheduler processes from the same codebase), not as independent services.
- **Context**: 4-person TypeScript team, a few thousand customers, six tightly-coupled capabilities that share data and need cross-capability transactions (charge + activate, renew + invoice).
- **Rationale**: One deploy and one database let four people move fast and keep billing state transactionally consistent. Microservices would impose network boundaries, distributed transactions, and operational overhead with no scale justification. NestJS modules preserve clean seams for later extraction.
- **Tradeoffs**: All capabilities scale and deploy together; a bug in one module can affect the whole service. Acceptable at this scale, mitigated by strong module boundaries and tests.

### AD-02: Payment gateway with tokenization; never store card data

- **Decision**: Use a gateway (recommended: Stripe) with Elements for capture and tokens for recurring charges; store only tokens and transaction references.
- **Context**: Hard constraint that payments use a gateway and no raw card data is stored; CAP-02 needs recurring charges, idempotency, and async confirmation.
- **Rationale**: Keeps PCI scope at SAQ A, removes the largest security liability, and the gateway natively provides the idempotency keys, stored methods, and webhooks the breakdown's edge cases require.
- **Tradeoffs**: Vendor lock-in to the gateway's API and fee structure; some flows (proration math, dunning logic) are split between our code and provider features. Isolate gateway calls behind a single `Payments` adapter to ease a future swap.

### AD-03: Postgres as the single transactional store

- **Decision**: One managed Postgres instance holds plans, subscriptions, transactions, invoices, and retry schedules.
- **Context**: Billing is relational and money-critical: atomic charge-and-activate, gapless invoice numbers, double-billing prevention.
- **Rationale**: ACID transactions, unique/idempotency constraints, sequences, and row locking directly implement the breakdown's correctness requirements. Scale is small enough that a single primary suffices.
- **Tradeoffs**: A single primary is an eventual scaling/availability ceiling; mitigated by managed backups/failover and the fact that this scale is far from the limit.

### AD-04: Scheduler + durable queue for batch and retries

- **Decision**: A cron scheduler triggers the recurring billing run and due retries; a durable queue (BullMQ or pg-boss) runs charges, webhook handling, PDF rendering, and email off the request path.
- **Context**: CAP-04 is a recurring batch, CAP-06 needs delayed retries over days, and several CAP-02/CAP-05 steps must not block users.
- **Rationale**: Durable delayed jobs with retry/backoff and idempotency are the natural fit; missed runs self-heal by querying all past-due work. Avoids a heavyweight streaming platform.
- **Tradeoffs**: Adds a Redis dependency if BullMQ is chosen (pg-boss avoids it but shares the DB); requires care to make jobs idempotent so a retried job never double-charges.

## Risks & Tradeoffs

- **Double-charging is the worst failure.** Mitigation: gateway idempotency keys per charge, a last-billing-date guard plus `SELECT ... FOR UPDATE` in CAP-04, and idempotent queue jobs. Test this path hardest.
- **The recurring billing job silently not running** would stall all revenue. Mitigation: alert on last-successful-run timestamp and job success counts; the catch-up query design means a missed run recovers automatically on the next run.
- **Proration correctness (CAP-03)** is subtle and money-visible; getting it wrong erodes trust. Mitigation: dedicated integration tests; the strategy itself is flagged for research below.
- **Single Postgres primary** is an availability/scaling ceiling. Acceptable now; revisit read replicas and connection pooling well before tens of thousands of active subscriptions.
- **Gateway lock-in.** Switching providers later is costly because tokens and webhook semantics are provider-specific. Accepted as a deliberate tradeoff for PCI scope reduction; the `Payments` adapter isolates it.
- **Dunning (CAP-06) retry policy** affects revenue recovery and customer experience; a poor schedule either loses recoverable revenue or annoys customers. Flagged for research below.

## Research Suggestions

High-stakes or uncertain choices to validate with the researcher skill (the researcher skill was not available in this session):

- **Payment gateway selection** — Stripe is the recommended default, but the choice is hard to reverse (tokens, webhooks, and fees are provider-specific) and depends on regional availability, payout terms, and roadmap. Suggested researcher query: "Stripe vs Braintree vs Adyen for a small-team SaaS recurring-billing system — tokenization, recurring-charge and dunning features, idempotency, webhook reliability, fees, and international/multi-currency roadmap."
- **Proration strategy for mid-cycle changes** — How to compute and present prorated charges/credits on upgrade and downgrade (CAP-01/CAP-03). Suggested researcher query: "Best practices for prorating subscription charges and credits on mid-cycle SaaS plan upgrades and downgrades, and how leading billing platforms implement it."
- **Payment retry / dunning schedule (CAP-06)** — Optimal retry intervals, max attempts, and notification cadence to maximize recovery without excess gateway cost or customer friction. Suggested researcher query: "Optimal payment retry intervals, maximum attempts, and dunning email sequencing for SaaS subscription payment recovery."
- **Queue technology: BullMQ (Redis) vs pg-boss (Postgres)** — Whether the extra Redis dependency is worth it at this scale, or reusing Postgres suffices. Suggested researcher query: "BullMQ vs pg-boss for delayed/scheduled jobs in a small Node.js billing service — durability, delayed-job support, operational overhead, and throughput limits."

## Open Questions

- Does an existing user-account / identity system exist that the billing service should delegate to (validating its tokens), or should it stand up a managed auth provider? (Drives the auth section: delegate vs. managed IdP.)
- Does an existing transactional email service exist that CAP-05/CAP-06 should send through, or should the system adopt a managed email API?
- Is a managed Redis readily available on the chosen host (favoring BullMQ), or should the system stay Postgres-only with pg-boss?
- Are there data-residency requirements for customer PII that constrain the hosting region?
- These are *technical* open questions. Functional questions (billing frequency, minimum subscription period, proration-credit policy, multi-currency, tax handling, multiple subscriptions per user) belong to the source breakdown and should be resolved with solution-architect, not here.

## Next Steps

1. Confirm whether existing identity and email systems exist (resolves the two highest-impact open questions and the auth/email recommendations).
2. Stand up the repo skeleton: NestJS modules for CAP-01..CAP-06, Prisma schema for the core tables, and the three process types (api/worker/scheduler) deployable to the chosen PaaS.
3. Spike the Stripe integration end-to-end in test mode: PaymentIntent with idempotency key, stored-token recurring charge, and signed webhook handling (de-risks CAP-02 and AD-02).
4. Build the integration test harness against a real Postgres for the money-critical paths: idempotent charge, recurring billing catch-up + double-billing guard, proration, and retry counting.
5. Wire observability for the billing job (last-run + success/failure alerts) before the first real charge.
6. Run the four research queries above (gateway choice, proration, dunning schedule, queue tech) before locking those decisions.

---
*Technical architecture produced by technical-architect skill. Use the librarian skill to persist this artifact.*
