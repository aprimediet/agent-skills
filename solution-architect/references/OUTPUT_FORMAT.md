# Output Format Reference

This file defines the exact output format for solution-architect capability breakdowns. Consult this when generating the final output.

## Capability Breakdown — `./solution-architect/{slug}.md`

Use this exact structure:

```markdown
# {Title}

> Solution Architect | Depth: {quick|standard|deep} | Generated: {date}

## Existing Knowledge

{If relevant research, specs, or notes were found via the librarian skill, list them here. If none, omit this section entirely.}

- [{Artifact title}]({path}) — {1-sentence summary of what it covers and how it informs this breakdown}

## Problem Statement

- **Business problem**: {What problem does this solve for the business?}
- **User problem**: {What problem does this solve for the end user?}
- **Success criteria**: {How will you know this feature is working? Measurable outcomes.}

## Scope

- **In scope**: {What this feature/system covers}
- **Out of scope**: {What is explicitly excluded}
- **Existing systems**: {What this needs to integrate with or work alongside}

## Capabilities

### CAP-01: {Capability name}

**Trigger**: {What initiates this capability — user action, system event, scheduled job, external input}

**Inputs**:
- {Input 1}: {description, format, source}
- {Input 2}: {description, format, source}

**Logic flow**:
1. {Step 1 — what happens first}
2. {Step 2 — what happens next, including any decision points}
3. {Step 3 — continue until the capability completes}
4. {Error path — what happens when something goes wrong}

**Outputs**:
- {Output 1}: {description, format, destination}
- {Output 2}: {description, format, destination}

**Edge cases**:
- {What happens if input is missing/invalid?}
- {What happens if a dependency fails?}
- {What happens under high load or unusual conditions?}

**Connects to**: {List other capability IDs this one depends on or feeds into}

---

### CAP-02: {Capability name}

{Same structure as above}

---

{Continue for each capability}

## Dependency Map

| Capability | Depends on | Feeds into |
|-----------|-----------|------------|
| CAP-01 | — | CAP-03, CAP-04 |
| CAP-02 | — | CAP-01 |
| CAP-03 | CAP-01, CAP-02 | CAP-05 |
| ... | ... | ... |

## Open Questions

- {Unresolved decision with brief context}
- {Unresolved decision with brief context}

## Research Suggestions

Topics that need deeper investigation by the researcher skill:

- **{Topic}** — {Why it needs research, suggested researcher query}
- **{Topic}** — {Why it needs research, suggested researcher query}

## Next Steps

1. {Concrete next action}
2. {Concrete next action}
3. {Concrete next action}

---
*Capability breakdown produced by solution-architect skill. Use the librarian skill to persist this artifact.*
```

## Slug derivation

The `slug` is derived from the feature or project name: lowercase, hyphens for spaces, max 60 chars. For example, "Subscription Billing System" becomes `subscription-billing-system`.

## Depth level guidance

| Depth | Capabilities | Question Rounds | When to use |
|-------|-------------|-----------------|-------------|
| **quick** | 1-3 | 2-3 | Single, well-defined features. Login, file upload, notification. |
| **standard** | 4-8 | 3-4 | Multi-feature areas. Subscription management, user onboarding, search. |
| **deep** | 8-15 | 4-5 | Entire systems or platforms. Marketplace, ERP module, SaaS product. |

## Capability ID format

Each capability gets a sequential ID: `CAP-01`, `CAP-02`, etc. This makes it easy to reference capabilities in the dependency map and in conversations.

## Logic flow guidelines

Logic flows describe **what** happens, not **how** it's implemented:

- ✅ "The system validates the user's payment method and charges the card"
- ❌ "The Stripe API is called with the customer ID and amount"

- ✅ "If the charge fails, the system retries up to 3 times with a 1-hour delay"
- ❌ "A Redis queue with exponential backoff processes retries"

Include decision points explicitly:
- "If the user is on a free plan, skip to CAP-03"
- "If the payment method is expired, notify the user and pause the subscription"

## Research suggestion format

Each research suggestion should include:
1. **Topic** — what to research
2. **Why** — why it matters for this capability breakdown
3. **Suggested query** — a ready-to-use prompt for the researcher skill

Example:
- **Payment retry strategies** — Need to define the retry policy for failed charges. Suggested researcher query: "Payment retry best practices for SaaS subscriptions — exponential backoff, max attempts, and dunning workflows"