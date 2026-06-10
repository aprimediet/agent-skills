# Telehealth Appointment-Booking System — Technical Architecture

> Technical Architect | Depth: standard | Generated: 2026-06-10

## Source Breakdown

Capability breakdown provided inline by the user (the librarian skill was unavailable, so this was not retrieved from stored specs). The system covers five capability areas. No CAP-NN IDs were supplied, so capabilities are listed by name and assigned working IDs here for traceability. No capabilities were invented — the architecture anchors only to the five listed.

- **CAP-01 Patient registration** — patient sign-up, identity, demographic and insurance profile, consent capture.
- **CAP-02 Provider scheduling** — provider availability, calendars, appointment slots, patient booking/rescheduling/cancellation.
- **CAP-03 Video visits** — live audio/video consultation between patient and provider.
- **CAP-04 Prescriptions** — provider issues prescriptions tied to a visit; record of medications.
- **CAP-05 Billing** — charges for visits, insurance/claims handling, patient payments.

> Note: A capability breakdown produced by the solution-architect skill (with explicit CAP-NN IDs, functional boundaries, and non-functional targets) would strengthen this architecture and tighten the capability mapping. Recommend running it if not already done.

## Constraints & Assumptions

- **Scale & load**: ~tens of thousands of patients, low-thousands of concurrent users at peak, single-region US to start; concurrent video sessions in the low hundreds at peak. **[assumed]** — not stated; right-sizes the design but does not change the AWS/HIPAA/Python decisions.
- **Team**: Team knows Python **[stated]**. Team size and frontend expertise **[assumed]** small-to-medium (5–15 engineers), assumed comfortable with TypeScript/React for web.
- **Hosting**: AWS only — no other cloud **[stated]**. Managed AWS services strongly preferred to minimize undifferentiated ops and shrink the HIPAA surface **[assumed rationale]**.
- **Hard constraints**:
  - HIPAA compliance is mandatory **[stated]** — only AWS services covered by the AWS Business Associate Addendum (BAA) may touch PHI; encryption at rest and in transit, access controls, and audit logging are required.
  - AWS-only, Python backend **[stated]**.
  - Data residency assumed US (`us-east-1` / `us-west-2`) **[assumed]**.
- **Existing systems**: None stated **[assumed greenfield]**. Likely future integrations: an e-prescribing network (e.g., Surescripts) for CAP-04 and a payment processor / claims clearinghouse for CAP-05 — flagged below.

> HIPAA caveat: This is a technical architecture, not a compliance attestation. A signed AWS BAA, a documented risk assessment, workforce training, and policies/procedures are organizational requirements outside this document. Every AWS service named below that touches PHI is, to the architect's knowledge, HIPAA-eligible under the AWS BAA — but eligibility lists change and **must be verified against the current AWS HIPAA-eligible services list** (see Research Suggestions).

## Architecture Overview

- **Style**: **Modular monolith for core booking/clinical domain + a few purpose-built managed services**, on AWS managed compute. One Python application houses CAP-01, CAP-02, CAP-04, and the orchestration of CAP-03 and CAP-05; video and payments are delegated to specialized HIPAA-eligible services. Rationale: at the assumed scale, a modular monolith gives a Python-savvy team fast delivery and a single deployable/auditable unit (simpler HIPAA boundary) while keeping clean module seams so individual domains (e.g., billing) can be peeled into separate services later. Full microservices would multiply the HIPAA-controlled surface and ops burden for no current benefit.
- **Shape**: A React web client (and later mobile) talks to a Python API behind API Gateway/ALB. The API runs as containers on **ECS Fargate** inside a private VPC. It persists PHI in **Amazon RDS for PostgreSQL** (encrypted), caches sessions in **ElastiCache**, stores documents/recordings in **S3** (encrypted), and emits domain events to **SQS/EventBridge** for async work (notifications, billing settlement, claim submission) handled by Python workers. **Video visits run on Amazon Chime SDK** (HIPAA-eligible), with the backend minting per-visit meeting sessions. **Billing** integrates an external payment processor over tokenized APIs so raw card data never lands in our environment. **Cognito** handles identity; everything is wrapped in CloudTrail + CloudWatch + KMS for audit logging, encryption, and key management.

## Tech Stack

### Frontend
- **Recommendation**: **React + TypeScript** single-page app (Vite build), served as static assets from **S3 behind CloudFront** (HTTPS/TLS 1.2+). A patient-facing portal and a provider-facing portal as one app with role-gated routes. For the video UI, use the **Amazon Chime SDK React component library**.
- **Why**: React/TS is the mainstream choice for interactive booking calendars (CAP-02) and the video-call UI (CAP-03), with first-class Chime SDK components. CloudFront + S3 is the standard, low-ops AWS way to serve a SPA. No PHI is stored in the static bundle; PHI is fetched at runtime over TLS.
- **Alternatives**: **Next.js on ECS/Amplify** if SEO or server-side rendering becomes important (a marketing+app surface) — heavier than needed for an authenticated clinical app. **Native mobile (React Native)** later if a patient app store presence is required; defer until web is proven.

### Backend / API
- **Recommendation**: **Python with FastAPI**, packaged as containers on **ECS Fargate**. Async-capable, typed (Pydantic) request/response models, OpenAPI out of the box. Organize as a modular monolith with clear module boundaries per capability (`registration`, `scheduling`, `clinical/prescriptions`, `billing`, `visits`).
- **Why**: Team knows Python **[stated]** — this is the highest-leverage constraint. FastAPI is the modern, performant, well-documented Python API framework; Pydantic typing reduces data-handling bugs that matter for PHI correctness. Fargate gives managed containers (no servers to patch — smaller HIPAA surface) and is BAA-eligible.
- **Alternatives**: **Django + Django REST Framework** if the team wants a batteries-included ORM, admin, and auth scaffolding and is willing to trade some performance/async ergonomics — a strong choice if clinical-admin CRUD dominates. **AWS Lambda (Python)** for a fully serverless API if traffic is spiky and low — viable and HIPAA-eligible, but long-lived video session orchestration and connection pooling to RDS are simpler on Fargate; consider Lambda for the async workers specifically (see below).

### Data storage
- **Primary database — Recommendation**: **Amazon RDS for PostgreSQL** (Multi-AZ), encrypted at rest with **KMS**, TLS enforced for connections. Holds patient records (CAP-01), provider calendars/slots/appointments (CAP-02), prescription records (CAP-04), and billing/invoice records (CAP-05).
  - **Why**: This domain is highly relational and transactional — appointments must not double-book, prescriptions tie to visits and patients, billing ties to visits. Postgres gives strong consistency, constraints, and rich querying. RDS is managed and HIPAA-eligible; Multi-AZ covers availability.
  - **Alternatives**: **Aurora PostgreSQL** if you want faster failover and read-scaling as you grow (recommended migration target — drop-in compatible). **DynamoDB** only for narrow high-write, simple-access-pattern sub-cases (e.g., availability-slot lookups at very large scale) — not for the relational core.
- **Cache — Recommendation**: **Amazon ElastiCache for Redis** (encryption in transit + at rest) for session/token caching and hot scheduling reads (provider availability).
  - **Why**: Reduces DB load on the read-heavy slot-browsing path (CAP-02) and backs server-side session state. HIPAA-eligible.
  - **Alternatives**: Skip initially if scale is small — add when availability queries become a hotspot.
- **Object store — Recommendation**: **Amazon S3** (SSE-KMS, bucket policies, Block Public Access, VPC endpoint) for documents — insurance cards/consent forms (CAP-01), and optionally encrypted video-visit recordings (CAP-03) if recording is a stated requirement (it is not in the breakdown — do not record by default; recording adds significant consent/retention obligations).
  - **Why**: Durable, encrypted, cheap blob storage; HIPAA-eligible. Access via pre-signed URLs scoped and short-lived.
  - **Alternatives**: None needed within AWS.
- **Search/analytics**: **Not needed initially.** No capability requires full-text search or an analytics warehouse yet. If reporting/BI emerges, add **Amazon Redshift** or query S3 with **Athena** (both BAA-eligible) — but that is a future, separate concern, not part of these five capabilities.

### Async / messaging
- **Recommendation**: **Amazon EventBridge** for domain events (e.g., `AppointmentBooked`, `VisitCompleted`) + **Amazon SQS** for work queues, consumed by **Python workers on Fargate or Lambda**. Use SQS-backed Lambda for: appointment reminders/notifications (CAP-02), billing settlement and claim submission after a completed visit (CAP-05), and e-prescription transmission (CAP-04).
- **Why**: Decouples slow/external work (sending an SMS, calling a payment processor, submitting a claim) from the synchronous booking/visit path so user actions stay fast and failures retry independently. EventBridge gives clean event routing; SQS gives durable retry + DLQ. All HIPAA-eligible. Keep PHI out of event payloads where possible — pass record IDs, not clinical detail.
- **Alternatives**: **Amazon MSK / Kafka** only if you later need high-throughput event streaming or replay — overkill now. **Step Functions** if billing/claims becomes a long multi-step workflow with human steps — a good fit for orchestrating claim → adjudication → reconciliation later.

### Authentication & authorization
- **Recommendation**: **Amazon Cognito** user pools for identity (patients and providers as separate groups), with MFA enforced for providers and clinical staff. Short-lived JWT access tokens; authorization enforced in the API layer with role/attribute checks (patient can only see own records; provider scoped to their patients). Cognito is HIPAA-eligible.
- **Why**: Managed identity removes the risk of rolling our own credential storage (a frequent HIPAA failure point), supports MFA and password policies, and integrates with API Gateway/ALB. RBAC in-app enforces minimum-necessary access — a HIPAA access-control requirement.
- **Alternatives**: **Auth0/Okta** for richer enterprise SSO and more flexible flows (both offer BAAs) — choose if you need broker SSO with hospital IdPs; costs more and adds a vendor. Self-managed auth: **avoid** — highest HIPAA risk for least benefit.

### Infrastructure & hosting
- **Recommendation**: **ECS Fargate** for the API and workers, inside a **VPC** with private subnets for compute/data and public subnets only for ALB/CloudFront. **Application Load Balancer** (or API Gateway) terminating TLS. **VPC endpoints** for S3/DynamoDB/Secrets so traffic to AWS services stays off the public internet. Single region (`us-east-1`) Multi-AZ to start. **WAF** in front of CloudFront/ALB.
- **Why**: Fargate = managed containers, no host patching (shrinks HIPAA responsibility under the shared-responsibility model). Private subnets + VPC endpoints keep PHI traffic internal. Multi-AZ covers the availability that a clinical scheduling/visit system needs.
- **Alternatives**: **EKS (Kubernetes)** if the team already runs k8s or anticipates many services — more operational overhead than this scale justifies. **Lambda + API Gateway fully serverless** if you want to minimize idle cost — workable, but Fargate is simpler for stateful-ish API + Chime orchestration.

### CI/CD & developer tooling
- **Recommendation**: **GitHub Actions (or AWS CodePipeline/CodeBuild) → ECR → ECS Fargate**, with **Terraform** (or AWS CDK in Python) for IaC. Separate `dev` / `staging` / `prod` AWS accounts under **AWS Organizations**, prod isolated. Automated tests (pytest), container image scanning (ECR scan / Trivy), and infra plan review on PRs.
- **Why**: Reproducible, auditable deployments (change control is a HIPAA expectation). CDK-in-Python keeps infra in the team's language; Terraform if multi-tool/standard preferred. Account-per-environment isolates prod PHI from non-prod (use only de-identified/synthetic data in dev/staging).
- **Alternatives**: **CodePipeline end-to-end** for an all-AWS, BAA-covered pipeline if the team prefers to avoid GitHub for build infra. **Pulumi (Python)** as a CDK/Terraform alternative.

### Observability
- **Recommendation**: **CloudWatch Logs + Metrics + Alarms**, **AWS X-Ray** for tracing, **CloudTrail** for API/audit logging (org-wide, log-file validation on, delivered to a locked-down S3 bucket). Structured JSON app logs scrubbed of PHI; alarms on error rates, latency, failed logins, and unauthorized-access attempts.
- **Why**: CloudTrail + access logging is a direct HIPAA audit-control requirement (who accessed what, when). CloudWatch/X-Ray are the native, BAA-eligible observability stack. PHI must be kept out of logs — enforce log scrubbing.
- **Alternatives**: **Datadog / New Relic** (both offer BAAs) for richer dashboards/APM if the team wants a single pane across services — added cost and another BAA to manage; native stack is sufficient at this scale.

### Third-party services & integrations
- **Video (CAP-03) — Recommendation**: **Amazon Chime SDK** — HIPAA-eligible under the AWS BAA, stays in-cloud, has Python server SDK + React client components. Backend mints per-visit meetings and attendee tokens; media is SRTP-encrypted. This is the specific HIPAA-eligible video approach. **Alternative**: **Twilio Video** or **Zoom Healthcare / Vonage** (all offer BAAs) — choose if you need features Chime lacks (e.g., advanced waiting rooms, broad device SDKs); trade-off is a non-AWS dependency and a second BAA, which cuts against the AWS-only preference.
- **Notifications (CAP-02 reminders) — Recommendation**: **Amazon SNS** (SMS) and **Amazon SES** (email), both BAA-eligible — but **keep PHI out of message bodies** (e.g., "You have an appointment Tuesday 3pm," not the visit reason). **Alternative**: Twilio for richer SMS deliverability/templating (BAA available).
- **Payments / billing (CAP-05) — Recommendation**: External **PCI-DSS-compliant payment processor** (e.g., **Stripe**) over tokenized APIs so card data never enters our environment (keeps us out of heavy PCI scope); store only tokens + invoice records in RDS. For insurance claims, integrate a **clearinghouse** (e.g., Change Healthcare/Availity) — flagged as a research/decision item. **Alternative**: AWS has no native payment-processing service; a processor is required regardless of AWS-only preference (it's a payment boundary, not a hosting choice).
- **E-prescribing (CAP-04) — Recommendation**: Integrate an **e-prescribing network (Surescripts)**, typically via a certified intermediary/EHR-integration vendor — true e-prescribing (especially EPCS for controlled substances) is heavily regulated and certification-bound. Flagged for research/decision. **Alternative (interim)**: store prescription records internally and generate documents for manual/faxed workflows until certified e-prescribing is integrated — confirm scope with the user (this is a functional decision for solution-architect, flagged below).

### Security
- **Encryption at rest**: KMS-managed keys (CMKs) for RDS, S3 (SSE-KMS), ElastiCache, SQS, and EBS. Customer-managed keys with rotation enabled. **[HIPAA control]**
- **Encryption in transit**: TLS 1.2+ everywhere — CloudFront, ALB/API Gateway, RDS connections (enforced), Redis in-transit encryption, Chime SRTP media. **[HIPAA control]**
- **Access control**: Cognito + in-app RBAC enforcing minimum-necessary; least-privilege **IAM roles** per service; no long-lived static credentials (task roles + IRSA-equivalent). MFA for clinical staff. **[HIPAA control]**
- **Audit logging**: CloudTrail (org-wide, tamper-evident), application-level access logs for PHI reads/writes, CloudWatch alarms on anomalous access. Define retention to meet HIPAA (≥6 years for required records) via S3 lifecycle + Object Lock for immutability. **[HIPAA control]**
- **Secrets**: **AWS Secrets Manager** (rotation) for DB creds and third-party API keys — never in code or env files in the image.
- **Network**: Private subnets, security groups, NACLs, VPC endpoints, **WAF** + **Shield** at the edge, **GuardDuty** for threat detection, **AWS Config** for continuous compliance rules, **Security Hub** to aggregate. **[HIPAA control: technical safeguards]**
- **BAA scope**: Confirm a signed AWS BAA and ensure every PHI-touching service is on the AWS HIPAA-eligible list; isolate any non-eligible service from PHI. Same for every third-party (Stripe, Twilio, e-prescribing vendor) — each needs its own BAA.

## Capability → Tech Mapping

| Capability | Implemented by | Notes |
|-----------|----------------|-------|
| CAP-01 Patient registration | Cognito (identity, MFA), FastAPI `registration` module, RDS PostgreSQL (patient/demographic/insurance/consent), S3 (consent forms, insurance-card images), KMS encryption | Consent capture stored with audit trail; PHI encrypted at rest and in transit. |
| CAP-02 Provider scheduling | FastAPI `scheduling` module, RDS PostgreSQL (calendars, slots, appointments) with transactional constraints to prevent double-booking, ElastiCache (hot availability reads), EventBridge→SQS→Lambda + SNS/SES for reminders | Booking is the consistency-critical path; relational integrity enforced in Postgres. Reminders carry no PHI. |
| CAP-03 Video visits | Amazon Chime SDK (HIPAA-eligible video), FastAPI `visits` module mints meetings/attendee tokens, Chime SDK React UI, SRTP media encryption; optional S3 (SSE-KMS) only if recording is required | Specific HIPAA-eligible video approach; recording off by default pending consent/retention decision. |
| CAP-04 Prescriptions | FastAPI `clinical/prescriptions` module, RDS PostgreSQL (prescription records linked to visit+patient), SQS→Lambda for transmission, external e-prescribing network (Surescripts via certified vendor) | E-prescribing/EPCS certification is a regulated integration — flagged. Interim internal record + document generation possible. |
| CAP-05 Billing | FastAPI `billing` module, RDS PostgreSQL (invoices/charges, tokens only), external payment processor (Stripe) via tokenized API, EventBridge/SQS (or Step Functions) for settlement + claims, clearinghouse integration for insurance | Card data never enters our environment (PCI scope minimized). Claims clearinghouse flagged as a decision/research item. |

## Key Architecture Decisions

### AD-01: Modular monolith on Fargate over microservices

- **Decision**: Build CAP-01/02/04 and orchestration of 03/05 as one modular Python (FastAPI) application on ECS Fargate, with clean module seams, rather than separate microservices.
- **Context**: Python team **[stated]**, assumed small-to-medium org and moderate scale, HIPAA in force.
- **Rationale**: Fewer moving parts = a smaller, more auditable HIPAA surface and faster delivery for the team's skill set. Module boundaries preserve the option to extract billing or scheduling into their own services later.
- **Tradeoffs**: A single deploy unit means coarser independent scaling and a shared blast radius; mitigated by module discipline, Multi-AZ, and offloading async work to queues/Lambda.

### AD-02: Amazon Chime SDK for video visits

- **Decision**: Use Amazon Chime SDK for CAP-03 video consultations.
- **Context**: AWS-only **[stated]**, HIPAA **[stated]**, video is a core clinical capability.
- **Rationale**: HIPAA-eligible under the AWS BAA, keeps the stack AWS-native (one cloud, one BAA), has Python server + React client SDKs, SRTP-encrypted media.
- **Tradeoffs**: Fewer turnkey clinical features (waiting rooms, broad device support) than specialized vendors like Twilio/Zoom Healthcare; revisit if those features are required (would add a second BAA and break AWS-only).

### AD-03: Externalize payments; keep card data out of scope

- **Decision**: Process payments (CAP-05) through an external PCI-compliant processor (Stripe) using tokenization; store only tokens and invoice records.
- **Context**: AWS has no native payment processor; PCI-DSS would otherwise apply broadly.
- **Rationale**: Card data never touches our environment, minimizing PCI scope and keeping the AWS environment focused on PHI under HIPAA. A processor is unavoidable regardless of cloud preference.
- **Tradeoffs**: A non-AWS dependency with its own BAA/contract; acceptable because it is a payment boundary, not a hosting choice. Insurance-claims path still needs a clearinghouse decision.

### AD-04: Managed AWS services to shrink the HIPAA surface

- **Decision**: Prefer managed, BAA-eligible AWS services (RDS, Fargate, Cognito, SQS/EventBridge, Chime, CloudTrail/CloudWatch, KMS, Secrets Manager) over self-managed equivalents.
- **Context**: HIPAA **[stated]**, AWS-only **[stated]**, assumed lean ops team.
- **Rationale**: Under the shared-responsibility model, managed services move host patching and much of the infra safeguard burden to AWS, reducing what the team must control and document.
- **Tradeoffs**: Some vendor lock-in to AWS and per-service cost; acceptable given the explicit AWS-only constraint.

## Risks & Tradeoffs

- **HIPAA-eligibility drift**: The set of BAA-eligible services changes; a service assumed eligible here may need verification. Mitigation: verify against the current AWS HIPAA-eligible list before building each component; isolate any non-eligible service from PHI.
- **PHI leaking into logs / events / notifications**: A common breach vector. Mitigation: structured logging with PHI scrubbing, IDs (not clinical detail) in event payloads, and no PHI in SMS/email bodies — enforce in code review and tests.
- **E-prescribing regulatory complexity (CAP-04)**: True e-prescribing, especially controlled substances (EPCS), is certification-heavy and may require a specialized vendor/EHR integration. Risk of underestimating scope. Mitigation: treat as its own track; confirm functional scope with solution-architect/user before committing.
- **Insurance claims complexity (CAP-05)**: Claims/adjudication is a deep domain (EDI 837/835, clearinghouses). Risk of treating "billing" as just card capture. Mitigation: scope patient-payment vs. payer-claims explicitly; the claims workflow may warrant Step Functions and a clearinghouse partner.
- **Modular monolith discipline erosion**: Without enforced module boundaries, the monolith can become a tangle that's hard to split later. Mitigation: clear module interfaces, dependency rules in CI, and per-module ownership.
- **Single region**: A region outage halts a clinical service. Mitigation: Multi-AZ now; evaluate multi-region DR (warm standby) once SLAs justify the cost.

## Research Suggestions

High-stakes / regulated choices to validate with the researcher skill (researcher was unavailable in this run):

- **AWS HIPAA-eligible services verification** — eligibility lists change and this design depends on it. Suggested researcher query: "Which AWS services are currently HIPAA-eligible under the AWS BAA as of 2026, specifically: ECS Fargate, RDS PostgreSQL, ElastiCache for Redis, S3, Cognito, SQS, EventBridge, SNS, SES, Amazon Chime SDK, CloudTrail, CloudWatch, X-Ray, KMS, Secrets Manager, WAF, GuardDuty? Note any that are NOT eligible."
- **HIPAA-eligible video for telehealth** — core clinical capability, high stakes. Suggested researcher query: "Compare Amazon Chime SDK vs Twilio Video vs Zoom Healthcare vs Vonage for HIPAA-compliant telehealth video in 2026: BAA availability, encryption, waiting-room/clinical features, Python/React SDK maturity, and pricing at low-hundreds concurrent sessions."
- **E-prescribing / EPCS integration path** — heavily regulated. Suggested researcher query: "What are the 2026 options and requirements for integrating e-prescribing (Surescripts) including EPCS for controlled substances into a custom telehealth platform — certified intermediaries, DEA/EPCS identity-proofing and two-factor requirements, and typical vendor integration models?"
- **Insurance claims / clearinghouse integration** — deep domain. Suggested researcher query: "For a US telehealth platform in 2026, what is the standard architecture for submitting insurance claims (EDI 837) and processing remittances (835) via a clearinghouse (Change Healthcare/Availity), and how does it integrate with a Stripe-based patient-payment flow?"

## Open Questions

- **Recording of video visits (CAP-03)**: Is recording required? It materially changes storage, consent, and retention. Defaulting to no recording. (Functional — confirm via solution-architect/user.)
- **Billing scope (CAP-05)**: Patient self-pay only, insurance claims, or both? Determines whether a clearinghouse and Step Functions workflow are in scope now. (Functional — flag back, not for the architect to invent.)
- **Prescription scope (CAP-04)**: Full e-prescribing (incl. controlled substances/EPCS) vs. internal records + documents for now? Drives the regulated-integration timeline.
- **Scale targets**: Confirm assumed user/concurrency numbers and any availability SLA; multi-region DR depends on this.
- **Team frontend skill**: Confirm React/TS comfort, or whether a Python-centric frontend approach is preferred.

## Next Steps

1. Confirm the open questions (recording, billing scope, prescription scope, scale, frontend skill) and verify the AWS BAA is signed.
2. Run the four Research Suggestions (HIPAA service eligibility, video, e-prescribing, claims) before committing those components.
3. Stand up the AWS landing zone: Organizations with prod/staging/dev account isolation, VPC with private subnets + VPC endpoints, KMS keys, CloudTrail org-wide, Config/GuardDuty/Security Hub baselines.
4. Spike the riskiest integration first — Amazon Chime SDK video flow (backend meeting minting + React client) — to validate the core clinical experience.
5. Scaffold the FastAPI modular monolith with module seams per capability, RDS PostgreSQL schema for CAP-01/02, and the CI/CD pipeline (IaC via CDK-Python or Terraform) into the isolated prod account.

---
*Technical architecture produced by technical-architect skill. Use the librarian skill to persist this artifact.*
