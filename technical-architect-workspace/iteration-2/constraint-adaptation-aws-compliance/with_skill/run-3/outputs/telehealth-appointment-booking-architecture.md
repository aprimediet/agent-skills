# Telehealth Appointment-Booking System — Technical Architecture

> Technical Architect | Depth: standard | Generated: 2026-06-10

## Source Breakdown

No librarian skill was available, so the capability breakdown was provided inline in the task prompt. Capabilities are anchored to the five listed; none were invented. Running the solution-architect skill first would produce a more granular CAP-NN breakdown (e.g. sub-capabilities under billing and scheduling), which would sharpen the capability→tech mapping below.

Capabilities (as stated):
- **Patient registration** — patient sign-up, identity, demographic + insurance profile.
- **Provider scheduling** — provider availability, slots, patient booking against those slots.
- **Video visits** — real-time audio/video consultation between patient and provider.
- **Prescriptions** — provider creates/transmits prescriptions tied to a visit.
- **Billing** — charges, insurance/claims context, payment capture.

## Constraints & Assumptions

- **Scale & load**: Mid-size telehealth practice — low tens of thousands of registered patients, hundreds of concurrent video visits at peak, spiky around business hours. Booking/registration are low-QPS; video is the bandwidth/latency-sensitive path. **[assumed]**
- **Team**: Team knows Python. **[stated]** Team size and frontend/mobile experience not stated; assume a small-to-mid backend-Python team with web frontend capability, no deep WebRTC/media-server expertise. **[assumed]**
- **Hosting**: AWS only — AWS managed services, no other cloud. **[stated]**
- **Hard constraints**: HIPAA compliance is mandatory — all PHI-handling services must be BAA-eligible, with encryption at rest and in transit, least-privilege access controls, and audit logging. **[stated]** Video visits require a HIPAA-eligible real-time media approach. **[stated, derived]** Budget not stated; assume cost-conscious but compliance is non-negotiable. **[assumed]**
- **Existing systems**: None stated. Assume greenfield, but prescriptions and billing will integrate with external regulated systems (e-prescribing network, payment processor, optionally claims/EHR). **[assumed]**

> HIPAA note: A signed AWS Business Associate Addendum (BAA) is required, and **only AWS HIPAA-eligible services may touch PHI**. Every service named below for a PHI path is HIPAA-eligible as of the knowledge cutoff; this list must be re-verified against the current AWS HIPAA-eligible services page before build (see Research Suggestions).

## Architecture Overview

- **Style**: **Modular monolith (Python) on serverless-friendly AWS managed services, with a separate managed video plane.** A single deployable Python application with clear internal module boundaries (registration, scheduling, prescriptions, billing) over a shared transactional database, plus a distinct real-time video subsystem that the app only orchestrates. This matches a Python team and modest scale without microservices overhead, while keeping module seams so high-divergence domains (billing, video) can be peeled off later. Microservices are not justified at this scale and would multiply the HIPAA audit surface.
- **Shape**: A web/mobile client talks to a Python API behind API Gateway / ALB. The API serves registration, scheduling, prescriptions, and billing from one codebase against an encrypted Postgres (RDS/Aurora) primary, with object storage for documents and a cache/queue for async work (notifications, claim submission, e-prescription transmission). **Video visits run on a managed WebRTC service (Amazon Chime SDK)** — the Python backend creates meeting/attendee tokens and the clients connect peer-to-media directly, so heavy media never transits the app servers. All PHI flows stay inside HIPAA-eligible services within a private VPC, fronted by audit logging (CloudTrail) and centralized access control (IAM + Cognito).

## Tech Stack

### Frontend
- **Recommendation**: **React (TypeScript) single-page web app**, served via S3 + CloudFront, integrating the **Amazon Chime SDK for JavaScript** for the video visit experience. A React Native or thin mobile wrapper can follow using the same APIs and the Chime SDK mobile clients.
- **Why**: Video visits need a mature, well-supported client SDK; Chime SDK's first-class JS client makes React the path of least resistance and keeps a single web codebase covering registration, booking, and the visit UI. CloudFront gives HIPAA-eligible TLS edge delivery.
- **Alternatives**: **Server-rendered Python (Django templates / HTMX)** — prefer if the team has zero JS appetite and video is the only rich-client need (you'd still drop to the Chime JS SDK for the call screen). **Flutter / React Native-first** — prefer if mobile is the primary channel rather than web.

### Backend / API
- **Recommendation**: **FastAPI (Python 3.12) as a modular monolith**, packaged as a container on **ECS Fargate** behind an Application Load Balancer (or API Gateway for managed authz/throttling). Internal modules: `registration`, `scheduling`, `prescriptions`, `billing`, plus a `video` orchestration module that brokers Chime sessions.
- **Why**: Directly honors the Python constraint. FastAPI gives typed request/response models (Pydantic) — valuable for PHI schemas and validation — async I/O for fan-out to external systems (e-prescribe, payments), and OpenAPI for free. Fargate avoids EC2 patching burden (lighter HIPAA hardening surface) while still being a long-lived service suited to WebSocket/notification needs and predictable latency.
- **Alternatives**: **Django + DRF** — prefer if the team wants batteries-included admin, ORM, and auth and is comfortable trading some async ergonomics; the built-in admin is genuinely useful for ops/support staff. **AWS Lambda (Python) + API Gateway (fully serverless)** — prefer if traffic is very spiky and the team wants zero server management; weigh cold-start latency on the booking path and the operational awkwardness of long-lived/orchestration logic.

### Data storage
- **Primary database — Recommendation**: **Amazon Aurora PostgreSQL (Serverless v2)**, encrypted at rest with KMS. Holds patients, providers, availability/slots, appointments, prescription records (metadata + status, not the controlled transmission itself), and billing/charge records.
  - **Why**: The domain is highly relational and transactional — booking a slot must be atomic to prevent double-booking, and billing needs consistency. Postgres gives strong constraints, row-level locking for slot reservation, and JSONB for flexible profile/insurance fields. Aurora is HIPAA-eligible, auto-scales (Serverless v2) for spiky load, and gives automated encrypted backups + Multi-AZ.
  - **Alternatives**: **Amazon RDS for PostgreSQL** — prefer for lower baseline cost and simpler mental model if you don't need Aurora's autoscaling/replica speed. **DynamoDB** — only for narrow high-write sub-domains (e.g. audit/event logs); avoid as the primary store given the relational, transactional booking/billing core.
- **Object/document store — Recommendation**: **Amazon S3** (KMS-encrypted, versioned, private with bucket policies + VPC endpoint) for registration documents (insurance cards, IDs), visit artifacts, and signed prescription PDFs.
  - **Why**: PHI documents need durable, encrypted, access-logged storage; S3 is HIPAA-eligible and integrates with KMS, access logging, and Object Lock for retention.
  - **Alternatives**: **EFS** — only if a workload needs POSIX file semantics (none here).
- **Cache — Recommendation**: **Amazon ElastiCache for Redis** (encryption in transit + at rest) for session/lookup caching and short-lived slot-hold locks during booking.
  - **Why**: Reduces DB contention on the read-heavy availability views and supports a TTL-based "slot held while patient confirms" pattern.
  - **Alternatives**: Skip initially and rely on Postgres advisory locks if traffic is low — prefer if you want to defer a moving part; revisit when booking contention appears.

### Async / messaging
- **Recommendation**: **Amazon SQS** for reliable background jobs (appointment reminders, claim submission, e-prescription transmission retries) plus **Amazon SNS / EventBridge** for fan-out events (e.g. "appointment booked" → notify + schedule reminder). Workers run as separate Fargate tasks or Lambda consumers sharing the Python codebase.
- **Why**: Prescriptions and billing involve calls to slow, sometimes-flaky external regulated systems; doing these inline would couple booking latency and reliability to third parties. Queues give retries, dead-letter handling, and decoupling. EventBridge scheduling cleanly handles "remind 24h before visit."
- **Not over-built**: No Kafka/MSK — event volume doesn't justify a streaming platform; SQS/SNS/EventBridge are sufficient and lower-ops.

### Authentication & authorization
- **Recommendation**: **Amazon Cognito** user pools for patient and provider identity (separate pools or groups), issuing OIDC/JWT tokens; **application-level RBAC** in the FastAPI layer distinguishing patient / provider / billing-staff / admin roles, enforced per endpoint and at the data-access layer (a patient may only read their own records; a provider only their panel). MFA enabled for providers and staff.
- **Why**: Cognito is HIPAA-eligible, removes the burden of building credential storage, and supports MFA and federation. Role checks in-app give the fine-grained, record-scoped authorization HIPAA's minimum-necessary principle requires — coarse IAM cannot express "this provider, this patient."
- **Alternatives**: **Auth0/Okta** — prefer if you need richer enterprise SSO/identity features and have a BAA with them; adds a non-AWS vendor (violates AWS-only unless explicitly excepted), so default to Cognito. **Self-managed auth in the app** — avoid; reinventing credential/MFA handling increases HIPAA risk.

### Infrastructure & hosting
- **Recommendation**: **VPC with private subnets** for all compute and data; **ECS Fargate** for the API and workers; **ALB + API Gateway** at the edge; **Aurora/RDS, ElastiCache, S3** reached via VPC endpoints so PHI never traverses the public internet internally. NAT only where outbound to external regulated systems is needed. Multi-AZ for the DB; multiple Fargate AZs for the API. **Amazon Chime SDK** provides the managed media plane (see Security/video).
- **Why**: Network isolation + private endpoints are core HIPAA technical safeguards. Fargate keeps the host-patching/hardening burden on AWS. Multi-AZ meets reasonable availability without multi-region complexity at this scale.
- **Alternatives**: **EKS (Kubernetes)** — prefer only if the org already standardizes on K8s; otherwise it adds operational and audit surface unjustified here. **Full Lambda** — see Backend alternatives.

### CI/CD & developer tooling
- **Recommendation**: **GitHub Actions (or AWS CodePipeline/CodeBuild) → ECR → ECS Fargate**, with **infrastructure as code in Terraform (or AWS CDK in Python)**. Separate `dev` / `staging` / `prod` AWS accounts (AWS Organizations) so PHI in prod is isolated and de-identified/synthetic data is used in lower environments. Automated tests (pytest), dependency/container scanning (e.g. ECR scanning, `pip-audit`), and IaC policy checks in the pipeline.
- **Why**: Account-level environment isolation is the cleanest way to keep PHI out of dev/test and to scope BAA-covered resources. CDK-in-Python keeps IaC in the team's language; Terraform if multi-cloud-portability or existing skills favor it. Image scanning is a HIPAA-relevant control.
- **Alternatives**: **CodePipeline end-to-end** — prefer if you want everything inside AWS for a tighter compliance boundary and fewer external vendors.

### Observability
- **Recommendation**: **Amazon CloudWatch** (logs, metrics, alarms) + **AWS X-Ray** (tracing) + **CloudTrail** (API/audit trail, mandatory). Structured JSON logging from FastAPI with **PHI scrubbing/redaction** before logs leave the app. Centralize logs to a dedicated, access-restricted log account/bucket with retention and Object Lock.
- **Why**: CloudTrail provides the immutable audit logging HIPAA requires for access to PHI-handling resources. CloudWatch/X-Ray cover operational health and latency on the booking and video-orchestration paths. The critical control is ensuring application logs never capture PHI in the clear.
- **Alternatives**: **Datadog/Grafana** — prefer for richer dashboards if a BAA is in place and AWS-only is relaxed; default to native CloudWatch to stay within the constraint.

### Third-party services & integrations
- **Prescriptions / e-prescribing — Recommendation**: integrate a **certified e-prescribing / Surescripts-connected vendor (e.g. DoseSpot, Photon, or similar)** via API from the `prescriptions` module, behind an SQS-backed worker with retries. The system stores prescription metadata and status; controlled-substance e-prescribing (EPCS) flows through the certified vendor.
  - **Why**: E-prescribing to pharmacies is a regulated network (Surescripts) with certification and EPCS requirements you should not build yourself. **Flagged for research** — vendor choice is high-stakes (see below).
- **Billing / payments — Recommendation**: **Stripe (with HIPAA considerations)** or a healthcare-oriented processor for card capture, plus a path to **claims/clearinghouse** integration (e.g. a clearinghouse API) if insurance billing is in scope.
  - **Why**: Keep card data (PCI) and claims out of your own systems via tokenization. Note: payment card data is PCI, not strictly PHI, but the linkage to a patient makes handling sensitive — keep PANs off your servers entirely (tokenized). **Flagged for research** — whether real insurance claim adjudication is in scope materially changes this layer; the prompt lists "billing" without specifying claims depth (Open Question).
- **Notifications — Recommendation**: **Amazon SES** (email) and **Amazon SNS / Pinpoint** (SMS) for appointment confirmations and reminders — HIPAA-eligible, but reminder content must be PHI-minimized (no diagnoses; generic "you have an appointment").
- **Video — Recommendation**: **Amazon Chime SDK** (detailed under Security).

### Security
- **Encryption in transit**: TLS 1.2+ everywhere — CloudFront/ALB, API, DB connections (force SSL on Aurora), Redis in-transit encryption, S3 TLS-only bucket policy. Chime SDK media is DTLS-SRTP encrypted end-to-transport.
- **Encryption at rest**: **AWS KMS** customer-managed keys (CMKs) for Aurora, S3, ElastiCache, EBS, and SQS/SNS message encryption. Per-domain key separation where practical; key rotation enabled.
- **Access controls**: Least-privilege **IAM** roles per service/task; **Cognito** for end-user identity; **application RBAC + record-level scoping** for minimum-necessary access; MFA for providers/staff/admins; **Secrets Manager** for DB creds and third-party API keys (auto-rotation).
- **Audit logging**: **CloudTrail** (immutable, to a locked log account), plus application-level access logs recording who-viewed-which-patient, stored separately and tamper-resistant (S3 Object Lock). This who-accessed-what trail is a HIPAA must.
- **Network**: Private subnets, VPC endpoints for AWS services, security groups + NACLs, WAF on the public edge, GuardDuty + AWS Config for continuous compliance monitoring.
- **Video visits — HIPAA-eligible approach (explicit)**: Use the **Amazon Chime SDK** — a HIPAA-eligible managed WebRTC service. The Python backend uses the AWS SDK (boto3) to create a **meeting** and per-participant **attendee** tokens; clients join directly to Chime's media plane, so PHI media never passes through your application servers (reduced surface). Media is encrypted in transit (DTLS-SRTP). **Disable/secure recording by default**; if visit recording is required, write to a KMS-encrypted S3 bucket with strict access controls and retention — and confirm it's a stated capability (it is *not* in the listed five, so treat recording as out of scope until confirmed — Open Question). Ensure the AWS BAA explicitly covers Chime SDK.
  - **Alternatives**: **Twilio Video** or **Vonage/Daily** — mature WebRTC platforms that offer BAAs; prefer if you need advanced features (large group rooms, advanced recording/transcription) Chime lacks — but each is a non-AWS vendor requiring its own BAA and breaking AWS-only, so Chime is the default given the constraint.

## Capability → Tech Mapping

| Capability | Implemented by | Notes |
|-----------|----------------|-------|
| Patient registration | FastAPI `registration` module · Cognito (patient pool) · Aurora PostgreSQL · S3 (KMS) for ID/insurance docs | Demographics + insurance in Postgres (JSONB for flexible fields); documents in encrypted S3; identity in Cognito. PHI-handling, all HIPAA-eligible. |
| Provider scheduling | FastAPI `scheduling` module · Aurora PostgreSQL (slots/appointments) · ElastiCache Redis (slot holds) · EventBridge + SQS + SES/SNS (reminders) | Atomic booking via Postgres row locks / Redis TTL holds to prevent double-booking; reminders via EventBridge schedule → SQS → SES/SNS with PHI-minimized content. |
| Video visits | Amazon Chime SDK · FastAPI `video` module (boto3 token broker) · React + Chime JS SDK client | HIPAA-eligible managed WebRTC; backend mints meeting/attendee tokens, media bypasses app servers, DTLS-SRTP encrypted. Recording off by default. |
| Prescriptions | FastAPI `prescriptions` module · certified e-prescribing vendor (Surescripts-connected) · SQS worker (retries) · Aurora (metadata/status) · S3 (signed PDFs) | App stores metadata/status; transmission + EPCS handled by certified vendor. Vendor choice flagged for research. |
| Billing | FastAPI `billing` module · Aurora (charges/records) · Stripe or healthcare processor (tokenized cards) · optional clearinghouse API · SQS worker | Card data tokenized off-server (PCI); claims/clearinghouse depth depends on scope (Open Question). |

## Key Architecture Decisions

### AD-01: Modular monolith over microservices

- **Decision**: Build one Python (FastAPI) deployable with strong internal module boundaries rather than per-capability microservices.
- **Context**: Small Python team, modest scale, five cohesive capabilities sharing patient/appointment data, and a HIPAA audit surface that grows with every separately deployed service.
- **Rationale**: Shared transactional data (booking ↔ billing ↔ visit) is easiest to keep consistent in one DB and codebase; fewer services mean a smaller compliance/networking footprint and faster delivery for a small team. Module seams preserve the option to extract billing or video later.
- **Tradeoffs**: Less independent scaling/deploy isolation; a bad deploy affects all capabilities. Mitigated by module boundaries, the separate video plane (Chime), and separate worker tasks for async.

### AD-02: Amazon Chime SDK for video visits

- **Decision**: Use Amazon Chime SDK as the HIPAA-eligible managed WebRTC plane; backend only brokers session tokens.
- **Context**: AWS-only + HIPAA + a team without WebRTC/media-server expertise; video is the most latency- and compliance-sensitive path.
- **Rationale**: Keeps media off application servers (shrinks PHI surface), stays within AWS (BAA-coverable), and avoids operating SFUs/TURN servers. Encrypted media in transit by default.
- **Tradeoffs**: Vendor lock-in to Chime; fewer advanced features (recording/transcription) than Twilio/Vonage. Acceptable given the AWS-only constraint and listed capabilities.

### AD-03: Aurora PostgreSQL as the transactional core

- **Decision**: Single encrypted relational primary (Aurora PostgreSQL Serverless v2) for registration, scheduling, prescriptions, billing.
- **Context**: Relational, transactional domain with double-booking and billing-consistency requirements; spiky load; HIPAA encryption/backup needs.
- **Rationale**: Strong constraints + locking for atomic booking, JSONB for flexible profile/insurance data, HIPAA-eligible with KMS encryption, Multi-AZ, automated encrypted backups, and autoscaling for spiky traffic.
- **Tradeoffs**: Single store can become a scaling chokepoint; mitigated by read replicas, ElastiCache, and offloading high-write logs to DynamoDB if needed.

### AD-04: Account-level environment isolation for PHI

- **Decision**: Separate AWS accounts for prod/staging/dev under AWS Organizations; only prod holds real PHI; lower envs use synthetic data.
- **Context**: HIPAA minimum-necessary + breach-blast-radius reduction; need to scope BAA-covered resources.
- **Rationale**: Hard isolation of PHI is simpler and more defensible than IAM-only separation within one account; keeps developers away from real patient data.
- **Tradeoffs**: More IaC/CI/CD complexity and cross-account plumbing; justified by the compliance posture.

## Risks & Tradeoffs

- **PHI leakage into logs/observability**: Structured logging and tracing can accidentally capture PHI. Mitigation: redaction middleware in FastAPI, log review, and never logging request bodies for PHI endpoints.
- **HIPAA-eligibility drift**: The set of AWS HIPAA-eligible services changes; a service assumed eligible may not be, or config (e.g. unencrypted backup) may break eligibility. Mitigation: verify against the current AWS HIPAA-eligible services list pre-build and gate via AWS Config rules.
- **Double-booking under concurrency**: Two patients booking the same slot. Mitigation: DB-level unique constraints + row locks and/or Redis TTL holds; never rely on read-then-write without a lock.
- **Third-party reliability (e-prescribe, claims, payments)**: External regulated systems are slow/flaky. Mitigation: async SQS workers, retries, DLQs, idempotency keys; never inline on the booking path.
- **Chime feature ceiling**: If recording, large group visits, or transcription become real requirements, Chime may not suffice and a re-platform to Twilio/Vonage (with its own BAA) could be needed. Mitigation: keep the `video` module's interface abstract.
- **Billing scope ambiguity**: "Billing" may mean simple card capture or full insurance claim adjudication — vastly different builds. Mitigation: resolve before committing the billing/clearinghouse stack (Open Question).

## Research Suggestions

High-stakes / compliance-sensitive choices to validate with the researcher skill:

- **Current AWS HIPAA-eligible services + BAA scope** — confirm Chime SDK, Aurora Serverless v2, Cognito, SES, SNS/Pinpoint, ElastiCache, and Fargate are all currently HIPAA-eligible and covered by the AWS BAA. Suggested researcher query: *"As of 2026, which AWS services are HIPAA-eligible under the AWS BAA, and is the Amazon Chime SDK (including media and any recording) covered? Note any configuration requirements for eligibility."*
- **HIPAA-eligible video for telehealth** — validate Chime SDK vs Twilio Video vs Vonage for HIPAA telehealth, including BAA terms, recording/encryption, and group-visit support. Suggested researcher query: *"Compare Amazon Chime SDK, Twilio Video, and Vonage Video API for HIPAA-compliant telehealth video visits in 2026: BAA availability, media encryption, recording controls, scalability, and Python backend integration."*
- **E-prescribing vendor selection (incl. EPCS)** — high-stakes regulated integration. Suggested researcher query: *"Compare Surescripts-connected e-prescribing API vendors (DoseSpot, Photon Health, others) for a telehealth platform in 2026: EPCS support, certification, pricing, HIPAA BAA, and Python/REST integration."*
- **Payment + insurance claims for telehealth** — whether to use Stripe (HIPAA posture) and what clearinghouse, if claims are in scope. Suggested researcher query: *"For a US telehealth platform in 2026, what are the options and HIPAA/PCI considerations for patient payment processing and insurance claim submission (clearinghouses), and does Stripe sign a BAA?"*

## Open Questions

- **Billing depth**: Is "billing" patient card capture only, or full insurance eligibility checks and claim adjudication? This changes whether a clearinghouse integration is needed. *(Functional question — belongs to solution-architect.)*
- **Visit recording**: Are video visits recorded (for records/legal)? Not in the listed five capabilities; if required it adds encrypted-storage, retention, and consent requirements. *(Functional — flag to solution-architect.)*
- **Web vs mobile priority**: Is the primary channel web, native mobile, or both? Affects frontend choice (React vs React Native/Flutter).
- **Controlled substances (EPCS)**: Will providers prescribe controlled substances? Drives e-prescribing vendor certification requirements.
- **Multi-state / data residency**: Operating across US states or regions may add licensing and data-handling rules (not pure-technical, but affects architecture).

## Next Steps

1. **Resolve scope Open Questions** (billing depth, recording, channel) with solution-architect/stakeholders before locking the billing and frontend stacks.
2. **Run the flagged researcher queries**, especially current AWS HIPAA-eligibility/BAA and the e-prescribing vendor comparison.
3. **Sign the AWS BAA** and stand up the multi-account AWS Organization (prod isolated for PHI) with Terraform/CDK and AWS Config compliance rules.
4. **Spike the Chime SDK video flow**: FastAPI token-broker endpoint + React client join, verifying encrypted media and no PHI on app servers.
5. **Spike atomic booking**: Aurora schema + slot-hold concurrency test to prove no double-booking under load.
6. **Stand up the FastAPI modular monolith skeleton** with the five modules, Cognito auth, RBAC scaffolding, and PHI-redacting structured logging from day one.

---
*Technical architecture produced by technical-architect skill. Use the librarian skill to persist this artifact.*
