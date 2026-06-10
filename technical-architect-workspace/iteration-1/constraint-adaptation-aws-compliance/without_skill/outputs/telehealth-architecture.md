# Telehealth Appointment-Booking System — Technical Architecture & Stack Recommendation

**Status:** Proposed
**Date:** 2026-06-10
**Constraints:** AWS-only infrastructure · HIPAA compliance (US PHI) · Team is Python-proficient

---

## 1. Executive Summary

This document defines the technical architecture and recommended stack for a HIPAA-compliant telehealth platform spanning five capability domains: **patient registration, provider scheduling, video visits, prescriptions (e-prescribing), and billing**.

The recommended approach is a **modular monolith for the core API (FastAPI on ECS Fargate), with a small number of carved-out services** for concerns that have independent scaling profiles, distinct compliance boundaries, or third-party integration needs (video, e-prescribing, billing/clearinghouse, notifications). This avoids premature microservice sprawl while isolating the highest-risk and highest-variability components.

All PHI-handling components run inside a private VPC, every data store is encrypted with customer-managed KMS keys, and all access to PHI is logged immutably. A signed **AWS Business Associate Addendum (BAA)** governs every HIPAA-eligible service used.

**Headline stack:** Python 3.12 · FastAPI · PostgreSQL (Aurora) · ECS Fargate · API Gateway · Cognito · KMS · S3 · SQS/EventBridge · CloudWatch + CloudTrail · Terraform/CDK.

---

## 2. Constraints & Their Architectural Consequences

| Constraint | Consequence |
|---|---|
| **AWS-only** | No GCP/Azure managed services. All build-vs-buy decisions resolve to an AWS-native service or a self-hosted-on-AWS option. Third-party SaaS (e.g., e-prescribing) is allowed but must sign a BAA and be reachable from AWS. |
| **HIPAA compliance** | Every component touching PHI must be on an AWS HIPAA-eligible service under the AWS BAA. Encryption at rest + in transit, audit logging, least-privilege IAM, network isolation, 6-year audit retention, breach-notification readiness, and signed BAAs with every vendor (including the video and e-Rx providers). |
| **Python team** | Backend in Python (FastAPI). Avoid stacks that force the team into unfamiliar languages. IaC in Python (CDK) is an option but Terraform is recommended for ecosystem maturity; either is acceptable. Lambda functions in Python. |

### HIPAA non-negotiables baked into this design
- **BAA coverage:** Use only [AWS HIPAA-eligible services](https://aws.amazon.com/compliance/hipaa-eligible-services-reference/). Do not place PHI in non-eligible services.
- **Encryption at rest:** KMS customer-managed keys (CMKs) on every store (Aurora, S3, EBS, DynamoDB, SQS, backups, logs).
- **Encryption in transit:** TLS 1.2+ everywhere, including intra-service traffic.
- **Audit trail:** Immutable, tamper-evident logging of all PHI access (who, what, when). 6-year minimum retention.
- **Least privilege:** IAM roles scoped per service; no long-lived human credentials; SSO + MFA for operators.
- **Network isolation:** PHI workloads in private subnets, no public IPs, access via VPC endpoints.
- **De-identification boundary:** Analytics and non-prod environments never receive raw PHI.

---

## 3. Architecture Style Decision

### Options considered

1. **Pure monolith** — one deployable, one database. Simplest, but couples wildly different scaling needs (video signaling vs. billing batch jobs) and makes the compliance blast radius the entire app.
2. **Full microservices** — one service per capability. Maximum isolation, but heavy operational overhead (service mesh, distributed tracing, data consistency) for a team that should be shipping features, not platform plumbing.
3. **Modular monolith + carved services (RECOMMENDED)** — a single well-structured core API with clear internal module boundaries, plus separate services only where justified.

### Decision: Modular monolith core + targeted services

**Core API (one ECS service)** owns the transactional, tightly-related domains:
- Patient registration & identity profile
- Provider scheduling & availability
- Appointment booking & lifecycle
- Visit metadata (the clinical record around a video visit)

**Carved-out services / async workers** for concerns with different shapes:
- **Video service** — thin wrapper around a managed WebRTC provider (Amazon Chime SDK). Different scaling (connection-bound), distinct SDK surface.
- **Prescription (e-Rx) integration service** — talks to an external Surescripts-connected EHR/e-prescribing vendor. Isolated for compliance/audit and because the integration is high-change and externally rate-limited.
- **Billing & claims service** — interacts with payment processor + insurance clearinghouse; batch/async heavy; distinct PCI + HIPAA overlap.
- **Notification worker** — SMS/email/push (appointment reminders), async, fan-out.

**Why this split:** Each carved service either (a) has a fundamentally different scaling/latency profile, (b) wraps a volatile external integration, or (c) carries a distinct compliance overlay (PCI for payments, Surescripts certification for e-Rx). Everything else stays in the modular monolith for development velocity and transactional integrity.

**Communication:** Synchronous request/response via internal HTTPS (API Gateway / service-to-service through private networking). Asynchronous workflows (reminders, claim submission, post-visit summaries, prescription status callbacks) via **EventBridge** (routing/domain events) + **SQS** (work queues, with DLQs).

---

## 4. System Architecture Diagram (logical)

```
                          ┌─────────────────────────────────────────────┐
   Patients / Providers   │                 Amazon CloudFront            │
        (browsers,        │           (WAF, TLS, static SPA assets)      │
       mobile apps)  ───▶ └───────────────────┬─────────────────────────┘
                                               │
                                  ┌────────────▼────────────┐
                                  │   Amazon API Gateway     │
                                  │  (REST/HTTP, throttling, │
                                  │   Cognito authorizer)    │
                                  └────────────┬─────────────┘
                                               │  (private)
        ┌──────────────────────────────────────┼───────────────────────────────────────┐
        │                          VPC (private subnets, multi-AZ)                       │
        │                                       │                                        │
        │   ┌───────────────────────────────────▼───────────────┐                        │
        │   │            Core API — FastAPI on ECS Fargate        │                        │
        │   │  modules: registration · scheduling · booking ·     │                        │
        │   │           visit-record                              │                        │
        │   └───┬───────────┬───────────────┬───────────────┬─────┘                        │
        │       │           │               │               │                              │
        │   ┌───▼────┐  ┌────▼─────┐   ┌─────▼──────┐  ┌──────▼───────┐                     │
        │   │ Aurora │  │  Amazon  │   │ EventBridge│  │ ElastiCache  │                     │
        │   │ Postgres│ │   S3     │   │  + SQS     │  │  (Redis)     │                     │
        │   │ (CMK)  │  │ (docs,   │   │  (events,  │  │ sessions/    │                     │
        │   │        │  │  CMK)    │   │   queues)  │  │ availability │                     │
        │   └────────┘  └──────────┘   └─────┬──────┘  └──────────────┘                     │
        │                                    │                                              │
        │   ┌────────────┐  ┌────────────────▼───┐  ┌───────────────┐  ┌────────────────┐  │
        │   │ Video svc  │  │ Notification worker │  │ e-Rx svc      │  │ Billing/claims │  │
        │   │ (Chime SDK)│  │ (SES/SNS/Pinpoint)  │  │ (Surescripts  │  │ svc (Stripe +  │  │
        │   │            │  │                     │  │  via vendor)  │  │  clearinghouse)│  │
        │   └─────┬──────┘  └─────────────────────┘  └──────┬────────┘  └───────┬────────┘  │
        └─────────┼──────────────────────────────────────────┼───────────────────┼─────────┘
                  │                                           │                   │
            ┌─────▼─────┐                            ┌────────▼──────┐    ┌────────▼────────┐
            │ Amazon    │                            │ External e-Rx │    │ Stripe (BAA) +  │
            │ Chime SDK │                            │ / Surescripts │    │ clearinghouse   │
            │ media     │                            │ vendor (BAA)  │    │ (837/835 EDI)   │
            └───────────┘                            └───────────────┘    └─────────────────┘

  Cross-cutting:  Cognito (authn) · KMS (CMKs) · Secrets Manager · CloudTrail · CloudWatch ·
                  GuardDuty · Security Hub · AWS Config · Backup · Terraform/CDK
```

---

## 5. Recommended Stack by Layer

### 5.1 Client / Frontend
| Concern | Recommendation | Rationale |
|---|---|---|
| Web app | **React + TypeScript (Vite)** SPA | Mature ecosystem; video SDKs (Chime) have first-class JS support. |
| Hosting | **S3 + CloudFront** (OAC) | Static, cheap, global, integrates with WAF. |
| Mobile (if needed) | React Native or native, sharing the API | Defer until web is validated. |

> The team is Python-strong; frontend is the one place a non-Python language is unavoidable. Keep the frontend thin — it is a client of the API, holds no PHI at rest, and stores tokens only in memory / secure storage.

### 5.2 API & Application Layer
| Concern | Recommendation | Rationale |
|---|---|---|
| Language/runtime | **Python 3.12** | Team expertise. |
| Web framework | **FastAPI** (+ Uvicorn/Gunicorn) | Async, high performance, automatic OpenAPI, Pydantic validation — strong fit for an audited API where request/response schemas matter. |
| Data validation | **Pydantic v2** | Enforces schema at the boundary; reduces malformed-PHI risk. |
| ORM / DB access | **SQLAlchemy 2.0 + Alembic** | Mature, async-capable, migrations. |
| Background/async tasks | **Celery** or native consumers reading **SQS** | Reminders, claims, summaries. Prefer SQS-driven workers on Fargate for AWS-native simplicity. |
| Edge | **API Gateway** + **AWS WAF** | Throttling, request validation, managed rules (OWASP), Cognito authorizer. |

### 5.3 Compute
| Workload | Recommendation | Rationale |
|---|---|---|
| Core API + carved services | **ECS Fargate** (containers, multi-AZ, behind ALB) | No server management, scales per-service, HIPAA-eligible, fits containerized FastAPI. Preferred over EKS to avoid Kubernetes operational burden for this team size. |
| Event-driven glue / light tasks | **AWS Lambda (Python)** | Prescription status callbacks, file post-processing, scheduled jobs (EventBridge Scheduler). |
| Why not Lambda for the core API | Long-lived connections, predictable latency, and container tooling favor Fargate for the main API; Lambda reserved for spiky/glue work. |

### 5.4 Data Stores
| Data | Store | Rationale |
|---|---|---|
| Transactional PHI (patients, providers, appointments, visits, prescriptions metadata, billing records) | **Amazon Aurora PostgreSQL** (CMK-encrypted, multi-AZ, private) | Relational integrity for bookings/scheduling; HIPAA-eligible; strong consistency; PostGIS available if geo needed. |
| Caching / sessions / availability slots | **ElastiCache for Redis** (encrypted, in-VPC) | Hot availability lookups, rate-limit counters, distributed locks for slot booking. |
| Documents (consent forms, uploaded ID, visit attachments, claim files) | **Amazon S3** (CMK, versioning, Object Lock for retention, block public access) | Durable object storage; lifecycle to Glacier for 6-year retention. |
| High-volume audit/event log (optional) | **DynamoDB** or **OpenSearch** (encrypted) | Fast append-only audit index; or stream to immutable store. |
| Analytics (de-identified) | **S3 data lake + Athena/Redshift**, PHI stripped on the way in | Keeps raw PHI out of analytics; satisfies minimum-necessary. |

**Booking concurrency:** Slot booking uses Aurora transactions with row-level locking (`SELECT ... FOR UPDATE`) or a Redis distributed lock to prevent double-booking the same provider slot.

### 5.5 Identity, AuthN/AuthZ
| Concern | Recommendation | Rationale |
|---|---|---|
| Authentication | **Amazon Cognito** (user pools) | HIPAA-eligible, MFA, hosted UI, OIDC/JWT. Separate pools or groups for patients vs. providers vs. staff. |
| Authorization | Role-based via Cognito groups + **fine-grained checks in FastAPI** (and optionally Verified Permissions / Cedar) | Patients see only their records; providers their panel; least privilege enforced in app + token claims. |
| Service-to-service | **IAM roles** (task roles) + SigV4 / mTLS internally | No static keys. |
| Secrets | **AWS Secrets Manager** (rotation) | DB creds, vendor API keys, signing keys. |
| Operator access | **IAM Identity Center (SSO) + MFA**, session-recorded | No shared accounts; CloudTrail attribution. |

### 5.6 Capability-Specific Integrations

#### Video Visits
- **Amazon Chime SDK** for WebRTC video/audio (HIPAA-eligible under AWS BAA). Backend mints meeting + attendee tokens; media never traverses our servers.
- Optional **Chime SDK media pipelines** for recording — recordings are PHI: store in CMK-encrypted S3 with Object Lock, explicit patient consent, and strict access logging. Default to **no recording** unless clinically/ legally required.
- Waiting-room and provider-ready signaling via WebSocket (API Gateway WebSocket or Chime messaging).

#### Prescriptions (e-Prescribing)
- **Do not build e-prescribing in-house.** Routing controlled substances and standard prescriptions to pharmacies requires **Surescripts certification** and **EPCS** (DEA two-factor for controlled substances). Integrate a certified vendor (e.g., DoseSpot, Surescripts-connected EHR module) under a BAA.
- The **e-Rx service** is a thin, heavily-audited adapter: it formats requests, handles vendor callbacks (Lambda/SQS), persists prescription metadata in Aurora, and never logs full PHI payloads to general logs.

#### Billing
- **Patient payments:** **Stripe** (signs a BAA; PCI-DSS Level 1) — keeps card data out of our environment (tokenization). Avoids us holding PAN data.
- **Insurance claims:** Submit **837** claims / receive **835** remittances via a **clearinghouse** (e.g., Availity, Change Healthcare) under BAA. The billing service handles EDI generation, eligibility (270/271), and reconciliation asynchronously via SQS.
- Billing records (which are PHI when tied to diagnoses/encounters) live in Aurora under CMK.

#### Notifications / Reminders
- **Amazon Pinpoint / SNS** (SMS) and **SES** (email) for appointment reminders. **Critical:** reminder content must avoid PHI (no diagnosis/treatment details) — send minimal "you have an appointment on <date>" + secure-portal link. Patient communication-channel consent captured at registration.

### 5.7 Async & Eventing
| Concern | Recommendation |
|---|---|
| Domain events (appointment.booked, visit.completed, prescription.sent, claim.submitted) | **Amazon EventBridge** (custom bus, schema registry) |
| Work queues + retries | **Amazon SQS** (standard/FIFO where ordering matters) with **DLQs** |
| Scheduled jobs (reminder sweeps, claim batches) | **EventBridge Scheduler** |
| Step orchestration (multi-step claim lifecycle) | **AWS Step Functions** (optional) |

### 5.8 Observability, Security & Compliance Tooling
| Concern | Recommendation | HIPAA tie-in |
|---|---|---|
| App + infra logs/metrics | **CloudWatch Logs/Metrics** (CMK-encrypted log groups) | PHI scrubbed from app logs; structured logging. |
| Audit trail (API/control plane) | **CloudTrail** (org trail, log-file validation, to locked S3) | Tamper-evident, 6-year retention. |
| PHI access audit (data plane) | App-level audit middleware → append-only store (DynamoDB/OpenSearch) | "Who accessed which patient record when." |
| Tracing | **AWS X-Ray** or OpenTelemetry | Diagnose without exposing PHI. |
| Threat detection | **GuardDuty**, **Security Hub**, **AWS Config** (conformance packs incl. HIPAA) | Continuous compliance posture. |
| Vuln scanning | **Amazon Inspector** (containers/EC2), **ECR scanning** | Image CVEs. |
| Secrets/PII scanning | **Macie** on S3 | Detect mis-stored PHI. |
| Backups | **AWS Backup** (cross-region, CMK, immutable vault) | DR + retention. |

### 5.9 Networking
- **VPC** with public subnets (ALB/NAT only) and private subnets (all compute + data).
- **VPC endpoints (PrivateLink)** for S3, KMS, Secrets Manager, SQS, etc. — keep traffic off the public internet.
- **TLS termination** at CloudFront/ALB; ACM-managed certs; TLS 1.2+ enforced.
- **Security groups** least-privilege; no `0.0.0.0/0` ingress except CloudFront-fronted ALB on 443.
- **WAF** managed rule groups + rate limiting on API Gateway / ALB.

### 5.10 DevOps / Delivery
| Concern | Recommendation | Rationale |
|---|---|---|
| IaC | **Terraform** (or **AWS CDK in Python** if the team prefers Python everywhere) | Reproducible, reviewable infra; environment parity. |
| CI/CD | **GitHub Actions** or **AWS CodePipeline/CodeBuild** → ECR → ECS rolling/blue-green | Automated tests, image scan, IaC plan/apply gates. |
| Containers | Docker images in **ECR** (scanned, immutable tags) | Supply-chain hygiene. |
| Environments | dev / staging / prod, **fully isolated accounts** (AWS Organizations) | Blast-radius isolation; non-prod has only synthetic/de-identified data. |
| Testing | pytest, schema/contract tests, load tests on booking concurrency | |

---

## 6. Data Flow Walkthroughs (representative)

**Booking an appointment**
1. Patient (authenticated via Cognito JWT) requests available slots → Core API reads provider availability (Redis cache, Aurora source of truth).
2. Patient selects slot → Core API opens a transaction, locks the slot, writes appointment, commits.
3. Emits `appointment.booked` to EventBridge → Notification worker sends a PHI-free reminder schedule; calendar/availability cache invalidated.

**Conducting a video visit**
1. At visit time, provider/patient request to join → Core API checks appointment state, calls Video service.
2. Video service creates a Chime meeting + attendee tokens, returns them; clients connect P2P/SFU via Chime media (not our servers).
3. On end, `visit.completed` event → visit record updated; optional consented recording lands in CMK S3 with Object Lock.

**Sending a prescription**
1. Provider submits Rx in the visit UI → Core API → e-Rx service formats and calls the certified vendor (EPCS 2FA for controlled substances).
2. Vendor delivers to pharmacy; async status callback (Lambda/SQS) updates prescription metadata in Aurora; all steps audit-logged.

**Billing a visit**
1. `visit.completed` triggers billing service → patient responsibility charged via Stripe (tokenized); insurance portion → 837 claim to clearinghouse via SQS.
2. 835 remittance received → reconciliation; patient statement issued through secure portal.

---

## 7. Compliance Control Mapping (HIPAA Security Rule)

| Safeguard | How this architecture satisfies it |
|---|---|
| **Access control** (§164.312(a)) | Cognito + IAM + RBAC, MFA, least privilege, unique user IDs, automatic session timeout. |
| **Audit controls** (§164.312(b)) | CloudTrail + app-level PHI access audit log, immutable, 6-yr retention. |
| **Integrity** (§164.312(c)) | Aurora ACID, S3 versioning + Object Lock, CloudTrail log-file validation. |
| **Transmission security** (§164.312(e)) | TLS 1.2+ end-to-end, VPC endpoints, no public PHI paths. |
| **Encryption at rest** (addressable) | KMS CMKs on all stores + backups + logs. |
| **Person/entity authentication** | Cognito (patients/providers), IAM SSO+MFA (operators). |
| **Administrative / BAA** | AWS BAA + vendor BAAs (Chime, Stripe, e-Rx vendor, clearinghouse, SES/Pinpoint). |
| **Contingency / DR** | AWS Backup cross-region, multi-AZ Aurora, documented RTO/RPO, runbooks. |
| **Minimum necessary** | De-identified analytics pipeline; PHI-free notifications; scoped tokens. |

---

## 8. Build vs. Buy Summary

| Capability | Decision | Why |
|---|---|---|
| Patient registration / scheduling / booking | **Build** (Core API) | Core differentiator; standard CRUD + concurrency the team can own. |
| Video | **Buy** (Amazon Chime SDK) | Don't build WebRTC media infra; AWS-native + BAA. |
| E-prescribing | **Buy** (certified vendor) | Requires Surescripts/EPCS certification — not feasible to build. |
| Card payments | **Buy** (Stripe) | Avoid PCI scope of handling PANs. |
| Insurance EDI | **Buy** (clearinghouse) | EDI 837/835/270/271 complexity + payer connectivity. |
| Notifications | **Buy** (SES/Pinpoint/SNS) | Managed deliverability. |
| Identity | **Buy** (Cognito) | HIPAA-eligible managed authn. |

---

## 9. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| PHI leaking into logs/analytics | Log scrubbing middleware; Macie scanning; de-identified analytics pipeline. |
| Double-booking under concurrency | DB row locks / Redis locks; idempotency keys on booking endpoint. |
| Vendor BAA gaps | Procurement checklist: no PHI to any vendor without a signed BAA. |
| Controlled-substance e-Rx compliance | Use EPCS-certified vendor; enforce DEA 2FA; never self-route controlled substances. |
| Cost of always-on multi-AZ | Right-size Fargate, autoscaling, reserved/savings plans; Aurora Serverless v2 for variable load. |
| Operational complexity creep | Keep modular monolith; resist splitting services without a scaling/compliance justification. |

---

## 10. Recommended Stack — One-Page Reference

- **Language:** Python 3.12
- **API framework:** FastAPI + Pydantic v2, SQLAlchemy 2.0 + Alembic
- **Compute:** ECS Fargate (core + services), Lambda (glue/scheduled)
- **Edge:** CloudFront + WAF + API Gateway, ACM TLS
- **Database:** Aurora PostgreSQL (CMK, multi-AZ); ElastiCache Redis
- **Storage:** S3 (CMK, Object Lock, lifecycle to Glacier)
- **Identity:** Cognito + IAM Identity Center; Secrets Manager
- **Async:** EventBridge + SQS (+DLQ) + EventBridge Scheduler; Step Functions (optional)
- **Video:** Amazon Chime SDK
- **E-Rx:** Certified Surescripts/EPCS vendor (e.g., DoseSpot)
- **Payments:** Stripe (BAA); **Claims:** clearinghouse (837/835)
- **Notifications:** SES / Pinpoint / SNS (PHI-free)
- **Security/compliance:** KMS, CloudTrail, GuardDuty, Security Hub, AWS Config (HIPAA pack), Inspector, Macie, AWS Backup
- **Observability:** CloudWatch, X-Ray/OpenTelemetry
- **Frontend:** React + TypeScript (Vite) on S3/CloudFront
- **IaC/CI:** Terraform (or CDK-Python), GitHub Actions/CodePipeline, ECR
- **Accounts:** AWS Organizations — isolated dev/staging/prod; non-prod de-identified only

---

## 11. Phased Rollout (suggested)

1. **Phase 0 — Compliance foundation:** AWS Organizations, BAA, landing zone, VPC, KMS, IAM/SSO, logging/audit baseline, CI/CD, Terraform skeleton.
2. **Phase 1 — Core booking:** Registration, provider scheduling, appointment booking (Core API + Aurora + Cognito + notifications).
3. **Phase 2 — Video visits:** Chime SDK integration, waiting room, visit records.
4. **Phase 3 — Prescriptions:** e-Rx vendor integration + EPCS.
5. **Phase 4 — Billing:** Stripe payments + clearinghouse claims + reconciliation.
6. **Phase 5 — Hardening:** Pen test, HIPAA risk assessment, DR game-day, analytics (de-identified).
