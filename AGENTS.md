# Repository Guide

## What this is

An Agent Skills project containing the `researcher` skill — a deep research skill for software development tech evaluation. Follows the [agentskills.io specification](https://agentskills.io/specification).

## Structure

```
researcher/                  # The skill (ships as-is)
├── SKILL.md                 # Skill definition (frontmatter + instructions)
├── examples/                # Real output examples for each research type
│   ├── tech-evaluation-deep.md + .meta.json
│   ├── product-research-standard.md + .meta.json
│   └── feature-investigation-quick.md + .meta.json
├── references/
│   └── OUTPUT_FORMAT.md     # Detailed output format templates + scoring rubric
└── evals/
    └── evals.json           # Test cases for skill evaluation

researcher-workspace/         # Eval artifacts (not shipped, not part of the skill)
```

## SKILL.md constraints (from spec)

- `name` field must match the parent directory name (`researcher`)
- `name`: lowercase, hyphens, no consecutive hyphens, max 64 chars
- `description`: max 1024 chars
- SKILL.md body: recommended under 500 lines (currently ~136)
- File references use relative paths from skill root
- Progressive disclosure: metadata → SKILL.md body → references/examples on demand

## Editing the skill

- Output format details live in `references/OUTPUT_FORMAT.md`, not inline in SKILL.md
- Examples in `examples/` are real eval outputs — update them if you change the output format
- After changing SKILL.md, re-run evals to verify structure is still produced correctly

## Running evals

Eval uses the skill-creator skill's tooling. The workflow:

1. Edit `researcher/evals/evals.json` to define test prompts
2. Spawn subagents with and without the skill for each test case
3. Grade outputs against assertions in `eval_metadata.json` per eval
4. Aggregate into `benchmark.json` and generate review HTML via `skill-creator/eval-viewer/generate_review.py`
5. Review outputs, iterate

The `researcher-workspace/` directory holds iteration artifacts — safe to delete between eval cycles.

## Skill output convention

The skill writes output to `./researcher/` (relative to working directory):
- `{slug}.md` — structured markdown report
- `{slug}.meta.json` — machine-readable metadata with scored sources

Slug is derived from the research topic: lowercase, hyphens, max 60 chars.