# GitPulse — Git Repository Activity CLI

> Brainstorm | Depth: quick | Generated: 2026-06-09

## Core Idea

A single-binary CLI tool that scans local git repositories and outputs a rich terminal dashboard showing recent activity — commits per author, bus factor risk, stale branches, review velocity, and contribution heatmaps. Designed for engineering leads and open-source maintainers who want instant insight without opening a browser or GitHub.

## Problem & Motivation

- **Problem**: Engineering leads and maintainers waste time context-switching to GitHub/GitLab web UIs (or running ad-hoc `git log` pipelines) just to get a pulse on repo activity. There's no fast, terminal-native way to answer "who's contributing, what's stale, and are we blocked?"
- **Who**: Engineering leads, senior developers, open-source maintainers, and any developer working across multiple repos who wants a quick activity overview.
- **Why now**: AI coding assistants are accelerating commit velocity — understanding churn patterns, identifying bottlenecks, and spotting bus-factor risks is more important than ever. Developers live in the terminal; they need tools that meet them there.

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Language | Rust | Single static binary, no runtime dependency, fast even on huge repos. Cross-compiles easily. |
| Output format | Rich terminal (ratatui, not plain text) | A dashboard is more scannable than scrolling text. Plain `--json` flag for piping. |
| Data source | Local git history only (no API) | Zero setup, no tokens, works offline. Future: optional GitHub/GitLab API enrichment. |
| Subcommand structure | `gitpulse stats`, `gitpulse watch`, `gitpulse report` | Three focused commands instead of flags on flags. Keeps help output clean. |

## Dimensions Explored

### Architecture & Tech Stack

Built in Rust as a single statically-linked binary. The core is a library that parses `git log` output and the reflog to extract commit metadata. No `libgit2` binding — shell out to `git` commands and parse stdout. This is slightly slower but avoids a heavy C dependency and ensures compatibility with any git version. Terminal rendering uses `ratatui` with a `crossterm` backend. The data model is entirely in-memory — no need for persistence since each run scans the repo fresh. For large repos (Linux kernel scale), we can cache parsed results to a `.gitpulse_cache` file keyed by HEAD hash for near-instant subsequent runs.

- Shelling out to `git` rather than using `libgit2` means the tool works with whatever git version the user has, including custom git wrappers and aliases. The performance penalty is negligible — `git log --format=%H` on the Linux kernel takes ~200ms.
- JSON output (`--json`) for piping into jq or feeding into dashboards. Terminal output is for humans, JSON is for machines.
- `gitpulse watch` runs in a loop (every 5 minutes by default) and re-renders the dashboard — useful for pairing sessions or monitoring CI activity.

### User Experience

Three subcommands: `stats` (on-demand snapshot), `watch` (live-updating dashboard), and `report` (markdown summary for sharing). The default `stats` view shows: top 5 contributors (commits/insertions/deletions), stale branches (no commit in 30 days), recent activity heatmap (last 7 days), and a bus-factor indicator (what % of recent commits are from a single author). Color-coded: green for healthy, yellow for warning, red for attention. The `report` command generates a markdown snippet you can paste into a PR or team chat.

- Bus-factor calculation: if a single author accounts for >50% of commits in the last 90 days, show a red warning with the author's name. This is a heuristic, not precise, but actionable.
- Stale branch detection: branches not merged or committed to in 30+ days. Color-coded by age. Optionally filter by "not touched in X days" via `--stale-days`.
- The `watch` mode uses a terminal dashboard with auto-refresh. It dims inactive panels and highlights changes since last refresh — a subtle animation draws the eye to new commits.

## Open Questions

- **Should we support monorepo mode (scan subdirectories as separate "projects")?** Monorepos are increasingly common. The `stats` command could accept a `--monorepo` flag that scans each top-level directory with a `Cargo.toml`/`package.json` as an independent project. But this adds complexity to the output layout. Leaning toward: monorepo support in v1.1, not v1.0.
- **How do we handle very large repos with 10k+ commits?** Initial scan on a repo like Linux could take 10+ seconds. Caching helps on subsequent runs, but the first run UX matters. Should we show a progress spinner with estimated branches scanned? Or restrict the scan to the last N commits by default (e.g., `--since=90.days`)?

## Research Suggestions

Topics that need deeper investigation by the researcher skill:

- **Bus-factor algorithms for git repositories** — Our simple heuristic (single author >50%) is too crude. There are academic and industry approaches to measuring bus factor that consider file-level ownership, contribution recency, and code review participation. Suggested researcher query: "Bus factor calculation algorithms for git repositories — file-level ownership and contribution diversity metrics"

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Shelling out to `git` breaks with unusual git configurations or unusual output formats | Low | Medium | Test against multiple git versions (2.30–2.50) and common configs (custom `log.date`, `i18n.commitEncoding`). Use `--no-color`, `--no-replace-objects`, `-c core.abbrev=40` to normalize output. |
| Ratatui terminal dashboard is inaccessible for CI/headless environments | Medium | Low | `stats` and `report` commands work without TUI. Only `watch` requires a terminal. CI users can use `stats --json` or `report --format=markdown`. |

## Next Steps

1. Write the core git log parser in Rust — parse `git log --format=...` output into structured commit data (sha, author, date, files changed, insertions/deletions). Test against open-source repos of varying sizes.
2. Build the `stats` command output with ratatui — focus on the top-contributors, stale-branches, and bus-factor panels. Ship a working prototype this week.
3. Publish a pre-built binary for macOS (arm64 + x64) and Linux (x64) via GitHub Releases — no npm/cargo install needed, just `curl` and `chmod +x`.

---
*Brainstorm document produced by brainstorm skill. Use the librarian skill to persist this artifact.*
