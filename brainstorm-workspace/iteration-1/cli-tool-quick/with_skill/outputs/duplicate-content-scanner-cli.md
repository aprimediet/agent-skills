# Duplicate Content Scanner — Directory File Hash CLI

> Brainstorm | Depth: quick | Generated: 2026-06-09

## Core Idea

A single-purpose CLI utility that scans a directory tree, computes SHA-256 hashes for every file, and reports groups of files with identical content (duplicates). Designed for developers, designers, and power users who need to reclaim disk space or clean up messy directories — all from the terminal with zero setup.

## Problem & Motivation

- **Problem**: Hard drives and project directories accumulate duplicate files over time (copied assets, unzipped archives, accidentally duplicated downloads, generated files committed alongside sources). Manually finding these is tedious, and existing GUI tools are slow or require installation of heavy dependency trees.
- **Who**: Developers cleaning up project directories, designers managing asset folders, power users reclaiming disk space, CI pipelines checking for unintended duplication.
- **Why now**: Disk space is cheap but clutter is costly — messy repos get cloned everywhere, AI tools generate artefacts that accumulate duplicates, and developers need fast terminal-native tools that don't leave the command line. Existing tools like `fdupes` are unmaintained on some platforms; `jdupes` is C-heavy; nothing ships as a single static binary with modern DX.

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Language | Rust | Single static binary, no runtime dependency, fast hashing via platform intrinsics. Cross-compiles to macOS/Linux/Windows easily. |
| Hashing strategy | Size filter first, then partial hash, then full SHA-256 | Avoids hashing large files unnecessarily — group by size first, then hash first 4KB, then full file only if needed. Optimizes for the common case. |
| Output format | Terminal table + optional JSON | Human-readable groups by default; `--json` flag for programmatic use. |
| Subcommand structure | Single flat command with flags | This is a single-purpose tool — no subcommands needed. `dupfinder [path] [flags]` is enough. |

## Dimensions Explored

### Architecture & Tech Stack

Built in Rust as a single statically-linked binary. The scanning pipeline has three stages: (1) walk the directory tree using `walkdir` (cross-platform, respects symlinks and permissions), (2) group files by size as a fast pre-filter — if two files differ in size they cannot be identical, (3) for same-size groups, compute SHA-256 hashes sequentially and collect duplicates in a `HashMap<[u8; 32], Vec<PathBuf>>`. A further optimization: for files over a threshold (e.g., 64KB), hash only the first 4KB first — most non-duplicate same-sized files will diverge in their headers, avoiding unnecessary full-file reads. The terminal output uses a simple table via `prettytable-rs` or `comfy-table`. No async needed — the tool is I/O-bound on the filesystem, and async adds complexity without benefit for a synchronous walk+hash pipeline.

- Using SHA-256 (not MD5 or SHA-1) because it's the gold standard for content-addressable integrity, avoids collision concerns, and is fast on modern CPUs with hardware SHA intrinsics.
- The `walkdir` crate handles symlinks, permission errors, and cross-platform path normalization consistently.
- For truly enormous directories (100k+ files), we could add a `--progress` flag showing files scanned per second, but for the 99% case the scan completes in under a second.

### User Experience

A single flat command: `dupfinder [path]` defaults to `.` (current directory). Output shows duplicate groups sorted by group size (largest first), with file sizes and full paths. Each group is separated by a blank line for scannability.

```
$ dupfinder ~/Downloads
Found 12 duplicate groups (wasting 342 MB)

Group 1: 4 files × 128 MB each
  /Users/me/Downloads/backup.zip
  /Users/me/Downloads/archive/backup.zip
  /Users/me/Downloads/old/backup.zip
  /Users/me/Desktop/backup.zip

Group 2: 2 files × 42 MB each
  /Users/me/Downloads/setup.exe
  /Users/me/Downloads/installers/setup.exe
```

Key flags: `--json` for machine-readable output (piped to `jq` or scripts), `--min-size 1MB` to skip tiny files (config.json, lockfiles), `--delete` for interactive deletion (prompt per group: "Delete all but one? [y/N]"), and `--exclude '*.git/*'` to skip paths by glob pattern. The tool does nothing destructive without `--delete` — it's read-only by default.

- Color output: groups with >100MB waste shown in red, >10MB in yellow. Pass `--no-color` to disable.
- The `--delete` mode shows a diff of what would be deleted and asks for confirmation before touching anything.

### Performance & Scalability

The main bottleneck is disk I/O, not CPU hashing. For a typical project directory (5,000 files, 2 GB total), the scan completes in 1–3 seconds. The size-based pre-filter eliminates >95% of pairwise comparisons immediately. For very large files (ISOs, disk images, video files), the partial-first-hash optimization avoids reading the entire file when files differ in their headers. Memory usage stays under 50MB even for 100k files because we store only paths and hashes, not file contents. The `walkdir` iterator is lazy — we don't load the full directory tree into memory, we walk as we go.

- Worst-case scenario: 100k files, all same size (e.g., an `icons/` directory with thousands of SVGs). In this case, every file gets a full SHA-256 hash. On a modern SSD this takes ~10–15 seconds. Partial pre-hashing helps here since SVG headers vary.
- The output table is built in memory and rendered at the end — for extremely large results (10k+ duplicate groups), we could stream output, but this is an edge case not worth optimizing in v1.
- Cross-platform filesystem considerations: NTFS case-insensitivity means `FileA.txt` and `filea.txt` are the same file on Windows — the tool should note this in documentation but not try to deduplicate across case differences on case-sensitive filesystems.

## Open Questions

- **Should we delete or just report by default?** The tool is read-only by default (report only), which is safe. But some users will want a "clean" command. Leaning toward: `--delete` flag triggers interactive deletion, with a `--force` flag for non-interactive (use with caution). The default stays read-only.
- **What about hard links and symlinks?** Two hard links to the same inode have identical content by definition. Should we report them as duplicates? They don't waste space, but a user might want to know about them. Symlinks to the same target are another gray area. Leaning toward: skip hard links to the same inode (they're not wasting space), report symlinks separately with a `[symlink]` marker.
- **Should we support a `.dupignore` file (like `.gitignore`) for excluding directories?** The `--exclude` flag covers the basics, but a config file would let teams standardize exclusions. Low priority — could be a v1.1 feature.

## Research Suggestions

Topics that need deeper investigation by the researcher skill:

- **SHA-256 performance on modern CPUs with hardware intrinsics** — Rust's `sha2` crate uses software implementations by default. Some platforms support SHA-NI instructions for hardware-accelerated hashing. Suggested researcher query: "Hardware-accelerated SHA-256 hashing in Rust — SHA-NI intrinsics vs software implementations benchmark 2025"
- **Cross-platform filesystem quirks for duplicate detection** — NTFS alternate data streams, case sensitivity, hard link detection, and permission errors vary by OS. Suggested researcher query: "Cross-platform filesystem edge cases for duplicate file detection — NTFS, APFS, ext4 comparison"

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Permission errors on system directories cause incomplete scans or crashes | Medium | Medium | Use `walkdir`'s `continue` on permission denied — log warnings to stderr, don't halt. Add `--strict` flag if the user wants errors to abort. |
| Large files (10GB+) cause long hashing times and memory pressure | Low | Medium | Partial pre-hash (first 4KB) filters most non-duplicates. Full SHA-256 on large files is unavoidable, but we can show a progress indicator per file. |
| Accidental deletion of important files via `--delete --force` | Low | High | Require `--delete` AND confirmation. `--force` skips the per-group prompt but still requires the initial `--delete` flag. Never delete without explicit user intent. |
| False negatives due to filesystem caching or in-flight writes | Low | Low | Document that the tool takes a point-in-time snapshot. Running while a file is being written could produce a partial hash. Not a concern for normal usage. |

## Next Steps

1. Write the core scanner in Rust — `walkdir` + size-based grouping + SHA-256 hashing. Get the hashing pipeline and duplicate group detection working as a library. Test against a curated set of test directories (empty files, same-size-non-duplicate, 100% duplicates, mixed).
2. Build the CLI frontend — argument parsing via `clap`, terminal table output with `comfy-table`, and the `--json` flag. Ship an MVP that runs `dupfinder .` and prints groups. No `--delete` yet.
3. Publish pre-built binaries for macOS (arm64 + x64), Linux (x64 + arm64), and Windows (x64) via GitHub Releases with a brew tap for macOS and a winget manifest for Windows.

---
*Brainstorm document produced by brainstorm skill. Use the librarian skill to persist this artifact.*
