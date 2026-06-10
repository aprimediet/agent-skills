# File Upload Feature — Technical Architecture & Tech Stack

**Version:** 1.0
**Date:** 2026-06-10
**Audience:** Small engineering team (2–5 devs) building a typical web application
**Scope:** Capabilities CAP-01 through CAP-05

---

## 1. Overview

This document describes the technical architecture and recommended tech stack for a file upload feature. Users upload **images** (JPEG, PNG, GIF, WebP) and **PDFs** up to **10 MB**. The system validates each file, scans it for viruses, generates thumbnails for images, and stores the file for later retrieval.

### Capability summary

| ID | Capability | Description |
|--------|-----------------------|-----------------------------------------------------------|
| CAP-01 | Validation | Verify file type, size, and content integrity |
| CAP-02 | Upload / Transfer | Move bytes from client to durable storage |
| CAP-03 | Virus scan | Detect malware before the file is made available |
| CAP-04 | Thumbnail generation | Produce small preview images for uploaded images |
| CAP-05 | Storage / Retrieval | Persist files durably and serve them back on demand |

### Guiding principles

- **Right-sized for a small team.** Favor managed services and a modular monolith over microservices. Minimize the number of moving parts to operate.
- **Decouple slow work.** Validation and upload must feel fast to the user; virus scanning and thumbnailing run asynchronously.
- **Quarantine until clean.** A file is never served to other users until it passes virus scanning.
- **Direct-to-storage uploads.** Avoid streaming large files through the application server.

---

## 2. High-Level Architecture

The design uses **direct-to-object-storage uploads via pre-signed URLs**, an **asynchronous processing pipeline** driven by a queue, and a **state machine** that tracks each file from `pending` to `available` (or `rejected`/`infected`).

```
                         ┌──────────────┐
                         │   Browser    │
                         │  (Web/SPA)   │
                         └──────┬───────┘
              1. request upload │  ▲ 6. poll / websocket status
                                ▼  │
                         ┌──────────────┐        ┌────────────────────┐
                         │  API Server  │◄──────►│   Metadata DB      │
                         │ (App Backend)│        │   (PostgreSQL)     │
                         └──────┬───────┘        └────────────────────┘
        2. pre-signed PUT URL   │  │ 4. enqueue job
                                ▼  └──────────────────────┐
                         ┌──────────────┐                 ▼
   3. PUT file directly  │ Object Store │          ┌──────────────┐
   ────────────────────► │ (S3, raw/    │          │  Job Queue   │
   (from browser)        │  quarantine) │          │ (SQS/Redis)  │
                         └──────┬───────┘          └──────┬───────┘
                                │                         │ 5. consume
                                │   ┌─────────────────────▼──────────┐
                                └──►│        Worker Pool             │
                                    │  CAP-01 deep validation        │
                                    │  CAP-03 virus scan (ClamAV)    │
                                    │  CAP-04 thumbnail generation   │
                                    │  CAP-05 promote to clean store │
                                    └────────────────────────────────┘
```

### Request lifecycle

1. **Client requests an upload.** The browser calls `POST /uploads` with file metadata (name, declared MIME type, size). The API performs **cheap pre-validation** (CAP-01): size ≤ 10 MB, declared type in allow-list, rate-limit check.
2. **API issues a pre-signed PUT URL** scoped to a key in the **quarantine bucket/prefix**, with a short TTL (e.g. 5 minutes) and content-length / content-type constraints enforced by the storage provider. It creates a metadata row with status `pending`.
3. **Client uploads the bytes directly to object storage** (CAP-02) using the pre-signed URL. The application server never proxies the file body.
4. **Client notifies completion** (`POST /uploads/{id}/complete`) — or a storage event notification fires. The API enqueues a processing job (CAP-03/04/05) and sets status `uploaded`.
5. **A worker consumes the job** and runs the pipeline: deep validation → virus scan → thumbnail generation → promotion to the clean bucket. Status transitions to `available` on success.
6. **Client polls or subscribes** for status and, once `available`, retrieves the file and thumbnail via short-lived signed download URLs.

---

## 3. Capability Design Details

### CAP-01 — Validation (defense in depth)

Validation happens in **three layers** because client-declared metadata cannot be trusted.

1. **Pre-upload (synchronous, in API).** Check declared size against the 10 MB limit, declared MIME type against an allow-list, filename sanitization, and per-user rate limits. Cheap and fast — rejects obvious bad requests before any bytes move.
2. **Storage-enforced.** The pre-signed URL is generated with a `Content-Length-Range` / max-size policy and content-type condition so the storage provider itself rejects oversized or mismatched uploads.
3. **Post-upload (asynchronous, in worker).** **Magic-number / content sniffing** to confirm the file's real type matches the declared type (e.g. `file`/libmagic, Apache Tika, or a language-native equivalent). For images, decode/parse the header to confirm it is a valid image and within dimension limits. For PDFs, confirm a valid PDF structure. Reject polyglot files and files whose true type is not in the allow-list.

**Allow-list (not block-list):** `image/jpeg`, `image/png`, `image/gif`, `image/webp`, `application/pdf`. Reject everything else.

### CAP-02 — Upload / Transfer

- **Pre-signed URL direct upload** is the recommended pattern. It offloads bandwidth and memory from app servers, scales naturally with the storage provider, and keeps the backend stateless.
- For files near the 10 MB ceiling a single `PUT` is fine; **multipart upload** is unnecessary at this size but is the upgrade path if limits grow.
- **Resumability / UX:** show progress via the browser's upload progress events. Pre-signed URL TTL kept short to limit abuse.
- **Security:** enforce HTTPS/TLS, set CORS on the bucket to only the app origin(s), and constrain the signed policy to a single key.

### CAP-03 — Virus Scan

- **Engine:** **ClamAV** (open-source, free, well-supported). Run as a long-lived `clamd` daemon so the virus signature DB is loaded once in memory; the worker streams files to it over its socket. Refresh signatures with `freshclam` on a schedule.
- **Flow:** worker fetches the file from the **quarantine** bucket, streams it to `clamd`.
  - **Clean →** continue to thumbnailing and promotion.
  - **Infected →** set status `infected`, delete the object from quarantine, log/alert, and never promote.
- **Quarantine isolation:** the quarantine bucket/prefix is **never publicly readable and never served**. Only the worker can read it.
- **Managed alternative:** if the team prefers not to operate ClamAV, use a managed scanning service (e.g. cloud-provider malware scanning, or a hosted AV API). ClamAV in a container is the cheapest and most portable default.

### CAP-04 — Thumbnail Generation

- Applies to **images only** (PDFs may optionally get a first-page raster preview as a later enhancement).
- **Library:** **libvips** (via `sharp` in Node, `pyvips` in Python) — substantially faster and lower-memory than ImageMagick, with hard limits on input dimensions to guard against decompression-bomb attacks.
- **Output:** generate a small set of fixed sizes (e.g. 150×150 thumbnail, 600px-wide preview), strip EXIF metadata (privacy + size), and emit a web-friendly format (WebP with JPEG fallback). Store derivatives alongside the original in the clean bucket under a predictable key prefix.
- **Safety:** cap decode dimensions/pixels and run inside the resource-limited worker so a malicious image cannot exhaust memory.

### CAP-05 — Storage / Retrieval

- **Object storage** (S3 or compatible) holds the bytes; the **relational DB** holds metadata. This split is the standard, scalable pattern — never store file blobs in the DB.
- **Two logical locations:**
  - **Quarantine** (`quarantine/…`): raw uploads, private, scanned-then-deleted.
  - **Clean** (`files/…`): validated, scanned, with thumbnails; the only location ever served.
- **Retrieval:** serve via **short-lived signed GET URLs** (private objects) so access is authorized by the application. For public assets, front the bucket with a **CDN** for caching and lower latency.
- **Metadata model** (PostgreSQL):

```sql
CREATE TABLE uploads (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id        UUID NOT NULL,
  original_name   TEXT NOT NULL,
  declared_type   TEXT NOT NULL,
  detected_type   TEXT,
  size_bytes      BIGINT NOT NULL,
  checksum_sha256 TEXT,
  storage_key     TEXT NOT NULL,          -- key in quarantine, then clean
  thumbnail_key   TEXT,
  status          TEXT NOT NULL,          -- see state machine
  scan_result     TEXT,                   -- clean | infected | error
  failure_reason  TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_uploads_owner ON uploads (owner_id, created_at DESC);
CREATE INDEX idx_uploads_status ON uploads (status);
```

- **Lifecycle policies:** auto-expire abandoned `pending` uploads in quarantine (e.g. after 24 h); optionally lifecycle-tier or expire old files.

---

## 4. State Machine

A single explicit status field makes the asynchronous pipeline auditable and idempotent.

```
pending ──(bytes uploaded)──► uploaded ──(job picked up)──► processing
                                                                │
            ┌───────────────────────────────────────────────────┤
            ▼                         ▼                          ▼
        rejected                  infected                   available
   (failed validation)      (virus detected)          (clean, thumbnailed,
                                                        promoted to clean store)
```

- `pending` → object key reserved, awaiting bytes.
- `uploaded` → bytes present in quarantine, job enqueued.
- `processing` → worker running validation/scan/thumbnail.
- `available` → safe and retrievable. Terminal success.
- `rejected` → failed deep validation (wrong type, corrupt, too large). Terminal.
- `infected` → virus found; object purged. Terminal.

The pipeline is **idempotent**: re-processing a job recomputes deterministic results, so at-least-once queue delivery is safe.

---

## 5. Recommended Tech Stack

The architecture is intentionally implementation-agnostic; below is a concrete, low-operations default for a small team, plus alternatives.

| Concern | Primary recommendation | Why | Alternatives |
|------------------------|------------------------------------------------|-----------------------------------------------|--------------------------------------|
| Backend API | **Node.js + TypeScript (NestJS/Express)** or **Python + FastAPI** | Strong async I/O, large ecosystem, easy hiring | Go, Ruby on Rails, Java/Spring |
| Object storage (CAP-02/05) | **AWS S3** (or any S3-compatible: GCS, R2, MinIO) | Pre-signed URLs, lifecycle rules, durability | Azure Blob, Cloudflare R2, MinIO (self-host) |
| Metadata DB | **PostgreSQL** (managed: RDS / Cloud SQL / Neon) | Reliable, transactional, JSON support | MySQL |
| Job queue (CAP-03/04) | **AWS SQS** (managed) or **Redis + BullMQ** | Decouples slow work; SQS is zero-ops | RabbitMQ, GCP Pub/Sub |
| Workers | **Containerized worker process** (same codebase) | Reuse domain code; scale independently | AWS Lambda (note timeout/size limits) |
| Virus scanning (CAP-03) | **ClamAV (`clamd`) in a container** | Free, portable, battle-tested | Managed malware-scan service |
| Image processing (CAP-04) | **libvips** via `sharp` (Node) / `pyvips` (Python) | Fast, low memory, bomb-resistant | ImageMagick / Pillow |
| Content-type detection (CAP-01) | **libmagic** / Apache Tika / `file-type` lib | True-type detection beyond extension | — |
| CDN (retrieval) | **CloudFront** / Cloudflare | Caching, lower latency for public assets | Fastly |
| Hosting | **Containers on ECS/Fargate, Cloud Run, or a PaaS** (Render/Fly) | Minimal ops for a small team | Kubernetes (likely overkill here) |
| IaC | **Terraform** | Reproducible buckets/queues/policies | Pulumi, CDK |

### Why a modular monolith + workers (not microservices)

A small team should ship the **API and worker from one codebase/repo**, deployed as two process types. This shares models, validation logic, and types while still allowing the worker pool to scale independently of the API. Microservices would add deployment, networking, and observability overhead disproportionate to the team size.

### Serverless note

The pipeline maps cleanly to event-driven serverless (S3 event → Lambda). At 10 MB files this is viable, but ClamAV's signature DB load time and Lambda's package-size/timeout constraints make a **persistent containerized `clamd` worker** simpler and cheaper to run. Lambda is a reasonable choice for the lightweight thumbnail step if the team is already serverless-first.

---

## 6. Cross-Cutting Concerns

### Security

- **Allow-list** types; verify by content, not extension. Strip metadata from images.
- **Quarantine before serving** — nothing reaches the clean store or users until scanned clean.
- **Pre-signed URLs** scoped to one key, short TTL, size/type constrained; **private buckets** with **signed GET** for retrieval.
- **Authn/Authz** on every API call; ownership checks on retrieval. Per-user **rate limiting** and quotas to prevent abuse.
- Bucket **CORS** locked to app origins; all transfers over **TLS**. Encryption at rest (SSE) and in transit.
- Sanitize filenames; never trust them for storage keys (use UUID-based keys). Set `Content-Disposition: attachment` and a strict `Content-Type` on download to prevent browser-side execution; serve user content from a separate domain where feasible.

### Reliability & error handling

- **At-least-once queue + idempotent workers**; use a **dead-letter queue** for repeatedly failing jobs and alert on it.
- Retries with backoff for transient storage/scan errors; distinguish **transient** (retry) from **permanent** (reject) failures.
- **Orphan cleanup:** scheduled job removes `pending` uploads with no bytes and quarantine objects with no DB row.

### Observability

- **Structured logs** with the upload `id` as correlation key across API and worker.
- **Metrics:** upload count, validation reject rate, scan duration, infection count, thumbnail latency, queue depth, DLQ size.
- **Alerts** on DLQ growth, rising infection/rejection rates, and queue backlog.

### Performance & scale

- Direct-to-storage uploads keep API memory/CPU flat regardless of file size.
- Workers scale horizontally on **queue depth**; the API and DB are unaffected by processing spikes.
- CDN caching for repeated retrieval of public assets.

### Cost

- Dominant costs are object storage and egress. Use **lifecycle rules** to expire abandoned uploads and to tier cold files. CDN reduces repeated egress. ClamAV and libvips are free/open-source.

---

## 7. Trade-offs & Decisions

| Decision | Chosen | Rejected alternative | Rationale |
|---------------------------------|------------------------------|-------------------------------|--------------------------------------------------|
| Upload path | Direct-to-storage (pre-signed) | Proxy through API | Saves bandwidth/memory; scales; keeps API stateless |
| Processing | Async via queue + workers | Synchronous in request | Scanning/thumbnailing are slow; keeps UX fast |
| Topology | Modular monolith + workers | Microservices | Right-sized for a small team; less ops overhead |
| Virus engine | ClamAV (self-run daemon) | Managed AV API | Free, portable; daemon avoids per-scan DB reload |
| Image lib | libvips/sharp | ImageMagick | Faster, lower memory, decompression-bomb safe |
| Serve files | Private + signed GET (+ CDN) | Public bucket | Authorization control; CDN for performance |

---

## 8. Implementation Roadmap (suggested)

1. **MVP storage + upload:** pre-signed URLs, metadata table, synchronous pre-validation, basic retrieval via signed GET. (CAP-01 layer 1, CAP-02, CAP-05)
2. **Async pipeline:** queue + worker, deep content validation, status state machine. (CAP-01 layer 3)
3. **Virus scanning:** ClamAV daemon, quarantine→clean promotion, DLQ. (CAP-03)
4. **Thumbnails:** libvips derivatives, EXIF stripping. (CAP-04)
5. **Hardening:** CDN, rate limits/quotas, lifecycle policies, metrics/alerts, orphan cleanup.

---

## 9. Open Questions / Assumptions

- **Assumed** files are largely private (signed retrieval default). If assets are public, lean harder on the CDN.
- **Assumed** no compliance regime (HIPAA/PCI) beyond standard hygiene; those would add encryption-key management and audit requirements.
- **Assumed** a single region is sufficient initially; multi-region is a later concern.
- **PDF previews** (first-page raster) are treated as an optional enhancement, not part of the core CAP-04 scope.
- **Expected volume** not specified; the design scales horizontally but capacity planning should be revisited once traffic is known.
