# Brainstorm: `dupscan` — CLI Duplicate File Detector

## Elevator Pitch

> A single-purpose CLI utility that scans a directory tree, computes SHA-256 hashes for every file, groups files by hash, and reports which files are duplicates — all in under 50ms for a typical project directory.

---

## Core Requirements

| Requirement | Priority | Notes |
|---|---|---|
| Scan a given directory recursively | P0 | Default to `.` if no path given |
| Compute SHA-256 hash of each file | P0 | Fast, collision-resistant |
| Group files by hash and report duplicates | P0 | Show size, path, last modified |
| Output to stdout | P0 | Plain text (terminal-friendly) |
| Cross-platform | P0 | Linux + macOS + Windows |
| Handle permission errors gracefully | P1 | Skip unreadable files, warn |
| Handle symlinks | P1 | Follow? Skip? Flag? |
| Handle very large files (GB+) | P1 | Stream-based hashing, progress |
| JSON output flag | P2 | `--json` for piping into jq |
| Exclude patterns | P2 | `--exclude "*.log"` or `--exclude-dir node_modules` |
| Minimum file size filter | P2 | `--min-size 1MB` to skip tiny files |
| Progress indicator | P2 | Spinner or simple counter for deep scans |
| Quiet mode | P2 | Only print duplicate groups, nothing else |

---

## User Experience

### Usage

```bash
# Basic scan of current directory
dupscan

# Scan a specific path
dupscan ~/Downloads

# Exclude patterns
dupscan --exclude "*.log" --exclude-dir node_modules,.git

# JSON output
dupscan --json > duplicates.json

# Only files >= 1 MB
dupscan --min-size 1M

# Quiet — only output duplicate groups
dupscan -q
```

### Sample Output (plain text)

```
Scanning /home/user/project...

Found 3 duplicate groups (12 files, 48.2 MB wasted)

━━━ Group 1: a1b2c3d4... (2 files, 2.1 MB each) ━━━
  /home/user/project/build/output.js
  /home/user/project/dist/output.js

━━━ Group 2: e5f6g7h8... (5 files, 256 KB each) ━━━
  /home/user/project/assets/icon.png
  /home/user/project/assets/icon-copy.png
  /home/user/project/backup/icon.png
  /home/user/project/docs/images/icon.png
  /home/user/project/src/assets/icon.png

━━━ Group 3: i9j0k1l2... (3 files, 14.5 MB each) ━━━
  /home/user/project/vendor/chromium.zip
  /home/user/project/.cache/chromium-download.zip

Summary: 3 groups, 12 duplicate files, ~48.2 MB reclaimable
```

---

## Technical Design

### Language Choice

| Option | Pros | Cons |
|---|---|---|
| **Rust** | Fastest, single binary, cross-compile | Steeper learning curve |
| **Go** | Fast, single binary, great stdlib | Slightly larger binary |
| **Node.js** | Ubiquitous, quick to prototype | Requires runtime, slower hashing |
| **Python** | Ubiquitous, easy to write | Requires runtime, slowest for big files |

**Recommendation: Go**

- Single static binary, no runtime dependency
- `crypto/sha256` in stdlib
- `filepath.Walk` in stdlib
- Good performance out of the box
- `encoding/json` for `--json` flag
- Cross-compilation is trivial

### Architecture

```
┌─────────────────────────────────────────┐
│              main.go                     │
│  - Parse flags (flag package)            │
│  - Orchestrate scan                      │
│  - Render output                         │
└────────────┬────────────────────────────┘
             │
┌────────────▼────────────────────────────┐
│           scanner/ package               │
│  - Walk directory tree                   │
│  - Open each file                        │
│  - Stream hash (io.Copy with sha256)     │
│  - Return map[hash][]FileInfo            │
└────────────┬────────────────────────────┘
             │
┌────────────▼────────────────────────────┐
│           reporter/ package              │
│  - Filter non-duplicates                 │
│  - Sort groups by total size             │
│  - Format text output                    │
│  - Format JSON output                    │
└─────────────────────────────────────────┘
```

### Hashing Strategy

- Use `bufio.NewReader` with a 64KB buffer
- Stream through `sha256.New()` — works for any file size
- Skip empty files immediately (they're all duplicates of each other, but trivial)
- Optionally add a fast-path: check file size first (different sizes can't be duplicates)

### Performance Considerations

- File size check is O(1) — quick reject of non-duplicates
- Only hash files whose sizes match at least one other file
- Use `sync.WaitGroup` + worker pool for parallel hashing in deep directories
- Number of workers: `runtime.NumCPU()` by default

### Error Handling

| Scenario | Behavior |
|---|---|
| Permission denied | Log warning, skip file, continue |
| Broken symlink | Log warning, skip |
| File vanishes during scan | Log warning, skip |
| Binary file | Treated same as text — hash is hash |
| Unicode filename | Go handles this natively on all OSes |

---

## Implementation Plan

### Phase 1 — MVP (1 session)

- [ ] `main.go` with flag parsing (`path`, `--json`, `-q`)
- [ ] `scanner.Scan(path)` returning `map[string][]string`
- [ ] Stream-based SHA-256 hashing
- [ ] Plain text reporter
- [ ] Skip empty files, handle permissions

### Phase 2 — Polish (1 session)

- [ ] `--exclude` and `--exclude-dir` flags
- [ ] `--min-size` flag (with human-readable parser: `1K`, `2M`, `1G`)
- [ ] JSON reporter
- [ ] Summary line (total wasted space)

### Phase 3 — Performance (stretch)

- [ ] Parallel hashing with worker pool
- [ ] Progress indicator
- [ ] Benchmark and optimize
- [ ] Pre-filter by file size before hashing

---

## Alternatives Considered

| Alternative | Why not chosen |
|---|---|
| `fdupes` / `rdfind` | Existing tools, but none are single-binary cross-platform with modern UX |
| `jdupes` | C-based, requires compilation per platform |
| Bash one-liner (`find ... -exec sha256sum ...`) | Slow, no grouping, no nice output, no parallel |
| Electron app | Way too heavy for a terminal utility |

---

## Open Questions

1. Should we follow symlinks by default or only with a `--follow-links` flag?
2. Should the tool be able to delete duplicates (with confirmation)? That drifts from "scan-only" scope.
3. Hard links — count as duplicates or ignore (since same inode)?
4. Should we offer `--dedupe` (replace duplicates with hard links / symlinks) as a future extension?
5. Naming: `dupscan`, `dupefinder`, `hashdup`, `fdup`?

---

## Potential Future Extensions

- `--delete` / `--dedupe` (interactive or with `--dry-run`)
- `--move-to <dir>` (quarantine duplicates)
- `--csv` output
- `.gitignore` awareness (auto-exclude gitignored paths)
- Integration with `trash-cli` for safe deletion
