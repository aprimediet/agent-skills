# File Upload Feature — Technical Architecture

> Technical Architect | Depth: quick | Generated: 2026-06-10

## Source Breakdown

Built on a solution-architect capability breakdown for a file upload feature, **provided inline** (the librarian skill was not available this session). It defines five capabilities: validation, upload/transfer, virus scan, thumbnail generation, and storage/retrieval. An agent with librarian access should retrieve the full breakdown from category **specs**, keywords *"file upload validation virus scan thumbnail storage"*, and link it here.

- **File Upload Feature (inline)** — users upload images and PDFs up to 10 MB; the system validates them, scans for viruses, generates thumbnails for images, and stores them for retrieval (CAP-01 validation, CAP-02 upload/transfer, CAP-03 virus scan, CAP-04 thumbnail generation, CAP-05 storage/retrieval).

## Constraints & Assumptions

- **Scale & load**: **[assumed]** Typical web application, modest concurrent uploads (tens, not thousands at once). 10 MB max per file **[stated]**. No explicit latency/availability targets given; assume non-blocking UX is desired (scan + thumbnail should not stall the user).
- **Team**: **[stated]** Small team. **[assumed]** Comfort with mainstream web tooling (TypeScript/JavaScript), no exotic-language requirement, limited ops capacity — prefer managed services over self-hosted infrastructure.
- **Hosting**: **[assumed]** Single managed cloud (AWS used as the concrete default below; substitute the GCP/Azure equivalents if that is the existing cloud). No on-prem requirement.
- **Hard constraints**: **[assumed]** No special compliance (no HIPAA/PCI/GDPR-specific controls beyond good hygiene). Cost-sensitive.
- **Existing systems**: **[assumed]** A typical web app with an existing auth system and a relational database; this feature plugs into them rather than standing alone.

## Architecture Overview

- **Style**: **Modular monolith + a small async processing tier.** The synchronous request path (validate, issue upload URL, record reference) lives as a module inside the existing app; the slow/heavy work (CAP-03 virus scan, CAP-04 thumbnail generation) runs off a queue on background workers. The five capabilities — specifically scanning and thumbnailing — justify exactly one async tier, no more.
- **Shape**: The browser uploads bytes **directly to object storage** via a short-lived pre-signed URL issued by the backend, so files never transit the app server. On the client's "done" callback the backend runs authoritative server-side validation (CAP-01) on the stored object's header/metadata, writes a `file_references` row with status `pending`, and enqueues a processing job. A **worker** consumes the queue: it virus-scans the object (CAP-03), and if the file is a clean image, generates a thumbnail (CAP-04) and stores it back. On success the reference flips to `ready` and becomes retrievable (CAP-05); on infection or failure it flips to `quarantined`/`failed` and the object is deleted. Retrieval serves files and thumbnails through pre-signed GETs, optionally behind a CDN.

## Tech Stack

### Frontend
- **Recommendation**: TypeScript + the team's existing SPA framework (React assumed), using the browser-native **File API** + **`fetch`/XMLHttpRequest with upload progress** to push directly to the pre-signed storage URL. A small reusable upload component handles file picker, drag-and-drop, progress bar, client-side pre-checks, and polling/subscribing for processing status.
- **Why**: CAP-02 needs a progress indication during transfer; direct-to-storage uploads expose native progress events. Client-side extension/size pre-checks give CAP-01 instant rejection before any bytes move. Because CAP-03/CAP-04 are async, the UI must reflect a `pending → ready` state — hence status polling.
- **Alternatives**: Uppy (or react-dropzone + tus) — prefer if you later need resumable/chunked uploads for much larger files or flaky-network resilience; overkill for a 10 MB cap.

### Backend / API
- **Recommendation**: TypeScript on **Node.js** as a module inside the existing application, exposing: `POST /uploads` (validate context + return pre-signed PUT URL), `POST /uploads/:id/complete` (authoritative validation, create `pending` reference, enqueue processing job), and `GET /uploads/:id` (status + retrieval URLs). Use the existing app framework (Express/Nest/Fastify).
- **Why**: Keeps the synchronous path in the current codebase and deployment, shares existing auth middleware, and keeps the server off the file's byte path. The complete-callback is the natural place to gate validation (CAP-01) and kick off async processing (CAP-03/CAP-04).
- **Alternatives**: A dedicated upload microservice — prefer only if uploads become a distinct scaling or team-ownership concern; unjustified for one feature on a small team.

### Data storage
- **File reference store (primary)**: **PostgreSQL** table `file_references` (id, storage_key, thumbnail_key, original_filename, content_type, size_bytes, owner_id, context_type, context_id, status [`pending`/`scanning`/`ready`/`quarantined`/`failed`], scan_result, created_at, updated_at). Relational because CAP-05 needs transactional reference records, status transitions, and indexed lookup by owner/context. Alternative: reuse whatever DB the app already runs — match it rather than add a second database.
- **Object/blob store**: **S3-compatible object storage** holds original bytes and generated thumbnails (separate key prefixes, e.g. `originals/` and `thumbnails/`). Pre-signed PUT for upload, pre-signed GET for retrieval. Natural home for CAP-02's bytes, CAP-04's thumbnails, and CAP-05's storage.
- **Cache / search / analytics**: **Not needed** — retrieval is by indexed reference ID/context; no search or analytics capability in the breakdown.

### Async / messaging
- **Recommendation**: A **managed queue (AWS SQS)** plus a small pool of **background workers** (containers or Lambda) that consume one job per uploaded file and run CAP-03 then CAP-04. Use a **dead-letter queue** for jobs that repeatedly fail.
- **Why**: This is the layer the five-capability breakdown demands. Virus scanning and image thumbnailing are slow, CPU/IO-heavy, and must not block the user's upload response — so they run asynchronously. A queue decouples upload throughput from processing throughput and gives retry/DLQ for transient failures.
- **Alternatives**: Storage event notifications (S3 → SQS/Lambda) to trigger processing without an explicit enqueue call — clean and event-driven; prefer if you'd rather react to object-created events than enqueue from the API. For a multi-step pipeline with branching (scan → conditional thumbnail), an explicit job with internal steps is simpler to reason about than chained events at this scale.

### Authentication & authorization
- **Recommendation**: Reuse the **existing authentication system**; every endpoint runs behind it. Authorization: the authenticated user must have access to the target context before a pre-signed URL is issued; the reference stores `owner_id` + context for access checks on retrieval. Files are only retrievable (CAP-05) once status is `ready`.
- **Why**: Uploads are tied to a user/session and retrieval must be access-controlled. Pre-signed URLs are short-lived (e.g., 5 min) so a grant can't be replayed. Gating retrieval on `ready` ensures unscanned/infected files are never served (CAP-03 safety).
- **Alternatives**: None warranted — introducing a separate identity system would fight the existing-systems assumption.

### Infrastructure & hosting
- **Recommendation**: Deploy the API as part of the existing app on its current managed compute (assumed AWS — ECS/Fargate or equivalent PaaS). Run workers as a separate, independently-scalable service (Fargate tasks or Lambda) so processing load doesn't compete with web request handling. Object storage on S3, managed Postgres on RDS. CDN (CloudFront) optionally fronts pre-signed GETs for downloads/thumbnails.
- **Why**: Separating worker compute from web compute lets scanning/thumbnailing scale (or burst) independently — important because they're the heavy part. Managed services keep ops light for a small team. Direct-to-storage upload means web compute doesn't scale with file size.
- **Alternatives**: Fully serverless (API Gateway + Lambda for the API, Lambda workers) — prefer if the rest of the app is already serverless; note Lambda's image-processing memory/time limits and clamAV cold-start cost. Otherwise it fragments the deployment for no gain.

### CI/CD & developer tooling
- **Recommendation**: Reuse the existing pipeline (e.g., GitHub Actions) — lint, typecheck, unit + integration tests, deploy to staging then prod. Bucket config, CORS, lifecycle rules, the queue, the DLQ, and worker service defined as **IaC** (Terraform/CDK). The worker (with its scanning engine) is a container image built and versioned in the same pipeline.
- **Why**: One feature shouldn't introduce a parallel toolchain. CORS on the bucket and the queue wiring are load-bearing for the flow, so they belong in versioned IaC, not console clicks. The virus-scanning engine and its signature DB are best baked/updated via the image build.
- **Alternatives**: None — match the team's existing pipeline.

### Observability
- **Recommendation**: Structured logs across the path (URL issued; validation pass/fail with reason; job enqueued; scan result; thumbnail generated; reference `ready`/`quarantined`/`failed`). Metrics: upload success rate, time-to-`ready` (end-to-end latency through the async pipeline), scan-infection rate, thumbnail-failure rate, queue depth, and DLQ count. Alert on rising queue depth (workers falling behind), DLQ growth, and any infection detections.
- **Why**: The async pipeline introduces a latency dimension (time-to-`ready`) and failure modes (stuck queue, poison jobs) that are invisible without metrics. Infection detections are security-relevant and should alert.
- **Alternatives**: Whatever the team already runs (CloudWatch, Datadog, etc.) — reuse it.

### Third-party services & integrations
- **Recommendation**: **Virus scanning engine** — self-hosted **ClamAV** running inside the worker (open-source, no per-scan cost) is the default for CAP-03. **Thumbnail generation** — **sharp** (libvips) in the Node worker for CAP-04 (fast, handles common image formats; PDFs get a generic icon or are skipped unless PDF-preview is in scope). Object storage as above. No payment/email SaaS needed.
- **Why**: ClamAV keeps scanning in-house and cost-free, fitting the cost-sensitive assumption; sharp is the standard high-performance image thumbnailer in the Node ecosystem. Both run in the worker, off the request path.
- **Alternatives**: A managed scanning API (e.g., VirusTotal, Cloudmersive) — prefer if you want broader/multi-engine detection and can accept per-scan cost and sending files to a third party. A managed media service (Cloudinary, imgproxy, AWS-native image processing) for CAP-04 — prefer if image transforms grow beyond simple thumbnails. **These two choices are high-stakes — see Research Suggestions.**

### Security
- **Recommendation**: Server-side validation is authoritative — re-check size (≤10 MB), extension allow-list (images + PDF only), and **magic-byte/header content-type** after the object lands; client checks are UX only. Pre-signed URLs are short-lived, single-object, content-length-bounded. **Files are not served until they pass virus scan** (status gate). Quarantine or delete infected objects immediately. Encryption at rest (SSE) and TLS in transit. Generate opaque storage keys (never use the user filename as a key — avoids path traversal); store original filename as data only. Tight bucket CORS (your origin only), no public bucket ACLs — downloads via pre-signed GET. Run thumbnail generation with resource limits and decompression-bomb guards (sharp pixel/size limits) since it parses untrusted image bytes.
- **Why**: CAP-01 must defend against disguised extensions (header analysis); CAP-03 is itself a security control whose value depends on never serving a file before it's scanned. Image parsing (CAP-04) and PDF handling are themselves attack surfaces, hence resource limits and the scan-before-process ordering.
- **Compliance**: None special **[assumed]**; the above is baseline good hygiene.

## Capability → Tech Mapping

| Capability | Implemented by | Notes |
|-----------|----------------|-------|
| CAP-01 Validation | Client-side pre-check (extension/size) for instant UX rejection + authoritative **server-side** re-validation in `POST /uploads/:id/complete` (size ≤10 MB, images+PDF allow-list, magic-byte header) | Header check catches disguised extensions; client check is UX only, never trusted. Failure deletes the stored object and returns the specific reason. |
| CAP-02 Upload / transfer | Frontend upload component (File API + progress events) → pre-signed PUT to object storage; `POST /uploads` issues the URL after an auth/access check | Bytes go browser→storage directly; app server stays off the data path. Tab-close/network-drop leave an orphan that cleanup removes. |
| CAP-03 Virus scan | SQS job consumed by a background worker running **ClamAV** against the stored object before the file is made retrievable | Async so it never blocks upload. Infected → status `quarantined` + object deleted + alert. Retrieval is gated on a clean scan. Repeated failures → DLQ. |
| CAP-04 Thumbnail generation | Same worker, after a clean scan, runs **sharp** on images to produce a thumbnail stored under `thumbnails/`; PDFs skipped or given a generic icon | Only runs on clean images. Resource/pixel limits guard against decompression bombs. Failure → status `failed`, original still usable if scan passed (policy choice — see Open Questions). |
| CAP-05 Storage / retrieval | S3-compatible object store holds originals + thumbnails; Postgres `file_references` row tracks status and keys; `GET /uploads/:id` returns pre-signed GET URLs once status is `ready`, optionally via CDN | Transactional reference links file to owner/context; opaque keys handle duplicate filenames; retrieval access-checked and gated on `ready`. |

## Key Architecture Decisions

### AD-01: Direct-to-storage upload via pre-signed URLs

- **Decision**: The browser uploads file bytes directly to object storage using a short-lived pre-signed URL; the application server never proxies the file body.
- **Context**: CAP-02 requires 10 MB uploads with progress; the app runs on cost-sensitive managed compute.
- **Rationale**: Keeps transfers off app compute (lower memory/cost, no request-size limits), gives native browser progress events, and scales with the storage service. Standard pattern for S3-class stores.
- **Tradeoffs**: Validation splits into pre-issue and post-upload phases (server can't inspect bytes in flight), and bucket CORS + URL scoping must be configured carefully. Adds a brief orphan window handled by a cleanup sweep.

### AD-02: Async processing tier for scan + thumbnail (one queue, one worker pool)

- **Decision**: Run CAP-03 (virus scan) and CAP-04 (thumbnail) off an SQS queue on background workers, with a status state machine (`pending → scanning → ready | quarantined | failed`) and a DLQ — rather than doing them inline in the upload request or building separate pipelines per step.
- **Context**: Five capabilities, two of which are slow and heavy; small team that can't afford a sprawling pipeline; uploads must stay responsive.
- **Rationale**: Scanning and thumbnailing are exactly the work that justifies async processing — they're slow, fail in interesting ways, and benefit from retry/DLQ. A single queue + worker that does scan-then-conditional-thumbnail is the simplest thing that covers both without per-step orchestration overhead. Decouples upload throughput from processing throughput so workers can scale independently.
- **Tradeoffs**: Introduces eventual-consistency UX (files aren't instantly retrievable; the frontend must poll/subscribe for `ready`) and operational surface (queue depth, DLQ, worker scaling) that must be monitored. The worker image carries ClamAV + its signature DB, adding build/maintenance weight.

### AD-03: Self-hosted ClamAV for virus scanning

- **Decision**: Use ClamAV inside the worker rather than a managed scanning API.
- **Context**: Cost-sensitive small team; CAP-03 must scan every upload; files are user-supplied images/PDFs.
- **Rationale**: No per-scan cost, no third-party data exposure, runs locally in the worker. Adequate detection for a typical web app's threat model.
- **Tradeoffs**: Single-engine detection (weaker than multi-engine managed services), and the team owns keeping signature definitions fresh and the engine patched. Flagged for research before committing.

## Risks & Tradeoffs

- **Trusting client metadata**: client-reported MIME/extension is forgeable. Mitigation — authoritative server-side magic-byte validation (CAP-01); client checks are UX only.
- **Serving unscanned/infected files**: the whole point of CAP-03 fails if a file is retrievable before scanning. Mitigation — retrieval gated strictly on status `ready`; infected objects quarantined/deleted and alerted.
- **Image-parsing attack surface (CAP-04)**: thumbnailing parses untrusted bytes (decompression bombs, malformed images). Mitigation — sharp with pixel/size limits, resource-capped workers, scan-before-thumbnail ordering.
- **Pipeline backlog / poison jobs**: a spike or a repeatedly-failing file can stall processing. Mitigation — DLQ, queue-depth and DLQ alerts, independently scalable workers.
- **Orphaned objects**: abandoned/failed uploads leave bytes with no `ready` reference. Mitigation — scheduled cleanup of unreferenced/non-ready objects past a grace period; track the count.
- **ClamAV freshness**: stale virus signatures degrade CAP-03 silently. Mitigation — automate `freshclam` updates and rebuild/redeploy the worker image on a schedule; alert if updates fail.
- **CORS/config drift**: direct browser uploads break silently if bucket CORS is wrong. Mitigation — manage CORS/lifecycle in IaC, test in staging.

## Research Suggestions

High-stakes choices to validate with the researcher skill (researcher was unavailable this session):

- **Virus scanning approach (ClamAV self-hosted vs. managed API)** — high-stakes because it's a security control and the detection/operational tradeoff is significant. Suggested researcher query: *"Virus/malware scanning for user-uploaded files in web apps (2026): self-hosted ClamAV vs. managed APIs (Cloudmersive, VirusTotal) — detection effectiveness, signature maintenance burden, cost, latency, and data-privacy tradeoffs for a small team."*
- **Thumbnail/image processing for untrusted uploads** — high-stakes because it parses attacker-controlled bytes. Suggested researcher query: *"Secure server-side image thumbnail generation from untrusted uploads (2026): sharp/libvips vs. managed media services (Cloudinary, imgproxy), decompression-bomb and malformed-image defenses, and PDF preview generation."*
- **Pre-signed URL hardening** — confirm current best practices for scoping/bounding pre-signed PUT URLs on the chosen provider. Suggested researcher query: *"Securing S3 (or equivalent) pre-signed PUT URLs for browser uploads — TTL, content-length-range conditions, CORS, and preventing abuse."*

## Open Questions

- Which **cloud/storage provider** is the app on? (Determines pre-signed URL specifics and exact managed-service names — AWS assumed.) An existing object-storage service may already be present — confirm.
- **PDF handling for CAP-04**: should PDFs get a rendered first-page preview, a generic icon, or be skipped? Rendered preview adds a heavier dependency (e.g., pdftoppm/poppler) and attack surface — flag back to solution-architect if "thumbnail" was meant to include PDFs.
- **Thumbnail-failure policy**: if a clean image fails to thumbnail, is the original still retrievable (status `ready` without thumbnail) or held `failed`? Affects the state machine.
- **Per-user/per-context storage quota?** If yes, the quota check belongs in `POST /uploads` before issuing the URL — possibly a new capability, flag back to solution-architect.
- Confirm the **allowed file-type list** beyond "images + PDF" (which image formats?) — drives the validation allow-list config.

## Next Steps

1. Confirm the existing cloud/storage provider and whether it supports pre-signed direct uploads; if not, revisit AD-01.
2. Spike the end-to-end flow: issue URL → browser PUT with progress → complete callback → `pending` row → SQS job → worker scan + thumbnail → `ready`, including bucket CORS in staging.
3. Stand up the worker image with ClamAV + sharp; wire the queue, DLQ, and the status state machine.
4. Implement authoritative server-side validation (magic-byte) and the retrieval gate on `ready`.
5. Add observability: time-to-`ready`, queue depth, DLQ, infection-rate metrics + alerts; plus the orphan-cleanup job.
6. Run the three research queries above before committing to the scanning and image-processing choices.

---
*Technical architecture produced by technical-architect skill. Use the librarian skill to persist this artifact.*
