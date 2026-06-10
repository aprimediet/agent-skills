# Repository Guide

## What this is

An Agent Skills project containing seven skills that work together for research, brainstorming, solution architecture, technical architecture, PRD compilation, sprint planning, and knowledge management. Follows the [agentskills.io specification](https://agentskills.io/specification).

- **researcher** — Deep research skill for software development tech evaluation
- **brainstorm** — Interactive brainstorming skill for software projects
- **solution-architect** — Feature breakdown skill that describes what a system does (capabilities, inputs, logic flows, outputs) — not how it's built
- **technical-architect** — Technical design skill that decides how a system is built (architecture style, comprehensive tech stack) from a capability breakdown — the HOW counterpart to solution-architect
- **prd** — Product Requirements Document skill that compiles a PRD by synthesizing a project's upstream artifacts (research + solution spec + technical spec) — the synthesis layer above the architects
- **sprint-planner** — Sprint planning skill that turns a PRD into an executable schedule: derives user stories, prioritizes and estimates them, groups them into sprints, and breaks the first sprint into tasks
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

prd/                         # PRD compilation skill (ships as-is)
├── SKILL.md                 # Skill definition (frontmatter + instructions)
├── examples/                # Real PRD outputs across input-completeness cases
│   ├── file-upload-prd.md            # solution-only inputs, gaps flagged
│   └── subscription-billing-prd.md   # full inputs
├── references/
│   └── OUTPUT_FORMAT.md     # PRD document structure + depth levels
└── evals/
    └── evals.json           # Test cases for skill evaluation

sprint-planner/              # Sprint planning skill (ships as-is)
├── SKILL.md                 # Skill definition (frontmatter + instructions)
├── examples/                # Real sprint plans by depth
│   ├── file-upload-sprint-plan.md            # single feature, one sprint (quick)
│   └── subscription-billing-sprint-plan.md   # product area, three sprints (standard)
├── references/
│   └── OUTPUT_FORMAT.md     # Sprint-plan structure + depth levels
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

- `name` field must match the parent directory name (`researcher` / `brainstorm` / `solution-architect` / `technical-architect` / `prd` / `sprint-planner` / `librarian`)
- `name`: lowercase, hyphens, no consecutive hyphens, max 64 chars
- `description`: max 1024 chars
- SKILL.md body: recommended under 500 lines (researcher: ~135 lines, brainstorm: ~136 lines, solution-architect: ~136 lines, technical-architect: ~133 lines, prd: ~115 lines, sprint-planner: ~111 lines, librarian: ~184 lines)
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

### prd

- Output format details live in `references/OUTPUT_FORMAT.md`, not inline in SKILL.md
- Examples in `examples/` show real PRDs across input-completeness cases (full inputs vs. solution-only with gaps flagged)
- The skill is interactive on the product layer — it asks the few questions the upstream artifacts don't answer (goals, personas, metrics, scope, phasing)
- It compiles a PRD from a project's research + solution spec + technical spec, retrieved via the librarian skill; if librarian is unavailable, reports what to retrieve
- It proceeds when inputs are missing and flags the gaps, naming which skill to run (researcher / solution-architect / technical-architect) — it does NOT invent capabilities or re-pick the stack
- The skill does NOT persist output — the `{slug}.md` it writes under `./prd/` is a temporary handoff draft; the librarian skill saves it as the project PRD. If librarian is unavailable, it tells the user what to save and where
- After changing SKILL.md, re-run evals to verify behavior

### sprint-planner

- Output format details live in `references/OUTPUT_FORMAT.md`, not inline in SKILL.md
- Examples in `examples/` show real sprint plans for each depth (one-sprint quick vs. multi-sprint standard)
- The skill is interactive at two decision points — delivery priority/scope, and breaking stories into tasks
- It reads the project PRD via the librarian skill; if no PRD exists, it recommends running the prd skill first (and may proceed from the solution spec, flagged); if librarian is unavailable, reports what to retrieve
- Every user story traces to a PRD requirement (FR/CAP); it estimates in Fibonacci points, groups by priority/dependency, and breaks down the first sprint only (just-in-time) — later sprints stay at story level
- The skill does NOT persist output — the `{slug}.md` it writes under `./sprint-planner/` is a temporary handoff draft; the librarian skill creates the sprints, user stories, and tasks. If librarian is unavailable, it tells the user what to create and where
- After changing SKILL.md, re-run evals to verify behavior

### librarian

- Artifact format details live in `references/ARTIFACT_FORMAT.md`, not inline in SKILL.md
- The Python script (`scripts/librarian.py`) handles all file operations — don't manually create/edit artifact files
- Examples in `examples/` show real artifact outputs for each category
- Stories carry optional `--points` (Fibonacci estimate) and `--priority` (MoSCoW) fields, surfaced in the sprint index; the PRD lives at the project root via the `prd` noun
- After changing SKILL.md or the script, re-run evals to verify behavior

## Running evals

Eval uses the skill-creator skill's tooling. The workflow:

1. Edit `{skill}/evals/evals.json` to define test prompts
2. Spawn subagents with and without the skill for each test case
3. Grade outputs against assertions in `eval_metadata.json` per eval
4. Aggregate into `benchmark.json` and generate review HTML via `skill-creator/eval-viewer/generate_review.py`
5. Review outputs, iterate

Each skill has its own `{skill}-workspace/` directory (e.g. `researcher-workspace/`, `solution-architect-workspace/`) holding iteration artifacts — not shipped, not part of the skill, safe to delete between eval cycles. Note: `researcher-workspace/`, `librarian-workspace/`, `prd-workspace/`, and `sprint-planner-workspace/` are gitignored; add new workspace dirs to `.gitignore` so `git add -A` doesn't sweep them into commits.

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

### prd

The skill writes a temporary draft to `./prd/` (relative to working directory):
- `{slug}.md` — structured PRD document (working draft for handoff)

Slug is derived from the project or feature name: lowercase, hyphens, max 60 chars.

The skill does NOT persist output — the `{slug}.md` file is a temporary handoff draft, and the librarian skill performs the actual save (as the project PRD). If librarian is unavailable, the skill tells the user what to save and where.

### sprint-planner

The skill writes a temporary draft to `./sprint-planner/` (relative to working directory):
- `{slug}.md` — structured sprint plan (working draft for handoff)

Slug is derived from the project or feature name: lowercase, hyphens, max 60 chars.

The skill does NOT persist output — the `{slug}.md` file is a temporary handoff draft, and the librarian skill creates the actual sprints, user stories (with `--points`/`--priority`), and tasks. If librarian is unavailable, the skill tells the user what to create and where.

### librarian

The skill manages artifacts under `./projects/` (project scope) or `$AGENT_ROOT/projects/` (global scope), project-first — every artifact lives inside one project directory (`YYYY_MM_DD_slug/`):
- `researches/` — date-prefixed notes (`YYYY_MM_DD_slug.md`)
- `specs/` — fixed-name specs by type (`technical.md`, `solution.md`, `api-design.md`, `design.md`)
- `prd.md` — one project-level PRD at the project root
- `sprints/` — sprints → user stories → tasks, each with an auto-maintained `index.md`; stories carry optional `points` (Fibonacci) and `priority` (MoSCoW) fields, surfaced in the sprint index
- `index.md` — auto-maintained at every level (all-projects, project, researches, specs, sprints, story)

The active project is tracked in `.librarian/current`; commands target it implicitly (override with `--project`). All operations go through `scripts/librarian.py` (noun-verb CLI, e.g. `project create`, `spec write`, `prd write`, `sprint create`, `story create --points --priority`). Slug format: lowercase, hyphens, max 60 chars.