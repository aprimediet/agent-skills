# File Upload Feature — Technical Architecture

> Technical Architect | Depth: quick | Generated: 2026-06-10

## Source Breakdown

Built on the solution-architect capability breakdown for the File Upload Feature, **provided inline** (the librarian skill was not available this session). It defines three capabilities: file upload with progress, file validation, and file storage reference.

- [File Upload Feature](../../solution-architect/examples/file-upload.md) — file selection, upload-with-progress, type/size validation, and persisting a retrievable reference to the stored file (CAP-01..CAP-03).

## Constraints & Assumptions

- **Scale & load**: **[assumed]** Typical web application, modest concurrent uploads (tens, not thousands at once). 25 MB max per file. Sub-3s perceived completion and <1% failure rate are the stated success criteria from the breakdown.
- **Team**: **[assumed]** Small team; assume comfort with mainstream web tooling (TypeScript/JavaScript). No exotic-language requirement.
- **Hosting**: **[assumed]** Single managed cloud (AWS used as the concrete default below); no on-prem requirement. Substitute the equivalent managed services on GCP/Azure if that is the existing cloud.
- **Hard constraints**: **[assumed]** No special compliance (no HIPAA/PCI/GDPR-specific controls beyond good hygiene). Cost-sensitive — prefer managed services over self-hosted infrastructure.
- **Existing systems**: **[stated]** Task management module, messaging module, user authentication system, and a file storage service already exist. This feature plugs into all four rather than replacing them.

## Architecture Overview

- **Style**: **Modular feature within the existing modular monolith** — the upload feature is a backend module exposing a small API plus a frontend widget, talking to object storage directly via pre-signed URLs. No new service or messaging tier; the breakdown's scope (single feature, validation, reference record) does not justify one.
- **Shape**: The browser uploads the file **directly to object storage** using a short-lived pre-signed URL issued by the backend, so large bytes never transit the application server. The backend's role is three small steps: (1) validate the request and issue the pre-signed URL, (2) on the client's "done" callback, run server-side validation of the stored object's metadata/header bytes, and (3) write a file-reference record into the existing relational database linked to the task or conversation. The frontend shows progress from the direct-to-storage upload's native progress events. A periodic cleanup job removes orphaned objects (uploaded but never referenced).

## Tech Stack

### Frontend
- **Recommendation**: TypeScript + the team's existing SPA framework (React assumed), using the browser-native **File API** + **XMLHttpRequest/`fetch` with upload progress** to push directly to the pre-signed storage URL. A small reusable upload component handles file picker, drag-and-drop, per-file progress bars, and retry.
- **Why**: CAP-01 needs client-side progress and independent multi-file uploads; direct-to-storage uploads expose native progress events. Client-side pre-checks (extension/size) give CAP-02 its instant rejection before any bytes move. No heavy library needed at this scale.
- **Alternatives**: Uppy (or react-dropzone + tus) — prefer if you later need resumable/chunked uploads for much larger files or flaky-network resilience; overkill for a 25 MB cap.

### Backend / API
- **Recommendation**: TypeScript on **Node.js** as a module inside the existing application, exposing two endpoints: `POST /uploads` (validate context + return pre-signed URL) and `POST /uploads/:id/complete` (server-side validation + create reference). Use the existing app framework (e.g., Express/Nest/Fastify).
- **Why**: Keeps the feature in the current codebase and deployment (modular monolith), shares the existing auth middleware, and keeps the server off the file's byte path. The two-call pattern cleanly separates CAP-02's two validation moments (pre-upload vs. post-upload header check).
- **Alternatives**: A dedicated upload microservice — prefer only if uploads become a distinct scaling or team-ownership concern; unjustified for one feature on a small team.

### Data storage
- **File reference store (primary)**: **PostgreSQL** table (`file_references`: id, storage_key, original_filename, content_type, size_bytes, uploaded_at, owner_id, context_type, context_id, status). PostgreSQL because the data is relational and CAP-03 needs a transactional link between the reference and its task/conversation, plus easy joins for the attachment list. Alternative: reuse whatever the existing modules already use — match it rather than introduce a second database.
- **Object/blob store**: the **existing file storage service** (modeled here as **S3-compatible object storage**) holds the bytes. Pre-signed PUT for upload, pre-signed GET for retrieval. This is the natural home for CAP-01's bytes and CAP-03's storage location.
- **Cache / search / analytics**: **Not needed** — attachment lists are small, queried by context ID (indexed), and there is no search or analytics capability in the breakdown.

### Async / messaging
- **Recommendation**: **No queue/stream.** The only background work is orphan cleanup (CAP-03 error path), handled by a **scheduled job** (cron/scheduled task) that deletes objects with no matching reference older than a grace period.
- **Why**: The breakdown explicitly puts virus scanning and thumbnailing out of scope, which removes the usual reason for an upload queue. Validation is synchronous and fast. A scheduled sweep is the simplest thing that satisfies the orphan-cleanup requirement.
- **Alternatives**: Storage event notifications (e.g., S3 → SQS/Lambda) to drive cleanup or post-processing — prefer if scope later adds scanning/thumbnailing or you want event-driven reconciliation.

### Authentication & authorization
- **Recommendation**: Reuse the **existing authentication system**; every upload endpoint runs behind it. Authorization check: the authenticated user must have access to the target task/conversation before a pre-signed URL is issued, and the reference record stores `owner_id` + context for later access checks on retrieval.
- **Why**: CAP-01 takes the user session as input and CAP-03 makes files "visible to all participants" — both require an access check against the existing context modules. Pre-signed URLs are short-lived (e.g., 5 min) so the grant can't be replayed.
- **Alternatives**: None warranted — introducing a separate identity system would fight the stated existing-systems constraint.

### Infrastructure & hosting
- **Recommendation**: Deploy as part of the existing application on its current managed compute (assumed AWS — ECS/Fargate or equivalent PaaS), with object storage (S3) and the managed Postgres (RDS) the app already uses. CDN (CloudFront) optionally fronts pre-signed GETs for download.
- **Why**: No new runtime; the feature is a module, not a service. Managed services keep ops light for a small team. Direct-to-storage upload means app compute does not scale with file size.
- **Alternatives**: Fully serverless (API Gateway + Lambda) — prefer if the rest of the app is already serverless; otherwise it fragments the deployment for no gain here.

### CI/CD & developer tooling
- **Recommendation**: Reuse the existing pipeline (e.g., GitHub Actions) — lint, typecheck, unit + integration tests, deploy to staging then prod. Storage bucket, CORS config, and lifecycle/cleanup rules defined as **IaC** (Terraform/CDK) alongside the rest of the infra.
- **Why**: One feature should not introduce a parallel toolchain. CORS on the bucket is load-bearing for direct browser uploads, so it belongs in versioned IaC, not console clicks.
- **Alternatives**: None — match the team's existing pipeline.

### Observability
- **Recommendation**: Structured logs for the three backend steps (URL issued, validation pass/fail with reason, reference created/failed); metrics for **upload success rate** and **time-to-complete** (directly tracks the <1% failure / 3s success criteria); an alert when failure rate breaches 1% over a window. Track orphan-cleanup counts.
- **Why**: The success criteria are quantitative, so they must be measurable. Validation-failure reasons (CAP-02) are valuable for tuning the allowed-types policy.
- **Alternatives**: Whatever the team already runs (CloudWatch, Datadog, etc.) — reuse it.

### Third-party services & integrations
- **Recommendation**: Only the **existing file storage service** (S3-compatible). No payment, email, or new SaaS needed for this scope.
- **Why**: The breakdown's integrations are entirely internal (storage, auth, task/messaging modules).
- **Alternatives**: A managed upload SaaS (Uploadcare, Filestack) — prefer only if the team wants to outsource validation/transformations and accept the cost/dependency; unnecessary here.

### Security
- **Recommendation**: Server-side validation is authoritative — re-check size, extension allow-list, and **magic-byte/header content-type** after the object lands (client checks are UX only, never trusted). Short-lived, single-object, content-length-bounded pre-signed URLs. Encryption at rest (SSE) and TLS in transit (both standard on managed object storage). Store the original filename as data, never use it as a storage key (avoid path traversal); generate opaque storage keys. Tight bucket CORS (only your origin) and no public bucket ACLs — downloads go through pre-signed GETs.
- **Why**: CAP-02 explicitly defends against disguised extensions via header analysis, and the breakdown flags file-type safety as a research item. The pre-signed-URL pattern's main risks (over-broad URLs, public buckets, trusting client metadata) are all mitigated above.
- **Compliance**: None special **[assumed]**; the above is baseline good hygiene.

## Capability → Tech Mapping

| Capability | Implemented by | Notes |
|-----------|----------------|-------|
| CAP-01 File upload | Frontend upload component (File API + progress events) → pre-signed PUT to object storage; `POST /uploads` issues the URL after an auth/access check | Bytes go browser→storage directly; app server stays off the data path. Per-file independent progress satisfies the multi-file edge case. Tab-close/network-drop leave an orphan that cleanup removes. |
| CAP-02 File validation | Client-side pre-check (extension/size) for instant UX rejection + authoritative **server-side** re-validation in `POST /uploads/:id/complete` (size, allow-list, magic-byte header) | Two validation moments map to the breakdown's "before upload" and "after transfer" triggers. Header check catches disguised extensions; zero-byte and unreadable-header files rejected. |
| CAP-03 File storage reference | `POST /uploads/:id/complete` writes a row to the Postgres `file_references` table linked to task/conversation; attachment list reads by context ID; scheduled cleanup job removes orphaned objects | Transactional insert links reference to context; opaque storage key handles duplicate filenames; orphan/unreachable-context cases set a `status` flag for later review. |

## Key Architecture Decisions

### AD-01: Direct-to-storage upload via pre-signed URLs

- **Decision**: The browser uploads file bytes directly to object storage using a short-lived pre-signed URL; the application server never proxies the file body.
- **Context**: CAP-01 requires 25 MB uploads with live progress at <1% failure; the app runs on cost-sensitive managed compute.
- **Rationale**: Keeps large transfers off app compute (lower memory/cost, no request-size limits to fight), gives native browser progress events, and scales with the storage service rather than the app. Standard pattern for S3-class stores.
- **Tradeoffs**: Validation must split into pre-issue and post-upload phases (the server can't inspect bytes in flight), and bucket CORS + URL scoping must be configured carefully. Adds a brief orphan window handled by the cleanup job.

### AD-02: Keep it in the modular monolith — no new service, no queue

- **Decision**: Implement as a module in the existing application with synchronous validation and a scheduled cleanup job, rather than a dedicated upload service or an async processing pipeline.
- **Context**: Single feature, three capabilities, small team; scanning and thumbnailing are explicitly out of scope.
- **Rationale**: The work that would justify a queue (scanning, transforms) isn't in scope. Reusing the app's auth, database, and pipeline minimizes moving parts and ops burden for a small team.
- **Tradeoffs**: If scope later adds virus scanning or image processing, an async tier (storage events → queue → worker) will need to be introduced then — a deliberate, localized change rather than upfront complexity.

## Risks & Tradeoffs

- **Trusting client metadata**: client-reported MIME/extension is forgeable. Mitigation — server-side magic-byte validation after upload is authoritative; client checks are UX-only.
- **Orphaned objects**: any abandoned/failed upload leaves bytes with no reference (CAP-01 edge cases, CAP-03 error path). Mitigation — scheduled cleanup of unreferenced objects past a grace period; track the count as a metric.
- **Pre-signed URL misuse**: an over-scoped or long-lived URL could be abused. Mitigation — short TTL, single object key, content-length range bound, HTTPS only.
- **CORS/config drift**: direct browser uploads break silently if bucket CORS is wrong. Mitigation — manage CORS and lifecycle rules in IaC, test in staging.
- **Post-upload validation rejects an already-stored object**: a file can land in storage and then fail server-side validation. Mitigation — delete the object immediately on validation failure and surface CAP-02's specific reason; cleanup job is the backstop.

## Research Suggestions

- **File-type safety and content validation** — carried over from the breakdown; high-stakes because it gates what users can upload safely. Suggested researcher query: *"File upload security best practices — content validation via magic-byte/header inspection, MIME type whitelisting, disguised-extension detection, and safe handling of user-uploaded files in web applications (2026)."*
- **Pre-signed URL hardening** — confirm current best practices for scoping and bounding pre-signed PUT URLs on the chosen storage provider. Suggested researcher query: *"Securing S3 (or equivalent) pre-signed PUT URLs for browser uploads — TTL, content-length-range conditions, CORS, and preventing abuse."*

## Open Questions

- Which **object storage provider/cloud** is the app already on? (Determines pre-signed URL specifics and the exact managed-service names — AWS assumed above.)
- Confirm the **allowed file-type list and size limits** (carried from the breakdown's open questions) — these drive the validation allow-list config.
- Is there a **per-user or per-context storage quota** to enforce? If yes, the quota check belongs in `POST /uploads` before issuing the URL — flag back to solution-architect as it may be a new capability.
- Does the existing **file storage service** support pre-signed/direct upload, or must the server proxy bytes? (Changes AD-01 if it cannot.)

## Next Steps

1. Confirm the existing cloud/storage provider and whether it supports pre-signed direct uploads; if not, revisit AD-01.
2. Spike the pre-signed-URL flow end to end: issue URL → browser PUT with progress → complete callback → reference row, including bucket CORS in staging.
3. Define the validation config (allowed extensions, size bounds) and implement authoritative server-side magic-byte checking.
4. Add the orphan-cleanup scheduled job and the success-rate / time-to-complete metrics + alert.
5. Run the two research queries above before finalizing the allowed-types policy.

---
*Technical architecture produced by technical-architect skill. Use the librarian skill to persist this artifact.*
