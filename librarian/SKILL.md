---
name: librarian
description: >
  Project-first knowledge management skill for organizing, searching, reading,
  and writing agent-produced artifacts as markdown files. Every artifact lives
  inside a project (YYYY_MM_DD_slug): researches (date-prefixed notes), specs
  (technical.md, solution.md, api-design.md, design.md), and sprints containing
  user stories containing tasks — each level with an auto-maintained index.md.
  Operates on an "active project" pointer set once, with a Python script for all
  file operations, full-text search, and migration from older flat layouts. Use
  this skill whenever you need to save, find, read, organize, or manage any agent
  output — research reports, specifications, sprint/user-story/task tracking,
  decision logs, or any markdown knowledge artifact. Triggers on "save this
  research", "start a new project", "find my notes on X", "write the technical
  spec", "create a sprint", "add a user story", "track this task", "where did I
  put X", "list all specs", "search docs for X", or any request involving
  reading, writing, or managing persisted agent knowledge.
metadata:
  author: aprimediet <aprimediet@gmail.com>
  version: "3.0"
---

# Librarian

You are a knowledge management system for agent artifacts. Everything is organized **inside a project** — a project bundles the research, specifications, and sprint/user-story/task tracking that belong to one body of work.

## Directory structure

```
./projects/                                   # project scope (cwd-relative)
├── index.md                                  # all-projects index (auto)
├── .librarian/current                        # active-project pointer
└── YYYY_MM_DD_<slug>/                         # one directory per project
    ├── index.md                              # project index (auto contents + your description)
    ├── researches/
    │   ├── index.md                          # research index (auto)
    │   └── YYYY_MM_DD_<slug>.md              # a research note
    ├── specs/
    │   ├── index.md                          # specs index (auto)
    │   ├── technical.md                      # technical spec
    │   ├── solution.md                       # solution spec (non-technical)
    │   ├── api-design.md                     # API design
    │   └── design.md                         # visual design
    └── sprints/
        ├── index.md                          # all sprints + status (auto)
        └── sprint-1/                         # sprint-1, sprint-2, ...
            ├── index.md                      # sprint index + user stories (auto)
            └── us-001/                        # user story directory
                ├── index.md                  # story description + task statuses (auto)
                └── us-001-task-001.md        # a task file
```

For global (cross-project) knowledge, pass `--scope global` — the root becomes `$AGENT_ROOT/projects/` (or `~/.agents/projects/`). Default to project scope; only go global when the user says "save this globally" or "this applies to all projects."

Each artifact is markdown with YAML frontmatter. See [references/ARTIFACT_FORMAT.md](references/ARTIFACT_FORMAT.md) for the full format. **Index files are auto-maintained** — the script rebuilds them on every write. For project/sprint/user-story indexes, your prose (description, goal, acceptance criteria) lives *above* the `LIBRARIAN:AUTO:BEGIN` marker and is preserved; only the auto block below it is regenerated.

## The active project

Almost everything happens inside a project, so the script tracks an **active project** in `.librarian/current`. Set it once and subsequent commands target it automatically. Override any command with `--project <slug>`.

This is why **the first thing to resolve on any save/read request is: which project?** Don't guess silently.

### Resolving the project (ask or suggest)

1. Run `project list` to see what already exists, and `project current` to see what's active.
2. **If the user named a project** (or there's an obvious active one that matches), use it.
3. **If a sensible existing project matches the request**, propose it: *"This looks like it belongs to the `billing-system` project — save it there?"*
4. **If nothing fits**, suggest a new project name derived from the user's prompt and confirm before creating: *"I'll start a new project `payment-gateway` for this — sound right, or do you have a name in mind?"*

The point is to never scatter artifacts into the wrong place or invent a project the user didn't want. A short confirmation is cheap; a misfiled spec is expensive to find later.

## Workflow

### First-time setup

```bash
python scripts/librarian.py init                    # creates ./projects/ and the index
```

### Starting / switching projects

```bash
# Create a project (becomes active automatically). Date prefix is added for you.
python scripts/librarian.py project create "Billing System" \
  --description "Recurring billing & checkout platform"

python scripts/librarian.py project list            # all projects, ⭐ marks active
python scripts/librarian.py project use billing-system   # switch active project
python scripts/librarian.py project current         # what's active right now
python scripts/librarian.py project status billing-system on-hold
```

You can refer to a project by its short slug (`billing-system`) or full directory name (`2026_06_10_billing-system`).

### Saving research

```bash
python scripts/librarian.py research write authn-options \
  --title "Authentication Options" \
  --content "# Findings..." \
  --tags "auth,security"

# or pipe / read from a file
echo "# Findings" | python scripts/librarian.py research write authn-options
python scripts/librarian.py research write authn-options --file /tmp/draft.md
```

Research notes are stored as `researches/YYYY_MM_DD_<slug>.md`. Writing the same slug again updates the existing note and preserves its `created` date.

### Saving specs

Specs are fixed-name files inside the project's `specs/`. The `type` argument *is* the filename:

```bash
python scripts/librarian.py spec write technical   --file /tmp/tech.md
python scripts/librarian.py spec write solution    --content "# Solution spec"
python scripts/librarian.py spec write api-design  --file /tmp/api.md
python scripts/librarian.py spec write design      --content "# Visual design"
```

`technical` and `solution` are where the `technical-architect` and `solution-architect` skills save their output. Custom types are allowed (e.g. `spec write data-model ...`) — they just become `data-model.md`.

### Sprints, user stories, tasks

```bash
# Sprint (auto-numbered if --name omitted)
python scripts/librarian.py sprint create --goal "MVP checkout"
python scripts/librarian.py sprint create --name 2 --goal "Refunds"
python scripts/librarian.py sprint list
python scripts/librarian.py sprint status 1 active

# User story under a sprint (id normalizes: 1 -> us-001)
python scripts/librarian.py story create 1 1 \
  --title "Checkout flow" --description "As a user I can pay with a card"
python scripts/librarian.py story list 1
python scripts/librarian.py story status 1 1 in-progress

# Task under a user story (sprint, story, task ids)
python scripts/librarian.py task write 1 1 1 \
  --title "Build payment form" --content "Implement Stripe element" --status in-progress
python scripts/librarian.py task list 1 1
python scripts/librarian.py task status 1 1 1 done
```

Tasks are stored as `sprints/sprint-N/us-XXX/us-XXX-task-XXX.md`. Status changes propagate up: the user-story index lists its tasks with status, the sprint index lists its stories, and the project index lists its sprints — all rebuilt automatically.

Suggested status vocabulary (free-form, but stay consistent): sprints `planned` → `active` → `done`; stories & tasks `todo` → `in-progress` → `done`, plus `blocked` when stuck.

### Finding and reading

```bash
python scripts/librarian.py search "stripe webhook"        # within the active project
python scripts/librarian.py search "stripe webhook" --all  # across all projects

python scripts/librarian.py research read authn-options
python scripts/librarian.py spec read technical
python scripts/librarian.py sprint show 1
python scripts/librarian.py story show 1 1
python scripts/librarian.py task read 1 1 1
python scripts/librarian.py project show
```

### Migrating an older flat layout

If a project predates this structure (old top-level `docs/researches`, `docs/specs`, `docs/tasks`), fold it into a project:

```bash
python scripts/librarian.py migrate --project-slug legacy
# or point at a specific source
python scripts/librarian.py migrate --source ./docs --project-slug legacy
```

Researches and specs move into the new project; tasks/docs are preserved as research notes so nothing is lost. Review the reported `moved` map afterward.

## Important guidelines

- **Resolve the project first.** Every save/read targets a project. Ask or suggest (see above) rather than guessing — and set it active so later commands are terse.
- **Always use the script** for file operations. It manages frontmatter, the nested directory structure, and every index. Don't hand-edit index files below the `AUTO:BEGIN` marker; that region is regenerated.
- **You *may* hand-edit prose above the auto marker** in project/sprint/user-story indexes — descriptions, goals, acceptance criteria. The script preserves it.
- **Slugs are auto-generated** from titles (lowercase, hyphens, ≤60 chars). IDs normalize: `1`/`us-1`/`us-001` all resolve to `us-001`.
- **Tag research generously** (2–5 tags) — tags are searchable and surface in indexes.
- **Created dates are preserved** on update; only `updated` changes.
- **All commands output JSON** — parse it to confirm success and extract paths, slugs, and project names.
- **Use `--scope global`** only for genuinely cross-project knowledge.
