# Output Format Reference

This file defines the exact output format for technical-architect documents. Consult this when generating the final output.

## Technical Architecture — `./technical-architect/{slug}.md`

Use this exact structure:

```markdown
# {Title} — Technical Architecture

> Technical Architect | Depth: {quick|standard|deep} | Generated: {date}

## Source Breakdown

{The capability breakdown this architecture builds on. If retrieved via the librarian skill, link it. If provided by the user inline, say so. If none existed and capabilities were inferred, say that and recommend running solution-architect.}

- [{Capability breakdown title}]({path}) — {1-sentence note on what it covers}

## Constraints & Assumptions

- **Scale & load**: {expected users/traffic, growth, latency/availability targets — stated or assumed}
- **Team**: {languages/frameworks the team knows, team size — stated or assumed}
- **Hosting**: {cloud preference, on-prem, existing infrastructure — stated or assumed}
- **Hard constraints**: {budget, compliance, data residency, must-use/must-avoid tech — stated or assumed}
- **Existing systems**: {what this integrates with or runs alongside}

Mark each item as **[stated]** or **[assumed]** so the user can correct assumptions quickly.

## Architecture Overview

- **Style**: {monolith | modular monolith | microservices | serverless | event-driven | hybrid} — {one-line rationale tied to scale and team}
- **Shape**: {2-4 sentences describing the major components and how they interact — the mental model of the system}

## Tech Stack

For each applicable layer: a **Recommendation**, a **Why**, and **Alternatives** (1-2, with when to prefer). Omit layers that genuinely don't apply and note why.

### Frontend
- **Recommendation**: {technology + brief shape}
- **Why**: {reasoning tied to capabilities/constraints}
- **Alternatives**: {option — when you'd prefer it}

### Backend / API
- **Recommendation**: ...
- **Why**: ...
- **Alternatives**: ...

### Data storage
{Primary database, plus cache, search, blob/object store, analytics store as needed — each with recommendation, why, alternatives.}

### Async / messaging
{Queues, event streams, background jobs — if the capabilities need them. If not, state "Not needed because …".}

### Authentication & authorization
{Identity, sessions/tokens, roles/permissions.}

### Infrastructure & hosting
{Compute model, deployment target, networking, scaling approach.}

### CI/CD & developer tooling
{Build/test/deploy pipeline, environments, IaC.}

### Observability
{Logging, metrics, tracing, alerting.}

### Third-party services & integrations
{Payment, email, storage, etc. — mapped to the capabilities that need them.}

### Security
{Secrets management, encryption in transit/at rest, key handling, relevant compliance controls.}

## Capability → Tech Mapping

Map every capability from the source breakdown to the components/technologies that implement it. This makes coverage explicit — no capability should be unsupported, no technology unjustified.

| Capability | Implemented by | Notes |
|-----------|----------------|-------|
| CAP-01 {name} | {components/tech} | {note} |
| CAP-02 {name} | {components/tech} | {note} |
| ... | ... | ... |

If the source breakdown has no CAP-NN IDs, list capabilities by name instead.

## Key Architecture Decisions

ADR-style, numbered. Record only the consequential choices.

### AD-01: {Decision title}

- **Decision**: {what was chosen}
- **Context**: {what forces the decision — capabilities, constraints, scale}
- **Rationale**: {why this over the alternatives}
- **Tradeoffs**: {what this costs or risks}

### AD-02: {Decision title}

{Same structure}

## Risks & Tradeoffs

- {Technical risk or sensitivity — where the design could bite, and the mitigation}
- {...}

## Research Suggestions

High-stakes or uncertain technology choices to validate with the researcher skill:

- **{Topic}** — {why it needs research}. Suggested researcher query: "{ready-to-use prompt}"

## Open Questions

- {Unresolved technical decision needing the user or a stakeholder}

## Next Steps

1. {Concrete action — e.g., spike, proof-of-concept, set up repo/infra}
2. {...}
3. {...}

---
*Technical architecture produced by technical-architect skill. Use the librarian skill to persist this artifact.*
```

## Slug derivation

The `slug` is derived from the feature or project name: lowercase, hyphens for spaces, max 60 chars. For example, "Subscription Billing System" becomes `subscription-billing-system-architecture` (append `-architecture` to distinguish from the capability breakdown's slug).

## Depth level guidance

| Depth | Stack coverage | Question Rounds | When to use |
|-------|----------------|-----------------|-------------|
| **quick** | Core layers (frontend, backend, data, hosting) | 2-3 | A single feature or small service. |
| **standard** | Full stack + 2-4 ADRs | 3-4 | A product or app with several capabilities. |
| **deep** | Full stack + architecture-style analysis + multiple ADRs + scaling | 4-5 | An entire system or platform. |

## Recommendation format

Recommendations are opinionated but transparent. Always give the reasoning and a real alternative:

- ✅ "Postgres — the data is relational and you need transactional integrity across billing records. Alternative: DynamoDB if you expect extreme write scale with simple access patterns."
- ❌ "You could use Postgres, MySQL, MongoDB, DynamoDB, or CockroachDB." (no call, no reasoning)

Adapt the recommendation to stated constraints. If the user said "we're an AWS shop," prefer managed AWS services and say so; don't recommend a stack that fights their constraints.

## How, not what

Stay on the technical side. Anchor every choice to a capability that already exists in the breakdown:

- ✅ "CAP-03 (virus scanning) runs as an async worker consuming an SQS queue, so uploads aren't blocked on scan latency."
- ❌ "The system should also let admins approve files before they're published." (that's a new capability — belongs in solution-architect, flag it back instead of inventing it)
