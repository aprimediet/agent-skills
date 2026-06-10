# Telehealth Appointment-Booking System — Technical Architecture

> Technical Architect | Depth: standard | Generated: 2026-06-10

## Source Breakdown

No formal capability breakdown (e.g., from the solution-architect skill) was available — the librarian skill is not accessible in this session. The capabilities below were taken **directly from the user's prompt** and not invented. Running the solution-architect skill first would produce sharper capability definitions (especially around prescription workflows and billing edge cases), which would in turn tighten this architecture.

Capabilities anchored from the prompt:

- **CAP-01 Patient registration** — patient sign-up, identity/profile, demographics, insurance details.
- **CAP-02 Provider scheduling** — provider availability, appointment slots, booking/rescheduling/cancellation.
- **CAP-03 Video visits** — real-time audio/video consultation between patient and provider.
- **CAP-04 Prescriptions** — provider issuing prescriptions, e-prescribing to pharmacies.
- **CAP-05 Billing** — charges, insurance claims, patient payments.

## Constraints & Assumptions

- **Scale & load**: **[assumed]** A regional-to-national telehealth service: low tens of thousands of registered patients, hundreds of concurrent video visits at peak, traffic concentrated in business hours. Not internet-scale (no millions of concurrent). Availability target **[assumed]** 99.9% for booking/registration; video visits tolerate brief degradation but PHI must never be lost.
- **Team**: **[stated]** Team knows **Python**. **[assumed]** Small-to-medium team (5–15 engineers), comfortable with managed services over bespoke infra.
- **Hosting**: **[stated]** **AWS-only** shop — no other cloud. Recommendations stay within AWS managed, **HIPAA-eligible** (BAA-covered) services wherever reasonable.
- **Hard constraints**: **[stated]** **HIPAA compliance** is mandatory — encryption at rest and in transit, access controls, audit logging, and a signed **AWS BAA** covering every service that touches PHI. **[stated]** AWS-only, Python backend. **[assumed]** Reasonable startup/SMB budget — favor serverless/managed to minimize ops headcount, but accept higher per-unit cost than raw EC2.
- **Existing systems**: **[assumed]** Greenfield, but must integrate with external **e-prescribing** (Surescripts-connected vendor) and a **payment/claims** path. No legacy EHR specified; assume optional future EHR/FHIR integration.

## Architecture Overview

- **Style**: **Modular monolith (Python) on AWS managed compute, with selected serverless/event-driven seams.** A single well-structured Python service (modules: registration, scheduling, prescriptions, billing) keeps a small team productive and keeps PHI flows easy to audit in one place; async and third-party-heavy work (notifications, claim submission, video-event handling) is pushed to event-driven Lambda/SQS seams. Video is **not** built in-house — it is delegated to a HIPAA-eligible managed real-time service.
- **Shape**: Patients and providers use a web (and optionally mobile) client behind CloudFront + WAF, hitting an API Gateway / ALB front door into a containerized Python API (ECS Fargate). The API owns the core domain modules and persists PHI to an encrypted Amazon RDS (PostgreSQL) database, with objects/documents in encrypted S3. Real-time video visits run on **Amazon Chime SDK** (HIPAA-eligible), with the backend issuing session tokens and recording metadata. Asynchronous and integration work — appointment reminders, prescription transmission to the e-prescribing vendor, billing/claim submission, and audit fan-out — flows through SQS/EventBridge to Lambda workers. All PHI-touching services are BAA-covered, encrypted with KMS CMKs, and audit-logged to CloudTrail + a dedicated immutable log store.

## Tech Stack

### Frontend
- **Recommendation**: **React (TypeScript) SPA**, served via **S3 + CloudFront** with **AWS WAF**. Patient and provider portals as one app with role-gated routes; video UI built on the **Amazon Chime SDK React components**.
- **Why**: React has the deepest talent pool and the best-supported Chime SDK client library, which directly serves CAP-03 (video visits). CloudFront + WAF gives TLS termination, DDoS protection, and geo/rate controls in front of PHI surfaces. Static hosting keeps the frontend cheap and isolated from the PHI backend.
- **Alternatives**: **Next.js (SSR)** — prefer if SEO/marketing pages and the app share a codebase, or you want server components; runs on Amplify Hosting or ECS. **Flutter / React Native** — prefer if a first-class native mobile app is a near-term requirement (Chime SDK has mobile SDKs).

### Backend / API
- **Recommendation**: **Python + FastAPI**, containerized on **ECS Fargate** behind an **Application Load Balancer** (or API Gateway HTTP API). Modular monolith: distinct internal packages for registration, scheduling, prescriptions, billing; shared auth/audit middleware.
- **Why**: Matches the **[stated]** Python skill. FastAPI gives typed request/response models (Pydantic) — valuable for the structured medical/insurance data in CAP-01/04/05 — plus async I/O for calling Chime, e-prescribing, and payment APIs. Fargate is HIPAA-eligible, removes server management, and scales per-service without managing EC2 hosts.
- **Alternatives**: **Django + DRF** — prefer if the team wants batteries-included admin, ORM, and migrations out of the box (strong fit for provider/patient admin screens). **Lambda + API Gateway (full serverless)** — prefer at lower/spikier traffic to cut idle cost, but cold starts and per-request PHI-handling auditing are easier to reason about in a long-lived container; revisit if traffic is very bursty.

### Data storage
- **Primary database — Recommendation**: **Amazon RDS for PostgreSQL** (Multi-AZ), encrypted at rest with a **KMS customer-managed key**. Holds patients, providers, availability, appointments, prescriptions metadata, billing records.
  - **Why**: The domain is highly relational and transactional — booking a slot, issuing a prescription tied to a visit, and creating a billing record all need ACID guarantees and referential integrity (CAP-02/04/05). RDS is HIPAA-eligible, Multi-AZ gives the availability target, and PostgreSQL handles structured + JSONB (insurance payloads, FHIR fragments) well.
  - **Alternatives**: **Amazon Aurora PostgreSQL** — prefer for higher availability/throughput headroom and faster failover as scale grows (drop-in upgrade path). **DynamoDB** — only for narrow high-write, simple-access-pattern tables (e.g., session/token state); wrong fit for the relational core.
- **Object/document store — Recommendation**: **Amazon S3**, SSE-KMS encrypted, bucket policies enforcing TLS and blocking public access. Stores uploaded ID/insurance documents, generated PDFs (visit summaries, receipts), and any visit recordings.
  - **Why**: Cheap, durable, HIPAA-eligible, integrates with KMS and CloudTrail data events for audit of PHI object access.
- **Cache — Recommendation**: **Amazon ElastiCache for Redis** (encryption in transit + at rest) for provider availability lookups and session/rate-limit state.
  - **Why**: Scheduling reads (CAP-02) are read-heavy and benefit from caching computed availability; keeps RDS load down. Omit initially if traffic is low and add when read latency justifies it.

### Async / messaging
- **Recommendation**: **Amazon SQS** (work queues) + **Amazon EventBridge** (domain events) with **AWS Lambda** workers (Python). Used for: appointment reminders/notifications, prescription transmission to the e-prescribing vendor, billing/claim submission and retries, and audit-event fan-out.
- **Why**: These are exactly the operations that must not block a user request and that need retries/dead-letter handling — transmitting a prescription (CAP-04) or submitting a claim (CAP-05) involves slow third parties that can fail. Decoupling via SQS gives durability and backpressure; EventBridge lets billing/notifications react to domain events (e.g., "visit.completed") without coupling modules.
- **Not needed**: Heavy streaming (Kinesis/Kafka) — there is no high-volume event stream here; SQS/EventBridge are sufficient. State so explicitly to avoid over-engineering.

### Authentication & authorization
- **Recommendation**: **Amazon Cognito** user pools for patient and provider identity (email/phone + **MFA**), federated where needed; **fine-grained RBAC enforced in the FastAPI layer** (roles: patient, provider, billing-staff, admin). JWT access tokens, short-lived, validated at the API edge.
- **Why**: Cognito is HIPAA-eligible, handles registration/sign-in flows for CAP-01, MFA (a HIPAA-relevant access control), and password policies without building auth from scratch. RBAC in the app enforces minimum-necessary access to PHI — providers see their patients, billing staff see billing data, etc.
- **Alternatives**: **Auth0/Okta** — richer identity features and easier B2B/SSO, but adds a non-AWS vendor that needs its own BAA; acceptable but fights the AWS-only preference. **Self-managed (Authlib + RDS)** — prefer only if you need full control of the identity store; more security surface to own and audit.

### Infrastructure & hosting
- **Recommendation**: **ECS Fargate** for the API, **Lambda** for async workers, all inside a **VPC** with private subnets for compute/data, public subnets only for ALB/NAT. **CloudFront + WAF + Shield** at the edge. Secrets in **AWS Secrets Manager**, config in **SSM Parameter Store**. Multi-AZ across at least two AZs in one region; **[assumed]** single region (US) unless data-residency/DR requires more.
- **Why**: Private-subnet isolation of PHI data stores is a baseline HIPAA network control. Fargate+Lambda minimizes ops for a small team. WAF/Shield protect public PHI endpoints. Single region keeps cost and compliance scope contained; add cross-region backup/DR for RPO/RTO needs.
- **Alternatives**: **EKS (Kubernetes)** — prefer only if the team already runs Kubernetes or needs multi-service orchestration at larger scale; otherwise it adds operational and audit burden a small team shouldn't take on. **Elastic Beanstalk** — simpler than Fargate but less control over networking/compliance posture.

### CI/CD & developer tooling
- **Recommendation**: **GitHub (or CodeCommit) + GitHub Actions / CodePipeline + CodeBuild**, deploying via **AWS CDK or Terraform** (IaC). Separate **dev / staging / prod** AWS accounts under **AWS Organizations**, with prod PHI isolated. Image scanning (ECR scan / Trivy), dependency scanning, and `pytest` gates in the pipeline.
- **Why**: IaC makes the HIPAA control set (encryption, private subnets, logging) reproducible and auditable — security posture lives in version control. Account-per-environment limits blast radius and keeps PHI out of dev/test. Python team → `pytest`-centric pipeline.
- **Alternatives**: **Terraform** over CDK if the team prefers HCL / multi-cloud-portable IaC (though AWS-only here makes CDK's Python support a natural fit with the team's language).

### Observability
- **Recommendation**: **Amazon CloudWatch** (logs, metrics, alarms) + **AWS X-Ray** (tracing) + **CloudTrail** (API/management + S3/KMS data events). Structured JSON logging from the Python app with **PHI scrubbing** before emission. Dashboards and alarms on error rates, video session failures, and queue depth/DLQ.
- **Why**: CloudWatch/X-Ray are native and HIPAA-eligible. The critical HIPAA-specific requirement — **audit logging of PHI access** — is met by CloudTrail data events plus application-level access logs. Logs must never contain raw PHI, hence scrubbing.
- **Alternatives**: **Datadog / New Relic** — richer APM and dashboards, but require a vendor BAA and careful config to avoid PHI leaving AWS; defer unless CloudWatch proves insufficient.

### Third-party services & integrations
- **Video (CAP-03) — Amazon Chime SDK**: HIPAA-eligible managed WebRTC. Backend creates meetings/attendees and issues join tokens; optional recording to encrypted S3. This is the recommended **HIPAA-eligible video approach** — do not build custom WebRTC/SFU infrastructure.
- **E-prescribing (CAP-04)**: integrate a **Surescripts-connected e-prescribing vendor** (e.g., DoseSpot, Dr. First) over their API from a Lambda worker. Prescribing controlled substances (EPCS) carries extra identity-proofing/2FA requirements — vendor-handled, flagged below.
- **Notifications**: **Amazon SES** (email) and **Amazon SNS / Pinpoint** (SMS) for appointment reminders/confirmations — all BAA-covered; keep PHI out of message bodies (link to portal instead).
- **Payments/billing (CAP-05)**: payment processing via a **PCI-compliant processor (e.g., Stripe)** so card data never touches your servers; insurance **claims** via a clearinghouse or the e-prescribing/billing vendor. Both need their own BAA where they touch PHI.

### Security
- **Recommendation**:
  - **Encryption in transit**: TLS 1.2+ everywhere (CloudFront, ALB, RDS, Redis, S3); enforce via policies.
  - **Encryption at rest**: KMS **customer-managed keys** for RDS, S3, EBS, ElastiCache, SQS, Secrets Manager; key rotation enabled.
  - **Access control**: least-privilege IAM roles per service; Cognito + app RBAC for users; MFA for providers/staff; private subnets for data tier.
  - **Audit logging**: CloudTrail (incl. S3/KMS data events) to a dedicated, **immutable (Object Lock) log bucket** in a separate logging account; application access logs for PHI reads/writes.
  - **Secrets**: AWS Secrets Manager with rotation; no secrets in code or env files.
  - **Compliance program**: signed **AWS BAA**; **AWS Config + Security Hub + GuardDuty** for continuous compliance monitoring; documented breach-notification and access-review processes.
- **Why**: These map directly to the HIPAA Security Rule's technical safeguards (access control, audit controls, integrity, transmission security). Using only BAA-eligible services and CMK encryption is the baseline that makes the whole system defensible.

## Capability → Tech Mapping

| Capability | Implemented by | Notes |
|-----------|----------------|-------|
| CAP-01 Patient registration | React portal → FastAPI registration module → RDS PostgreSQL; Cognito for identity/MFA; S3 (SSE-KMS) for ID/insurance docs | PHI from first touch — TLS + KMS + audit logging apply immediately. |
| CAP-02 Provider scheduling | FastAPI scheduling module → RDS (transactional slot booking); ElastiCache for availability reads; EventBridge emits `appointment.booked` | ACID booking prevents double-booking; cache optional until read load grows. |
| CAP-03 Video visits | Amazon Chime SDK (HIPAA-eligible WebRTC); FastAPI issues meeting/attendee tokens; optional recording → S3 (SSE-KMS) | Managed, BAA-covered. Do not build custom WebRTC. |
| CAP-04 Prescriptions | FastAPI prescriptions module → RDS metadata; Lambda worker → Surescripts-connected e-prescribing vendor via SQS | Controlled substances (EPCS) add identity-proofing/2FA — vendor-handled; see research flag. |
| CAP-05 Billing | FastAPI billing module → RDS; Lambda workers via SQS for payment processor (Stripe) and claims clearinghouse; EventBridge `visit.completed` triggers charge | Card data offloaded to PCI processor; claims path needs vendor BAA. |

## Key Architecture Decisions

### AD-01: Modular monolith in Python on Fargate, not microservices

- **Decision**: Build the core domain as one modular Python (FastAPI) service on ECS Fargate, with async/integration seams split into Lambda workers.
- **Context**: Small Python team; five tightly-related capabilities sharing patient/provider data; HIPAA requires auditable, well-understood PHI flows.
- **Rationale**: A monolith keeps transactions (booking → prescription → billing) and PHI handling in one auditable place and is far cheaper to operate and certify than a microservices fleet. Async seams isolate slow/failure-prone third parties without fragmenting the domain.
- **Tradeoffs**: Less independent scaling per capability; mitigated by horizontal Fargate scaling and offloading bursty work to Lambda. Revisit decomposition only if a capability develops a genuinely independent scaling or team-ownership profile.

### AD-02: Amazon Chime SDK for video, not self-hosted WebRTC

- **Decision**: Use Amazon Chime SDK for all real-time video (CAP-03).
- **Context**: Video is the highest-risk capability technically and for compliance; self-hosting WebRTC/SFU is complex and must itself be HIPAA-compliant.
- **Rationale**: Chime SDK is HIPAA-eligible (BAA-covered), AWS-native (satisfies AWS-only), scales media handling for us, and has first-class React/mobile client SDKs. Building media infrastructure would consume the team and expand compliance scope.
- **Tradeoffs**: Vendor lock-in to Chime and per-minute media cost; acceptable versus the cost and risk of owning real-time media + its compliance.

### AD-03: RDS PostgreSQL (Multi-AZ, CMK-encrypted) as the system of record

- **Decision**: Single relational system of record on RDS PostgreSQL, Multi-AZ, KMS CMK.
- **Context**: Strongly relational, transactional domain with PHI and availability requirements.
- **Rationale**: ACID integrity across booking/prescription/billing; HIPAA-eligible with encryption and Multi-AZ failover; PostgreSQL JSONB absorbs semi-structured insurance/FHIR data. Clear upgrade path to Aurora.
- **Tradeoffs**: A relational DB needs schema discipline and managed scaling; far outweighed by integrity needs. DynamoDB reserved for narrow non-relational cases only.

### AD-04: All PHI on BAA-eligible AWS services with CMK encryption and immutable audit logs

- **Decision**: Restrict every PHI-touching component to AWS HIPAA-eligible services, encrypt with customer-managed KMS keys, and centralize CloudTrail logs in an immutable (Object Lock) bucket in a separate account.
- **Context**: HIPAA Security Rule technical safeguards are mandatory and the user is AWS-only.
- **Rationale**: Using only BAA-covered services keeps PHI within the signed BAA; CMKs give key control/rotation; immutable centralized logs satisfy audit-control and integrity requirements and resist tampering.
- **Tradeoffs**: Constrains service choices (e.g., a non-eligible AWS service can't touch PHI) and adds KMS/logging cost and key-management overhead; non-negotiable for compliance.

## Risks & Tradeoffs

- **PHI leakage into logs/telemetry** — the most common HIPAA slip. Mitigation: structured logging with explicit PHI scrubbing, no PHI in URLs/SMS/email bodies, and review of X-Ray/CloudWatch payloads.
- **EPCS (controlled substances) complexity** — e-prescribing controlled substances has strict federal identity-proofing/2FA rules beyond ordinary prescriptions. Mitigation: lean on a certified vendor; scope EPCS as a distinct workstream. Flagged for research.
- **Chime SDK lock-in and media cost** — switching video providers later is non-trivial. Mitigation: keep video token issuance and recording behind an internal interface so the provider can be swapped.
- **Billing/claims correctness** — insurance claim submission and reconciliation are error-prone and capability-ambiguous in the prompt. Mitigation: idempotent SQS workers with DLQs and retries; and run solution-architect to nail down billing rules before building.
- **Single-region availability/DR** — a regional outage affects everything. Mitigation: Multi-AZ now; add cross-region encrypted backups and a documented DR plan with defined RPO/RTO.
- **Cost of fully-managed/serverless** — managed services trade per-unit cost for low ops. Acceptable for a small team; monitor with budgets/alarms and revisit hot paths.

## Research Suggestions

High-stakes or uncertain choices to validate with the researcher skill:

- **HIPAA-eligible AWS service list & BAA scope (2026)** — the set of BAA-eligible services changes; every PHI-touching choice here (Chime SDK, Cognito, SES/SNS/Pinpoint, X-Ray) must be confirmed currently eligible. Suggested query: *"Which AWS services are HIPAA-eligible under the AWS BAA as of 2026, specifically Amazon Chime SDK, Cognito, SES, SNS, Pinpoint, X-Ray, and ElastiCache for Redis? Cite the official AWS HIPAA-eligible services reference."*
- **EPCS / controlled-substance e-prescribing requirements** — federal identity-proofing and 2FA rules for e-prescribing controlled substances drive vendor and workflow choices. Suggested query: *"What are the current DEA EPCS requirements for electronic prescribing of controlled substances in a telehealth product, and which Surescripts-connected vendors (DoseSpot, DrFirst) handle identity proofing and two-factor for prescribers?"*
- **Telehealth video compliance specifics** — confirm Chime SDK configuration (recording, data handling, regional residency) meets HIPAA for clinical video. Suggested query: *"Best practices and configuration requirements for using Amazon Chime SDK for HIPAA-compliant clinical telehealth video, including recording storage and PHI handling."*
- **Payment + claims path** — confirm the boundary between PCI scope (Stripe) and PHI/claims clearinghouse, and BAA needs. Suggested query: *"Architecture for separating PCI-DSS card processing (Stripe) from HIPAA insurance-claims submission in a US telehealth platform — what needs a BAA vs. PCI attestation, and which clearinghouse integration patterns are standard?"*

## Open Questions

- What is the realistic peak of **concurrent video visits**? It sizes Chime usage and Fargate capacity and is currently assumed.
- Is a **native mobile app** required at launch, or is responsive web sufficient? It changes the frontend choice (React SPA vs. React Native/Flutter).
- Must the system **integrate with an external EHR/FHIR** system now, or later? It affects the data model and an integration layer.
- What are the **DR requirements (RPO/RTO)** and is multi-region needed for data residency or resilience?
- Are **controlled substances** in scope for prescribing (triggers EPCS), or non-controlled only?
- These are functional/scope questions best resolved by the **solution-architect skill** before build, since they shape capabilities, not just technology.

## Next Steps

1. Run the **solution-architect skill** to firm up the billing, prescription (EPCS?), and EHR-integration capabilities, then revisit this architecture's mapping.
2. Sign the **AWS BAA** and stand up the **AWS Organizations** account structure (dev/staging/prod + separate logging account) with baseline guardrails (Config, Security Hub, GuardDuty, CloudTrail to immutable bucket) via IaC.
3. **Spike Amazon Chime SDK** end-to-end (token issuance from FastAPI → React join → optional encrypted recording) to validate the video approach and cost.
4. Spike the **e-prescribing vendor** integration (incl. EPCS path) and the **payment/claims** boundary to de-risk the third-party-heavy capabilities.
5. Scaffold the **FastAPI modular monolith** + RDS schema + CDK infra, with PHI-scrubbing logging and RBAC middleware in place from day one.
6. Hand off the high-stakes items above to the **researcher skill** using the provided queries before committing to vendors.

---
*Technical architecture produced by technical-architect skill. Use the librarian skill to persist this artifact.*
