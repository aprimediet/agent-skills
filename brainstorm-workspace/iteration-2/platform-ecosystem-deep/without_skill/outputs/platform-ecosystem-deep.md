# IndieVerse — Brainstorm Document

> **Idea**: An indie-friendly alternative to Steam where independent game developers can publish games, handle payments, manage DRM, collect analytics, and distribute updates.
> **Platform Targets**: Windows, macOS, Linux, Android, iOS
> **Depth**: Thorough exploration
> **Date**: 2026-06-09

---

## Table of Contents

1. [Vision & Core Identity](#1-vision--core-identity)
2. [User Personas](#2-user-personas)
3. [Feature Inventory](#3-feature-inventory)
4. [System Architecture (High-Level)](#4-system-architecture-high-level)
5. [Platform-Specific Considerations](#5-platform-specific-considerations)
6. [Business Model](#6-business-model)
7. Revenue Model Deep-Dive
8. [Competitive Landscape](#7-competitive-landscape)
9. [Risks & Challenges](#8-risks--challenges)
10. [Go-To-Market Strategy](#9-go-to-market-strategy)
11. [Feature Prioritization (Phased Roadmap)](#10-feature-prioritization-phased-roadmap)
12. [Open Questions](#11-open-questions)
13. [Appendix: Technical Spikes Needed](#12-appendix-technical-spikes-needed)

---

## 1. Vision & Core Identity

### One-Sentence Pitch
*"The publishing platform Steam *would* be if it were built today exclusively for indies — fair revenue share, modern tooling, and genuine developer-friendliness."*

### Core Beliefs
- **Indie-first** not indie-friendly-as-an-afterthought. Every design decision starts with the solo dev or small team.
- **Fairness** is a feature. A 10-15% revenue split (vs Steam's 30% and even the 25/20 tiers) is table stakes. Transparent, simple terms.
- **Developer autonomy** over the storefront — custom pages, direct community access, no opaque algorithms burying you.
- **Quality over quantity** — curated but not gatekept; think "we help good games find players" not "we host everything."

### Key Differentiators from Steam
| Area | Steam | IndieVerse |
|------|-------|------------|
| Revenue split | 30/25/20% (tiered) | 10% flat, no tiers |
| Store visibility | Algorithm-driven, paid ads for visibility | Curated collections, dev-controlled storefronts, discovery through quality signals |
| DRM | Steamworks (optional but encouraged) | Optional, modular — choose your own or none |
| Analytics | Basic Steamworks stats | Rich funnel analytics, crash reporting, playtest metrics |
| Publishing fee | $100 per app (recoupable) | $0 upfront, revenue-share only |
| Payment options |地域限定的 | Global: cards, PayPal, crypto, regional wallets |
| Updates | SteamPipe (proprietary) | Multi-channel: Steam-like patching + delta updates + optional itch-style direct downloads |
| Mobile support | None (Steam Deck is handheld PC, not mobile) | Android/iOS store listings + cross-platform cloud saves |

---

## 2. User Personas

### Developer Personas

**Persona A: Solana — Solo Dev**
- Age: 28, full-time indie, 2 years shipping small games
- Pain: Steam's $100/app fee + 30% cut eats into thin margins; store algorithm buries her niche games
- Needs: Simple upload, fair cut, direct connection to players, minimal paperwork
- Quote: *"I don't want to think about pipelines, I want to publish and get back to coding."*

**Persona B: Tiny Studio — 3-person team**
- Working on their sophomore title after a modest hit
- Pain: Managing beta branches, playtesting, analytics across Steam + itch.io is fragmented
- Needs: Unified dashboard, playtest gating, crash reporting, update rollback
- Quote: *"We need pro tools without enterprise pricing."*

**Persona C: Porting House**
- Takes indie games to consoles and mobile
- Pain: No single platform handles Win/Mac/Linux *and* mobile store listings
- Needs: Cross-platform build pipeline, mobile-ready SDK, unified analytics across all stores
- Quote: *"If I can push to desktop and mobile from one place, I'm sold."*

### Gamer Personas

**Persona D: Indie Enthusiast**
- Follows 50+ indie devs on Twitter, buys 2-3 games/month
- Pain: Steam's discovery surface is flooded; hard to find hidden gems
- Needs: Curated discovery, direct dev interaction, bundle deals, DRM-free options
- Quote: *"I want to support devs directly and feel like I'm part of a community, not a transaction."*

**Persona E: Budget Gamer**
- Limited spend, values discounts and regional pricing
- Pain: Many platforms don't support their local currency or payment method
- Needs: Regional pricing, wishlist price-drop alerts, demos, fair refunds
- Quote: *"I want to discover great games I can actually afford."*

---

## 3. Feature Inventory

Grouped by domain. Features marked **[MVP]** are essential for launch.

### 3.1 Developer Dashboard

| Feature | Description | Priority |
|---------|-------------|----------|
| Game submission wizard | Form to submit title, description, assets, tags, pricing | **[MVP]** |
| Build uploader | CLI tool + web upload for builds; versioned, with release channels | **[MVP]** |
| Store page editor | Rich editor with preview; custom CSS/theming? | **[MVP]** |
| Analytics dashboard | Sales, downloads, wishlists, refunds, playtime, geographic data | **[MVP]** |
| Payouts & tax center | Stripe Connect-style onboarding, 1099/W-8BEN handling | **[MVP]** |
| DRM settings | Per-build toggle: none, Steam-like (DLL check), key-based, third-party | **[MVP]** |
| Update manager | Set update channels (stable/beta/dev), write patch notes, schedule rollouts | **[MVP]** |
| Review management | Reply to user reviews, flag abusive, see aggregated sentiment | Phase 2 |
| A/B testing tools | Test store page variants (capsule art, description, price) | Phase 2 |
| Community hub | Built-in forums, devlog posts, announcement system | Phase 2 |
| Playtest gating | Distribute keys / grant access to playtesters, collect feedback | Phase 2 |
| Localization management | Upload locale files, crowd-sourced translation workflow | Phase 2 |
| Marketing tools | Discount/sale scheduler, bundle builder, press key generator | Phase 2 |

### 3.2 Storefront (Gamer-Facing)

| Feature | Description | Priority |
|---------|-------------|----------|
| Game listing page | Screenshots, trailers, descriptions, system requirements, reviews | **[MVP]** |
| Search & discovery | Filters (tags, price range, OS, controller support), sorting | **[MVP]** |
| Curated collections | Hand-picked lists by platform team ("Staff Picks," genre spotlights) | **[MVP]** |
| User library | Purchased games list, download manager, update notifications | **[MVP]** |
| Shopping cart & checkout | Multi-game purchase, guest checkout, gift purchases | **[MVP]** |
| Wishlist | Save games for later, price-drop alerts | **[MVP]** |
| User reviews | Star rating + written review; "helpful" voting | **[MVP]** |
| Bundles & sales | Developer-configured bundles (e.g., "buy both games save 20%") | Phase 2 |
| DLC & season passes | Purchase additional content per game | Phase 2 |
| Friend activity | See what friends are playing, game feeds | Phase 2 |
| Game forums / discussions | Per-game community boards | Phase 2 |
| Workshop / mod support | User-generated content hosting and distribution | Phase 3 |

### 3.3 Client / Launcher

| Feature | Description | Priority |
|---------|-------------|----------|
| Lightweight launcher | Download, install, update, launch games | **[MVP]** |
| Offline mode | Play purchased games without internet | **[MVP]** |
| Cloud saves | Automatic sync of save data per game | **[MVP]** |
| Auto-updating | Background updates with delta patching | **[MVP]** |
| DRM runtime | Optional DRM enforcer if dev chooses DRM | **[MVP]** |
| Social overlay | In-game overlay for friends, screenshots, recording | Phase 2 |
| Controller configuration | Mapping profiles per game | Phase 2 |
| Accessibility settings | UI scaling, high-contrast, screen reader support | Phase 2 |
| Linux/macOS native clients | First-class support, not wrappers | Phase 2 |

### 3.4 Backend & Infrastructure

| Feature | Description | Priority |
|---------|-------------|----------|
| User accounts | Email/password, OAuth (Google, GitHub, Discord), 2FA | **[MVP]** |
| Payment processing | Stripe, PayPal, regional processors (Pix, Alipay, iDEAL) | **[MVP]** |
| Order fulfillment | License key generation, entitlement management | **[MVP]** |
| CDN for builds | Global edge distribution for game downloads | **[MVP]** |
| Update system | Binary diff patching (bsdiff/hdiff), incremental updates | **[MVP]** |
| Analytics pipeline | Event ingestion, aggregation, dashboard queries | **[MVP]** |
| Anti-piracy / DRM | Optional token-based validation, no invasive rootkit DRM | **[MVP]** |
| Refund system | Automated refunds within window (e.g., 14 days / <2h playtime) | **[MVP]** |
| Review moderation | Abuse detection, spam filtering, dev response system | **[MVP]** |

---

## 4. System Architecture (High-Level)

```
┌─────────────────────────────────────────────────────┐
│                    CDN Layer                         │
│  (CloudFront / Fastly / BunnyCDN — build files,     │
│   screenshots, videos, patches)                     │
└───────────┬───────────────────────────┬─────────────┘
            │                           │
┌───────────▼───────────┐   ┌───────────▼─────────────┐
│   API Gateway / LB     │   │   Web App (Next.js)     │
│   (AWS API Gateway /   │   │   Storefront + Dash     │
│    Cloudflare / Nginx) │   └─────────────────────────┘
└───────────┬───────────┘
            │
┌───────────▼─────────────────────────────────────────┐
│              Service Mesh (Kubernetes / Nomad)       │
│                                                      │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐  │
│  │ Auth    │ │ Payment  │ │ Fulfill- │ │ Store  │  │
│  │ Service │ │ Service  │ │ ment Svc │ │ Search │  │
│  └─────────┘ └──────────┘ └──────────┘ └────────┘  │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐  │
│  │ Update  │ │ Analytic │ │ DRM      │ │Review  │  │
│  │ Service │ │ Service  │ │ Service  │ │Service │  │
│  └─────────┘ └──────────┘ └──────────┘ └────────┘  │
│  ┌─────────┐ ┌──────────┐                           │
│  │ Notif.  │ │ Social   │                           │
│  │ Service │ │ Service  │                           │
│  └─────────┘ └──────────┘                           │
└─────────────────────────────────────────────────────┘
            │
┌───────────▼─────────────────────────────────────────┐
│              Data Layer                              │
│  ┌──────────┐ ┌───────────┐ ┌──────────────────┐   │
│  │ Postgres │ │ Redis     │ │ S3 / Object Store │   │
│  │ (primary)│ │ (cache,   │ │ (build artifacts, │   │
│  │          │ │  sessions)│ │  screenshots)     │   │
│  └──────────┘ └───────────┘ └──────────────────┘   │
│  ┌──────────┐ ┌───────────┐                         │
│  │ ClickHouse││ RabbitMQ /│                         │
│  │(analytics)││ Kafka     │                         │
│  └──────────┘ └───────────┘                         │
└─────────────────────────────────────────────────────┘
```

### Architecture Notes

- **Services should be independently deployable** — a spike in analytics traffic shouldn't affect payment processing.
- **Update service is the most novel piece.** Binary diff patching (bsdiff/xdelta) with chunk-level deduplication. This is a build-vs-buy decision early on. Existing solutions: Microsoft's MSIX, Google's Courgette (used in Chrome), or custom with zchunk + bsdiff.
- **DRM should be an optional add-on layer**, not core infrastructure. Think of it as a checkbox that adds token validation on launch. No invasive kernel-level drivers. If developers want stronger DRM, they can integrate third-party (Denuvo, VMProtect) at their own cost.
- **Analytics pipeline**: Event ingestion -> Kafka -> ClickHouse. Pre-aggregated dashboards for developers. Raw event access via SQL for power users (with privacy filtering).
- **CDN costs will be significant** for large game downloads. Negotiate volume pricing early, or build on top of BunnyCDN (more indie-friendly pricing). Offer developers the option to self-host builds (link out to their own servers) to reduce platform costs.

---

## 5. Platform-Specific Considerations

### Windows
- **Primary target** — most indie games ship here first
- Launcher: Electron + native C++ bootstrap for auto-update reliability
- DRM: Simple DLL check or Steam-style app_ticket validation
- Installer: MSIX or custom installer; support for both per-user and per-machine installs
- Store integration: Xbox Game Pass? (long-term partnership play)

### macOS
- **Notarization & signing**: Apple's Gatekeeper requirements mean every build needs to be signed with an Apple Developer cert. This is a dev-pain-point we could solve with a centralized signing service (devs upload build, we sign with a platform cert and distribute).
- **Universal binary support**: Intel + Apple Silicon
- Sandboxing considerations for DRM and overlay
- Launcher: SwiftUI native or Electron? Electron is easier to maintain cross-platform but Apple's recent restrictions on notarized Electron apps cause friction. Native SwiftUI launcher is a better long-term bet.

### Linux
- **Fragmentation is the enemy**: Target Steam Flatpak runtime (Steam Linux Runtime — Soldier/Sniper) for compatibility. Also support native AppImage/Flakpak builds.
- **No DRM expectation from the Linux audience** — many Linux gamers prefer DRM-free. Make this easy, make it transparent.
- Launcher: GTK or Electron? Given the small audience, Electron may win for shared codebase, but a lightweight GTK shell launcher that invokes the web-based store would be more "native."

### Android
- **Cross-store challenge**: If we distribute APKs directly, we compete with Google Play. If we list on Google Play as a "powered by IndieVerse" app, we're in their ecosystem.
- **Approach**: Offer a separate Android launcher app that manages IndieVerse-purchased games. Games install via APK expansion files or Play Asset Delivery.
- Alternatively, act as a listing and payment layer *on top of* existing stores — devs publish to Play Store and Apple App Store, but IndieVerse handles cross-platform analytics, DRM, and community.
- **Revenue share**: Google Play takes 15-30% on top — this complicates the 10% model. Need to decide: pass-through or eat the cost.

### iOS
- **Sideloading is limited** (as of 2026, EU DMA is forcing change, but US market remains App Store-only). This makes iOS the hardest target.
- **Approach 1**: Web-based distribution via PWA for iOS. Limited, no DRM enforcement.
- **Approach 2**: Use Apple's App Store with IndieVerse as a middleman — devs publish on App Store, IndieVerse provides community/analytics overlay.
- **Approach 3**: Wait for sideloading regulation to expand globally. In the meantime, focus on desktop + Android.
- **Recommendation**: De-prioritize iOS for MVP. Start with Windows + macOS + Linux, add Android in Phase 2, iOS in Phase 3 (or when regulatory landscape shifts).

---

## 6. Business Model

### Revenue Streams

| Stream | % of Revenue (Projected) | Details |
|--------|--------------------------|---------|
| Commission on sales | 70% | 10% flat on all transactions |
| Subscription (Dev Pro) | 15% | $15/mo — advanced analytics, A/B testing, priority support, custom store CSS, early access to features |
| Featured placements | 10% | Developer-purchased featured slots in curated sections ("Indie Spotlight") — clearly labeled as sponsored |
| White-label / API | 5% | Allow other storefronts to use IndieVerse's backend (payments, fulfillment, updates) under their own branding |

### Cost Structure

| Cost Center | % of Revenue | Notes |
|-------------|-------------|-------|
| Payment processing fees | ~3-4% | Stripe/PayPal take 2.9% + $0.30; pass-through to dev or absorb? |
| CDN & bandwidth | ~15-20% | Largest cost — game builds are big. Needs aggressive optimization (delta updates, P2P seeding?) |
| Cloud infrastructure | ~10-15% | Compute, databases, caching |
| Salaries & operations | ~30-40% | Engineering, support, curation, moderation |
| Payment / fraud losses | ~2% | Refunds, chargebacks |
| **Margin** | **~10-20%** | Tight — need volume to be viable |

### Key Economic Insight
> **This business is a volume game.** At 10% commission, with 15-20% going to CDN costs alone, we need significant transaction volume to be profitable. The win condition is: *thousands of games × thousands of sales each × low margin = sustainable business.* This only works if we keep infrastructure costs ruthlessly optimized.

---

## 7. Revenue Model Deep-Dive

### Why 10%?
- Industry precedent: Epic Game Store (12%), Itch.io (10%, or 0% at dev's choice), Humble Widget (5-15%). 10% is the sweet spot that says "we're on your side" without being unsustainable.
- Trade-off: lower margin per transaction forces us to earn through volume and value-add services (Dev Pro, placements), not pure transaction fees.

### Payout Model

| Transaction Volume | Payout Frequency | Payout Fee |
|-------------------|-----------------|------------|
| < $100/month | Manual request | Deducted from balance |
| $100–$1,000/month | Monthly automatic | Free |
| $1,000+ /month | Bi-weekly automatic | Free |
| $10,000+ /month | Weekly automatic | Free |

### Tax Handling
- Integrated tax collection during checkout (VAT for EU, GST for AU/NZ, sales tax for US states)
- Automated W-8BEN/W-9 collection via tax form service (e.g., TaxJar, Stripe Tax)
- Annual tax report generation for developers

### Refund Policy
- Mandatory: 14 days / 2 hours of playtime (matching Steam)
- Optional: Developers can offer more generous terms
- Refund costs split: platform refunds from its commission; dev keeps their share? Or full chargeback to dev?
- *Recommended*: Platform takes the hit on the commission portion (10%); dev returns the 90%. This aligns incentives — platform only makes money when sales stick.

---

## 8. Competitive Landscape

### Direct Competitors

| Platform | Revenue Share | DRM | Analytics | Updates | Mobile | Notes |
|----------|--------------|-----|-----------|---------|--------|-------|
| **Steam** | 30/25/20% | Steamworks (optional) | Basic | SteamPipe | No | The 800-lb gorilla. Network effects are enormous. |
| **Epic Games Store** | 12% | Optional | Limited | Basic | No | Exclusivity deals drive adoption but hurt developer trust. Smaller userbase. |
| **itch.io** | 10% (or 0%) | None | None | Direct download only | No | The "anti-platform." No DRM, no analytics, no update system. Loves by purists, too bare-bones for commercial releases. |
| **GOG** | 30% | DRM-free as policy | Limited | GOG Galaxy | No | Curated, DRM-free focus. Strong for older/classic games, harder for new indies to break in. |
| **Game Jolt** | 50/50 rev share | None | Basic | Direct download | Yes (web) | More social network than store. Low commercial viability for most devs. |
| **Humble Store** | 25% (75% to dev after Humble cut) | None | None | Keys only | No | Acts as a key reseller for Steam — depends on Steam ecosystem. |

### Indirect Competitors / Adjacent

| Product | Relevance | Threat Level |
|---------|-----------|-------------|
| **Patreon / Kickstarter** | Devs use these for funding; not a store | Low — complementary |
| **Discord Store** (discontinued) | Shut down — but shows how hard this market is | Informational |
| **Itch.io App** (their new desktop app) | Finally getting a launcher; still no DRM/analytics | Medium — could evolve |
| **Microsoft Store / Xbox** | PC Game Pass is growing; could absorb indie distribution | Medium — partnership possibility |
| **Steam Deck / Proton** | Makes Linux gaming viable; Steam's lead widens | High — mitigates competitor advantage |

### Competitive Insight
> The market gap is not *storefront* — it's *tooling*. Steam has the storefront and users. What indies lack is a unified, modern publishing toolchain that doesn't take 30%. IndieVerse competes on **developer experience** first, storefront second.

---

## 9. Risks & Challenges

### Technical Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| CDN costs explode with game size growth | High | Medium | P2P seeding (BitTorrent-style), delta patching, developer self-hosting option |
| DRM is cracked immediately, damaging reputation | Medium | High | Don't position DRM as "unbreakable" — be honest it's a deterrent. Offer a range of options. |
| Cross-platform client maintenance burden | High | High | Focus on Electron for speed-to-market; invest in native clients only when PMF is confirmed |
| Analytics pipeline can't scale | High | Low-Medium | Use ClickHouse + Kafka from day one; design for sharding |
| Payment fraud / chargebacks | Medium | Medium | AI fraud detection (Stripe Radar + custom rules); hold payouts for first 30 days |

### Business Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Can't attract enough developers (cold start problem) | Critical | High | Seed with curated, high-quality games via targeted outreach. Partner with game jams (Ludum Dare, GMTK). Offer migration tools from Steam. |
| Can't attract enough gamers (network effects work against us) | Critical | High | Invest in curation quality over quantity. Build community features that lock in gamers (forums, reviews, friend activity). |
| Steam matches our revenue split | High | Medium-Low | Steam's infrastructure costs make 10% unlikely. If they do, compete on developer experience and curation quality. |
| Regulatory issues (EU Digital Markets Act, data privacy) | Medium | Medium | GDPR compliance from day one. DMA compliance as EU regulations evolve. |
| Indie games are a hit-driven business — majority don't sell | Medium | High | Embrace this — don't charge upfront fees. Platform revenue comes from the hits that do sell. |

---

## 10. Go-To-Market Strategy

### Phase 0: Community Building (3 months before beta)
- Start a dev blog / newsletter focused on indie publishing tips (not just platform promotion)
- Build a Discord community for indie devs — be genuinely useful
- Partner with existing indie-friendly events (Ludum Dare, Steam Game Festival alternatives, IndieCade)
- "Steam migration guide" content — how to use IndieVerse alongside Steam

### Phase 1: Closed Beta (invite-only, 50 devs)
- Curated selection of known indie devs with existing audiences
- Free tier (no commission during beta) + active feedback loops
- Focus on core publishing flow: upload, set price, publish, sell
- Gamers: free keys to beta testers' communities to build initial userbase

### Phase 2: Open Beta (public registration)
- Open to all devs, 5% commission for first 6 months (introductory rate)
- Launch storefront with ~200-500 games
- Gamer-facing marketing: "Discover the next generation of indie games"
- Key messaging: **"10% or less — forever."** Build trust through transparent pricing.

### Phase 3: Full Launch
- 10% standard commission; Dev Pro subscription launched
- Mobile support (Android first)
- API / white-label program
- Marketing push at major game conferences (GDC, Gamescom)

---

## 11. Feature Prioritization (Phased Roadmap)

**Year 1 — MVP (Focus: Core Publishing Loop)**

| Quarter | Focus | Key Deliverables |
|---------|-------|-----------------|
| Q1 | Foundation | Auth service, user accounts, dev onboarding, game submission, basic storefront (listing page + search) |
| Q2 | Purchasing | Payment integration, checkout flow, order fulfillment, license key generation, refund system |
| Q3 | Client & Updates | Lightweight desktop launcher (Win/Mac/Linux), auto-updating with delta patches, cloud saves |
| Q4 | Analytics & Polish | Developer analytics dashboard, basic store curation, launch with 50+ games |

**Year 2 — Growth (Focus: Community & Retention)**

| Quarter | Focus | Key Deliverables |
|---------|-------|-----------------|
| Q1 | Community | Dev blogs, user reviews with reply system, game forums |
| Q2 | Advanced Tools | A/B testing, playtest gating, marketing tools (discounts, bundles, press keys) |
| Q3 | Mobile | Android launcher, Android store listings, cross-platform cloud saves |
| Q4 | Scale | Performance optimization, CDN cost reduction, localization/i18n support |

**Year 3 — Expansion (Focus: Ecosystem)**

| Quarter | Focus | Key Deliverables |
|---------|-------|-----------------|
| Q1 | Platform | Dev Pro subscription, advanced analytics (funnel, cohort), SDK for custom integrations |
| Q2 | Ecosystem | Workshop/mod support, white-label API, third-party integrations |
| Q3 | iOS | iOS support (subject to regulatory landscape), PWA storefront |
| Q4 | Sustainability | Cost optimization, partnership program, potential Series A/B fundraising |

---

## 12. Open Questions

These need investigation before committing to the architecture.

### Product Strategy
1. **Do we build a launcher at all, or go web-only + itch.io-style direct downloads?** Launcher builds lock-in but is expensive to maintain. Web-only is faster to market but reduces update/DRM capabilities.
2. **Should we support existing store integrations (e.g., sell on IndieVerse but fulfill via Steam keys)?** This could bootstrap our game library overnight but makes us a key reseller rather than a platform.
3. **How do we handle game keys sold on third-party resellers (Fanatical, Humble)?** Do we generate keys to be sold elsewhere, or keep purchases exclusive to our storefront?

### Technical
4. **Build our own update/patching system or integrate existing?** Options: google/omaha (used by Chrome), The Update Framework (TUF), or commercial (Humble Bundle's Brimstone?)
5. **What's the right CDN strategy?** Single provider vs multi-CDN? Do we build P2P seeding into the launcher to reduce bandwidth costs?
6. **How do we handle Linux compatibility?** Target Steam Runtime containers? Flatpak? AppImage? Support all three?

### Business
7. **What's the minimum viable game library size for launch?** 50 games? 200? 500? How do we seed this before we have critical mass?
8. **Do we charge developers for CDN bandwidth above a threshold?** This could discourage large games but also prevent cost explosion.
9. **Should we offer a "pay what you want" model like itch.io?** It's popular with indie fans but introduces complexity for refunds, analytics, and revenue recognition.

### Legal & Regulatory
10. **How do we handle age-restricted content?** Indie games often push boundaries. A clear content policy is needed from day one.
11. **EU Digital Services Act compliance** — transparency reporting, illegal content moderation, user data access. This is non-trivial.

---

## 13. Appendix: Technical Spikes Needed

Before committing to the architecture, the following should be prototyped:

| Spike | Duration | Goal |
|-------|----------|------|
| Binary delta patching (bsdiff vs zchunk vs Courgette) | 2 weeks | Measure patch sizes and generation time for a 2GB game build |
| DRM token validation performance | 1 week | Measure startup time impact; ensure it's under 100ms |
| CDN cost projection for 100MB / 1GB / 10GB games at 10k/100k downloads | 1 week | Build a pricing model to validate the business |
| ClickHouse analytics pipeline with sample game events | 2 weeks | Verify query performance at simulated scale (1M events/hour) |
| Electron vs Tauri vs native launcher POC | 2 weeks | Compare bundle size, memory usage, update mechanism, and dev velocity |
| Cross-platform build pipeline (GitHub Actions + matrix builds) | 1 week | Validate that we can auto-build for Win/Mac/Linux from a single repo |
| Stripe Connect multi-party payments | 2 weeks | End-to-end: buyer pays -> platform takes 10% -> dev gets 90% automatically |

---

## Summary

IndieVerse aims to fill the gap between Steam's market dominance and its indifference to indie developers. The bet is that **developer experience + fair economics + curation quality** can win over a meaningful slice of the indie ecosystem, even without Steam's network effects.

The biggest challenges are:
1. **The cold start problem** — games need players, players need games
2. **Infrastructure costs** — game distribution is expensive; margins will be thin
3. **Steam's inertia** — developers and gamers are deeply embedded

But the opportunity is real: indie games are a growing market, and there's genuine developer frustration with the status quo. A platform that truly serves indies — not just accommodates them — has a real shot.
