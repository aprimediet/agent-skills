# Indie Game Publishing Platform — Deep Brainstorm

> **Project Idea:** An indie-friendly alternative to Steam where developers can publish games, handle payments, manage DRM, collect analytics, and distribute updates across Windows, Mac, Linux, and mobile.
> **Date:** 2026-06-09
> **Depth:** Thorough exploration

---

## Table of Contents

1. [Vision & Positioning](#1-vision--positioning)
2. [Core Feature Breakdown](#2-core-feature-breakdown)
3. [Platform & Client Support](#3-platform--client-support)
4. [Technical Architecture (High-Level)](#4-technical-architecture-high-level)
5. [Payment & Revenue Model](#5-payment--revenue-model)
6. [DRM Strategies](#6-drm-strategies)
7. [Analytics Pipeline](#7-analytics-pipeline)
8. [Update & Distribution System](#8-update--distribution-system)
9. [Developer Experience & Tools](#9-developer-experience--tools)
10. [Storefront & Discovery](#10-storefront--discovery)
11. [Community & Social Features](#11-community--social-features)
12. [Monetization for the Platform](#12-monetization-for-the-platform)
13. [Competitive Landscape](#13-competitive-landscape)
14. [Risks & Challenges](#14-risks--challenges)
15. [Roadmap / Phased Build Plan](#15-roadmap--phased-build-plan)

---

## 1. Vision & Positioning

### Core Problem
Steam dominates PC game distribution but has issues for indies:
- **Visibility:** 10,000+ games released per year; discoverability is awful for new titles.
- **Revenue split:** 70/30 (though reduced to 75/25 after $10M, and 80/20 after $50M — still steep for small devs).
- **Limited control:** Developers can't customize store pages deeply, run their own sales easily, or own their customer relationships.
- **Heavyweight:** Steamworks SDK is powerful but complex. Many indies want simpler tooling.
- **No built-in mobile path:** Steam is PC-only; an indie with a mobile version needs separate infrastructure.

### Positioning Statement
> "The publishing platform for indie developers who want professional tooling without giving up control or their fair share."

### Key Differentiators
| Dimension | Steam | Itch.io | This Platform |
|-----------|-------|---------|---------------|
| Revenue split | 70/30 (sliding) | 90/10 (optional 0%) | **85/15 or 88/12** |
| DRM | Steamworks CEG (mandatory) | None (optional) | **Tiered: none / lightweight / strong** |
| Analytics | Steamworks (game-level only) | None built-in | **Built-in pipeline: crash, usage, funnel** |
| Updates | SteamPipe (good, but Steam-only) | Manual upload | **Git-based + CLI + auto-patching** |
| Mobile | No | No | **Yes (Android via APK, iOS via TestFlight/App Store bridge)** |
| Store customizability | Low | High | **High (custom pages, widgets, embeds)** |
| Dev fee | $100 per app | Free / $2-6 per sale | **Free to list, $25 per app (refundable on first $100 earned)** |

---

## 2. Core Feature Breakdown

### 2.1 Game Publishing Pipeline
- **Submission workflow:** Upload build → configure metadata → set pricing → submit for review (automated sanity checks, optional manual QA).
- **Metadata system:** Title, description, screenshots, trailers, tags, categories, localizations, system requirements.
- **Build management:** Version history, release channels (stable / beta / experimental), rollback support.

### 2.2 Payment Processing
- **Supported methods:** Credit/debit cards, PayPal, Stripe, local payment methods (Pix, iDEAL, etc.), crypto (optional, USDC for stable value).
- **Payout to devs:** Monthly automatic payouts, threshold configurable ($50–$1000), wire / PayPal / Stripe Connect.
- **Tax handling:** Automated VAT / GST collection per region (Stripe Tax or similar), US sales tax, withholding tax treaties.
- **Regional pricing:** Per-currency pricing suggestions, auto-conversion with manual override, purchasing power parity adjustments.

### 2.3 DRM Module
- **Tier 0 — None:** Just a download link. No restrictions.
- **Tier 1 — Lightweight:** Simple license key check at install, then runs freely. Good for honest users, zero runtime overhead.
- **Tier 2 — Standard:** Periodic online check (every 7 days or on major update). Bind license to hardware ID (limited activations).
- **Tier 3 — Strong:** Full online activation with machine-locked licenses, offline token refresh, anti-tamper checks.
- **Custom:** Devs can bring their own DRM (Denuvo, etc.) via a plugin interface — platform just handles the delivery.

### 2.4 Analytics Collection
- **Game-level:** Daily active users, sessions, playtime, retention (D1/D7/D30), crash rate, OS/hardware breakdown.
- **Event pipeline:** Custom event tracking (player died, level completed, item purchased) — devs define schemas.
- **Funnel analysis:** Conversion tracking (store page view → purchase → install → play).
- **Performance metrics:** FPS histograms, memory usage, load times.
- **Privacy:** GDPR-compliant by default, opt-in extended telemetry, data ownership belongs to dev (not platform).

### 2.5 Update Distribution
- **Binary diff patching:** Only ship changed bytes (like SteamPipe or bsdiff).
- **Channel system:** Stable / Beta / Nightly per build.
- **Forced vs optional updates:** Dev chooses; platform enforces for multiplayer titles.
- **Rollback:** One-click revert to previous build.
- **Bandwidth management:** CDN caching, P2P-assisted distribution (optional, like Bittorrent or IPFS for large games), regional edge nodes.

### 2.6 Developer Dashboard
- **Unified dashboard:** Sales, analytics, builds, releases, reviews, support tickets.
- **API / SDK:** REST API for automation, client SDK (C++, C#, Rust, Unity, Unreal) for analytics/DRM/updates.
- **CLI tool:** `publish push`, `publish status`, `publish rollback` — CI/CD friendly.

---

## 3. Platform & Client Support

### 3.1 Desktop (Phase 1)
| Platform | Client Approach | Key Challenges |
|----------|----------------|----------------|
| **Windows** | Native launcher (Rust/C++ or C# with .NET) | Most important; DirectX/GPU detection |
| **macOS** | Native launcher (Swift or Rust) | Notarization, codesigning, M-series support |
| **Linux** | Flathub / AppImage + CLI launcher | Fragmentation (distros, lib versions, display servers) |

**Client responsibilities:**
- Install, update, repair, and uninstall games
- Launch games with correct environment variables
- Show overlay (friends, achievements, screenshots)
- Cache license tokens for offline play
- P2P update seeding (opt-in)

### 3.2 Mobile (Phase 2)
| Platform | Approach | Details |
|----------|----------|---------|
| **Android** | Standalone APK/AAB via website + Google Play bridge | Devs can distribute outside Google Play; platform handles licensing checks |
| **iOS** | TestFlight / Ad-hoc distribution + web-based install (Enterprise cert for beta) | Apple restrictions are heavy; may need to be a "buy on web, get a code you redeem" model |
| **Cross-play** | Same entitlement works across mobile & desktop (if dev enables) | Requires dev to use platform's auth SDK |

### 3.3 Client Technology Stack Options
- **Option A: Electron/Chromium** — Fast to build, high memory usage, large download. Best for rapid prototyping.
- **Option B: Rust (Tauri)** — Small binary, native performance, web-based UI. Good balance.
- **Option C: C++ (Qt or native)** — Full control, hardest to maintain. Best for performance-critical overlay.
- **Recommendation:** **Tauri** for the launcher UI, Rust for the backend/subsystem. Overlay can be a separate compositor layer (DirectX/Vulkan hook via imgui or similar).

---

## 4. Technical Architecture (High-Level)

```
┌─────────────────────────────────────────────────────────┐
│                    CDN / Edge Network                     │
│  (Cloudflare / Fastly / BunnyCDN + regional edge caches) │
└──────────────┬──────────────────────┬───────────────────┘
               │                      │
     ┌─────────▼──────────┐  ┌───────▼────────┐
     │   API Gateway       │  │  Download       │
     │   (Kong / Envoy)    │  │  Service        │
     └─────────┬──────────┘  │  (range reqs,   │
               │             │   patch apply)   │
     ┌─────────▼──────────┐  └─────────────────┘
     │  Microservices      │
     │  (Go / Rust)        │
     │  ┌───┬───┬───┬───┐ │
     │  │ A │ B │ C │ D │ │
     │  └───┴───┴───┴───┘ │
     └─────────┬──────────┘
               │
     ┌─────────▼──────────┐
     │  Data Layer         │
     │  Postgres (primary) │
     │  ClickHouse (anal)  │
     │  Redis (cache/queue)│
     │  S3 (build storage) │
     └─────────────────────┘
```

### 4.1 Key Services (Microservices)
| Service | Responsibility | Tech |
|---------|---------------|------|
| **Auth Service** | OAuth 2.0 / OpenID Connect, session management, SSO | Go + Redis |
| **Store Service** | Game listings, search, recommendations, reviews | Rust + Postgres + Meilisearch (search) |
| **Payment Service** | Checkout, invoicing, refunds, payout processing | Go + Stripe API + ledger |
| **Build Service** | Upload, versioning, binary diff generation, publishing | Rust + S3 + custom diff engine |
| **Analytics Service** | Event ingestion, aggregation, dashboards | Rust + ClickHouse + Kafka |
| **DRM Service** | License generation, validation, activation counting | Rust + Postgres + Redis (rate limits) |
| **Community Service** | Reviews, forums, user profiles, friends | Go + Postgres |
| **Notification Service** | Email, web push, in-app notifications | Go + RabbitMQ |

### 4.2 Infrastructure
- **Cloud:** Multi-region (US, EU, APAC) on bare metal or spot instances to save cost.
- **Container orchestration:** Nomad or Kubernetes (K3s for simplicity).
- **Object storage:** S3-compatible (MinIO for on-prem, Backblaze B2 or Cloudflare R2 for cheaper egress).
- **CDN:** Cloudflare or BunnyCDN (game builds are large; egress costs matter).
- **CI/CD:** GitHub Actions / GitLab CI for platform itself; devs use our CLI in their own CI.

---

## 5. Payment & Revenue Model

### 5.1 Transaction Flow
```
Player clicks "Buy" → Platform checkout → Payment processor → 
→ License key generated → Game added to library → 
→ Money settles → Platform takes cut → Rest goes to dev (minus fees)
```

### 5.2 Revenue Split Options
| Tier | Platform Cut | Conditions |
|------|-------------|------------|
| Standard | **15%** | Default for all games |
| Reduced | **12%** | Exclusive titles or revenue > $500k |
| Charity | **0%** | Free games, donations only |

### 5.3 Fees & Charges
- **Payment processing fee:** 2.9% + $0.30 (passed through at cost) or absorbed into the 15%.
- **Currency conversion:** 1% if applicable.
- **Payout fee:** Free for bank transfer (ACH/SEPA); $2 for PayPal/Wire.

### 5.4 Regional Pricing
- Auto-suggest prices based on PPP (Purchasing Power Parity).
- Developer can override per region.
- Sales tax / VAT auto-added at checkout, remitted by platform.

---

## 6. DRM Strategies

### 6.1 Philosophy
- **Indie-friendly:** DRM should not frustrate paying customers.
- **Tiered choice:** Devs pick their comfort level.
- **No rootkits, no always-online:** Unless the game itself requires it.

### 6.2 Implementation Details

**Tier 1 — License Key (Light):**
- Dev uploads game, gets a "release ID."
- On first launch, the game client calls `/license/activate` with release ID + machine fingerprint.
- Server returns a signed token (JWT) cached locally.
- Token checked at install time only; game runs offline indefinitely after that.
- No activation limit.

**Tier 2 — Hardware Binding (Medium):**
- Same as Tier 1, but token is bound to a hardware hash (CPU + motherboard + GPU).
- Max 5 activations per license (can be reset by dev via dashboard).
- Token refreshed every 7 days if online; otherwise cached for 30 days.

**Tier 3 — Online Verification (Strong):**
- Game sends heartbeat every 60–120 minutes.
- If heartbeat fails, game enters "grace period" (2 hours) then locks.
- Machine bound, 3 activations.
- Offline tokens: Dev can issue a 72-hour offline pass from the dashboard.

### 6.3 DRM SDK
- Small C header library (C bindings for C++, Rust, C# via FFI).
- Unity Package and Unreal Engine Plugin provided.
- Open source the client-side SDK (transparency builds trust).

---

## 7. Analytics Pipeline

### 7.1 Data Flow
```
Game Instrumentation → SDK → HTTPS POST → API Gateway → 
→ Kafka → ClickHouse → Dev Dashboard (WebSockets refresh)
```

### 7.2 Collected Metrics (Default)
| Category | Metrics |
|----------|---------|
| Engagement | DAU/MAU, session length, sessions per day |
| Retention | D1, D3, D7, D14, D30 (cohort analysis) |
| Performance | FPS (avg, p1, p99), load times, memory |
| Crashes | Stack trace, OS, GPU driver, frequency |
| Hardware | CPU, GPU, RAM, OS version, screen resolution |
| Geography | Country, region (determined from IP, no GPS) |

### 7.3 Custom Events
- Dev defines event schema in dashboard (name + properties with types).
- SDK provides typed helpers:
  ```c
  analytics_track(
    "boss_defeated",
    analytics_property_string("boss_name", "Megadrake"),
    analytics_property_int("attempts", 3),
    analytics_property_float("health_remaining", 0.87)
  );
  ```
- Max 100 custom event types per game (plan limit).
- Data retention: Raw events 90 days, aggregated metrics forever.

### 7.4 Privacy & Compliance
- **GDPR:** No personal data collected by default. IP anonymized after geo-lookup.
- **Player opt-out:** Players can disable telemetry in launcher settings; SDK respects the flag.
- **Data ownership:** Dev owns 100% of their game's analytics data. Platform cannot use it for advertising or training.
- **Data export:** Dev can export all data as CSV/JSON at any time.

---

## 8. Update & Distribution System

### 8.1 Upload Pipeline
1. Dev runs `publish upload <build.zip>` (or points CLI at a directory).
2. CLI computes file hashes, detects changes from previous build.
3. Server stores full build + generates binary diff.
4. Dev sets metadata (changelog, channel, required vs optional).
5. Dev clicks "Publish" or schedules for later.

### 8.2 Patching Strategy
- **Full file replacement** for small games (<500 MB).
- **Bsdiff / xdelta3** for larger games — only changed bytes transferred.
- **Zstd compression** for all downloads.
- **Resumable downloads** with HTTP range requests.
- **Integrity verification:** SHA-256 hash per file, checked before launch.

### 8.3 Channel System
| Channel | Audience | Update Behavior |
|---------|----------|-----------------|
| Stable | All players | Auto-update (can defer 48h) |
| Beta | Opt-in players | Auto-update (can defer 7d) |
| Nightly | Dev + testers | Always update to latest |

### 8.4 Large Game Optimization
- For games >10 GB: offer P2P peer-assisted downloads (libtorrent-based).
- Dev can provide magnet links or platform manages a tracker.
- Fallback to CDN if no peers available.

---

## 9. Developer Experience & Tools

### 9.1 Developer Onboarding
1. Sign up with GitHub / email.
2. Set up payment info (Stripe Connect onboarding).
3. Download CLI + SDK.
4. `publish init` → generates config file.
5. `publish upload` → first build submitted.
6. Fill store page via web dashboard or `publish store edit`.
7. Submit for listing — automated checks pass, game goes live.

### 9.2 SDK & Integration
| Engine Support | Status | Notes |
|---------------|--------|-------|
| Unity | Phase 1 | Package via UPM, no-code analytics setup |
| Unreal Engine 5 | Phase 1 | Plugin via Marketplace |
| Godot | Phase 1 | GDExtension or C# binding |
| Custom (C/C++/Rust) | Phase 1 | Static library, C ABI |
| GameMaker / Construct | Phase 2 | Community-driven or SDK wrapper |

### 9.3 API for Automation
```
POST   /v1/builds                    Upload new build
GET    /v1/builds/:id                Build status
POST   /v1/releases                 Create release
GET    /v1/analytics/dau            Daily active users
GET    /v1/analytics/events         Custom event query
POST   /v1/pricing                 Set regional prices
GET    /v1/sales                    Sales report
```

All API responses paginated with cursor-based pagination. Rate limit: 1000 req/min.

### 9.4 CI/CD Integration
- GitHub Action: `publish-game` — runs `publish upload` on tag push.
- GitLab CI template, Jenkins plugin (Phase 2).
- Webhook on new version: POST to dev's URL with build ID.

---

## 10. Storefront & Discovery

### 10.1 Store Pages
- Rich markdown descriptions, custom CSS (sandboxed), embedded video, GIFs.
- Recommendation engine: Collaborative filtering + tag-based similarity.
- Curated collections: "Picks of the Week," community-voted lists.
- User reviews: Upvote/downvote, no "review bombing" mitigations (recent activity weighted).

### 10.2 Search & Discovery
- Full-text search with typo tolerance (Meilisearch).
- Faceted filters: genre, price range, platform, features (multiplayer, VR, controller support).
- "Similar games" carousel on each store page.
- Developer blogs shown on store page (built-in mini CMS).

### 10.3 Wishlists & Following
- Wishlist analytics shown to devs: "43 people wishlisted after the trailer update."
- Follow devs to get notified of new releases and updates.

---

## 11. Community & Social Features

### 11.1 Built-in (Phase 1)
- **User profiles:** Game library, wishlist, reviews, friends.
- **Reviews & ratings:** Star rating (1-5) + text review. Helpfulness voting.
- **Discussion boards:** Per-game forums (optional — dev can disable).

### 11.2 Phase 2
- **Friend system:** Chat, game invites, "what friends are playing."
- **Screenshots & sharing:** In-game screenshot capture (overlay), upload to gallery.
- **Workshop / mods:** Mod hosting with versioned dependencies. Dev approves mods.
- **Game jams:** Host jam pages, time-limited submissions, community voting.

---

## 12. Monetization for the Platform

### 12.1 Revenue Sources
1. **Revenue split (primary):** 15% of all game sales.
2. **Analytics Pro:** $19/mo — extended event history (365d), custom dashboards, CSV export, Slack integration.
3. **DRM licensing:** Tier 1 = free, Tier 2 = $5/mo per game, Tier 3 = $15/mo per game.
4. **Promoted placement:** Devs pay for featured slots in search/categories (auction-based, similar to Steam's "featured" slots — but transparent pricing).
5. **Publisher services:** For devs who want help with localization, QA, porting — refer to vetted partners, take a finder's fee.

### 12.2 Financial Projections (Rough)
| Metric | Year 1 | Year 2 | Year 3 |
|--------|--------|--------|--------|
| Games listed | 500 | 3,000 | 10,000 |
| Platform revenue (est.) | $350K | $2.5M | $8M |
| Break-even | No (investing) | Yes | Profitable |

---

## 13. Competitive Landscape

### 13.1 Direct Comparison

| Platform | Strengths | Weaknesses | Opportunity for Us |
|----------|-----------|------------|-------------------|
| **Steam** | Massive user base, features, trust | 70/30 split, poor discoverability, no mobile | Better split, better dev tools, mobile support |
| **itch.io** | Dev-friendly, flexible, open | No DRM, no analytics, low traffic | Professional tooling + indie ethos |
| **GOG** | DRM-free, curated, trusted | Hard to get in, PC-only, slow updates | Self-service indie publishing |
| **Epic Games Store** | 88/12 split, UE integration | Low userbase, exclusive-focused, sparse features | Always open, no exclusives required |
| **Humble / Green Man** | Curated, bundles | Distributors, not platforms | Direct-to-player relationship |
| **Xbox Game Pass / PC Game Pass** | Revenue guarantee | Deal-based, not self-serve | Different category entirely |

### 13.2 Our Niche
The indie who:
- Has a game on Steam earning $1K–$50K/mo (the "long tail").
- Wants to also reach mobile players.
- Wants better analytics than Steamworks.
- Wants a bigger cut.
- Is willing to give up Steam's massive user base for better margins + mobile reach.

**Winning strategy:** Not "replace Steam" but "be the secondary store every indie uses." Offer a "publish once, sell everywhere" model — we handle licensing across platforms.

---

## 14. Risks & Challenges

### 14.1 Technical Risks
| Risk | Mitigation |
|------|-----------|
| Binary diff performance for large games | Use rsync-style delta (zdelta/xdelta3), benchmark early |
| Analytics pipeline scaling to millions of events/day | Kafka + ClickHouse is battle-tested; plan for 10M+ events/day |
| DRM being cracked | Accept it; DRM is about convenience, not absolute security. Make it easy enough that most won't bother cracking |
| Cross-platform client maintenance | Use Tauri (Rust core, web UI) — one codebase, three platforms |

### 14.2 Business Risks
| Risk | Mitigation |
|------|-----------|
| Low developer adoption | Build for a specific pain point (analytics + mobile), not a Steam clone |
| User acquisition (players) | Developer-driven: each dev brings their audience. Seed with launch partnerships |
| Payment fraud, chargebacks | Stripe Radar + manual review threshold; hold payouts for 14 days |
| Legal: DMCA, IP disputes | Clear TOS, takedown process, copyright registration optional |

### 14.3 Platform Risks
- **Steam retaliating:** Valve could mandate exclusivity or ban cross-linking. Mitigation: don't position as "anti-Steam," position as "complementary."
- **Mobile platform gatekeeping (Apple/Google):** Apple's 30% cut and sideloading restrictions. Mitigation: web-based install for iOS (PWA-ish), or accept Apple's cut and pass to dev.
- **Regulatory:** EU Digital Markets Act may help (sideloading required by 2027). Stay compliant from day 1.

---

## 15. Roadmap / Phased Build Plan

### Phase 0: Foundation (Months 1–4)
- [ ] API Gateway + Auth Service (OAuth 2.0)
- [ ] Store Service (basic listings, purchase flow)
- [ ] Payment Service (Stripe integration, basic checkout)
- [ ] Build Service (upload, store, basic download)
- [ ] CLI tool (upload, publish)
- [ ] Windows launcher (alpha, install + launch only)

**Milestone:** Dev can upload a game and a player can buy and download it.

### Phase 1: Core (Months 5–9)
- [ ] Analytics Service (ingestion + dashboard v1)
- [ ] DRM Service (Tier 1 & 2)
- [ ] Update System (binary diff, channels, rollback)
- [ ] macOS + Linux launchers
- [ ] Unity + Unreal SDKs
- [ ] Developer Dashboard (sales, analytics, builds)
- [ ] Community features (reviews, basic profiles)

**Milestone:** Feature parity with itch.io + basic Steamworks capabilities.

### Phase 2: Growth (Months 10–14)
- [ ] Mobile support (Android APK distribution)
- [ ] iOS support (web buy + code redemption)
- [ ] P2P update distribution
- [ ] Analytics Pro (paid tier)
- [ ] Promoted placements (auction)
- [ ] Godot + GameMaker SDKs
- [ ] Workshop / mod support
- [ ] Game jams

**Milestone:** Unique value proposition — mobile + desktop with one SDK.

### Phase 3: Scale (Months 15–24)
- [ ] Friend system, chat, overlay
- [ ] Localization marketplace (community translations)
- [ ] Publisher services marketplace
- [ ] Regional data centers (APAC, LATAM)
- [ ] Enterprise features (bulk licensing for studios)
- [ ] API v2 with GraphQL
- [ ] Platform-native streaming (cloud gaming, experimental)

**Milestone:** Self-sustaining platform with 10,000+ games and 500K+ monthly active players.

---

## Appendix A: Key Open Questions

1. **Should we build a custom launcher or integrate with existing ones like Playnite?** — Building our own gives brand presence but is expensive. Consider Playnite plugin for Phase 1, custom launcher for Phase 2.
2. **How do we handle refunds?** — Steam-style (≤2 hours played, ≤14 days since purchase) or more generous?
3. **Bundle support?** — "Buy the dev's collection" or "build your own bundle"? itch.io does this well.
4. **Gifting?** — A must-have for social virality. Adds fraud vectors.
5. **Regional licensing restrictions?** — Some games are region-locked by publisher. Do we support that?
6. **What about free-to-play / microtransactions?** — Our 15% on IAP? Different model entirely. Phase 3 question.
7. **Server hosting for multiplayer?** — Do we offer game server hosting or just matchmaking? Likely neither — partner with Multiplay / Edgegap.

## Appendix B: Ideal Tech Stack Summary

| Layer | Choice | Why |
|-------|--------|-----|
| Backend language | **Rust** (performance-critical), **Go** (services) | Rust for build/analytics (CPU-heavy), Go for API services (fast iteration) |
| Database | **PostgreSQL** (primary), **ClickHouse** (analytics), **Redis** (cache) | Proven, reliable |
| Search | **Meilisearch** | Dev-friendly, typo-tolerant, fast |
| Queue | **Kafka** (analytics), **RabbitMQ** (notifications) | Kafka for high-throughput events |
| Client | **Tauri (Rust + web)** | Small binary, cross-platform, modern |
| Cloud | **Hetzner / OVH** (bare metal), **Cloudflare** (edge/cdn) | Cost-effective, indie-friendly pricing |
| Container | **Nomad** | Simpler than K8s for small team |
| CI/CD | **GitHub Actions** | What the team knows |
