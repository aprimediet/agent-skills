# Output Format Reference

This file defines the exact output format for brainstorm skill documents. Consult this when generating the final output.

## Brainstorm Document — `./brainstorm/{slug}.md`

Use this exact structure:

```markdown
# {Title}

> Brainstorm | Depth: {quick|standard|deep} | Generated: {date}

## Existing Knowledge

{If relevant research, specs, or notes were found via the librarian skill, list them here. If none, omit this section entirely.}

- [{Artifact title}]({path}) — {1-sentence summary of what it covers and how it informs this brainstorm}

## Core Idea

{1-3 sentences capturing the essence of the project idea as discussed.}

## Problem & Motivation

- **Problem**: {What problem does this solve?}
- **Who**: {Target users}
- **Why now**: {Why is this timely or important?}

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| {e.g., "Architecture"} | {e.g., "Monolith first"} | {e.g., "Faster to ship, refactor later"} |
| {e.g., "Data store"} | {e.g., "Undecided — Postgres vs MongoDB"} | {e.g., "Depends on query patterns"} |

## Dimensions Explored

### {Dimension 1: e.g., "Architecture & Tech Stack"}

{2-4 sentences summarizing what was discussed and decided.}

- {Key point}
- {Key point}

### {Dimension 2: e.g., "User Experience"}

{2-4 sentences summarizing what was discussed and decided.}

- {Key point}
- {Key point}

{Continue for each dimension explored.}

## Open Questions

- {Question that wasn't answered during brainstorm, with brief context}
- {Question that wasn't answered during brainstorm, with brief context}

## Research Suggestions

Topics that need deeper investigation by the researcher skill:

- **{Topic}** — {Why it needs research, suggested researcher query}
- **{Topic}** — {Why it needs research, suggested researcher query}

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| {Risk description} | {High/Medium/Low} | {High/Medium/Low} | {How to address it} |

## Next Steps

1. {Concrete next action}
2. {Concrete next action}
3. {Concrete next action}

---
*Brainstorm document produced by brainstorm skill. Use the librarian skill to persist this artifact.*
```

## Slug derivation

The `slug` is derived from the project idea: lowercase, hyphens for spaces, max 60 chars. For example, "Task Management SaaS for Remote Teams" becomes `task-management-saas-remote-teams`.

## Depth level guidance

The depth level affects how many dimensions are explored and how detailed the document is:

| Depth | Dimensions | Question Rounds | When to use |
|-------|-----------|-----------------|-------------|
| **quick** | 2-3 | 2-3 | Small, well-defined ideas. CLI tools, simple utilities. |
| **standard** | 4-5 | 3-4 | Typical projects. SaaS products, web apps, APIs. |
| **deep** | 5-7 | 4-5 | Complex, multi-faceted projects. Platforms, ecosystems, large-scale systems. |

## Dimension coverage

Not every brainstorm needs every dimension. Pick the most relevant ones:

**Technical dimensions:**
- Architecture & tech stack
- Data model & storage
- APIs & integrations
- Security & auth
- Performance & scalability
- DevOps & deployment
- Testing strategy

**Non-technical dimensions:**
- Target users & personas
- User experience & workflows
- Business model & monetization
- Competition & differentiation
- Team & resourcing
- Regulatory & compliance
- Go-to-market strategy

## Research suggestion format

Each research suggestion should include:
1. **Topic** — what to research
2. **Why** — why it matters for this project
3. **Suggested query** — a ready-to-use prompt for the researcher skill

Example:
- **Tech stack comparison** — Need to decide between Postgres and MongoDB for the data layer. Suggested researcher query: "Postgres vs MongoDB for SaaS multi-tenant applications 2025"