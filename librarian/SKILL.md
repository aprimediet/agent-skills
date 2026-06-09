---
name: librarian
description: >
  Knowledge management skill for organizing, searching, reading, and writing
  agent-produced artifacts as markdown files. Manages structured directories
  (researches, specs, tasks, docs) with YAML frontmatter metadata and an
  auto-maintained index. Researches use date-prefixed directories
  (YYYY_MM_DD__topic). Provides a Python script for all file operations,
  full-text search, and artifact retrieval. Use this skill whenever you need
  to save, find, read, organize, or manage any agent output — research reports,
  specifications, task notes, decision logs, or any markdown knowledge artifact.
  Triggers on "save this research", "find my notes on X", "organize these
  artifacts", "where did I put X", "list all specs", "search docs for X",
  "store this finding", "write up these results", or any request involving
  reading, writing, or managing persisted agent knowledge.
metadata:
  author: skills-dev-oc
  version: "2.0"
---

# Librarian

You are a knowledge management system for agent artifacts. Your job is to help organize, store, find, and manage the markdown files that agents produce during their work — research reports, specifications, task notes, decision logs, and any other structured knowledge.

## How it works

Artifacts are markdown files stored in a structured directory:

```
./docs/                          # Project-scoped (relative to working directory)
├── index.md                     # Auto-maintained knowledge index
├── researches/                  # Date-prefixed directories
│   └── 2026_06_09__topic/       # YYYY_MM_DD__slug format
│       └── index.md             # The artifact file
├── specs/                       # Flat structure
│   └── api-auth.md              # slug.md format
├── tasks/                       # Flat structure
│   └── sprint-12.md
└── docs/                        # Flat structure
    └── deployment-guide.md
```

For global (cross-project) artifacts:

```
$AGENT_ROOT/docs/                # Or ~/.agents/docs/
├── index.md
├── researches/
├── specs/
├── tasks/
└── docs/
```

Each artifact is a markdown file with YAML frontmatter. See [references/ARTIFACT_FORMAT.md](references/ARTIFACT_FORMAT.md) for the full format specification.

The **index.md** file at the root of the docs directory is auto-maintained — it lists all artifacts grouped by category with links, dates, and tags. It's rebuilt automatically on every write, move, or delete operation.

## Workflow

### When the user wants to save knowledge

1. Determine the **category** (researches, specs, tasks, docs, or custom)
2. Determine the **scope** — project (default) or global
3. Generate a **slug** from the title (lowercase, hyphens, max 60 chars)
4. Run the write command:

```bash
python scripts/librarian.py write <category> <slug> \
  --title "Full Title" \
  --content "Markdown content here" \
  --tags "tag1,tag2" \
  --scope project
```

Or pipe content via stdin:

```bash
echo "# My Document\n\nContent here" | \
  python scripts/librarian.py write researches my-document --title "My Document"
```

Or read from a file:

```bash
python scripts/librarian.py write specs api-design \
  --title "API Design Spec" \
  --file /tmp/draft.md
```

**Note:** Researches automatically get date-prefixed directories (`YYYY_MM_DD__slug/`). Other categories use flat files (`slug.md`).

### When the user wants to find knowledge

**Search by content:**

```bash
python scripts/librarian.py search "authentication flow" --scope project
```

**Find by partial name:**

```bash
python scripts/librarian.py fetch "api-design" --scope project
```

**List all artifacts in a category:**

```bash
python scripts/librarian.py list --category researches --scope project
```

**Filter by tags:**

```bash
python scripts/librarian.py list --tags "security,api" --scope project
```

**View the knowledge index:**

```bash
python scripts/librarian.py index --scope project
```

### When the user wants to read knowledge

```bash
python scripts/librarian.py read researches my-document --scope project
```

### When the user wants to reorganize

**Move between categories:**

```bash
python scripts/librarian.py move tasks api-design specs --scope project
```

**Delete an artifact:**

```bash
python scripts/librarian.py delete tasks outdated-note --scope project
```

**Rebuild the index** (if it gets out of sync):

```bash
python scripts/librarian.py index --rebuild --scope project
```

### First-time setup

If the docs directory doesn't exist yet, initialize it:

```bash
python scripts/librarian.py init --scope project
```

This creates the default categories (researches, specs, tasks, docs) and the initial index.md. You can customize:

```bash
python scripts/librarian.py init --scope project --categories "researches,specs,tasks,docs,decisions"
```

## Choosing scope

- **project** (default): Use `./docs/` relative to the current working directory. For knowledge specific to the current project.
- **global**: Use `$AGENT_ROOT/docs/` (or `~/.agents/docs/`). For cross-project knowledge like reusable patterns, personal preferences, or general reference.

When in doubt, use project scope. Only use global scope when the user explicitly says "save this globally" or "this applies to all projects."

## Choosing a category

| Category | Structure | Purpose | Examples |
|-----------|-----------|---------|---------|
| `researches` | `YYYY_MM_DD__slug/index.md` | Research reports, findings, evaluations | "Yjs vs Automerge comparison", "Bun production readiness" |
| `specs` | `slug.md` | Specifications, design docs, architecture decisions | "API design spec", "Auth flow design" |
| `tasks` | `slug.md` | Task tracking, sprint notes, TODO lists | "Sprint 5 notes", "Bug triage log" |
| `docs` | `slug.md` | General documentation, how-tos, guides | "Deployment guide", "Onboarding checklist" |

You can create custom categories by simply writing to them — the script creates directories on demand.

## Important guidelines

- **Always use the script** for file operations. Don't manually create or edit artifact files — the script manages frontmatter, directory structure, and the index automatically.
- **Slugify titles** into lowercase-hyphenated form (max 60 chars). The script auto-slugifies the `slug` argument if you pass a raw title.
- **Tag generously** — tags make artifacts findable later. Use 2-5 tags per artifact.
- **Preserve created dates** — when updating an artifact, the script keeps the original `created` timestamp and only updates `updated`.
- **All commands output JSON** — parse the output to confirm operations succeeded and extract paths, slugs, and metadata.
- **Initialize before first use** — run `init` if the docs directory doesn't exist yet.
- **The index is auto-maintained** — every write, move, or delete rebuilds `index.md`. You can also manually rebuild with `index --rebuild`.
- **Researches use date-prefixed directories** — this keeps research chronologically organized and avoids name collisions.