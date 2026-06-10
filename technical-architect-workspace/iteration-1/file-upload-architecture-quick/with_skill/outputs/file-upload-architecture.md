# File Upload Feature — Technical Architecture

> Technical Architect | Depth: quick | Generated: 2026-06-10

## Source Breakdown

Built on a capability breakdown for the File Upload Feature, **provided inline in the prompt** (the librarian skill was not available this session, so nothing was retrieved from stored specs). The breakdown defines five capabilities: validation, upload/transfer, virus scanning, thumbnail generation, and storage/retrieval.

- **File Upload Feature (inline breakdown)** — users upload images and PDFs up to 10 MB; the system validates them (CAP-01), transfers them (CAP-02), scans for viruses (CAP-03), generates thumbnails for images (CAP-04), and stores them for retrieval (CAP-05).

An agent with librarian access should retrieve the canonical version with: `specs` matching `"file upload validation virus scan thumbnail storage"`. If a richer solution-architect breakdown exists, prefer it over this inline summary.

## Constraints & Assumptions

- **Scale & load**: **[assumed]** Typical web application — modest concurrent uploads (tens, not thousands at once). 10 MB max per file (**[stated]**), images and PDFs only (**[stated]**). No explicit latency/availability target; assume sub-few-second perceived upload, with scanning/thumbnailing allowed to complete asynchronously.
- **Team**: **[stated]** Small team. **[assumed]** Comfortable with mainstream web tooling (TypeScript/JavaScript); no exotic-language requirement.
- **Hosting**: **[assumed]** Single managed cloud (AWS used as the concrete default below). No on-prem requirement. Substitute equivalent managed services on GCP/Azure if that is the existing cloud.
- **Hard constraints**: **[assumed]** No special compliance regime (no HIPAA/PCI/GDPR-specific controls beyond good hygiene). Cost-sensitive — prefer managed services over self-hosted infrastructure.
- **Existing systems**: **[assumed]** Typical web app with an existing auth system and relational database the feature plugs into; no pre-existing storage or scanning service is assumed (this design provides them).

## Architecture Overview

- **Style**: **Modular monolith for the synchronous path + a lightweight async worker tier for post-upload processing.** The upload feature is a backend module exposing a small API plus a frontend widget; virus scanning (CAP-03) and thumbnail generation (CAP-04) run as background workers driven by a storage event/queue, so they never block the user's upload. This is the smallest shape that honors CAP-03 and CAP-04 — they are the reason an async tier exists here, unlike a scan-free upload feature.
- **Shape**: The browser uploads file bytes **directly to object storage** via a short-lived pre-signed URL issued by the backend, so large bytes never transit the app server. The backend does three small synchronous steps: (1) validate the request and issue the pre-signed URL, (2) on the client's "done" callback, run authoritative server-side validation (size, type allow-list, magic-byte header check) and write a `file_references` row with status `pending_scan`, (3) the object landing in storage emits an event onto a queue. A **worker** consumes the queue: it runs the virus scan (CAP-03), and for images generates a thumbnail (CAP-04), then flips the reference status to `available` (or `quarantined` on a positive scan). Retrieval (CAP-05) reads the reference by context/owner and serves the file/thumbnail via pre-signed GET. A scheduled job sweeps orphaned objects (uploaded but never referenced).

## Tech Stack

### Frontend
- **Recommendation**: TypeScript + the team's existing SPA framework (React assumed), using the browser-native **File API** + **`fetch`/XMLHttpRequest with upload progress** to push directly to the pre-signed storage URL. A small reusable upload component handles the file picker, drag-and-drop, per-file progress, retry, and a post-upload "scanning…" / "thumbnail ready" state.
- **Why**: CAP-02 needs client-side progress; direct-to-storage uploads expose native progress events. Client-side pre-checks (extension/size) give CAP-01 instant rejection before any bytes move. The async scan/thumbnail (CAP-03/04) means the UI must show a pending→ready transition, which the component polls or receives via a status endpoint.
- **Alternatives**: Uppy or react-dropzone + tus — prefer if you later need resumable/chunked uploads for much larger files or flaky-network resilience; overkill for a 10 MB cap.

### Backend / API
- **Recommendation**: TypeScript on **Node.js** as a module inside the existing application, exposing: `POST /uploads` (validate context + return pre-signed URL), `POST /uploads/:id/complete` (server-side validation + create reference with `pending_scan`), and `GET /uploads/:id` (status + retrieval links for CAP-05). Use the team's existing app framework (Express/NestJS/Fastify).
- **Why**: Keeps the feature in the current codebase and deployment, shares existing auth middleware, and keeps the server off the file's byte path. The status endpoint exposes the async result of CAP-03/04 to the frontend.
- **Alternatives**: A dedicated upload microservice — prefer only if uploads become a distinct scaling or team-ownership concern; unjustified for one feature on a small team.

### Data storage
- **File reference store (primary)**: **PostgreSQL** table `file_references` (id, storage_key, thumbnail_key, original_filename, content_type, size_bytes, owner_id, context_type, context_id, status [`pending_scan`|`available`|`quarantined`|`failed`], scan_result, uploaded_at, processed_at). PostgreSQL because the data is relational, CAP-05 needs transactional, indexed lookups by owner/context, and the status field is the source of truth for the async pipeline. **Alternative**: reuse whatever the existing app already uses — match it rather than introduce a second database.
- **Object/blob store**: **S3 (or S3-compatible) object storage** holds originals and generated thumbnails (separate key prefixes). Pre-signed PUT for upload (CAP-02), pre-signed GET for retrieval (CAP-05). This is the natural home for the bytes and the trigger source for the processing pipeline.
- **Cache / search / analytics**: **Not needed** — retrieval is by indexed context/owner ID; the breakdown has no search or analytics capability.

### Async / messaging
- **Recommendation**: **A queue + worker.** Object-created events from storage (S3 event notifications) land on **SQS**; a worker (container or Lambda) consumes them to run CAP-03 (virus scan) and CAP-04 (thumbnail generation), then updates the reference status. Use a dead-letter queue for repeated failures and visibility-timeout-based retries.
- **Why**: This is the layer the scan-free file-upload pattern omits — but CAP-03 and CAP-04 are explicitly in scope here. Scanning can take seconds and thumbnailing is CPU work; doing them asynchronously keeps CAP-02's upload fast and lets each retry independently. The queue decouples the user-facing path from processing latency and antivirus availability.
- **Alternatives**: A simpler in-process background job/cron poll over `pending_scan` rows — prefer only if you want to avoid managed queue infrastructure entirely on a very small footprint; loses the natural event trigger and per-message retry semantics.

### Authentication & authorization
- **Recommendation**: Reuse the **existing authentication system**; every endpoint runs behind it. Authorization: the authenticated user must have access to the target context before a pre-signed URL is issued; the reference stores `owner_id` + context for access checks on retrieval (CAP-05). Quarantined files (CAP-03) are never served to anyone.
- **Why**: Upload and retrieval both require an access check against the existing app's identity. Pre-signed URLs are short-lived (e.g., 5 min) so the grant can't be replayed.
- **Alternatives**: None warranted — a separate identity system would fight a typical existing-auth setup.

### Infrastructure & hosting
- **Recommendation**: Deploy the API as part of the existing application on its current managed compute (assumed AWS — ECS/Fargate or a PaaS), with **S3** for objects, **RDS Postgres** for references, **SQS** for the pipeline, and the scan/thumbnail **worker on Fargate or Lambda**. CloudFront optionally fronts pre-signed GETs for downloads/thumbnails.
- **Why**: No new runtime for the synchronous path; the worker is the one genuinely new compute unit, justified by CAP-03/04. Managed services keep ops light for a small team, and direct-to-storage upload means app compute doesn't scale with file size.
- **Alternatives**: Fully serverless (API Gateway + Lambda for API and worker) — prefer if the rest of the app is already serverless; Lambda is an especially good fit for the bursty thumbnail/scan worker. Note: ClamAV-on-Lambda has cold-start and package-size friction — see Research Suggestions.

### CI/CD & developer tooling
- **Recommendation**: Reuse the existing pipeline (e.g., GitHub Actions) — lint, typecheck, unit + integration tests, deploy to staging then prod. Bucket, CORS config, lifecycle/cleanup rules, SQS queue + DLQ, and the worker are defined as **IaC** (Terraform/CDK).
- **Why**: One feature shouldn't introduce a parallel toolchain. Bucket CORS and the S3→SQS event wiring are load-bearing for the flow, so they belong in versioned IaC, not console clicks.
- **Alternatives**: None — match the team's existing pipeline.

### Observability
- **Recommendation**: Structured logs for each step (URL issued; validation pass/fail with reason; reference created; scan started/result; thumbnail generated/failed). Metrics: upload success rate, time-to-complete, **scan queue depth and processing latency**, scan-positive count, thumbnail failure rate. Alerts on queue backlog, rising scan/thumbnail failures, and any DLQ message.
- **Why**: The async pipeline (CAP-03/04) introduces failure modes invisible to the user, so queue health and processing outcomes must be measured. Validation-failure reasons (CAP-01) help tune the allow-list.
- **Alternatives**: Whatever the team already runs (CloudWatch, Datadog, etc.) — reuse it.

### Third-party services & integrations
- **Recommendation**: **Antivirus engine** for CAP-03 — self-hosted **ClamAV** in the worker is the cost-friendly default; a managed scanning API is the alternative. **Image library** for CAP-04 — **sharp** (libvips) for fast Node thumbnail generation. Object storage (S3) is the only other dependency.
- **Why**: CAP-03 needs a real scanning engine; ClamAV is free and embeddable but you own signature updates and runtime sizing. sharp is the standard high-performance Node image resizer and handles common image formats; PDF thumbnails (CAP-04 for PDFs, if required) need a PDF rasterizer — see Open Questions.
- **Alternatives**: Managed AV/content-safety APIs (e.g., a cloud malware-scan service or VirusTotal-style API) — prefer if you want to outsource signature maintenance and accept per-scan cost/latency and an external dependency.

### Security
- **Recommendation**: Server-side validation is authoritative — re-check size, an **allow-list of images + PDF**, and **magic-byte/header content-type** after the object lands; client checks are UX only. Files are `pending_scan` and **not retrievable** until CAP-03 clears them; a positive scan sets `quarantined` and the object is deleted or isolated. Short-lived, single-object, content-length-bounded pre-signed URLs. SSE encryption at rest, TLS in transit. Generate opaque storage keys (never use the user filename as a key — avoids path traversal); store the original filename as data only. Tight bucket CORS (your origin only), no public ACLs — all access via pre-signed GETs. Set strict `Content-Type`/`Content-Disposition` on download to prevent inline execution of disguised content.
- **Why**: CAP-01 must defend against disguised extensions (header analysis) and CAP-03 is the gate before any file is exposed — so "scan before serve" is a hard sequencing rule, not just hygiene. PDF and image handling are common malware vectors, which is why the allow-list and quarantine flow matter.
- **Compliance**: None special **[assumed]**; the above is baseline good hygiene.

## Capability → Tech Mapping

| Capability | Implemented by | Notes |
|-----------|----------------|-------|
| CAP-01 Validation | Client-side pre-check (extension/size) for instant UX rejection + authoritative **server-side** re-validation in `POST /uploads/:id/complete` (size ≤ 10 MB, image+PDF allow-list, magic-byte header) | Two validation moments: before upload (UX) and after transfer (authoritative). Header check catches disguised extensions; zero-byte / unreadable files rejected. |
| CAP-02 Upload / transfer | Frontend upload component (File API + progress events) → pre-signed PUT to S3; `POST /uploads` issues the URL after an auth/access check | Bytes go browser→storage directly; app server stays off the data path, so transfer scales with storage, not app compute. |
| CAP-03 Virus scan | S3 object-created event → SQS → worker runs ClamAV (or managed AV); reference status `pending_scan` → `available` or `quarantined`; positive scan isolates/deletes the object | Asynchronous so it never blocks upload; DLQ + retries for AV unavailability. File is never served until cleared. |
| CAP-04 Thumbnail generation | Same worker: for image content types, generate a thumbnail with **sharp**, store under a `thumbnails/` prefix, record `thumbnail_key` | Runs only after a clean scan. PDF thumbnailing needs a rasterizer (see Open Questions). Thumbnail failure is non-fatal — file can still be `available`. |
| CAP-05 Storage / retrieval | Originals + thumbnails in S3; `file_references` row in Postgres as source of truth; `GET /uploads/:id` returns status + pre-signed GET URLs after an access check; CloudFront optional in front | Quarantined/pending files are not retrievable; retrieval is by indexed owner/context. |

## Key Architecture Decisions

### AD-01: Direct-to-storage upload via pre-signed URLs

- **Decision**: The browser uploads file bytes directly to object storage using a short-lived pre-signed URL; the application server never proxies the file body.
- **Context**: CAP-02 requires uploads up to 10 MB with live progress on cost-sensitive managed compute.
- **Rationale**: Keeps transfers off app compute (lower memory/cost, no request-size limits to fight), gives native browser progress events, and scales with the storage service. Standard pattern for S3-class stores, and the object-created event is the natural trigger for the CAP-03/04 pipeline.
- **Tradeoffs**: Validation must split into pre-issue and post-upload phases (the server can't inspect bytes in flight); bucket CORS and URL scoping must be configured carefully; a brief orphan window exists, handled by the cleanup job.

### AD-02: Async worker tier (queue + worker) for scan and thumbnail

- **Decision**: Run virus scanning (CAP-03) and thumbnail generation (CAP-04) asynchronously on a worker driven by storage events on SQS, with a `pending_scan` → `available`/`quarantined` status model; do not serve files until scanned.
- **Context**: CAP-03 and CAP-04 are explicitly in scope; scanning has variable latency and external dependency, thumbnailing is CPU-bound — neither belongs on the synchronous upload path.
- **Rationale**: Decouples user-facing upload speed (CAP-02) from processing time and AV availability; gives independent per-message retry and a DLQ; lets the worker scale separately (good fit for bursty load and for Lambda). The status field makes the pipeline observable and the "scan before serve" security rule enforceable.
- **Tradeoffs**: Introduces genuinely new infrastructure (queue + worker + DLQ) and eventual-consistency UX (a brief pending state). This is the deliberate cost of having scanning/thumbnailing in scope; it is the smallest tier that satisfies both capabilities safely.

## Risks & Tradeoffs

- **Scan latency / AV availability**: a slow or down antivirus engine backs up the queue and delays files reaching `available`. Mitigation — async pipeline with DLQ + retries, queue-depth alerting, and a clear pending UX; consider a managed AV API if self-hosted ClamAV ops become a burden.
- **Serving an unscanned/malicious file**: the core safety risk for CAP-03. Mitigation — hard rule that only `available` (clean-scanned) files are retrievable; quarantine isolates positives; this sequencing is enforced in `GET /uploads/:id`.
- **Trusting client metadata**: client-reported MIME/extension is forgeable. Mitigation — authoritative server-side magic-byte validation; client checks are UX-only.
- **PDF thumbnailing gap**: sharp handles images but not PDF rasterization; if PDF thumbnails are required, CAP-04 needs an extra dependency (e.g., pdf-to-image via a rasterizer). Mitigation — clarify scope (Open Questions) before committing the library set.
- **Orphaned objects**: abandoned/failed uploads leave bytes with no reference. Mitigation — scheduled cleanup of unreferenced objects past a grace period; track the count.
- **Pre-signed URL misuse / CORS drift**: over-scoped URLs or wrong bucket CORS break or expose the flow. Mitigation — short TTL, single key, content-length bound, HTTPS only; manage CORS + event wiring in IaC and test in staging.

## Research Suggestions

High-stakes or uncertain technology choices to validate with the researcher skill:

- **Virus-scanning approach for user uploads** — high-stakes; gates safety and shapes the worker's runtime/cost. Suggested researcher query: *"Best-practice virus scanning for user-uploaded files in a web app (2026): self-hosted ClamAV vs managed malware-scan APIs — accuracy, signature-update operations, scan latency, and running ClamAV on AWS Lambda vs Fargate."*
- **File-type safety and content validation** — gates what users can safely upload. Suggested researcher query: *"File upload security best practices — magic-byte/header content validation, MIME allow-listing for images and PDFs, disguised-extension detection, and safe serving of user-uploaded files (2026)."*
- **PDF + image thumbnail generation in Node** — confirms the CAP-04 library set. Suggested researcher query: *"Generating thumbnails for both images and PDFs in a Node.js worker — sharp/libvips for images and options for PDF rasterization, performance and dependency footprint."*

## Open Questions

- Which **cloud / object storage provider** is the app already on? (Determines pre-signed URL specifics, the event→queue mechanism, and exact service names — AWS assumed above.)
- Does **CAP-04 (thumbnails) apply to PDFs**, or only to images? PDFs need a rasterizer beyond sharp; this changes the dependency set. (Flag back to solution-architect if the breakdown is silent.)
- On a **positive virus scan**, what is the desired behavior — delete, quarantine-and-notify, or surface to an admin? (Borders on a new capability; flag to solution-architect.)
- Is there a **per-user or per-context storage quota** to enforce? If yes, the quota check belongs in `POST /uploads` — likely a new capability for solution-architect.
- Confirm the **exact allowed image formats** (e.g., JPEG/PNG/WebP/GIF) behind "images" — drives the validation allow-list and thumbnail handling.

## Next Steps

1. Confirm the existing cloud/storage provider and whether it supports pre-signed direct uploads and object-created events; if not, revisit AD-01/AD-02.
2. Decide the virus-scanning approach (ClamAV self-hosted vs managed API) — run the research query first, as it shapes the worker runtime.
3. Spike the full pipeline end to end: issue URL → browser PUT with progress → complete callback (validate + `pending_scan`) → S3 event → SQS → worker (scan + thumbnail) → status `available` → retrieval via pre-signed GET, including bucket CORS in staging.
4. Clarify PDF-thumbnail and positive-scan-handling scope with solution-architect before finalizing the worker.
5. Add orphan-cleanup job, and the success-rate / queue-depth / processing-latency metrics + alerts.

---
*Technical architecture produced by technical-architect skill. Use the librarian skill to persist this artifact.*
