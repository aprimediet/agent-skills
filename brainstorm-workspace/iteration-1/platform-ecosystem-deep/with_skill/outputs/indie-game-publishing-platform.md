# IndieGameHub — Indie Game Publishing Platform

> Brainstorm | Depth: deep | Generated: 2026-06-09

## Core Idea

A publishing and distribution platform purpose-built for indie game developers — handles storefront listings, payment processing, DRM, analytics, automatic updates, and community features across Windows, Mac, Linux, and mobile. An indie-first alternative to Steam that prioritizes developer economics, transparent algorithms, and a genuine audience connection rather than a black-box marketplace that takes 30%.

## Problem & Motivation

- **Problem**: Indie developers are trapped in a broken ecosystem. Steam takes 30% revenue, buries indie titles under AAA marketing budgets, and provides opaque discoverability algorithms. itch.io offers better terms but lacks distribution infrastructure (DRM, auto-updates, proper analytics). GOG requires DRM-free which limits commercial viability for many devs. Epic takes 12% but is selective and PC-only. No single platform offers fair revenue share, genuine discoverability, cross-platform distribution, and the tooling indie devs actually need — auto-updaters, analytics, DRM choices, community building, and wishlist/release orchestration.
- **Who**: Solo indie developers and small indie studios (1–15 people) making PC and mobile games. These are developers who are technically competent but don't have the resources to build their own distribution infrastructure. They want to focus on making games, not on building a payment system, update servers, or analytics pipeline.
- **Why now**: Steam's 30% cut is increasingly untenable as development costs rise. The Unity runtime fee debacle and Unreal Engine royalty changes have made developers acutely sensitive to platform risk. Developers are actively seeking alternatives. Meanwhile, indie games are a larger market segment than ever — $4B+ annually. The indie audience is also tired of Steam's "firehose" problem (13,000 games released in 2024 alone) and wants curated discovery. The technological pieces (cloud CDN, serverless, Stripe Connect, Electron/Tauri for launchers) are mature enough that a new platform is feasible without building everything from scratch.

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Architecture | Cloud-native modular monolith with CDN distribution layer | Rapid development for MVP. Core platform (storefront, auth, payments, dev dashboard) as a monolith. Distribution pipeline (CDN, auto-updater, analytics ingestion) as separate services from day one — these have fundamentally different scaling profiles. |
| Frontend (store) | Next.js with SSR | SEO-critical for game pages. Fast page loads. Server components for game listings, wishlists, and search. Client components for interactive features (reviews, community). |
| Client launcher | Tauri (Rust-based, lightweight alternative to Electron) | Electron is 100MB+ per install — unacceptable for a game launcher. Tauri uses the system webview (30-50MB) with Rust for native functionality (file system access for game installs, registry management, auto-updater control). Cross-platform by default (Windows, Mac, Linux). |
| DRM | Tiered: no DRM / lightweight (Steam-style stub) / 3rd-party (Denuvo) partnership | Not all indies want DRM. Give developers choice. Default: lightweight CEG-style stub that validates ownership on launch (offline grace period). Premium: refer to Denuvo or similar with volume pricing. No-DRM option for devs who prefer GOG-style distribution. |
| Payment processing | Stripe Connect with platform fee split | Handles global payments, tax compliance, and payouts to developers. Platform takes a configurable cut (target 15%) from each sale. Stripe Connect's "destination charges" model means each sale is direct from customer to dev with platform fee skimmed. No capital required — no holding money. |
| Auth | OAuth (Steam, Google, GitHub, Discord) + email/password | Gamers expect social login. Steam OAuth is essential for cross-platform identity. Discord login for community integration. GitHub login for devs. |
| Update delivery | Custom delta-update protocol on CDN (CloudFront/Cloudflare R2) | Full game downloads are expensive and slow. Binary diff patching (bsdiff/hdiff) reduces update sizes by 60-90%. CDN edge caching for popular titles. Background patching in the launcher. |
| Analytics pipeline | ClickHouse + Redpanda (Kafka-compatible message broker) | Game events are write-heavy (thousands of events per session per player). ClickHouse handles OLAP queries on event streams efficiently. Redpanda for ingestion buffering. No Postgres for analytics — it collapses under write load. |
| Revenue share | 15% flat, reduced to 10% after $1M gross per game | Significantly better than Steam's 30% / 25% at $10M / 20% at $50M tier. The 10% tier after $1M incentivizes successful games to stay rather than going direct. |

## Dimensions Explored

### Architecture & Tech Stack

The platform has three distinct subsystems with different architectural needs: (1) the **storefront and developer portal** — a typical web app with auth, listings, payments, and dashboards, (2) the **distribution pipeline** — game file storage, CDN delivery, and the auto-updater protocol, and (3) the **analytics pipeline** — high-volume event ingestion and querying. Subsystem 1 works well as a monolith (Django or Rails with a Next.js frontend), deployed on containers with Postgres, Redis, and standard job queues. Subsystem 2 is glued to CDN infrastructure and needs its own service for managing builds, generating diffs, and orchestrating releases. Subsystem 3 is the most architecturally distinct — it's write-heavy, needs columnar storage, and benefits from stream processing. The tech stack across all three is unified by a shared language for the API layer (TypeScript/Node.js for API gateways) but each subsystem uses the best tool for its job internally.

- The storefront monolith uses Postgres as the primary store and Redis for caching (game listings, session state, wishlist counts). Background jobs (email notifications, receipt generation, build processing) go through a job queue.
- The launcher communicates with the distribution API via signed JWTs. The launcher checks for updates, downloads manifests, verifies file integrity via SHA-256 hashes, and applies binary diffs.
- Real-time features (community chat, live game status, concurrent player counts) use WebSockets via a dedicated Socket.io or Phoenix Channels server. This is extracted from the monolith early because it has persistent connections.
- Game developers upload builds via the developer portal (web UI) or a CLI tool. The build pipeline compresses, signs, diffs against the previous build, and deploys to CDN. An S3-compatible object store (Cloudflare R2 or Backblaze B2) holds the canonical build artifacts.

### Data Model & Storage

The core entities are: **Games** (metadata, builds, pricing, DRM config, analytics config), **Developers** (user profiles, payment info from Stripe Connect, game library), **Players** (user profiles, purchased games, playtime, reviews, wishlists), **Transactions** (purchases, refunds, chargebacks, payout records), **Builds** (version, file manifest, checksums, diff artifacts, release channel — stable/beta/alpha), and **AnalyticsEvents** (immutable event stream: session start, achievement, crash, purchase, etc.). Games have a one-to-many relationship with builds. Each build references a set of files with their SHA-256 hashes and sizes. The file manifest is used by the launcher to verify local installation integrity.

- Postgres handles transactional data. The games table has JSONB for flexible metadata (trailer URLs, tags, system requirements JSON, supported languages, DRM config).
- The builds table references objects in S3-compatible storage. Files are content-addressed (hash-based naming) for deduplication across builds.
- AnalyticsEvents go into ClickHouse, not Postgres. A typical game might emit 50-100 events per session. With 10,000 concurrent players, that's 500K-1M events per hour. Postgres cannot handle this write volume gracefully.
- Each developer gets their own ClickHouse "database" (logical separation within the cluster) so analytics queries from one game don't impact another. Developers query their game data through a REST API that translates to ClickHouse SQL.
- Player game libraries are a simple join table with purchase status, install path, last played timestamp, and current build version installed.

### Security & DRM

DRM is a spectrum, not a binary choice. The platform offers three tiers: (1) **No DRM** — the game files are delivered as-is. The launcher manages installation and updates but there is no runtime validation. This appeals to developers who trust their audience or whose games are already easily pirated. (2) **Lightweight DRM** — a small runtime stub bundled with the game executable that checks license validity at launch. Players authenticate through the launcher, which generates a short-lived token the game verifies locally. Offline grace period of 14 days (or configurable by the developer). Token is cached locally and refreshed on network availability. This catches casual sharing but won't stop determined crackers. (3) **Third-party DRM** — partnership with a DRM vendor (Denuvo, VMProtect) for developers who want robust protection. The platform provides the integration layer; the developer contracts directly with the DRM vendor.

- The lightweight DRM stub is open-source (MIT license) so developers can inspect it. Transparency builds trust. The stub is ~50KB and does two things: validates the license token signature, and checks a local cache for offline expiry.
- No kernel-level anti-cheat or always-online requirements. Indie games don't have competitive multiplayer cheating problems at scale. If a developer needs anti-cheat (competitive multiplayer games), recommend Easy Anti-Cheat or BattlEye integration as a separate concern.
- Payment security is handled by Stripe Connect. The platform never touches raw credit card numbers. All sensitive data (payout preferences, tax IDs) are stored in Stripe, accessed via API on demand.
- Developer accounts require 2FA (TOTP or WebAuthn). Player accounts have optional 2FA. Developer API keys are scoped per-game with granular permissions (read analytics, upload builds, manage pricing).

### Business Model & Monetization

The core revenue model is a **15% platform fee on gross sales** — half of Steam's standard 30%. This drops to 10% after a game grosses $1M on the platform. The rationale is that at $1M+, the developer could afford to go direct (their own storefront, payment processing) and the reduced fee creates a retention incentive. No upfront listing fees, no "Steam Direct" equivalent ($100 Steam fee). Developers pay nothing to publish. Additional revenue streams: (1) a **featured placement marketplace** — developers can bid for placement in curated carousels (not an opaque algorithm). Auction-based, transparent pricing. (2) **Cloud save storage** — free tier (100MB/game), premium tier (10GB/game, $2.99/mo for players). Platform takes 30% of premium storage revenue. (3) **Asset hosting** — indies can host and sell DLC, soundtracks, and art books through the platform. Platform takes 15% on those too. (4) **Bundles and sales events** — curated seasonal sales where the platform takes 12.5% (promotional rate). Developers opt in.

- No paid wishlist slots, no payola for search results, no "visibility" black box. Developers see exactly how discoverability works: recently updated, trending (based on normalized wishlist additions), staff picks (human-curated), and tag-based search.
- The 15% rate is survivable if the platform achieves scale. Steam's margin at 30% is estimated at 25-30% after payment processing, bandwidth, and operational costs. At 15%, margins are thinner but viable with efficient infrastructure (CDN caching, serverless, minimal staff). Target is 5,000 paying games to reach operational breakeven.
- Mobile game distribution is a separate question. iOS requires sideloading (possible in EU via DMA, globally uncertain) or signing up as a marketplace. Android allows third-party stores natively. The MVP should focus on desktop (Windows/Mac/Linux) and add mobile after traction on desktop.

### Competition & Differentiation

The competitive landscape: **Steam** (dominant, 30% cut, 13K+ releases/year, Valve doesn't share roadmap or algorithm details, terrible for indie visibility), **itch.io** (great for discovery, no DRM, no auto-updater, no proper analytics, community-focused but not a storefront), **GOG** (DRM-free only, curated, limited to PC, slower to accept indies), **Epic Games Store** (88/12 split but curated and PC-only, limited tools for devs), **Humble Games Store** (bundle-focused, not a publishing platform), and **Xbox Game Pass / PC Game Pass** (subscription model, curated, takes rights/licensing). The key differentiation: IndieGameHub is the only platform that combines (a) genuinely fair revenue share, (b) transparency in curation and algorithm, (c) cross-platform support including mobile, (d) the tooling indies actually need (analytics, DRM tiers, auto-updates, community features) as a unified offering.

- Steam's lock-in is real but weakening. Developers increasingly run their own storefronts (GameJolt, Itch.io, direct sales via Humble widget) alongside Steam. A platform that provides Steam-level distribution infrastructure at half the cost, with better discoverability and transparency, is compelling.
- Itch.io is the closest analogue but lacks the distribution infrastructure (no launcher, no auto-updater, no built-in analytics, no DRM). Itch is for discovery and sales; IndieGameHub is for publishing and ongoing distribution.
- The moat is twofold: (1) developer tooling — once a developer builds their update pipeline and analytics setup around the platform, switching costs are high, and (2) player library lock-in — players who build a library on the platform are sticky. The launcher is the moat.

### Developer Experience & Workflows

The developer portal is the heart of the platform. It needs to be genuinely delightful, not an afterthought. The workflow: (1) **Sign up and verify identity** — Stripe Connect onboarding for payouts, 2FA setup, tax info collection (W-9/W-8BEN for US, equivalent for others). (2) **Create a game page** — title, description, screenshots, trailer, tags, system requirements, pricing. WYSIWYG editor with preview. (3) **Upload a build** — via web upload, CLI tool, or direct API. The platform validates the build (checks for malware via VirusTotal API, verifies executable structure, runs basic sanity checks). (4) **Configure settings** — DRM tier, pricing (including regional pricing suggestions based on market data), release date, pre-order availability, beta branches. (5) **Submit for review** — a human reviews the listing (not the game content — no "quality bar" like Steam, just verification that the listing is accurate and the build is functional). (6) **Release** — set a release date, manage wishlists, orchestrate launch.

- The build validation pipeline is crucial. It checks: executables aren't packed with known malware (VirusTotal API), the game launches (headless VM test, 30-second timeout), file manifest matches hash list, and all supported platforms have builds. This catches common issues before they reach players.
- Regional pricing is a massive pain point for indies. Steam suggests regional pricing but many indies get it wrong. The platform provides data-driven suggestions: "Based on 500 similar games, we recommend $14.99 in the US, R$55 in Brazil, and ¥58 in China." Developers can override, but it's a starting point.
- The wishlist system is first-class. Developers see: wishlist adds per day, conversion rate from wishlist to purchase, and the effect of events (press coverage, sale, update) on wishlist velocity. The launcher shows wishlisted games with release countdowns.
- Developer analytics dashboard: units sold (real-time), revenue (net after fees), refund rate, concurrent players, playtime distribution, crash rate (per build), and player geography. This is the analytics that indies need but currently get from 3-4 fragmented tools.

### Performance, Scalability & Distribution

Game distribution is bandwidth-intensive. A typical indie game is 500MB–5GB. A popular launch could push 10TB+ in a day. The distribution architecture: game files are stored in S3-compatible object storage (Backblaze B2 at $0.006/GB/month, egress at $0.01/GB), cached at CDN edge (CloudFront or Cloudflare R2 at ~$0.01-0.03/GB egress). The launcher downloads game files from the nearest CDN edge. For updates, the launcher downloads only the binary diff (using bsdiff or hdiff), not the full game. The diff server computes the delta when the developer uploads a new build, stores it alongside the full build, and serves it via CDN. This reduces update downloads by 60-90%.

- CDN costs are the single largest operational expense. At 15% revenue share, bandwidth cost must stay below 3% of gross revenue for the platform to be viable. Target: <$0.02/GB effective egress cost through CDN negotiation and multi-CDN strategy.
- The launcher implements peer-to-peer distribution as an optional fallback (similar to Battle.net's peer-to-peer or Steam's content sharing). Players on the same LAN or ISP can share already-downloaded game files. This is opt-in and verified via hash checks.
- For launch day spikes, the platform uses pre-loading: players who pre-ordered can pre-load the game 48 hours before release. This spreads the download burst over two days.
- Mobile distribution is architecturally different: on Android, the platform can distribute APK/AAB files directly through the launcher app. On iOS, the platform needs to either (a) distribute via the App Store as a "store within a store" (not allowed by Apple), (b) use TestFlight-like ad-hoc distribution for beta/early access (limited to 10K users), or (c) participate in Apple's upcoming third-party marketplace framework (EU DMA compliance, rolling out 2024-2026). The recommendation: target Android first for mobile support, treat iOS as a future opportunity dependent on regulatory changes.

## Open Questions

- **What happens when a developer wants to leave the platform?** Players who purchased games through the platform expect continued access. If a developer moves their game to Steam or direct sales, players who bought on IndieGameHub need to keep their access. One option: the platform continues hosting the game files (read-only, no updates) for existing purchasers indefinitely. Another: the platform provides a migration tool that transfers licenses. This needs a clear policy before launch.
- **How do we handle refunds without destroying developer revenue?** Steam's 2-hour/14-day refund policy works but hurts indies disproportionately (short games can be completed and refunded). Options: (1) match Steam's policy for consumer trust, (2) a developer-configurable refund window (1-4 hours) with a platform minimum of 1 hour, (3) no-question refund within 48 hours regardless of playtime, then case-by-case. The right answer depends on consumer protection laws and competitive positioning.
- **Should the platform have a built-in community/forum system or integrate with Discord?** A built-in forum system (like Itch.io's per-game forums) adds development cost but keeps players on the platform. Discord integration is cheaper and leverages existing communities but fragments the experience. Compromise: lightweight per-game discussion board (Markdown, threaded) plus optional Discord widget/SDK integration for real-time chat.
- **Should the launcher be optional?** Some players prefer buying through the web and downloading directly. Others want a launcher for auto-updates and library management. The recommendation: the launcher is recommended but not required. Direct downloads are available from the web store for a limited time (30 days post-purchase). This reduces friction for hesitant buyers.
- **How do we verify developer identity without being exclusionary?** Stripe Connect's identity verification can take weeks and requires government ID. Many indies are outside the US or are minors. The platform needs alternative verification paths (GitHub presence, past game releases, trusted reference from an existing developer on the platform) while still meeting KYC/AML requirements for payment processing.

## Research Suggestions

Topics that need deeper investigation by the researcher skill:

- **CDN cost optimization for game distribution** — Bandwidth costs are the single largest operational expense. Need to benchmark CloudFront, Cloudflare R2, Fastly, and Bunny CDN for game file delivery. Evaluate multi-CDN strategies, peer-to-peer distribution overhead, and caching effectiveness for game files (which are often not cache-friendly large binaries). Suggested researcher query: "CDN cost optimization for large binary game file distribution — cost per GB comparison across CloudFront, Cloudflare R2, Fastly, Bunny CDN in 2025-2026"

- **Binary diff patching algorithms for game updates** — Deciding between bsdiff, hdiff, and Courgette for game update patching. Need data on average patch sizes for common game file types (assets, compiled code, audio). Also need to evaluate memory/CPU requirements for applying patches on player machines. Suggested researcher query: "Binary diff algorithms bsdiff vs hdiff vs Courgette for game update delivery — patch size reduction ratios and client-side resource requirements"

- **Regional pricing data and consumer behavior in game markets** — Steam's regional pricing is based on decade-old PPP data. Need current research on price elasticity in major game markets (Brazil, China, India, Russia, EU). What regional price ratios drive optimal conversion without leaving money on the table? Suggested researcher query: "Regional pricing optimization for indie PC games — price elasticity by country, Steam regional pricing data analysis 2024-2025"

- **Third-party marketplace compliance on iOS (EU DMA)** — Apple's third-party marketplace framework is evolving rapidly (EU DMA compliance). Need to understand the current requirements, fees (Core Technology Fee €0.50 per install), limitations (sideloading only in EU?), and timeline. This determines whether mobile iOS distribution is feasible in 2026-2027. Suggested researcher query: "Apple third-party marketplace requirements under EU Digital Markets Act — current state, fees, limitations, and timeline for game distribution 2025-2026"

- **Stripe Connect vs alternative payment platforms for marketplace payouts** — Comparison of Stripe Connect, Adyen for Platforms, Paddle, and Lemon Squeezy for handling game sales with split payments. Need data on: payout speed, fee structures, tax compliance automation, refund handling, and country coverage for both merchants (developers) and customers. Suggested researcher query: "Payment processing platforms for game distribution marketplaces — Stripe Connect vs Adyen vs Paddle vs Lemon Squeezy fee comparison and feature analysis 2025"

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Cold-start problem — no developers means no games, no games means no players, no players means no developers | High | High | Launch with 20-30 curated indie titles that have existing audiences. Offer zero platform fees for the first 3 months to early adopters. Build a waitlist of 10,000+ players before announcing developer partnerships. Partner with 5-10 known indie studios as launch partners. |
| Bandwidth costs exceed revenue at 15% fee | Medium | High | Negotiate CDN volume discounts before launch. Implement peer-to-peer sharing in the launcher. Cap per-game bandwidth (not per-player — per-game: if a game costs the platform more in bandwidth than it generates, renegotiate pricing with that developer). Target <$0.02/GB effective egress. |
| Stripe Connect onboarding friction drives developers away | Medium | Medium | Build a streamlined onboarding wizard. Allow developers to start building their game page and upload builds before completing payment verification. Only require full KYC when listing goes live or when revenue exceeds $100. Offer alternative verification (GitHub profile, existing game on Steam). |
| Players perceive a "lesser" platform vs Steam's convenience | Medium | High | The launcher must be as polished as Steam's. No compromise on UX: seamless install, auto-updates, overlay support (screenshots, FPS counter, screenshot sharing), cloud saves, and a clean library UI. The platform must feel premium, not like an indie side project. |
| Developers release malware or malicious builds through the platform | Low | High | Automated malware scanning (VirusTotal API + YARA rules) on every upload. Manual review for new developers' first upload. Reputation system: developers with a history of clean builds get expedited reviews. Bond/insurance requirement for developers distributing builds over a certain size or price. |
| Refund abuse (buy, finish, refund) hurts developer revenue | Medium | Medium | Developer-configurable refund windows (1-4 hours) with a platform minimum. Anti-abuse detection: flag accounts with >30% refund rate. Restrict refunds to one per game per account. Transparent refund policy disclosed at checkout. |
| Mobile distribution blocked by platform policies (Apple/Google) | High | Medium (for strategy) | Prioritize desktop (Windows, Mac, Linux) for MVP. Launch mobile on Android via direct APK distribution through the launcher. Treat iOS as a regulatory-dependent opportunity. If the DMA creates viable third-party marketplace access, invest in iOS. Otherwise, focus on desktop + Android. |

## Next Steps

1. **Build a clickable prototype of the developer portal** — focus on the game submission flow (create listing, upload build, configure settings, release). Test with 5-10 indie developers to validate the workflow before building the full platform. Use this to refine the developer experience before writing production code.

2. **Negotiate CDN commitments** — approach Cloudflare (R2), Bunny CDN, and AWS (CloudFront) for committed-use pricing at projected volume (estimate 50TB/month after 6 months). Get letters of intent so the unit economics model is based on real numbers, not public pricing.

3. **Build the launcher MVP** — Tauri-based launcher with the minimum feature set: library display, install/uninstall, auto-updater (download full game initially, add delta patching later), and platform login. Ship to a small beta group of players to validate UX before full launch.

4. **Recruit launch partner developers** — identify 20-30 indie games that are: in active development or recently released, have an existing audience (wishlists, social following), and are frustrated with Steam's revenue share or discoverability. Offer them zero fees for 6 months and co-marketing support in exchange for being launch titles.

5. **Build and validate the unit economics model** — model projected revenue at 15% fee vs. bandwidth costs, payment processing fees (Stripe: 2.9% + $0.30), and operational costs. Determine the minimum number of paying games and average revenue per game needed for breakeven. Model multiple scenarios (optimistic: 500 games in year 1, realistic: 200 games, pessimistic: 75 games). This model determines whether the business is viable before writing code.

---
*Brainstorm document produced by brainstorm skill. Use the librarian skill to persist this artifact.*
