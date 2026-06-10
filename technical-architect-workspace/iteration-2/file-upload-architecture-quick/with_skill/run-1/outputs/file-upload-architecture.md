# File Upload Service — Technical Architecture

> Technical Architect | Depth: quick | Generated: 2026-06-10

## Source Breakdown

Capability breakdown provided inline by the user (from the solution-architect skill). The librarian skill was unavailable this run, so this architecture builds on the pasted breakdown rather than a retrieved artifact. An agent with librarian access could retrieve the source with: **specs matching "file upload validation virus scan thumbnail storage"**.

Capabilities this architecture builds on:

- **CAP-01 Validation** — users upload images and PDFs up to 10MB; the system validates them.
- **CAP-02 Upload / transfer** — get the file from the client into the system reliably.
- **CAP-03 Virus scan** — scan uploaded files for malware before they are made available.
- **CAP-04 Thumbnail generation** — generate thumbnails for image uploads.
- **CAP-05 Storage / retrieval** — store files durably and serve them back for retrieval.

## Constraints & Assumptions

- **Scale & load**: Typical web app — low-to-moderate volume (hundreds to low thousands of uploads/day), no extreme spikes stated. **[assumed]**
- **Team**: Small team. Language/framework not stated; assume a small full-stack team comfortable with a mainstream language (recommendation favors a single, widely-known stack to minimize operational surface). **[stated: small team; assumed: stack familiarity]**
- **Hosting**: Not stated. Assume a single mainstream public cloud (AWS used as the concrete reference; the design ports cleanly to GCP/Azure). **[assumed]**
- **Hard constraints**: None stated — no compliance (HIPAA/PCI/GDPR), budget, or data-residency requirements given. Designed to be cheap to run and operationally light. **[assumed]**
- **Existing systems**: None stated; treated as a standalone feature/service that an existing web app calls. **[assumed]**

## Architecture Overview

- **Style**: **Modular monolith API + an async worker**, deployed serverless-first where it fits. A small team and a single bounded feature don't justify microservices; one deployable API service handles request/validation/storage, and a separate worker handles the slow, untrusted work (virus scan, thumbnails) off the request path. Rationale: keeps the synchronous upload path fast and the team's operational surface small, while isolating the two latency/risk-heavy capabilities (CAP-03, CAP-04).
- **Shape**: The browser requests a **pre-signed upload URL** from the API (CAP-02) and uploads the file **directly to object storage**, so large bytes never transit the app servers. The API records metadata (status = `pending`) and runs cheap synchronous validation of the request (declared type, size limit) (CAP-01). Object-storage events enqueue a job; an **async worker** pulls the job, does deep content validation (magic-byte sniffing), runs the **virus scan** (CAP-03), and on clean images generates a **thumbnail** (CAP-04), writing results back to storage and flipping status to `available`. Retrieval (CAP-05) serves files via pre-signed download URLs or a CDN, gated on `available` status.

## Tech Stack

### Frontend
- **Recommendation**: The app's existing web frontend (assume React/TypeScript) using a direct-to-storage upload via a pre-signed URL, with client-side pre-checks for extension and size to fail fast.
- **Why**: Client-side checks improve UX for CAP-01 but are never trusted; the authoritative validation is server/worker-side. Direct-to-storage upload (CAP-02) avoids proxying 10MB bodies through the API.
- **Alternatives**: A resumable/chunked uploader (tus, Uppy) — prefer if uploads grow well beyond 10MB or mobile/flaky-network support becomes a priority. At 10MB a single PUT is sufficient.

### Backend / API
- **Recommendation**: A single API service in a mainstream language the team knows — **Node.js/TypeScript (NestJS or Express)** as the default, or Python (FastAPI) if the team leans Python. Endpoints: request upload URL, confirm upload, get file status, get download URL.
- **Why**: One small, well-understood service covers CAP-01 (request validation), CAP-02 (issuing pre-signed URLs), and CAP-05 (retrieval). TypeScript keeps frontend and backend in one language for a small team.
- **Alternatives**: Go — prefer if you want a single static binary and lower memory footprint; costs the team a second language. Serverless functions for the API (see Infrastructure) — viable and cheaper at low volume.

### Data storage
- **Object store (files + thumbnails)** — **Recommendation**: S3 (or GCS/Azure Blob). **Why**: Durable, cheap, scales without ops, and is the backbone of CAP-02 (direct upload) and CAP-05 (retrieval via pre-signed URLs). Use separate prefixes/buckets for `quarantine/` (just-uploaded, unscanned), `clean/`, and `thumbnails/`. **Alternatives**: Self-hosted MinIO — only if on-prem/data-residency is later required.
- **Metadata database** — **Recommendation**: PostgreSQL (managed: RDS/Cloud SQL). **Why**: File records are relational and need a reliable status field (`pending` → `scanning` → `available`/`rejected/infected`) that gates retrieval (CAP-05); transactional updates keep status honest. **Alternatives**: DynamoDB — prefer only at extreme scale with simple key access; overkill here and weaker for ad-hoc queries.
- **Cache / search**: **Not needed** at this scale — file lookups are by ID against an indexed table; add a CDN (below) rather than a cache layer.

### Async / messaging
- **Recommendation**: A managed queue — **SQS** (or Cloud Tasks / a Postgres-backed queue like a `jobs` table if you want zero extra infra). Object-storage upload events trigger a job; the worker consumes it.
- **Why**: Virus scanning (CAP-03) and thumbnail generation (CAP-04) are slow and must not block the upload response. A queue decouples them, gives retries and a dead-letter queue for poison files, and smooths spikes.
- **Alternatives**: Direct S3 → Lambda trigger without an explicit queue — simpler, but you lose centralized retry/DLQ control and back-pressure; acceptable for a first cut.

### Authentication & authorization
- **Recommendation**: Reuse the host web app's existing auth (session or JWT). The API authorizes who may request an upload URL and who may retrieve a given file (owner/ACL check before issuing a download URL). Pre-signed URLs are short-lived (minutes).
- **Why**: CAP-02 and CAP-05 must be tied to an authenticated user; short TTL on pre-signed URLs limits exposure. No new identity system needed.
- **Alternatives**: A managed IdP (Cognito/Auth0) — only if the host app lacks auth.

### Infrastructure & hosting
- **Recommendation**: Single cloud (AWS reference). API on **serverless containers / functions** (Lambda + API Gateway, or a small container on Fargate/Cloud Run). Worker as a **Lambda** (or Fargate task) consuming the queue. ClamAV for scanning runs in the worker container (see Security/CAP-03 note).
- **Why**: Low, bursty volume suits scale-to-zero serverless; a small team avoids managing servers. Containers (Fargate/Cloud Run) are the fallback when ClamAV's memory/startup footprint is awkward in a function.
- **Alternatives**: A single always-on VM/container running API + worker — simplest mental model, prefer if the team is uncomfortable with serverless; loses scale-to-zero savings.

### CI/CD & developer tooling
- **Recommendation**: GitHub Actions for build/test/deploy; infrastructure as code via Terraform or AWS CDK; two environments (staging, prod).
- **Why**: Buckets, queue, DB, IAM, and pre-signed-URL permissions are fiddly and security-sensitive — IaC makes them reviewable and reproducible. Standard tooling suits a small team.
- **Alternatives**: Serverless Framework / SST — prefer if going all-in on Lambda; nice DX for function + event wiring.

### Observability
- **Recommendation**: Structured logs + metrics to the cloud-native stack (CloudWatch) or a hosted tool; key metrics: upload success rate, scan queue depth/age, scan duration, infected-file count, thumbnail failures. Alert on queue backlog and scan worker error rate.
- **Why**: The async path (CAP-03/CAP-04) is where failures hide — a file stuck in `pending` is invisible without queue-age and worker-error visibility.
- **Alternatives**: Sentry for error tracking + a managed metrics tool — prefer for richer error grouping.

### Third-party services & integrations
- **Recommendation**: Image processing via a library in the worker (**sharp** for Node, **Pillow/libvips** for Python) for CAP-04; virus scanning via **ClamAV** (self-run in the worker) for CAP-03.
- **Why**: Both are mature, free, and run locally to the worker — no per-file SaaS cost at this scale.
- **Alternatives**: A managed AV/file-scanning API or a managed image-CDN-resize service (e.g., on-the-fly thumbnailing) — prefer if you want to avoid running ClamAV and keeping signatures fresh, or to skip pre-generating thumbnails. Flagged for research below.

### Security
- **Recommendation**: TLS everywhere (in transit); object store and DB encrypted at rest (default managed KMS). Newly uploaded files land in a **quarantine bucket** with no public/download access until CAP-03 marks them clean; only then are they copied to `clean/` and retrievable. Validate by **content (magic bytes), not just extension/MIME** (CAP-01). Short-TTL, least-privilege pre-signed URLs scoped to a single object. Strip/normalize filenames; serve downloads with `Content-Disposition` and a safe content type to avoid browser-side execution.
- **Why**: The core risk of an upload feature is serving malicious content. Quarantine-until-clean enforces CAP-03 as a gate on CAP-05; content-sniffing closes the "rename .exe to .pdf" gap in CAP-01.
- **Compliance**: None stated — no specific controls required beyond the above baseline.

## Capability → Tech Mapping

| Capability | Implemented by | Notes |
|-----------|----------------|-------|
| CAP-01 Validation | Client pre-checks (UX) + API request validation (declared type/size) + worker deep validation (magic-byte sniffing) | Authoritative check is server/worker-side; reject on type mismatch or >10MB. |
| CAP-02 Upload / transfer | API issues short-lived pre-signed URL; browser PUTs directly to object store (S3) | Bytes bypass the app server; metadata row created as `pending`. |
| CAP-03 Virus scan | Async worker (Lambda/Fargate) running ClamAV, fed by SQS/storage event | Off the request path; clean files promoted from `quarantine/` to `clean/`, infected files rejected + alerted. |
| CAP-04 Thumbnail generation | Async worker using sharp/libvips; output to `thumbnails/` | Images only; runs only after a clean scan. |
| CAP-05 Storage / retrieval | S3 for bytes, Postgres for metadata/status; retrieval via pre-signed download URL or CDN, gated on `available` | Download authorized per user/ACL; status gate prevents serving unscanned files. |

## Key Architecture Decisions

### AD-01: Direct-to-storage upload via pre-signed URLs

- **Decision**: Clients upload file bytes directly to object storage using a short-lived pre-signed URL, not through the API server.
- **Context**: CAP-02 with 10MB files on a small-team, low-ops design.
- **Rationale**: Keeps large payloads off app compute (cheaper, faster, fewer timeouts), and object storage already handles durability/scale for CAP-05.
- **Tradeoffs**: Validation and scanning must happen *after* the byte upload (async), so files are briefly `pending`; requires careful pre-signed-URL scoping and TTL.

### AD-02: Asynchronous scan + thumbnail via a queue and worker

- **Decision**: Run virus scanning (CAP-03) and thumbnail generation (CAP-04) in a separate worker driven by a queue, not inline in the upload request.
- **Context**: Scanning and image processing are slow and failure-prone relative to an HTTP request.
- **Rationale**: Decoupling keeps uploads responsive, enables retries/DLQ for poison files, and lets the worker scale independently.
- **Tradeoffs**: Eventual consistency — a file isn't immediately retrievable; the UI must reflect `pending`/`available` status.

### AD-03: Quarantine-until-clean storage gate

- **Decision**: Uploads land in a quarantine location with no retrieval access; only files that pass scanning are promoted to a clean location and made retrievable.
- **Context**: CAP-03 must gate CAP-05 — never serve an unscanned/infected file.
- **Rationale**: Makes the security property structural (enforced by bucket separation + status field) rather than relying on code discipline.
- **Tradeoffs**: Extra copy/move step and a second bucket/prefix to manage; status field becomes critical-path state.

## Risks & Tradeoffs

- **ClamAV operational burden**: self-running ClamAV means keeping virus signatures fresh and managing its memory/startup footprint (notably awkward inside Lambda). Mitigation: run the worker as a container (Fargate/Cloud Run) with scheduled `freshclam` updates, or use a managed scanning API.
- **PDF threat surface**: PDFs can carry active content; ClamAV catches known malware but not all malicious-but-novel PDFs. Mitigation: serve with safe content-disposition; consider sandboxed rendering if PDFs are displayed inline.
- **Stuck-in-pending files**: a worker failure leaves files unretrievable and invisible. Mitigation: DLQ + alert on queue age, plus a reconcile job for `pending` files older than N minutes.
- **Pre-signed URL misuse**: overly broad scope or long TTL leaks write/read access. Mitigation: scope to a single object key + content-length range, TTL in minutes.

## Research Suggestions

- **Virus-scanning approach (self-hosted ClamAV vs managed API)** — high-stakes security + ops choice; affects cost, signature freshness, and accuracy for CAP-03. Suggested researcher query: *"Compare self-hosted ClamAV (in Lambda vs Fargate/Cloud Run) against managed file-scanning APIs for a low-volume file upload service — cost, signature-update burden, detection efficacy on images and PDFs, and serverless integration patterns as of 2026."*
- **Thumbnail strategy (pre-generate vs on-the-fly image CDN)** — affects CAP-04 cost and complexity. Suggested researcher query: *"For a small-team web app, compare pre-generating thumbnails with sharp/libvips in a worker vs on-the-fly resizing via an image CDN — cost, latency, cache behavior, and operational simplicity."*

## Open Questions

- What backend language/framework does the team already know? (Defaulted to Node/TypeScript; confirm to finalize Backend/Worker choices.)
- Which cloud, if any, is preferred or already in use? (Defaulted to AWS; design ports to GCP/Azure.)
- Are thumbnails needed for PDFs (first-page preview), or images only? (Assumed images only per CAP-04 wording.)
- Expected upload volume and growth — confirms serverless-vs-always-on hosting and whether an explicit queue is warranted.

## Next Steps

1. Confirm the four open questions (language, cloud, PDF thumbnails, volume) to lock the stack.
2. Stand up IaC for buckets (`quarantine`/`clean`/`thumbnails`), the metadata DB, and the queue with least-privilege IAM.
3. Spike the pre-signed-URL upload flow end-to-end (request URL → PUT → metadata `pending`).
4. Spike the worker: storage-event → scan (ClamAV) → thumbnail (sharp/libvips) → promote + status `available`, with DLQ.
5. Validate the two research flags (scanning approach, thumbnail strategy) before committing.

---
*Technical architecture produced by technical-architect skill. Use the librarian skill to persist this artifact.*
