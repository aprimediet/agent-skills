#!/usr/bin/env python3
"""Librarian — Project-first artifact management for agent knowledge.

Everything is organized under a single project. A project bundles the
research, specifications, and sprint/user-story/task tracking that belong
together:

    projects/
    ├── index.md                              # all-projects index
    ├── .librarian/current                     # active-project pointer
    └── YYYY_MM_DD_<slug>/                      # one directory per project
        ├── index.md                           # project index
        ├── researches/
        │   ├── index.md
        │   └── YYYY_MM_DD_<slug>.md
        ├── specs/
        │   ├── index.md
        │   ├── technical.md                   # technical spec
        │   ├── solution.md                    # solution (non-technical) spec
        │   ├── api-design.md
        │   └── design.md                      # visual design
        └── sprints/
            ├── index.md                       # all sprints + status
            └── sprint-1/
                ├── index.md                   # sprint index
                └── us-001/
                    ├── index.md               # user story + task statuses
                    └── us-001-task-001.md

Most commands operate on the *active* project (set via `project use` or by
creating one). Pass `--project <slug>` to any command to override.

All commands output JSON for easy parsing by agents.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_SUBDIRS = ["researches", "specs", "sprints"]
SPEC_TYPES = ["technical", "solution", "api-design", "design"]

AUTO_BEGIN = "<!-- LIBRARIAN:AUTO:BEGIN — regenerated; edit above this line -->"
AUTO_END = "<!-- LIBRARIAN:AUTO:END -->"

DATE_RE = re.compile(r"^(\d{4}_\d{2}_\d{2})_(.+)$")
RESEARCH_FILE_RE = re.compile(r"^\d{4}_\d{2}_\d{2}_(.+)\.md$")

# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------


def _slugify(text: str) -> str:
    """Convert text to a URL-friendly slug: lowercase, hyphens, max 60 chars."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    text = text.strip("-")
    return text[:60]


def _now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today_prefix() -> str:
    """Return today's date as YYYY_MM_DD."""
    return datetime.now(timezone.utc).strftime("%Y_%m_%d")


def _output(data: dict) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def _error(msg: str) -> None:
    _output({"error": msg})
    sys.exit(1)


def _get_base_dir(scope: str) -> Path:
    """Return the base projects directory for the given scope."""
    if scope == "global":
        agent_root = os.environ.get("AGENT_ROOT", os.path.expanduser("~/.agents"))
        return Path(agent_root) / "projects"
    return Path.cwd() / "projects"


def _parse_frontmatter(content: str) -> Tuple[Dict[str, str], str]:
    """Parse YAML frontmatter. Returns (metadata_dict, body)."""
    if not content.startswith("---"):
        return {}, content
    end = content.find("\n---", 3)
    if end == -1:
        return {}, content
    fm_text = content[3:end].strip()
    body = content[end + 4:].lstrip("\n")
    meta: Dict[str, str] = {}
    for line in fm_text.splitlines():
        line = line.strip()
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    return meta, body


def _build_frontmatter(meta: Dict[str, object]) -> str:
    """Build a frontmatter block from an ordered dict. Lists render as JSON arrays."""
    lines = ["---"]
    for key, value in meta.items():
        if isinstance(value, list):
            value = "[" + ", ".join(f'"{v}"' for v in value) + "]"
        lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def _read_meta(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    meta, _ = _parse_frontmatter(path.read_text(encoding="utf-8"))
    return meta


def _read_tags(meta: Dict[str, str]) -> List[str]:
    try:
        return json.loads(meta.get("tags", "[]"))
    except (json.JSONDecodeError, TypeError):
        return []


def _resolve_content(args) -> str:
    """Resolve content from --file, --content, or stdin."""
    if getattr(args, "file", None):
        return Path(args.file).read_text(encoding="utf-8")
    if getattr(args, "content", None):
        return args.content
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return ""


def _replace_auto_section(path: Path, auto_lines: List[str]) -> None:
    """Regenerate the auto-maintained block of an entity index, preserving
    everything the user authored above it."""
    block = AUTO_BEGIN + "\n\n" + "\n".join(auto_lines).rstrip() + "\n\n" + AUTO_END + "\n"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if AUTO_BEGIN in text and AUTO_END in text:
        pre = text[: text.index(AUTO_BEGIN)]
        post = text[text.index(AUTO_END) + len(AUTO_END):]
        text = pre.rstrip("\n") + "\n\n" + block + post.lstrip("\n")
    else:
        if text and not text.endswith("\n"):
            text += "\n"
        text = text.rstrip("\n") + "\n\n" + block
    path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Active-project pointer
# ---------------------------------------------------------------------------


def _pointer_path(base: Path) -> Path:
    return base / ".librarian" / "current"


def _get_active(base: Path) -> Optional[str]:
    p = _pointer_path(base)
    if p.exists():
        name = p.read_text(encoding="utf-8").strip()
        if name and (base / name).is_dir():
            return name
    return None


def _set_active(base: Path, dirname: str) -> None:
    p = _pointer_path(base)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(dirname, encoding="utf-8")


# ---------------------------------------------------------------------------
# Project / id resolution
# ---------------------------------------------------------------------------


def _project_slug(dirname: str) -> str:
    m = DATE_RE.match(dirname)
    return m.group(2) if m else dirname


def _iter_project_dirs(base: Path) -> List[Path]:
    if not base.is_dir():
        return []
    return [
        e for e in sorted(base.iterdir())
        if e.is_dir() and not e.name.startswith(".") and DATE_RE.match(e.name)
    ]


def _find_project_dir(base: Path, project: str) -> Optional[Path]:
    """Resolve a project by full directory name or by its short slug."""
    cand = base / project
    if cand.is_dir():
        return cand
    target = _slugify(project)
    for entry in _iter_project_dirs(base):
        if _project_slug(entry.name) == target or entry.name.endswith(f"_{target}"):
            return entry
    return None


def _resolve_project_dir(base: Path, project_arg: Optional[str], required: bool = True) -> Optional[Path]:
    if project_arg:
        d = _find_project_dir(base, project_arg)
        if d:
            return d
        if required:
            _error(f"Project not found: {project_arg}. Create it with 'project create {project_arg}'.")
        return None
    active = _get_active(base)
    if active:
        return base / active
    if required:
        _error("No active project. Run 'project use <slug>' or pass --project <slug>.")
    return None


def _norm_sprint(name: str) -> str:
    m = re.search(r"(\d+)", name)
    return f"sprint-{int(m.group(1))}" if m else _slugify(name)


def _norm_us(us_id: str) -> str:
    m = re.search(r"(\d+)", us_id)
    return f"us-{int(m.group(1)):03d}" if m else _slugify(us_id)


def _norm_task_num(task_id: str) -> str:
    m = re.search(r"(\d+)", task_id)
    return f"{int(m.group(1)):03d}" if m else _slugify(task_id)


# ---------------------------------------------------------------------------
# Index rebuilders
# ---------------------------------------------------------------------------


def _rebuild_projects_index(base: Path) -> None:
    lines = [
        "# Projects",
        "",
        "> Auto-generated by librarian. Lists every project in this scope.",
        "",
    ]
    rows = []
    for entry in _iter_project_dirs(base):
        meta = _read_meta(entry / "index.md")
        title = meta.get("title", _project_slug(entry.name))
        status = meta.get("status", "active")
        created = meta.get("created", "")[:10]
        rows.append((entry.name, title, status, created))
    active = _get_active(base)
    for dirname, title, status, created in sorted(rows, reverse=True):
        marker = " ⭐" if dirname == active else ""
        lines.append(f"- [{title}]({dirname}/index.md) — `{status}` · {created}{marker}")
    if not rows:
        lines.append("_No projects yet. Create one with `project create <name>`._")
    (base / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _rebuild_research_index(proj: Path) -> None:
    rd = proj / "researches"
    rd.mkdir(parents=True, exist_ok=True)
    lines = ["# Researches", "", "> Auto-generated by librarian.", ""]
    files = [f for f in sorted(rd.glob("*.md"), reverse=True) if f.name != "index.md"]
    for f in files:
        meta = _read_meta(f)
        title = meta.get("title", f.stem)
        date = meta.get("created", "")[:10]
        tags = " ".join(f"`{t}`" for t in _read_tags(meta))
        lines.append(f"- [{title}]({f.name}) — {date} {tags}".rstrip())
    if not files:
        lines.append("_No research yet._")
    (rd / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _rebuild_spec_index(proj: Path) -> None:
    sd = proj / "specs"
    sd.mkdir(parents=True, exist_ok=True)
    lines = ["# Specs", "", "> Auto-generated by librarian.", ""]
    files = [f for f in sorted(sd.glob("*.md")) if f.name != "index.md"]
    # Show known types first in a stable order, then any extras.
    ordered = [f"{t}.md" for t in SPEC_TYPES if (sd / f"{t}.md").exists()]
    extras = [f.name for f in files if f.name not in ordered]
    for name in ordered + extras:
        meta = _read_meta(sd / name)
        title = meta.get("title", name[:-3].replace("-", " ").title())
        date = meta.get("updated", meta.get("created", ""))[:10]
        lines.append(f"- [{title}]({name}) — {date}".rstrip())
    if not (ordered or extras):
        lines.append("_No specs yet._")
    (sd / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _iter_sprints(proj: Path) -> List[Path]:
    sd = proj / "sprints"
    if not sd.is_dir():
        return []
    dirs = [e for e in sd.iterdir() if e.is_dir() and e.name.startswith("sprint-")]
    return sorted(dirs, key=lambda d: int(re.search(r"(\d+)", d.name).group(1)) if re.search(r"(\d+)", d.name) else 0)


def _iter_stories(sprint: Path) -> List[Path]:
    dirs = [e for e in sprint.iterdir() if e.is_dir() and e.name.startswith("us-")]
    return sorted(dirs, key=lambda d: int(re.search(r"(\d+)", d.name).group(1)) if re.search(r"(\d+)", d.name) else 0)


def _iter_tasks(story: Path) -> List[Path]:
    files = [f for f in story.glob("*-task-*.md")]
    return sorted(files, key=lambda f: int(re.search(r"task-(\d+)", f.name).group(1)) if re.search(r"task-(\d+)", f.name) else 0)


def _rebuild_story(story: Path) -> None:
    tasks = _iter_tasks(story)
    lines = [f"## Tasks ({len(tasks)})", ""]
    for t in tasks:
        meta = _read_meta(t)
        title = meta.get("title", t.stem)
        status = meta.get("status", "todo")
        lines.append(f"- [{title}]({t.name}) — `{status}`")
    if not tasks:
        lines.append("_No tasks yet._")
    _replace_auto_section(story / "index.md", lines)


def _rebuild_sprint(sprint: Path) -> None:
    stories = _iter_stories(sprint)
    lines = [f"## User Stories ({len(stories)})", ""]
    for s in stories:
        meta = _read_meta(s / "index.md")
        title = meta.get("title", s.name)
        status = meta.get("status", "todo")
        ntasks = len(_iter_tasks(s))
        lines.append(f"- [{s.name} · {title}]({s.name}/index.md) — `{status}` · {ntasks} task(s)")
    if not stories:
        lines.append("_No user stories yet._")
    _replace_auto_section(sprint / "index.md", lines)


def _rebuild_sprints_index(proj: Path) -> None:
    sd = proj / "sprints"
    sd.mkdir(parents=True, exist_ok=True)
    sprints = _iter_sprints(proj)
    lines = ["# Sprints", "", "> Auto-generated by librarian.", ""]
    for s in sprints:
        meta = _read_meta(s / "index.md")
        status = meta.get("status", "planned")
        goal = meta.get("goal", "")
        nstories = len(_iter_stories(s))
        suffix = f" — {goal}" if goal else ""
        lines.append(f"- [{s.name}]({s.name}/index.md) — `{status}` · {nstories} story(ies){suffix}")
    if not sprints:
        lines.append("_No sprints yet._")
    (sd / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _rebuild_project_index(proj: Path) -> None:
    researches = [f for f in (proj / "researches").glob("*.md") if f.name != "index.md"] if (proj / "researches").is_dir() else []
    specs = [f for f in (proj / "specs").glob("*.md") if f.name != "index.md"] if (proj / "specs").is_dir() else []
    sprints = _iter_sprints(proj)

    lines = ["## Contents", ""]
    lines.append(f"- **[Researches](researches/index.md)** — {len(researches)} item(s)")
    spec_names = ", ".join(sorted(f.stem for f in specs)) if specs else "none"
    lines.append(f"- **[Specs](specs/index.md)** — {spec_names}")
    lines.append(f"- **[Sprints](sprints/index.md)** — {len(sprints)} sprint(s)")
    if sprints:
        lines.append("")
        for s in sprints:
            meta = _read_meta(s / "index.md")
            status = meta.get("status", "planned")
            lines.append(f"  - [{s.name}](sprints/{s.name}/index.md) — `{status}`")
    _replace_auto_section(proj / "index.md", lines)


def _rebuild_all(base: Path, proj: Path) -> None:
    """Rebuild every index for a project plus the top-level projects index."""
    _rebuild_research_index(proj)
    _rebuild_spec_index(proj)
    for sprint in _iter_sprints(proj):
        for story in _iter_stories(sprint):
            _rebuild_story(story)
        _rebuild_sprint(sprint)
    _rebuild_sprints_index(proj)
    _rebuild_project_index(proj)
    _rebuild_projects_index(base)


# ---------------------------------------------------------------------------
# Commands — setup & projects
# ---------------------------------------------------------------------------


def cmd_init(args) -> None:
    base = _get_base_dir(args.scope)
    base.mkdir(parents=True, exist_ok=True)
    (base / ".librarian").mkdir(parents=True, exist_ok=True)
    _rebuild_projects_index(base)
    _output({
        "action": "init",
        "scope": args.scope,
        "base": str(base),
        "index": str(base / "index.md"),
    })


def cmd_project_create(args) -> None:
    base = _get_base_dir(args.scope)
    raw = args.slug
    if DATE_RE.match(raw):
        dirname = raw
        slug = _project_slug(raw)
    else:
        slug = _slugify(raw)
        dirname = f"{_today_prefix()}_{slug}"

    existing = _find_project_dir(base, slug)
    if existing:
        _set_active(base, existing.name)
        _rebuild_projects_index(base)
        _output({
            "action": "project_create",
            "status": "already_exists",
            "project": existing.name,
            "path": str(existing),
            "active": True,
        })
        return

    proj = base / dirname
    for sub in PROJECT_SUBDIRS:
        (proj / sub).mkdir(parents=True, exist_ok=True)

    now = _now_iso()
    title = args.title or slug.replace("-", " ").title()
    fm = _build_frontmatter({
        "title": title,
        "type": "project",
        "slug": slug,
        "status": args.status or "active",
        "created": now,
        "updated": now,
        "scope": args.scope,
    })
    body = (args.description or "_Describe this project here._") + "\n"
    (proj / "index.md").write_text(fm + f"# {title}\n\n{body}\n", encoding="utf-8")

    _set_active(base, dirname)
    _rebuild_all(base, proj)
    _output({
        "action": "project_create",
        "status": "created",
        "project": dirname,
        "slug": slug,
        "title": title,
        "path": str(proj),
        "active": True,
        "scope": args.scope,
    })


def cmd_project_list(args) -> None:
    base = _get_base_dir(args.scope)
    active = _get_active(base)
    projects = []
    for entry in _iter_project_dirs(base):
        meta = _read_meta(entry / "index.md")
        projects.append({
            "project": entry.name,
            "slug": _project_slug(entry.name),
            "title": meta.get("title", _project_slug(entry.name)),
            "status": meta.get("status", "active"),
            "created": meta.get("created", ""),
            "active": entry.name == active,
            "path": str(entry),
        })
    _output({"action": "project_list", "scope": args.scope, "active": active,
             "count": len(projects), "projects": projects})


def cmd_project_use(args) -> None:
    base = _get_base_dir(args.scope)
    proj = _find_project_dir(base, args.slug)
    if not proj:
        _error(f"Project not found: {args.slug}")
    _set_active(base, proj.name)
    _rebuild_projects_index(base)
    _output({"action": "project_use", "active": proj.name, "path": str(proj), "scope": args.scope})


def cmd_project_show(args) -> None:
    base = _get_base_dir(args.scope)
    proj = _resolve_project_dir(base, args.project)
    index = proj / "index.md"
    _output({
        "action": "project_show",
        "project": proj.name,
        "path": str(index),
        "content": index.read_text(encoding="utf-8") if index.exists() else "",
    })


def cmd_project_current(args) -> None:
    base = _get_base_dir(args.scope)
    active = _get_active(base)
    _output({"action": "project_current", "active": active,
             "path": str(base / active) if active else None})


def cmd_project_status(args) -> None:
    base = _get_base_dir(args.scope)
    proj = _resolve_project_dir(base, args.project)
    _update_frontmatter(proj / "index.md", {"status": args.status})
    _rebuild_projects_index(base)
    _output({"action": "project_status", "project": proj.name, "status": args.status})


# ---------------------------------------------------------------------------
# Commands — research
# ---------------------------------------------------------------------------


def _find_research(proj: Path, slug: str) -> Optional[Path]:
    rd = proj / "researches"
    if not rd.is_dir():
        return None
    for f in sorted(rd.glob("*.md")):
        m = RESEARCH_FILE_RE.match(f.name)
        if m and m.group(1) == slug:
            return f
    return None


def cmd_research_write(args) -> None:
    base = _get_base_dir(args.scope)
    proj = _resolve_project_dir(base, args.project)
    slug = _slugify(args.slug)
    existing = _find_research(proj, slug)
    path = existing or (proj / "researches" / f"{_today_prefix()}_{slug}.md")
    path.parent.mkdir(parents=True, exist_ok=True)

    content = _resolve_content(args)
    now = _now_iso()
    old_meta = _read_meta(path) if existing else {}
    created = old_meta.get("created", now)
    if existing and not content:
        _, content = _parse_frontmatter(path.read_text(encoding="utf-8"))
    tags = args.tags.split(",") if args.tags else _read_tags(old_meta)
    title = args.title or old_meta.get("title") or slug.replace("-", " ").title()

    fm = _build_frontmatter({
        "title": title, "type": "research", "slug": slug,
        "created": created, "updated": now, "tags": tags, "scope": args.scope,
    })
    path.write_text(fm + content, encoding="utf-8")
    _rebuild_research_index(proj)
    _rebuild_project_index(proj)
    _output({"action": "research_write", "project": proj.name, "slug": slug,
             "title": title, "path": str(path), "tags": tags})


def cmd_research_read(args) -> None:
    base = _get_base_dir(args.scope)
    proj = _resolve_project_dir(base, args.project)
    path = _find_research(proj, _slugify(args.slug))
    if not path:
        _error(f"Research not found: {args.slug} in {proj.name}")
    meta, body = _parse_frontmatter(path.read_text(encoding="utf-8"))
    _output({"action": "research_read", "project": proj.name, "path": str(path),
             "meta": meta, "body": body})


def cmd_research_list(args) -> None:
    base = _get_base_dir(args.scope)
    proj = _resolve_project_dir(base, args.project)
    rd = proj / "researches"
    items = []
    if rd.is_dir():
        for f in sorted(rd.glob("*.md"), reverse=True):
            if f.name == "index.md":
                continue
            meta = _read_meta(f)
            m = RESEARCH_FILE_RE.match(f.name)
            items.append({
                "slug": m.group(1) if m else f.stem,
                "title": meta.get("title", f.stem),
                "created": meta.get("created", ""),
                "tags": _read_tags(meta),
                "path": str(f),
            })
    _output({"action": "research_list", "project": proj.name, "count": len(items), "researches": items})


# ---------------------------------------------------------------------------
# Commands — specs
# ---------------------------------------------------------------------------


def cmd_spec_write(args) -> None:
    base = _get_base_dir(args.scope)
    proj = _resolve_project_dir(base, args.project)
    spec_type = _slugify(args.type)
    path = proj / "specs" / f"{spec_type}.md"
    path.parent.mkdir(parents=True, exist_ok=True)

    content = _resolve_content(args)
    now = _now_iso()
    old_meta = _read_meta(path) if path.exists() else {}
    created = old_meta.get("created", now)
    if path.exists() and not content:
        _, content = _parse_frontmatter(path.read_text(encoding="utf-8"))
    default_title = spec_type.replace("-", " ").title() + " Spec"
    title = args.title or old_meta.get("title") or default_title
    tags = args.tags.split(",") if args.tags else _read_tags(old_meta)

    fm = _build_frontmatter({
        "title": title, "type": "spec", "spec_type": spec_type,
        "created": created, "updated": now, "tags": tags, "scope": args.scope,
    })
    path.write_text(fm + content, encoding="utf-8")
    _rebuild_spec_index(proj)
    _rebuild_project_index(proj)
    _output({"action": "spec_write", "project": proj.name, "spec_type": spec_type,
             "title": title, "path": str(path)})


def cmd_spec_read(args) -> None:
    base = _get_base_dir(args.scope)
    proj = _resolve_project_dir(base, args.project)
    path = proj / "specs" / f"{_slugify(args.type)}.md"
    if not path.exists():
        _error(f"Spec not found: {args.type} in {proj.name}")
    meta, body = _parse_frontmatter(path.read_text(encoding="utf-8"))
    _output({"action": "spec_read", "project": proj.name, "path": str(path),
             "meta": meta, "body": body})


def cmd_spec_list(args) -> None:
    base = _get_base_dir(args.scope)
    proj = _resolve_project_dir(base, args.project)
    sd = proj / "specs"
    items = []
    if sd.is_dir():
        for f in sorted(sd.glob("*.md")):
            if f.name == "index.md":
                continue
            meta = _read_meta(f)
            items.append({"spec_type": f.stem, "title": meta.get("title", f.stem),
                          "updated": meta.get("updated", ""), "path": str(f)})
    _output({"action": "spec_list", "project": proj.name, "count": len(items), "specs": items})


# ---------------------------------------------------------------------------
# Commands — sprints
# ---------------------------------------------------------------------------


def _new_entity_index(path: Path, fm: Dict[str, object], heading: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_build_frontmatter(fm) + f"# {heading}\n\n{body}\n\n", encoding="utf-8")


def cmd_sprint_create(args) -> None:
    base = _get_base_dir(args.scope)
    proj = _resolve_project_dir(base, args.project)
    sprints_dir = proj / "sprints"
    sprints_dir.mkdir(parents=True, exist_ok=True)

    if args.name:
        name = _norm_sprint(args.name)
    else:
        nums = [int(re.search(r"(\d+)", s.name).group(1)) for s in _iter_sprints(proj)]
        name = f"sprint-{(max(nums) + 1) if nums else 1}"

    sprint = sprints_dir / name
    if (sprint / "index.md").exists():
        _output({"action": "sprint_create", "status": "already_exists",
                 "project": proj.name, "sprint": name, "path": str(sprint)})
        return

    now = _now_iso()
    fm = {"title": args.title or name, "type": "sprint", "name": name,
          "status": args.status or "planned", "goal": args.goal or "",
          "created": now, "updated": now}
    body = (args.goal or "_Sprint goal._")
    _new_entity_index(sprint / "index.md", fm, args.title or name, body)
    _rebuild_sprint(sprint)
    _rebuild_sprints_index(proj)
    _rebuild_project_index(proj)
    _output({"action": "sprint_create", "status": "created", "project": proj.name,
             "sprint": name, "path": str(sprint)})


def cmd_sprint_list(args) -> None:
    base = _get_base_dir(args.scope)
    proj = _resolve_project_dir(base, args.project)
    items = []
    for s in _iter_sprints(proj):
        meta = _read_meta(s / "index.md")
        items.append({"sprint": s.name, "status": meta.get("status", "planned"),
                      "goal": meta.get("goal", ""), "stories": len(_iter_stories(s)),
                      "path": str(s)})
    _output({"action": "sprint_list", "project": proj.name, "count": len(items), "sprints": items})


def cmd_sprint_show(args) -> None:
    base = _get_base_dir(args.scope)
    proj = _resolve_project_dir(base, args.project)
    path = proj / "sprints" / _norm_sprint(args.sprint) / "index.md"
    if not path.exists():
        _error(f"Sprint not found: {args.sprint} in {proj.name}")
    _output({"action": "sprint_show", "project": proj.name, "path": str(path),
             "content": path.read_text(encoding="utf-8")})


def cmd_sprint_status(args) -> None:
    base = _get_base_dir(args.scope)
    proj = _resolve_project_dir(base, args.project)
    sprint = proj / "sprints" / _norm_sprint(args.sprint)
    if not (sprint / "index.md").exists():
        _error(f"Sprint not found: {args.sprint} in {proj.name}")
    _update_frontmatter(sprint / "index.md", {"status": args.status})
    _rebuild_sprints_index(proj)
    _rebuild_project_index(proj)
    _output({"action": "sprint_status", "project": proj.name, "sprint": sprint.name, "status": args.status})


# ---------------------------------------------------------------------------
# Commands — user stories
# ---------------------------------------------------------------------------


def cmd_story_create(args) -> None:
    base = _get_base_dir(args.scope)
    proj = _resolve_project_dir(base, args.project)
    sprint = proj / "sprints" / _norm_sprint(args.sprint)
    if not sprint.is_dir():
        _error(f"Sprint not found: {args.sprint}. Create it with 'sprint create'.")
    us = _norm_us(args.us_id)
    story = sprint / us
    if (story / "index.md").exists() and not (args.title or args.description):
        _output({"action": "story_create", "status": "already_exists",
                 "project": proj.name, "sprint": sprint.name, "story": us, "path": str(story)})
        return

    now = _now_iso()
    title = args.title or us.upper()
    fm = {"title": title, "type": "user_story", "id": us,
          "status": args.status or "todo", "created": now, "updated": now}
    body = (args.description or "_User story description._")
    _new_entity_index(story / "index.md", fm, f"{us.upper()} · {title}", body)
    _rebuild_story(story)
    _rebuild_sprint(sprint)
    _rebuild_sprints_index(proj)
    _rebuild_project_index(proj)
    _output({"action": "story_create", "status": "created", "project": proj.name,
             "sprint": sprint.name, "story": us, "title": title, "path": str(story)})


def cmd_story_list(args) -> None:
    base = _get_base_dir(args.scope)
    proj = _resolve_project_dir(base, args.project)
    sprint = proj / "sprints" / _norm_sprint(args.sprint)
    if not sprint.is_dir():
        _error(f"Sprint not found: {args.sprint}")
    items = []
    for s in _iter_stories(sprint):
        meta = _read_meta(s / "index.md")
        items.append({"story": s.name, "title": meta.get("title", s.name),
                      "status": meta.get("status", "todo"), "tasks": len(_iter_tasks(s)),
                      "path": str(s)})
    _output({"action": "story_list", "project": proj.name, "sprint": sprint.name,
             "count": len(items), "stories": items})


def cmd_story_show(args) -> None:
    base = _get_base_dir(args.scope)
    proj = _resolve_project_dir(base, args.project)
    path = proj / "sprints" / _norm_sprint(args.sprint) / _norm_us(args.us_id) / "index.md"
    if not path.exists():
        _error(f"User story not found: {args.us_id}")
    _output({"action": "story_show", "project": proj.name, "path": str(path),
             "content": path.read_text(encoding="utf-8")})


def cmd_story_status(args) -> None:
    base = _get_base_dir(args.scope)
    proj = _resolve_project_dir(base, args.project)
    sprint = proj / "sprints" / _norm_sprint(args.sprint)
    story = sprint / _norm_us(args.us_id)
    if not (story / "index.md").exists():
        _error(f"User story not found: {args.us_id}")
    _update_frontmatter(story / "index.md", {"status": args.status})
    _rebuild_sprint(sprint)
    _output({"action": "story_status", "project": proj.name, "sprint": sprint.name,
             "story": story.name, "status": args.status})


# ---------------------------------------------------------------------------
# Commands — tasks
# ---------------------------------------------------------------------------


def _task_path(proj: Path, sprint: str, us: str, task_num: str) -> Path:
    us_n = _norm_us(us)
    return proj / "sprints" / _norm_sprint(sprint) / us_n / f"{us_n}-task-{_norm_task_num(task_num)}.md"


def cmd_task_write(args) -> None:
    base = _get_base_dir(args.scope)
    proj = _resolve_project_dir(base, args.project)
    path = _task_path(proj, args.sprint, args.us_id, args.task_id)
    story = path.parent
    if not story.is_dir():
        _error(f"User story not found: {args.us_id} in {_norm_sprint(args.sprint)}. Create it with 'story create'.")

    content = _resolve_content(args)
    now = _now_iso()
    old_meta = _read_meta(path) if path.exists() else {}
    created = old_meta.get("created", now)
    if path.exists() and not content:
        _, content = _parse_frontmatter(path.read_text(encoding="utf-8"))
    title = args.title or old_meta.get("title") or path.stem
    status = args.status or old_meta.get("status") or "todo"

    fm = _build_frontmatter({
        "title": title, "type": "task", "id": path.stem,
        "status": status, "created": created, "updated": now,
    })
    path.write_text(fm + content, encoding="utf-8")
    _rebuild_story(story)
    _rebuild_sprint(story.parent)
    _output({"action": "task_write", "project": proj.name, "path": str(path),
             "title": title, "status": status})


def cmd_task_read(args) -> None:
    base = _get_base_dir(args.scope)
    proj = _resolve_project_dir(base, args.project)
    path = _task_path(proj, args.sprint, args.us_id, args.task_id)
    if not path.exists():
        _error(f"Task not found: {path.name}")
    meta, body = _parse_frontmatter(path.read_text(encoding="utf-8"))
    _output({"action": "task_read", "project": proj.name, "path": str(path),
             "meta": meta, "body": body})


def cmd_task_list(args) -> None:
    base = _get_base_dir(args.scope)
    proj = _resolve_project_dir(base, args.project)
    story = proj / "sprints" / _norm_sprint(args.sprint) / _norm_us(args.us_id)
    if not story.is_dir():
        _error(f"User story not found: {args.us_id}")
    items = []
    for t in _iter_tasks(story):
        meta = _read_meta(t)
        items.append({"id": t.stem, "title": meta.get("title", t.stem),
                      "status": meta.get("status", "todo"), "path": str(t)})
    _output({"action": "task_list", "project": proj.name, "count": len(items), "tasks": items})


def cmd_task_status(args) -> None:
    base = _get_base_dir(args.scope)
    proj = _resolve_project_dir(base, args.project)
    path = _task_path(proj, args.sprint, args.us_id, args.task_id)
    if not path.exists():
        _error(f"Task not found: {path.name}")
    _update_frontmatter(path, {"status": args.status})
    _rebuild_story(path.parent)
    _rebuild_sprint(path.parent.parent)
    _output({"action": "task_status", "project": proj.name, "path": str(path), "status": args.status})


# ---------------------------------------------------------------------------
# Shared frontmatter update
# ---------------------------------------------------------------------------


def _update_frontmatter(path: Path, updates: Dict[str, str]) -> None:
    meta, body = _parse_frontmatter(path.read_text(encoding="utf-8"))
    meta.update(updates)
    meta["updated"] = _now_iso()
    # Preserve tags as a list in output
    if "tags" in meta:
        tags = _read_tags(meta)
        meta = {k: (tags if k == "tags" else v) for k, v in meta.items()}
    path.write_text(_build_frontmatter(meta) + body, encoding="utf-8")


# ---------------------------------------------------------------------------
# Commands — search
# ---------------------------------------------------------------------------


def _walk_markdown(proj: Path) -> List[Path]:
    return [f for f in proj.rglob("*.md")]


def cmd_search(args) -> None:
    base = _get_base_dir(args.scope)
    query = args.query.lower()
    if args.all:
        roots = _iter_project_dirs(base)
    else:
        roots = [_resolve_project_dir(base, args.project)]

    results = []
    for proj in roots:
        for f in _walk_markdown(proj):
            if f.name == "index.md":
                continue
            meta, body = _parse_frontmatter(f.read_text(encoding="utf-8"))
            score, matches = 0.0, []
            if query in meta.get("title", "").lower():
                score += 2.0
                matches.append("title")
            if any(query in t.lower() for t in _read_tags(meta)):
                score += 1.5
                matches.append("tags")
            if query in body.lower():
                score += min(body.lower().count(query) * 0.1, 1.0)
                matches.append("content")
            if score > 0:
                results.append({
                    "title": meta.get("title", f.stem),
                    "type": meta.get("type", ""),
                    "project": proj.name,
                    "score": round(score, 2),
                    "matched_in": matches,
                    "path": str(f),
                })
    results.sort(key=lambda r: r["score"], reverse=True)
    _output({"action": "search", "query": args.query, "scope": args.scope,
             "count": len(results), "results": results})


# ---------------------------------------------------------------------------
# Commands — migrate
# ---------------------------------------------------------------------------


def cmd_migrate(args) -> None:
    """Migrate an old flat docs/ layout into a project under the new layout."""
    base = _get_base_dir(args.scope)
    old = (Path(args.source) if args.source else (_get_base_dir(args.scope).parent / "docs"))
    if not old.is_dir():
        _error(f"No source docs directory found at {old}")

    slug = _slugify(args.project_slug or "legacy")
    dirname = f"{_today_prefix()}_{slug}"
    proj = base / dirname
    for sub in PROJECT_SUBDIRS:
        (proj / sub).mkdir(parents=True, exist_ok=True)
    now = _now_iso()
    if not (proj / "index.md").exists():
        fm = _build_frontmatter({"title": slug.replace("-", " ").title(), "type": "project",
                                 "slug": slug, "status": "active", "created": now,
                                 "updated": now, "scope": args.scope})
        (proj / "index.md").write_text(fm + f"# {slug.title()}\n\nMigrated from `{old}`.\n\n", encoding="utf-8")

    moved = {"researches": [], "specs": [], "notes": []}

    # researches: old researches/<date>__slug/index.md  -> researches/<date>_slug.md
    old_research = old / "researches"
    if old_research.is_dir():
        for entry in sorted(old_research.iterdir()):
            src = entry / "index.md" if entry.is_dir() else entry
            if not src.exists() or src.suffix != ".md":
                continue
            name = entry.name.replace("__", "_") if entry.is_dir() else entry.stem
            name = re.sub(r"^(\d{4}_\d{2}_\d{2})_?", lambda m: m.group(1) + "_", name)
            if not RESEARCH_FILE_RE.match(name + ".md"):
                name = f"{_today_prefix()}_{_slugify(name)}"
            dest = proj / "researches" / f"{name}.md"
            dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            moved["researches"].append(dest.name)

    # specs: old specs/*.md (flat) and specs/<date>__slug/{solution,technical}.md
    old_specs = old / "specs"
    if old_specs.is_dir():
        for entry in sorted(old_specs.iterdir()):
            if entry.is_dir():
                for md in sorted(entry.glob("*.md")):
                    dest = proj / "specs" / md.name  # solution.md / technical.md
                    if dest.exists():
                        dest = proj / "specs" / f"{entry.name.replace('__', '_')}-{md.name}"
                    dest.write_text(md.read_text(encoding="utf-8"), encoding="utf-8")
                    moved["specs"].append(dest.name)
            elif entry.suffix == ".md":
                dest = proj / "specs" / entry.name
                dest.write_text(entry.read_text(encoding="utf-8"), encoding="utf-8")
                moved["specs"].append(dest.name)

    # tasks/docs and anything else: preserve as research notes so nothing is lost
    for misc in ("tasks", "docs"):
        old_misc = old / misc
        if not old_misc.is_dir():
            continue
        for md in sorted(old_misc.rglob("*.md")):
            dest = proj / "researches" / f"{_today_prefix()}_{misc}-{_slugify(md.stem)}.md"
            dest.write_text(md.read_text(encoding="utf-8"), encoding="utf-8")
            moved["notes"].append(dest.name)

    _set_active(base, dirname)
    _rebuild_all(base, proj)
    _output({"action": "migrate", "source": str(old), "project": dirname,
             "path": str(proj), "moved": moved})


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _add_scope(p) -> None:
    p.add_argument("--scope", choices=["project", "global"], default="project",
                   help="Scope: project (./projects/) or global ($AGENT_ROOT/projects/)")


def _add_project(p) -> None:
    p.add_argument("--project", default=None,
                   help="Target project (slug or dir name). Defaults to the active project.")


def _add_content(p) -> None:
    p.add_argument("--title", help="Title")
    p.add_argument("--content", help="Content string")
    p.add_argument("--file", help="Read content from file")
    p.add_argument("--tags", help="Comma-separated tags")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Librarian — Project-first artifact management for agent knowledge",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="group")

    # init
    p = sub.add_parser("init", help="Create the projects/ root")
    _add_scope(p)
    p.set_defaults(func=cmd_init)

    # ---- project ----
    g = sub.add_parser("project", help="Project management").add_subparsers(dest="cmd")

    p = g.add_parser("create", help="Create a project (and make it active)")
    p.add_argument("slug", help="Project name or slug (date prefix added automatically)")
    p.add_argument("--description", help="Project description (body)")
    p.add_argument("--status", help="Initial status (default: active)")
    p.add_argument("--title", help="Title")
    _add_scope(p); p.set_defaults(func=cmd_project_create)

    p = g.add_parser("list", help="List all projects"); _add_scope(p); p.set_defaults(func=cmd_project_list)

    p = g.add_parser("use", help="Set the active project")
    p.add_argument("slug"); _add_scope(p); p.set_defaults(func=cmd_project_use)

    p = g.add_parser("show", help="Show a project index")
    _add_project(p); _add_scope(p); p.set_defaults(func=cmd_project_show)

    p = g.add_parser("current", help="Print the active project"); _add_scope(p); p.set_defaults(func=cmd_project_current)

    p = g.add_parser("status", help="Set a project's status")
    p.add_argument("status"); _add_project(p); _add_scope(p); p.set_defaults(func=cmd_project_status)

    # ---- research ----
    g = sub.add_parser("research", help="Research artifacts").add_subparsers(dest="cmd")

    p = g.add_parser("write", help="Write/update a research note")
    p.add_argument("slug"); _add_content(p); _add_project(p); _add_scope(p); p.set_defaults(func=cmd_research_write)

    p = g.add_parser("read", help="Read a research note")
    p.add_argument("slug"); _add_project(p); _add_scope(p); p.set_defaults(func=cmd_research_read)

    p = g.add_parser("list", help="List research notes")
    _add_project(p); _add_scope(p); p.set_defaults(func=cmd_research_list)

    # ---- spec ----
    g = sub.add_parser("spec", help="Specifications").add_subparsers(dest="cmd")

    p = g.add_parser("write", help="Write/update a spec (technical, solution, api-design, design, ...)")
    p.add_argument("type"); _add_content(p); _add_project(p); _add_scope(p); p.set_defaults(func=cmd_spec_write)

    p = g.add_parser("read", help="Read a spec")
    p.add_argument("type"); _add_project(p); _add_scope(p); p.set_defaults(func=cmd_spec_read)

    p = g.add_parser("list", help="List specs")
    _add_project(p); _add_scope(p); p.set_defaults(func=cmd_spec_list)

    # ---- sprint ----
    g = sub.add_parser("sprint", help="Sprints").add_subparsers(dest="cmd")

    p = g.add_parser("create", help="Create a sprint (auto-numbered if --name omitted)")
    p.add_argument("--name", help="Sprint name/number (e.g. 2 or sprint-2)")
    p.add_argument("--title"); p.add_argument("--goal"); p.add_argument("--status")
    _add_project(p); _add_scope(p); p.set_defaults(func=cmd_sprint_create)

    p = g.add_parser("list", help="List sprints"); _add_project(p); _add_scope(p); p.set_defaults(func=cmd_sprint_list)

    p = g.add_parser("show", help="Show a sprint index")
    p.add_argument("sprint"); _add_project(p); _add_scope(p); p.set_defaults(func=cmd_sprint_show)

    p = g.add_parser("status", help="Set a sprint's status")
    p.add_argument("sprint"); p.add_argument("status"); _add_project(p); _add_scope(p); p.set_defaults(func=cmd_sprint_status)

    # ---- story ----
    g = sub.add_parser("story", help="User stories").add_subparsers(dest="cmd")

    p = g.add_parser("create", help="Create a user story under a sprint")
    p.add_argument("sprint"); p.add_argument("us_id", help="User story id (e.g. 1 or us-001)")
    p.add_argument("--title"); p.add_argument("--description"); p.add_argument("--status")
    _add_project(p); _add_scope(p); p.set_defaults(func=cmd_story_create)

    p = g.add_parser("list", help="List user stories in a sprint")
    p.add_argument("sprint"); _add_project(p); _add_scope(p); p.set_defaults(func=cmd_story_list)

    p = g.add_parser("show", help="Show a user story")
    p.add_argument("sprint"); p.add_argument("us_id"); _add_project(p); _add_scope(p); p.set_defaults(func=cmd_story_show)

    p = g.add_parser("status", help="Set a user story's status")
    p.add_argument("sprint"); p.add_argument("us_id"); p.add_argument("status")
    _add_project(p); _add_scope(p); p.set_defaults(func=cmd_story_status)

    # ---- task ----
    g = sub.add_parser("task", help="Tasks").add_subparsers(dest="cmd")

    p = g.add_parser("write", help="Write/update a task under a user story")
    p.add_argument("sprint"); p.add_argument("us_id"); p.add_argument("task_id", help="Task id (e.g. 1)")
    p.add_argument("--status"); _add_content(p); _add_project(p); _add_scope(p); p.set_defaults(func=cmd_task_write)

    p = g.add_parser("read", help="Read a task")
    p.add_argument("sprint"); p.add_argument("us_id"); p.add_argument("task_id")
    _add_project(p); _add_scope(p); p.set_defaults(func=cmd_task_read)

    p = g.add_parser("list", help="List tasks in a user story")
    p.add_argument("sprint"); p.add_argument("us_id"); _add_project(p); _add_scope(p); p.set_defaults(func=cmd_task_list)

    p = g.add_parser("status", help="Set a task's status")
    p.add_argument("sprint"); p.add_argument("us_id"); p.add_argument("task_id"); p.add_argument("status")
    _add_project(p); _add_scope(p); p.set_defaults(func=cmd_task_status)

    # ---- search ----
    p = sub.add_parser("search", help="Search artifacts within a project (or --all projects)")
    p.add_argument("query"); p.add_argument("--all", action="store_true", help="Search across all projects")
    _add_project(p); _add_scope(p); p.set_defaults(func=cmd_search)

    # ---- migrate ----
    p = sub.add_parser("migrate", help="Migrate an old flat docs/ layout into a project")
    p.add_argument("--source", help="Source docs directory (default: ../docs relative to projects/)")
    p.add_argument("--project-slug", dest="project_slug", default="legacy", help="Target project slug (default: legacy)")
    _add_scope(p); p.set_defaults(func=cmd_migrate)

    args = parser.parse_args()
    if not getattr(args, "func", None):
        parser.print_help()
        sys.exit(1)
    try:
        args.func(args)
    except Exception as e:  # noqa: BLE001 — surface errors as JSON for the agent
        _error(f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
