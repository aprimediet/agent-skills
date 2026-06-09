# Repository Guide

## What this is

An Agent Skills project containing three skills that work together for research, brainstorming, and knowledge management. Follows the [agentskills.io specification](https://agentskills.io/specification).

- **researcher** — Deep research skill for software development tech evaluation
- **brainstorm** — Interactive brainstorming skill for software projects
- **librarian** — Knowledge management skill for organizing, searching, reading, and writing agent-produced artifacts

## Structure

```
researcher/                  # Research skill (ships as-is)
├── SKILL.md                 # Skill definition (frontmatter + instructions)
├── examples/                # Real output examples for each research type
│   ├── tech-evaluation-deep.md + .meta.json
│   ├── product-research-standard.md + .meta.json
│   └── feature-investigation-quick.md + .meta.json
├── references/
│   └── OUTPUT_FORMAT.md     # Detailed output format templates + scoring rubric
└── evals/
    └── evals.json           # Test cases for skill evaluation

brainstorm/                  # Brainstorming skill (ships as-is)
├── SKILL.md                 # Skill definition (frontmatter + instructions)
├── examples/                # Real output examples for each brainstorm depth
│   ├── saas-mvp-brainstorm.md
│   ├── cli-tool-brainstorm.md
│   └── platform-brainstorm.md
├── references/
│   └── OUTPUT_FORMAT.md     # Output format spec (document structure, depth levels)
└── evals/
    └── evals.json           # Test cases for skill evaluation

librarian/                   # Knowledge management skill (ships as-is)
├── SKILL.md                 # Skill definition (frontmatter + instructions)
├── examples/                # Real output examples for each artifact type
│   ├── research-note.md
│   ├── spec-document.md
│   └── task-tracking.md
├── references/
│   └── ARTIFACT_FORMAT.md   # Artifact format spec (frontmatter, directory structure)
├── scripts/
│   └── librarian.py         # CLI for all file operations, search, and retrieval
└── evals/
    └── evals.json           # Test cases for skill evaluation

researcher-workspace/         # Eval artifacts (not shipped, not part of the skill)
```

## SKILL.md constraints (from spec)

Applies to all skills:

- `name` field must match the parent directory name (`researcher` / `brainstorm` / `librarian`)
- `name`: lowercase, hyphens, no consecutive hyphens, max 64 chars
- `description`: max 1024 chars
- SKILL.md body: recommended under 500 lines (researcher: ~135 lines, brainstorm: ~120 lines, librarian: ~191 lines)
- File references use relative paths from skill root
- Progressive disclosure: metadata → SKILL.md body → references/examples on demand

## Editing the skills

### researcher

- Output format details live in `references/OUTPUT_FORMAT.md`, not inline in SKILL.md
- Examples in `examples/` are real eval outputs — update them if you change the output format
- After changing SKILL.md, re-run evals to verify structure is still produced correctly

### brainstorm

- Output format details live in `references/OUTPUT_FORMAT.md`, not inline in SKILL.md
- Examples in `examples/` show real brainstorm outputs for each depth level
- The skill is interactive — it asks questions, doesn't dump a questionnaire
- When research is needed, it flags topics and suggests the researcher skill — it does NOT research itself
- The skill does NOT persist output — it produces a document and suggests the librarian skill for saving
- After changing SKILL.md, re-run evals to verify behavior

### librarian

- Artifact format details live in `references/ARTIFACT_FORMAT.md`, not inline in SKILL.md
- The Python script (`scripts/librarian.py`) handles all file operations — don't manually create/edit artifact files
- Examples in `examples/` show real artifact outputs for each category
- After changing SKILL.md or the script, re-run evals to verify behavior

## Running evals

Eval uses the skill-creator skill's tooling. The workflow:

1. Edit `{skill}/evals/evals.json` to define test prompts
2. Spawn subagents with and without the skill for each test case
3. Grade outputs against assertions in `eval_metadata.json` per eval
4. Aggregate into `benchmark.json` and generate review HTML via `skill-creator/eval-viewer/generate_review.py`
5. Review outputs, iterate

The `researcher-workspace/` directory holds iteration artifacts — safe to delete between eval cycles.

## Skill output conventions

### researcher

The skill writes output to `./researcher/` (relative to working directory):
- `{slug}.md` — structured markdown report
- `{slug}.meta.json` — machine-readable metadata with scored sources

Slug is derived from the research topic: lowercase, hyphens, max 60 chars.

### brainstorm

The skill writes output to `./brainstorm/` (relative to working directory):
- `{slug}.md` — structured brainstorm document

Slug is derived from the project idea: lowercase, hyphens, max 60 chars.

The skill does NOT persist output — it suggests the librarian skill for saving.

### librarian

The skill manages artifacts in `./docs/` (project scope) or `$AGENT_ROOT/docs/` (global scope):
- `researches/` — date-prefixed directories (`YYYY_MM_DD__slug/index.md`)
- `specs/` — flat files (`slug.md`)
- `tasks/` — flat files (`slug.md`)
- `docs/` — flat files (`slug.md`)
- `index.md` — auto-maintained knowledge index

All operations go through `scripts/librarian.py`. Slug format: lowercase, hyphens, max 60 chars.