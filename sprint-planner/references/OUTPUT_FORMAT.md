# Sprint Plan Output Format

The sprint plan is a single markdown document, written to `./sprint-planner/{slug}.md` as a working draft. The librarian skill turns it into real sprints, user stories, and tasks — this file is the handoff, not the stored artifact.

## Frontmatter

```yaml
---
title: <Project / feature name> Sprint Plan
type: sprint-plan        # working-draft marker; librarian stores the structure, not this file
created: <ISO 8601>
updated: <ISO 8601>
source: prd              # what this plan was scheduled from
---
```

## Document structure

Use this template. Scale to the depth level. Every story carries an ID, its source PRD requirement, a priority, and a point estimate — that traceability is what makes the plan auditable.

```markdown
# <Project / feature name> — Sprint Plan

## Overview
One paragraph: what's being scheduled, how many sprints, and the headline of
each sprint's goal. Note the PRD it was compiled from.

## Backlog (prioritized)
Every in-scope user story, ordered by priority then dependency.

| Story | As a… I want… so that… | Source | Priority | Points |
|-------|------------------------|--------|----------|--------|
| US-001 | As a customer, I want to subscribe, so that I can use paid features | FR-1 / CAP-01 | Must | 5 |
| US-002 | As a customer, I want to change plan mid-cycle, so that I'm billed fairly | FR-2 / CAP-02 | Should | 8 |

Deferred (out of scope this round): list any stories cut, with one-line why.

## Dependencies
Hard ordering constraints that shaped the schedule (e.g. "US-003 needs US-001").
Omit if none.

## Schedule

### Sprint 1 — <theme / goal>  (points: N)
Stories in this sprint, with their tasks broken out (Sprint 1 only).

- **US-001** — <story> · `Must` · 5 pts
  - [ ] task: <concrete task>
  - [ ] task: <concrete task>
- **US-00X** — <story> · `Must` · 3 pts
  - [ ] task: <concrete task>

### Sprint 2 — <theme / goal>  (points: N)
Stories only — broken into tasks just-in-time when Sprint 2 is next.

- **US-002** — <story> · `Should` · 8 pts
- **US-00Y** — <story> · `Could` · 2 pts

## Risks & Open Questions
Oversized stories flagged for splitting, lopsided sprints, unresolved priority
calls, or PRD gaps surfaced during planning (recommend the prd skill to close).

## Librarian handoff
The exact commands to create this structure (sprints, every story, Sprint 1
tasks). See the skill's Step 6.
```

## Notes

- **Traceability is the point.** The `Source`, `Priority`, and `Points` columns let anyone see why a story is where it is. Keep them honest.
- **Tasks for Sprint 1 only.** Later sprints stay at story level — detailing them now is waste.
- **A 13-point story is a flag.** Either split it (preferred) or call it out as a risk; don't quietly schedule it whole.
- **The plan is the user's.** Priority, scope, and task breakdown reflect what the user decided, not what you assumed.
