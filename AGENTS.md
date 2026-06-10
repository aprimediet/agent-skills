# Repository Guide

## What this is

An Agent Skills project containing five skills that work together for research, brainstorming, solution architecture, technical architecture, and knowledge management. Follows the [agentskills.io specification](https://agentskills.io/specification).

- **researcher** — Deep research skill for software development tech evaluation
- **brainstorm** — Interactive brainstorming skill for software projects
- **solution-architect** — Feature breakdown skill that describes what a system does (capabilities, inputs, logic flows, outputs) — not how it's built
- **technical-architect** — Technical design skill that decides how a system is built (architecture style, comprehensive tech stack) from a capability breakdown — the HOW counterpart to solution-architect
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

solution-architect/          # Feature breakdown skill (ships as-is)
├── SKILL.md                 # Skill definition (frontmatter + instructions)
├── examples/                # Real output examples for each depth level
│   ├── file-upload.md
│   ├── subscription-billing.md
│   └── marketplace-platform.md
├── references/
│   └── OUTPUT_FORMAT.md     # Output format spec (capability breakdown structure)
└── evals/
    └── evals.json           # Test cases for skill evaluation

technical-architect/         # Technical design skill (ships as-is)
├── SKILL.md                 # Skill definition (frontmatter + instructions)
├── examples/                # Real output examples for each depth level
│   ├── file-upload-architecture.md
│   ├── subscription-billing-architecture.md
│   └── marketplace-platform-architecture.md
├── references/
│   └── OUTPUT_FORMAT.md     # Output format spec (technical architecture structure)
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

- `name` field must match the parent directory name (`researcher` / `brainstorm` / `solution-architect` / `technical-architect` / `librarian`)
- `name`: lowercase, hyphens, no consecutive hyphens, max 64 chars
- `description`: max 1024 chars
- SKILL.md body: recommended under 500 lines (researcher: ~135 lines, brainstorm: ~136 lines, solution-architect: ~136 lines, technical-architect: ~133 lines, librarian: ~191 lines)
- File references use relative paths from skill root
- Progressive disclosure: metadata → SKILL.md body → references/examples on demand

## Editing the skills

### researcher

- Output format details live in `references/OUTPUT_FORMAT.md`, not inline in SKILL.md
- Examples in `examples/` are real eval outputs — update them if you change the output format
- After changing SKILL.md, re-run evals to verify structure is still produced correctly
- Suggests the librarian skill for persisting research artifacts; if librarian is unavailable, reports what to save and where so another agent can persist it

### brainstorm

- Output format details live in `references/OUTPUT_FORMAT.md`, not inline in SKILL.md
- Examples in `examples/` show real brainstorm outputs for each depth level
- The skill is interactive — it asks questions, doesn't dump a questionnaire
- Before brainstorming, the skill checks for existing research/specs via the librarian skill; if unavailable, reports what to search for so another agent can retrieve it
- When research is needed, it flags topics and suggests the researcher skill — it does NOT research itself
- The skill does NOT persist output — it produces a document and suggests the librarian skill for saving; if librarian is unavailable, tells the user what to save and where
- After changing SKILL.md, re-run evals to verify behavior

### solution-architect

- Output format details live in `references/OUTPUT_FORMAT.md`, not inline in SKILL.md
- Examples in `examples/` show real capability breakdowns for each depth level
- The skill is interactive — it asks questions, doesn't dump a questionnaire
- Before starting, the skill checks for existing artifacts via the librarian skill; if unavailable, reports what to search for so another agent can retrieve it
- The skill describes WHAT a system does (capabilities, inputs, logic flows, outputs), NOT HOW it's built (no tech stack, no architecture, no code)
- When research is needed, it flags topics and suggests the researcher skill — it does NOT research itself
- The skill does NOT persist output — the `{slug}.md` it writes is a temporary handoff draft; the librarian skill performs the actual save. If librarian is unavailable, it tells the user what to save and where
- After changing SKILL.md, re-run evals to verify behavior

### technical-architect

- Output format details live in `references/OUTPUT_FORMAT.md`, not inline in SKILL.md
- Examples in `examples/` show real technical architectures for each depth level
- The skill is interactive but light — it asks only the few constraint questions (scale, team, hosting, compliance) that change the recommendation, not an exhaustive questionnaire
- It builds on a capability breakdown (ideally from solution-architect), retrieved via the librarian skill or provided by the user; if neither exists, it suggests running solution-architect first
- The skill describes HOW a system is built (architecture style, comprehensive tech stack), NOT WHAT it does — it does not invent or redefine capabilities; ambiguous capabilities are flagged back to solution-architect
- Recommendations are opinionated (one choice per layer with rationale + alternatives) and adapt to stated constraints
- When a tech choice is high-stakes/uncertain, it flags the topic for the researcher skill — it does NOT research itself
- The skill does NOT persist output — the `{slug}.md` it writes is a temporary handoff draft; the librarian skill performs the actual save. If librarian is unavailable, it tells the user what to save and where
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

Each skill has its own `{skill}-workspace/` directory (e.g. `researcher-workspace/`, `solution-architect-workspace/`) holding iteration artifacts — not shipped, not part of the skill, safe to delete between eval cycles. Note: only `researcher-workspace/` and `librarian-workspace/` are currently gitignored; add new workspace dirs to `.gitignore` so `git add -A` doesn't sweep them into commits.

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

### solution-architect

The skill writes a temporary draft to `./solution-architect/` (relative to working directory):
- `{slug}.md` — structured capability breakdown document (working draft for handoff)

Slug is derived from the feature or project name: lowercase, hyphens, max 60 chars.

The skill does NOT persist output — the `{slug}.md` file is a temporary handoff draft, and the librarian skill performs the actual save. If librarian is unavailable, the skill tells the user what to save and where.

### technical-architect

The skill writes a temporary draft to `./technical-architect/` (relative to working directory):
- `{slug}.md` — structured technical architecture document (working draft for handoff)

Slug is derived from the feature or project name with an `-architecture` suffix: lowercase, hyphens, max 60 chars.

The skill does NOT persist output — the `{slug}.md` file is a temporary handoff draft, and the librarian skill performs the actual save. If librarian is unavailable, the skill tells the user what to save and where.

### librarian

The skill manages artifacts in `./docs/` (project scope) or `$AGENT_ROOT/docs/` (global scope):
- `researches/` — date-prefixed directories (`YYYY_MM_DD__slug/index.md`)
- `specs/` — flat files (`slug.md`)
- `tasks/` — flat files (`slug.md`)
- `docs/` — flat files (`slug.md`)
- `index.md` — auto-maintained knowledge index

All operations go through `scripts/librarian.py`. Slug format: lowercase, hyphens, max 60 chars.