# Artifact Format Reference

Every artifact managed by the librarian skill is a markdown file with YAML frontmatter, stored inside a **project**.

## Directory structure

```
projects/                                     # project scope (cwd-relative)
├── index.md                                  # all-projects index (auto)
├── .librarian/current                        # active-project pointer
└── 2026_06_10_billing-system/                # YYYY_MM_DD_<slug>
    ├── index.md                              # project index (your prose + auto contents)
    ├── researches/
    │   ├── index.md                          # research index (auto)
    │   └── 2026_06_10_authn-options.md       # YYYY_MM_DD_<slug>.md
    ├── specs/
    │   ├── index.md                          # specs index (auto)
    │   ├── technical.md                      # technical spec
    │   ├── solution.md                       # solution spec (non-technical)
    │   ├── api-design.md                     # API design
    │   └── design.md                         # visual design
    └── sprints/
        ├── index.md                          # all sprints + status (auto)
        └── sprint-1/
            ├── index.md                      # sprint index + user stories (auto)
            └── us-001/
                ├── index.md                  # story description + task statuses (auto)
                └── us-001-task-001.md        # a task file
```

- **Researches** are flat, date-prefixed files: `researches/YYYY_MM_DD_<slug>.md`.
- **Specs** are fixed-name files; the type *is* the filename: `technical.md`, `solution.md`, `api-design.md`, `design.md` (custom types allowed).
- **Sprints** nest: `sprints/sprint-N/us-XXX/us-XXX-task-XXX.md`.

## File location

- **Project scope**: `{working_dir}/projects/...`
- **Global scope**: `$AGENT_ROOT/projects/...` (or `~/.agents/projects/`)

## Frontmatter by artifact type

All artifacts share `created`/`updated` (ISO 8601) and preserve `created` across updates. Type-specific fields:

| Type | Key fields |
|------|-----------|
| project | `title`, `type: project`, `slug`, `status`, `scope` |
| research | `title`, `type: research`, `slug`, `tags`, `scope` |
| spec | `title`, `type: spec`, `spec_type` (technical/solution/api-design/design/...) |
| sprint | `title`, `type: sprint`, `name`, `status`, `goal` |
| user_story | `title`, `type: user_story`, `id` (us-XXX), `status` |
| task | `title`, `type: task`, `id` (us-XXX-task-XXX), `status` |

Example research note:

```yaml
---
title: Authentication Options
type: research
slug: authn-options
created: 2026-06-10T10:30:00Z
updated: 2026-06-10T14:22:00Z
tags: ["auth", "security"]
scope: project
---

# Authentication Options

Content goes here...
```

## Auto-maintained indexes

Index files are rebuilt by the script on every write. There are two kinds:

- **Container indexes** (`projects/index.md`, `researches/index.md`, `specs/index.md`, `sprints/index.md`) are fully generated — don't edit them.
- **Entity indexes** (project `index.md`, `sprint-N/index.md`, `us-XXX/index.md`) carry your prose *above* a marker and an auto-generated section *below* it:

```markdown
# US-001 · Checkout flow

As a user I can pay with a card.

## Acceptance Criteria
- Card accepted
- Receipt emailed

<!-- LIBRARIAN:AUTO:BEGIN — regenerated; edit above this line -->

## Tasks (2)

- [Build payment form](us-001-task-001.md) — `done`
- [Add validation](us-001-task-002.md) — `todo`

<!-- LIBRARIAN:AUTO:END -->
```

Everything above `AUTO:BEGIN` is yours and is preserved; the block between the markers is regenerated.

## Slug & id derivation

Slugs are lowercased, hyphenated, stripped of non-alphanumerics, collapsed, and truncated to 60 chars:
- "Authentication Options" → `authn-options` (`authentication-options`)
- "API Design Specification v2" → `api-design-specification-v2`

IDs normalize on input: `1`, `us-1`, `us-001` all resolve to `us-001`; sprint `2`/`sprint-2` → `sprint-2`; task `1` → `...-task-001`.

## Status vocabulary

Free-form, but stay consistent:
- sprints: `planned` → `active` → `done`
- stories & tasks: `todo` → `in-progress` → `done`, plus `blocked`

## Script commands

All commands output JSON. The script is at `scripts/librarian.py`.

| Group | Commands |
|-------|----------|
| (top) | `init`, `search <query> [--all]`, `migrate [--source DIR] [--project-slug SLUG]` |
| `project` | `create <slug>`, `list`, `use <slug>`, `show`, `current`, `status <status>` |
| `research` | `write <slug>`, `read <slug>`, `list` |
| `spec` | `write <type>`, `read <type>`, `list` |
| `sprint` | `create [--name N --goal G]`, `list`, `show <sprint>`, `status <sprint> <status>` |
| `story` | `create <sprint> <id>`, `list <sprint>`, `show <sprint> <id>`, `status <sprint> <id> <status>` |
| `task` | `write <sprint> <story> <id>`, `read ...`, `list <sprint> <story>`, `status <sprint> <story> <id> <status>` |

Common options: `--project <slug>` (override the active project), `--scope project|global`, and for writes `--title`, `--content`, `--file`, `--tags`. Content can also be piped via stdin.
