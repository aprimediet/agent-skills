# Subscription Billing System — Technical Architecture

> Technical Architect | Depth: standard | Generated: 2026-06-10

## 1. Context & Constraints

This architecture covers the technical design and tech-stack recommendation for a SaaS subscription billing system whose capabilities are already defined: plan selection (CAP-01), payment processing (CAP-02), subscription lifecycle (CAP-03), billing cycle (CAP-04), invoice generation (CAP-05), and payment retry/dunning (CAP-06).

### Stated constraints

| Constraint | Value | Architectural implication |
|-----------|-------|---------------------------|
| Team size | 4 engineers | Favor a modular monolith over microservices; minimize the number of moving parts and bespoke infrastructure. |
| Team skills | Comfortable with TypeScript | Single-language stack (TypeScript end-to-end) to reduce context switching and let any engineer work anywhere. |
| Year-one scale | A few thousand customers | Low absolute load. A single relational database and a single app process (horizontally scalable later) is more than sufficient. Premature distributed-systems complexity is a liability, not an asset. |
| Domain | Money movement | Correctness, idempotency, auditability, and PCI scope reduction dominate the design. Bugs here cost real money and trust. |

### Guiding principles

1. **Do not build a payment gateway or a card vault.** Use a PCI-Level-1 provider (Stripe) and keep raw card data entirely out of our systems. This single decision removes the largest compliance and security burden.
2. **The provider is the source of truth for money; our database is the source of truth for product entitlements.** We mirror provider state via webhooks rather than trying to out-think it.
3. **Every money-touching operation is idempotent.** Retries, duplicate webhooks, and concurrent schedulers must never double-charge or double-provision.
4. **Optimize for a 4-person team.** Boring, well-documented, batteries-included technology beats cutting-edge. One database, one deployable, one language.

---

## 2. Architecture Style

### Decision: Modular monolith (TypeScript) + managed Postgres + a job queue

A **modular monolith** — a single deployable application internally organized into bounded modules that map to the capabilities — is the right altitude for a 4-person team at a few-thousand-customer scale.

Why not microservices: each of CAP-01..06 *could* be a service, but at this scale that would mean 6 deploy pipelines, 6 sets of dashboards, inter-service network calls, distributed transactions, and a platform-engineering burden that 4 people cannot carry while also shipping features. The capabilities are tightly coupled around shared subscription/transaction state; splitting them introduces distributed-data problems with no offsetting benefit.

Why not serverless-first (e.g. all Lambda): the billing scheduler (CAP-04) and dunning (CAP-06) are inherently stateful, time-driven background workloads that are simpler to reason about as long-lived workers against a queue. Serverless functions are a fine *complement* (webhook ingestion) but a poor *foundation* for the whole system.

### Module map (within the monolith)

```
billing-app/
├── modules/
│   ├── catalog/        # CAP-01 plan catalog: plans, prices, features
│   ├── checkout/       # CAP-01 selection + proration preview + routing
│   ├── payments/       # CAP-02 charge orchestration, idempotency, Stripe adapter
│   ├── subscriptions/  # CAP-03 lifecycle state machine
│   ├── billing-cycle/  # CAP-04 scheduled renewal logic
│   ├── invoices/       # CAP-05 invoice assembly, numbering, PDF, delivery
│   ├── dunning/        # CAP-06 retry scheduling + recovery notifications
│   └── shared/         # domain types, money type, event bus, db, auth
├── jobs/               # queue workers (renewal sweep, retries, invoice render)
├── webhooks/           # Stripe webhook ingestion + signature verification
└── api/                # HTTP layer (REST), billing portal endpoints
```

Modules communicate **in-process** through explicit service interfaces and an **internal event bus** (a typed emitter persisting to an `events` outbox table). This keeps the capability boundaries from the breakdown intact and makes a future extraction to services possible without a rewrite — but we pay none of the distributed-systems tax today.

### Request vs. background split

- **Synchronous (HTTP request path)**: plan selection, immediate upgrade charges, payment-method updates, portal reads. Users wait on these.
- **Asynchronous (queue/worker path)**: the daily renewal sweep (CAP-04), payment retries (CAP-06), invoice PDF rendering and email delivery (CAP-05), and webhook follow-up processing. These must survive process restarts and run with at-least-once + idempotent semantics.

```
                    ┌─────────────────────────────────────────┐
   Browser ───────► │  Next.js (billing portal UI + API)       │
                    └───────────────┬─────────────────────────┘
                                    │ in-process modules
                    ┌───────────────▼─────────────────────────┐
   Stripe webhooks ►│  Modular monolith (Node/TS)              │
                    │  catalog│checkout│payments│subs│cycle│... │
                    └───┬──────────────┬───────────────┬───────┘
                        │              │               │
                  ┌─────▼────┐   ┌─────▼─────┐   ┌──────▼──────┐
                  │ Postgres │   │ Redis +   │   │  Stripe API │
                  │ (state + │   │ BullMQ    │   │ (gateway,   │
                  │  outbox) │   │ (jobs)    │   │  vault, SoT)│
                  └──────────┘   └───────────┘   └─────────────┘
```

---

## 3. Recommended Tech Stack

One opinionated choice per layer, with rationale and the runner-up.

### Language & runtime — **TypeScript on Node.js 22 LTS**

- **Why**: Matches team skill exactly. End-to-end TypeScript (DB types → API → UI) gives compile-time safety across the whole money path, which matters disproportionately in billing. Node 22 is LTS through 2027.
- **Alternative**: Bun (faster, native TS) — promising but less battle-tested for long-running financial workloads and has thinner library/observability support. Revisit later; do not bet the billing system on it now.

### Web framework / app shell — **Next.js (App Router) for the portal + a dedicated Node API**

- **Why**: The customer-facing billing portal (plan selection, payment-method update, invoice list/download) is a CRUD-y authenticated web app — Next.js delivers UI + API routes + SSR in one TypeScript codebase the whole team already understands. Use Stripe Elements / Checkout on the front end so card data never touches our origin.
- **API style**: REST over HTTPS. The surface is small and resource-shaped (plans, subscriptions, invoices, payment-methods); REST keeps it inspectable and easy to test. Skip GraphQL — no client-shape-flexibility problem to solve here.
- **Alternative**: A separate React SPA + standalone Fastify/NestJS API. Cleaner separation, but two codebases and two deploys for a 4-person team. NestJS is a reasonable pick if the team prefers a heavier, opinionated DI framework; Next.js + a thin service layer is lighter.

### Database — **PostgreSQL 16 (managed: Supabase, Neon, or RDS)**

- **Why**: Billing is relational and transactional to its core — subscriptions, transactions, invoices, and retry schedules have strict referential integrity and need ACID guarantees. Postgres gives us transactions, `NUMERIC` for exact money math, `SELECT ... FOR UPDATE SKIP LOCKED` for safe concurrent job claiming, partial unique indexes for idempotency keys, and JSONB for storing raw provider payloads. A managed instance removes ops burden. At a few thousand customers, a single primary with automated backups is ample.
- **Critical rule**: store money as integer minor units (cents) or `NUMERIC(19,4)` — **never floats**.
- **Alternative**: MySQL/PlanetScale — fine, but Postgres's richer feature set (partial indexes, `SKIP LOCKED`, JSONB, exclusion constraints) is genuinely useful for billing concurrency. No reason to prefer MySQL here.

### ORM / data access — **Drizzle ORM**

- **Why**: TypeScript-first, thin, SQL-shaped, with fully typed queries and a transparent migration story (`drizzle-kit`). You see the SQL you run — important when reasoning about locking and concurrency in the renewal sweep. Low magic = predictable behavior in a money system.
- **Alternative**: Prisma — excellent DX and the most popular choice; viable if the team prefers its schema language and tooling. We lean Drizzle for finer control over raw SQL (locking hints, partial indexes) that billing concurrency needs, but Prisma is a defensible second choice.

### Payment gateway & card vault — **Stripe**

- **Why**: This is the keystone decision. Stripe is PCI-DSS Level 1; using Stripe Elements/Checkout + Setup Intents means raw PAN/CVV never hit our servers, collapsing our PCI scope to the lightweight **SAQ A**. Stripe also natively provides much of CAP-02..06: `PaymentIntents` (idempotent charges), `SetupIntents` (stored payment-method tokens), `Customer` objects, `Invoices`, and **Smart Retries** for dunning. We orchestrate and mirror, not reimplement.
- **Build vs. buy nuance**: Stripe *Billing* (its subscriptions product) can manage plans, proration, the billing cycle, invoices, and retries for you. Given the team size, **lean heavily on Stripe Billing** and let our `subscriptions`/`billing-cycle`/`dunning` modules be thin orchestration + entitlement-mirroring layers driven by webhooks. Only hand-roll the parts where product rules diverge from Stripe's defaults.
- **Alternative**: Adyen / Braintree (capable but heavier integration), or a billing platform like Chargebee/Recurly layered on a PSP (more turnkey subscription logic, recurring SaaS fee, less control). For a TS team that wants control and the best docs/DX, Stripe is the clear pick.

### Background jobs & scheduling — **BullMQ on Redis**

- **Why**: The daily renewal sweep (CAP-04), delayed retries (CAP-06), and async invoice rendering/email need durable, scheduled, retryable jobs. BullMQ is the mature TypeScript-native queue: delayed jobs (perfect for "retry in 3/7/14 days"), repeatable/cron jobs (the daily sweep), automatic retwith backoff, and concurrency control — all in-process-compatible with our Node workers. Redis is also our cache/rate-limit store, so no new dependency.
- **Alternative**: pg-boss (queue *inside* Postgres — removes Redis entirely, attractive for minimizing infra at this scale; viable and worth considering if you want one fewer system). Cloud-native (SQS + EventBridge Scheduler) — works but pulls logic into provider-specific config and away from the typed codebase. BullMQ is the sweet spot of power and TS ergonomics; pg-boss is the "one less moving part" alternative.

### Email / notifications — **Resend (transactional) + React Email templates**

- **Why**: CAP-05 (invoice delivery) and CAP-06 (dunning sequence, recovery, exhaustion notices) need reliable transactional email with good deliverability. Resend is TypeScript-native and pairs with React Email so templates live in our codebase as typed components. Note: if leaning on Stripe Billing, Stripe can send many of these emails itself — choose one owner per email type to avoid duplicates.
- **Alternative**: Postmark (best-in-class transactional deliverability/reputation) or AWS SES (cheapest at scale, more setup). Any is fine; Resend wins on DX for a TS team.

### Invoice PDF generation — **Stripe-hosted invoices first; React-PDF / Puppeteer if custom**

- **Why**: Stripe generates and hosts compliant invoice PDFs automatically. Use those to start — zero rendering code. Only if branding/format requirements exceed Stripe's templates, render in-house with React-PDF (declarative, pure-TS, runs in a worker) or Puppeteer (HTML→PDF, heavier). Keep custom rendering on the async worker path (CAP-05), never inline in a request.

### Hosting / deployment — **Containerized app on a managed platform (Railway / Render / Fly.io), Postgres + Redis managed**

- **Why**: A 4-person team should not run Kubernetes. A managed container platform gives push-to-deploy, autoscaling, managed Postgres + Redis add-ons, and secret management with near-zero ops. Run two process types from one image: a **web** process (Next.js + API + webhooks) and a **worker** process (BullMQ consumers + the scheduler). Scale them independently.
- **Alternative**: AWS ECS Fargate + RDS + ElastiCache — more control and a clearer enterprise/compliance story, but materially more setup and operational surface. Choose it later if procurement/compliance demands AWS; start lighter.

### Observability — **Sentry (errors) + structured logs (pino) + platform metrics; OpenTelemetry-ready**

- **Why**: In billing, a silently failed renewal job or a swallowed webhook is a revenue incident. Sentry captures exceptions with context; pino emits structured JSON logs (correlate by `idempotency_key` / `subscription_id`); the hosting platform supplies basic metrics/alerts. Instrument with OpenTelemetry from day one so you can add a tracing backend later without re-instrumenting. Add **alerts on: webhook processing failures, renewal-sweep job failures, retry-exhaustion spikes, and payment-decline-rate anomalies.**
- **Alternative**: Datadog (one-stop, excellent, pricier) — adopt when you outgrow the basics.

### Auth — **reuse the existing user-account system; add a billing-portal session**

- **Why**: The capability breakdown states a user-account system already exists. Do not build a second identity system. The billing app authenticates portal users via the existing system (OIDC/JWT or shared session) and authorizes admin-only actions (immediate cancel, manual retry) via a role claim. If a standalone auth is ever needed, **Auth.js (NextAuth)** fits the Next.js stack.

### Stack summary

| Layer | Choice | Top alternative |
|-------|--------|-----------------|
| Language/runtime | TypeScript / Node.js 22 LTS | Bun |
| App shell + UI | Next.js (App Router) + Stripe Elements | React SPA + Fastify/NestJS |
| API style | REST/HTTPS | GraphQL (not needed) |
| Database | PostgreSQL 16 (managed) | MySQL/PlanetScale |
| Data access | Drizzle ORM | Prisma |
| Payments + vault | Stripe (lean on Stripe Billing) | Adyen/Braintree, Chargebee/Recurly |
| Jobs/scheduling | BullMQ + Redis | pg-boss (Postgres-only) |
| Email | Resend + React Email | Postmark / SES |
| Invoice PDF | Stripe-hosted → React-PDF | Puppeteer |
| Hosting | Railway/Render/Fly.io (containers) | AWS ECS Fargate |
| Observability | Sentry + pino + OTel | Datadog |
| Auth | Existing account system / Auth.js | — |

---

## 4. Data Model (core entities)

Mirrors the capability breakdown's stored outputs. Money is integer minor units; all rows carry `created_at`/`updated_at`; provider IDs are stored for reconciliation.

- **plan** — `id, code, name, price_cents, currency, billing_interval, features(jsonb), is_active, stripe_price_id`
- **subscription** — `id, user_id, plan_id, status(active|past_due|cancelled|expired|paused), current_period_start, current_period_end, cancel_at_period_end(bool), pending_plan_id(nullable), stripe_subscription_id, stripe_customer_id`
- **transaction** — `id, user_id, subscription_id, amount_cents, currency, status(success|declined|error|pending), decline_reason, stripe_payment_intent_id, idempotency_key(unique), created_at`
- **invoice** — `id, user_id, subscription_id, transaction_id, invoice_number(unique, configurable sequence), period_start, period_end, line_items(jsonb), subtotal_cents, tax_cents, total_cents, status(open|paid|void|credited), stripe_invoice_id, pdf_url`
- **credit_note** — `id, invoice_id, amount_cents, reason, created_at` (handles post-invoice refunds, CAP-05 edge case)
- **retry_schedule** — `id, subscription_id, transaction_id, attempt_number, scheduled_at, status(scheduled|succeeded|failed|cancelled)` (CAP-06)
- **payment_method** — store only the Stripe token reference: `id, user_id, stripe_payment_method_id, brand, last4, exp, is_default` (never raw PAN)
- **event_outbox** — `id, type, payload(jsonb), processed_at` (internal event bus + reliable async dispatch)
- **webhook_event** — `id, stripe_event_id(unique), type, payload, processed_at` (idempotent webhook ingestion)

Key indexes: partial unique on `transaction.idempotency_key`; index on `subscription(status, current_period_end)` for the renewal sweep; unique on `webhook_event.stripe_event_id` for dedupe.

---

## 5. How the Architecture Realizes Each Capability

| Cap | Realization |
|-----|-------------|
| **CAP-01 Plan selection** | `catalog` + `checkout` modules. Plans served from Postgres (cached in Redis; cached copy satisfies the "catalog unavailable" error path). Proration preview comes from Stripe's upcoming-invoice API. Upgrades route to synchronous payment; downgrades set `pending_plan_id` to apply at period end. |
| **CAP-02 Payment processing** | `payments` module orchestrates a Stripe **PaymentIntent** with a caller-supplied **idempotency key** (satisfies the duplicate-charge edge case natively). Stored payment methods used for recurring charges. Gateway-unreachable retries handled by BullMQ backoff (3 attempts). Zero-amount charges short-circuit. Success emits `payment.succeeded`; failure emits `payment.failed` → dunning. |
| **CAP-03 Subscription lifecycle** | `subscriptions` module is an explicit **state machine** (activate/upgrade/downgrade/cancel/reactivate/expire) with guarded transitions that reject illegal actions (e.g. upgrade on a cancelled sub) inside a DB transaction. Cancel sets `cancel_at_period_end`; downgrade defers; reactivate within period preserves the period end. Emits lifecycle + billing + invoice events. |
| **CAP-04 Billing cycle** | A BullMQ **repeatable (daily cron) job** sweeps `subscription WHERE status='active' AND current_period_end <= today` using `FOR UPDATE SKIP LOCKED` for safe concurrency. Idempotency check on last-billed date prevents double-billing. Success extends the period; failure starts grace period; grace expiry signals lifecycle to suspend. Missed-run catch-up is automatic since the query is date-based, not tick-based. |
| **CAP-05 Invoice generation** | `invoices` module triggered by `payment.succeeded` / lifecycle / renewal events via the outbox. Uses Stripe-hosted invoices by default; sequential numbering with configurable fiscal-year reset for custom invoices. Async PDF render + Resend email on the worker. Refunds create a `credit_note`; failed transactions produce no invoice. |
| **CAP-06 Payment retry / dunning** | `dunning` module. On `payment.failed`, schedule **delayed BullMQ jobs** at the configured intervals (3/7/14 days), creating `retry_schedule` rows and sending dunning emails. Lean on Stripe **Smart Retries** where possible. Payment-method update resets the schedule and retries immediately; method removal cancels pending retries; exhaustion signals lifecycle to suspend; admin manual retry resets the counter. |

---

## 6. Cross-Cutting Concerns

### Idempotency & exactly-once-effects (the central correctness requirement)
- Every outbound charge carries a deterministic **idempotency key** (e.g. `sub:{id}:period:{period_end}`), stored uniquely in `transaction`. Stripe deduplicates on the same key.
- **Webhook dedupe**: `webhook_event.stripe_event_id` unique constraint; process each event at most once.
- **Outbox pattern**: domain state changes and the events that announce them commit in the same DB transaction; a dispatcher publishes from the outbox to BullMQ at-least-once. Consumers are idempotent.
- The renewal sweep is safe to run twice (date-based query + last-billed guard + `SKIP LOCKED`).

### Security & compliance
- **PCI scope = SAQ A** by construction: card data captured by Stripe Elements/Checkout in the browser, tokenized; our servers store only Stripe references. This is the single biggest risk reduction available and the reason Stripe is non-negotiable.
- Verify Stripe webhook **signatures**; reject unsigned/replayed events.
- Secrets via the platform secret manager; never in the repo. TLS everywhere. Least-privilege DB roles. Audit-log every admin money action (force-cancel, manual retry, refund).
- **Revenue recognition (ASC 606)** flagged for research — see below — invoice timing and refund handling must align with the accounting system reconciliation.

### Reliability
- Two independently scalable processes (web, worker) from one image. Stateless web; workers idempotent.
- Managed Postgres with PITR backups; Redis as cache/queue is non-authoritative (rebuildable). Stripe is the money source of truth, so a Redis loss never loses money.
- Dead-letter handling on BullMQ for poison jobs; alert on DLQ depth.

### Scale (year-one and headroom)
- A few thousand customers ⇒ a few thousand renewals/month, trivially handled by a single Postgres primary and one worker. Headroom is large: add worker concurrency, then a read replica, long before any re-architecture. The modular boundaries leave a clean path to extract a service (most likely `dunning` or `invoices`) if a specific load hotspot ever emerges.

### Testing
- Unit-test the lifecycle state machine and proration math exhaustively (pure functions, no I/O).
- Integration-test against **Stripe test mode** and the **Stripe CLI** for webhook replay.
- Contract-test webhook handlers with recorded fixtures. Use **Stripe test clocks** to simulate billing-cycle advancement and dunning timelines deterministically.

---

## 7. Build vs. Buy Summary

| Concern | Decision | Rationale |
|---------|----------|-----------|
| Card vault / PCI | **Buy (Stripe)** | Removes PCI Level-1 burden; collapses scope to SAQ A. |
| Charge processing, stored methods, retries | **Buy (Stripe PaymentIntents/SetupIntents/Smart Retries)** | Battle-tested, idempotent, less code. |
| Subscription/plan/proration/invoice engine | **Mostly buy (Stripe Billing), thin orchestration in-house** | 4-person team; mirror entitlements, don't reimplement billing math. |
| Lifecycle product rules, entitlements, portal UX | **Build** | This is the product's differentiation and where rules diverge from Stripe defaults. |
| Scheduling/dunning orchestration | **Build (BullMQ) layered over Stripe** | Custom retry cadence and notification ownership. |
| Email delivery | **Buy (Resend/Stripe)** | Commodity; deliverability is hard to self-host. |
| Identity | **Reuse existing account system** | Already exists per the breakdown. |

---

## 8. Open Technical Questions

- **Stripe Billing vs. custom billing engine split**: exactly which of CAP-03/04/05 rules diverge from Stripe defaults enough to justify in-house logic? Resolve before sprint 1 — it determines how thin the modules are.
- **Redis vs. Postgres-only queue (pg-boss)**: if minimizing infrastructure is paramount, pg-boss removes Redis entirely at this scale. Decide based on whether Redis earns its keep as a cache too.
- **Multiple active subscriptions per user** (open question from the capability breakdown) changes the `subscription`↔`user` cardinality and Stripe Customer modeling — confirm before finalizing the schema.
- **Invoice numbering authority**: Stripe-generated vs. our own sequence — must be settled with finance/accounting for ASC 606 and audit continuity.

## 9. Research Suggestions (flag to researcher skill — not resolved here)

- **ASC 606 revenue recognition for SaaS billing** — invoice timing, proration, and refund handling that satisfies the accounting/ERP reconciliation. High-stakes/compliance.
- **Optimal dunning cadence** — retry intervals and email sequencing that maximize recovery vs. gateway cost and churn; compare against Stripe Smart Retries defaults.
- **Proration strategy** — fairest, most legible mid-cycle upgrade/downgrade proration model and how it maps to Stripe's proration behavior.

## 10. Next Steps

1. Stand up the Stripe account (test mode), define Products/Prices mirroring the plan catalog, and prototype Elements checkout to confirm SAQ-A flow.
2. Decide the Stripe Billing vs. custom-engine boundary (Open Question #1); write the lifecycle state-machine spec.
3. Scaffold the modular monolith (Next.js + Drizzle + Postgres + BullMQ), the two process types, and the webhook ingestion path with signature verification and dedupe.
4. Implement CAP-02 + CAP-01 happy path end-to-end (selection → PaymentIntent → activation → invoice) with idempotency and Stripe test-clock integration tests before building dunning.

---
*Technical architecture produced for a 4-person TypeScript team at few-thousand-customer scale. Built on the subscription-billing capability breakdown (CAP-01..06). Use the librarian skill to persist this artifact.*
