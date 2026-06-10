# IndieGameHub — Indie Game Publishing Platform

> Brainstorm | Depth: deep | Generated: 2026-06-09

## Core Idea

A publishing platform tailored for indie game developers that handles payment processing, DRM, analytics, and update distribution — essentially an indie-friendly alternative to Steam without the 30% revenue cut, opaque algorithms, and storefront noise. Developers get a custom storefront, buyers get a curated discovery experience, and the platform takes a flat 10% commission with no exclusivity requirements.

## Problem & Motivation

- **Problem**: Indie game developers are squeezed between Steam's 30% cut and algorithmic obscurity, and the fractured alternative landscape (Itch.io has no DRM/analytics, GameJolt has a small audience, self-publishing requires building your own infrastructure). There is no mid-tier platform that combines professional publishing tools (DRM, analytics, updates) with fair economics and genuine discovery support.
- **Who**: Indie game developers with 1-10 person teams who want professional publishing infrastructure without Steam's costs; also indie-friendly game players who want curated discovery outside Steam's firehose.
- **Why now**: The indie game market is projected to grow 12% YoY through 2030. Platforms like Itch.io proved there's demand for an alternative, but haven't built the professional tooling developers need. Meanwhile, Steam's 30% cut is increasingly questioned as distribution costs have plummeted (CDN costs have dropped 70%+ in 5 years). The window for a fairer platform is open.

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Architecture | Modular monolith with service extraction path | Core platform (auth, storefronts, payments, user accounts) as monolith. Extract DRM verification, analytics pipeline, update distribution as separate services when scale demands it. |
| Frontend | Next.js for storefront + React Native for launcher client | SSR for SEO on store pages, progressive web app for discovery. Native launcher client for DRM, auto-updates, and overlay features. |
| Payment processing | Stripe Connect for seller payouts, Stripe for buyer payments | Direct Stripe integration avoids building payment infra. Stripe Connect handles split payments (platform cut → us, remainder → dev) automatically. |
| DRM | Cloud-verified license token + optional binary encryption | No rootkit-style DRM. Lightweight cloud check on launch (configurable offline period, e.g., 72 hours). Optional AES-256 encryption for developers who want it. |
| Game distribution | Signed builds via signed URLs with CDN edge caching | Game builds are uploaded to S3-compatible storage, distributed via CloudFront/CDN with signed URLs that expire per download. Delta updates via bsdiff for patches. |
| Analytics pipeline | Event-sourced telemetry with Parquet export | Game events (session start, achievements, crashes) streamed to Kafka, stored in S3 as Parquet, queryable via Presto/Trino. Developers get a dashboard and raw data export. |
| Revenue model | 10% commission on sales + optional premium features | 10% flat (vs. Steam's 30%). Premium features: advanced analytics ($9/mo), custom storefront theming ($5/mo), bundle/pack management (free). No exclusivity. |
| Developer onboarding | Self-serve with 24-hour manual review | Submit game info, upload build, set price. Review checks for malware, copyright, content guidelines. Reviewed by a real person (all 3 team members rotate). |

## Dimensions Explored

### Architecture & Tech Stack

The platform splits into two major surfaces: the web storefront (where players discover and buy games) and the native launcher client (where players download, launch, and update games). The web storefront is a Next.js application with server-side rendering for store pages, game listings, and developer dashboards — critical for SEO. The launcher client is a React Native (or Tauri for smaller binary size) application that handles DRM verification, game library management, download/resume, auto-updates, and an optional overlay for in-game screenshots and friends. The backend is a modular monolith in Node.js or Go (undecided — Go for performance on DRM/license verification routes, Node.js for faster iteration on the storefront API). Separate satellite services handle: (1) the analytics pipeline (Go or Rust for throughput), (2) the CDN/game distribution layer (CloudFront/CDN with signed URLs), and (3) the DRM verification service (stateless, horizontally scalable).

- The modular monolith uses bounded contexts: Auth, Games, Payments, Licenses, Reviews, DeveloperAccounts. Each is a separate Go module or NestJS module with a well-defined API. This prevents the monolith from becoming a ball of mud.
- The launcher client communicates with the backend via a REST API for all CRUD operations and WebSocket for real-time notifications (friend activity, wishlist price drops, download status).
- Gamers don't need to create another account — OAuth sign-in via Steam, Google, GitHub, Discord. Guest accounts for try-before-you-buy demos.
- The DRM verification service runs as a stateless Lambda/Cloud Function — no server to manage, scales to zero when idle.

### Distribution & Update Pipeline

Game distribution is the platform's core technical challenge. When a developer uploads a build, the platform: (1) scans it for malware (ClamAV + a YARA ruleset), (2) signs the binary with a per-game certificate, (3) uploads to S3-compatible object storage, (4) generates a manifest file listing all files and their SHA-256 hashes, and (5) invalidates the CDN cache for that game's distribution endpoint. When a player downloads, the launcher requests a signed URL from the license verification service (valid only if the user owns the game). The signed URL expires after the download completes (or after 15 minutes). For updates, the system supports delta patching: on upload, a diff is computed against the previous build (using bsdiff for binaries and xdelta for assets), and the launcher downloads only changed blocks. Developers can manage multiple "branches" (alpha, beta, release) and set auto-update policies.

- Malware scanning is mandatory before any build goes live. Every build is scanned; flagged builds are quarantined with a report sent to the developer.
- Delta updates use a Merkle-tree-style hash comparison: the launcher knows the hash of every file it has; the manifest tells it which hashes changed; only changed blocks download. This reduces patch sizes by 60-90% for code-only updates.
- Developers can roll back to any previous build instantly — the manifest system makes it a CDN cache invalidation + version pointer update.
- The signed URL approach means the CDN does not need to know about auth — it just validates a pre-signed URL. This keeps the distribution pipeline simple and secure.

### DRM & Security

The DRM model is deliberately lightweight and developer-friendly, avoiding the invasive rootkit approaches common in AAA DRM (Denuvo, StarForce). Each game license is a signed JWT containing: user ID, game ID, purchase timestamp, and offline grace period expiry. The launcher client verifies online once at launch (lightweight HTTPS call to the DRM verification service), then allows offline play for a configurable period (default 72 hours). After the grace period, the launcher requires a re-check. Developers can opt into additional security: (1) binary encryption with a per-user key (the game binary is encrypted at rest on the CDN and decrypted by the launcher using a key retrieved at license verification time), (2) periodic heartbeats during gameplay (for multiplayer or always-online games), and (3) watermarking of screenshots/video capture. No Denuvo-style performance impact, no kernel-level drivers, no always-online requirement.

- The JWT license token is signed with a platform key and verified server-side on each check. Token contents include a device fingerprint (derived from hardware characteristics) to prevent token sharing across machines.
- Binary encryption is optional and opt-in. It adds ~2 seconds to first-launch time (decryption). Developers who choose it can also set a "re-verify every N hours" policy.
- Anti-tampering: the launcher client checks its own integrity via code signing and runtime integrity checks. If the client is modified, license verification fails.
- Server-side, the DRM verification service is stateless and horizontally scalable. It checks: does this user own this game? Is the device fingerprint valid? Is the offline grace period not exceeded? Response is a simple yes/no + new token.

### Payment Processing & Business Model

The financial model is built around fairness and transparency. Payments go through Stripe Connect — when a player buys a game, Stripe splits the transaction: 10% to the platform (our commission), 2.9% + $0.30 to Stripe (processing fee), and 87.1% - $0.30 to the developer. Developers can set their own prices (minimum $1.00, no upper limit), offer regional pricing (suggested based on the World Bank/SteamDB data), run sales, and create bundles. Payouts are weekly with a $50 minimum threshold, deposited directly to the developer's bank account. Players get Steam-style refunds: full refund within 2 hours of playtime or 14 days, whichever is shorter. The refund cost is borne by the platform (we return our commission) — the developer keeps their cut.

- Regional pricing is essential for indie games. Suggested pricing tiers: US/EU/AU (100%), UK/JP (85%), Latin America (50%), Southeast Asia (40%), India/Africa (25%). Developers can override per region.
- Bundles work like Steam: "Complete the Set" pricing, publisher bundles, and franchise bundles. Bundle pricing is prorated — buyers who own some items pay only for the missing ones.
- Developers can generate discount coupons (percentage or fixed amount, limited quantity or unlimited, time-bound) for press, influencers, and beta testers.
- Subscription model for developers: free tier (10% commission, basic analytics, 1 concurrent build branch); Pro at $19/mo (advanced analytics cohort report, 10 build branches, custom storefront CSS, priority support).
- No exclusivity — developers can publish on any other platform simultaneously. We compete on service and commission, not on locking in games.

### Competition & Differentiation

The competitive landscape includes: Steam (70% market share, 30% cut, massive audience but oversaturated and algorithm-dependent), Itch.io (indie-first, no DRM, no analytics, no update pipeline — more of a marketplace than a publishing platform), GameJolt (smaller audience, focused on web games and HTML5), GOG (curated, DRM-free, but AAA-focused and hard for indies to get into), Epic Games Store (88/12 split, but exclusive-focused and PC-only), and Humble Bundle (bundle-centric, not a full storefront). IndieGameHub's differentiation is: (1) professional publishing tooling (DRM, analytics, updates) combined with indie-friendly economics (10% commission, no exclusivity), (2) cross-platform support (Windows, Mac, Linux, and mobile as a secondary focus) — Steam has no mobile storefront for game sales, (3) developer-controlled discovery — instead of an opaque algorithm, developers can opt into curated collections, thematic bundles, and community reviews, and (4) transparent analytics — developers get raw event data, not just aggregated metrics.

- Itch.io has the community and indie ethos but lacks the professional tooling. Steam has the tooling but charges 30% and buries indies. IndieGameHub sits in the gap: indie-friendly economics with Steam-grade tooling.
- The 10% commission is sustainable because: (a) CDN costs have plummeted (CloudFront costs ~$0.085/GB, most game downloads are 1-5GB), (b) we don't have Steam's overhead (no massive office, no VR hardware division, no Steam Deck), (c) payment processing is handled by Stripe. Our marginal cost per sale is ~$0.50 (CDN + payment processing).
- The lack of exclusivity is a feature, not a limitation. We attract developers who want to use us alongside Steam, not instead of Steam. This reduces risk for developers and makes our platform additive rather than competitive.
- Mobile support is a long-term differentiator: no existing PC game storefront also sells mobile games. A unified publishing dashboard for PC + mobile could be compelling.

### User Experience & Discovery

The platform has four core surfaces: (1) the Storefront — curated game discovery with collections, tags, and a "New & Trending" section (curated by the team, not algorithmic), (2) the Developer Dashboard — tools for uploading builds, managing pricing, viewing analytics, and responding to reviews, (3) the Library — the player's purchased games in the launcher client, with download/update management, and (4) the Community Hub — per-game forums, user reviews, and mod/screenshot sharing. Discovery is curator-driven rather than algorithm-driven: the platform team creates weekly collections ("Roguelikes this week", "Games made in Godot", "Under 500MB bangers"), and developers can suggest their games for inclusion. User reviews are binary (recommend/don't recommend) with optional written review, and developers can respond publicly to reviews.

- The storefront emphasizes curation over quantity. No "sponsored" slots or paid placement within content — if you're featured, it's because the curators genuinely think it's good.
- Tags are developer-set but moderated by the platform team. Tag spam (tagging a puzzle game as "FPS" for visibility) results in a warning, then delisting.
- The launcher client has a built-in "DevLog" feed — developers can post dev blog updates that appear in players' feeds for games they own. This replaces Steam's news/event system.
- User reviews show playtime (under 2 hours = "early impression", 2+ hours = "review") to prevent review bombing without playtime. Review analysis sentiment over time is shown on the store page.
- Accessibility filters: players can filter games by accessibility features (colorblind modes, rebindable controls, subtitle options, text size options). Developers tag their games with supported features.

### Go-to-Market Strategy

Initial launch targets a curated cohort of 100 indie developers recruited via personal networks, r/gamedev, itch.io forums, and Discord communities. The pitch: "Launch your next game on our platform in addition to Steam — keep the extra revenue from the 10% commission while maintaining your Steam presence." For players, the pitch is "find great indie games without fighting Steam's algorithm, and know that 90% of your money goes to the developer." Launch timing targets the Winter/Spring indie game release window (February-March 2027, avoiding Steam's Winter/Summer sale clutter). Initial marketing budget ($20k) goes to: sponsoring 5-10 indie game-focused YouTube channels (GMTK, Game Maker's Toolkit adjacent), running a "December Dev Showcase" event where 50 featured indie games are highlighted, and a launch week "Everything 10% off" sale funded by the platform (we take 0% commission for launch week).

- Developer acquisition is the primary challenge — players follow games, and games follow developers. Focus recruiting on developers who already have a following and a game in development.
- Offer a "revenue guarantee" to the first 50 developers: if they make less on IndieGameHub in the first 6 months than they would have from Steam's 30% cut (estimated), we make up the difference. This lowers the risk of trying a new platform.
- Player acquisition through developer networks: each developer on the platform has a referral link for their audience. The developer gets 1% additional revenue share (i.e., 9% platform commission instead of 10%) for every player they refer who makes a purchase.
- Community-building before launch: a developer Discord server (for devs to discuss the platform, request features, give feedback) and a public "coming soon" landing page with email signup for players.

## Open Questions

- **Should the launcher client be open-source?** An open-source launcher builds trust (no spyware concerns) and invites community contributions, but makes the DRM/tamper-check logic visible and harder to protect. Potential middle ground: the launcher UI/framework is open-source, the DRM verification module is a closed-source dynamic library.
- **How do we handle chargebacks and fraud?** Game purchases are digital goods, so chargebacks hurt doubly (we lose the game AND the payment). Stripe Radar for fraud detection, IP/country velocity checks, and requiring verified email for purchases over $50. Chargeback cost is split 50/50 with the developer (or platform eats it above a certain threshold).
- **What is the offline DRM grace period for different game types?** 72 hours works for single-player games, but multiplayer games need different rules (can't play multiplayer offline anyway). Always-online games don't need offline grace. Should this be per-game configurable or platform-wide?
- **Should we support early access / paid demos / crowdfunding integration?** Steam Early Access is a huge revenue driver for indies. Supporting it means managing "promise vs. delivery" risk, refund policies for unfinished games, and development timeline tracking. Worth exploring but adds significant complexity to payment/review systems.
- **How do we handle regional pricing abuse?** Players using VPNs to buy from cheaper regions is a known problem. Solutions include: requiring a payment method from the same region, IP-based geolocation at checkout, and flagging accounts that switch regions frequently. Need to balance against accessibility for genuinely lower-income players.

## Research Suggestions

Topics that need deeper investigation by the researcher skill:

- **Delta update algorithms for game distribution** — The choice between bsdiff, xdelta, or a custom solution (hashed block-level diffing) affects patch sizes, client performance, and server CPU costs. Need benchmarks for typical game binary sizes (100MB-10GB). Suggested researcher query: "Delta update algorithms for game distribution — bsdiff vs xdelta vs block-level hashing for binary patch optimization 2026"
- **DRM approaches for indie games — effectiveness vs. user friction** — Need real data on how different DRM approaches (cloud-token, binary encryption, watermarking, always-online) affect piracy rates vs. customer satisfaction for indie games specifically (not AAA). Suggested researcher query: "DRM effectiveness for indie games — piracy rate impact and customer satisfaction tradeoffs for cloud-token vs binary encryption vs always-online DRM"
- **Stripe Connect marketplace models for digital goods platforms** — Stripe Connect has complex compliance requirements, including KYC/AML for developers, tax form collection (W-9/W-8BEN), and 1099 reporting. Need to understand the operational overhead and cost implications. Suggested researcher query: "Stripe Connect marketplace implementation for digital goods — KYC/AML requirements, tax reporting, and operational overhead for game publishing platforms"
- **Cross-platform game launcher architecture comparison** — Evaluate Tauri vs Electron vs React Native for building a game launcher client that handles large downloads, DRM verification, and overlay features on Windows, Mac, and Linux. Suggested researcher query: "Cross-platform game launcher client framework comparison — Tauri vs Electron vs React Native for download managers, DRM verification, and game overlays"
- **Game storefront curation models and their impact on developer satisfaction** — Compare algorithm-driven (Steam), curator-driven (Apple Arcade), and community-driven (Itch.io) discovery models. What are the metrics for developer satisfaction and revenue distribution under each model? Suggested researcher query: "Game storefront curation models — algorithm-driven vs curator-driven vs community-driven discovery and their impact on indie game developer revenue"

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Cold start — no players because no games, no games because no players | High | High | Recruit 100 developers before launch with revenue guarantee. Developer referral program turns existing audiences into player base. Seed with 10 curated collections. |
| Steam retaliates (e.g., demoting games also on our platform) | Low | Medium | Steam already allows multi-platform publishing. Legal risk is low. Mitigation: encourage developers to use us for "late port" releases (putting games on our platform 3-6 months after Steam launch), reducing competitive friction. |
| Payment fraud / chargebacks drain margins | Medium | High | Stripe Radar + manual review of flagged transactions. Chargeback buffer fund (5% of revenue set aside). Per-developer chargeback thresholds — if a developer's games generate excessive chargebacks, their payout schedule changes. |
| DRM is ineffective and games are widely pirated | Medium | Medium | Indie games are typically purchased, not pirated (piracy is a distribution problem — if the game is easy to buy at a fair price, most people pay). The DRM is lightweight by design. Focus on value (fair price, easy buying) over enforcement. |
| Malware in submitted game builds damages platform reputation | Low | High | Every build scanned with ClamAV + YARA. Automated quarantine of flagged builds. Manual review by team. Emergency game delisting and refund process if malware is discovered post-release. |
| Developer churn after revenue guarantee period ends | Medium | Medium | Build platform loyalty through tools (analytics, community features) that developers rely on. Maintain 10% commission as a permanent differentiator. Regular feature requests and community voting on roadmap. |

## Next Steps

1. Build a clickable prototype of the developer dashboard (build upload flow, analytics overview, pricing management) and test with 10 indie developers. Validate that the workflow is smoother than Steamworks.
2. Implement the core architecture: modular monolith with auth (OAuth), game CRUD, and Stripe Connect payment integration. Deploy as a private alpha to 20 developers.
3. Build the launcher client MVP with download/resume, DRM token verification, and basic library management. Test on Windows, Mac, and Linux.
4. Recruit 100 indie developers for the beta launch with the revenue guarantee offer. Target developers with upcoming games (3-6 months from release) who are already planning to self-publish or use Itch.io.
5. Research and implement the analytics pipeline: instrument the launcher to emit game session events, build the streaming pipeline (Kafka → S3 → Trino), and create the developer analytics dashboard (10 charts: sales, playtime, geography, retention, crashes, performance).
6. Set up the legal entity, tax collection (VAT, sales tax), and developer terms of service. Consult with a lawyer familiar with digital goods marketplace regulations in the US, EU, and UK.
7. Design and launch the "coming soon" landing page with email signup for players, and the developer Discord server for early community building.

---
*Brainstorm document produced by brainstorm skill. Use the librarian skill to persist this artifact.*
