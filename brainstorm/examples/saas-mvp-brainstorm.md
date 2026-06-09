# TaskFlow — Task Management for Remote Teams

> Brainstorm | Depth: standard | Generated: 2026-06-09

## Core Idea

A lightweight, real-time task management app purpose-built for remote and hybrid teams who are overwhelmed by bloated tools like Jira and Asana. TaskFlow strips away ceremony (sprints, story points, burndown charts) and focuses on async-first task tracking with thread-based comments, optional deadlines, and team-wide visibility.

## Problem & Motivation

- **Problem**: Existing task tools are either too heavy (Jira, Asana) for small teams or too simple (plain Trello, todo lists) for structured async work. Remote teams need something in between — fast to adopt, but with enough structure to stay organized across time zones.
- **Who**: Remote-first teams of 5–50 people — startups, small agencies, open-source project maintainers, distributed engineering teams.
- **Why now**: Remote work is permanent for millions of teams. The tools that emerged during the pandemic were either rushed (buggy, missing features) or pivoted to enterprise (expensive, complex). There's a gap for a affordable, focused tool that does one thing well.

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Architecture | Monolith (Rails/Next.js) with background jobs | Ship in 8 weeks, not 8 months. Vertical slice monolith we can split later if needed. |
| Data store | PostgreSQL | Reliable, great JSON support for flexible task metadata, strong ecosystem. |
| Frontend framework | React (Next.js) with server components | Server-rendered for instant first paint, progressively enhanced with client interactivity for drag-and-drop and real-time updates. |
| Real-time updates | Server-Sent Events (SSE) via ActionCable-style channel | WebSockets are overkill for task updates. SSE is simpler to deploy, works through proxies, and handles reconnection gracefully. |
| Auth | Magic-link + OAuth (Google/GitHub) | No password management. Remote teams already have Google/GitHub accounts. |
| Pricing | Per-seat monthly ($8/user/mo) with free tier (5 users) | Simple, predictable. Free tier acts as adoption funnel. |
| Task model | Single flat list with labels, not nested hierarchies | Hierarchies (epics → stories → subtasks) overcomplicate things. Labels + filters are more flexible. |

## Dimensions Explored

### Architecture & Tech Stack

Decided on a monolithic first approach using a full-stack Next.js app with PostgreSQL. The team (2–3 engineers) needs to ship fast, and a monolith avoids the operational overhead of microservices, message queues, and separate API servers. Background jobs (email notifications, digest generation) handled by a simple job queue backed by Postgres (using Que or similar). If the app needs to scale later, the natural split is separating the real-time channel server and background worker into standalone services. The frontend uses server components for the task list view (fast initial load, SEO-friendly for public pages) and client components for the drag-and-drop board view and inline editing.

- Chose Postgres over MongoDB because task data is highly relational (users, tasks, comments, labels, assignments) and Postgres JSONB handles flexible metadata well.
- SSE over WebSockets because task updates are low-frequency (a few per minute per team) and SSE is trivially deployable without sticky sessions or a separate WS server.
- Next.js app router with server actions for mutations — keeps the data flow simple and avoids building a separate API layer initially.

### User Experience

The app centers around three views: a "List" view (default, spreadsheet-like), a "Board" view (Kanban columns), and a "Timeline" view (Gantt-like for deadlines). Every view shares the same underlying data model — switching views is a client-side filter, not a different backend query. Tasks support markdown descriptions, file attachments (drag-and-drop), threaded comments, and labels. Notifications are async: daily digests and @mentions trigger in-app notifications plus optional email. No push notifications, no Slack integration in v1 — keep scope tight.

- Async-first: the default notification is a daily digest, not real-time. Real-time updates are available for "active" tasks but opt-in.
- Keyboard shortcuts as a first-class feature — power users (engineers) expect them. Every action has a shortcut.
- Mobile web is responsive (no native app in v1). PWA support for install-to-homescreen.

### Business Model

Per-seat subscription with a free tier that caps at 5 active users and 3 projects. Paid plans unlock unlimited projects, advanced permissions, audit logs, and priority support. Annual billing discount (2 months free). No usage-based pricing — remote teams want predictable costs. The key challenge is converting free teams before they hit the 5-user limit; the viral loop is inviting teammates (each new user triggers a trial prompt for the inviter's workspace). Plan to offer a 14-day free trial on paid plans with no credit card required.

- Free tier is a funnel: 5 users, 3 projects, 7-day history retention. Enough to be genuinely useful, but with clear upgrade triggers.
- Enterprise tier ($15/user/mo) adds SSO, SAML, and dedicated onboarding for teams of 50+.
- No ads, no data selling. Revenue comes entirely from subscriptions.

### Security & Auth

Magic-link and OAuth only — no passwords to store, no password reset flows, no bcrypt hashing. Email-based magic links use a signed token with 15-minute expiry. OAuth providers are GitHub (for engineering teams) and Google (for everyone else). Row-level security (RLS) in Postgres enforces workspace isolation at the database level — every query is scoped by `workspace_id` from the authenticated session. API tokens for integrations (future) will be scoped to specific workspaces with read/write granularity. No SOC2 or HIPAA in v1, but audit logging is built from day one (who did what, when) to make certification easier later.

- RLS means a bug in the application layer can't leak data across workspaces — defense in depth.
- Session tokens (HTTP-only, SameSite=Strict) rather than JWT localStorage to minimize XSS risk.
- File uploads scanned for malware server-side (ClamAV) before serving. Uploads stored in S3-compatible storage with presigned URLs.

## Open Questions

- **Should tasks support recurring instances (e.g., "weekly standup notes") or keep it simple?** Recurring tasks add significant complexity (instance generation, editing one vs. all, skipping instances). The team leans toward keeping it out of v1 and using a simple "duplicate task" button instead. Needs user research to validate.
- **How do we handle cross-workspace collaboration when a user belongs to multiple teams?** The simplest approach is a workspace switcher in the sidebar with a unified "My Tasks" view across all workspaces. But merging notifications across workspaces is tricky — should you get one daily digest or per-workspace? Needs design exploration.
- **Should the free tier include API access?** API access is a power feature — free-tier users building integrations would create lock-in and conversion upside. But it also increases support burden. Leaning toward no API on free tier, but open to revisiting.

## Research Suggestions

Topics that need deeper investigation by the researcher skill:

- **Postgres RLS performance at scale** — Row-level security works great for 50-workspace deployments, but how does it perform at 10,000+ workspaces with complex policies? Suggested researcher query: "PostgreSQL Row-Level Security performance benchmarks for multi-tenant SaaS applications with 10k+ tenants"
- **Magic-link UX vs. passwordless trade-offs** — Magic links are convenient but add friction (check email, click link). Some users prefer passkeys or device-based auth. Suggested researcher query: "Magic link vs passkey vs OAuth-only signup UX comparison 2025/2026"

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Monolith becomes hard to maintain as team grows | Medium | High | Enforce strict module boundaries from day one. Use Packwerk (Rails) or similar to define public APIs between internal modules. Split into services only when metrics indicate pain. |
| Free tier users never convert to paid | High | Medium | Design free tier with natural upgrade triggers (history retention limit, user cap). Run conversion analytics from launch. Offer usage-based upgrade nudges (e.g., "You've created 3 projects — unlock unlimited for $8/mo"). |
| SSE connection limits under heavy load | Low | Medium | Each browser connection keeps a Postgres LISTEN/NOTIFY slot. At 10k concurrent connections this may strain Postgres. Mitigation: use a dedicated channel server (e.g., AnyCable) or migrate to WebSockets with a standalone service. |
| Async-first notification approach frustrates users who want real-time | Medium | Low | Default to daily digest but allow per-user opt-in to real-time notifications for specific tasks/projects. Survey beta users on their preference before committing to the default. |

## Next Steps

1. Build a clickable Figma prototype of all three views (List, Board, Timeline) with the async notification flow and test with 5 remote teams.
2. Set up the Next.js + Postgres monolith with SSE and deploy a bare-bones proof-of-concept that lets a team create tasks and see them update in real-time across browsers.
3. Implement RLS policies and auth flow (magic-link + OAuth) before writing any business logic — security foundation first.

---
*Brainstorm document produced by brainstorm skill. Use the librarian skill to persist this artifact.*
