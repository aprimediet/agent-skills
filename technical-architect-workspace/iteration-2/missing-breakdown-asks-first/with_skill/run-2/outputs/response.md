Happy to design the technical architecture and pick a tech stack — but before I can do that well, I need one thing and a few quick constraints. My job is the technical *how*, and that only works if it's anchored to *what* the system actually does. Right now I don't have either the capability breakdown or a description of the app, so I'd be inventing both, which is exactly what this skill is built to avoid.

## 1. I need the capability breakdown first

I build the architecture on top of a capability/feature breakdown — ideally the one the **solution-architect** skill produces (the "what it does"). Every layer of the stack I recommend gets traced back to a specific capability, so nothing is unsupported and nothing is gratuitous.

**Do you have a capability or feature breakdown for this app** (for example, from the solution-architect skill) that I should build on?

- **If yes** — paste it here, or give me a path/file and I'll read it.
- **If no** — that's fine, but I'd strongly recommend running the **solution-architect** skill first. It will produce a much stronger, more honest architecture than me guessing at the capabilities. Alternatively, give me a few sentences describing the app and I'll infer a capability list to work from — but I'll flag those as *inferred* so the mapping stays honest.

### On retrieving it automatically

Normally I'd try to pull an existing breakdown via the **librarian** skill before asking you. **The librarian skill isn't available in this environment**, so I can't search the knowledge store myself.

If you're running an agent that *does* have librarian access, it could retrieve the breakdown with something like:

- **Category:** `specs`, scope `project`
- **Search keywords:** the app/feature name (e.g. `librarian.py search "<your app name>" --scope project`)
- **List:** `librarian.py list --category specs --scope project`

What it's looking for: the **capability-breakdown artifact** for this app. Once you paste it or point me at it, I'll take it from there.

## 2. A few constraints that actually change the recommendation

I keep this light — just the handful of questions that genuinely move the architecture, not an exhaustive questionnaire. While you're pulling the breakdown together, answers to these will let me give you sharp, opinionated calls instead of hedged ones:

1. **Scale & load** — roughly what are we designing for? A few hundred users, tens of thousands, millions? Any latency or availability targets you already know you need?
2. **Team** — what languages/frameworks does the team already know well, and how big is the team? (This often matters more than the "theoretically best" tech.)
3. **Hosting** — any cloud preference (AWS / GCP / Azure), an on-prem or data-residency requirement, or existing infrastructure I should build on?
4. **Hard constraints** — budget ceiling, compliance (HIPAA, PCI, GDPR, SOC 2…), or any must-use / must-avoid technologies?

If you don't know some of these yet, just say so and I'll proceed with clearly-labeled assumptions you can correct.

## What happens next

Once I have **(a)** the capability breakdown (pasted, pointed to, or generated via solution-architect) and **(b)** rough answers to the four questions above, I'll produce a full technical architecture: architecture style, a layer-by-layer tech stack (frontend through infrastructure, observability, and security) with one opinionated recommendation plus alternatives per layer, a capability-to-tech mapping, key decisions, risks, and any high-stakes choices flagged for the researcher skill.

(Note: I don't persist the result myself — saving it is the librarian skill's job. Since the librarian skill isn't available here, once the architecture is done I'll tell you exactly what to save and where so it can be persisted later.)
