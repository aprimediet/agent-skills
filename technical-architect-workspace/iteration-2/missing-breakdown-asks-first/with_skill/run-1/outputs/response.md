Happy to design the technical architecture and pick a stack — but I need one thing first, and I shouldn't guess at it.

## I need the capability breakdown first

I design the **how** (architecture style + tech stack), and every technical choice has to trace back to a **capability** — the *what* the system does. Right now I don't have that, and the app itself is unspecified, so there's nothing concrete to architect against. Designing a full stack for an unknown app would mean inventing both the features and the technology, and the inventing-features part isn't my job (that's the solution-architect skill's).

So before I design anything:

**1. Do you already have a capability or feature breakdown for this app** — for example, from the solution-architect skill? If so, paste it here or point me to a path/file.

**2. I'd normally retrieve it for you via the librarian skill, but it isn't available in this session.** Degrading gracefully: please provide the breakdown directly. If you later run this through an agent that *does* have librarian access, it could retrieve the breakdown automatically with something like:

> Search the **specs** category (scope: project) for the capability breakdown matching this app's name / domain keywords, then hand it to the technical-architect skill.

**3. If no breakdown exists yet, the strongest path is to run the solution-architect skill first** to produce the capability breakdown (the CAP-NN list), then bring that back here. I *can* proceed from a plain description of the app instead, but I'll have to infer the capabilities myself, and I'll flag every inferred one so the mapping stays honest — it's a weaker foundation than a real breakdown.

## A few high-leverage constraints (so I only ask once)

These are the questions that actually change the recommendation. If you can answer them alongside the breakdown, I can go straight to a design:

- **Scale & load** — roughly how many users/traffic are we designing for: a few hundred, tens of thousands, millions? Any latency or availability targets?
- **Team** — what languages/frameworks does your team already know, and how big is the team? (This often matters more than any "best" technology.)
- **Hosting** — any cloud preference (AWS / GCP / Azure), on-prem requirement, or existing infrastructure I should build on?
- **Hard constraints** — budget ceiling, compliance (HIPAA, PCI, GDPR, SOC 2…), data residency, or any must-use / must-avoid technologies?

## What happens next

Once I have **(a)** the capability breakdown (or your go-ahead to infer it from a description) and **(b)** answers to whichever constraints apply, I'll produce a comprehensive, layer-by-layer technical architecture: architecture style, a tech stack with one opinionated recommendation per layer (plus alternatives and rationale), a capability-to-tech mapping, key decisions, risks, and any high-stakes choices I'd flag for deeper research.

To be explicit: I'm **not** producing an architecture yet, because doing so for an unspecified app would mean fabricating both the requirements and the stack. Send me the breakdown (or a description + your go-ahead) and the constraints, and I'll build it properly.
