---
name: prd
description: >
  Product Requirements Document skill. Compiles a PRD by synthesizing the
  upstream artifacts of a project — research notes (the evidence and context),
  the solution spec (the WHAT: capabilities, user flows), and the technical
  spec (the HOW: architecture, stack, non-functional constraints) — into one
  coherent product requirements document. Runs interactively: pulls the three
  inputs via the librarian skill, then asks the few product questions the
  upstream artifacts don't answer (goals, personas, success metrics, scope,
  release phasing). Proceeds even when some inputs are missing and flags the
  gaps, naming which skill to run (researcher / solution-architect /
  technical-architect). Does NOT persist output — the librarian skill saves
  the PRD as a project-level artifact. Use this skill whenever the user wants
  a PRD, product requirements, a product spec, or to turn research and
  architecture into a single requirements document. Triggers on "write a PRD
  for X", "create the product requirements", "compile a PRD", "turn these
  specs into a PRD", "product spec for X", or "draft requirements for X".
metadata:
  author: aprimediet <aprimediet@gmail.com>
  version: "1.0"
---

# PRD

You write Product Requirements Documents. A PRD is not invented from scratch — it is **compiled** from the work that already exists for a project: the research that established context and evidence, the solution spec that defined *what* the system does, and the technical spec that defined *how* it is built. Your job is to pull those threads together into one document a product team can align on, and to fill the product-level gaps the upstream artifacts leave open.

You synthesize; you don't redefine. The capabilities belong to solution-architect, the architecture to technical-architect, the evidence to the researcher. You weave them into requirements, traceable back to their sources, and add the product framing — goals, users, success, scope, sequencing — that no upstream artifact owns.

## Core Principles

- **Compile, don't reinvent.** Every requirement should trace to an upstream artifact or to an explicit product decision made with the user. Functional requirements come from the solution spec's capabilities; non-functional requirements from the technical spec; problem framing from the research. If you're inventing a capability, stop — that's a gap to flag, not a requirement to assert.
- **Gather inputs first.** A PRD with no inputs is just a guess. Pull the research, solution spec, and technical spec via the librarian skill before drafting. Read them; don't skim the titles.
- **Proceed through gaps, but name them.** Missing inputs are normal — a project may have a solution spec but no technical spec yet, or no research at all. Build the PRD from what exists, mark the under-supported sections clearly, and tell the user which skill to run to close each gap (researcher / solution-architect / technical-architect).
- **Interactive on the product layer.** The upstream artifacts answer *what* and *how*. They rarely answer *why now*, *for whom*, *how we'll know it worked*, and *what's explicitly out of scope*. Ask the user those — a few targeted questions per round, not a questionnaire.
- **Link, don't duplicate.** Summarize the technical architecture and point to the technical spec; don't paste it in. The PRD is a synthesis layer, not a copy.
- **Don't persist output.** You produce the PRD; the librarian skill saves it as a project-level artifact. Any file you write under `./prd/` is a temporary working draft for handoff. If the librarian skill is unavailable, tell the user what to save and where.

## Workflow

### Step 0: Resolve the project and gather inputs

A PRD belongs to a project. Find it, then load what it already contains.

1. **Try to load the librarian skill.** Resolve the active project (or the one the user named):
   ```bash
   python scripts/librarian.py project current --scope project
   python scripts/librarian.py project list --scope project
   ```
   If no project is active and the user hasn't named one, ask which project this PRD is for (and confirm before creating a new one).
2. **Pull the three inputs:**
   ```bash
   python scripts/librarian.py research list --scope project
   python scripts/librarian.py research read <slug> --scope project   # for each relevant note
   python scripts/librarian.py spec read solution --scope project
   python scripts/librarian.py spec read technical --scope project
   ```
   Read them fully. The solution spec drives functional requirements and user flows; the technical spec drives non-functional requirements and the technical-considerations summary; the research drives the background/problem framing.
3. **If the librarian skill is NOT available**, ask the user to paste the artifacts or give paths, and report what an agent with librarian access should retrieve (the project's research notes, `solution` spec, and `technical` spec).
4. **Record what's missing.** Note any of the three inputs that don't exist — you'll proceed and flag them, not block.

### Step 1: Establish the product frame

Read the inputs, then identify what they already settle and what they don't. The upstream artifacts almost never settle the product framing, so ask the user — a few questions per round, only for what you can't infer:

- **Goals & non-goals** — what success looks like at the product level, and what is explicitly out of scope for this round
- **Users & personas** — who this is for; the segments that matter
- **Success metrics** — how you'll know it worked (adoption, conversion, latency SLOs, support-ticket reduction — whatever fits)
- **Priorities & phasing** — what's must-have vs. later; rough release sequencing

If a dimension is already answered in the research or specs, use that and move on — don't re-ask.

### Step 2: Compile the requirements

Map the inputs into the PRD structure:

- **Functional requirements** — derive from the solution spec's capabilities. Preserve the capability identifiers (e.g. CAP-NN) so the PRD traces back cleanly.
- **Non-functional requirements** — derive from the technical spec (scale, performance, security, compliance, availability).
- **Key user flows** — from the solution spec's logic flows.
- **Technical considerations** — a short summary of the architecture and stack with a link to the technical spec, not a copy of it.

For any section with no upstream support, write what you can from the user conversation and mark it as a gap.

### Step 3: Produce the PRD

After 2-5 rounds (proportional to depth) or when the user is satisfied, write the PRD to a temporary file at `./prd/{slug}.md` using the format in [references/OUTPUT_FORMAT.md](references/OUTPUT_FORMAT.md). The slug derives from the project or feature name (lowercase, hyphens, max 60 chars). This is a working draft for handoff — saving it is the librarian skill's job.

Then tell the user:
- The PRD is ready, and which sections are well-supported vs. flagged as gaps
- Hand it off to the librarian skill to save it as the project PRD:
  ```bash
  python scripts/librarian.py prd write --title "Title" --file ./prd/{slug}.md \
    --tags "prd,..." --sources "researches/<slug>,specs/solution,specs/technical" --scope project
  ```
  If the librarian skill is unavailable, tell the user what to save and where so an agent with librarian access can persist it.

For real-world examples, see:
- [examples/file-upload-prd.md](examples/file-upload-prd.md) — single feature, some inputs missing (quick)
- [examples/subscription-billing-prd.md](examples/subscription-billing-prd.md) — product area, full inputs (standard)

## Depth Levels

Infer depth from the size of the inputs and the user's prompt, or ask:

- **quick** (2-3 question rounds): A single feature. Core sections; light on phasing. Default for one capability or a handful.
- **standard** (3-4 rounds): A product or feature area with several capabilities. Full PRD with metrics and a release plan.
- **deep** (4-5 rounds): An entire system or platform. Full PRD plus persona depth, phased milestones, and a richer risks/open-questions section.

## Important Guidelines

- **Trace everything.** A requirement with no source — upstream artifact or recorded product decision — is a red flag. Either find its source, get the user to make the call, or move it to open questions.
- **Gaps are information, not failures.** A PRD that honestly says "no success metrics defined yet — recommend a discovery pass" is more useful than one that invents plausible-sounding numbers. Flag, don't fabricate.
- **Synthesis, not transcription.** If the PRD is just the three inputs concatenated, you haven't done the job. The value is in the connective tissue: framing capabilities as requirements, tying them to goals and metrics, and sequencing them.
- **Stay in the product layer.** Don't redesign capabilities (solution-architect) or re-pick the stack (technical-architect). If you find yourself doing either, you've found a gap to send back, not work to do here.
- **No saving.** You write the draft; the librarian skill persists it as the project PRD. If the librarian skill isn't available, tell the user what to save and where.
