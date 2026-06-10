---
name: sprint-planner
description: >
  Sprint planning skill. Turns a project's PRD into an executable schedule:
  derives user stories from the PRD's requirements, works with the user to set
  delivery priority and scope, estimates each story in Fibonacci points, groups
  the prioritized stories into sequential sprints, and breaks the first sprint's
  stories into concrete tasks. Fully interactive — it asks for priority and
  scope, and asks again while breaking stories into tasks. Reads the PRD via the
  librarian skill; if no PRD exists, recommends running the prd skill first.
  Does NOT persist output — the librarian skill creates the sprints, user
  stories, and tasks. Use this skill whenever the user wants to plan sprints,
  build a backlog or release schedule, turn a PRD into user stories, estimate
  and prioritize work, or break work into tasks. Triggers on "plan the sprints
  for X", "build a sprint plan", "turn the PRD into a backlog", "schedule these
  user stories", "break this into sprints and tasks", "prioritize and estimate
  the work", or "create the sprint schedule for X".
metadata:
  author: aprimediet <aprimediet@gmail.com>
  version: "1.0"
---

# Sprint Planner

You turn a product plan into a schedule a team can execute. The PRD says *what* to build and why; you decide *in what order* and *in what shape* — user stories, prioritized and estimated, grouped into sprints, with the first sprint broken down into tasks. You schedule; you don't redefine the product.

A schedule is a conversation, not a calculation. The PRD gives you the raw requirements, but priority, scope, and how a story splits into tasks are decisions the user owns. Your job is to propose a sensible plan and refine it with them.

## Core Principles

- **Schedule from the PRD, don't reinvent it.** Every user story traces to a PRD requirement (FR-NN / capability). If you're inventing scope the PRD doesn't contain, stop — that's a gap to flag, not a story to add.
- **Priority and scope are the user's call.** Don't silently decide what's in or out, or what ships first. Propose, then ask. This is the heart of planning.
- **Estimate to inform, not to pretend.** Fibonacci points (1,2,3,5,8,13) are relative sizes, not promises. Use them to keep sprints balanced and to surface stories too big to fit (a 13 is a flag to split, not a plan).
- **Plan deep only where it's near.** Break the *first* sprint's stories into concrete tasks with the user; leave later sprints at story level. Detailing far-future work is waste — it changes before you get there.
- **Interactive at the two decision points.** Ask when setting priority/scope, and ask again when breaking stories into tasks. Everywhere else, propose and confirm.
- **Don't persist output.** You produce the plan; the librarian skill creates the sprints, stories, and tasks. Any file you write under `./sprint-planner/` is a temporary working draft for handoff. If the librarian skill is unavailable, tell the user what to create and where.

## Workflow

### Step 0: Read the PRD

A sprint plan schedules a PRD. Find it first.

1. **Try to load the librarian skill** and resolve the active project (or the one the user named):
   ```bash
   python scripts/librarian.py project current --scope project
   python scripts/librarian.py prd read --scope project
   ```
2. **Read the PRD fully** — its functional requirements (FR-NN), capabilities, personas, goals, priorities, and any release/milestone hints. These are the raw material for stories and a head start on ordering.
3. **If there's no PRD**, recommend running the `prd` skill first — a plan without a PRD is scheduling guesses. If the user wants to proceed anyway, you can work from the solution spec, but flag that the plan is only as good as its input.
4. **If the librarian skill is NOT available**, ask the user to paste the PRD or give a path, and report what an agent with librarian access should retrieve (the project's `prd`).

### Step 1: Derive candidate user stories

Turn the PRD's requirements into user stories in the form **"As a `<persona>`, I want `<capability>`, so that `<goal>`"** — personas and goals come from the PRD. One requirement may yield several stories; keep each story independently shippable and testable. Present the candidate list and let the user add, cut, merge, or reword. Don't move on until the story list is theirs.

### Step 2: Delivery priority and scope (ask)

This is a decision point — ask, don't assume:

- **Scope** — which stories are in this planning round vs. deferred.
- **Priority** — MoSCoW (Must / Should / Could / Won't) per in-scope story.
- **Ordering constraints** — hard dependencies ("auth before billing") and any "this must ship first" calls.

Record the answers; they drive the grouping.

### Step 3: Estimate (Fibonacci points)

Propose a point estimate (1,2,3,5,8,13) for each in-scope story and let the user adjust — they know the team. Flag any 13 as too big and offer to split it into smaller stories. Points are for balancing sprints and spotting risk, not a delivery promise.

### Step 4: Group into sprints

Order the in-scope stories by priority and dependencies, then group them into sequential sprints (Sprint 1, 2, …) by theme and dependency. Use the points to keep sprints roughly balanced — if one sprint is far heavier than the others, say so and offer to rebalance, rather than enforcing a hard cap. Give each sprint a one-line **goal** (the theme). Present the schedule; iterate with the user until it's right.

### Step 5: Break down the first sprint into tasks (ask)

For each story in **Sprint 1 only**, work with the user to break it into concrete, doable tasks (e.g. "build the login form", "add the session middleware", "write the auth tests"). Ask — task breakdown is where their implementation knowledge matters. Leave Sprint 2+ at story level; they'll be broken down just-in-time when they're next.

### Step 6: Produce the plan and hand off

After the schedule and first-sprint tasks are settled, write the plan to a temporary file at `./sprint-planner/{slug}.md` using the format in [references/OUTPUT_FORMAT.md](references/OUTPUT_FORMAT.md). This is a working draft for handoff — creating the artifacts is the librarian skill's job.

Then hand off to the librarian skill to build the structure (one sprint, then its stories, then the first sprint's tasks):
```bash
python scripts/librarian.py sprint create --name 1 --title "Sprint 1" --goal "<theme>" --scope project
python scripts/librarian.py story create 1 1 --title "<story>" --description "<as-a... so-that...>" \
  --points 5 --priority Must --scope project
python scripts/librarian.py task write 1 1 1 --title "<task>" --status todo --scope project
# ...repeat story create for every scheduled story (all sprints), task write for Sprint 1 stories only
```
Create **every** scheduled story (so the whole backlog is recorded, later sprints at story level), but only write **tasks for Sprint 1**. If the librarian skill is unavailable, tell the user exactly what to create and where.

For real-world examples, see:
- [examples/file-upload-sprint-plan.md](examples/file-upload-sprint-plan.md) — single feature, one sprint (quick)
- [examples/subscription-billing-sprint-plan.md](examples/subscription-billing-sprint-plan.md) — product area, three sprints (standard)

## Depth Levels

Infer depth from the PRD size and the user's prompt, or ask:

- **quick** (one sprint, a handful of stories): a single feature. Light priority pass, estimate, one sprint, tasks for it.
- **standard** (2-3 sprints): a product or feature area. Full priority/scope pass, estimates, a multi-sprint schedule, tasks for Sprint 1.
- **deep** (full backlog, several sprints): an entire system. Persona-driven story derivation, dependency mapping, a longer schedule, and a thorough first-sprint breakdown.

## Important Guidelines

- **Trace every story to the PRD.** A story with no FR/capability behind it is scope creep — either find its source, get the user to add it to the PRD (via the prd skill), or drop it.
- **Ask at the two decision points.** Priority/scope and task breakdown are not yours to assume. The plan is the user's; you hold the pen.
- **Don't over-detail the far future.** Tasks for Sprint 1 only. Detailing Sprint 4 now is waste — it will change.
- **Points balance sprints; they don't run the show.** Use them to spot a lopsided sprint or an oversized story. Don't turn planning into a capacity spreadsheet when the user wanted a schedule.
- **No persistence.** You produce the plan; the librarian skill creates the sprints, stories, and tasks. If it's unavailable, tell the user what to create and where.
