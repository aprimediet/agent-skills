Happy to design the technical architecture and pick a stack — but before I can do that well, I need to anchor it to **what the app actually does**. I design the *how* (architecture style + tech stack); the *what* (the capabilities and features) comes first, and every technical choice should trace back to a specific capability. Without that I'd be guessing at an unspecified app, which isn't useful to you.

So a couple of things to get us unblocked.

## 1. I need the capability breakdown

Do you have a capability or feature breakdown for this app — ideally from the **solution-architect** skill — that I should build on?

- **If yes:** paste it here, or point me to a path/file and I'll work from it.
- **If no:** I'd recommend running the **solution-architect** skill first to produce one. It'll give us a clean list of capabilities (what the system must do), and I'll turn that into the architecture and stack. You *can* also just describe the app in a few sentences and I'll infer a working capability list — but I'll flag those as inferred, and a real breakdown will produce a noticeably stronger architecture.

### A note on retrieval

Normally I'd try to pull an existing breakdown automatically via the **librarian** skill (searching saved `specs` artifacts for this project). **That skill isn't available in this session**, so I can't retrieve it myself — I need you to provide it directly.

> If you're running this in an environment where the librarian skill *is* available, an agent could fetch the breakdown with something like: `librarian search "<your app keywords>" --scope project` or `librarian list --category specs --scope project`. Here, please just paste it or give me a path.

## 2. The few constraints that actually change the design

While you're grabbing the breakdown, answering these will let me make sharp, opinionated calls instead of hedged ones. These are the high-leverage ones — I'm deliberately not running a long questionnaire:

1. **Scale & load** — roughly what are we designing for: a few hundred users, tens of thousands, or millions? Any hard latency or availability targets?
2. **Team** — what languages/frameworks does your team already know well, and how big is the team? (This often matters more than any "best" technology.)
3. **Hosting** — any cloud preference (AWS / GCP / Azure), an on-prem/self-host requirement, or existing infrastructure I should fit into?
4. **Hard constraints** — budget ceiling, compliance (HIPAA / PCI / GDPR / SOC 2), data-residency requirements, or any must-use or must-avoid technologies?

## What happens next

Once I have **(a)** the capability breakdown (or your short description) and **(b)** answers to whichever of the four constraints apply, I'll produce:

- an **architecture style** (e.g. modular monolith vs. microservices vs. serverless) with the rationale,
- a **layer-by-layer tech stack** — frontend, backend/API, data, async/messaging, auth, hosting, CI/CD, observability, integrations, security — each with one clear recommendation, the reasoning, and 1-2 alternatives,
- a **capability → technology mapping** so nothing is unsupported and nothing is gratuitous,
- **key decisions, risks, and any high-stakes choices I'd flag for deeper research.**

I won't fabricate any of that for an unspecified app — give me the breakdown (or a sketch) plus those constraints and I'll get to work.
