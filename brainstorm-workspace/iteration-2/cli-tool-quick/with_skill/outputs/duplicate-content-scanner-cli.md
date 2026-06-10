# Duplicate Content Scanner — Directory-wide SHA-256 Duplicate Finder CLI

> Brainstorm | Depth: quick | Generated: 2026-06-09

## Core Idea

A single-binary CLI tool that scans a directory tree, computes SHA-256 hashes for every file, and reports which files have identical content — allowing the user to review, deduplicate, or clean up redundant copies from the terminal.

## Problem & Motivation

- **Problem**: Disk space fills up with duplicate files — accidental copies, backup artifacts, repeated downloads, unzipped archives. Manually finding duplicates with `find` + `cmp` or `diff` is slow and doesn't scale beyond a handful of files.
- **Who**: Developers, sysadmins, data hoarders, and anyone managing files who wants to reclaim disk space or identify redundant content without installing a heavy GUI tool.
- **Why now**: Storage is cheap but clutter grows faster than ever. A fast, zero-dependency CLI tool that works everywhere (Linux, macOS, Windows) fits the terminal-native workflow that developers and ops people already live in.

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Language | Rust vs Go (undecided) | Both produce static binaries. Rust gives better control over memory for huge file scans; Go has faster iteration for a quick utility. Needs research. |
| Hashing strategy | Streaming SHA-256 (not loading whole files) | Avoids OOM on large files (e.g., ISOs, videos, DB dumps). Read in 64 KB chunks, feed into the hash. |
| Output format | Grouped list (group by hash) with sizes | Most useful terminal output: shows each duplicate group, file paths, and sizes. `--json` flag for piping to other tools. |
| Dedup action | Report-only in v1 | The tool finds and reports duplicates. A `--delete` or `--dedup` flag is deferred — the user should review before deleting. |
| Symlink handling | Follow symlinks? Probably not by default | Symlinks can create false positives or loops. Default: skip symlinks, add `--follow-symlinks` flag for opt-in. |

## Dimensions Explored

### Architecture & Tech Stack

The core is a recursive directory walker that feeds each file through a streaming SHA-256 hasher, then groups results by hash in a hash map. Memory use is O(unique hashes × file paths) — the file contents are never fully loaded. The walk uses a cross-platform file traversal library (e.g., Go's `filepath.Walk` or Rust's `walkdir` crate). Output goes to stdout with colored grouping for the terminal, and the `--json` flag switches to JSON for script consumption.

- Rust vs Go is the main decision point. Rust: single static binary ~5 MB, faster execution, but steeper build. Go: ~10 MB binary, faster to write, goroutines help parallelize hashing trivially. For a simple utility, Go may be the pragmatic choice unless the user wants to learn Rust.
- Parallelism: File hashing is embarrassingly parallel. Walking the tree is I/O-bound, but hashing each file is CPU-bound. A worker pool (e.g., 4-8 concurrent hashers) speeds things up significantly on SSDs.
- The `--json` output should follow a simple schema: `{ "duplicates": [{ "hash": "...", "size": 123, "files": ["path1", "path2"] }] }`. Easy to pipe into `jq` or a script.

### User Experience

Three output modes: `default` (grouped terminal view), `--summary` (just counts and total wasted space), and `--json` (machine-readable). The default view shows each group with a header line (`Duplicates of <hash> (123 KB):`) followed by indented file paths, with the oldest or shortest path suggested as the "keep" candidate. A progress indicator (files scanned so far) keeps the user informed on large directories.

- The command should be simple: `dscan /path/to/dir` — no subcommands needed for a single-purpose tool. Flags handle variations:
  - `--min-size 1MB` — ignore tiny files (configs, logs) to reduce noise
  - `--exclude "*.tmp"` / `--exclude "node_modules"` — skip patterns
  - `--hash sha256` — future-proof for other hash algorithms (blake3, xxhash for speed)
- Color output: green for normal progress, yellow when duplicates are found, red for errors (permission denied on a file). Disable with `--no-color` or when stdout is piped.
- Exit codes: 0 = no duplicates found, 1 = duplicates found, 2 = error. This makes it script-friendly — `if dscan /data; then echo "all clean"; fi`.

### Performance & Scalability

The main performance concern is scanning directories with millions of small files (e.g., `node_modules`, `.git/objects`, photo libraries). Walking the tree is fast (kernel-level `readdir`), but opening and hashing every file adds up. Key strategies:

1. **First-pass size check**: Before hashing, group files by size. Only files with matching sizes can be duplicates. If a 1 KB file has no size-mates, skip it entirely — no hash needed. This eliminates 90%+ of files on typical systems.
2. **Streaming hash with early abort**: Once we hash the first file in a size group, subsequent files in that group can abort early as soon as the hash diverges. But SHA-256 isn't designed for streaming comparison — a simpler approach is to compute the full hash for each size-mate and compare at the end. For very large files, consider a fast pre-filter (first 4 KB, then full hash only if matching).
3. **Worker pool concurrency**: Use a bounded semaphore (e.g., `runtime.NumCPU()` workers) to hash files concurrently. I/O bottlenecks are negligible for SSD; HDD scans may benefit from sequential hashing (fewer seeks). Autodetect or accept `--workers N` flag.
4. **Exclusion defaults**: Skip common noise directories: `.git/`, `node_modules/`, `.cache/`, `__pycache__/`, `vendor/`. The user can override with `--no-default-excludes`.

## Open Questions

- **Should we use a fast pre-filter (first 4 KB hash) before full SHA-256?** For very large files (1 GB+), a quick first-4KB hash catch can skip full hashing of files that differ in the first few kilobytes. But this adds complexity — most duplicates are small files where the overhead doesn't matter. Leaning toward optional via `--fast-precheck` flag.
- **How should hardlinks be handled?** Hardlinked files share the same inode and are technically the same content, but they don't consume extra disk space. Should the tool flag them as duplicates or silently skip them? Probably flag them with a "(hardlink)" annotation so the user knows they share disk blocks.
- **What about empty files?** All empty files hash to `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (SHA-256 of empty input). Should they be reported as duplicates? Likely suppress by default (too much noise), with a `--include-empty` flag.

## Research Suggestions

Topics that need deeper investigation by the researcher skill:

- **Fast duplicate detection algorithms** — The size-grouping pre-filter is basic but effective. There are more sophisticated approaches (CDC-based chunking, bloom filters, perceptual hashing for images) that might be relevant for specific use cases. Suggested researcher query: "Fast content-defined chunking vs size-first dedup for file-level duplicate detection CLI tools"
- **Rust vs Go for CLI utilities in 2026** — The language choice substantially affects development speed, binary size, and distribution. Suggested researcher query: "Rust vs Go for small CLI utilities in 2026 — binary size, startup time, cross-compilation ease, and ecosystem comparison"
- **Cross-platform terminal color libraries** — The tool needs colored output on Linux, macOS, and Windows (PowerShell/CMD). Suggested researcher query: "Best cross-platform terminal color libraries for Rust CLI tools in 2026 — colored output on Windows Terminal, CMD, and PowerShell"

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| SHA-256 hashing of very large files (4 GB+) causes visible slowdown | Medium | Medium | Size pre-filter eliminates most candidates. For remaining large files, add `--fast-precheck` to hash only first 4 KB as an early-out check. Default worker count caps at 4 to avoid thrashing HDDs. |
| Permission-denied errors on partial directories confuse users | Medium | Low | Print warnings to stderr, continue scanning. Summarize skipped files at the end. Add `--ignore-permission-denied` (default: true). |
| Accidentally suggesting deletion of hardlinked files (no space savings) | Low | Medium | Detect hardlinks via inode comparison on Linux/macOS; annotate them in output. Do not include them in "wasted space" calculations. |

## Next Steps

1. Decide on language (Go recommended for speed of shipping, Rust if binary size and learning are priorities) and scaffold the project — directory walker, SHA-256 streaming hasher, size-grouping pre-filter.
2. Implement the default terminal output (grouped by hash with file paths and sizes) and the `--json` flag. Test on a moderate directory (e.g., `~/Downloads` with ~10K files) to validate performance.
3. Add exclusion defaults (`.git`, `node_modules`, etc.) and the `--min-size` filter. Publish the first pre-built binary for Linux and macOS via GitHub Releases.

---
*Brainstorm document produced by brainstorm skill. Use the librarian skill to persist this artifact.*
