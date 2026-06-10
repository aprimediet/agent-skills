# File Upload Feature — Technical Architecture

> Technical Architect | Depth: quick | Generated: 2026-06-10

## Source Breakdown

Built on a solution-architect capability breakdown for a file upload feature, **provided inline** in the task prompt (the librarian skill was not available this session, so nothing was retrieved or saved). It defines five capabilities: validation, upload/transfer, virus scanning, thumbnail generation, and storage/retrieval. Note that this feature includes asynchronous post-processing (scanning + thumbnails) — that shapes the architecture below.

- **File Upload Feature (inline)** — users upload images and PDFs up to 10MB; the system validates them (CAP-01), transfers them (CAP-02), scans for viruses (CAP-03), generates thumbnails for images (CAP-04), and stores them for retrieval (CAP-05).

> An agent with librarian access should retrieve the source breakdown with: **specs matching "file upload validation virus scan thumbnail storage"** and persist this architecture there afterward.

## Constraints & Assumptions

- **Scale & load**: **[assumed]** Typical web application — modest concurrent uploads (tens, not thousands at once). 10MB max per file **[stated]**. Images and PDFs only **[stated]**. No latency/availability targets given; assume interactive upload UX with async scan/thumbnail completion within seconds.
- **Team**: **[stated]** Small team. **[assumed]** Comfortable with mainstream web tooling (TypeScript/JavaScript); no exotic-language requirement; minimize operational surface.
- **Hosting**: **[assumed]** Single managed cloud (AWS used as the concrete default below); no on-prem requirement. Substitute equivalent managed services on GCP/Azure if that is the existing cloud.
- **Hard constraints**: **[assumed]** No special compliance regime stated (no HIPAA/PCI). Cost-sensitive — prefer managed services over self-hosted infrastructure.
- **Existing systems**: **[assumed]** A "typical web app" with its own auth and database; this feature is a module within it, not a standalone platform.

## Architecture Overview

- **Style**: **Modular feature within a monolith/modular monolith, plus a lightweight async worker tier** — synchronous path (validate, issue upload URL, write reference) lives in the app; scanning (CAP-03) and thumbnailing (CAP-04) run as background workers triggered by a storage event. A small team gets one deployable app plus a thin worker, not microservices.
- **Shape**: The browser uploads file bytes **directly to object storage** via a short-lived pre-signed URL issued by the backend, so large bytes never transit the app server. On upload completion the backend runs authoritative server-side validation (CAP-01) and writes a file-reference record with `status = pending`. The storage upload emits an event that fans out to a **queue** feeding two async workers: a **virus scanner** (CAP-03) and a **thumbnail generator** (CAP-04, images only). Each worker updates the reference status (`clean` / `infected` / `thumbnailed`). Retrieval (CAP-05) serves files and thumbnails through pre-signed GET URLs only once status is `clean`. A scheduled job sweeps orphaned/abandoned objects.

## Tech Stack

### Frontend
- **Recommendation**: TypeScript + the app's existing SPA framework (React assumed), using the browser-native **File API** + `fetch`/XHR with upload-progress events to PUT directly to the pre-signed storage URL. A small reusable upload component handles file picker, drag-and-drop, per-file progress, and retry, and **polls (or subscribes to) reference status** to show "scanning…", "ready", or "rejected" states.
- **Why**: CAP-02 needs client-side progress; direct-to-storage uploads expose native progress events. Client-side pre-checks (extension/size/type) give CAP-01 instant rejection before bytes move. Because CAP-03/CAP-04 are async, the UI must reflect post-upload processing state rather than treating "uploaded" as "done".
- **Alternatives**: Uppy or react-dropzone + tus — prefer if you later need resumable/chunked uploads for much larger files or flaky-network resilience; overkill for a 10MB cap.

### Backend / API
- **Recommendation**: TypeScript on **Node.js** as a module in the existing app, exposing: `POST /uploads` (validate context + return pre-signed PUT URL), `POST /uploads/:id/complete` (authoritative server-side validation + create reference with `status = pending`), `GET /uploads/:id` (status + pre-signed GET URL once `clean`). Use the app's existing framework (Express/Nest/Fastify).
- **Why**: Keeps the feature in the current codebase/deployment, shares existing auth middleware, keeps the server off the file byte path. Splitting issue vs. complete cleanly separates CAP-01's pre-upload check from the post-transfer check.
- **Alternatives**: A dedicated upload microservice — prefer only if uploads become a distinct scaling/ownership concern; unjustified for one feature on a small team.

### Data storage
- **File reference store (primary)**: **PostgreSQL** table (`file_references`: id, storage_key, original_filename, content_type, size_bytes, owner_id, uploaded_at, **scan_status** [pending|clean|infected], **thumbnail_status** [n/a|pending|ready], thumbnail_key, status). Relational with transactional updates as workers progress the record; easy queries for "ready" attachments. Reuse the app's existing database/engine if it already runs one — match it rather than add a second.
- **Object/blob store**: **S3-compatible object storage** holds originals and generated thumbnails (separate key prefixes). Pre-signed PUT for upload (CAP-02), pre-signed GET for retrieval (CAP-05).
- **Cache / search / analytics**: **Not needed** — attachment lists are small and queried by indexed owner/context ID; no search or analytics capability in the breakdown.

### Async / messaging
- **Recommendation**: **A queue/event tier is needed** (unlike a scan-free upload feature). On upload completion, a storage event (e.g., **S3 → SQS**, or an app-published message) enqueues a processing job; **worker(s)** consume it to run virus scan (CAP-03) and thumbnail generation (CAP-04). Use the cloud-native queue (SQS) with a Lambda or small container worker. A dead-letter queue captures repeated failures.
- **Why**: CAP-03 and CAP-04 are slow, CPU/IO-heavy, and must not block the upload response or hold the app server. Decoupling via a queue lets uploads complete fast while scanning/thumbnailing happen out-of-band, with retries and back-pressure. This is the core architectural difference driven by the scan + thumbnail capabilities.
- **Alternatives**: In-process background jobs (e.g., BullMQ on Redis) — prefer if you want to avoid cloud-specific queues or already run Redis; acceptable at this scale but couples processing to app instances.

### Authentication & authorization
- **Recommendation**: Reuse the app's **existing authentication system**; all upload/retrieval endpoints sit behind it. Authorization: the authenticated user must own/have access to the upload context before a pre-signed URL is issued; the reference stores `owner_id` for retrieval access checks. Pre-signed URLs are short-lived (e.g., 5 min).
- **Why**: Uploads and retrieval are per-user (CAP-02, CAP-05); access checks belong to the existing identity system. Short TTL prevents URL replay.
- **Alternatives**: None warranted — a separate identity system would fight the "typical web app" constraint.

### Infrastructure & hosting
- **Recommendation**: Deploy the app on its existing managed compute (assumed AWS — ECS/Fargate or a PaaS), object storage on **S3**, managed Postgres on **RDS**, queue on **SQS**, workers as **Lambda** (or small Fargate tasks). CDN (CloudFront) optionally fronts pre-signed GETs for downloads/thumbnails.
- **Why**: No new runtime for the synchronous path; the async tier is serverless/managed so a small team avoids running scanner/worker infrastructure full-time. Direct-to-storage upload means app compute doesn't scale with file size.
- **Alternatives**: Fully serverless (API Gateway + Lambda for the API too) — prefer if the rest of the app is already serverless; otherwise it fragments the deployment.

### CI/CD & developer tooling
- **Recommendation**: Reuse the existing pipeline (e.g., GitHub Actions) — lint, typecheck, unit + integration tests, deploy to staging then prod. Bucket config, **CORS**, lifecycle/cleanup rules, queue, and worker definitions as **IaC** (Terraform/CDK).
- **Why**: One feature shouldn't fork the toolchain. Bucket CORS is load-bearing for direct browser uploads and must be versioned, not console-clicked. The worker + queue topology benefits from reproducible IaC.
- **Alternatives**: None — match the team's existing pipeline.

### Observability
- **Recommendation**: Structured logs across the lifecycle (URL issued, validation pass/fail + reason, reference created, scan result, thumbnail result); metrics for **upload success rate**, **scan latency / backlog (queue depth)**, **scan-failure / infected rate**, and **thumbnail success rate**; alerts on queue backlog growth, DLQ messages, and infected-file detections.
- **Why**: The async tier can silently back up; queue depth and DLQ are the leading indicators. Infected-file events are security-relevant and worth alerting.
- **Alternatives**: Whatever the team already runs (CloudWatch, Datadog) — reuse it.

### Third-party services & integrations
- **Recommendation**: **Virus scanning engine** for CAP-03 — **ClamAV** packaged into the worker (open-source, no per-scan cost) as the default; or a managed scanning API/AWS-native scanning if available. **Thumbnail generation** for CAP-04 via **sharp** (libvips) for images in the worker; for **PDF** previews use a renderer (e.g., **pdf-to-image via pdfium/poppler**) to rasterize the first page.
- **Why**: ClamAV is the standard self-contained scanner and avoids per-file SaaS cost for a cost-sensitive small team. `sharp` is the fastest mainstream Node image library. PDFs are in scope, so "thumbnail" must cover rasterizing a PDF page, not just resizing images.
- **Alternatives**: Managed scanning SaaS (e.g., VirusTotal/commercial AV API) — prefer if you want signature updates and uptime managed for you, at per-scan cost. Managed image SaaS (Uploadcare/Imgix) — prefer to outsource transforms entirely.

### Security
- **Recommendation**: Server-side validation is authoritative — re-check size (≤10MB), extension allow-list, and **magic-byte/header content-type** (confirm actual image/PDF, not a disguised extension) after the object lands; client checks are UX only. **Quarantine until clean**: files are not retrievable (CAP-05) until CAP-03 marks them `clean`; infected files are deleted/quarantined and never served. Short-lived, single-object, content-length-bounded pre-signed URLs. Encryption at rest (SSE) and TLS in transit. Generate **opaque storage keys** (never use the user filename as a key — avoid path traversal). Tight bucket CORS (only your origin), no public bucket ACLs — downloads via pre-signed GET. Run scanner/thumbnail workers with least privilege; treat PDF rendering as untrusted input (sandbox the renderer).
- **Why**: CAP-01 must defend against disguised file types; CAP-03 exists specifically to keep malware out, so the serve-only-when-clean gate is essential. PDF rasterization parses untrusted files and is a real attack surface, hence sandboxing.
- **Compliance**: None special **[assumed]**; the above is baseline good hygiene.

## Capability → Tech Mapping

| Capability | Implemented by | Notes |
|-----------|----------------|-------|
| CAP-01 Validation | Client-side pre-check (extension/size/type) + authoritative server-side re-validation in `POST /uploads/:id/complete` (size ≤10MB, image/PDF allow-list, magic-byte header) | Two validation moments: before upload (UX) and after transfer (authoritative). Header check rejects disguised extensions. |
| CAP-02 Upload / transfer | Frontend upload component (File API + progress) → pre-signed PUT to S3; `POST /uploads` issues the URL after an auth/access check | Bytes go browser→storage directly; app server stays off the data path; native progress events. |
| CAP-03 Virus scan | Storage event → SQS → scanner worker (ClamAV) updates `scan_status`; infected files quarantined/deleted; files served only when `clean` | Async so uploads aren't blocked; DLQ + retries; infected-rate alerting. |
| CAP-04 Thumbnail generation | Same queue → thumbnail worker; `sharp` resizes images, PDF first page rasterized (pdfium/poppler); writes `thumbnail_key`, sets `thumbnail_status = ready` | Images and PDFs both produce a preview; runs only after/with scan. |
| CAP-05 Storage / retrieval | S3 stores originals + thumbnails; Postgres `file_references` row links metadata; `GET /uploads/:id` returns pre-signed GET URL once `clean`; CDN optional | Retrieval gated on clean status; opaque keys; access check on owner/context. |

## Key Architecture Decisions

### AD-01: Direct-to-storage upload via pre-signed URLs

- **Decision**: The browser uploads file bytes directly to object storage using a short-lived pre-signed URL; the app server never proxies the file body.
- **Context**: CAP-02 requires up-to-10MB uploads with live progress on cost-sensitive managed compute.
- **Rationale**: Keeps transfers off app compute (lower memory/cost, no request-size limits), gives native browser progress, scales with the storage service. Standard pattern for S3-class stores.
- **Tradeoffs**: Validation splits into pre-issue and post-upload phases; bucket CORS + URL scoping must be configured carefully; brief orphan window handled by a cleanup job.

### AD-02: Async worker tier (queue) for scanning and thumbnailing

- **Decision**: Run CAP-03 (virus scan) and CAP-04 (thumbnails) as background workers fed by a queue triggered on upload completion, rather than synchronously in the upload request.
- **Context**: Scanning and thumbnailing are slow and resource-heavy; the upload response must stay fast; a small team wants minimal always-on infrastructure.
- **Rationale**: Decoupling lets uploads complete immediately while heavy processing runs out-of-band with retries, back-pressure, and a DLQ. Serverless workers (Lambda) keep the always-on cost near zero. This is the decisive structural choice that the scan + thumbnail capabilities force.
- **Tradeoffs**: Introduces eventual consistency — files exist but aren't "ready" until processed, so the UI and retrieval must handle a `pending` state. Adds queue/worker components to operate and monitor (queue depth, DLQ).

### AD-03: Quarantine-until-clean retrieval gate

- **Decision**: Files are not retrievable (CAP-05) until the scanner (CAP-03) marks them `clean`; infected files are never served.
- **Context**: The whole point of CAP-03 is to prevent serving malware to other users.
- **Rationale**: A status gate on retrieval is the simplest correct enforcement; without it, the async scan provides no actual protection during the processing window.
- **Tradeoffs**: A short delay between upload and availability; the UI must show a "scanning…" state. Acceptable and expected for scanned uploads.

## Risks & Tradeoffs

- **Trusting client metadata**: client-reported MIME/extension is forgeable. Mitigation — authoritative server-side magic-byte validation; client checks are UX-only.
- **Scan backlog / latency**: a burst of uploads can back the queue up, delaying availability. Mitigation — monitor queue depth, scale workers (Lambda concurrency or more Fargate tasks), alert on backlog and DLQ.
- **PDF rendering as attack surface**: rasterizing untrusted PDFs can exploit the renderer. Mitigation — run the thumbnail worker with least privilege and sandbox the renderer; cap render time/resources.
- **Orphaned objects**: abandoned/failed uploads leave bytes with no usable reference. Mitigation — scheduled cleanup of unreferenced objects past a grace period; track the count.
- **Eventual-consistency UX**: "uploaded" ≠ "ready". Mitigation — explicit `pending`/`clean`/`infected`/`thumbnailed` states surfaced to the UI via polling/subscription.
- **ClamAV signature freshness**: an out-of-date scanner misses new malware. Mitigation — keep signature DB updated (scheduled `freshclam`/image rebuild); or use a managed scanning API (see research flag).

## Research Suggestions

High-stakes or uncertain technology choices to validate with the researcher skill (researcher was unavailable this session):

- **Virus scanning approach: self-hosted ClamAV vs. managed scanning API** — high-stakes security and ops choice; affects detection quality, cost, and maintenance for a small team. Suggested researcher query: *"Virus/malware scanning for user-uploaded files in web apps (2026): self-hosted ClamAV vs. managed scanning APIs / AWS-native scanning — detection efficacy, signature freshness, cost, and operational burden for a small team."*
- **File-type safety and content validation** — gates what users can upload safely. Suggested researcher query: *"File upload security best practices (2026): magic-byte/header content validation, MIME whitelisting, disguised-extension detection, and safe handling of user-uploaded images and PDFs."*
- **Safe PDF rasterization for thumbnails** — untrusted-PDF rendering is an attack surface. Suggested researcher query: *"Securely rendering/rasterizing untrusted PDF first-page thumbnails server-side (pdfium vs. poppler vs. managed services): sandboxing and resource limits."*

## Open Questions

- Which **cloud/object-storage provider** is the app already on? (Determines pre-signed URL specifics and managed-service names — AWS assumed above.)
- Confirm the exact **allowed types and size limit** beyond "images and PDFs, 10MB" (which image formats? animated? multi-page PDFs?) — drives the validation allow-list.
- **Thumbnail spec**: dimensions, formats, and whether PDFs need first-page-only or multi-page previews (affects CAP-04 worker scope) — if richer than a single preview, flag back to solution-architect as a possible capability expansion.
- Should **infected files** be hard-deleted or quarantined for audit? (Affects CAP-03 handling and any retention policy.)
- Is there a **per-user/per-context storage quota** to enforce? If yes, the check belongs in `POST /uploads` — flag back to solution-architect as it may be a new capability.

## Next Steps

1. Confirm the existing cloud/storage provider and whether it supports pre-signed direct uploads; if not, revisit AD-01.
2. Spike the full pipeline: issue URL → browser PUT with progress → complete callback → reference row → storage event → queue → scan + thumbnail workers update status, including bucket CORS in staging.
3. Define validation config (allowed image/PDF types, 10MB bound) and implement authoritative server-side magic-byte checking.
4. Stand up the scanner (ClamAV worker) and thumbnail worker (sharp + PDF rasterizer), with DLQ, retries, and the quarantine-until-clean gate.
5. Add observability: upload success rate, queue depth, scan/thumbnail success + infected rate, and alerts on backlog/DLQ/infected detections; add the orphan-cleanup job.
6. Run the three research queries above before finalizing the scanning approach and validation/thumbnail policies.

---
*Technical architecture produced by technical-architect skill. Use the librarian skill to persist this artifact.*
