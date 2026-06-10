# Telehealth Appointment-Booking System — Technical Architecture

> Technical Architect | Depth: standard | Generated: 2026-06-10

## Source Breakdown

No capability breakdown artifact was retrieved — the librarian skill is unavailable in this run. The capabilities below were provided **inline** by the user as a five-item list. They are treated as the fixed foundation; no capabilities were invented or expanded. Running the solution-architect skill first would produce CAP-NN IDs, acceptance criteria, and edge cases that would sharpen this architecture (e.g., async messaging needs, no-show/reschedule flows, refund rules).

Capabilities (inline, named here for mapping):
- **CAP-01 Patient registration** — patient identity, demographics, account creation, consent capture.
- **CAP-02 Provider scheduling** — provider availability, appointment slots, booking/reschedule/cancel.
- **CAP-03 Video visits** — real-time audio/video consultations between patient and provider.
- **CAP-04 Prescriptions** — provider-issued prescriptions / e-prescribing record.
- **CAP-05 Billing** — charges, payment capture, insurance/claims data, invoicing.

> An agent with librarian access should retrieve: **specs** matching `"telehealth appointment booking patient registration provider scheduling video visit prescription billing"`, scope `project`, to confirm these capabilities against a formal breakdown before build.

## Constraints & Assumptions

- **Scale & load**: ~50k–200k registered patients, low-thousands of concurrent users at peak clinic hours, dozens-to-low-hundreds of concurrent video sessions. Standard business-hours-weighted traffic, not millions of users. **[assumed]**
- **Team**: Team knows **Python** **[stated]**. Team size and frontend skill assumed small-to-mid (5–15 engineers), web-first **[assumed]**.
- **Hosting**: **AWS only — no other cloud** **[stated]**. Prefer AWS managed, BAA-eligible services throughout.
- **Hard constraints**:
  - **HIPAA compliance required** **[stated]** — PHI is pervasive (every capability touches PHI). Requires: AWS BAA signed; only BAA-eligible services used; encryption at rest and in transit; least-privilege access control; comprehensive audit logging; data retention/disposal controls.
  - **AWS-only** **[stated]** — no GCP/Azure/non-AWS SaaS for PHI paths unless the vendor signs a BAA (relevant for video and e-prescribing, below).
  - **Python backend** **[stated]**.
- **Existing systems**: None stated. Assume greenfield, but billing and prescriptions will need external integrations (payment processor, e-prescribing network) that themselves must be HIPAA-appropriate. **[assumed]**

## Architecture Overview

- **Style**: **Modular monolith** (Python) deployed on AWS ECS Fargate, with **selective serverless/managed offload** for media (video), async work, and notifications — *not* full microservices. Rationale: five cohesive capabilities at moderate scale, a Python team, and HIPAA's preference for a smaller, more auditable attack/access surface all favor one well-structured deployable over a fleet of services. Split out only what has a genuinely different runtime profile (video media, async jobs).
- **Shape**: A React web client and provider portal talk over HTTPS to a Python (FastAPI) API behind an Application Load Balancer in private subnets. The API is internally modularized by capability (registration, scheduling, prescriptions, billing) sharing an Amazon Aurora PostgreSQL database with strict row/role access. **Video visits** are handled by a HIPAA-eligible managed real-time service (**Amazon Chime SDK**, BAA-eligible) — the backend only mints session tokens and stores metadata, never the media stream. Asynchronous work (notifications, claim submission, audit fan-out) flows through Amazon SQS/EventBridge to Python workers. All PHI is encrypted with KMS-managed keys at rest and TLS 1.2+ in transit; every PHI access is audit-logged.

## Tech Stack

### Frontend
- **Recommendation**: **React (TypeScript) SPA** for the patient app and provider portal, built with Vite, served as static assets from **S3 + CloudFront**. Use a component library (e.g. Radix/Chakra) for accessible forms (registration, scheduling). Integrate the **Amazon Chime SDK React components** for the video-visit UI.
- **Why**: Registration (CAP-01) and scheduling (CAP-02) are form- and state-heavy; video (CAP-03) needs a mature client SDK — Chime SDK ships first-class JS/React libraries. CloudFront stays inside AWS and is BAA-eligible. TypeScript adds safety on PHI-handling forms.
- **Alternatives**: **Next.js (SSR)** if SEO/marketing pages and the app share a codebase, or you want server components for faster first paint — heavier to operate. **Two separate apps** (patient vs. provider) if the provider portal grows materially different; start unified.

### Backend / API
- **Recommendation**: **Python + FastAPI**, packaged as a modular monolith with clear internal module boundaries per capability; **Pydantic** for request/response validation, **SQLAlchemy 2.x** for data access. Containerized and run on ECS Fargate.
- **Why**: Team knows Python **[stated]**. FastAPI gives async I/O (useful for Chime token minting, payment/claims calls), automatic OpenAPI docs, and strong validation — valuable when every payload may carry PHI. A modular monolith keeps the HIPAA audit/access surface small and deployment simple at this scale.
- **Alternatives**: **Django + DRF** if you want batteries-included admin, ORM, and auth and value convention over speed — heavier and more synchronous. **Microservices** only if/when a capability needs independent scaling or a separate compliance boundary (e.g., billing isolating cardholder data) — premature now.

### Data storage
- **Primary database**: **Amazon Aurora PostgreSQL (Serverless v2 or provisioned)**, encrypted with KMS. Relational, transactional integrity across patients, providers, appointments, prescriptions, and invoices; foreign keys and constraints matter for clinical/financial correctness. Aurora is BAA-eligible, supports encryption at rest, automated backups, and PITR. *Why over alternatives*: DynamoDB is BAA-eligible and scales further but the access patterns here are relational and transactional (booking conflicts, billing reconciliation) — Postgres fits. **Alternative**: RDS PostgreSQL (single-instance) for lower cost if Aurora's HA/scaling isn't needed yet.
- **Cache / session**: **Amazon ElastiCache for Redis** (encryption in transit + at rest, BAA-eligible) for provider-availability lookups, slot-locking during booking, and rate limiting. **Alternative**: skip initially and add when read pressure appears.
- **Object/blob store**: **Amazon S3** (SSE-KMS, bucket policies, VPC endpoints) for consent PDFs, uploaded documents, and prescription artifacts. Do **not** store video recordings unless a capability explicitly requires it (none stated — flagged in Open Questions).
- **Search/analytics**: **Not needed now** — query volumes are modest and relational; defer OpenSearch/analytics warehouse until a reporting capability is added (would be a new capability → solution-architect).

### Async / messaging
- **Recommendation**: **Amazon SQS** for work queues (appointment reminders, claim submission, post-visit billing) and **Amazon EventBridge** for domain events (`AppointmentBooked`, `VisitCompleted`, `PrescriptionIssued`) consumed by Python workers on Fargate (or Lambda for light tasks). **Step Functions** for multi-step billing/claims workflows if they grow.
- **Why**: Reminders (scheduling), claim submission (billing), and audit fan-out should not block the request path or fail the user transaction. Decoupling via SQS/EventBridge gives retries and durability — important when a dropped billing event has financial/compliance impact. All BAA-eligible.
- **Note**: Keep PHI out of message bodies where possible — pass record IDs and let workers fetch from the DB under their own least-privilege role, reducing PHI sprawl across services.

### Authentication & authorization
- **Recommendation**: **Amazon Cognito** user pools for patient and provider identity (separate pools or groups), with MFA for providers; short-lived JWTs validated at the API. **Role-based access control** in the application layer (patient, provider, billing-admin, super-admin) plus **record-level authorization** (a provider sees only their patients; a patient sees only their own data) enforced in the data-access layer.
- **Why**: HIPAA requires strong access control and unique user identification. Cognito is BAA-eligible, managed, and integrates with ALB/API. Record-level checks are essential — RBAC alone is insufficient for PHI minimum-necessary access.
- **Alternatives**: **Auth0/Okta** are more feature-rich and offer BAAs but add a non-AWS dependency — against the AWS-only preference. **Self-managed auth** — avoid; rolling your own identity under HIPAA is unnecessary risk.

### Infrastructure & hosting
- **Recommendation**: **ECS Fargate** for API and workers in a **multi-AZ VPC**: public subnets for ALB only, **private subnets** for compute and data, NAT for egress, **VPC endpoints** (S3, KMS, Secrets Manager, SQS) so PHI traffic stays off the public internet. WAF on the ALB/CloudFront. Multi-AZ Aurora and ElastiCache for availability.
- **Why**: Fargate removes host-patching burden (a HIPAA win) while running standard Python containers. Private subnets + VPC endpoints enforce network isolation of PHI. Multi-AZ meets reasonable availability for clinical scheduling.
- **Alternatives**: **EKS (Kubernetes)** if you already have k8s expertise or expect many services — operational overkill here. **AWS App Runner** for the simplest container hosting — less network control, weaker fit for strict VPC isolation. **Lambda-first** for the whole API — possible with FastAPI via adapters, but cold starts and execution limits make it a poorer fit than Fargate for a stateful-ish API.

### CI/CD & developer tooling
- **Recommendation**: **GitHub Actions** (or AWS CodePipeline/CodeBuild to stay fully in-AWS) building Docker images to **Amazon ECR**, deploying to Fargate via blue/green (CodeDeploy). **Infrastructure as Code with Terraform** (or AWS CDK in Python — aligns with the team's language). Separate **dev / staging / prod** accounts via AWS Organizations; PHI only in controlled environments with synthetic data in lower envs.
- **Why**: IaC makes the HIPAA control posture reviewable and reproducible; CDK in Python keeps tooling in the team's language. Account separation is a strong HIPAA isolation practice.
- **Alternatives**: **CodePipeline end-to-end** if you want zero non-AWS CI dependency; **GitHub Actions** if developer experience and ecosystem matter more.

### Observability
- **Recommendation**: **Amazon CloudWatch** (logs, metrics, alarms) + **AWS X-Ray** for tracing across API → workers → DB. **Structured JSON logging** with PHI scrubbed from logs (log record IDs, never names/diagnoses). **Dedicated, immutable audit log** (see Security) separate from operational logs.
- **Why**: HIPAA requires monitoring and the ability to detect/investigate access. CloudWatch/X-Ray are BAA-eligible and native. Crucially, operational logs must not become an uncontrolled PHI store — scrubbing is a design requirement, not an afterthought.
- **Alternatives**: **Datadog/Grafana Cloud** are stronger products and offer BAAs, but add non-AWS dependencies — defer unless CloudWatch proves limiting.

### Third-party services & integrations
- **Video (CAP-03)**: **Amazon Chime SDK** — BAA-eligible, AWS-native real-time media; backend mints attendee tokens, media never transits your servers. (See AD-02.)
- **Billing/payments (CAP-05)**: A payment processor for card capture. **Stripe** (offers a BAA; but card data + PHI proximity warrants care) or **AWS-adjacent** options. Keep cardholder data out of your DB — tokenize via the processor (reduces PCI scope). Insurance/claims (837/835 EDI) typically goes through a **clearinghouse** that signs a BAA.
- **Prescriptions (CAP-04)**: E-prescribing to pharmacies in the US generally requires certified networks (**Surescripts**) via an integration partner; controlled substances require **EPCS**. There is no AWS-native e-prescribing service — this needs a BAA-covered third party. (Flagged for research.)
- **Email/SMS notifications**: **Amazon SES** (email) and **Amazon SNS / Amazon Pinpoint** (SMS) for appointment confirmations/reminders — BAA-eligible; keep PHI out of message content (e.g., "You have an appointment" without diagnosis).

### Security
PHI is pervasive — security is a first-class layer here, not a footnote. Controls mapped to HIPAA:
- **AWS BAA**: Sign the AWS Business Associate Addendum; restrict architecture to BAA-eligible services (all services chosen above qualify).
- **Encryption in transit**: TLS 1.2+ everywhere (CloudFront, ALB, internal service calls, DB connections). Enforce HTTPS-only; HSTS.
- **Encryption at rest**: **KMS customer-managed keys** for Aurora, S3 (SSE-KMS), ElastiCache, EBS, SQS, and backups. Key rotation enabled.
- **Access control**: Cognito MFA for providers/admins; least-privilege **IAM roles** per service/worker; application RBAC + record-level authorization enforcing HIPAA minimum-necessary access. No shared/standing admin credentials — use IAM Identity Center + short-lived sessions.
- **Audit logging**: **CloudTrail** (API-level, log-file validation on, delivered to a locked S3 bucket in a separate logging account) plus an **application-level PHI access audit trail** (who accessed which patient record, when, why) written to an append-only store (e.g., dedicated Aurora table or S3 Object Lock). This is a HIPAA requirement, not optional.
- **Secrets**: **AWS Secrets Manager** (DB creds, third-party API keys) with rotation; no secrets in code/env files.
- **Network isolation**: Private subnets, security groups, VPC endpoints, WAF, GuardDuty + Security Hub for threat detection and posture monitoring.
- **Data lifecycle**: Defined retention and secure disposal for PHI; backups encrypted and access-controlled; lower environments use synthetic data only.

## Capability → Tech Mapping

| Capability | Implemented by | Notes |
|-----------|----------------|-------|
| CAP-01 Patient registration | React forms → FastAPI registration module → Aurora; Cognito for identity; S3 (SSE-KMS) for consent docs | PHI from first contact; record-level auth + audit log from day one |
| CAP-02 Provider scheduling | FastAPI scheduling module → Aurora; Redis for slot-locking/availability cache; SQS + SES/SNS for reminders | Slot-locking in Redis prevents double-booking; reminders async so they don't block booking |
| CAP-03 Video visits | Amazon Chime SDK (BAA-eligible); FastAPI mints attendee tokens; Aurora stores visit metadata only | Media never transits app servers; recordings out of scope unless a capability requires it |
| CAP-04 Prescriptions | FastAPI prescriptions module → Aurora; integration with certified e-prescribing partner (Surescripts via vendor); EventBridge `PrescriptionIssued` | No AWS-native e-prescribing; needs BAA third party; EPCS for controlled substances — research-flagged |
| CAP-05 Billing | FastAPI billing module → Aurora; payment processor (tokenized, BAA); SQS/Step Functions for claim submission to clearinghouse; EventBridge `VisitCompleted` triggers billing | Keep card data tokenized off-platform to limit PCI scope; claims via BAA clearinghouse |

## Key Architecture Decisions

### AD-01: Modular monolith on Fargate, not microservices

- **Decision**: Build one modularized Python (FastAPI) deployable on ECS Fargate, splitting out only video media and async workers.
- **Context**: Five cohesive capabilities, moderate scale **[assumed]**, a Python team **[stated]**, and HIPAA's preference for a small, auditable access surface.
- **Rationale**: Microservices multiply the number of PHI-handling boundaries, IAM roles, network paths, and audit points to secure — cost without benefit at this scale. A modular monolith keeps the compliance surface small and the team productive, while still allowing later extraction (e.g., billing) along module seams.
- **Tradeoffs**: Shared database and deployable mean a bad change can affect all capabilities; mitigated by module boundaries, tests, and blue/green deploys. Independent scaling per capability isn't available until extracted.

### AD-02: Amazon Chime SDK for video visits

- **Decision**: Use Amazon Chime SDK for real-time video (CAP-03); backend mints session/attendee tokens and never proxies media.
- **Context**: AWS-only **[stated]** and HIPAA **[stated]**; video must be HIPAA-eligible and ideally AWS-native.
- **Rationale**: Chime SDK is BAA-eligible, AWS-native (no other-cloud dependency), and provides client SDKs and server APIs for token minting, sidestepping the build/operate cost and compliance risk of self-hosting WebRTC. Twilio Video (a common choice) was avoided because it is non-AWS — against the stated constraint.
- **Tradeoffs**: Vendor lock-in to Chime's feature set and pricing model; fewer turnkey features than specialist video vendors. Recording, if ever needed, requires explicit configuration and PHI-grade storage.

### AD-03: Aurora PostgreSQL as the single source of truth for PHI

- **Decision**: Use Aurora PostgreSQL (KMS-encrypted, multi-AZ) as the primary transactional store for all capabilities.
- **Context**: Relational, transactional data (bookings, prescriptions, invoices) with strong integrity needs; HIPAA encryption/backup requirements.
- **Rationale**: Relational integrity and ACID transactions fit booking-conflict and billing-reconciliation logic better than NoSQL; Aurora is BAA-eligible with encryption, PITR, and multi-AZ HA. Centralizing PHI in one controlled store simplifies access control and audit.
- **Tradeoffs**: A single relational store can become a scaling chokepoint at very high write volume; not expected at this scale, and Aurora Serverless v2 / read replicas provide headroom.

### AD-04: PHI minimization across logs, queues, and lower environments

- **Decision**: Pass record IDs (not PHI) through queues/events; scrub PHI from operational logs; use synthetic data in non-prod.
- **Context**: HIPAA minimum-necessary and breach-surface reduction across an async, observable system.
- **Rationale**: Every place PHI lands is a place that must be secured and audited. Keeping PHI out of message bodies, logs, and lower environments shrinks the compliance surface dramatically.
- **Tradeoffs**: Slightly more DB lookups in workers and less convenient debugging; acceptable for the compliance benefit.

## Risks & Tradeoffs

- **E-prescribing has no AWS-native path (CAP-04)** — requires a certified third party (e.g., Surescripts via an integration vendor) with a BAA, plus EPCS for controlled substances. This is the highest-uncertainty integration; cost, certification, and timeline are non-trivial. *Mitigation*: validate the vendor and EPCS requirements early (research-flagged) before committing the prescriptions module design.
- **PHI + payment data proximity (CAP-05)** — combining cardholder data with PHI raises both PCI and HIPAA scope. *Mitigation*: tokenize card data via the processor, never store PAN; route claims through a BAA clearinghouse.
- **AWS-only constrains best-of-breed choices** — Chime SDK and SES/SNS are solid but less feature-rich than specialist vendors (Twilio, Datadog). *Mitigation*: accept for compliance/simplicity; revisit per-capability only if a real gap appears, requiring a vendor BAA.
- **Audit logging completeness** — missing PHI-access audit trails is a direct HIPAA gap. *Mitigation*: treat the application-level audit log as a first-class, append-only feature built into the data-access layer, not bolted on later.
- **Single shared database blast radius** — a schema or query bug can affect all capabilities. *Mitigation*: module boundaries, migrations review, automated tests, blue/green deploys.

## Research Suggestions

High-stakes / uncertain choices to validate with the researcher skill (researcher is unavailable this run — queries provided ready to use):

- **HIPAA-compliant e-prescribing integration (CAP-04)** — no AWS-native option; certification-heavy. Suggested researcher query: *"What are the options and requirements for integrating HIPAA-compliant e-prescribing (including EPCS for controlled substances) into a US telehealth platform — Surescripts certification path, integration vendors that sign BAAs, costs, and timelines as of 2026?"*
- **HIPAA video stack: Amazon Chime SDK vs. alternatives** — confirm Chime SDK BAA coverage, feature limits, and whether any AWS-only constraint exception (e.g., Twilio with BAA) is warranted. Suggested researcher query: *"Compare Amazon Chime SDK against Twilio Video and Vonage for HIPAA-compliant telehealth video visits — BAA coverage, recording with PHI-grade storage, latency, client SDK maturity, and pricing."*
- **AWS HIPAA architecture reference & BAA-eligible service list** — verify every chosen service is currently BAA-eligible. Suggested researcher query: *"Current AWS HIPAA-eligible services list and AWS reference architecture for HIPAA telehealth workloads (Aurora, Cognito, Chime SDK, SQS, SES/SNS, CloudTrail) as of 2026."*
- **Billing/claims clearinghouse with BAA** — payment + insurance claims path under HIPAA. Suggested researcher query: *"HIPAA-compliant payment processors and EDI 837/835 clearinghouses that sign BAAs for US telehealth billing, and how to minimize combined PCI + HIPAA scope."*

## Open Questions

- **Are video visits recorded?** No capability states recording. If required, it adds PHI-grade media storage (S3 SSE-KMS + Object Lock), consent, and retention rules — confirm with solution-architect rather than assuming.
- **Real scale and concurrency targets** — concurrent video sessions and peak booking load drive Fargate/Aurora sizing and cost; current figures are assumed.
- **US-only vs. multi-region/state licensing** — affects data residency and provider-licensing logic (a potential new capability for solution-architect).
- **Insurance/claims depth** — is CAP-05 full claims adjudication (837/835 EDI) or card payment only? Changes the billing integration substantially.
- **Identity proofing / KYC for patients** — does CAP-01 require verified identity (e.g., for controlled-substance prescribing)? This is a functional question for solution-architect.

## Next Steps

1. Sign the **AWS BAA** and lock the build to the BAA-eligible service set; stand up multi-account AWS Organizations (dev/staging/prod + logging) via IaC.
2. Spike the **Amazon Chime SDK** video flow (token minting + React client) end-to-end to confirm it meets clinical UX needs (AD-02).
3. Run the **e-prescribing research** (CAP-04) and select a BAA-covered integration partner before finalizing the prescriptions module — highest-risk dependency.
4. Build the **FastAPI modular-monolith skeleton** with Cognito auth, record-level authorization, and the append-only PHI audit log as foundational cross-cutting concerns.
5. Stand up Aurora (KMS), Secrets Manager, VPC with private subnets + endpoints, and CloudTrail-to-locked-bucket as the security baseline before feature work.
6. (Recommended) Run **solution-architect** to formalize the five capabilities into CAP-NN with acceptance criteria, then revisit this architecture against it.

---
*Technical architecture produced by technical-architect skill. Use the librarian skill to persist this artifact.*
