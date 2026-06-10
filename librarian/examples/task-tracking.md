<!-- Example: how sprint / user-story / task tracking looks in the new layout.
     Tasks live at: projects/<proj>/sprints/sprint-N/us-XXX/us-XXX-task-XXX.md
     This file shows a single task artifact plus the indexes that reference it. -->

## A task file — `sprints/sprint-1/us-001/us-001-task-001.md`

```markdown
---
title: Implement JWT refresh token rotation
type: task
id: us-001-task-001
status: in-progress
created: 2026-06-07T14:00:00Z
updated: 2026-06-07T16:30:00Z
---

Rotate refresh tokens on every use; invalidate the prior token.

- [ ] Issue new refresh token on `/auth/refresh`
- [ ] Revoke the consumed token
- [ ] Add replay-detection test
```

Written via:

```bash
python scripts/librarian.py task write 1 1 1 \
  --title "Implement JWT refresh token rotation" \
  --status in-progress --file /tmp/task.md
python scripts/librarian.py task status 1 1 1 done   # later
```

## The user-story index it rolls up into — `us-001/index.md`

Your prose stays above the marker; the task list below is regenerated on each task change:

```markdown
---
title: Authentication flow
type: user_story
id: us-001
status: in-progress
created: 2026-06-07T14:00:00Z
updated: 2026-06-07T16:30:00Z
---

# US-001 · Authentication flow

As a user I can sign in and stay signed in securely.

## Acceptance Criteria
- Refresh tokens rotate on use
- Sessions expire after 30 days idle

<!-- LIBRARIAN:AUTO:BEGIN — regenerated; edit above this line -->

## Tasks (2)

- [Implement JWT refresh token rotation](us-001-task-001.md) — `in-progress`
- [Fix pagination bug in /users endpoint](us-001-task-002.md) — `todo`

<!-- LIBRARIAN:AUTO:END -->
```

## The sprint index above that — `sprint-1/index.md`

```markdown
# sprint-1

Goal: complete auth flow + fix Sprint-0 criticals.

<!-- LIBRARIAN:AUTO:BEGIN — regenerated; edit above this line -->

## User Stories (1)

- [us-001 · Authentication flow](us-001/index.md) — `in-progress` · 2 task(s)

<!-- LIBRARIAN:AUTO:END -->
```

Status flows upward automatically: change a task → the story index updates → the sprint index updates → the project index updates.
