# PRD Output Format

The PRD is a single markdown document, written to `./prd/{slug}.md` as a working draft. The librarian skill persists it as the project-level `prd.md`.

## Frontmatter

```yaml
---
title: <Product / feature name> PRD
type: prd
status: draft            # draft | review | approved
created: <ISO 8601>      # librarian sets/preserves this on save
updated: <ISO 8601>
tags: [prd, <domain tags>]
sources:                 # provenance — what this PRD was compiled from
  - researches/<slug>
  - specs/solution
  - specs/technical
---
```

When you hand off to the librarian skill, pass `--sources` so the provenance is recorded on the saved artifact.

## Document structure

Use this template. Scale each section to the depth level — omit a section only when it genuinely doesn't apply, and say why rather than leaving it blank. Mark any section without upstream support with a `> ⚠ Gap:` callout naming the skill that would close it.

```markdown
# <Product / feature name> — PRD

## 1. Summary
One paragraph: what this is, who it's for, and why it matters now. A reader
should grasp the product in 30 seconds.

## 2. Background & Problem
The context and evidence. *Compiled from research.* What problem are we
solving, for whom, and what do we know (data, prior art, constraints)? If no
research exists:
> ⚠ Gap: No research on record. Recommend the researcher skill for <topics>.

## 3. Goals & Non-Goals
- **Goals** — the product outcomes this round is committing to.
- **Non-Goals** — what is explicitly out of scope, so the boundary is unambiguous.

## 4. Success Metrics
How we'll know it worked — measurable where possible (adoption, conversion,
latency SLO, ticket reduction). If none are defined:
> ⚠ Gap: Success metrics undefined. Recommend a discovery pass with the user.

## 5. Users & Personas
The segments this serves and what each needs. Keep it to the personas that
change a decision.

## 6. Requirements

### 6.1 Functional Requirements
*Compiled from the solution spec's capabilities.* Preserve capability IDs.

| ID | Requirement | Source capability | Priority |
|----|-------------|-------------------|----------|
| FR-1 | … | CAP-01 | Must |
| FR-2 | … | CAP-03 | Should |

### 6.2 Non-Functional Requirements
*Compiled from the technical spec.* Scale, performance, security, compliance,
availability.

| ID | Requirement | Source |
|----|-------------|--------|
| NFR-1 | … | technical spec |

## 7. Key User Flows
*From the solution spec's logic flows.* The main paths through the product, as
short step lists or a simple diagram.

## 8. Technical Considerations
A short summary of the chosen architecture and stack, with a link to the
technical spec — not a copy. Call out anything that materially shapes scope,
timeline, or risk. If no technical spec exists:
> ⚠ Gap: No technical spec. Recommend the technical-architect skill.

## 9. Milestones / Release Plan
Phased sequencing tied to the priorities — what ships first and why.

## 10. Risks & Open Questions
Risks, dependencies, and decisions still needing an owner. Unresolved gaps from
above land here too.

## 11. Sources
Links to the artifacts this PRD was compiled from:
- Research: researches/<slug>
- Solution spec: specs/solution
- Technical spec: specs/technical
```

## Notes

- **Traceability is the point.** The `Source` columns and the Sources section are what make a PRD a compilation rather than a fresh invention. Keep them honest.
- **Gaps over fabrication.** A flagged gap is more valuable than an invented metric or capability.
- **Don't duplicate the technical spec.** Summarize and link. The PRD is the synthesis layer.
