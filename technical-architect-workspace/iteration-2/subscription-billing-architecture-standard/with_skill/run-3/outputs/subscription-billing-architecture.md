# SaaS Subscription Billing System — Technical Architecture

> Technical Architect | Depth: standard | Generated: 2026-06-10

## Source Breakdown

Capability breakdown was provided inline by the user (the librarian skill is unavailable, so nothing was retrieved from stored artifacts). This architecture builds on the six capabilities below and does not invent new ones. If a richer breakdown exists, an agent with librarian access could retrieve it with: **specs matching "subscription billing capability breakdown plan payment invoice dunning"**.

- **CAP-01 — Plan selection**: customer chooses a subscription plan/tier (and presumably billing interval).
- **CAP-02 — Payment processing**: capturing and charging a payment method via a gateway.
- **CAP-03 — Subscription lifecycle**: create, upgrade/downgrade, pause, cancel, reactivate a subscription.
- **CAP-04 — Billing cycle**: time-driven generation of charges per the subscription's interval (proration, anchor dates).
- **CAP-05 — Invoice generation**: producing invoices/receipts for each billed period.
- **CAP-06 — Payment retry / dunning**: retrying failed payments on a schedule and escalating (emails, eventual suspension).

> Note: the breakdown as stated is a functional list without explicit interval/proration/tax rules. Those are *functional* details that belong to solution-architect; where they affect a technical choice I flag them in Open Questions rather than inventing the rule.

## Constraints & Assumptions

- **Scale & load**: A few thousand customers in year one **[stated]**. Implies low write throughput (billing events are periodic, not high-frequency) and modest concurrency — well within a single relational database and a single application instance **[assumed]**. No stated latency/availability SLA; assume "small SaaS" expectations: 99.9% target, sub-second API responses **[assumed]**.
- **Team**: 4 people, comfortable with TypeScript **[stated]**. Small team — operational simplicity and a single language across the stack matter more than best-of-breed polyglot tooling **[assumed]**.
- **Hosting**: Not specified **[assumed]**. Recommending a managed PaaS to minimize ops burden for a 4-person team; cloud-agnostic enough to move to AWS/GCP later.
- **Hard constraints**: Payment must go through a gateway with **no raw card storage** **[stated]** — this is a PCI-DSS scope-reduction requirement and shapes CAP-02/CAP-06. No other compliance stated; assume GDPR-style data-protection hygiene is prudent (customer PII) **[assumed]**.
- **Existing systems**: None mentioned **[assumed greenfield]**.

## Architecture Overview

- **Style**: **Modular monolith** (single deployable, internally partitioned by capability) with a **scheduled-job + lightweight queue** for time-driven and retry work. Rationale: a 4-person team at a few-thousand-customer scale should not pay the operational tax of microservices; billing is highly transactional and benefits from a single database with ACID guarantees, while the genuinely asynchronous parts (CAP-04 billing runs, CAP-06 dunning) are handled by background workers rather than separate services.
- **Shape**: A TypeScript web application exposes the customer-facing UI (CAP-01 plan selection, CAP-03 self-service lifecycle) and an API. Internal modules — `plans`, `subscriptions`, `billing`, `invoicing`, `dunning`, `payments` — share one Postgres database but keep clear boundaries. The payment gateway (Stripe) holds all card data and is the source of truth for charge outcomes; our system records subscription state, invoices, and dunning attempts, and reacts to gateway webhooks. A scheduler triggers periodic billing-cycle and retry jobs, which enqueue work onto a background-job queue processed by a worker running in the same codebase. Customers and the team are notified via a transactional email provider.

## Tech Stack

### Frontend
- **Recommendation**: **Next.js (React, App Router) in TypeScript**, server-rendered, deployed alongside or in front of the API. Use a component library such as shadcn/ui or Mantine for the plan-selection and account-management screens.
- **Why**: CAP-01 (plan selection) and CAP-03 (self-service lifecycle: upgrade/downgrade/cancel) are interactive UI flows; CAP-05 needs an invoice/receipt view. Next.js gives SSR for fast first paint and a single TypeScript codebase the whole team already knows. It also pairs cleanly with Stripe's hosted/embedded payment elements so no card data touches our UI's own form state.
- **Alternatives**: **Plain React + Vite SPA** if you want to fully decouple frontend from backend and host it as static assets (prefer when the API is consumed by multiple clients). **Remix** if you favor its data-loading model — comparable, pick on team taste.

### Backend / API
- **Recommendation**: **Node.js + TypeScript with NestJS** (or Fastify if you prefer minimalism), exposing a REST/JSON API. Keep modules aligned to capabilities (`plans`, `subscriptions`, `billing`, `invoicing`, `dunning`, `payments`).
- **Why**: Single-language stack for a small team. NestJS gives opinionated module boundaries that map directly to the capability list and enforce the modular-monolith discipline; its DI and structure help a 4-person team stay organized as billing logic grows. Billing logic is transactional and rule-heavy (proration in CAP-04, state transitions in CAP-03), which suits a structured server framework over ad-hoc handlers.
- **Alternatives**: **Fastify (+ Zod)** for a lighter, faster, less prescriptive setup — prefer if the team finds NestJS too heavy. **Next.js API routes / server actions** to collapse front and back into one app — prefer only if the API is purely for this one frontend and you want minimal moving parts; weaker for background workers.

### Data storage
- **Primary database — Recommendation**: **PostgreSQL** with **Prisma** (or Drizzle) as the TypeScript ORM.
  - **Why**: Billing data is deeply relational (customer → subscription → plan → invoices → line items → payment attempts) and demands transactional integrity and correctness over scale — money must not be double-charged or lost. Postgres gives ACID transactions, strong constraints, and exact-numeric (`NUMERIC`) money columns. At a few thousand customers it is nowhere near a scaling limit. Prisma keeps schema and types in TypeScript, matching the team.
  - **Alternatives**: **MySQL** — equivalent for this use case, pick on familiarity/hosting. Avoid document stores (e.g. MongoDB) here: the relational integrity and transactional charging logic are exactly what NoSQL trades away.
- **Cache — Recommendation**: **Redis** (managed), used for the job queue and rate limiting; optional read caching.
  - **Why**: Doubles as the backing store for the background-job queue (below). At this scale a dedicated read cache is not yet justified — note this and add later if hot reads appear.
- **Search / analytics store**: **Not needed.** A few thousand customers don't justify a search engine or separate analytics warehouse; Postgres queries cover reporting. Add a warehouse (e.g. BigQuery) only when finance reporting outgrows the operational DB.
- **Object/blob store — Recommendation**: **S3-compatible object storage** (provider's bucket, e.g. AWS S3 / Cloudflare R2) for generated invoice PDFs (CAP-05).
  - **Why**: Invoices are immutable documents better stored as files than DB blobs; cheap, durable, and servable via signed URLs.

### Async / messaging
- **Recommendation**: **BullMQ (Redis-backed job queue)** plus a **scheduler** (BullMQ repeatable jobs, or a managed cron) driving the worker process.
- **Why**: CAP-04 (billing cycle) is time-triggered — a daily scheduled job finds subscriptions due for billing and enqueues a charge job each. CAP-06 (dunning) is inherently a delayed-retry workflow — BullMQ's delayed jobs and backoff map directly onto a dunning schedule (retry at +1d, +3d, +5d, then suspend). Processing charges off the request path keeps the API responsive and isolates third-party (gateway/email) latency and failures with built-in retries. A full broker (Kafka/RabbitMQ) is overkill at this scale.
- **Alternatives**: **pg-boss** (Postgres-backed queue) — prefer if you want zero extra infrastructure and to avoid Redis entirely; slightly less throughput headroom but ample here. **Cloud-native queue (SQS + EventBridge scheduler)** — prefer if you commit to AWS and want fully managed.

### Authentication & authorization
- **Recommendation**: **Managed auth provider** — **Clerk** or **Auth0** (or **Supabase Auth** if you lean Postgres-native) — issuing sessions/JWTs; simple role model (customer, admin) enforced in the backend.
- **Why**: Auth is not a capability in the breakdown but is required to gate CAP-03 self-service and CAP-05 invoice access to the right customer. A managed provider offloads password/MFA/social-login security from a 4-person team and reduces breach surface. Authorization is coarse (a customer sees only their own subscription/invoices; admins see all), enforced server-side on every billing resource.
- **Alternatives**: **Lucia / Auth.js (self-hosted)** — prefer if you want to avoid per-MAU vendor cost and keep auth in-house; more maintenance. Roll-your-own is discouraged for a team this size.

### Infrastructure & hosting
- **Recommendation**: **Managed PaaS** — **Render**, **Railway**, or **Fly.io** — running (1) the web/API app and (2) the worker as separate processes from one repo, plus managed Postgres and managed Redis from the same provider.
- **Why**: A 4-person team should spend its time on billing correctness, not Kubernetes. PaaS gives push-to-deploy, managed databases, TLS, and easy horizontal scaling of the worker if dunning/billing volume grows. The modular monolith deploys as one image with two process types (web, worker).
- **Alternatives**: **AWS ECS Fargate + RDS + ElastiCache** (Terraform/CDK) — prefer when you outgrow PaaS or have a compliance/data-residency reason to control the account directly; more ops overhead. **Vercel (frontend) + separate backend host** — prefer if you split Next.js frontend from the API.

### CI/CD & developer tooling
- **Recommendation**: **GitHub Actions** for CI (typecheck, lint, test, build) and CD (deploy on merge to `main` via the PaaS integration). **pnpm** monorepo (or single package), **ESLint + Prettier**, **Vitest/Jest** for tests, **Prisma Migrate** for schema migrations. Environments: `preview` (per-PR), `staging`, `production`.
- **Why**: Standard, low-cost, TypeScript-native pipeline. Migrations gated in CI protect the money-critical schema. Per-PR preview environments help a small team review billing flows safely. **Use Stripe test mode in CI/staging** so payment flows are exercised without real charges.
- **Alternatives**: **Provider-native CI** (Render/Railway build hooks) — simpler but less control; prefer for absolute minimal setup. **GitLab CI** if you host code there.

### Observability
- **Recommendation**: **Structured logging** (pino) shipped to a managed log platform; **error tracking with Sentry**; **uptime/synthetic checks** on the API and on the daily billing job; **alerting** to Slack/email. Track key business/technical metrics: failed-charge rate, dunning queue depth, billing-job completion, webhook processing lag.
- **Why**: In billing, silent failures cost money — an unran billing cycle (CAP-04) or a stuck dunning queue (CAP-06) must page someone. Sentry catches exceptions in charge and webhook handlers. A heartbeat/alert on the scheduled billing job is the single most important monitor in this system.
- **Alternatives**: **OpenTelemetry → Grafana Cloud / Datadog** — prefer when you want unified traces/metrics/logs and can absorb the cost/setup. **Provider-built-in metrics + Sentry** is enough to start.

### Third-party services & integrations
- **Payment gateway — Recommendation**: **Stripe** (Billing + Payment Intents + Customer Portal), used as the system of record for cards, charges, and ideally subscription objects.
  - **Why**: Directly satisfies the **no-raw-card-storage [stated]** constraint — card data lives in Stripe, drastically shrinking PCI scope (SAQ A). Stripe Billing natively models plans/prices (CAP-01), subscriptions and proration (CAP-03/CAP-04), invoices (CAP-05), and **Smart Retries / dunning** (CAP-06), and its hosted Customer Portal can deliver much of CAP-03 self-service for near-zero build cost. Webhooks drive our state updates. Excellent TypeScript SDK.
  - **Alternatives**: **Paddle / Lemon Squeezy (merchant-of-record)** — prefer if you want them to also handle global sales-tax/VAT remittance and act as reseller; less control over the data model. **Braintree/Adyen** — prefer at larger scale or for specific regional payment methods.
- **Transactional email — Recommendation**: **Resend** (or Postmark/SendGrid) for invoice delivery (CAP-05) and dunning notifications (CAP-06).
  - **Why**: CAP-06 dunning requires reliable "payment failed / please update card" emails; CAP-05 sends receipts/invoices. Managed deliverability beats self-hosted SMTP. Resend has a clean TypeScript SDK.
- **Tax (conditional)**: If you sell across tax jurisdictions, **Stripe Tax** (or a merchant-of-record like Paddle) handles VAT/sales-tax. Flagged in Open Questions — depends on a functional rule not in the breakdown.

### Security
- **Recommendation**:
  - **PCI scope**: never let card data touch our servers — use Stripe Elements/Checkout/Customer Portal so the browser sends card data directly to Stripe; we store only Stripe customer/payment-method *tokens*. Keeps us at **SAQ A** **[stated constraint honored]**.
  - **Secrets**: store Stripe keys, DB/Redis URLs, email keys, and the **webhook signing secret** in the platform's secret manager (or AWS Secrets Manager) — never in the repo. **Verify every Stripe webhook signature** before acting on it.
  - **Encryption**: TLS everywhere (provider-managed certs); encryption at rest on managed Postgres/Redis/object store (provider default).
  - **Idempotency**: use Stripe idempotency keys on charge calls and de-dupe webhook deliveries (store processed event IDs) so retries (CAP-06) and redeliveries never double-charge.
  - **Access control**: enforce per-customer ownership checks on every subscription/invoice endpoint; restrict admin actions by role; audit-log billing-state changes.
- **Why**: Money + PII raise the stakes of every gap. Most card-data risk is eliminated by the gateway design; the remaining critical controls are webhook authenticity, idempotency, and tenant data isolation.

## Capability → Tech Mapping

| Capability | Implemented by | Notes |
|-----------|----------------|-------|
| CAP-01 Plan selection | Next.js UI + `plans` module + Stripe Prices/Products | Plans defined in Stripe, mirrored/read in Postgres for display; UI presents tiers and intervals. |
| CAP-02 Payment processing | Stripe (Payment Intents / Checkout) + `payments` module + Stripe webhooks | Card data stays in Stripe (no raw storage). We trigger charges and react to outcomes via signed webhooks. |
| CAP-03 Subscription lifecycle | `subscriptions` module + Postgres (state) + Stripe Subscriptions + Customer Portal | Create/upgrade/downgrade/pause/cancel as DB state transitions kept in sync with Stripe; Portal can offload self-service. |
| CAP-04 Billing cycle | Scheduler + BullMQ worker + `billing` module + Postgres + Stripe invoicing/proration | Daily job finds due subscriptions and enqueues charge jobs; Stripe handles proration math at the period anchor. |
| CAP-05 Invoice generation | `invoicing` module + Stripe Invoices + S3 (PDF) + Resend (delivery) | Invoice records in Postgres, PDF stored in object storage, emailed to customer. |
| CAP-06 Payment retry / dunning | BullMQ delayed jobs + backoff + `dunning` module + Resend + Stripe Smart Retries | Failed charges enqueue a retry schedule with escalation emails; final step suspends via CAP-03 state change. Stripe Smart Retries can own the retry curve. |

> Auth, observability, and infra are cross-cutting and support all six capabilities (notably gating CAP-03/CAP-05 access and monitoring CAP-04/CAP-06 jobs).

## Key Architecture Decisions

### AD-01: Modular monolith over microservices

- **Decision**: Build one deployable TypeScript application internally partitioned by capability, with a separate worker process for async work.
- **Context**: 4-person team **[stated]**, a few thousand customers year one **[stated]**, transactional billing logic spanning subscriptions/invoices/payments.
- **Rationale**: Microservices would add network boundaries, distributed transactions, and ops overhead that a small team and modest scale don't warrant. A single Postgres + modular code gives ACID correctness and fast iteration. Modules keep boundaries clean if a future split is ever needed.
- **Tradeoffs**: All capabilities share one deploy and DB — a bad migration or hot path can affect everything. Mitigated by module discipline, migration gating in CI, and splitting only the worker process.

### AD-02: Stripe as billing system of record (offload, don't rebuild)

- **Decision**: Use Stripe Billing for prices, subscriptions, proration, invoices, and dunning rather than rebuilding these in-house; treat our DB as a synchronized projection driven by webhooks.
- **Context**: No-raw-card-storage constraint **[stated]**; CAP-01..CAP-06 closely mirror Stripe Billing primitives; small team that can't afford to build/maintain a charging engine.
- **Rationale**: Maximizes correctness and minimizes PCI scope and build effort. Stripe Smart Retries directly implements CAP-06; the Customer Portal covers much of CAP-03.
- **Tradeoffs**: Vendor lock-in and per-transaction fees; logic spread across our DB and Stripe requires careful webhook-driven sync and idempotency. Mitigated by keeping a clean `payments` abstraction so the gateway is replaceable, and by treating Stripe as source of truth for money state.

### AD-03: Redis-backed job queue (BullMQ) for time-driven and retry work

- **Decision**: Run billing-cycle (CAP-04) and dunning (CAP-06) as scheduled + delayed background jobs via BullMQ on Redis, processed by a dedicated worker.
- **Context**: Billing is periodic; dunning is delayed-retry-with-backoff; charges call slow/failable third parties.
- **Rationale**: Keeps the API responsive, gives automatic retries/backoff and a delayed-job model that maps onto a dunning schedule, and isolates third-party failures. Right-sized vs. a full message broker.
- **Tradeoffs**: Adds Redis as a dependency and a second process to operate. Mitigated by managed Redis; **pg-boss** is the fallback if avoiding Redis is preferred (recorded in Async layer).

### AD-04: Managed PaaS + managed auth to minimize ops for a small team

- **Decision**: Host on a managed PaaS with managed Postgres/Redis and use a managed auth provider.
- **Context**: 4-person team **[stated]**; no stated cloud or compliance lock-in.
- **Rationale**: Conserves the team's time for billing correctness; reduces security surface (auth, patching). Cloud-agnostic enough to migrate to AWS later.
- **Tradeoffs**: Higher per-unit cost than raw IaaS and some platform lock-in; acceptable at this scale and revisitable when economics or compliance change.

## Risks & Tradeoffs

- **State drift between our DB and Stripe** — the biggest operational risk. If a webhook is missed or processed twice, subscription/invoice state diverges. Mitigate with signature verification, idempotent webhook handling (store processed event IDs), and a periodic reconciliation job against the Stripe API.
- **Silent failure of the billing cron (CAP-04)** — if the daily job doesn't run, customers aren't billed and nobody notices. Mitigate with a heartbeat/dead-man's-switch alert on job completion.
- **Double-charging on retries (CAP-06)** — retried charges without idempotency keys can bill twice. Mitigate with Stripe idempotency keys and at-most-once charge logic per invoice period.
- **Proration / interval rules underspecified** — CAP-04 proration and CAP-03 mid-cycle changes have many edge cases. Leaning on Stripe's proration reduces risk, but the *policy* (credit vs. charge immediately, anchor dates) is a functional decision still open.
- **Vendor lock-in (Stripe + PaaS)** — accepted deliberately for speed; the `payments` module abstraction and standard Postgres keep an exit path.
- **Tax/compliance gap** — if selling internationally, unhandled VAT/sales-tax is a legal/financial risk; see Open Questions.

## Research Suggestions

The researcher skill is unavailable in this run. High-stakes choices to validate, with ready-to-use queries:

- **Build-vs-buy depth on Stripe Billing** — how much of CAP-03/CAP-04/CAP-06 to delegate to Stripe vs. own, and the migration cost if you ever leave. Suggested researcher query: *"For a small TypeScript SaaS billing a few thousand customers, compare delegating subscription lifecycle, proration, invoicing, and dunning to Stripe Billing + Customer Portal + Smart Retries versus implementing them in-house against a payment-intents-only integration — covering correctness, PCI scope, fees, vendor lock-in, and exit cost in 2026."*
- **Job queue choice: BullMQ (Redis) vs pg-boss (Postgres)** — whether to add Redis at all at this scale. Suggested researcher query: *"Compare BullMQ on Redis versus pg-boss on Postgres for scheduled billing runs and delayed dunning retries in a Node.js modular monolith at low volume (a few thousand customers): reliability, delayed/backoff support, operational overhead, and when Redis becomes worth it."*
- **Sales-tax / VAT handling** — Stripe Tax vs. merchant-of-record (Paddle/Lemon Squeezy). Suggested researcher query: *"For a small SaaS selling subscriptions internationally in 2026, compare Stripe + Stripe Tax versus a merchant-of-record (Paddle, Lemon Squeezy) for VAT/sales-tax collection and remittance, on liability, integration effort, fees, and control over the billing data model."*

## Open Questions

- **Billing intervals & proration policy** — which intervals (monthly/annual), and on upgrade/downgrade do you charge/credit immediately or at next cycle? (Functional — confirm via solution-architect; drives CAP-03/CAP-04 config.)
- **Tax obligations** — do you sell across jurisdictions requiring VAT/sales-tax? Determines Stripe Tax vs merchant-of-record (affects CAP-02/CAP-05).
- **Dunning schedule & terminal action** — exact retry cadence and what happens after final failure (suspend immediately, grace period, downgrade?). Drives CAP-06 and the CAP-03 suspended state.
- **Self-service scope** — adopt Stripe's hosted Customer Portal for CAP-03, or build the lifecycle UI in-house for branding/control? Large build-effort lever.
- **Hosting/cloud preference** — any future requirement to be on a specific cloud or region (data residency) that would favor AWS/GCP over PaaS now?
- **Admin/internal needs** — is an internal admin/back-office for support refunds and manual adjustments in scope? (If yes, it's a capability for solution-architect, not assumed here.)

## Next Steps

1. Confirm the Open Questions with the user/solution-architect — especially intervals/proration, dunning policy, tax, and Customer-Portal-vs-custom — before locking the Stripe integration shape.
2. Stand up the repo: TypeScript monorepo (Next.js app + NestJS/Fastify API + worker), Postgres + Prisma schema for customers/subscriptions/plans/invoices/payment-attempts, GitHub Actions CI with migration gating.
3. Spike the Stripe integration in **test mode**: create products/prices (CAP-01), a checkout/payment-intent flow (CAP-02), and a webhook handler with signature verification + idempotent event storage.
4. Implement the scheduled billing job (CAP-04) and a dunning workflow (CAP-06) on BullMQ with a heartbeat alert; verify retries don't double-charge using idempotency keys.
5. Wire invoice PDF storage to object storage and delivery via Resend (CAP-05); add Sentry + structured logging + the billing-job dead-man's-switch.
6. Hand this architecture to the librarian skill to persist as a spec artifact.

---
*Technical architecture produced by technical-architect skill. Use the librarian skill to persist this artifact.*
