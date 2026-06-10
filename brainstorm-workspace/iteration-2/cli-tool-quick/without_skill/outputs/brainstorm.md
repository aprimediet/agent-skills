# DupeScan — CLI Duplicate File Finder (Brainstorm)

## Overview

A single-purpose CLI utility that recursively scans a directory, computes SHA-256 hashes for every file, and reports which files are duplicates (identical content). No database, no daemon, no config files — just run it and get results.

---

## Goals & Non-Goals

### Goals
- Scan a directory tree and identify duplicate files by content (SHA-256)
- Output results in a clear, human-readable format
- Be fast enough for directories with thousands of files
- Zero dependencies beyond the standard library (or minimal, well-justified ones)
- Single-binary distribution (if compiled language) or single-script (if interpreted)

### Non-Goals
- No interactive mode / TUI
- No file deletion or deduplication actions (user pipes to `rm` if they want)
- No persistent database across runs
- No network features
- No GUI

---

## User Stories

1. **As a user**, I can run `dupescan ./` and see a grouped list of all duplicate files.
2. **As a user**, I can run `dupescan --min-size 1M ./downloads` to only check files >= 1 MB.
3. **As a user**, I can run `dupescan --exclude "*.tmp" --exclude "node_modules" ./` to skip certain patterns.
4. **As a user**, I can run `dupescan --format json ./` to get machine-readable output.
5. **As a user**, I can see progress while scanning so I know it hasn't hung.
6. **As a user**, I get a non-zero exit code when duplicates are found (for scripting).

---

## CLI Interface Design

```
dupescan [OPTIONS] <PATH>

Arguments:
  PATH       Directory to scan (default: current directory)

Options:
  -h, --help                 Show help
  -m, --min-size <SIZE>      Minimum file size (e.g., 1K, 5M, 1G)
  -M, --max-size <SIZE>      Maximum file size
  -e, --exclude <PATTERN>    Glob pattern to exclude (can be repeated)
  -H, --hidden               Include hidden files/directories (default: skip)
  -f, --format <FMT>         Output format: text | json | csv (default: text)
  -q, --quiet                Suppress progress output
  -0, --print0               Print null-delimited paths (for xargs piping)
  -s, --symlinks             Follow symlinks (default: skip)
  -v, --version              Show version
```

### Output: Text format (default)

```
Scanning /home/user/files... (2,341 files)
Found 3 groups of duplicates (total wasted space: 45.2 MB)

=== Duplicate Group 1 (5 copies, 12.3 MB each) ===
  /home/user/files/photo.jpg
  /home/user/files/backup/photo.jpg
  /home/user/files/misc/DSC_001.jpg
  /home/user/files/old/photo.jpg
  /home/user/files/duplicates/photo.jpg

=== Duplicate Group 2 (2 copies, 8.1 MB each) ===
  /home/user/files/report-v2.pdf
  /home/user/files/report-final.pdf

=== Duplicate Group 3 (3 copies, 1.2 MB each) ===
  /home/user/files/notes.txt
  /home/user/files/notes_copy.txt
  /home/user/files/backup/notes_backup.txt
```

### Output: JSON format

```json
{
  "scanned_path": "/home/user/files",
  "total_files": 2341,
  "total_duplicate_groups": 3,
  "wasted_bytes": 45200000,
  "duplicates": [
    {
      "hash": "sha256:abc123...",
      "size": 12300000,
      "count": 5,
      "paths": [
        "/home/user/files/photo.jpg",
        "/home/user/files/backup/photo.jpg",
        "/home/user/files/misc/DSC_001.jpg",
        "/home/user/files/old/photo.jpg",
        "/home/user/files/duplicates/photo.jpg"
      ]
    }
  ]
}
```

---

## Technical Design

### Algorithm

1. **Walk** the directory tree (respecting exclude patterns, hidden file rules).
2. **First pass — size filter**: Group files by size. Any file with a unique size cannot be a duplicate → skip hashing.
3. **Second pass — partial hash**: For files sharing a size, read the first 4 KB and hash it. Files with unique partial hashes → skip full hash.
4. **Third pass — full SHA-256**: For remaining candidates, compute full SHA-256. Group by hash.
5. **Report** groups with count > 1.

This avoids hashing every file when there are few collisions by size.

### Implementation Language Options

| Language   | Pros                                      | Cons                                        |
|------------|-------------------------------------------|---------------------------------------------|
| Rust       | Fast, single binary, excellent CLI crates | Steeper learning curve                      |
| Go         | Fast, single binary, great stdlib         | Slightly larger binary                      |
| Python     | Quick to write, ubiquitous                | Requires Python runtime, slower for large scans |
| Node.js    | Quick to write, good streams              | Heavy runtime, callback-heavy I/O           |
| Zig        | Tiny binaries, no deps                    | Niche, smaller ecosystem                    |

**Recommended**: **Rust** (using `clap` for CLI, `walkdir` for directory traversal, `sha2` for hashing) — fast, reliable, distributes as a single binary.

### Memory Considerations

- Don't load full file contents into memory at once — stream through buffer.
- Store hash → paths mapping in a `HashMap<String, Vec<PathBuf>>`.
- For very large scans (millions of files), consider chunked processing or SQLite-backed map.
- Soft limit: handle 100K+ files with reasonable memory (~200 MB).

### Performance Targets

- Scan 10K files (average 1 MB): under 30 seconds
- Scan 100K files (average 100 KB): under 2 minutes
- Minimum file size filtering should skip small files before any I/O

---

## Edge Cases & Considerations

- **Empty files**: All empty files are technically duplicates. Consider a flag to include/exclude zero-byte files.
- **Permission errors**: Skip unreadable files with a warning, don't crash.
- **Symlinks**: Default to not following; option to follow.
- **Files renamed during scan**: Unlikely but possible — scan is read-only so no corruption risk.
- **Very large files (>4 GB)**: Streaming hash handles this fine; no issue.
- **Special files**: Skip devices, sockets, FIFOs.
- **Unicode filenames**: Must handle all valid OS filenames (Rust does this well).
- **Hard links**: Files with the same inode are already the same content. Could detect and report separately.
- **Hanging on network mounts**: Add a timeout or warning for slow filesystems.
- **Case-insensitive filesystems** (macOS): File paths may differ only by case — still valid duplicate detection.
- **Binary vs text**: Doesn't matter — we hash content regardless.

---

## Roadmap

### v0.1 — MVP
- [ ] Recursive directory scan
- [ ] SHA-256 hashing with size pre-filter
- [ ] Text output grouped by hash
- [ ] Basic error handling (permission denied, broken symlinks)
- [ ] `--help` / `--version`

### v0.2 — Usability
- [ ] `--min-size` / `--max-size` filters
- [ ] `--exclude` glob patterns
- [ ] Skip hidden files/dirs by default
- [ ] Progress indicator (spinner or file counter)
- [ ] Non-zero exit when duplicates found

### v0.3 — Advanced
- [ ] JSON and CSV output formats
- [ ] `--print0` for scripting
- [ ] Hard link detection
- [ ] Empty file handling flag

### v1.0 — Polish
- [ ] Performance optimization (parallel hashing with thread pool)
- [ ] Cross-platform testing (Linux, macOS, Windows)
- [ ] Package distribution (Homebrew, cargo install, GitHub releases)

---

## Alternatives Considered

| Approach                     | Verdict                                                      |
|------------------------------|--------------------------------------------------------------|
| `fdupes` (C)                 | Mature but outdated output format, no JSON, no --min-size    |
| `rdfind` (C++)               | Good but more complex (dedup actions built in)               |
| `jdupes` (C)                 | Fast, feature-rich, but C codebase, harder to contribute to  |
| `find + sha256sum + sort`    | Works but slow (hashes every file, no size pre-filter), awkward parsing |

**Differentiator for dupescan**: Modern CLI UX, streaming algorithm, JSON output, single-binary distribution, easy to extend.

---

## Questions for Further Exploration

1. Should we support BLAKE3 as an alternative / faster hash? (SHA-256 is standard, BLAKE3 is ~10x faster.)
2. Should we auto-detect hard links and skip the hash? (Same inode → guaranteed duplicate.)
3. Should we add a `--delete` flag or strictly keep it read-only? (Out of scope for MVP.)
4. Windows support — how to handle `\` vs `/` paths and drive letters?
5. Should we add a `--dedupe` dry-run mode showing `rm` / `ln -f` commands?
