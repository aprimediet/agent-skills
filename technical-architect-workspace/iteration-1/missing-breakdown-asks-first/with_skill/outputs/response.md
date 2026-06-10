# Before I design the architecture, I need the capability breakdown

I'm the technical architect. I decide the **how** — architecture style and tech stack — by building on a **capability breakdown** that says **what** the app does. Right now I have neither the breakdown nor a description of the app ("my app" is unspecified), so designing a stack now would mean inventing your product for you. That's the solution-architect's job, not mine, and a fabricated stack would be unanchored guesswork. So my first step is to get the breakdown.

## 1. Do you have a capability breakdown?

Do you have a capability or feature breakdown for this app (for example, from the **solution-architect** skill) that I should build on?

- **If yes** — paste it here or give me a file path.
- **If no** — I'd recommend running the **solution-architect** skill first to produce one; it makes for a much stronger, fully-traceable architecture. I *can* proceed from a plain-English description of the app if you'd rather move fast, but I'll have to capture the capabilities I infer so the mapping stays honest.

## 2. I tried to retrieve it automatically — couldn't

Normally I'd try to pull a saved breakdown via the **librarian** skill before asking you. **The librarian skill is not available in this run**, so I can't retrieve it myself.

If you (or an agent) have librarian access, here's what to retrieve and how:

- **Category**: `specs`
- **Scope**: `project`
- **Keywords**: the app/feature name plus its domain (I can't pick precise keywords yet because the app is unspecified — once you name it, e.g. "file upload", "subscription billing", I'll give you the exact query).
- **Commands an agent with librarian access could run**:
  ```bash
  python scripts/librarian.py search "{app/feature keywords}" --scope project
  python scripts/librarian.py list --category specs --scope project
  ```
- **What to look for**: the capability-breakdown artifact for this app (the `CAP-NN` list).

## 3. While you grab the breakdown — four constraint questions

These are the only constraints that actually change my recommendation. Quick answers are fine; "don't know / no preference" is a valid answer and I'll state a sensible default.

1. **Scale & load** — roughly how many users/traffic are we designing for, and any growth, latency, or availability targets? (a few hundred internal users vs. millions of public users pushes very different architectures)
2. **Team** — what languages/frameworks does your team already know, and how big is the team? (I bias toward what you can actually maintain)
3. **Hosting** — any cloud preference (AWS / GCP / Azure), on-prem requirement, or existing infrastructure I should fit into?
4. **Hard constraints** — budget ceiling, compliance (HIPAA, PCI, GDPR, SOC 2, data residency), or any must-use / must-avoid technologies?

## What happens next

Once I have **(a)** the capability breakdown or an app description, and **(b)** your answers to whichever of the four questions apply, I'll produce a full technical architecture: architecture style, a layer-by-layer opinionated tech stack (each with reasoning and alternatives), a capability→tech mapping, key decisions, risks, and any high-stakes choices flagged for the researcher skill. I'll write it as a working draft and hand it to the librarian skill to persist (or, if the librarian skill stays unavailable, tell you exactly what to save and where).

---
*No architecture was generated because the app and its capabilities are unspecified — designing one now would invent your product rather than architect it. This response gathers the inputs first, per the technical-architect skill's Step 0.*
